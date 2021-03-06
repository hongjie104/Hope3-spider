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
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import urllib


error_detail_url = {}

# 本次爬取过程中已经爬过的url
goods_url_list = []

platform = 'goat'

fetched_url_list = []


def fetch_page_json(gender, sort_by, query, page = 1):
    category = ['men', 'women', 'boy', 'girl', 'youth', 'infant'][gender - 1]
    # json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/ProductVariants/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_v2/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    if sort_by == 'PRICE_LOW_HIGH':
        # json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_by_price_asc/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
        json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_v2_by_price_asc/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    elif sort_by == 'PRICE_HIGH_LOW':
        # json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_by_price_desc/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
        json_url = 'https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_v2_by_price_desc/query?x-algolia-agent=Algolia%20for%20vanilla%20JavaScript%203.25.1&x-algolia-application-id=2FWOTDVM2O&x-algolia-api-key=ac96de6fef0e02bb95d433d8d5c7038a'
    try:
        query = urllib.quote(query.upper())
    except:
        query = urllib.parse.quote(query.upper())
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
        'Referer': 'https://www.goat.com/search?category=%s&query=%s&sortBy=%s' % (category, query, sort_by),
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36 OPR/55.0.2994.61'
    }, returnText=True, platform=platform)
    if html:
        return json.loads(html)
    return None


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
        time.sleep(3.6)
        global platform
        global error_detail_url
        try:
            slug = self.url.replace('https://www.goat.com/sneakers/', '')
            html = helper.get(self.url, returnText=True, platform=platform)
            if html:
                json_data = re.compile(r'window.__context__.*')
                json_data = json_data.findall(html)[0]
                json_data = json_data.replace('window.__context__ = ', '')
                json_data = json_data.replace('</script>', '')
                json_data = json.loads(json_data)
                json_data = json_data.get('default_store')
                json_data = json_data.get('product-templates')
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
                img_downloaded = mongo.is_pending_goods_img_downloaded(self.url)
                if not img_downloaded:
                    img_url = product_json.get('original_picture_url')
                    result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
                    if result == 1:
                        # 上传到七牛
                        qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
                        img_downloaded = True
                mongo.insert_pending_goods(name, number, self.url, size_price_list, ['%s.jpg' % number], self.gender, color_value, platform, '5bbf4561c7e854cab45218ba', self.crawl_counter, color_name, img_downloaded)
                fetched_url_list.append(self.url)
                helper.writeFile(json.dumps(fetched_url_list), './logs/goat-%s.json' % helper.today())
            else:
                error_counter = error_detail_url.get(self.url, 1)
                error_detail_url[self.url] = error_counter + 1
                helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
                if error_counter < 3:
                    self.q.put(self.url)
        except Exception as e:
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            helper.log(e, platform)
            if error_counter < 3:
                self.q.put(self.url)
        finally:
            helper.log('[INFO] %s is done' % self.url, platform)


def fetch_page(gender, sort_by, query, q, error_page_url_queue, crawl_counter):
    page_json = fetch_page_json(gender, sort_by, query)
    while not page_json:
        # 如果page_json获取失败，就等一会再获取
        time.sleep(3)
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
    global error_detail_url
    while True:
        # 如果有问题的详情页数量超过了9，那就认为是网站的反爬虫机制启动了
        # 就停止爬虫，等几个小时候再启动
        # if len(error_detail_url.items()) > 9:
        #     helper.log('[info] return, len(error_detail_url.items()) = %d' % len(error_detail_url.items()), platform)
        #     return False
        queue_size = q.qsize()
        if queue_size > 0:
            # 每次启动5个抓取商品的线程
            for i in range(5 if queue_size > 5 else queue_size):
                url = q.get()
                if url in goods_url_list:
                    continue
                if url in fetched_url_list:
                    helper.log('[info] fetched url = %s' % url, platform)
                    continue
                goods_url_list.append(url)
                goods_spider = GoodsSpider(url, gender, q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            return True


def start(action):
    # 读取今天已经抓取过的url
    global fetched_url_list
    json_txt = helper.readFile('./logs/goat-%s.json' % helper.today())
    try:
        if json_txt:
            fetched_url_list = json.loads(json_txt)
    except:
        fetched_url_list = []
    f = open('./keyword.json')
    txt = f.read()
    f.close()
    key_list = json.loads(txt)
    # 去重
    # key_list = list(set(key_list))
    key_list = helper.delRepeat(key_list)
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()

    # TODO:
    key_list = ['DUNK']
    for key in key_list:
        key = key.replace('\n', '')
        helper.log('[INFO] now key = ' + key, platform)
        # 先取男鞋 价格从低到高
        if fetch_page(1, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter):
            helper.log('[INFO] => fetch_page is done, 1, PRICE_LOW_HIGH', platform)
        # 先取男鞋 价格从高到低
        if fetch_page(1, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter):
            helper.log('[INFO] => fetch_page is done, 1, PRICE_HIGH_LOW', platform)
        # 先取女鞋 价格从低到高
        if fetch_page(2, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter):
            helper.log('[INFO] => fetch_page is done, 2, PRICE_LOW_HIGH', platform)
        # 先取女鞋 价格从高到低
        if fetch_page(2, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter):
            helper.log('[INFO] => fetch_page is done, 2, PRICE_HIGH_LOW', platform)
        # 先取青少年鞋 价格从低到高
        if fetch_page(5, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter):
            helper.log('[INFO] => fetch_page is done, 5, PRICE_LOW_HIGH', platform)
        # 先取青少年鞋 价格从高到低
        if fetch_page(5, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter):
            helper.log('[INFO] => fetch_page is done, 5, PRICE_HIGH_LOW', platform)
        #     # 先取婴儿鞋 价格从低到高
        #     if fetch_page(6, 'PRICE_LOW_HIGH', key, q, error_page_url_queue, crawl_counter):
        #         helper.log('[INFO] => fetch_page is done, 6, PRICE_LOW_HIGH', platform)
        #         # 先取婴儿鞋 价格从高到低
        #         fetch_page(6, 'PRICE_HIGH_LOW', key, q, error_page_url_queue, crawl_counter)
        #         helper.log('[INFO] => fetch_page is done, 6, PRICE_HIGH_LOW', platform)

    # goods_spider = GoodsSpider('https://www.goat.com/sneakers/force-savage-pro-baseball-cleat-880144-410', 1, Queue(), crawl_counter)
    # goods_spider.start()

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

