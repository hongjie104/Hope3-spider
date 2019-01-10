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
import stockx
import goat
import nike
import kickz
import sys


# WEB_DOMAIN = ['footlocker', 'jimmyjazz', 'sneakersnstuff', 'footaction']
WEB_DOMAIN = ['finishline', 'champssports', 'stadiumgoods',
              'flightclub', 'eastbay', 'stockx', 'goat', 'kickz', 'footlocker',
              'nike', 'jimmyjazz']

if __name__ == '__main__':
    for dir_name in WEB_DOMAIN:
        helper.mkDir(os.path.join('.', 'imgs', dir_name))
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help=','.join(WEB_DOMAIN))
    parser.add_argument("action", help='common or hot')
    options = parser.parse_args()

    target = options.target
    action = options.action
    if target not in WEB_DOMAIN:
        print('legal target: [%s] ' % ', '.join(WEB_DOMAIN))
    else:
        if target == 'eastbay':
            eastbay.start(action)
        elif target == 'footlocker':
            footlocker.start(action)
        elif target == 'jimmyjazz':
            jimmyjazz.start(action)
            pass
        elif target == 'sneakersnstuff':
            # sneakersnstuff.start(action)
            pass
        elif target == 'footaction':
            # footaction.start(action)
            pass
        elif target == 'finishline':
            finishline.start(action)
        elif target == 'champssports':
            champssports.start(action)
        elif target == 'stadiumgoods':
            stadiumgoods.start(action)
        elif target == 'flightclub':
            flightclub.start(action)
        elif target == 'stockx':
            stockx.start(action)
        elif target == 'goat':
            goat.start(action)
        elif target == 'kickz':
            kickz.start(action)
        elif target == 'nike':
            nike.start(action)
