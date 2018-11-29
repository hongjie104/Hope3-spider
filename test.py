#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import json
import mongo
import os
import time
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from pyquery import PyQuery
import requests


error_detail_url = {}

platform = 'stockx'


class GoodsSpider(Thread):
    def __init__(self, url, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.q = q
        self.crawl_counter = crawl_counter


    def run(self):
        '''
        解析网站源码
        '''
        time.sleep(2)
        try:
            pq = helper.get(self.url, platform=platform)
            # 款型名称
            name = pq('h1.name').text()
            number = ''
            color_value = ''
            # price = 0.0
            for div in pq('div.detail'):
                div = PyQuery(div)
                key = div.find('span.title').text()
                if key == 'Style':
                    # 配色的编号
                    number = div.find('span')[-1].text.strip()
                elif key == 'Colorway':
                    color_value = div.find('span')[-1].text.strip()
                # elif key == 'Retail Price':
                #     price = div.find('span')[-1].text.replace('US$', '').strip()
                #     price = float(price)
            if number != '':
                # 找出所有尺寸
                size_price_arr = []
                select_options = pq('div.select-options')
                if select_options and len(select_options) > 0:
                    div_list = PyQuery(select_options[0]).find('div.inset div')
                    for i in range(0, len(div_list), 2):
                        if div_list[i].text == 'All':
                            continue
                        if div_list[i + 1].text == 'Bid':
                            size_price_arr.append({
                                'size': div_list[i].text,
                                'price': 0.0,
                                'isInStock': False
                            })
                        else:
                            size_price_arr.append({
                                'size': div_list[i].text,
                                'price': float(div_list[i + 1].text.replace('US$', '').replace(',', '').strip()),
                                'isInStock': True
                            })
                    # 下载图片
                    img_downloaded = mongo.is_pending_goods_img_downloaded(self.url)
                    if not img_downloaded:
                        img_url = ''
                        img_list = pq('div.image-container img')
                        if img_list:
                            img_url = img_list[-1].get('src')
                        else:
                            img_url = pq('div.product-media img').attr('src')
                        img_url_list = img_url.split('?')
                        img_url_query_list = img_url_list[1].split('&')
                        for i in range(0, len(img_url_query_list)):
                            if img_url_query_list[i].split('=')[0] == 'w':
                                img_url_query_list[i] = 'w=600'
                            elif  img_url_query_list[i].split('=')[0] == 'h':
                                img_url_query_list[i] = 'h=600'
                        img_url = img_url_list[0] + '?' + '&'.join(img_url_query_list)
                        result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
                        if result == 1:
                            # 上传到七牛
                            qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
                            img_downloaded = True
            else:
                size_price_arr = []
                # https://stockx.com/api/products/adidas-human-race-nmd-pharrell-cream?includes=market,360&currency=USD
                size_price_url = 'https://stockx.com/api/products%s?includes=market,360&currency=USD' % self.url.split('stockx.com')[1]
                json_txt = helper.get(size_price_url, returnText=True)
                json_data = json.loads(json_txt)
                product_children = json_data.get('Product').get('children')
                for product_key in product_children.keys():
                    product_data = product_children[product_key]
                    market_data = product_data.get('market')
                    size_price_arr.append({
                        'size': product_data.get("shoeSize"),
                        'price': market_data.get("lastSale"),
                        'isInStock': market_data.get("lastSale") > 0
                    })
                number = json_data.get('Product').get('styleId')
                color_value = json_data.get('Product').get('colorway')
                name = json_data.get('Product').get('title')
                # print('number = ', number)
                # print('color_value = ', color_value)
                # print('name = ', name)
                if number != '':
                    # 下载图片
                    img_downloaded = mongo.is_pending_goods_img_downloaded(self.url)
                    if not img_downloaded:
                        img_url_list = json_data.get('Product').get('media').get('360')
                        if len(img_url_list) > 0:
                            img_url = img_url_list[0]
                        else:
                            img_url = json_data.get('Product').get('media').get('imageUrl')
                        img_path = os.path.join('.', 'imgs', platform, '%s.jpg' % number)
                        helper.downloadImg(img_url, img_path)
                        # 上传到七牛
                        qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, img_path)
                        img_downloaded = True
            if number != '':
                mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], 0, color_value, platform, '5bace180c7e854cab4dbcc83', self.crawl_counter, img_downloaded=img_downloaded)
            # print(name, number, self.url, size_price_arr, ['%s.jpg' % number], 0, color_value, platform, '5bace180c7e854cab4dbcc83', self.crawl_counter, img_downloaded)
        except:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            if error_counter < 3:
                self.q.put(self.url)


def start():
    page = 1
    total_page = 1
    while page <= total_page:
        url = 'https://stockx.com/api/browse?_tags=one%2Cair%20jordan&productCategory=sneakers&page=' + str(page)
        html = helper.get(url, returnText=True)
        json_data = json.loads(html)
        pagination = json_data.get('Pagination')
        total_page = pagination.get('lastPage')

        product_list = json_data.get('Products')
        for product in product_list:
            price = product.get('market').get('lowestAsk', None)
            if price:
                number = product.get('styleId')
                if not mongo.add_hot_platform_with_number('5bace180c7e854cab4dbcc83', number):
                    helper.log('not in db... url => ' + product.get('shortDescription') + ' number => ' + number, 'stockx')
        page += 1

    helper.log('done', platform)


if __name__ == "__main__":
    start()