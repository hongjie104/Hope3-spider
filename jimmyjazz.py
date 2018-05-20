#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
爬虫
'''

__author__ = "32968210@qq.com"

import helper
from pyquery import PyQuery
import json
import os


def fetch_detail(url):
    pq = helper.get(url)
    name = pq('h1.product_title').text()
    print('name = %s' % name)
    number = pq('span.pistylevalue').text().strip()
    print('number = %s' % number)

    size_price_arr = []
    price = float(pq('div.product_price_content > span.product_price').text().replace('$', ''))
    for a in pq('div.box_wrapper > a'):
        # print(a.text, a.get('class'))
        size_price_arr.append({
            'isInStock': 'piunavailable' not in a.get('class'),
            'size': float(a.text),
            'price': price
        })
    print('size_price_arr = ', size_price_arr)

    img_url = pq('img.product_image').attr('src')
    print('img_url = ', img_url)
    helper.downloadImg(img_url, os.path.join('.', 'imgs', 'jimmyjazz', '%s.jpg' % number))


def fetch_page(url):
    total_page = -1
    page = 1
    while True:
        page_url = '%s??ppg=104&page=%d' % (url, page)
        pq = helper.get(page_url)
        if total_page < 0:
            div = pq('div.pagination_info')[0]
            total_page = int(div.text.strip().split('of ')[1])
        # 获取商品详情url
        for a in pq('div.product_grid_image > a'):
            fetch_detail('http://www.jimmyjazz.com%s' % a.get('href'))
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break


def start():
    fetch_page('http://www.jimmyjazz.com/mens/footwear')
    fetch_page('http://www.jimmyjazz.com/womens/footwear')
    # fetch_detail('http://www.jimmyjazz.com/mens/footwear/jordan-1-mid-sneaker/554724-605?color=Red')
