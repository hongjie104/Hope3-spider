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
import flightclub

# WEB_DOMAIN = ['eastbay', 'footlocker', 'jimmyjazz', 'sneakersnstuff', 'footaction']
WEB_DOMAIN = ['finishline', 'champssports', 'stadiumgoods', 'flightclub', 'eastbay']

if __name__ == '__main__':
    for dir_name in WEB_DOMAIN:
        helper.mkDir(os.path.join('.', 'imgs', dir_name))
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help=','.join(WEB_DOMAIN))
    options = parser.parse_args()

    target = options.target
    if target not in WEB_DOMAIN:
        print('legal target: [%s] ' % ', '.join(WEB_DOMAIN))
    else:
        if target == 'eastbay':
            eastbay.start()
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
            finishline.start()
        elif target == 'champssports':
            champssports.start()
        elif target == 'stadiumgoods':
            stadiumgoods.start()
        elif target == 'flightclub':
            flightclub.start()
