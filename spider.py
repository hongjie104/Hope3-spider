#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
商品数据爬虫
'''

__author__ = "32968210@qq.com"

import helper
import os
import mongo
import argparse
import eastbay
import footlocker
import jimmyjazz
import sneakersnstuff
import footaction
import finishline
import champssports
import stadiumgoods

# WEB_DOMAIN = ['eastbay', 'footlocker', 'jimmyjazz', 'sneakersnstuff', 'footaction']
WEB_DOMAIN = ['finishline', 'champssports', 'stadiumgoods']

if __name__ == '__main__':
    for dir_name in WEB_DOMAIN:
        helper.mkDir(os.path.join('.', 'imgs', dir_name))
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help = "web domain")
    options = parser.parse_args()

    target = options.target
    if target not in WEB_DOMAIN:
        print('legal target: [%s] ' % ', '.join(WEB_DOMAIN))
    else:
        crawl_counter = mongo.get_crawl_counter()
        if target == 'eastbay':
            # eastbay.start(crawl_counter)
            pass
        elif target == 'footlocker':
            # footlocker.start(crawl_counter)
            pass
        elif target == 'jimmyjazz':
            # jimmyjazz.start(crawl_counter)
            pass
        elif target == 'sneakersnstuff':
            # sneakersnstuff.start(crawl_counter)
            pass
        elif target == 'footaction':
            # footaction.start(crawl_counter)
            pass
        elif target == 'finishline':
            finishline.start(crawl_counter)
        elif target == 'champssports':
            champssports.start(crawl_counter)
        elif target == 'stadiumgoods':
            stadiumgoods.start(crawl_counter)
