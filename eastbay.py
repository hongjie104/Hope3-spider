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


def fetch_detail(url):
    pq = helper.get(url)
    name = pq('h1.product_title').text()
    print('name = %s' % name)
    number = pq('span#productSKU').text()
    print('number = %s' % number)

    json_str = re.compile(r'var\smodel.*"\};').findall(pq.html())[0]
    size_arr = json.loads(json_str.replace('var model = ', '').replace('"};', '"}')).get('AVAILABLE_SIZES')
    try:
        size_arr = [float(size) for size in size_arr]
    except:
        helper.log('%s 的尺寸不是小数，怀疑不是鞋子' % url)
        return
    size_arr = [float(size) for size in size_arr]
    print(size_arr)
    json_str = re.compile(r'var\ssizeObj.*"\}\];').findall(pq.html())[0]
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
        img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
        img_item_arr = img_json.get('set').get('item')
        if isinstance(img_item_arr, list):
            img_url = img_item_arr[0].get('s').get('n')
        elif isinstance(img_item_arr, dict):
            img_url = img_item_arr.get('s').get('n')
        
    img_url = 'https://images.eastbay.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
    print(img_url)
    helper.downloadImg(img_url, os.path.join('.', 'imgs', 'eastbay', '%s.jpg' % number))

    mongo.insert_pending_goods(name, number, url, size_price_arr, ['%s.jpg' % number], 'eastbay')



def fetch_page(url):
    total_page = -1
    page = 1
    while True:
        page_url = '%s?cm_PAGE=%d&Rpp=180&crumbs=61&Nao=%d' % (url, (page - 1) * 180, (page - 1) * 180)
        pq = helper.get(page_url)
        if total_page < 0:
            a = pq('a.next')
            a_arr = a.prevAll('a')
            total_page = int(a_arr[-1].text)
        # 获取商品详情url
        for span in pq('span.product_title'):
            a = PyQuery(span).parents('a')
            fetch_detail(a.attr('href'))
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break


def start():
    fetch_page('https://www.eastbay.com/Mens/_-_/N-1p')
    # fetch_page('https://www.eastbay.com/Womens/_-_/N-1q')
    # fetch_detail('https://www.eastbay.com/product/model:171799/sku:10805002/jordan-retro-10-mens/grey/black/')
