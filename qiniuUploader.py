#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
from qiniu import Auth, put_file, etag, urlsafe_base64_encode
import mongo


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
