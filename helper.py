#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
import time
import platform
import datetime
import subprocess
import inspect
from pyquery import PyQuery
from requests.adapters import HTTPAdapter

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36'}

def now():
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

def today():
	return time.strftime('%Y-%m-%d', time.localtime(time.time()))

def mkDir(path):
	if not os.path.exists(path):
		os.makedirs(path)
	return path

def writeFile(content, path, mode='w'):
	try:
		f = open(path, mode)
		f.write(content)
		f.close()
		return True
	except Exception as e:
		print(e)
		return False


def readFile(path):
	if os.path.exists(path):
		f = open(path)
		txt = f.read()
		f.close()
		return txt


def log(content, platform):
	content = '[%s] %s\n' % (now(), content)
	if platform:
		mkDir(os.path.join('.', 'logs'))
		log_path = os.path.join('.', 'logs', '%s-%s.log' % (today(), platform))
		writeFile(content, log_path, 'a' if os.path.exists(log_path) else 'w')
	print('[%s] => %s' % (platform or 'None', content))

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


# def get_ak_bmsc_cookie(url):
# 	s = requests.Session()
# 	s.mount('http://', HTTPAdapter(max_retries=10))
# 	s.mount('https://', HTTPAdapter(max_retries=10))
# 	print('get url => ' + url)
# 	s.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
# 	return s.cookies.get_dict().get('ak_bmsc')


def get(url, cookies={}, myHeaders=None, sleep=0, returnText=False, withCookie=False, platform=None):
	s = requests.Session()
	s.mount('http://', HTTPAdapter(max_retries=10))
	s.mount('https://', HTTPAdapter(max_retries=10))
	if sleep > 0:
		time.sleep(sleep)
	log('get url => ' + url, platform)
	global headers
	response = None
	try:
		response = s.get(url, headers=myHeaders or headers, cookies=cookies, timeout=30)
	except Exception as err:
		# log('get url error!!! repeat again!!!', platform)
		log(err, platform)
		# return get(url, cookies, myHeaders, sleep or 3, returnText)
		return None
	if response.status_code == 200:
		pq = None
		try:
			pq = PyQuery(response.text)
		except:
			pq = None
		if withCookie:
			return response.text if returnText else PyQuery(response.text), s.cookies.get_dict()
		return response.text if returnText else pq
	else:
		log('response.status_code: %d' % response.status_code, platform)
		return None


def post(url, data={'imgContinue': 'Continue to image ... '}, myHeaders=None, cookies={}, sleep=0, returnText=False, platform=None, json=None, timeout=30):
	'''post'''
	s = requests.Session()
	s.mount('http://', HTTPAdapter(max_retries=10))
	s.mount('https://', HTTPAdapter(max_retries=10))
	if sleep > 0:
		time.sleep(sleep)
	log('post url => ' + url, platform)
	global headers
	response = None
	try:
		if data:
			response = s.post(url, headers=myHeaders or headers, cookies=cookies, data=data, timeout=timeout)
		else:
			response = s.post(url, headers=myHeaders or headers, cookies=cookies, json=json, timeout=timeout)
		# response = s.post('http://httpbin.org/post', headers=myHeaders or headers, cookies=cookies, data=data)
	except Exception as e:
		print(e)
		response = None
	if response:
		# log('post status => ', response.status_code)
		if response.status_code == 200:
			return response.text if returnText else PyQuery(response.text)
	log('post url not OK => ' + url, platform)
	return None

def lookUp(obj):
	print(inspect.getmembers(obj, inspect.ismethod))

def getMonth(english):
	'''从英文转成阿拉伯数字'''
	if english == 'Jan':
		return 1
	if english == 'Feb':
		return 2
	if english == 'Mar':
		return 3
	if english == 'Apr':
		return 4
	if english == 'May':
		return 5
	if english == 'Jun':
		return 6
	if english == 'Jul':
		return 7
	if english == 'Aug':
		return 8
	if english == 'Sep':
		return 9
	if english == 'Oct':
		return 10
	if english == 'Nov':
		return 11
	if english == 'Dec':
		return 12
	return english


def runCmd(cmd, logfile='./aria2c.log', timeout=1200):
	process = None
	if logfile:
		process = subprocess.Popen('%s >>%s 2>&1' % (cmd, logfile), shell=True)
	else:
		process = subprocess.Popen(cmd, shell=True)
	# print(u'run cmd => %s' % cmd)
	process.wait()
	start = datetime.datetime.now()
	while process.poll() is None:
		time.sleep(0.1)
		now = datetime.datetime.now()
		if (now - start).seconds > timeout:
			try:
				process.terminate()
			except Exception as e:
				return None
			return None
	out = process.communicate()[0]
	if process.stdin:
		process.stdin.close()
	if process.stdout:
		process.stdout.close()
	if process.stderr:
		process.stderr.close()
	try:
		process.kill()
	except OSError:
		pass
	return out

def delRepeat(list):
	for x in list:
		while list.count(x)>1:
			del list[list.index(x)]
	return list
