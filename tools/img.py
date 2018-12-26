#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
from bson import objectid
import datetime
import requests
import re
from qiniu import Auth, put_file, etag, urlsafe_base64_encode
import os
import time
from pyquery import PyQuery
from requests.adapters import HTTPAdapter
import json

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36'}

conn = MongoClient('106.15.93.73', 27017)
# 连接NAS数据库，没有则自动创建
db = conn.Hope3
# 使用models集合，没有则自动创建
pending_goods_collection = db.hope_pendinggoods


def upload_2_qiniu(img_space, img_name, img_local_path):
	# 需要填写你的 Access Key 和 Secret Key
	access_key = 'u8204eU35XvUiDcFE-NcctjgVtdUkeEeaR6UObWi'
	secret_key = 'lFdpeVd89l5u5e7GKKapdqtI-yPAeHxB9NEDJPv-'
	# 构建鉴权对象
	q = Auth(access_key, secret_key)
	# 要上传的空间
	bucket_name = 'hope3'
	# 上传到七牛后保存的文件名
	key = '%s/%s' % (img_space, img_name)
	# 生成上传 Token，可以指定过期时间等
	token = q.upload_token(bucket_name, key, 3600)
	# 要上传文件的本地路径
	localfile = img_local_path
	ret, info = put_file(token, key, localfile)
	# print(info)
	assert ret['key'] == key
	assert ret['hash'] == etag(localfile)


def now():
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))


def mkDir(path):
	if not os.path.exists(path):
		os.makedirs(path)
	return path


def get(url, cookies={}, myHeaders=None, sleep=0, returnText=False):
	s = requests.Session()
	s.mount('http://', HTTPAdapter(max_retries=10))
	s.mount('https://', HTTPAdapter(max_retries=10))
	if sleep > 0:
		time.sleep(sleep)
	global headers
	response = None
	try:
		response = s.get(url, headers=myHeaders or headers, cookies=cookies, timeout=30)
	except Exception as err:
		return None
	if response.status_code == 200:
		pq = None
		try:
			pq = PyQuery(response.text)
		except:
			pq = None
		return response.text if returnText else pq
	else:
		log('response.status_code: %d' % response.status_code, platform)
		return None


# 开始下载图片
def downloadImg(url, imgPath):
	if url != None:
		if os.path.exists(imgPath):
			print('%s is exists, jump it!' % imgPath)
			return 2
		else:
			parent = os.sep.join(imgPath.split(os.sep)[: -1])
			mkDir(parent)
			print('[%s] download image: %s' % (now(), url))
			try:
				global headers
				r = requests.get(url, stream=True, headers=headers)
			except Exception as e:
				print(e)
				return -2
			with open(imgPath, 'wb') as f:
				for chunk in r.iter_content(chunk_size = 1024):
					if chunk:
						f.write(chunk)
						f.flush()
		return 1
	return -1


if __name__ == '__main__':
    # 5b04ff19b0394165bc8de23d  是eastbay
    pending_goods_list = pending_goods_collection.find({'platform_id': objectid.ObjectId('5b04ff19b0394165bc8de23d')}, {'url': 1, 'number': 1})
    i = 1
    start_i = 5455
    for pending_goods in pending_goods_list:
        print(i)
        if i < start_i:
            i += 1
            continue
        i += 1
        number = pending_goods.get('number')
        img_url = 'http://hope3.pksen.com/eastbay/%s.jpg' % number
        response = requests.get(img_url)
        if response and response.status_code == 200:
            print('%s is ok' % img_url)
            pending_goods_collection.update({'_id': pending_goods.get('_id')}, {'$set': {
                'img_downloaded': True,
            }})
            continue
        print('number = ', number)
        # https://images.eastbay.com/is/image/EBFL2/435038MM?req=set,json
        img_json_str = get('https://images.eastbay.com/is/image/EBFL2/%sMM?req=set,json' % number, returnText=True)
        img_json = None
        img_url = None
        try:
            # print('1111', img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
            img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
            # print('2222')
            img_item_arr = img_json.get('set').get('item')
            # print('333')
            # print(img_item_arr)
            # print(img_item_arr)
            for img_item in img_item_arr:
                # print(img_item)
                if img_item.get('type') == 'img_set':
                    img_url = img_item.get('set').get('item')[0].get('s').get('n')
                    break
        except:
            img_json_str = get('https://images.eastbay.com/is/image/EBFL2/%s?req=set,json' % number, returnText=True)
            try:
                img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
                img_item_arr = img_json.get('set').get('item')
                if isinstance(img_item_arr, list):
                    img_url = img_item_arr[0].get('s').get('n')
                elif isinstance(img_item_arr, dict):
                    img_url = img_item_arr.get('s').get('n')
            except:
                img_url = None
        # print(name, number ,color_value, size_price_arr)
        # print(img_url)
        if img_url:
            # EBFL2/435038_a1
            img_url = 'https://images.eastbay.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
            print('img_url = ', img_url)
            # print(img_url)
            print('start to downloading')
            result = downloadImg(img_url, os.path.join('.', 'imgs', 'eastbay', '%s.jpg' % number))
            print('downloaded')
            if result == 1:
                # 上传到七牛
                upload_2_qiniu('eastbay', '%s.jpg' % number, './imgs/eastbay/%s.jpg' % number)
                print('uploaded')
                pending_goods_collection.update({'_id': pending_goods.get('_id')}, {'$set': {
                    'img_downloaded': True,
                }})
        else:
            print('no img', number)