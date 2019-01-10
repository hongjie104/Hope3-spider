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
import time
import qiniuUploader
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue


platform = 'jimmyjazz'

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
        # 获取商品详情url
        try:
            pq = helper.get(self.url)
            for a in pq('div.product_grid_image > a'):
                self.q.put('http://www.jimmyjazz.com%s' % a.get('href'))
        except:
            global platform
            helper.log('[ERROR] => ' + self.url, platform)
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
        time.sleep(2)
        global platform
        try:
            pq = helper.get(self.url)
            name = pq('h1.product_title').text()
            print('name = %s' % name)
            number = pq('span.pistylevalue').text().strip()
            print('number = %s' % number)
            color_value = pq('span.pithecolor').text().strip()
            print('color_value = %s' % color_value)
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

            img_downloaded = mongo.is_pending_goods_img_downloaded(self.url)
            if not img_downloaded:
                img_url = pq('img.product_image').attr('src')
                if not img_url.startswith('http'):
                    img_url = 'http://www.jimmyjazz.com' + img_url
                print('img_url = ', img_url)
                if helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number)) == 1:
                # 上传到七牛
                    qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
                img_downloaded = True
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, platform, '5b4b59b6bb8bdb5a84ddee09', self.crawl_counter, img_downloaded=img_downloaded)
        except Exception as e:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            helper.log(e, platform)
            if error_counter < 3:
                self.q.put(self.url)


def fetch_page(url, q, crawl_counter, gender, error_page_url_queue):
    total_page = -1
    page = 1
    page_thread_list = []
    while True:
        page_url = '%s?ppg=104&page=%d' % (url, page)
        # 创建并启动线程
        time.sleep(1.2)
        page_spider = PageSpider(page_url, q, error_page_url_queue, gender)
        page_spider.start()
        page_thread_list.append(page_spider)

        if total_page < 0:
            pq = helper.get(page_url)
            div = pq('div.pagination_info')[0]
            total_page = int(div.text.strip().split('of ')[1])
        page += 1
        if page > total_page:
            # 下一页超过最大页数，break
            break
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


def start(action):
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()
    if action == 'common':
        fetch_page('http://www.jimmyjazz.com/mens/footwear', q, crawl_counter, 1, error_page_url_queue)
        fetch_page('http://www.jimmyjazz.com/womens/footwear', q, crawl_counter, 2, error_page_url_queue)
# fetch_detail('http://www.jimmyjazz.com/mens/footwear/jordan-1-mid-sneaker/554724-605?color=Red')
    helper.log('done', platform)
