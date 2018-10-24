#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import json
import re
import os
import time
import random
from threading import Thread
from Queue import Queue
from pyquery import PyQuery


error_detail_url = {}


class PageSpider(Thread):
    def __init__(self, url, q, error_page_url_queue):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.q = q
        self.error_page_url_queue = error_page_url_queue
        self.headers = {'User-Agent': 'Mozilla/5.0'}


    def run(self):
        try:
            pq = helper.get(self.url, myHeaders=self.headers)
            a_list = pq('a.product-image')
            for a in a_list:
                self.q.put(a.get('href'))
        except:
            self.error_page_url_queue.put(self.url)


class GoodsSpider(Thread):
    def __init__(self, url, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.q = q
        self.crawl_counter = crawl_counter
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def run(self):
        '''
        解析网站源码
        '''
        try:
            pq = helper.get(self.url, myHeaders=self.headers)
            # 款型名称
            name = pq('div.product-brand').text().strip() + ' ' + pq('h1.product-name').text().strip()
            # 颜色尺寸
            # 找出所有的尺寸
            size_span_list = pq('div.product-sizes__options span.product-sizes__detail')
            size_price_list = []
            for size_span in size_span_list:
                size = PyQuery(size_span).find('span.product-sizes__size').text().strip()
                if 'K' in size or 'k' in size or '-' in size or 'XS' in size:
                    continue
                size = re.sub(r'[WwYyCc\*]', '', size)
                # 还有非数字的size，醉了
                if size == 'S':
                    continue
                elif size == 'M':
                    continue
                elif size == 'L':
                    continue
                elif size == 'XL':
                    continue
                elif size == 'XXL':
                    continue
                elif size == 'XXXL':
                    continue
                elif size == '':
                    continue
                elif size == 'OS':
                    continue
                price = PyQuery(size_span).find('span.product-sizes__price').text().strip()
                if price.startswith('$'):
                    price = price.replace('$', '').replace(',', '')
                    size_price_list.append({
                        'size': float(size),
                        'price': float(price),
                        'isInStock': True
                    })
                else:
                    size_price_list.append({
                        'size': float(size),
                        'price': 0.0,
                        'isInStock': False
                    })
            if len(size_price_list) < 1:
                return
            # 配色的编号
            number = ''
            # 性别
            gender = 0
            # 颜色
            color_value = ''
            tr_list = pq('table#product-attribute-specs-table tr')
            for tr in tr_list:
                key = PyQuery(tr).find('th').text().strip()
                if key == 'Gender':
                    gender_txt = PyQuery(tr).find('td').text().strip()
                    if gender_txt == 'Mens':
                        gender = 1
                    elif gender_txt == 'Womens':
                        gender = 2
                elif key == 'Colorway':
                    color_value = PyQuery(tr).find('td').text().strip()
                elif key == 'Manufacturer Sku':
                    number = PyQuery(tr).find('td').text().strip()
            # print(name, number, self.url, size_price_list, gender, color_value)
            result = mongo.insert_pending_goods(name, number, self.url, size_price_list, ['%s.jpg' % number], gender, color_value, 'stadiumgoods', '5b8f484b299207efc1fb0904', self.crawl_counter)
            if result:
                img_url = pq('div.product-gallery-image > img')[0].get('src')
                # 下载图片
                result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'stadiumgoods', '%s.jpg' % number))
                if result == 1:
                    # 上传到七牛
                    qiniuUploader.upload_2_qiniu('stadiumgoods', '%s.jpg' % number, './imgs/stadiumgoods/%s.jpg' % number)
        except:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), 'stadiumgoods')
            if error_counter < 3:
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
            # 每次启动10个抓取商品的线程
            for i in xrange(10 if queue_size > 10 else queue_size):
                time.sleep(random.uniform(1.0, 3.6))
                goods_spider = GoodsSpider(q.get(), q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start():
    crawl_counter = mongo.get_crawl_counter('stadiumgoods')
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()
    total_page = 37
    url_arr = ['https://www.stadiumgoods.com/nike/page/%d/show/96' % page for page in range(1, total_page + 1)]
    fetch_page(url_arr, q, error_page_url_queue, crawl_counter)

    total_page = 17
    url_arr = ['https://www.stadiumgoods.com/air-jordan/page/%d/show/96' % page for page in range(1, total_page + 1)]
    fetch_page(url_arr, q, error_page_url_queue, crawl_counter)

    total_page = 14
    url_arr = ['https://www.stadiumgoods.com/adidas/page/%d/show/96' % page for page in range(1, total_page + 1)]
    fetch_page(url_arr, q, error_page_url_queue, crawl_counter)

    total_page = 10
    url_arr = ['https://www.stadiumgoods.com/footwear/page/%d/show/96' % page for page in range(1, total_page + 1)]
    fetch_page(url_arr, q, error_page_url_queue, crawl_counter)

    # 处理出错的链接
    while not error_page_url_queue.empty():
        error_page_url_list = []
        while not error_page_url_queue.empty():
            error_page_url_list.append(error_page_url_queue.get())
        # print('wrong page url num:', len(error_page_url_list))
        fetch_page(error_page_url_list, q, error_page_url_queue, crawl_counter)

    helper.log('done', 'stadiumgoods')
