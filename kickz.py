#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os
import time
import json
from pyquery import PyQuery
from threading import Thread
from Queue import Queue


error_detail_url = {}
platform = 'kickz'
cookie = {
    'isSdEnabled': 'false',
    'JSESSIONID': '3523CF3460F24ACD45F82C8F1B793380.tomcat-8000',
    'CS_CONTEXT': 'us',
    'BT_pdc': 'eyJldGNjX2N1c3QiOjAsImVjX29yZGVyIjowLCJldGNjX25ld3NsZXR0ZXIiOjB9',
    '_ga': 'GA1.2.1618271438.1539865433',
    '_gid': 'GA1.2.1726487726.1540307036',
    '_gcl_au': '1.1.1382208459.1539865434',
    '_et_coid': '3d91a13471f6ccfb82bf8ae32e206e6f',
    'scarab.visitor': '%22752948ECF9340ED2%22',
    '_hjIncludedInSample': '1',
    'scarab.mayAdd': '%5B%7B%22i%22%3A%22141510003%22%7D%5D',
    'scarab.profile': '%22145946001%7C1539866607%22',
    '_gaexp': 'GAX1.2.UNtUbfJwQ9qOrw9pLHrqiw.17915.0',
    'USER_LAST_VISITED_PRODUCTS': '145946001%3A1%7C138841004%3A1%7C141510003%3A1',
    'BT_ctst': '',
    'BT_sdc': 'eyJldF9jb2lkIjoiM2Q5MWExMzQ3MWY2Y2NmYjgyYmY4YWUzMmUyMDZlNmYiLCJyZnIiOiIiLCJ0aW1lIjoxLCJwaSI6NSwicmV0dXJuaW5nIjoxLCJldGNjX2NtcCI6Ik5BIn0%3D'
}


class PageSpider(Thread):
    def __init__(self, url, q, error_page_url_queue, gender):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.q = q
        self.error_page_url_queue = error_page_url_queue
        self.gender = gender
        self.headers = {
            'User-Agent': 'Mozilla/5.0'
        }


    def run(self):
        # 获取商品详情url
        try:
            pq = helper.get(self.url, cookies=cookie, myHeaders=self.headers)
            for a in pq('a.no-h-over'):
                self.q.put(a.get('link'))
                # helper.log('[DEBUG] => ' + a.get('link'), platform)
        except:
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
        try:
            pq = helper.get(self.url, cookie)
            name = pq('h1#prodNameId').text()
            number = pq('span#supplierArtNumSpan').text()
            color_value = pq('span#variantColorId').text()
            size_price_arr = []
            for a in pq('div#2SizeContainer > div > a'):
                arr = [item.strip() for item in a.get('onclick').replace('ProductDetails.changeSizeAffectedLinks(', '').replace(');', '').split('\n')]
                # print(arr)
                # '8+', => 8+, => 8+
                arr[6] = arr[6].replace('\'', '').replace(',', '').replace('Y', '')
                size_price_arr.append({
                    'size': float(arr[6]) if '+' not in arr[6] else float(arr[6].replace('+', '')) + 0.5,
                    # '115,76 USD', => '115.76 USD'. => '115.76 USD'. => '115.76 => 115.76
                    'price': float(arr[2].replace(',', '.').replace(' USD\'.', '').replace('\'', '')),
                    'isInStock': True
                })
            # print(size_price_arr)
            img_downloaded = mongo.is_pending_goods_img_downloaded(self.url)
            if not img_downloaded:
                img_url = pq('img.productDetailPic').attr('src')
                result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
                if result == 1:
                    # 上传到七牛
                    qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
                    img_downloaded = True
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, platform, '5bc87d6dc7e854cab4875368', self.crawl_counter, img_downloaded=img_downloaded)
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
            for i in xrange(5 if queue_size > 5 else queue_size):
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
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()
    # 先获取cookie
    _, tmpCookie = helper.get('https://www.kickz.com/us/men/shoes/c', myHeaders={
        'User-Agent': 'Mozilla/5.0'
    }, withCookie=True)
    global cookie
    cookie['JSESSIONID'] = tmpCookie.get('JSESSIONID', '')
    total_page = 20
    fetch_page(['https://www.kickz.com/us/men/shoes/c?selectedPage=%d' % page
                for page in xrange(1, total_page + 1)], 1, q, error_page_url_queue, crawl_counter)

    total_page = 17
    fetch_page(['https://www.kickz.com/us/kids,women/shoes/shoe-sizes/38+,36-2:3,40+,37+,41+,39-1:3,35+,36,36+,39+,39,37,38,41-1:3,42,41,40,39:40,38-2:3,40-2:3,35:36,37:38,37-1:3,41:42/c?selectedPage=%d' % page
                for page in xrange(1, total_page + 1)], 2, q, error_page_url_queue, crawl_counter)

    # # 处理出错的链接
    # while not error_page_url_queue.empty():
    #     error_page_url_list = []
    #     while not error_page_url_queue.empty():
    #         error_page_url_list.append(error_page_url_queue.get())

    #     error_page_men_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 1]
    #     fetch_page(error_page_men_url_list, 1, q, error_page_url_queue, crawl_counter)
    #     error_page_women_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 2]
    #     fetch_page(error_page_women_url_list, 2, q, error_page_url_queue, crawl_counter)
    helper.log('done', platform)
