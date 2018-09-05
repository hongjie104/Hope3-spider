#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os
import time
from threading import Thread
from Queue import Queue


class PageSpider(Thread):
    def __init__(self, url, count, q, error_page_url_queue, post_body, gender):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.count = count
        self.q = q
        self.error_page_url_queue = error_page_url_queue
        self.post_body = post_body
        self.post_body['No'] = str(count)
        self.gender = gender
        self.headers = {
            'origin': 'https://www.finishline.com',
            'referer': 'https://www.finishline.com/store/men/shoes/_/N-1737dkj?mnid=men_shoes&Ns=sku.bestSeller%7C1&sort=sort%3Abest%20sellers%0A%20',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36 OPR/52.0.2871.40',
            'x-requested-with': 'XMLHttpRequest',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-length': '0'
        }

    def run(self):
        pattern = re.compile(r'<div\sclass="product\-card"\sid="\w+"\sdata\-prodid="\w+"\sdata\-productid="\w+"\sdata\-baseurl="[\/\w\-\?]*">\s+<a\sid="\w+"\shref="[\/\w\-\?&=]*"')
        try:
            html = helper.post(self.url, self.post_body, {
                'origin': 'https://www.finishline.com',
                'referer': 'https://www.finishline.com/store/men/shoes/_/N-1737dkj?mnid=men_shoes&Ns=sku.bestSeller%7C1&sort=sort%3Abest%20sellers%0A%20',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36 OPR/52.0.2871.40',
                'x-requested-with': 'XMLHttpRequest',
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'zh-CN,zh;q=0.9',
                'content-length': '0'
            }, returnText=True)
            str_arr = pattern.findall(html)
            for s in str_arr:
                self.q.put('https://www.finishline.com%s' % s.split(' href="')[1].replace('"', ''))
        except:
            self.error_page_url_queue.append({'url': self.url, 'count': self.count, 'post_body': self.post_body, 'gender': self.gender})


class GoodsSpider(Thread):
    def __init__(self, url, gender, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.gender = gender
        self.q = q
        self.crawl_counter = crawl_counter
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36 OPR/54.0.2952.71',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://www.finishline.com',
            'referer': 'https://www.finishline.com/store/men/shoes/_/N-1737dkj?mnid=men_shoes&Ns=sku.bestSeller%7C1&sort=sort%3Abest%20sellers%0A%20',
            'x-requested-with': 'XMLHttpRequest',
            'accept': '*/*',
            'content-length': '0'
        }

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
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, '', 'finishline', '5ac8594e48555b1ba31896ba', self.crawl_counter)
            # 下载图片
            img_list = pq('div.pdp-image')
            img_url = 'https:' + (img_list[2].get('data-large') if len(img_list) > 2 else img_list[-1].get('data-large'))
            result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'finishline', '%s.jpg' % number))
            if result == 1:
                # 上传到七牛
                qiniuUploader.upload_2_qiniu('finishline', '%s.jpg' % number, './imgs/finishline/%s.jpg' % number)
        except:
            print('[ERROR] => ', self.url)
            self.q.put(self.url)


def fetch_page(url_list, gender, q, error_page_url_queue, post_body, crawl_counter):
    page_thread_list = []
    # 构造所有url
    for url in url_list:
        # 创建并启动线程
        time.sleep(1.2)
        page_spider = PageSpider(url.get('url'), url.get('count'), q, error_page_url_queue, post_body, gender)
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
    total_page = 35
    base_url = 'https://www.finishline.com/store/men/shoes/_/N-1737dkj?mnid=men_shoes&Ns=sku.daysAvailable%7C0&isAjax=true&No='
    fetch_page([{'base_url': base_url + str((page - 1) * 40), 'count': (page - 1) * 40} for page in xrange(1, total_page + 1)], 1, q, error_page_url_queue, {
        'mnid': 'men_shoes',
        'Ns': 'sku.bestSeller | 1',
        'isAjax': 'true'
    }, crawl_counter)

    total_page = 23
    base_url = 'https://www.finishline.com/store/women/shoes/_/N-1hednxh?mnid=women_shoes&isAjax=true&No='
    fetch_page([{'base_url': base_url + str((page - 1) * 40), 'count': (page - 1) * 40} for page in xrange(1, total_page + 1)], 2, q, error_page_url_queue, {
        'mnid': 'women_shoes',
        'isAjax': 'true',
    }, crawl_counter)

    # 处理出错的链接
    while not error_page_url_queue.empty():
        error_page_url_list = []
        while not error_page_url_queue.empty():
            error_page_url_list.append(error_page_url_queue.get())

        error_page_men_url_list = [{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_url_list if url_data.get('gender') == 1]
        fetch_page([{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_men_url_list], 1, q, error_page_url_queue, {
            'mnid': 'men_shoes',
            'Ns': 'sku.bestSeller | 1',
            'isAjax': 'true'
        }, crawl_counter)
        error_page_women_url_list = [{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_url_list if url_data.get('gender') == 2]
        fetch_page([{'url': url_data.get('url'), 'count': url_data.get('count')} for url_data in error_page_women_url_list], 2, q, error_page_url_queue, {
            'mnid': 'women_shoes',
            'isAjax': 'true',
        }, crawl_counter)
    print('done')
