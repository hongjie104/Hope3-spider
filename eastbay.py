#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
爬虫
'''

__author__ = "32968210@qq.com"

import helper
import mongo
from pyquery import PyQuery
import re
import json
import os
import datetime

# ak_bmsc = None

def fetch_detail(url, page = 1):
    print('page = ', page)
    updateTime = mongo.get_goods_update_date(url)
    if datetime.datetime.now().date() == updateTime.date():
        print('just updated today, jump it')
        return
    # global ak_bmsc
    if not mongo.is_pending_goods_deleted(url):
        # pq = helper.get(url, {'ak_bmsc': ak_bmsc})
        pq = helper.get(url, myHeaders={'User-Agent': 'Mozilla/5.0'})
        name = pq('h1.product_title').text()
        if not name:
            return
        print('name = %s' % name)
        number = pq('span#productSKU').text()
        if not number:
            return
        print('number = %s' % number)

        json_str = re.compile(r'var\smodel\s=\s.*"\};').findall(pq.html())[0]
        size_arr = json.loads(json_str.replace('var model = ', '').replace('"};', '"}')).get('AVAILABLE_SIZES')
        try:
            size_arr = [float(size) for size in size_arr]
        except:
            helper.log('%s 的尺寸不是小数，怀疑不是鞋子' % url)
            return
        size_arr = [float(size) for size in size_arr]
        print(size_arr)
        json_str = re.compile(r'var\ssizeObj\s=\s.*"\}\];').findall(pq.html())[0]
        # available_size_arr = json.loads(json_str.replace('var sizeobj = ', '').replace('"}];', '"}]'))
        available_size_arr = json_str.replace('var sizeObj = ', '').replace('"}];', '"}]')
        available_size_arr = json.loads(available_size_arr)
        # print(available_size_arr)
        size_price_arr = [{'size': size, 'isInStock': False, 'price': 0.00} for size in size_arr]
        for available_size in available_size_arr:
            tmp_size = float(available_size.get('size'))
            for size_price in size_price_arr:
                if tmp_size == size_price.get('size'):
                    size_price['isInStock'] = True
                    size_price['price'] = available_size.get('pr_sale')
                    break
        print('size_price_arr = ', size_price_arr)

        if not mongo.is_pending_goods_img_downloaded(url):
            img_json_str = helper.get('https://images.eastbay.com/is/image/EBFL2/%sMM?req=set,json' % number, returnText=True)
            img_json = None
            img_url = None
            try:
                img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
                img_item_arr = img_json.get('set').get('item')
                for img_item in img_item_arr:
                    if img_item.get('type') == 'img_set':
                        img_url = img_item.get('set').get('item')[0].get('s').get('n')
                        break
            except:
                img_json_str = helper.get('https://images.eastbay.com/is/image/EBFL2/%s?req=set,json' % number, returnText=True)
                try:
                    img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
                    img_item_arr = img_json.get('set').get('item')
                    if isinstance(img_item_arr, list):
                        img_url = img_item_arr[0].get('s').get('n')
                    elif isinstance(img_item_arr, dict):
                        img_url = img_item_arr.get('s').get('n')
                except:
                    img_url = None
            if img_url:
                img_url = 'https://images.eastbay.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
                print(img_url)
                helper.downloadImg(img_url, os.path.join('.', 'imgs', 'eastbay', '%s.jpg' % number))
        mongo.insert_pending_goods(name, number, url, size_price_arr, ['%s.jpg' % number], 'eastbay')


def fetch_page(url, page = 1):    
    # global ak_bmsc
    total_page = -1
    while True:
        page_url = '%s?cm_PAGE=%d&Rpp=180&crumbs=61&Nao=%d' % (url, (page - 1) * 180, (page - 1) * 180)
        # pq = helper.get(page_url, cookies={'aK_bmsc': ak_bmsc})
        pq = helper.get(page_url, myHeaders={'User-Agent': 'Mozilla/5.0'})
        if total_page < 0:
            a = pq('a.next')
            a_arr = a.prevAll('a')
            total_page = int(a_arr[-1].text)
        # 获取商品详情url
        for span in pq('span.product_title'):
            a = PyQuery(span).parents('a')
            fetch_detail(a.attr('href'), page)
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break


# def fetch_ak_bmsc():
#     global ak_bmsc
#     ak_bmsc = helper.get_ak_bmsc_cookie('https://www.eastbay.com')


def start():
    # fetch_ak_bmsc()
    fetch_page('https://www.eastbay.com/Mens/_-_/N-1p', 14)
    fetch_page('https://www.eastbay.com/Womens/_-_/N-1q')
    # fetch_detail('https://www.eastbay.com/product/model:282467/sku:2571D013/brooks-ghost-10-mens/silver/navy/')
    # fetch_detail('https://www.eastbay.com/product/model:190074/sku:55088031/jordan-retro-1-high-og-mens/black/gold/')
    # fetch_detail('https://www.eastbay.com/product/model:291471/sku:DB0895/adidas-adizero-5-star-7.0-adimoji-mens/gold/black/')
