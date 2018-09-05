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
from threading import Thread
from Queue import Queue


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
            pq = helper.get(self.url, myHeaders=self.headers)
            a_list = pq('div.mainsite_record_listing li > a')
            total = len(a_list)
            for i in range(0, total):
                self.q.put(a_list[i].get('href'))
        except:
            self.error_page_url_queue.append({'url': self.url, 'gender': self.gender})


class GoodsSpider(Thread):
    def __init__(self, url, gender, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.gender = gender
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
            name = None
            try:
                name = pq('span.product_title').text()
            except:
                return
            # 配色的编号
            number = pq('span#productSKU').text()
            # 颜色尺寸
            # 找出所有的尺寸
            size_all_list = json.loads(re.compile(r'var model =.*"\};').findall(pq.html())[0].replace('var model = ', '').replace('"};', '"}'))
            size_all_list = size_all_list.get('AVAILABLE_SIZES')
            size_all_list = [float(size.strip()) for size in size_all_list]
            size_price_json = json.loads(re.compile(r'var sizeObj =.*}];').findall(pq.html())[0].replace('var sizeObj = ', '').replace('}];', '}]'))
            size_price_json = [{'size': float(item.get('size').strip()), 'price': float(item.get('pr_sale').strip())} for item in size_price_json]
            # size_price_list = [{'size': float(a.get('size').strip()), 'price': float(a.get('pr_sale').strip())} for a in size_price_json]
            size_price_list = []
            for size in size_all_list:
                finded = False
                for size_price in size_price_json:
                    if size_price.get('size') == size:
                        size_price_list.append({
                            'size': size,
                            'price': size_price.get('price'),
                            'isInStock': True,
                        })
                        finded = True
                        break
                if not finded:
                    size_price_list.append({
                        'size': size,
                        'price': 0.0,
                        'isInStock': False,
                    })
            print(name, number, self.url, size_price_list)
            result = mongo.insert_pending_goods(name, number, self.url, size_price_list, ['%s.jpg' % number], self.gender, '', 'champssports', '5af1310e48555b1ba3387bcc', self.crawl_counter)
            if result:
                img_response = helper.get('https://images.champssports.com/is/image/EBFL2/%s?req=imageset,json' % number, returnText=True)
                img_response = re.compile(r'"IMAGE_SET":"\w+/[_\w]+;').findall(img_response)
                img_url = 'https://images.champssports.com/is/image/%s?hei=600&wid=600' % img_response[0].replace('"IMAGE_SET":"', '').replace(';', '')
                # 下载图片
                result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'champssports', '%s.jpg' % number))
                if result == 1:
                    # 上传到七牛
                    qiniuUploader.upload_2_qiniu('champssports', '%s.jpg' % number, './imgs/champssports/%s.jpg' % number)
        except:
            print('[ERROR] => ', self.url)
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


def start(crawl_counter):
    # 创建一个队列用来保存进程获取到的数据
    q = Queue()
    # 有错误的页面链接
    error_page_url_queue = Queue()
    total_page = 16
    base_url = 'https://www.champssports.com/Mens/Shoes/_-_/N-24Zrj?cm_PAGE=%d&Rpp=180&crumbs=991&Nao=%d'
    fetch_page([base_url % ((page - 1) * 180, (page - 1) * 180) for page in xrange(1, total_page + 1)], 1, q, error_page_url_queue, crawl_counter)

    total_page = 7
    base_url = 'https://www.champssports.com/Womens/Shoes/_-_/N-25Zrj?cm_PAGE=%d&Rpp=180&crumbs=991&Nap=%d'
    fetch_page([base_url % ((page - 1) * 180, (page - 1) * 180) for page in xrange(1, total_page + 1)], 2, q, error_page_url_queue, crawl_counter)

    # 处理出错的链接
    while not error_page_url_queue.empty():
        error_page_url_list = []
        while not error_page_url_queue.empty():
            error_page_url_list.append(error_page_url_queue.get())

        error_page_men_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 1]
        fetch_page(error_page_men_url_list, 1, q, error_page_url_queue, crawl_counter)
        error_page_women_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 2]
        fetch_page(error_page_women_url_list, 2, q, error_page_url_queue, crawl_counter)

    print('done')
