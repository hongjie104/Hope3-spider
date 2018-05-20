#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
import datetime

conn = MongoClient('47.100.164.90', 27017)
# 连接NAS数据库，没有则自动创建
db = conn.Hope3
# 使用models集合，没有则自动创建
identityCounter = db.identitycounters
pendingGoods = db.pendinggoods
# goods = db.goods
# skus = db.skus
# goodsTypeColor = db.goodstypecolors


# def get_pending_goods(query):
#     global pendingGoods
#     result = pendingGoods.find(query, {})
#     return result


# def get_one_sku(query, fields={}):
#     global skus
#     result = skus.find_one(query, fields)
#     return result


# def get_one_goods_type_color(query, fields={}):
#     global goodsTypeColor
#     result = goodsTypeColor.find_one(query, fields)
#     return result


# def update_goods_type_color(query, update):
#     global goodsTypeColor
#     goodsTypeColor.update(query, update)


def get_pending_goods_id():
    global identityCounter
    result = identityCounter.find_one({'model': 'PendingGoods'})
    if result:
        count = result.get('count', 1)
        identityCounter.update({'model': 'PendingGoods'}, {'$inc': {'count': 1}})
    else:
        count = 0
        identityCounter.insert({'model': 'PendingGoods', 'count': 1, '__v': 0})
    return count + 1


def insert_pending_goods(name, number, url, size_price_arr, imgs, platform):
    global pendingGoods
    result = pendingGoods.find_one({'url': url})
    if result:
        pendingGoods.update({'url': url}, {'$set': {
            'platform': platform,
            'name': name,
            'number': number,
            'size_price_arr': size_price_arr
        }})
        return False
    id = get_pending_goods_id()
    pendingGoods.insert({
        'id': id,
        'platform': platform,
        'name': name,
        'colorName': '',
        'colorValue': '',
        'number': number,
        'url': url,
        'size_price_arr': size_price_arr,
        'imgs': imgs,
        'check_date': datetime.datetime(1970, 1, 1),
        'is_checked': False,
        '__v': 0        
    })
    return True
