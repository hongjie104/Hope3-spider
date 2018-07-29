#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
爬虫
'''

__author__ = "32968210@qq.com"

import helper
from pyquery import PyQuery
import json
import re
import os
import mongo
import qiniuUploader


def fetch_detail(url, page = 0):
    if url == 'https://www.sneakersnstuff.com/en/product/21411/adidas-ultra-boost':
        return
    if url == 'https://www.sneakersnstuff.com/en/product/21129/brooks-regent-american-dream':
        return
    if url == 'https://www.sneakersnstuff.com/en/product/20527/vans-sk8-hi':
        return
    print('page = %d' % page)
    pq = helper.get(url)
    name = None
    try:
        name = pq('h1#product-name').text()
        if name == '':
            name = 1 / 0
    except:
        name = pq('p.product-name > span.brand').text()
        name += pq('p.product-name > span.name').text()
    print('name = %s' % name)

    number = None
    try:
        number = pq('span#product-artno').text().split(':')[1].strip()
    except:
        number = pq('div#tab1 strong').parents('p').text().replace('Article number:', '').strip()
    print('number = %s' % number)

    size_price_arr = []
    price = 0.0
    span_arr = []
    try:
        span_arr = pq('div.product-price > span')
        price = float(span_arr[0].text.encode('utf-8').replace('$', '').replace('¥', ''))
        price *= 0.1468
        price = float("%.2f" % price)
        for span in pq('span.size-type'):
            size = '.'.join(re.compile(r'\d{1,2}').findall(span.text))
            size_price_arr.append({
                'isInStock': True,
                'size': size,
                'price': price
            })
    except:
        try:
            price = float(pq('p.product-price > span.sale').text().encode('utf-8').replace('¥', ''))
            price *= 0.1468
            price = float("%.2f" % price)
            for span in pq('span.size-type'):
                size = span.text.replace('US ', '').replace('\r', '').replace('\n', '').replace('\t', '')
                size_price_arr.append({
                    'isInStock': True,
                    'size': size,
                    'price': price
                })
        except:
            pass
    print('size_price_arr = ', size_price_arr)

    mongo.insert_pending_goods(name, number, url, size_price_arr, ['%s.jpg' % number], 'sneakersnstuff')

    img_url = None
    try:
        img_url = pq('img#primary-image').attr('src')
        if not img_url:
            img_url = 1 / 0
    except:
        img_url = pq('div.media > img').attr('src')
    img_url = 'https://www.sneakersnstuff.com%s' % img_url
    print('img_url = ', img_url)
    if helper.downloadImg(img_url, os.path.join('.', 'imgs', 'sneakersnstuff', '%s.jpg' % number)) > 0:
        # 上传到七牛
        qiniuUploader.upload_2_qiniu('sneakersnstuff', '%s.jpg' % number, './imgs/sneakersnstuff/%s.jpg' % number)

def fetch_page(url):
    total_page = -1
    page = 27
    while True:
        page_url = '%s/%d?orderBy=Published' % (url, page)
        pq = helper.get(page_url)
        if total_page < 0:
            span = pq('span.current-page')[0]
            total_page = int(span.text.strip().split('(')[1].replace(')', ''))
        # 获取商品详情url
        for a in pq('li.product > a'):
            fetch_detail('https://www.sneakersnstuff.com%s' % a.get('href'), page)
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break


def start():
    fetch_page('https://www.sneakersnstuff.com/en/904/mens-sneakers')
    # fetch_page('https://www.sneakersnstuff.com/en/908/womens-sneakers')
    # fetch_detail('https://www.sneakersnstuff.com/en/product/21412/adidas-equipment-running-guidance-93')
