#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os
import time
import json
from threading import Thread
from Queue import Queue
import urllib


error_detail_url = {}

# 本次爬取过程中已经爬过的url
goods_url_list = []

platform = 'goat'

fetched_url_list = []


def fetch_page_json(gender, sort_by, query, page = 1):
    category = ['men', 'women', 'boy', 'girl', 'youth', 'infant'][gender - 1]
    json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/ProductVariants/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    if sort_by == 'PRICE_LOW_HIGH':
        json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_by_price_asc/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    elif sort_by == 'PRICE_HIGH_LOW':
        json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_by_price_desc/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    html = helper.post(json_url, json.dumps({
        'distinct': True,
        'facets': ['size'],
        'hitsPerPage': 20,
        'page': page - 1,
        'facetFilters': '(), (single_gender: %s)' % category,
        'query': query,
    }), {
        'accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Content-Length': '128',
        'content-type': 'application/x-www-form-urlencoded',
        'Host': '2fwotdvm2o-dsn.algolia.net',
        'Origin': 'https://www.goat.com',
        'Referer': 'https://www.goat.com/search?category=%s&query=%s&sortBy=%s' % (category, urllib.quote(query.upper()), sort_by),
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36 OPR/55.0.2994.61'
    }, returnText=True)
    return json.loads(html)


class PageSpider(Thread):
    def __init__(self, gender, sort_by, query, page, q, error_page_url_queue):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.gender = gender
        self.sort_by = sort_by
        self.query = query
        self.page = page
        self.q = q
        self.error_page_url_queue = error_page_url_queue


    def run(self):
        try:
            json_list = fetch_page_json(self.gender, self.sort_by, self.query, self.page)
            url_list = ['https://www.goat.com/sneakers/' + item.get('slug') for item in json_list.get('hits', [])]
            for url in url_list:
                self.q.put(url)
        except:
            helper.log('[ERROR] => ' + self.url, platform)
            self.error_page_url_queue.put({
                'url': self.url,
                'gender': self.gender,
                'sort_by': self.sort_by,
                'query': self.query,
                'page': self.page,
            })


class GoodsSpider(Thread):
    def __init__(self, url, gender, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.gender = gender
        self.q = q
        self.crawl_counter = crawl_counter

    def run(self):
        '''
        解析网站源码
        '''
        global platform
        global error_detail_url
        try:
            slug = self.url.replace('https://www.goat.com/sneakers/', '')
            html = helper.get(self.url, returnText=True)
            if html:
                json_data = json.loads(re.compile(r'window.__context__.*').findall(html)[0].replace('window.__context__ = ', '')).get('default_store').get('product-templates')
                product_json = json_data.get('slug_map').get(slug)
                name = product_json.get('name')
                number = product_json.get('sku')
                color_value = product_json.get('details')
                color_name = name.split('\'')[1] if '\'' in name else ''
                size_list = product_json.get('formatted_available_sizes_new_v2')
                size_price_list = [{'size': float(data.get('size')), 'price': float(data.get('price_cents') / 100), 'isInStock': True} for data in size_list]
                # print({
                #     'name': name,
                #     'number': number,
                #     'color_value': color_value,
                #     'color_name': color_name,
                #     'size_price_list': size_price_list,
                # })

                mongo.insert_pending_goods(name, number, self.url, size_price_list, ['%s.jpg' % number], self.gender, color_value, platform, '5bbf4561c7e854cab45218ba', self.crawl_counter, color_name)

                img_url = product_json.get('original_picture_url')
                result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
                if result == 1:
                    # 上传到七牛
                    qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
                fetched_url_list.append(self.url)
                helper.writeFile(json.dumps(fetched_url_list), './goat-%s.json' % helper.today())
            else:
                error_counter = error_detail_url.get(self.url, 1)
                error_detail_url[self.url] = error_counter + 1
                helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
                if error_counter <= 3:
                    self.q.put(self.url)
        except Exception as e:
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            helper.log(e, platform)
            if error_counter <= 3:
                self.q.put(self.url)


def fetch_page(gender, sort_by, query, q, error_page_url_queue, crawl_counter):
    page_json = fetch_page_json(gender, sort_by, query)
    total_page = page_json.get('nbPages', 0) + 1
    page_thread_list = []
    page = 1
    while page < total_page:
        time.sleep(1.2)
        page_spider = PageSpider(gender, sort_by, query, page, q, error_page_url_queue)
        page_spider.start()
        page_thread_list.append(page_spider)
        page += 1
    for t in page_thread_list:
        t.join()

    goods_thread_list = []
    global goods_url_list
    global fetched_url_list
    while True:
        queue_size = q.qsize()
        if queue_size > 0:
            # 每次启动5个抓取商品的线程
            for i in xrange(5 if queue_size > 5 else queue_size):
                url = q.get()
                if url in goods_url_list:
                    continue
                if url in fetched_url_list:
                    continue
                time.sleep(3.6)
                goods_url_list.append(url)
                goods_spider = GoodsSpider(url, gender, q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start():
    # 读取今天已经抓取过的url
    global fetched_url_list
    json_txt = helper.readFile('./goat-%s.json' % helper.today())
    try:
        if json_txt:
            fetched_url_list = json.loads(json_txt)
    except:
        fetched_url_list = []
    key_list = [
        'Air Jordan 1',
        'jordan 1 retro',
        'jordan 1 mid',
        'JORDAN 1 HI',
        'JORDAN 1 LOW',
        'JORDAN 1 BG',
        'JORDAN 1 GS',
        'JORDAN 1 GP',
        'JORDAN 1 GG',
        'JORDAN 1 TD',
        'JORDAN 1 PS',
        'JORDAN 1 BT',
        'JORDAN 1 J2K',
        'JORDAN 1 KO',
        'JORDAN 1 PRE',
        'JORDAN 1 OG',
        'JORDAN 1 SE',
        'JORDAN 1 WMNS',
        'JORDAN 1 X',
        'Jordan 2',
        'Jordan 3',
        'Jordan 4',
        'Jordan 5',
        'Jordan 6',
        'jordan 7',
        'jordan 8',
        'jordan 9',
        'jordan 10',
        'jordan 11',
        'jordan 12',
        'jordan 13',
        'jordan 14',
        'jordan 15',
        'jordan 16',
        'jordan 17',
        'jordan 18',
        'jordan 19',
        'jordan 20',
        'jordan 21',
        'jordan 22',
        'jordan 23',
        'jordan 25',
        'jordan 26',
        'jordan 27',
        'jordan 28',
        'jordan 29',
        'jordan 30',
        'jordan 31',
        'jordan 32',
        'jordan 33',
        'jordan 34',
        'jordan 35',
        'jordan 36',
        'jordan 37',
        'jordan 38',
        'jordan 39',
        'jordan 40',
        'JORDAN FUSION',
        'JORDAN FUTURE',
        'JORDAN CP3',
        'JORDAN MELO',
        'JORDAN SPIZIKE',
        'JORDAN WESTBROOK',
        'JORDAN TEAM',
        'JORDAN LEGACY',
        'JORDAN HYDRO',
        'JORDAN DB',
        'JORDAN WHY NOT',
        'JORDAN FLYKNIT',
        'JORDAN NRG',
        'JORDAN TURE',
        'JORDAN SHINE',
        'JORDAN HORIZON',
        'JORDAN SUPER.FLY',
        'SON OF MARS',
        'JORDAN FORMULA',
        'ORDAN B.FLY',
        'JORDAN ULTRA FLY',
        'JORDAN TRAINER',
        'JORDAN JUMPMAN',
        'JORDAN SC',
        'JORDAN ECLIPSE',
        'JORDAN 1 TREK',
        'JORDAN 6-17-2',
        'JORDAN ACADEMY',
        'JORDAN FLY 89',
        'JORDAN 1 FLIGHT',
        'JORDAN FLIGHT',
        'JORDAN FIRST CLASS',
        'JORDAN FLY LOCK',
        'JORDAN FRANCHISE',
        'JORDAN FLOW'
    ]
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()

    for key in key_list:
        # 先取男鞋 价格从低到高
        fetch_page(1, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter)
        # 先取男鞋 价格从高到低
        fetch_page(1, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter)
        # 先取女鞋 价格从低到高
        fetch_page(2, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter)
        # 先取女鞋 价格从高到低
        fetch_page(2, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter)
        # 先取青少年鞋 价格从低到高
        fetch_page(5, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter)
        # 先取青少年鞋 价格从高到低
        fetch_page(5, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter)
        # 先取婴儿鞋 价格从低到高
        fetch_page(6, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter)
        # 先取婴儿鞋 价格从高到低
        fetch_page(6, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter)

    # url = 'https://www.goat.com/sneakers/air-jordan-11-retro-low-women-s-snakeskin-833003-103'
    # slug = url.replace('https://www.goat.com/sneakers/', '')
    # html = helper.get(url, returnText=True)
    # json_data = json.loads(re.compile(r'window.__context__.*').findall(html)[0].replace('window.__context__ = ', '')).get('default_store').get('product-templates')
    # product_json = json_data.get('slug_map').get(slug)
    # name = product_json.get('name')
    # number = product_json.get('sku')
    # color_value = product_json.get('details')
    # color_name = name.split('\'')[1] if '\'' in name else ''
    # size_list = product_json.get('formatted_available_sizes_new_v2')
    # size_price_list = [{'size': float(data.get('size')), 'price': float(data.get('price_cents') / 100), 'isInStock': True} for data in size_list]
    # # print(name, number ,color_value, color_name, size_price_list)

    # mongo.insert_pending_goods(name, number, url, size_price_list, ['%s.jpg' % number], 2, color_value, platform, '5bbf4561c7e854cab45218ba', 2, color_name)

    # img_url = product_json.get('original_picture_url')
    # result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
    # if result == 1:
    #     # 上传到七牛
    #     qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))

    # 处理出错的链接
    # while not error_page_url_queue.empty():
    #     error_page_url_list = []
    #     while not error_page_url_queue.empty():
    #         error_page_url_list.append(error_page_url_queue.get())

    #     error_page_men_url_list = [{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_url_list if url_data.get('gender') == 1]
    #     fetch_page([{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_men_url_list], 1, q, error_page_url_queue, {
    #         'mnid': 'men_shoes',
    #         'Ns': 'sku.bestSeller | 1',
    #         'isAjax': 'true'
    #     }, crawl_counter)
    helper.log('done', platform)

