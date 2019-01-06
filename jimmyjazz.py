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
import mongo
import qiniuUploader


def fetch_detail(url, page, total_page):
    print('page / total_page  => ', page, '/', total_page)
    pq = helper.get(url)
    name = pq('h1.product_title').text()
    print('name = %s' % name)
    number = pq('span.pistylevalue').text().strip()
    print('number = %s' % number)

    size_price_arr = []
    price = 0.0
    try:
        price = float(pq('div.product_price_content > span.product_price').text().replace('$', ''))
    except:
        price = 0.0

    for a in pq('div.box_wrapper > a'):
        # print(a.text, a.get('class'))
        size = a.text
        size_price_arr.append({
            'isInStock': 'piunavailable' not in a.get('class'),
            'size': size,
            'price': price
        })
    print('size_price_arr = ', size_price_arr)

    img_downloaded = mongo.is_pending_goods_img_downloaded(url)
    if not img_downloaded:
        img_url = pq('img.product_image').attr('src')
        if not img_url.startswith('http'):
            img_url = 'http://www.jimmyjazz.com' + img_url
        print('img_url = ', img_url)
        if helper.downloadImg(img_url, os.path.join('.', 'imgs', 'jimmyjazz', '%s.jpg' % number)) == 1:
        # 上传到七牛
            qiniuUploader.upload_2_qiniu('jimmyjazz', '%s.jpg' % number, './imgs/jimmyjazz/%s.jpg' % number)
    img_downloaded = True
    mongo.insert_pending_goods(name, number, url, size_price_arr, ['%s.jpg' % number], 'jimmyjazz', img_downloaded=img_downloaded)


def fetch_page(url, page = 1):
    total_page = -1
    while True:
        page_url = '%s??ppg=104&page=%d' % (url, page)
        pq = helper.get(page_url)
        if total_page < 0:
            div = pq('div.pagination_info')[0]
            total_page = int(div.text.strip().split('of ')[1])
        # 获取商品详情url
        for a in pq('div.product_grid_image > a'):
            fetch_detail('http://www.jimmyjazz.com%s' % a.get('href'), page, total_page)
        page += 1
        print('total_page', total_page)
        if page > total_page:
            # 下一页超过最大页数，break
            break


def start(action):
    if action == 'common':
        fetch_page('http://www.jimmyjazz.com/mens/footwear', 21)
        fetch_page('http://www.jimmyjazz.com/womens/footwear')
# fetch_detail('http://www.jimmyjazz.com/mens/footwear/jordan-1-mid-sneaker/554724-605?color=Red')
