#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
爬虫
'''

__author__ = "32968210@qq.com"

import mongo
import helper
from pyquery import PyQuery
import re
import json
import os
import qiniuUploader
import math

platform = 'footaction'

# cookies = {
#     'ak_bmsc': 'E8F58E0198AA3BF03FA774B2AD82144A7D38DA29F74A0000EF384B5B09A3C117~plfYfGa42ztFnSKbskuPKM/6C302118XB02QhZJpWZKCp9wkIdA626ymthoNeRJX232prQkJFXH/1MNlahM+v5kxII4EoX0vYOAYfEokEeyNtWtLH5YJkJ8idDLTAJw5jDxbItLZom337ZbOFcWaK1XdTRLX8PTk9zBeAaBAsk565bZz2Jdr0ocWYm7pfNg+jXfjBFBrBySacjicJoVXdpkRwSgzIbohBT+ex2DvjasxslwpNxb9IJP1wO2yPHQRPa',
# }

cookies = {
    'DCT_Exp_100': 'DCT',
    '_ga': 'GA1.2.741765830.1531043896',
    'rmStore': 'amid:35196',
    '_mibhv': 'anon-1531043897791-6758467275_6179',
    'mbdc': 'D6D2408A.1EE5.5D90.99C0.B9FA053E9EB9',
    'mbcc': '59A7E4F5-AC27-51D2-B8CB-EB9C84E746D0',
    '_abck': '6C4D60D014F4A2257925F9112AFF697E7D38DA29BE1800002EE0415B82543E26~0~t/03PuZPOdSMk0wzEk2vDwomaYgfkcem9+8339i+8qw=~-1~-1',
    # xyz_cr_100236_et_100==NaN&cr=100236&et=100;
    'AAMC_footlocker_0': 'REGION%7C11',
    'bm_sz': '051909339D5700C263EEBB812E0294F4~QAAQKdo4fZ5955xkAQAAEFRknX4iLY1QjFh91XsVb87Q+RCLOdOG04b4mcUNOrmijXto/ueBuBDYKRA/bfnW5ITbvPwV0nFq4Nw+1r1nF8Co+QBO6KBqnRvf+MBp1Pq6ON0njGki48ioRy3QJpL7wqzoS+2Bur19Yu84gMWo8J8ceAbqi052vU34aDue+DMsRCMf',
    'rxVisitor': '1531648955904ES136VFF4TBP5VNH0DP92S2Q488EIDEB',
    'check': 'true',
    '_gid': 'GA1.2.856685975.1531648957',
    'AMCVS_40A3741F578E26BA7F000101%40AdobeOrg': '1',
    's_pr_tbe65': '1531648964017',
    's_cc': 'true',
    's_pr_tbe66': '1531649680908',
    's_sq': '%5B%5BB%5D%5D',
    'JSESSIONID': 'cr3f25drn70vr5c0dss6id8h.azupkaraf138881',
    'dtSa': '-',
    'bm_mi': 'FB7606753FEDBAD67F4C1164F3DE1A15~rg1oYdzPXob9ydIRkcs2SZhF3ojKSPvnGJjM6kmxBOKPoyX3XquseG3P1u4fmNPlb/bTQEmivmAUcuSmLf45olG9STJV9Z9/R8kzL4ZOTDF8+3dATBagbbyKXuBcq5cs/Osmd2w8N3+syi429G/qYeHrOsOcX9UpyUndVK5xE6fA4AN/cftimNFdRFaTUCQmc4saoffHbmfPp8BPmb9TDtMvZAW1WPpudH2XDwUVcqkHG6WIwRwc9i/0GHrKKeVbfaQ4bVX4GaoyTvhYritbu33nTSS31yGlUnsyQvFOjr93uvdsVhGqX2jCMg8Jedjp',
    'ak_bmsc': 'E8F58E0198AA3BF03FA774B2AD82144A7D38DA29F74A0000EF384B5B09A3C117~plfYfGa42ztFnSKbskuPKM/6C302118XB02QhZJpWZKCp9wkIdA626ymthoNeRJX232prQkJFXH/1MNlahM+v5kxII4EoX0vYOAYfEokEeyNtWtLH5YJkJ8idDLTAJw5jDxbItLZom337ZbOFcWaK1XdTRLX8PTk9zBeAaBAsk565bZz2Jdr0ocWYm7pfNg+jXfjBFBrBySacjicJoVXdpkRwSgzIbohBT+ex2DvjasxslwpNxb9IJP1wO2yPHQRPa',
    's_lv_s': 'Less%20than%201%20day',
    'gpv_v13': 'FA%3A%20W%3A%20Category%3A%20Mens%3A%20Shoes',
    's_vnum': '1533052800754%26vn%3D6',
    's_invisit': 'true',
    's_vs': '1',
    'mbox': 'PC#255d0d746a0c4060aa55d5bab4003561.24_13#1594288695|session#a81b77eaf81f4b0bb0b17aecdaf02f3e#1531658922',
    'stc111430': 'env:1531656581%7C20180815120941%7C20180715124741%7C3%7C1011980:20190715121741|uid:1531043898554.863576805.2595744.111430.2066777970.:20190715121741|srchist:1011980%3A1531656581%3A20180815120941:20190715121741|tsa:1531656581216.1698871706.0723276.6656449679083218.:20180715124741',
    '_uetsid': '_uetfc1f78e4',
    's_ppvl': 'FA%253A%2520W%253A%2520Category%253A%2520Mens%253A%2520Shoes%2C9%2C16%2C1586%2C1440%2C780%2C1440%2C900%2C1%2CL',
    'AMCV_40A3741F578E26BA7F000101%40AdobeOrg': '-330454231%7CMCIDTS%7C17728%7CMCMID%7C80765951905264690684288819499406804587%7CMCAAMLH-1532261873%7C11%7CMCAAMB-1532261873%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1531663750s%7CNONE%7CMCSYNCSOP%7C411-17735%7CMCCIDH%7C405989790%7CvVersion%7C3.1.2',
    's_ptc': '0.00%5E%5E0.00%5E%5E0.00%5E%5E0.13%5E%5E0.09%5E%5E0.03%5E%5E17.52%5E%5E0.01%5E%5E17.91',
    'dtPC': '2$457060171_478h-vUOJSVAMWAICNDXTVLQICGSTVSCISFWBF',
    'rxvt': '1531658882593|1531655819736',
    'bm_sv': '05D10B6F73B7FC30C455DEE4CE789D9A~PMZs7VvUM55meTMDSVmXy5uKN6H5t5qNfaQoTPkbOgREqzyQXZb+npW6H8NB8vi79uoy5DaDCC+HzNtUJ9TPJKSJ3nGaAoGOWVF+iJwYkyhvKORQMIdXFrcWzmQBuZpySmDiF6ayDboZPbDdgyPNJ73AgeyLCD3so9Sq6k3P9d8=',
    'dtLatC': '1',
    's_lv': '1531657140090',
    's_ppv': 'FA%253A%2520W%253A%2520Category%253A%2520Mens%253A%2520Shoes%2C8%2C8%2C780%2C952%2C780%2C1440%2C900%2C1%2CL',
    's_tps': '85',
    's_pvs': '79',
    'dtCookie': '2$MCBQK5AF1I5F2NTNBNE7VQBJS3AU6O70|Footaction|1'
}

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1;WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
    'upgrade-insecure-requests': '1',
    'pragma': 'no-cache',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    # 'accept': 'application/json'
}

def fetch_detail(url):
    url = 'https://www.footaction.com' + url
    pq = helper.get(url, cookies)
    name = pq('span.c-product-name').text()
    print('name = %s' % name)
    number = pq('div.c-tab-panel').text().split(' ')[2]
    print('number = %s' % number)

    size_price_arr = []
    price = '0.00'
    try:
        price = float(pq('span.sr-only').text().replace('$', ''))
    except:
        price = float(pq('span.final').text().replace('$', ''))
    size_arr = pq('div.c-size p > label').text().split(' ')
    for size in size_arr:
        size_price_arr.append({
            'size': float(size),
            'price': price,
            'isInStock': True
        })
    print('size_price_arr = ', size_price_arr)

    img_json_str = helper.get('https://images.footaction.com/is/image/EBFL2/%sMM?req=set,json' % number, returnText=True)
    img_json = None
    img_url = None
    try:
        img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
        img_item_arr = img_json.get('set').get('item')
        for img_item in img_item_arr:
            if img_item.get('type') == 'img_set':
                img_url = img_item.get('set').get('item')[0].get('s').get('n')
                break
    except:
        img_json_str = helper.get('https://images.footaction.com/is/image/EBFL2/%s?req=set,json' % number, returnText=True)
        img_json = json.loads(img_json_str.replace('/*jsonp*/s7jsonResponse(', '').replace(',"");', ''))
        img_item_arr = img_json.get('set').get('item')
        try:
            img_url = img_item_arr[0].get('s').get('n')
        except:
            img_url = img_item_arr.get('s').get('n')

    img_url = 'https://images.footaction.com/is/image/%s?wid=600&hei=600&fmt=jpg' % img_url
    print(img_url)
    global platform
    helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
    mongo.insert_pending_goods(name, number, url, size_price_arr, ['%s.jpg' % number], platform)
    # 上传到七牛
    qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/%s/%s.jpg' % (platform, number))


def fetch_page(url, page = 1, total_page = -1):
    page_url = '%s?currentPage=%d&sort=name-asc' % (url, page - 1)
    pq = helper.get(page_url, cookies, headers)
    # 获取商品详情url
    a_arr = pq('div.c-product-card > a')
    for a in a_arr:
        fetch_detail(a.get('href'))
    if total_page < 0:
        total_str = pq('div.sub strong').text()
        total_page = int(math.ceil(int(total_str) / 60))
    if page + 1 < total_page:
        fetch_page(url, page + 1, total_page)


def start():
    # fetch_page('https://www.footaction.com/Mens/Shoes/_-_/N-24Zrj')
    fetch_page('https://www.footaction.com/category/mens/shoes.html', 5)


    # fetch_man_page()
    # fetch_page('https://www.footlocker.com/Womens/Shoes/_-_/N-25Zrj')
    # fetch_detail('https://www.footaction.com/product/model:271276/sku:23511201/nike-air-force-1-lv8-mens/olive-green/black/')
