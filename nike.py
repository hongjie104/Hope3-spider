#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os
import time
import math
import random
import json
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from pyquery import PyQuery


platform = 'nike'

error_detail_url = {}


class PageSpider(Thread):
    def __init__(self, url, q, error_page_url_queue, gender):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.q = q
        self.error_page_url_queue = error_page_url_queue
        self.gender = gender
        self.headers = {'User-Agent': 'Mozilla/5.0'}


    def run(self):
        try:
            txt = helper.get(self.url, myHeaders=self.headers, returnText=True)
            json_data = json.loads(txt)
            item_list = json_data.get('sections')[0].get('items')
            for item_data in item_list:
                self.q.put(item_data.get('pdpUrl'))
        except Exception as e:
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            helper.log(e, platform)
            if error_counter < 3:
                self.q.put(self.url)
        finally:
            helper.log('[INFO] %s is done' % self.url, platform)


class GoodsSpider(Thread):
    def __init__(self, url, gender, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.gender = gender
        self.q = q
        self.crawl_counter = crawl_counter
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.cookies = {
            'nike_locale': 'us/en_us',
            'NIKE_COMMERCE_COUNTRY': 'US',
            'NIKE_COMMERCE_LANG_LOCALE': 'en_US'
        }

    def run(self):
        '''
        解析网站源码
        '''
        time.sleep(random.randint(2, 5))
        try:
            pq = helper.get(self.url, myHeaders=self.headers, cookies=self.cookies)
            # 款型名称
            name = pq('h1#pdp_product_title')[0].text
            # 配色的编号
            number = pq('li.description-preview__style-color').text().split(':')[1].strip()
            # 颜色值
            color_value = pq('li.description-preview__color-description').text().split(':')[1].strip()
            price = 0
            for div in pq('div.text-color-black'):
                if div.get('data-test') == 'product-price':
                    price = float(div.text.replace('$', ''))
                    break
            size_price_arr = []
            for input in pq('div.availableSizeContainer input'):
                # M 3.5 / W 5
                size = input.get('aria-label').replace('W', '').replace('M', '').replace('C', '').strip()
                if '/' in size:
                    size = size.split('/')[0].strip()
                size_price_arr.append({
                    'size': float(size),
                    'price': price,
                    'isInStock': input.get('disabled', False) == False
                })
            img_url = None
            for source in pq('noscript > picture > source'):
                img_url = source.get('srcset')
                break
            if img_url:
                pass
            result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
            if result == 1:
                # 上传到七牛
                qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, platform, '5be444e3c7e854cab4b252a0', self.crawl_counter, '', True if img_url else False)
        except Exception as e:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            helper.log(e, platform)
            if error_counter < 3:
                self.q.put(self.url)


def fetch_page(url_list, gender, q, error_page_url_queue, crawl_counter):
    page_thread_list = []
    # 构造所有url
    for url in url_list:
        # 创建并启动线程
        time.sleep(1.2)
        page_spider = PageSpider(url, q, error_page_url_queue, gender)
        page_spider.start()
        page_thread_list.append(page_spider)
    for t in page_thread_list:
        t.join()

    goods_thread_list = []
    while True:
        queue_size = q.qsize()
        if queue_size > 0:
            # 每次启动5个抓取商品的线程
            for i in range(5 if queue_size > 5 else queue_size):
                goods_spider = GoodsSpider(q.get(), gender, q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start_spider():
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()

    total_num = 781
    url_list = ['https://store.nike.com/html-services/gridwallData?country=US&lang_locale=en_US&gridwallPath=mens-shoes/7puZoi3&pn=%d' % page for page in range(1, int(math.ceil(total_num / 60 + 0.5)))]
    fetch_page(url_list, 1, q, error_page_url_queue, crawl_counter)

    total_num = 616
    url_list = ['https://store.nike.com/html-services/gridwallData?country=US&lang_locale=en_US&gridwallPath=womens-shoes/7ptZoi3&pn=%d' % page for page in range(1, int(math.ceil(total_num / 60 + 0.5)))]
    fetch_page(url_list, 2, q, error_page_url_queue, crawl_counter)

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


def start(action):
    if action == 'common':
        start_spider()
    elif action == 'hot':
        start_hot()

    # goods_spider = GoodsSpider('https://www.nike.com/t/kyrie-5-shoe-sVp7VL', 1, Queue(), 1)
    # goods_spider.start()

    helper.log('done', platform)
