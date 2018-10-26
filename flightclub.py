#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os
import time
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue


error_detail_url = {}


class PageSpider(Thread):
    def __init__(self, url, q, error_page_url_queue, gender):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.q = q
        self.error_page_url_queue = error_page_url_queue
        self.gender = gender

    def run(self):
        try:
            pq = helper.get(self.url)
            for a in pq('li.item > a'):
                self.q.put(a.get('href'))
        except:
            helper.log('[ERROR] => ' + self.url, 'flightclub')
            self.error_page_url_queue.put({'url': self.url, 'gender': self.gender})


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
        try:
            pq = helper.get(self.url)
            name = pq('div.nosto_product > span.name').text()
            number = ''
            color_value = ''
            index = 0
            for li in pq('li.attribute-list-item'):
                if index == 0:
                    number = li.text.strip()
                elif index == 1:
                    color_value = li.text.strip()
                index += 1
            size_price_arr = []
            for div in pq('div.hidden > div'):
                price = float(div.find('span').text)
                size = float(div.find('div').find('meta').get('content').split('_')[-1])
                size_price_arr.append({
                    'size': size,
                    'price': price,
                    'isInStock': True
                })
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, 'flightclub', '5ac8592c48555b1ba318964a', self.crawl_counter)
            img_url = pq('link.hidden').attr('src')
            result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'flightclub', '%s.jpg' % number))
            if result == 1:
                # 上传到七牛
                qiniuUploader.upload_2_qiniu('flightclub', '%s.jpg' % number, './imgs/flightclub/%s.jpg' % number)
        except:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), 'flightclub')
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
                time.sleep(2)
                goods_spider = GoodsSpider(q.get(), gender, q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start():
    crawl_counter = mongo.get_crawl_counter('flightclub')
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()
    total_page = 70
    base_url = 'https://www.flightclub.com/men?id=446&limit=90&p='
    fetch_page([base_url + str(page) for page in range(1, total_page + 1)], 1, q, error_page_url_queue, crawl_counter)

    total_page = 4
    base_url = 'https://www.flightclub.com/women?id=350&limit=90&p='
    fetch_page([base_url + str(page) for page in range(1, total_page + 1)], 2, q, error_page_url_queue, crawl_counter)

    # 处理出错的链接
    while not error_page_url_queue.empty():
        error_page_url_list = []
        while not error_page_url_queue.empty():
            error_page_url_list.append(error_page_url_queue.get())

        error_page_men_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 1]
        fetch_page(error_page_men_url_list, 1, q, error_page_url_queue, crawl_counter)

        error_page_women_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 2]
        fetch_page(error_page_women_url_list, 2, q, error_page_url_queue, crawl_counter)
    helper.log('done', 'flightclub')
