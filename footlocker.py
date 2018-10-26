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
try:
    from queue import Queue
except ImportError:
    from Queue import Queue


error_detail_url = {}

platform = 'footlocker'


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
            html = helper.get(self.url, myHeaders=self.headers, returnText=True)
            json_data = json.loads(html)
            print(json_data.get('products', [])[0])
            # for span in pq('span.product_title'):
            #     a = PyQuery(span).parents('a')
            #     self.q.put(a.attr('href'))
        except:
            helper.log('[ERROR] => ' + self.url, platform)
            self.error_page_url_queue.put({'url': self.url, 'gender': self.gender})


# class GoodsSpider(Thread):
#     def __init__(self, url, gender, q, crawl_counter):
#         # 重写写父类的__init__方法
#         super(GoodsSpider, self).__init__()
#         self.url = url
#         self.gender = gender
#         self.q = q
#         self.crawl_counter = crawl_counter
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0'
#         }

#     def run(self):
#         '''
#         解析网站源码
#         '''
#         try:
#             pq = helper.get(self.url, myHeaders=self.headers)
#             name = pq('h1.product_title').text()
#             if not name:
#                 return
#             number = pq('span#productSKU').text()
#             if not number:
#                 return
#             color_value = pq('span.attType_color').text()

#             json_str = re.compile(r'var\smodel\s=\s.*"\};').findall(pq.html())[0]
#             size_arr = json.loads(json_str.replace('var model = ', '').replace('"};', '"}')).get('AVAILABLE_SIZES')
#             try:
#                 size_arr = [float(size) for size in size_arr]
#             except:
#                 size_arr = []
#                 return
#             if len(size_arr) < 1:
#                 return

#             json_str = re.compile(r'var\ssizeObj\s=\s.*"\}\];').findall(pq.html())[0]
#             available_size_arr = json_str.replace('var sizeObj = ', '').replace('"}];', '"}]')
#             available_size_arr = json.loads(available_size_arr)
#             size_price_arr = [{'size': size, 'isInStock': False, 'price': 0.00} for size in size_arr]
#             for available_size in available_size_arr:
#                 tmp_size = float(available_size.get('size'))
#                 for size_price in size_price_arr:
#                     if tmp_size == size_price.get('size'):
#                         size_price['isInStock'] = True
#                         size_price['price'] = float(available_size.get('pr_sale'))
#                         break

#             mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, platform, '5bcf1b5cc7e854cab48a7662', self.crawl_counter)
#             img_json_str = helper.get('https://images.eastbay.com/is/image/EBFL2/%sMM?req=set,json' % number, returnText=True)
#             img_json = None
#             img_url = None
#             try:
#                 img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
#                 img_item_arr = img_json.get('set').get('item')
#                 for img_item in img_item_arr:
#                     if img_item.get('type') == 'img_set':
#                         img_url = img_item.get('set').get('item')[0].get('s').get('n')
#                         break
#             except:
#                 img_json_str = helper.get('https://images.eastbay.com/is/image/EBFL2/%s?req=set,json' % number, returnText=True)
#                 try:
#                     img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
#                     img_item_arr = img_json.get('set').get('item')
#                     if isinstance(img_item_arr, list):
#                         img_url = img_item_arr[0].get('s').get('n')
#                     elif isinstance(img_item_arr, dict):
#                         img_url = img_item_arr.get('s').get('n')
#                 except:
#                     img_url = None
#             # print(name, number ,color_value, size_price_arr)
#             # print(img_url)
#             if img_url:
#                 img_url = 'https://images.eastbay.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
#                 # print(img_url)
#                 result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
#                 if result == 1:
#                     # 上传到七牛
#                     qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))
#         except:
#             global error_detail_url
#             error_counter = error_detail_url.get(self.url, 1)
#             error_detail_url[self.url] = error_counter + 1
#             helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
#             if error_counter < 3:
#                 self.q.put(self.url)


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

    # goods_thread_list = []
    # while True:
    #     queue_size = q.qsize()
    #     if queue_size > 0:
    #         # 每次启动5个抓取商品的线程
    #         for i in range(5 if queue_size > 5 else queue_size):
    #             time.sleep(2)
    #             goods_spider = GoodsSpider(q.get(), gender, q, crawl_counter)
    #             goods_spider.start()
    #             goods_thread_list.append(goods_spider)
    #         for t in goods_thread_list:
    #             t.join()
    #         goods_thread_list = []
    #     else:
    #         break


def start():
    crawl_counter = mongo.get_crawl_counter(platform)
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()

    # total_page = 86
    total_page = 1
    url_list = ['https://www.footlocker.com/api/products/search?currentPage=' + str(page - 1) + '&pageSize=60&query=Men%27s%20Shoes%20%20%20%20&sort=brand-asc&timestamp=2' for page in range(1, total_page + 1)]
    fetch_page(url_list, 1, q, error_page_url_queue, crawl_counter)
