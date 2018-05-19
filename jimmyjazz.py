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
    name = pq('h1.product_title').text()
    print('name = %s' % name)
    # number = pq('span#productSKU').text()
    # print('number = %s' % number)

    # json_str = re.compile(r'var\smodel.*"\};').findall(pq.html())[0]
    # size_arr = json.loads(json_str.replace('var model = ', '').replace(
    #     '"};', '"}')).get('AVAILABLE_SIZES')
    # try:
    #     size_arr = [float(size) for size in size_arr]
    # except:
    #     helper.log('%s 的尺寸不是小数，怀疑不是鞋子' % url)
    #     return
    # size_arr = [float(size) for size in size_arr]
    # print(size_arr)
    # json_str = re.compile(r'var\ssizeObj.*"\}\];').findall(pq.html())[0]
    # # available_size_arr = json.loads(json_str.replace('var sizeobj = ', '').replace('"}];', '"}]'))
    # available_size_arr = json_str.replace(
    #     'var sizeObj = ', '').replace('"}];', '"}]')
    # available_size_arr = json.loads(available_size_arr)
    # # print(available_size_arr)
    # size_price_arr = [{'size': size, 'isInStock': False,
    #                    'price': 0.00} for size in size_arr]
    # for available_size in available_size_arr:
    #     tmp_size = float(available_size.get('size'))
    #     for size_price in size_price_arr:
    #         if tmp_size == size_price.get('size'):
    #             size_price['isInStock'] = True
    #             size_price['price'] = available_size.get('pr_sale')
    #             break
    # print('size_price_arr = ', size_price_arr)

    # sku_id = pq('span#productSKU').text()
    # img_json_str = helper.get(
    #     'https://images.footlocker.com/is/image/EBFL2/%sMM?req=set,json' % sku_id, returnText=True)
    # img_json = None
    # img_url = None
    # try:
    #     img_json = json.loads(img_json_str.replace(
    #         '/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
    #     img_item_arr = img_json.get('set').get('item')
    #     for img_item in img_item_arr:
    #         if img_item.get('type') == 'img_set':
    #             img_url = img_item.get('set').get('item')[0].get('s').get('n')
    #             break
    # except:
    #     img_json_str = helper.get(
    #         'https://images.footlocker.com/is/image/EBFL2/%s?req=set,json' % sku_id, returnText=True)
    #     img_json = json.loads(img_json_str.replace(
    #         '/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
    #     img_item_arr = img_json.get('set').get('item')
    #     img_url = img_item_arr[0].get('s').get('n')

    # img_url = 'https://images.footlocker.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
    # print(img_url)
    # helper.downloadImg(img_url, os.path.join(
    #     '.', 'imgs', 'footlocker', '%s.jpg' % sku_id))


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
            break
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break
        break


def start():
    fetch_page('http://www.jimmyjazz.com/mens/footwear')
    # fetch_page('https://www.footlocker.com/Womens/Shoes/_-_/N-25Zrj')
    # fetch_detail('https://www.footlocker.com/product/model:150073/sku:14571006/jordan-retro-13-mens/black/olive-green/')
