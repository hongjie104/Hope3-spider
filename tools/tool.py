#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
from bson import objectid
import re

conn = MongoClient('106.15.93.73', 27017)
# 连接NAS数据库，没有则自动创建
db = conn.Hope3
# 使用models集合，没有则自动创建
goods_type_collection = db.hope_goodstypes
goods_color_collection = db.hope_goodscolors


def write_csv(csv_name, dict_value):
    txt = 'name, number'
    for key in dict_value:
        number_list = dict_value.get(key)
        txt += '\n%s,%s' % (key, ','.join(number_list))
    f = open(csv_name, 'w')
    f.write(txt.encode('utf-8'))
    f.close()


def get_result(goods_type_list):
    pattern = re.compile(r'\w{5,7}[\s-]?\d{3}a?')
    goods_type_number_dict = {}
    goods_type_wrong_number_dict = {}
    for goods_type in goods_type_list:
        # 找到每个款型的配色
        goods_color_id_list = [objectid.ObjectId(_id) for _id in goods_type.get('goods_color_arr', [])]
        goods_color_list = goods_color_collection.find({
            '_id': {
                '$in': goods_color_id_list
            }
        }, {'number': 1})
        for goods_color in goods_color_list:
            # 取出每个配色的number
            number_list = goods_color.get('number', [])
            # 378037 623
            for number in number_list:
                match = pattern.match(number)
                if match and match.group() == number:
                    if number.endswith('a'):
                        number = number[:-1]
                    if ' ' in number:
                        number = number.split(' ')[0]
                    elif '-' in number:
                        number = number.split('-')[0]
                    else:
                        number = number[:-3]
                    tmp_number_list = goods_type_number_dict.get(goods_type.get('name'), None)
                    if tmp_number_list:
                        tmp_number_list.append(number)
                    else:
                        goods_type_number_dict[goods_type.get('name')] = [number]
                else:
                    # 不规则的number
                    tmp_number_list = goods_type_wrong_number_dict.get(goods_type.get('name'), None)
                    if tmp_number_list:
                        tmp_number_list.append(number)
                    else:
                        goods_type_wrong_number_dict[goods_type.get('name')] = [number]
    # 去重
    for key in goods_type_number_dict:
        goods_type_number_dict[key] = list(set(goods_type_number_dict.get(key)))
    return goods_type_number_dict, goods_type_wrong_number_dict


def main():
    # 耐克的鞋子
    goods_type_list = goods_type_collection.find({
        'brand': objectid.ObjectId('5aba668eee851c35fa151186'),
        'is_deleted': False,
    }, {'goods_color_arr': 1, 'name': 1, 'id': 1})
    goods_type_number_dict, goods_type_wrong_number_dict = get_result(goods_type_list)
    write_csv('nike.csv', goods_type_number_dict)
    write_csv('nike_wrong.csv', goods_type_wrong_number_dict)

    # AIR JORDAN
    goods_type_list = goods_type_collection.find({
        'brand': objectid.ObjectId('5aa4f40e30302f3bc95cea7c'),
        'is_deleted': False,
    }, {'goods_color_arr': 1, 'name': 1, 'id': 1})
    goods_type_number_dict, goods_type_wrong_number_dict = get_result(goods_type_list)
    write_csv('jordan.csv', goods_type_number_dict)
    write_csv('jordan_wrong.csv', goods_type_wrong_number_dict)


if __name__ == '__main__':
    main()
    print('done')
