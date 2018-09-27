#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import json
import mongo
import os
import time
from threading import Thread
from Queue import Queue


error_detail_url = {}


class PageSpider(Thread):
    def __init__(self, url, q, error_page_url_queue):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.q = q
        self.error_page_url_queue = error_page_url_queue


    def run(self):
        try:
            json_txt = helper.get(self.url, returnText=True)
            json_data = json.loads(json_txt)
            products = json_data.get('Products')
            for p in products:
                self.q.put('https://stockx.com/%s' % p.get('urlKey'))
                print('https://stockx.com/%s' % p.get('urlKey'))
        except:
            helper.log('[ERROR] => ' + self.url, 'stockx')
            self.error_page_url_queue.put(self.url)


class GoodsSpider(Thread):
    def __init__(self, url, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.q = q
        self.crawl_counter = crawl_counter


    def run(self):
        '''
        解析网站源码
        '''
        try:
            pq = helper.get(self.url, myHeaders=self.headers)
            # 款型名称
            name = pq('input.bVProductName').attr('value')
            # 配色的编号
            span = pq('div#styleColors span.styleColorIds')
            number = span.text().strip().replace('- ', '')
            number = re.sub(re.compile(r'\s'), ' ', number)
            number = ''.join(number.split())
            span = pq('div#productPrices span')
            price = span.text().replace('$', '').split(' ')[0]
            try:
                price = float(price)
            except:
                price = 0.0
            aria_label_list = pq('div#productSizes button')
            size_price_arr = [{'size': float(re.compile(r'\d+\.[05]').findall(a.get('aria-label'))[0]), 'price': price, 'isInStock': 'unavailable' not in a.get('aria-label')} for a in aria_label_list]
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, '', 'stockx', '5bace180c7e854cab4dbcc83', self.crawl_counter)
            # 下载图片
            img_list = pq('div.pdp-image')
            img_url = 'https:' + (img_list[2].get('data-large') if len(img_list) > 2 else img_list[-1].get('data-large'))
            result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'stockx', '%s.jpg' % number))
            if result == 1:
                # 上传到七牛
                qiniuUploader.upload_2_qiniu('stockx', '%s.jpg' % number, './imgs/stockx/%s.jpg' % number)
        except:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), 'stockx')
            if error_counter <= 3:
                self.q.put(self.url)


def fetch_page(url_list, q, error_page_url_queue, crawl_counter):
    page_thread_list = []
    # 构造所有url
    for url in url_list:
        # 创建并启动线程
        time.sleep(1.2)
        page_spider = PageSpider(url, q, error_page_url_queue)
        page_spider.start()
        page_thread_list.append(page_spider)
    for t in page_thread_list:
        t.join()

    goods_thread_list = []
    while True:
        queue_size = q.qsize()
        if queue_size > 0:
            # 每次启动5个抓取商品的线程
            for i in xrange(5 if queue_size > 5 else queue_size):
                time.sleep(2)
                goods_spider = GoodsSpider(q.get(), q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start():
    crawl_counter = mongo.get_crawl_counter('stockx')
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()
    url = 'https://stockx.com/api/browse?order=DESC&page=1&productCategory=sneakers&sort=release_date'
    json_txt = helper.get(url, returnText=True)
    json_data = json.loads(json_txt)
    pagination = json_data.get('Pagination')
    total_page = pagination.get('lastPage')
    fetch_page(['https://stockx.com/api/browse?order=DESC&page=%d&productCategory=sneakers&sort=release_date' % page for page in xrange(1, total_page)], q, error_page_url_queue, crawl_counter)

    # # 处理出错的链接
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
    #     error_page_women_url_list = [{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_url_list if url_data.get('gender') == 2]
    #     fetch_page([{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_women_url_list], 2, q, error_page_url_queue, {
    #         'mnid': 'women_shoes',
    #         'isAjax': 'true',
    #     }, crawl_counter)
    helper.log('done', 'stockx')
