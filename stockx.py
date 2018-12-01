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


# class PageSpider(Thread):
#     def __init__(self, url, q, error_page_url_queue):
#         # 重写写父类的__init__方法
#         super(PageSpider, self).__init__()
#         self.url = url
#         self.q = q
#         self.error_page_url_queue = error_page_url_queue


#     def run(self):
#         try:
#             json_txt = helper.get(self.url, returnText=True, platform=platform)
#             json_data = json.loads(json_txt)
#             goods_list = json_data.get('hits')
#             for goods in goods_list:
#                 if goods.get('product_category') == 'sneakers':
#                     self.q.put('https://stockx.com/%s' % goods.get('url'))
#         except:
#             helper.log('[ERROR] => ' + self.url, platform)
#             self.error_page_url_queue.put(self.url)


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


# def fetch_page(url_list, q, error_page_url_queue, crawl_counter):
#     page_thread_list = []
#     # 构造所有url
#     for url in url_list:
#         # 创建并启动线程
#         time.sleep(1.2)
#         page_spider = PageSpider(url, q, error_page_url_queue)
#         page_spider.start()
#         page_thread_list.append(page_spider)
#     for t in page_thread_list:
#         t.join()

#     goods_thread_list = []
#     while True:
#         queue_size = q.qsize()
#         if queue_size > 0:
#             # 每次启动5个抓取商品的线程
#             for i in range(5 if queue_size > 5 else queue_size):
#                 goods_spider = GoodsSpider(q.get(), q, crawl_counter)
#                 goods_spider.start()
#                 goods_thread_list.append(goods_spider)
#             for t in goods_thread_list:
#                 t.join()
#             goods_thread_list = []
#         else:
#             break


def start_spider():
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # # 有错误的页面链接
    # error_page_url_queue = Queue()
    # # url = 'https://stockx.com/api/browse?order=DESC&page=1&productCategory=sneakers&sort=release_date'
    # # json_txt = helper.get(url, returnText=True)
    # # json_data = json.loads(json_txt)
    # # pagination = json_data.get('Pagination')
    # # total_page = pagination.get('lastPage')
    # # fetch_page(['https://stockx.com/api/browse?order=DESC&page=%d&productCategory=sneakers&sort=release_date' % page for page in range(1, total_page + 1)], q, error_page_url_queue, crawl_counter)

    # f = open('./keyword.json')
    # txt = f.read()
    # f.close()
    # keywords = json.loads(txt)
    # for keyword in keywords:
    #     url = 'https://stockx.com/api/search?query=%s&page=0&currency=USD' % keyword
    #     json_txt = helper.get(url, returnText=True, platform=platform)
    #     json_data = json.loads(json_txt)
    #     total_page = json_data.get('nbPages')
    #     fetch_page(['https://stockx.com/api/search?query=%s&page=%d&currency=USD' % (keyword, page) for page in range(0, total_page)], q, error_page_url_queue, crawl_counter)

    # # # 处理出错的链接
    # # while not error_page_url_queue.empty():
    # #     error_page_url_list = []
    # #     while not error_page_url_queue.empty():
    # #         error_page_url_list.append(error_page_url_queue.get())

    # #     fetch_page(error_page_url_list, q, error_page_url_queue, crawl_counter)


    # # goods_spider = GoodsSpider('https://stockx.com/adidas-sl-loop-wish-independent-currency', Queue(), 1)
    # # goods_spider.start()
    # # goods_spider.join()

    f = open('./keyword.json')
    txt = f.read()
    f.close()
    key_list = json.loads(txt)
    # 去重
    key_list = helper.delRepeat(key_list)
    for key in key_list:
        helper.log('key = ' + key, platform)
        page = 0
        total_page = 1
        while page < total_page:
            time.sleep(2)
            data = {"params":"query=" + key.replace(' ', '%20').replace('/', '%2F') + "&facets=*&filters=product_category%3A%22sneakers%22&page=" + str(page)}
            headers = {
                'accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'content-type': 'application/x-www-form-urlencoded',
                'Host': 'xw7sbct9v6-2.algolianet.com',
                'Origin': 'https://stockx.com',
                'Referer': 'https://stockx.com/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36 OPR/56.0.3051.104',
            }
            html = helper.post('https://xw7sbct9v6-2.algolianet.com/1/indexes/products/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.30.0&x-algolia-application-id=XW7SBCT9V6&x-algolia-api-key=6bfb5abee4dcd8cea8f0ca1ca085c2b3', None, headers, returnText=True, platform=platform, json=data, timeout=60)
            json_data = json.loads(html)
            total_page = json_data.get('nbPages', 1)
            nb_hits = json_data.get('nbHits', 0)
            if nb_hits < 1:
                helper.log('no hit key = ' + key, platform)
                break
            hits = json_data.get('hits')
            for hit in hits:
                q.put('https://stockx.com/' + hit.get('url'))
            page += 1

        while True:
            queue_size = q.qsize()
            if queue_size > 0:
                goods_thread_list = []
                # 每次启动5个抓取商品的线程
                for i in range(5 if queue_size > 5 else queue_size):
                    goods_spider = GoodsSpider(q.get(), q, crawl_counter)
                    goods_spider.start()
                    goods_thread_list.append(goods_spider)
                for t in goods_thread_list:
                    t.join()
                goods_thread_list = []
            else:
                break


def start_hot():
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    url_list = [
        'https://stockx.com/api/browse?_tags=one%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=two%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=three%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=four%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=five%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=six%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=seven%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=eight%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=nine%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=ten%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=eleven%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twelve%2Cair%20jordan&currency=AUD&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=thirteen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=fourteen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=fifteen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=sixteen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=seventeen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=eighteen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=nineteen%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-one%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-two%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-three%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-four%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-five%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-six%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-seven%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-eight%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=twenty-nine%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=thirty%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=thirty-one%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=packs%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=other%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=spizike%2Cair%20jordan&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=foamposite%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=kd%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=kobe%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=lebron%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=air%20force%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=air%20max%2Cnike&productCategory=sneakers&page=',
        'Https://stockx.com/api/browse?_tags=nike%20basketball%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=nike%20sb%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=nike%20other%2Cnike&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=yeezy%2Cadidas&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=ultra%20boost%2Cadidas&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=nmd%2Cadidas&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=iniki%2Cadidas&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=other%2Cadidas&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=asics&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=diadora&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=new%20balance&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=puma&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=under%20armour&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=vans&currency=CAD&productCategory=sneakers&page=',
        'https://stockx.com/api/browse?_tags=converse&productCategory=sneakers&page=',
    ]
    for url in url_list:
        page = 1
        total_page = 1
        while page <= total_page:
            html = helper.get(url + str(page), returnText=True)
            json_data = json.loads(html)
            pagination = json_data.get('Pagination')
            total_page = pagination.get('lastPage')

            product_list = json_data.get('Products')
            for product in product_list:
                price = product.get('market').get('lowestAsk', None)
                if price:
                    number = product.get('styleId')
                    if not mongo.add_hot_platform_with_number('5bace180c7e854cab4dbcc83', number):
                        q.put('https://stockx.com/' + product.get('urlKey'))
                        helper.log('not in db... url => ' + product.get('urlKey') + ' number => ' + number, 'stockx')
            page += 1
    # 开始抓取还没有入库的商品
    while True:
        queue_size = q.qsize()
        if queue_size > 0:
            goods_thread_list = []
            # 每次启动5个抓取商品的线程
            for i in range(5 if queue_size > 5 else queue_size):
                goods_spider = GoodsSpider(q.get(), q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start(action):
    if action == 'common':
        start_spider()
    elif action == 'hot':
        start_hot()

    helper.log('done', platform)
