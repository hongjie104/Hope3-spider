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

conn = MongoClient('106.15.93.73', 27017)
# 连接NAS数据库，没有则自动创建
db = conn.Hope3
# 使用models集合，没有则自动创建
goods_type_collection = db.hope_pendinggoods

if __name__ == "__main__":
    # pending_goods_list = pending_goods_collection.find({ 'is_deleted': False }, { 'size_price_arr': 1 })
    # for pending_goods in pending_goods_list:
    #     size_price_list = pending_goods.get('size_price_arr')
    #     size_list = [size_price.get('size') for size_price in size_price_list]
    pass