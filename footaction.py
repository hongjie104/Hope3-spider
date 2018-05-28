#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
爬虫
'''

__author__ = "32968210@qq.com"

import helper
from pyquery import PyQuery
import re
import json
import os


def fetch_detail(url):
    pq = helper.get(url)
    name = pq('#pdp_title > h1').text()
    print('name = %s' % name)
    number = pq('#pdp_selectedSKU').attr('value')
    print('number = %s' % number)

    size_price_arr = []
    # price = pq('.current_price')
    span = pq('span').filter(lambda i, this: PyQuery(this).attr('itemprop') == 'price')
    price = span.text().replace('$', '')
    print('price = ', price)
    price = float(price)
    for a in pq('#pdp_sizes > ul > li > a'):
        size_price_arr.append({
            'size': float(a.text),
            'price': price,
            'isInStock': 'available' in a.get('class')
        })
    print('size_price_arr = ', size_price_arr)

    img_json_str = helper.get(
        'https://images.footaction.com/is/image/EBFL2/%sMM?req=set,json' % number, returnText=True)
    img_json = None
    img_url = None
    try:
        img_json = json.loads(img_json_str.replace(
            '/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
        img_item_arr = img_json.get('set').get('item')
        for img_item in img_item_arr:
            if img_item.get('type') == 'img_set':
                img_url = img_item.get('set').get('item')[0].get('s').get('n')
                break
    except:
        img_json_str = helper.get(
            'https://images.footaction.com/is/image/EBFL2/%s?req=set,json' % number, returnText=True)
        img_json = json.loads(img_json_str.replace(
            '/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
        img_item_arr = img_json.get('set').get('item')
        img_url = img_item_arr[0].get('s').get('n')

    img_url = 'https://images.footaction.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
    print(img_url)
    helper.downloadImg(img_url, os.path.join(
        '.', 'imgs', 'footaction', '%s.jpg' % number))


def fetch_page(url):
    total_page = -1
    page = 1
    while True:
        page_url = '%s?cm_PAGE=%d&Rpp=180&crumbs=76%%20991&Nao=%d' % (
            url, (page - 1) * 180, (page - 1) * 180)
        pq = helper.get(page_url)
        if total_page < 0:
            a = pq('a.next')
            a_arr = a.prevAll('a')
            total_page = int(a_arr[-1].text)
        # 获取商品详情url
        for div in pq('div.product_title'):
            a = PyQuery(div).parents('a')
            fetch_detail(a.attr('href'))
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break


def start():
    # fetch_page('https://www.footaction.com/Mens/Shoes/_-_/N-24Zrj')
    # fetch_page('https://www.footlocker.com/Womens/Shoes/_-_/N-25Zrj')
    fetch_detail('https://www.footaction.com/product/model:271276/sku:23511201/nike-air-force-1-lv8-mens/olive-green/black/')
