#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
商品数据爬虫
'''

__author__ = "32968210@qq.com"

import argparse
import eastbay
import footlocker
import jimmyjazz

WEB_DOMAIN = ['eastbay', 'footlocker', 'jimmyjazz']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help = "web domain")
    options = parser.parse_args()

    target = options.target
    if target not in WEB_DOMAIN:
        print('legal target: [%s] ' % ', '.join(WEB_DOMAIN))
    else:
        if target == 'eastbay':
            eastbay.start()
        elif target == 'footlocker':
            footlocker.start()
        elif target == 'jimmyjazz':
            jimmyjazz.start()
