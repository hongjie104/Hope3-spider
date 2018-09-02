#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os


def fetch_detail(url):
    pq = helper.get(url, {}, {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36 OPR/54.0.2952.71',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.finishline.com',
        'referer': 'https://www.finishline.com/store/men/shoes/_/N-1737dkj?mnid=men_shoes&Ns=sku.bestSeller%7C1&sort=sort%3Abest%20sellers%0A%20',
        'x-requested-with': 'XMLHttpRequest',
        'accept': '*/*',
        'content-length': '0'
    })
    if pq:
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
        result = mongo.insert_pending_goods(name, number, url, size_price_arr, ['%s.jpg' % number], 'finishline')
        # 下载图片
        img_list = pq('div.pdp-image')            
        img_url = 'https:' + (img_list[2].get('data-large') if len(img_list) > 2 else img_list[-1].get('data-large'))

        # result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'finishline', '%s.jpg' % number))
        # if result == 1:
        #     # 上传到七牛
        #     qiniuUploader.upload_2_qiniu('finishline', '%s.jpg' % number, './imgs/finishline/%s.jpg' % number)
        print(name, number, url, size_price_arr, img_url)
    else:
        print('error!!!')
    

def fetch_page(url, page = 1):
    pattern = re.compile(r'<div\sclass="product\-card"\sid="\w+"\sdata\-prodid="\w+"\sdata\-productid="\w+"\sdata\-baseurl="[\/\w\-\?]*">\s+<a\sid="\w+"\shref="[\/\w\-\?&=]*"')
    while True:
        count = (page - 1) * 40
        print('cur page => %d' % page)
        html = helper.post('%s&No=%d' % (url, count), {
            'mnid': 'men_shoes',
            'No': count,
            'Ns': 'sku.bestSeller | 1',
            'isAjax': 'true'
        }, {
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
        if len(str_arr) < 1:
            break
        index = 0
        for s in str_arr:
            print('cur page = %d, index = %d' % (page, index))
            goods_url = 'https://www.finishline.com%s' % s.split(' href="')[1].replace('"', '')
            fetch_detail(goods_url)
            index += 1
            break
        page += 1
        break


def start():
    # fetch_page('https://www.footaction.com/Mens/Shoes/_-_/N-24Zrj')
    fetch_page('https://www.finishline.com/store/men/shoes/_/N-1737dkj?mnid=men_shoes&Ns=sku.daysAvailable%7C0&isAjax=true')