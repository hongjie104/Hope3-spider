#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
爬虫
'''

__author__ = "32968210@qq.com"

import helper
from pyquery import PyQuery


def fetch_detail(url):
    pq = helper.get(url)
    name = pq('h1.product_title').text()
    number = pq('span#productSKU').text()
    size_price_arr = []


def fetch_man():
    total_page = -1
    page = 1
    while True:
        url = 'https://www.eastbay.com/Mens/_-_/N-1p?cm_PAGE=%d&Rpp=180&crumbs=61&Nao=%d' % ((page - 1) * 180, (page - 1) * 180)
        pq = helper.get(url)
        if total_page < 0:
            a = pq('a.next')
            total_page = int(a.prevAll()[-1].text)
        # 获取商品详情url
        for span in pq('span.product_title'):
            a = PyQuery(span).parents('a')
            fetch_detail(a.attr('href'))
        if page + 1 > total_page:
            # 下一页超过最大页数，break
            break


def start():
    # fetch_man()
    fetch_detail('https://www.eastbay.com/product/model:171799/sku:10805002/jordan-retro-10-mens/grey/black/')
