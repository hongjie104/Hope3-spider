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


def fetch_detail(url):
    pq = helper.get(url)
    name = pq('h1#product-name').text()
    print('name = %s' % name)
    number = pq('span#product-artno').text().split(':')[1].strip()
    print('number = %s' % number)

    size_price_arr = []
    price = 0.0
    span_arr = pq('div.product-price > span')
    price = float(span_arr[0].text.replace('$', ''))
    for span in pq('span.size-type'):
        size = '.'.join(re.compile(r'\d{1,2}').findall(span.text))
        size_price_arr.append({
            'isInStock': True,
            'size': size,
            'price': price
        })
    print('size_price_arr = ', size_price_arr)

    img_url = pq('img#primary-image').attr('src')
    img_url = 'https://www.sneakersnstuff.com%s' % img_url
    print('img_url = ', img_url)
    helper.downloadImg(img_url, os.path.join('.', 'imgs', 'sneakersnstuff', '%s.jpg' % number))

def fetch_page(url):
    total_page = -1
    page = 1
    while True:
        page_url = '%s/%d?orderBy=Published' % (url, page)
        pq = helper.get(page_url)
        if total_page < 0:
            span = pq('span.current-page')[0]
            total_page = int(span.text.strip().split('(')[1].replace(')', ''))
        # 获取商品详情url
        for a in pq('li.product > a'):
            fetch_detail('https://www.sneakersnstuff.com%s' % a.get('href'))
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break


def start():
    fetch_page('https://www.sneakersnstuff.com/en/904/mens-sneakers')
    fetch_page('https://www.sneakersnstuff.com/en/908/womens-sneakers')
    # fetch_detail('https://www.sneakersnstuff.com/en/product/33362/adidas-stan-smith')
