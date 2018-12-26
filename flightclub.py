#!/usr/bin/env python
# -*- coding: utf-8 -*-

import helper
import re
import qiniuUploader
import mongo
import os
import time
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue


error_detail_url = {}


class PageSpider(Thread):
    def __init__(self, url, q, error_page_url_queue, gender):
        # 重写写父类的__init__方法
        super(PageSpider, self).__init__()
        self.url = url
        self.q = q
        self.error_page_url_queue = error_page_url_queue
        self.gender = gender

    def run(self):
        try:
            pq = helper.get(self.url)
            for a in pq('li.item > a'):
                self.q.put(a.get('href'))
        except:
            helper.log('[ERROR] => ' + self.url, 'flightclub')
            self.error_page_url_queue.put({'url': self.url, 'gender': self.gender})


class GoodsSpider(Thread):
    def __init__(self, url, gender, q, crawl_counter):
        # 重写写父类的__init__方法
        super(GoodsSpider, self).__init__()
        self.url = url
        self.gender = gender
        self.q = q
        self.crawl_counter = crawl_counter

    def run(self):
        '''
        解析网站源码
        '''
        time.sleep(2)
        try:
            pq = helper.get(self.url)
            name = pq('div.nosto_product > span.name').text()
            number = ''
            color_value = ''
            index = 0
            for li in pq('li.attribute-list-item'):
                if index == 0:
                    number = li.text.strip()
                elif index == 1:
                    color_value = li.text.strip()
                index += 1
            size_price_arr = []
            for div in pq('div.hidden > div'):
                price = float(div.find('span').text)
                size = float(div.find('div').find('meta').get('content').split('_')[-1])
                size_price_arr.append({
                    'size': size,
                    'price': price,
                    'isInStock': True
                })
            img_downloaded = mongo.is_pending_goods_img_downloaded(self.url)
            # TODO: 先不管怎么样，图片都先过一遍
            # if not img_downloaded:
            if True:
                try:
                    img_url = pq('div.mobile-product-image > img.product-img').attr('data-src')
                except:
                    img_url = None
                if not img_url:
                    img_url = pq('link.hidden').attr('src')
                result = helper.downloadImg(img_url, os.path.join('.', 'imgs', 'flightclub', '%s.jpg' % number))
                if result == 1:
                    # 上传到七牛
                    qiniuUploader.upload_2_qiniu('flightclub', '%s.jpg' % number, './imgs/flightclub/%s.jpg' % number)
                    img_downloaded = True
            mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, 'flightclub', '5ac8592c48555b1ba318964a', self.crawl_counter, img_downloaded=img_downloaded)
        except:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), 'flightclub')
            if error_counter < 3:
                self.q.put(self.url)


def fetch_page(url_list, gender, q, error_page_url_queue, crawl_counter):
    page_thread_list = []
    # 构造所有url
    for url in url_list:
        # 创建并启动线程
        time.sleep(1.2)
        page_spider = PageSpider(url, q, error_page_url_queue, gender)
        page_spider.start()
        page_thread_list.append(page_spider)
    for t in page_thread_list:
        t.join()

    goods_thread_list = []
    while True:
        queue_size = q.qsize()
        if queue_size > 0:
            # 每次启动5个抓取商品的线程
            for i in range(5 if queue_size > 5 else queue_size):
                goods_spider = GoodsSpider(q.get(), gender, q, crawl_counter)
                goods_spider.start()
                goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start(action):
    if action == 'common':
        crawl_counter = mongo.get_crawl_counter('flightclub')
        # 创建一个队列用来保存进程获取到的数据
        q = Queue()
        # 有错误的页面链接
        error_page_url_queue = Queue()
        total_page = 70
        base_url = 'https://www.flightclub.com/men?id=446&limit=90&p='
        fetch_page([base_url + str(page) for page in range(1, total_page + 1)], 1, q, error_page_url_queue, crawl_counter)

        total_page = 4
        base_url = 'https://www.flightclub.com/women?id=350&limit=90&p='
        fetch_page([base_url + str(page) for page in range(1, total_page + 1)], 2, q, error_page_url_queue, crawl_counter)

        # 处理出错的链接
        while not error_page_url_queue.empty():
            error_page_url_list = []
            while not error_page_url_queue.empty():
                error_page_url_list.append(error_page_url_queue.get())

            error_page_men_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 1]
            fetch_page(error_page_men_url_list, 1, q, error_page_url_queue, crawl_counter)

            error_page_women_url_list = [url_data.get('url') for url_data in error_page_url_list if url_data.get('gender') == 2]
            fetch_page(error_page_women_url_list, 2, q, error_page_url_queue, crawl_counter)
    helper.log('done', 'flightclub')

    # pq = helper.get('https://www.flightclub.com/nike-air-force-1-07-white-metallix-silver-021260')
    # img_url = pq('div.mobile-product-image > img.product-img').attr('data-src')
    # print(img_url)



# [2018-12-26 16:50:14] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-5-retro-og-black-fire-red-mtllc-slvr-wht-012471
# [2018-12-26 16:50:14] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-11-retro-low-binary-blue-binary-blue-sail-803915
# [2018-12-26 16:50:15] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-8-retro-black-gym-red-black-wolf-grey-801785
# [2018-12-26 16:50:15] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-pw-human-race-nmd-tr-noble-ink-bold-yellow-footwear-white-802504
# [2018-12-26 16:50:15] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-8-retro-black-white-lt-graphite-012347
# [2018-12-26 16:50:17] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-black-white-201336
# [2018-12-26 16:50:18] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-core-black-core-black-clear-mint-804805
# [2018-12-26 16:50:18] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-black-780023
# [2018-12-26 16:50:18] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-mid-acronym-white-black-hot-lava-volt-053066
# [2018-12-26 16:50:18] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-3-retro-hc-metallic-silver-cool-grey-802525
# [2018-12-26 16:50:21] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-sb-zoom-dunk-low-pro-binary-blue-binary-blue-801637
# [2018-12-26 16:50:21] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/201031/
# [2018-12-26 16:50:21] [ERROR] error timer = 3, url = https://www.flightclub.com/old-skool-primar-primary-check-rng-rd-w-803191
# [2018-12-26 16:50:21] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-huarache-run-habanero-red-black-white-805722
# [2018-12-26 16:50:22] [ERROR] error timer = 3, url = https://www.flightclub.com/jason-markk-suede-cleaning-kit-2-piece-cleaning-kit-992178
# [2018-12-26 16:50:25] [ERROR] error timer = 3, url = https://www.flightclub.com/the-ultimate-scuff-eraser-803338
# [2018-12-26 16:50:25] [ERROR] error timer = 3, url = https://www.flightclub.com/air-vapormax-plus-cool-grey-team-orange-805411
# [2018-12-26 16:50:25] [ERROR] error timer = 3, url = https://www.flightclub.com/air-force-1-high-black-black-white-805718
# [2018-12-26 16:50:25] [ERROR] error timer = 3, url = https://www.flightclub.com/air-max-98-gundam-white-university-red-obsidian-803075
# [2018-12-26 16:50:25] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-j-mulit-color-multi-color-801834
# [2018-12-26 16:50:28] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-little-posite-pro-dk-grey-heather-black-black-801222
# [2018-12-26 16:50:28] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-1-black-black-white-gym-red-801367
# [2018-12-26 16:50:28] [ERROR] error timer = 3, url = https://www.flightclub.com/creeper-white-black-white-black-800647
# [2018-12-26 16:50:28] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-sb-dunk-low-trd-qs-dune-twig-wheat-gum-med-brown-800964
# [2018-12-26 16:50:29] [ERROR] error timer = 3, url = https://www.flightclub.com/rihanna-x-puma-fenty-bow-trinomic-sweet-lavender-800713
# [2018-12-26 16:50:32] [ERROR] error timer = 3, url = https://www.flightclub.com/creeper-wrinkled-patent-black-black-800650
# [2018-12-26 16:50:32] [ERROR] error timer = 3, url = https://www.flightclub.com/vapormax-fx-cdg-pure-platinum-white-wolf-grey-800612
# [2018-12-26 16:50:32] [ERROR] error timer = 3, url = https://www.flightclub.com/legacy-crew-sock-ultramarine-800199
# [2018-12-26 16:50:32] [ERROR] error timer = 3, url = https://www.flightclub.com/ultra-boost-reigning-champ-white-heather-800686
# [2018-12-26 16:50:32] [ERROR] error timer = 3, url = https://www.flightclub.com/legacy-crew-sock-kelly-800200
# [2018-12-26 16:50:35] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-legacy-crew-sock-red-white-701119
# [2018-12-26 16:50:35] [ERROR] error timer = 3, url = https://www.flightclub.com/crep-protect-the-ultimate-shoe-cleaner-cure-solution-200-ml-bottle-780040
# [2018-12-26 16:50:35] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-legacy-crew-sock-neon-green-black-701117
# [2018-12-26 16:50:35] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-charcoal-grey-780026
# [2018-12-26 16:50:37] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/156652/
# [2018-12-26 16:50:41] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-grey-white-780027
# [2018-12-26 16:50:42] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-athl-orange-780029
# [2018-12-26 16:50:42] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-grape-780028
# [2018-12-26 16:50:42] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-high-risk-red-780022
# [2018-12-26 16:50:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-se-qs-neutral-grey-black-kmqt-strng-052942
# [2018-12-26 16:50:45] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-5-retro-td-sail-orange-peel-black-hyper-royal-805092
# [2018-12-26 16:50:45] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-dunk-low-premium-sb-atomic-pink-black-white-081284
# [2018-12-26 16:50:45] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-2-retro-black-varsity-red-012373
# [2018-12-26 16:50:46] [ERROR] error timer = 3, url = https://www.flightclub.com/air-force-1-as-qs-white-white-white-803575
# [2018-12-26 16:50:46] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-max-1-97-vf-sw-td-lt-blue-fury-lemon-wash-803623
# [2018-12-26 16:50:49] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-little-posite-one-td-black-psn-green-pink-fl-gmm-bl-803882
# [2018-12-26 16:50:49] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-5-retro-gp-td-black-black-deadly-pink-white-804208
# [2018-12-26 16:50:49] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-more-uptempo-island-green-white-802927
# [2018-12-26 16:50:49] [ERROR] error timer = 3, url = https://www.flightclub.com/jason-markk-foam-803832
# [2018-12-26 16:50:51] [ERROR] error timer = 3, url = https://www.flightclub.com/air-more-uptempo-chi-qs-university-red-university-red-802931
# [2018-12-26 16:50:54] [ERROR] error timer = 3, url = https://www.flightclub.com/iniki-runner-pine-green-white-gum-803041
# [2018-12-26 16:50:54] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-sb-zoom-dunk-low-elite-qs-black-black-white-medium-grey-802761
# [2018-12-26 16:50:54] [ERROR] error timer = 3, url = https://www.flightclub.com/futurecraft-4d-cblack-grefiv-ashgrn-803127
# [2018-12-26 16:50:54] [ERROR] error timer = 3, url = https://www.flightclub.com/ultimate-gift-pack-802514
# [2018-12-26 16:50:55] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-dunk-high-sb-qs-blue-ribbon-blue-ribbon-802827
# [2018-12-26 16:50:58] [ERROR] error timer = 3, url = https://www.flightclub.com/climacool-02-17-tacgrn-tacgrn-ftwwht-802069
# [2018-12-26 16:50:58] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-13-retro-gp-black-metallic-gold-mint-foam-802250
# [2018-12-26 16:50:58] [ERROR] error timer = 3, url = https://www.flightclub.com/cleated-creepersuede-wn-s-puma-black-801869
# [2018-12-26 16:50:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-grey-three-grey-three-801976
# [2018-12-26 16:50:58] [ERROR] error timer = 3, url = https://www.flightclub.com/superstar-ftwwht-conavy-ftwwht-802455
# [2018-12-26 16:51:01] [ERROR] error timer = 3, url = https://www.flightclub.com/crep-protect-the-ultimate-rain-stain-resistant-barrier-780004
# [2018-12-26 16:51:01] [ERROR] error timer = 3, url = https://www.flightclub.com/leadcat-fenty-pink-pink-801429
# [2018-12-26 16:51:01] [ERROR] error timer = 3, url = https://www.flightclub.com/foundation-sweatpants-black-fc-red-801292
# [2018-12-26 16:51:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-grey-raw-pink-801871
# [2018-12-26 16:51:02] [ERROR] error timer = 3, url = https://www.flightclub.com/nikelab-air-force-1-low-cmft-tc-light-cognac-purple-agate-ivory-light-cognac-801541
# [2018-12-26 16:51:05] [ERROR] error timer = 3, url = https://www.flightclub.com/jason-markk-travel-kit-800585
# [2018-12-26 16:51:05] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-11-retro-low-gp-td-505835-010-801121
# [2018-12-26 16:51:05] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-11-retro-low-gp-td-blue-moon-polarized-blue-801119
# [2018-12-26 16:51:05] [ERROR] error timer = 3, url = https://www.flightclub.com/rihanna-x-puma-fenty-bow-trinomic-pink-tint-pink-tint-pink-tint-800714
# [2018-12-26 16:51:05] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1w-sunglo-wwht-hzcor-800674
# [2018-12-26 16:51:09] [ERROR] error timer = 3, url = https://www.flightclub.com/alumni-full-zip-ultramarine-800385
# [2018-12-26 16:51:09] [ERROR] error timer = 3, url = https://www.flightclub.com/nikelab-air-max-plus-pearl-pink-cobblestone-sail-800980
# [2018-12-26 16:51:09] [ERROR] error timer = 3, url = https://www.flightclub.com/alumni-full-zip-navy-800228
# [2018-12-26 16:51:09] [ERROR] error timer = 3, url = https://www.flightclub.com/alumni-full-zip-heather-800226
# [2018-12-26 16:51:09] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r2-pk-collegiate-navy-running-white-800810
# [2018-12-26 16:51:12] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-legacy-crew-sock-black-red-701120
# [2018-12-26 16:51:12] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/179239/
# [2018-12-26 16:51:12] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-brown-red-white-800052
# [2018-12-26 16:51:13] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-legacy-crew-sock-grey-white-701118
# [2018-12-26 16:51:13] [ERROR] error timer = 3, url = https://www.flightclub.com/legacy-crew-sock-purple-800203
# [2018-12-26 16:51:16] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-mid-acronym-black-black-bamboo-053065
# [2018-12-26 16:51:16] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-question-mid-primal-red-ice-992279
# [2018-12-26 16:51:16] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-mid-acronym-med-olive-black-dust-053067
# [2018-12-26 16:51:16] [ERROR] error timer = 3, url = https://www.flightclub.com/new-balance-w990-v4-pink-grey-300840
# [2018-12-26 16:51:16] [ERROR] error timer = 3, url = https://www.flightclub.com/crep-protect-the-ultimate-shoe-cleaner-cure-travel-pack-3-piece-cleaning-kit-780012
# [2018-12-26 16:51:19] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-royal-nylon-black-black-carbon-992242
# [2018-12-26 16:51:20] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-cl-lthr-black-gum-992156
# [2018-12-26 16:51:20] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-black-black-black-052868
# [2018-12-26 16:51:20] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-aqua-780030
# [2018-12-26 16:51:20] [ERROR] error timer = 3, url = https://www.flightclub.com/flight-club-stealth-no-show-sock-ultramarine-780024
# [2018-12-26 16:51:23] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-4-retro-td-black-vivid-pink-dynmc-bl-wht-012554
# [2018-12-26 16:51:53] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-lebron-10-honey-honey-041971
# [2018-12-26 16:51:53] [ERROR] error timer = 3, url = https://www.flightclub.com/pure-boost-grey-black-800010
# [2018-12-26 16:51:53] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-6-retro-gp-wht-frc-grn-dp-ryl-bl-hypr-pnk-012192
# [2018-12-26 16:51:53] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-qs-black-zen-grey-habor-blue-052839
# [2018-12-26 16:52:40] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-prsn-violet-blck-ntrl-gry-wht-053052
# [2018-12-26 16:52:40] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-club-c-85-black-white-992230
# [2018-12-26 16:52:40] [ERROR] error timer = 3, url = https://www.flightclub.com/new-balance-w530-steel-blue-rain-300827
# [2018-12-26 16:52:40] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-wnms-air-huarache-run-white-fchs-flsh-artsn-tl-fchs-052680
# [2018-12-26 16:52:40] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-ultra-boost-uncaged-j-pink-white-201429
# [2018-12-26 16:53:27] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-cl-nylon-team-navy-platinum-992249
# [2018-12-26 16:53:27] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-cl-lthr-spirit-respect-energy-992182
# [2018-12-26 16:53:27] [ERROR] error timer = 3, url = https://www.flightclub.com/reebok-cl-lthr-spirit-philosophic-white-energy-992183
# [2018-12-26 16:53:27] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-max-thea-lotc-qs-blacjk-black-white-052977
# [2018-12-26 16:53:27] [ERROR] error timer = 3, url = https://www.flightclub.com/asics-gel-lyte-3-turquoise-white-991944
# [2018-12-26 16:54:14] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-free-flyknit-chukka-pr-qs-gm-royal-obsdn-hypr-pnch-ivry-052228
# [2018-12-26 16:54:14] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-tp-qs-tumbled-grey-black-anthrct-wht-052744
# [2018-12-26 16:54:14] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-lil-posite-pro-cb-black-black-laser-crimson-042293
# [2018-12-26 16:54:14] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-qs-black-yellow-streak-ntrl-grey-052805
# [2018-12-26 16:54:14] [ERROR] error timer = 3, url = https://www.flightclub.com/asics-gel-lyte-3-dk-olive-black-991857
# [2018-12-26 16:55:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-tp-qs-black-anthracite-black-052743
# [2018-12-26 16:55:01] [ERROR] error timer = 3, url = https://www.flightclub.com/saucony-shadow-original-black-grey-991945
# [2018-12-26 16:55:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-presto-sp-black-black-cement-grey-052287
# [2018-12-26 16:55:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-max-1-prm-grain-orange-blaze-052074
# [2018-12-26 16:55:01] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-10-retro-gp-white-verde-black-infrared-23-012182
# [2018-12-26 16:55:22] [ERROR] error timer = 3, url = https://www.flightclub.com/air-jordan-14-retro-low-white-pacific-blu-mts-brt-ceramic-011177
# [2018-12-26 16:55:22] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-glc-promo-black1-black1-black1-200804
# [2018-12-26 16:55:23] [ERROR] error timer = 3, url = https://www.flightclub.com/girls-jordan-1-td-emerald-green-black-grp-ic-wht-011116
# [2018-12-26 16:55:23] [ERROR] error timer = 3, url = https://www.flightclub.com/women-s-air-jordan-10-retro-white-medium-violet-light-graphite-010249
# [2018-12-26 16:55:23] [ERROR] error timer = 3, url = https://www.flightclub.com/jordan-3-retro-td-white-black-metallic-silver-varsity-red-010677
# [2018-12-26 16:55:34] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-8-vday-gym-red-ember-glow-team-red-803202
# [2018-12-26 16:55:34] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-11-retros-neutral-olive-mtlc-stout-sail-805670
# [2018-12-26 16:55:34] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-12-retro-vachetta-tan-metallic-gold-803392
# [2018-12-26 16:55:34] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-4-retro-nrg-fire-red-summit-white-black-805694
# [2018-12-26 16:55:35] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-force-1-high-white-white-white-805419
# [2018-12-26 16:55:38] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-re-hi-og-sl-black-black-starfish-sail-803897
# [2018-12-26 16:55:38] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-11-retro-sail-mtlc-red-bronze-803590
# [2018-12-26 16:55:38] [ERROR] error timer = 1, url = https://www.flightclub.com/w-s-air-huarache-run-black-black-801232
# [2018-12-26 16:55:38] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-high-zip-particle-beige-mtlc-red-bronze-804550
# [2018-12-26 16:55:38] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-plus-light-crimson-black-white-805436
# [2018-12-26 16:55:41] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-utiblk-ftwwht-mgsogr-800675
# [2018-12-26 16:55:41] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-13-retro-phantom-moon-particle-804534
# [2018-12-26 16:55:41] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-ash-pearl-chalk-pearl-white-802615
# [2018-12-26 16:55:42] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-3-retro-se-bordeaux-bordeaux-phantom-805066
# [2018-12-26 16:55:42] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-black-light-cream-white-804927
# [2018-12-26 16:55:45] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-3-retro-se-particle-beige-mtlc-red-bronze-804251
# [2018-12-26 16:55:45] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-plus-lx-dusty-peach-bio-beige-803889
# [2018-12-26 16:55:45] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-802836
# [2018-12-26 16:55:45] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-white-black-university-red-804037
# [2018-12-26 16:55:45] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-95-se-sail-arctic-pink-racer-blue-804584
# [2018-12-26 16:55:48] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/170757/
# [2018-12-26 16:55:48] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-white-pink-801145
# [2018-12-26 16:55:48] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-clear-onix-light-onix-vapour-pink-800411
# [2018-12-26 16:55:49] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-blue-white-801432
# [2018-12-26 16:55:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-white-052856
# [2018-12-26 16:55:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-gym-red-gym-red-052807
# [2018-12-26 16:55:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-black-mint-green-805489
# [2018-12-26 16:55:52] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-90-white-court-purple-wolf-grey-805350
# [2018-12-26 16:55:52] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-lebron-xvi-lmtd-sail-white-light-bone-805019
# [2018-12-26 16:55:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-lx-white-black-total-orange-804343
# [2018-12-26 16:55:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-more-uptempo-dark-stucco-white-black-802794
# [2018-12-26 16:55:57] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-air-vapormax-flyknit-string-chrome-sunset-glow-802784
# [2018-12-26 16:55:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-black-black-varsity-royal-804022
# [2018-12-26 16:55:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-max-1-prm-mtlc-pewter-mtlc-pewter-summit-wht-802914
# [2018-12-26 16:56:00] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r2-w-linen-linen-ftwwht-802145
# [2018-12-26 16:56:00] [ERROR] error timer = 1, url = https://www.flightclub.com/bb2368-maroon-cburgu-ftwwht-802457
# [2018-12-26 16:56:00] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-pk-sea-crystal-turquoise-sea-crystal-800910
# [2018-12-26 16:56:00] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-mystery-blue-mystery-blue-vapour-grey-801987
# [2018-12-26 16:56:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-salmon-800036
# [2018-12-26 16:56:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-pk-shock-pink-core-black-running-white-ftw-800772
# [2018-12-26 16:56:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-xr1-pk-w-icepur-midgre-ftwwht-800663
# [2018-12-26 16:56:05] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-ultra-boost-w-core-black-black-grey-201351
# [2018-12-26 16:56:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-dark-grey-teal-052764
# [2018-12-26 16:56:08] [ERROR] error timer = 1, url = https://www.flightclub.com/ultra-boost-w-ash-green-ash-green-real-teal-804645
# [2018-12-26 16:56:08] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-desert-sand-desert-sand-804212
# [2018-12-26 16:56:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-pink-white-gum-803671
# [2018-12-26 16:56:08] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-pearl-pink-pearl-pink-803928
# [2018-12-26 16:56:08] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-green-201035
# [2018-12-26 16:56:11] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/232155/
# [2018-12-26 16:56:11] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-hi-prem-black-metallic-gold-803536
# [2018-12-26 16:56:11] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-95-white-court-purple-803222
# [2018-12-26 16:56:12] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-purple-earth-white-803186
# [2018-12-26 16:56:12] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-93-white-sport-turq-black-803524
# [2018-12-26 16:56:15] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-xr1-w-white-white-pearl-grey-801270
# [2018-12-26 16:56:15] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-classic-cortez-leather-white-varsity-red-801434
# [2018-12-26 16:56:15] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r2-w-wonpnk-wonpnk-cblack-801683
# [2018-12-26 16:56:15] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-xr1-w-drkbur-drkbur-vappnk-802997
# [2018-12-26 16:56:15] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-summit-white-mtlc-red-bronze-801680
# [2018-12-26 16:56:19] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-x-parley-w-night-navy-intense-blue-800938
# [2018-12-26 16:56:19] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-sock-dart-prm-black-white-black-800766
# [2018-12-26 16:56:19] [ERROR] error timer = 1, url = https://www.flightclub.com/iniki-runner-w-purple-white-cream-800646
# [2018-12-26 16:56:19] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-vapour-pink-light-onix-800410
# [2018-12-26 16:56:19] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-plus-qs-metallic-gold-university-red-801048
# [2018-12-26 16:56:22] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-presto-flyknit-ultra-hyper-turq-hyper-turq-053029
# [2018-12-26 16:56:22] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-red-201385
# [2018-12-26 16:56:22] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-grey-mtllc-silver-201364
# [2018-12-26 16:56:22] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-pink-black-white-800368
# [2018-12-26 16:56:22] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-binary-blue-binary-blue-black-800256
# [2018-12-26 16:56:25] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-force-1-07-se-black-wheat-gold-805400
# [2018-12-26 16:56:25] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-white-black-wolf-grey-805083
# [2018-12-26 16:56:25] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-5-white-fire-red-sunset-dark-cinder-010743
# [2018-12-26 16:56:25] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-raw-pink-white-201307
# [2018-12-26 16:56:30] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-black-tactile-rose-bold-red-804324
# [2018-12-26 16:56:30] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-trace-scarlet-trace-scarlet-running-white-804437
# [2018-12-26 16:56:30] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-grey-blue-804472
# [2018-12-26 16:56:30] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-red-black-804187
# [2018-12-26 16:56:30] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-lx-total-orange-white-black-804430
# [2018-12-26 16:56:33] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-gold-black-804006
# [2018-12-26 16:56:33] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/242350/
# [2018-12-26 16:56:33] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/243219/
# [2018-12-26 16:56:33] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-ash-pearl-ash-pearl-ash-pearl-803574
# [2018-12-26 16:56:33] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-high-zip-white-white-university-red-803772
# [2018-12-26 16:56:36] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-air-more-uptempo-white-chrome-blue-tint-803139
# [2018-12-26 16:56:36] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-plum-fog-plum-fog-803279
# [2018-12-26 16:56:36] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-light-aqua-white-metallic-gold-803146
# [2018-12-26 16:56:36] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-sol-sunblush-white-metallic-gold-803145
# [2018-12-26 16:56:36] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-ice-peach-white-metallic-gold-803147
# [2018-12-26 16:56:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-midnight-fog-multi-color-black-802785
# [2018-12-26 16:56:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-volt-802753
# [2018-12-26 16:56:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-white-white-sail-light-bone-803067
# [2018-12-26 16:56:40] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-xr1-pk-w-utiivy-utiivy-corred-802928
# [2018-12-26 16:56:44] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-metallic-silver-802634
# [2018-12-26 16:56:44] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-footscape-woven-sail-white-red-stardust-802444
# [2018-12-26 16:56:44] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-black-black-white-racer-blue-802551
# [2018-12-26 16:56:44] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-black-carbon-running-white-802681
# [2018-12-26 16:56:44] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-bordeaux-tea-berry-black-802338
# [2018-12-26 16:56:47] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-raw-pink-trace-pink-legend-ink-801864
# [2018-12-26 16:56:47] [ERROR] error timer = 1, url = https://www.flightclub.com/womens-roshe-one-black-black-dark-grey-802319
# [2018-12-26 16:56:47] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-huarache-run-prm-txt-mahogany-mtlc-mahogany-802276
# [2018-12-26 16:56:47] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-90-prm-db-white-black-dynamic-yellow-801898
# [2018-12-26 16:56:48] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-plus-se-white-white-black-801882
# [2018-12-26 16:56:51] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r2-w-clear-granite-vintage-white-801272
# [2018-12-26 16:56:51] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-black-white-801450
# [2018-12-26 16:56:51] [ERROR] error timer = 1, url = https://www.flightclub.com/w-s-air-huarache-run-max-orange-cool-grey-801387
# [2018-12-26 16:56:51] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-huarache-run-dusted-clay-white-gum-yellow-801401
# [2018-12-26 16:56:51] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-grey-grey-801431
# [2018-12-26 16:56:54] [ERROR] error timer = 1, url = https://www.flightclub.com/iniki-runner-w-pink-blue-gum-801246
# [2018-12-26 16:56:54] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-huarache-run-ember-glow-dark-cayenne-white-801233
# [2018-12-26 16:56:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-cs2-pk-w-peagre-peagre-ftw-801098
# [2018-12-26 16:56:54] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-hurache-run-sport-fuchsia-white-gum-yellow-801071
# [2018-12-26 16:56:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-cs2-pk-w-tragrn-tragrn-trapnk-801240
# [2018-12-26 16:56:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-90-white-white-wolf-grey-black-801021
# [2018-12-26 16:56:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-zero-white-black-800987
# [2018-12-26 16:56:57] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-white-white-white-801004
# [2018-12-26 16:56:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-toki-slip-canvas-white-white-800992
# [2018-12-26 16:56:57] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-black-blue-801055
# [2018-12-26 16:57:00] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-dark-grey-black-wolf-grey-800867
# [2018-12-26 16:57:01] [ERROR] error timer = 1, url = https://www.flightclub.com/w-s-air-huarache-run-anthracite-oatmeal-cool-grey-800851
# [2018-12-26 16:57:01] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-pk-green-pink-green-800909
# [2018-12-26 16:57:01] [ERROR] error timer = 1, url = https://www.flightclub.com/air-max-zero-wolf-grey-wolf-grey-white-800986
# [2018-12-26 16:57:01] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-pinnacle-silt-red-silt-red-sail-800897
# [2018-12-26 16:57:04] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-classic-cortez-str-ltr-black-black-black-800764
# [2018-12-26 16:57:04] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-pk-black-pink-white-800788
# [2018-12-26 16:57:04] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-white-wolf-grey-800731
# [2018-12-26 16:57:04] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r2-w-olive-white-800736
# [2018-12-26 16:57:04] [ERROR] error timer = 1, url = https://www.flightclub.com/iniki-runner-w-orange-white-gum-800845
# [2018-12-26 16:57:08] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-university-red-800690
# [2018-12-26 16:57:08] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-white-grey-800653
# [2018-12-26 16:57:08] [ERROR] error timer = 1, url = https://www.flightclub.com/iniki-runner-w-mint-white-gum-800645
# [2018-12-26 16:57:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-r1-w-grey-white-800601
# [2018-12-26 16:57:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-cs2-pk-w-conavy-conavy-ftwwht-800689
# [2018-12-26 16:57:11] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-owhite-800325
# [2018-12-26 16:57:11] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-desert-ochre-desert-ochre-800257
# [2018-12-26 16:57:11] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-xr1-w-midgre-nobink-grey-800338
# [2018-12-26 16:57:11] [ERROR] error timer = 1, url = https://www.flightclub.com/ultra-boost-w-black-black-met-800211
# [2018-12-26 16:57:16] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-rl-w-black-sand-white-800062
# [2018-12-26 16:57:16] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-white-teal-sand-201550
# [2018-12-26 16:57:16] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-huarache-run-se-mtlc-dark-sea-midnight-turq-053228
# [2018-12-26 16:57:16] [ERROR] error timer = 1, url = https://www.flightclub.com/nmd-xr1-w-vapgre-icepur-owhite-800008
# [2018-12-26 16:57:17] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-se-mtlc-red-bronze-elm-053083
# [2018-12-26 16:57:20] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmdxr1-pk-w-pink-white-201535
# [2018-12-26 16:57:20] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-force-1-hi-prm-flax-flax-outdoor-green-021534
# [2018-12-26 16:57:20] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-tubular-viral-w-metsil-cgrani-cwhite-201506
# [2018-12-26 16:57:20] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-light-bone-light-bone-sail-021538
# [2018-12-26 16:57:25] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-linen-linen-gum-lt-brown-053063
# [2018-12-26 16:57:25] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-white-white-201418
# [2018-12-26 16:57:25] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-space-pink-challenge-red-space-pink-052760
# [2018-12-26 16:57:25] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-navy-white-bergundy-201503
# [2018-12-26 16:57:29] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-blue-white-201365
# [2018-12-26 16:57:29] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-black-white-201408
# [2018-12-26 16:57:29] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-unity-blue-collegiate-navy-vivid-red-201414
# [2018-12-26 16:57:29] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-black-pink-201224
# [2018-12-26 16:57:29] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-blanch-purple-white-201259
# [2018-12-26 16:57:32] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-pink-blast-white-052980
# [2018-12-26 16:57:32] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-anniversary-bronze-black-infrared-white-052624
# [2018-12-26 16:57:32] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-sunset-gold-dart-white-black-053036
# [2018-12-26 16:57:32] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-zx-flux-w-cblack-cblack-coppmt-201377
# [2018-12-26 16:57:32] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-grey-white-pink-201401
# [2018-12-26 16:57:36] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-beige-beige-white-201285
# [2018-12-26 16:57:36] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-og-white-cool-grey-ntrl-grey-blk-052656
# [2018-12-26 16:57:36] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-essential-wolf-grey-infrared-black-white-053022
# [2018-12-26 16:57:36] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-atomic-pink-atomic-pink-052974
# [2018-12-26 16:57:36] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-presto-ttl-crmsn-brght-crmsn-wht-blck-053016
# [2018-12-26 16:57:39] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-island-green-islnd-grn-ftl-gld-052959
# [2018-12-26 16:57:39] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-052692
# [2018-12-26 16:57:39] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-ultra-boost-w-white-white-201180
# [2018-12-26 16:57:39] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-black-black-mtllc-gold-white-052919
# [2018-12-26 16:57:39] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-rdnt-emrld-sprt-fchs-smm-052966
# [2018-12-26 16:57:42] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-cool-grey-052759
# [2018-12-26 16:57:42] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-bronzine-bronzine-sail-black-052450
# [2018-12-26 16:57:42] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-qs-viola-fushia-glow-chilling-red-052763
# [2018-12-26 16:57:42] [ERROR] error timer = 1, url = https://www.flightclub.com/womens-air-jordan-3-retro-white-harbor-blue-boarder-blue-010536
# [2018-12-26 16:57:42] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-loyal-blue-loyal-blue-052879
# [2018-12-26 16:57:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-anniversary-gym-red-black-infrrd-mtllc-gld-052596
# [2018-12-26 16:57:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-white-white-052603
# [2018-12-26 16:57:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-pure-platinum-052664
# [2018-12-26 16:57:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-white-052455
# [2018-12-26 16:57:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-hot-lava-hot-lava-052613
# [2018-12-26 16:57:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-blue-legend-blue-legend-052625
# [2018-12-26 16:57:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-prm-mtlc-gold-silk-blck-clssc-brwn-051857
# [2018-12-26 16:57:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-lib-qs-dp-brgndy-dp-brgndy-brght-mng-052420
# [2018-12-26 16:57:50] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-lyon-blue-lyn-bl-smmt-wht-blk-052580
# [2018-12-26 16:57:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-vntg-sail-hypr-rd-strt-gry-icd-crmn-051833
# [2018-12-26 16:57:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-blue-spark-coastel-blue-white-800190
# [2018-12-26 16:57:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-university-red-maroon-white-800191
# [2018-12-26 16:57:54] [ERROR] error timer = 1, url = https://www.flightclub.com/w-s-air-jordan-7-retro-white-varsity-maize-black-010314
# [2018-12-26 16:58:20] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-obsidian-obsidian-phantom-053216
# [2018-12-26 16:58:20] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-ultra-boost-uncage-w-teal-white-201428
# [2018-12-26 16:58:35] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-dk-electric-blu-clrwtr-white-053183
# [2018-12-26 16:58:42] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-mayfly-woven-black-dark-grey-white-090189
# [2018-12-26 16:58:42] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-black-white-201242
# [2018-12-26 16:58:42] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-blanch-blue-collegiate-navy-201304
# [2018-12-26 16:58:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-ultra-lotc-qs-ink-ink-summit-white-team-red-052612
# [2018-12-26 16:58:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-pinnacle-black-black-sail-052970
# [2018-12-26 16:58:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-black-black-sail-052971
# [2018-12-26 16:58:46] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-hot-lava-bl-legend-white-052609
# [2018-12-26 16:58:46] [ERROR] error timer = 1, url = https://www.flightclub.com/adidas-nmd-r1-w-white-blue-lt-blu-201240
# [2018-12-26 16:58:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-dp-royal-vlt-blk-pr-pltnm-052924
# [2018-12-26 16:58:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-black-smmt-wht-052588
# [2018-12-26 16:58:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-roshe-one-flyknit-gym-red-brght-crimson-tm-rd-sl-052934
# [2018-12-26 16:58:49] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-menta-hot-lava-052437
# [2018-12-26 16:58:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-essential-white-black-052871
# [2018-12-26 16:58:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-brnzn-smmt-wht-mtllc-gld-052586
# [2018-12-26 16:58:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-obsidian-obsidian-black-052568
# [2018-12-26 16:58:54] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-flyknit-zoom-agility-black-white-elctrc-grn-pnk-pw-052535
# [2018-12-26 16:58:58] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-lsr-crimson-lsr-crmsn-blk-vlt-052174
# [2018-12-26 16:58:58] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-lt-retro-sail-blk-052589
# [2018-12-26 16:59:03] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-cinnabar-lsr-orng-fbrlss-blk-052661
# [2018-12-26 16:59:03] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-chllng-rd-chllg-rd-smmt-wht-b-052600
# [2018-12-26 16:59:03] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-university-red-tr-yllw-sl-blck-052638
# [2018-12-26 16:59:03] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-artisan-teal-sail-black-052597
# [2018-12-26 16:59:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-grey-mint-052584
# [2018-12-26 16:59:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-essential-black-gym-red-sail-gm-md-brown-052780
# [2018-12-26 16:59:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-volt-volt-obsidian-052571
# [2018-12-26 16:59:08] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-mtllc-slvr-strng-snst-glw-grn-052723
# [2018-12-26 16:59:12] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-blue-force-blue-force-sail-052491
# [2018-12-26 16:59:12] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-court-purple-violet-wash-volt-051798
# [2018-12-26 16:59:12] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-white-white-wolf-grey-volt-052567
# [2018-12-26 16:59:12] [ERROR] error timer = 1, url = https://www.flightclub.com/w-s-air-jordan-8-retro-white-varsity-red-bright-concord-aqua-tone-010598
# [2018-12-26 16:59:12] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-nike-rosherun-white-mtlc-platinum-052556
# [2018-12-26 16:59:15] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-black-black-anthracite-052359
# [2018-12-26 16:59:16] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-lib-qs-blue-recall-white-lnn-atmc-mng-052408
# [2018-12-26 16:59:16] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-hyper-crimson-space-blue-052466
# [2018-12-26 16:59:21] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-force-one-hi-prm-qs-white-white-metallic-silver-021413
# [2018-12-26 16:59:21] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-volt-light-bone-052322
# [2018-12-26 16:59:21] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-fv-qs-black-volt-white-052315
# [2018-12-26 16:59:21] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-print-anthracite-black-anthrct-vlt-052340
# [2018-12-26 16:59:21] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-roshe-run-hyp-bright-mango-dk-magnet-grey-052299
# [2018-12-26 16:59:24] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-prm-ivry-mtlc-gld-cn-hypr-pnch-gm-052235
# [2018-12-26 16:59:24] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-vlt-sh-vlt-shd-lsr-crmsn-vlt-052215
# [2018-12-26 16:59:24] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-cut-out-prm-mtlc-rd-brnz-mtlc-rd-brnz-lght-052280
# [2018-12-26 16:59:29] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-vt-qs-black-sail-052190
# [2018-12-26 16:59:29] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-pwm-n7-black-black-summit-white-dark-turquoise-052097
# [2018-12-26 16:59:29] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-sp-obsidian-tropical-teal-volt-052112
# [2018-12-26 16:59:29] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-woven-qs-tropical-twist-white-white-052069
# [2018-12-26 17:00:18] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-air-max-97-vrsty-red-vrsty-red-white-050484
# [2018-12-26 17:00:18] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-air-max-95-medium-grey-turbo-pink-white-050418
# [2018-12-26 17:00:18] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/7445/
# [2018-12-26 17:00:18] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-rosherun-total-crimson-sail-brght-ctrs-051890
# [2018-12-26 17:00:18] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/21311/
# [2018-12-26 17:01:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-dunk-low-light-lava-white-light-blueberry-030546
# [2018-12-26 17:01:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-air-max-90-classic-white-asian-concord-lz-pink-light-zen-grey-050337
# [2018-12-26 17:01:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-blazer-mid-73-black-vivid-violet-anthracite-040650
# [2018-12-26 17:01:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-dunk-low-birch-atomic-red-light-chocolate-030460
# [2018-12-26 17:01:05] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-vandal-sp-hi-premium-tweed-baroque-brown-classic-olive-040265
# [2018-12-26 17:01:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-wmns-dunk-hi-birch-pink-ice-white-030370
# [2018-12-26 17:01:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-dunk-low-premium-celery-papaya-med-mint-varsity-red-030338
# [2018-12-26 17:01:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-womens-air-force-1-07-perfect-pink-white-rose-coral-light-lvp-020706
# [2018-12-26 17:01:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-force-1-supreme-black-black-engine-1-laser-pink-020954
# [2018-12-26 17:01:52] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-wmns-air-force-1-premium-07-tomatillo-pistachio-black-forest-020682
# [2018-12-26 17:02:35] [ERROR] error timer = 1, url = https://www.flightclub.com/womens-air-jordan-4-retro-white-border-blue-light-sand-010467
# [2018-12-26 17:02:35] [ERROR] error timer = 1, url = https://www.flightclub.com/w-s-air-jordan-8-retro-ice-blue-metallic-silver-orange-blaze-010613
# [2018-12-26 17:02:35] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-w-s-air-max-1-charcoal-sail-gym-red-052013
# [2018-12-26 17:02:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-force1-hi-se-night-maroon-dark-cayenne-gum-medium-brown-805723
# [2018-12-26 17:02:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-force-1-07-lx-particle-beige-805777
# [2018-12-26 17:02:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-force-1-hi-se-elemental-gold-805583
# [2018-12-26 17:02:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-nrg-black-black-white-805692
# [2018-12-26 17:02:40] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-force-1-hi-prm-white-white-metallic-silver-805733
# [2018-12-26 17:02:43] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-hi-phantom-white-805480
# [2018-12-26 17:02:43] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-qs-black-silt-red-summit-white-805301
# [2018-12-26 17:02:43] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-90-lx-mushroom-mushroom-smokey-blue-805272
# [2018-12-26 17:02:43] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-se-tartan-black-black-university-red-805178
# [2018-12-26 17:02:48] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-court-force-hi-sali-wshd-green-cmt-rd-gm-yllw-804718
# [2018-12-26 17:02:48] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-desert-sand-phantom-805085
# [2018-12-26 17:02:48] [ERROR] error timer = 1, url = https://www.flightclub.com/catalog/product/view/id/262990/
# [2018-12-26 17:02:48] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-plus-tn-se-tartan-black-black-university-red-805081
# [2018-12-26 17:02:48] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-trainer-max-91-anthracite-ice-blue-obsidian-805026
# [2018-12-26 17:02:51] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-zoom-fly-sp-white-bright-crimson-sail-804502
# [2018-12-26 17:02:51] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-1-premium-sc-guava-ice-metallic-red-bronze-804665
# [2018-12-26 17:02:51] [ERROR] error timer = 1, url = https://www.flightclub.com/workout-lo-plus-vintage-white-practical-pink-804535
# [2018-12-26 17:02:51] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-plus-tn-se-black-volt-solar-red-804571
# [2018-12-26 17:02:51] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-90-lx-particle-rose-particle-rose-804572
# [2018-12-26 17:02:54] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-max-plus-lx-particle-rose-vast-grey-804440
# [2018-12-26 17:02:54] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-re-low-liftd-mtlc-red-bronze-804220
# [2018-12-26 17:02:54] [ERROR] error timer = 1, url = https://www.flightclub.com/ultra-boost-w-grey-five-carbon-ash-pearl-804487
# [2018-12-26 17:02:54] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-barely-grape-white-804382
# [2018-12-26 17:02:54] [ERROR] error timer = 1, url = https://www.flightclub.com/ultraboost-w-red-night-red-night-core-black-804388
# [2018-12-26 17:02:57] [ERROR] error timer = 1, url = https://www.flightclub.com/air-vapormax-97-mtlc-dark-sea-white-black-804039
# [2018-12-26 17:02:57] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-air-max-90-lx-gunsmoke-gunsmoke-804075
# [2018-12-26 17:02:57] [ERROR] error timer = 1, url = https://www.flightclub.com/nike-wmns-blazer-mid-vintage-suede-blue-803868
# [2018-12-26 17:02:58] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-light-cream-sail-lemon-wash-803929
# [2018-12-26 17:02:58] [ERROR] error timer = 1, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-black-black-dark-grey-803877
# [2018-12-26 17:03:01] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-8-vday-gym-red-ember-glow-team-red-803202
# [2018-12-26 17:03:01] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-4-retro-nrg-fire-red-summit-white-black-805694
# [2018-12-26 17:03:01] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-12-retro-vachetta-tan-metallic-gold-803392
# [2018-12-26 17:03:01] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-11-retros-neutral-olive-mtlc-stout-sail-805670
# [2018-12-26 17:03:01] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-force-1-high-white-white-white-805419
# [2018-12-26 17:03:04] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-high-zip-particle-beige-mtlc-red-bronze-804550
# [2018-12-26 17:03:04] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-re-hi-og-sl-black-black-starfish-sail-803897
# [2018-12-26 17:03:04] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-plus-light-crimson-black-white-805436
# [2018-12-26 17:03:04] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-11-retro-sail-mtlc-red-bronze-803590
# [2018-12-26 17:03:04] [ERROR] error timer = 2, url = https://www.flightclub.com/w-s-air-huarache-run-black-black-801232
# [2018-12-26 17:03:07] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-ash-pearl-chalk-pearl-white-802615
# [2018-12-26 17:03:07] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-utiblk-ftwwht-mgsogr-800675
# [2018-12-26 17:03:07] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-13-retro-phantom-moon-particle-804534
# [2018-12-26 17:03:07] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-3-retro-se-bordeaux-bordeaux-phantom-805066
# [2018-12-26 17:03:08] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-black-light-cream-white-804927
# [2018-12-26 17:03:11] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-3-retro-se-particle-beige-mtlc-red-bronze-804251
# [2018-12-26 17:03:11] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-white-black-university-red-804037
# [2018-12-26 17:03:11] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-plus-lx-dusty-peach-bio-beige-803889
# [2018-12-26 17:03:11] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-95-se-sail-arctic-pink-racer-blue-804584
# [2018-12-26 17:03:11] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-802836
# [2018-12-26 17:03:14] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-white-pink-801145
# [2018-12-26 17:03:14] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-white-052856
# [2018-12-26 17:03:14] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-clear-onix-light-onix-vapour-pink-800411
# [2018-12-26 17:03:14] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-blue-white-801432
# [2018-12-26 17:03:18] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-90-white-court-purple-wolf-grey-805350
# [2018-12-26 17:03:18] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-lebron-xvi-lmtd-sail-white-light-bone-805019
# [2018-12-26 17:03:18] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-lx-white-black-total-orange-804343
# [2018-12-26 17:03:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-black-mint-green-805489
# [2018-12-26 17:03:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-gym-red-gym-red-052807
# [2018-12-26 17:03:21] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-air-vapormax-flyknit-string-chrome-sunset-glow-802784
# [2018-12-26 17:03:21] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-max-1-prm-mtlc-pewter-mtlc-pewter-summit-wht-802914
# [2018-12-26 17:03:21] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-black-black-varsity-royal-804022
# [2018-12-26 17:03:21] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r2-w-linen-linen-ftwwht-802145
# [2018-12-26 17:03:21] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-more-uptempo-dark-stucco-white-black-802794
# [2018-12-26 17:03:24] [ERROR] error timer = 2, url = https://www.flightclub.com/bb2368-maroon-cburgu-ftwwht-802457
# [2018-12-26 17:03:24] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-salmon-800036
# [2018-12-26 17:03:24] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-pk-sea-crystal-turquoise-sea-crystal-800910
# [2018-12-26 17:03:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-pk-shock-pink-core-black-running-white-ftw-800772
# [2018-12-26 17:03:25] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-mystery-blue-mystery-blue-vapour-grey-801987
# [2018-12-26 17:03:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-dark-grey-teal-052764
# [2018-12-26 17:03:28] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-desert-sand-desert-sand-804212
# [2018-12-26 17:03:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-xr1-pk-w-icepur-midgre-ftwwht-800663
# [2018-12-26 17:03:28] [ERROR] error timer = 2, url = https://www.flightclub.com/ultra-boost-w-ash-green-ash-green-real-teal-804645
# [2018-12-26 17:03:28] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-ultra-boost-w-core-black-black-grey-201351
# [2018-12-26 17:03:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-pink-white-gum-803671
# [2018-12-26 17:03:31] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-pearl-pink-pearl-pink-803928
# [2018-12-26 17:03:31] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-hi-prem-black-metallic-gold-803536
# [2018-12-26 17:03:31] [ERROR] error timer = 2, url = https://www.flightclub.com/catalog/product/view/id/232155/
# [2018-12-26 17:03:31] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-green-201035
# [2018-12-26 17:03:34] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-95-white-court-purple-803222
# [2018-12-26 17:03:34] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-xr1-w-white-white-pearl-grey-801270
# [2018-12-26 17:03:34] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-purple-earth-white-803186
# [2018-12-26 17:03:34] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-classic-cortez-leather-white-varsity-red-801434
# [2018-12-26 17:03:34] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-93-white-sport-turq-black-803524
# [2018-12-26 17:03:37] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-summit-white-mtlc-red-bronze-801680
# [2018-12-26 17:03:37] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-x-parley-w-night-navy-intense-blue-800938
# [2018-12-26 17:03:37] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-sock-dart-prm-black-white-black-800766
# [2018-12-26 17:03:37] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-xr1-w-drkbur-drkbur-vappnk-802997
# [2018-12-26 17:03:37] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r2-w-wonpnk-wonpnk-cblack-801683
# [2018-12-26 17:03:40] [ERROR] error timer = 2, url = https://www.flightclub.com/iniki-runner-w-purple-white-cream-800646
# [2018-12-26 17:03:40] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-vapour-pink-light-onix-800410
# [2018-12-26 17:03:40] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-red-201385
# [2018-12-26 17:03:40] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-plus-qs-metallic-gold-university-red-801048
# [2018-12-26 17:03:40] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-presto-flyknit-ultra-hyper-turq-hyper-turq-053029
# [2018-12-26 17:03:43] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-white-black-wolf-grey-805083
# [2018-12-26 17:03:43] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-pink-black-white-800368
# [2018-12-26 17:03:44] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-grey-mtllc-silver-201364
# [2018-12-26 17:03:44] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-force-1-07-se-black-wheat-gold-805400
# [2018-12-26 17:03:44] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-binary-blue-binary-blue-black-800256
# [2018-12-26 17:03:47] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-5-white-fire-red-sunset-dark-cinder-010743
# [2018-12-26 17:03:47] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-trace-scarlet-trace-scarlet-running-white-804437
# [2018-12-26 17:03:47] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-grey-blue-804472
# [2018-12-26 17:03:47] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-black-tactile-rose-bold-red-804324
# [2018-12-26 17:03:47] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-raw-pink-white-201307
# [2018-12-26 17:03:50] [ERROR] error timer = 2, url = https://www.flightclub.com/catalog/product/view/id/242350/
# [2018-12-26 17:03:50] [ERROR] error timer = 2, url = https://www.flightclub.com/catalog/product/view/id/243219/
# [2018-12-26 17:03:50] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-red-black-804187
# [2018-12-26 17:03:50] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-gold-black-804006
# [2018-12-26 17:03:50] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-lx-total-orange-white-black-804430
# [2018-12-26 17:03:53] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-ash-pearl-ash-pearl-ash-pearl-803574
# [2018-12-26 17:03:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-high-zip-white-white-university-red-803772
# [2018-12-26 17:03:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-light-aqua-white-metallic-gold-803146
# [2018-12-26 17:03:53] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-air-more-uptempo-white-chrome-blue-tint-803139
# [2018-12-26 17:03:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-plum-fog-plum-fog-803279
# [2018-12-26 17:03:56] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-volt-802753
# [2018-12-26 17:03:56] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-midnight-fog-multi-color-black-802785
# [2018-12-26 17:03:56] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-sol-sunblush-white-metallic-gold-803145
# [2018-12-26 17:03:56] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-white-white-sail-light-bone-803067
# [2018-12-26 17:03:56] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-ice-peach-white-metallic-gold-803147
# [2018-12-26 17:03:59] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-black-black-white-racer-blue-802551
# [2018-12-26 17:03:59] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-xr1-pk-w-utiivy-utiivy-corred-802928
# [2018-12-26 17:03:59] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-footscape-woven-sail-white-red-stardust-802444
# [2018-12-26 17:03:59] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-metallic-silver-802634
# [2018-12-26 17:03:59] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-black-carbon-running-white-802681
# [2018-12-26 17:04:02] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-bordeaux-tea-berry-black-802338
# [2018-12-26 17:04:02] [ERROR] error timer = 2, url = https://www.flightclub.com/womens-roshe-one-black-black-dark-grey-802319
# [2018-12-26 17:04:02] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-90-prm-db-white-black-dynamic-yellow-801898
# [2018-12-26 17:04:02] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-raw-pink-trace-pink-legend-ink-801864
# [2018-12-26 17:04:03] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-huarache-run-prm-txt-mahogany-mtlc-mahogany-802276
# [2018-12-26 17:04:06] [ERROR] error timer = 2, url = https://www.flightclub.com/w-s-air-huarache-run-max-orange-cool-grey-801387
# [2018-12-26 17:04:06] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-black-white-801450
# [2018-12-26 17:04:06] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r2-w-clear-granite-vintage-white-801272
# [2018-12-26 17:04:06] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-huarache-run-dusted-clay-white-gum-yellow-801401
# [2018-12-26 17:04:06] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-plus-se-white-white-black-801882
# [2018-12-26 17:04:09] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-grey-grey-801431
# [2018-12-26 17:04:09] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-hurache-run-sport-fuchsia-white-gum-yellow-801071
# [2018-12-26 17:04:09] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-cs2-pk-w-peagre-peagre-ftw-801098
# [2018-12-26 17:04:09] [ERROR] error timer = 2, url = https://www.flightclub.com/iniki-runner-w-pink-blue-gum-801246
# [2018-12-26 17:04:09] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-huarache-run-ember-glow-dark-cayenne-white-801233
# [2018-12-26 17:04:12] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-cs2-pk-w-tragrn-tragrn-trapnk-801240
# [2018-12-26 17:04:12] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-zero-white-black-800987
# [2018-12-26 17:04:12] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-toki-slip-canvas-white-white-800992
# [2018-12-26 17:04:12] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-90-white-white-wolf-grey-black-801021
# [2018-12-26 17:04:12] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-white-white-white-801004
# [2018-12-26 17:04:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-pk-green-pink-green-800909
# [2018-12-26 17:04:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-black-blue-801055
# [2018-12-26 17:04:15] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-dark-grey-black-wolf-grey-800867
# [2018-12-26 17:04:15] [ERROR] error timer = 2, url = https://www.flightclub.com/w-s-air-huarache-run-anthracite-oatmeal-cool-grey-800851
# [2018-12-26 17:04:15] [ERROR] error timer = 2, url = https://www.flightclub.com/air-max-zero-wolf-grey-wolf-grey-white-800986
# [2018-12-26 17:04:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-pk-black-pink-white-800788
# [2018-12-26 17:04:18] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-white-wolf-grey-800731
# [2018-12-26 17:04:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r2-w-olive-white-800736
# [2018-12-26 17:04:18] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-pinnacle-silt-red-silt-red-sail-800897
# [2018-12-26 17:04:19] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-classic-cortez-str-ltr-black-black-black-800764
# [2018-12-26 17:04:22] [ERROR] error timer = 2, url = https://www.flightclub.com/iniki-runner-w-orange-white-gum-800845
# [2018-12-26 17:04:22] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-white-grey-800653
# [2018-12-26 17:04:22] [ERROR] error timer = 2, url = https://www.flightclub.com/iniki-runner-w-mint-white-gum-800645
# [2018-12-26 17:04:22] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-r1-w-grey-white-800601
# [2018-12-26 17:04:22] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-university-red-800690
# [2018-12-26 17:04:25] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-owhite-800325
# [2018-12-26 17:04:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-desert-ochre-desert-ochre-800257
# [2018-12-26 17:04:25] [ERROR] error timer = 2, url = https://www.flightclub.com/ultra-boost-w-black-black-met-800211
# [2018-12-26 17:04:25] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-xr1-w-midgre-nobink-grey-800338
# [2018-12-26 17:04:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-cs2-pk-w-conavy-conavy-ftwwht-800689
# [2018-12-26 17:04:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-se-mtlc-red-bronze-elm-053083
# [2018-12-26 17:04:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-rl-w-black-sand-white-800062
# [2018-12-26 17:04:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-huarache-run-se-mtlc-dark-sea-midnight-turq-053228
# [2018-12-26 17:04:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nmd-xr1-w-vapgre-icepur-owhite-800008
# [2018-12-26 17:04:28] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-white-teal-sand-201550
# [2018-12-26 17:04:31] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-tubular-viral-w-metsil-cgrani-cwhite-201506
# [2018-12-26 17:04:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-light-bone-light-bone-sail-021538
# [2018-12-26 17:04:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-linen-linen-gum-lt-brown-053063
# [2018-12-26 17:04:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-force-1-hi-prm-flax-flax-outdoor-green-021534
# [2018-12-26 17:04:32] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmdxr1-pk-w-pink-white-201535
# [2018-12-26 17:04:35] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-white-white-201418
# [2018-12-26 17:04:35] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-navy-white-bergundy-201503
# [2018-12-26 17:04:35] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-blue-white-201365
# [2018-12-26 17:04:35] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-black-white-201408
# [2018-12-26 17:04:35] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-space-pink-challenge-red-space-pink-052760
# [2018-12-26 17:04:38] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-blanch-purple-white-201259
# [2018-12-26 17:04:38] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-unity-blue-collegiate-navy-vivid-red-201414
# [2018-12-26 17:04:38] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-anniversary-bronze-black-infrared-white-052624
# [2018-12-26 17:04:38] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-black-pink-201224
# [2018-12-26 17:04:38] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-pink-blast-white-052980
# [2018-12-26 17:04:41] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-beige-beige-white-201285
# [2018-12-26 17:04:41] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-og-white-cool-grey-ntrl-grey-blk-052656
# [2018-12-26 17:04:41] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-zx-flux-w-cblack-cblack-coppmt-201377
# [2018-12-26 17:04:41] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-grey-white-pink-201401
# [2018-12-26 17:04:41] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-sunset-gold-dart-white-black-053036
# [2018-12-26 17:04:44] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-atomic-pink-atomic-pink-052974
# [2018-12-26 17:04:44] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-052692
# [2018-12-26 17:04:44] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-presto-ttl-crmsn-brght-crmsn-wht-blck-053016
# [2018-12-26 17:04:44] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-essential-wolf-grey-infrared-black-white-053022
# [2018-12-26 17:04:44] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-island-green-islnd-grn-ftl-gld-052959
# [2018-12-26 17:04:47] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-black-black-mtllc-gold-white-052919
# [2018-12-26 17:04:47] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-rdnt-emrld-sprt-fchs-smm-052966
# [2018-12-26 17:04:47] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-ultra-boost-w-white-white-201180
# [2018-12-26 17:04:48] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-bronzine-bronzine-sail-black-052450
# [2018-12-26 17:04:48] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-cool-grey-052759
# [2018-12-26 17:04:50] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-qs-viola-fushia-glow-chilling-red-052763
# [2018-12-26 17:04:51] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-loyal-blue-loyal-blue-052879
# [2018-12-26 17:04:51] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-white-white-052603
# [2018-12-26 17:04:51] [ERROR] error timer = 2, url = https://www.flightclub.com/womens-air-jordan-3-retro-white-harbor-blue-boarder-blue-010536
# [2018-12-26 17:04:51] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-anniversary-gym-red-black-infrrd-mtllc-gld-052596
# [2018-12-26 17:04:54] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-blue-legend-blue-legend-052625
# [2018-12-26 17:04:54] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-pure-platinum-052664
# [2018-12-26 17:04:54] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-prm-mtlc-gold-silk-blck-clssc-brwn-051857
# [2018-12-26 17:04:54] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-hot-lava-hot-lava-052613
# [2018-12-26 17:04:54] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-white-052455
# [2018-12-26 17:04:57] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-lib-qs-dp-brgndy-dp-brgndy-brght-mng-052420
# [2018-12-26 17:04:57] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-university-red-maroon-white-800191
# [2018-12-26 17:04:57] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-vntg-sail-hypr-rd-strt-gry-icd-crmn-051833
# [2018-12-26 17:04:57] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-lyon-blue-lyn-bl-smmt-wht-blk-052580
# [2018-12-26 17:04:57] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-blue-spark-coastel-blue-white-800190
# [2018-12-26 17:05:00] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-obsidian-obsidian-phantom-053216
# [2018-12-26 17:05:00] [ERROR] error timer = 2, url = https://www.flightclub.com/w-s-air-jordan-7-retro-white-varsity-maize-black-010314
# [2018-12-26 17:05:00] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-dk-electric-blu-clrwtr-white-053183
# [2018-12-26 17:05:00] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-ultra-boost-uncage-w-teal-white-201428
# [2018-12-26 17:05:00] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-mayfly-woven-black-dark-grey-white-090189
# [2018-12-26 17:05:03] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-ultra-lotc-qs-ink-ink-summit-white-team-red-052612
# [2018-12-26 17:05:03] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-black-white-201242
# [2018-12-26 17:05:03] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-pinnacle-black-black-sail-052970
# [2018-12-26 17:05:04] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-blanch-blue-collegiate-navy-201304
# [2018-12-26 17:05:05] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-black-black-sail-052971
# [2018-12-26 17:05:08] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-roshe-one-flyknit-gym-red-brght-crimson-tm-rd-sl-052934
# [2018-12-26 17:05:08] [ERROR] error timer = 2, url = https://www.flightclub.com/adidas-nmd-r1-w-white-blue-lt-blu-201240
# [2018-12-26 17:05:08] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-dp-royal-vlt-blk-pr-pltnm-052924
# [2018-12-26 17:05:08] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-hot-lava-bl-legend-white-052609
# [2018-12-26 17:05:09] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-black-smmt-wht-052588
# [2018-12-26 17:05:12] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-flyknit-zoom-agility-black-white-elctrc-grn-pnk-pw-052535
# [2018-12-26 17:05:12] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-essential-white-black-052871
# [2018-12-26 17:05:12] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-obsidian-obsidian-black-052568
# [2018-12-26 17:05:12] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-menta-hot-lava-052437
# [2018-12-26 17:05:12] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-brnzn-smmt-wht-mtllc-gld-052586
# [2018-12-26 17:05:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-chllng-rd-chllg-rd-smmt-wht-b-052600
# [2018-12-26 17:05:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-university-red-tr-yllw-sl-blck-052638
# [2018-12-26 17:05:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-cinnabar-lsr-orng-fbrlss-blk-052661
# [2018-12-26 17:05:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-lsr-crimson-lsr-crmsn-blk-vlt-052174
# [2018-12-26 17:05:15] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-lt-retro-sail-blk-052589
# [2018-12-26 17:05:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-artisan-teal-sail-black-052597
# [2018-12-26 17:05:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-volt-volt-obsidian-052571
# [2018-12-26 17:05:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-mtllc-slvr-strng-snst-glw-grn-052723
# [2018-12-26 17:05:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-essential-black-gym-red-sail-gm-md-brown-052780
# [2018-12-26 17:05:18] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-grey-mint-052584
# [2018-12-26 17:05:21] [ERROR] error timer = 2, url = https://www.flightclub.com/w-s-air-jordan-8-retro-white-varsity-red-bright-concord-aqua-tone-010598
# [2018-12-26 17:05:21] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-court-purple-violet-wash-volt-051798
# [2018-12-26 17:05:21] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-white-white-wolf-grey-volt-052567
# [2018-12-26 17:05:21] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-blue-force-blue-force-sail-052491
# [2018-12-26 17:05:22] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-nike-rosherun-white-mtlc-platinum-052556
# [2018-12-26 17:05:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-hyper-crimson-space-blue-052466
# [2018-12-26 17:05:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-black-black-anthracite-052359
# [2018-12-26 17:05:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-volt-light-bone-052322
# [2018-12-26 17:05:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-force-one-hi-prm-qs-white-white-metallic-silver-021413
# [2018-12-26 17:05:25] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-lib-qs-blue-recall-white-lnn-atmc-mng-052408
# [2018-12-26 17:05:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-roshe-run-hyp-bright-mango-dk-magnet-grey-052299
# [2018-12-26 17:05:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-print-anthracite-black-anthrct-vlt-052340
# [2018-12-26 17:05:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-fv-qs-black-volt-white-052315
# [2018-12-26 17:05:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-vlt-sh-vlt-shd-lsr-crmsn-vlt-052215
# [2018-12-26 17:05:28] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-prm-ivry-mtlc-gld-cn-hypr-pnch-gm-052235
# [2018-12-26 17:05:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-woven-qs-tropical-twist-white-white-052069
# [2018-12-26 17:05:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-sp-obsidian-tropical-teal-volt-052112
# [2018-12-26 17:05:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-cut-out-prm-mtlc-rd-brnz-mtlc-rd-brnz-lght-052280
# [2018-12-26 17:05:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-pwm-n7-black-black-summit-white-dark-turquoise-052097
# [2018-12-26 17:05:31] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-vt-qs-black-sail-052190
# [2018-12-26 17:05:35] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-rosherun-total-crimson-sail-brght-ctrs-051890
# [2018-12-26 17:05:35] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-womens-air-max-97-vrsty-red-vrsty-red-white-050484
# [2018-12-26 17:05:40] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-womens-air-max-90-classic-white-asian-concord-lz-pink-light-zen-grey-050337
# [2018-12-26 17:05:45] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-force-1-supreme-black-black-engine-1-laser-pink-020954
# [2018-12-26 17:05:45] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-womens-dunk-low-premium-celery-papaya-med-mint-varsity-red-030338
# [2018-12-26 17:05:50] [ERROR] error timer = 2, url = https://www.flightclub.com/w-s-air-jordan-8-retro-ice-blue-metallic-silver-orange-blaze-010613
# [2018-12-26 17:05:50] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-w-s-air-max-1-charcoal-sail-gym-red-052013
# [2018-12-26 17:05:50] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-force-1-07-lx-particle-beige-805777
# [2018-12-26 17:05:50] [ERROR] error timer = 2, url = https://www.flightclub.com/womens-air-jordan-4-retro-white-border-blue-light-sand-010467
# [2018-12-26 17:05:50] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-force1-hi-se-night-maroon-dark-cayenne-gum-medium-brown-805723
# [2018-12-26 17:05:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-force-1-hi-se-elemental-gold-805583
# [2018-12-26 17:05:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-force-1-hi-prm-white-white-metallic-silver-805733
# [2018-12-26 17:05:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-hi-phantom-white-805480
# [2018-12-26 17:05:53] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-nrg-black-black-white-805692
# [2018-12-26 17:05:54] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-qs-black-silt-red-summit-white-805301
# [2018-12-26 17:05:57] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-90-lx-mushroom-mushroom-smokey-blue-805272
# [2018-12-26 17:05:57] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-desert-sand-phantom-805085
# [2018-12-26 17:05:57] [ERROR] error timer = 2, url = https://www.flightclub.com/catalog/product/view/id/262990/
# [2018-12-26 17:05:57] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-court-force-hi-sali-wshd-green-cmt-rd-gm-yllw-804718
# [2018-12-26 17:05:57] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-se-tartan-black-black-university-red-805178
# [2018-12-26 17:06:00] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-zoom-fly-sp-white-bright-crimson-sail-804502
# [2018-12-26 17:06:00] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-plus-tn-se-tartan-black-black-university-red-805081
# [2018-12-26 17:06:00] [ERROR] error timer = 2, url = https://www.flightclub.com/workout-lo-plus-vintage-white-practical-pink-804535
# [2018-12-26 17:06:00] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-1-premium-sc-guava-ice-metallic-red-bronze-804665
# [2018-12-26 17:06:00] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-trainer-max-91-anthracite-ice-blue-obsidian-805026
# [2018-12-26 17:06:03] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-plus-tn-se-black-volt-solar-red-804571
# [2018-12-26 17:06:03] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-max-plus-lx-particle-rose-vast-grey-804440
# [2018-12-26 17:06:03] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-re-low-liftd-mtlc-red-bronze-804220
# [2018-12-26 17:06:03] [ERROR] error timer = 2, url = https://www.flightclub.com/ultra-boost-w-grey-five-carbon-ash-pearl-804487
# [2018-12-26 17:06:03] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-90-lx-particle-rose-particle-rose-804572
# [2018-12-26 17:06:06] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-barely-grape-white-804382
# [2018-12-26 17:06:06] [ERROR] error timer = 2, url = https://www.flightclub.com/ultraboost-w-red-night-red-night-core-black-804388
# [2018-12-26 17:06:06] [ERROR] error timer = 2, url = https://www.flightclub.com/air-vapormax-97-mtlc-dark-sea-white-black-804039
# [2018-12-26 17:06:06] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-air-max-90-lx-gunsmoke-gunsmoke-804075
# [2018-12-26 17:06:06] [ERROR] error timer = 2, url = https://www.flightclub.com/nike-wmns-blazer-mid-vintage-suede-blue-803868
# [2018-12-26 17:06:09] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-black-black-dark-grey-803877
# [2018-12-26 17:06:09] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-4-retro-nrg-fire-red-summit-white-black-805694
# [2018-12-26 17:06:09] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-8-vday-gym-red-ember-glow-team-red-803202
# [2018-12-26 17:06:09] [ERROR] error timer = 2, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-light-cream-sail-lemon-wash-803929
# [2018-12-26 17:06:11] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-12-retro-vachetta-tan-metallic-gold-803392
# [2018-12-26 17:06:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-plus-light-crimson-black-white-805436
# [2018-12-26 17:06:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-force-1-high-white-white-white-805419
# [2018-12-26 17:06:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-re-hi-og-sl-black-black-starfish-sail-803897
# [2018-12-26 17:06:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-11-retros-neutral-olive-mtlc-stout-sail-805670
# [2018-12-26 17:06:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-high-zip-particle-beige-mtlc-red-bronze-804550
# [2018-12-26 17:06:17] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-13-retro-phantom-moon-particle-804534
# [2018-12-26 17:06:17] [ERROR] error timer = 3, url = https://www.flightclub.com/w-s-air-huarache-run-black-black-801232
# [2018-12-26 17:06:17] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-ash-pearl-chalk-pearl-white-802615
# [2018-12-26 17:06:17] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-11-retro-sail-mtlc-red-bronze-803590
# [2018-12-26 17:06:17] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-utiblk-ftwwht-mgsogr-800675
# [2018-12-26 17:06:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-3-retro-se-particle-beige-mtlc-red-bronze-804251
# [2018-12-26 17:06:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-3-retro-se-bordeaux-bordeaux-phantom-805066
# [2018-12-26 17:06:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-black-light-cream-white-804927
# [2018-12-26 17:06:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-plus-lx-dusty-peach-bio-beige-803889
# [2018-12-26 17:06:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-white-black-university-red-804037
# [2018-12-26 17:06:24] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-clear-onix-light-onix-vapour-pink-800411
# [2018-12-26 17:06:24] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-95-se-sail-arctic-pink-racer-blue-804584
# [2018-12-26 17:06:24] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-white-052856
# [2018-12-26 17:06:24] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-white-pink-801145
# [2018-12-26 17:06:24] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-802836
# [2018-12-26 17:06:27] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-90-white-court-purple-wolf-grey-805350
# [2018-12-26 17:06:27] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-lx-white-black-total-orange-804343
# [2018-12-26 17:06:27] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-black-mint-green-805489
# [2018-12-26 17:06:27] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-blue-white-801432
# [2018-12-26 17:06:28] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-lebron-xvi-lmtd-sail-white-light-bone-805019
# [2018-12-26 17:06:31] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r2-w-linen-linen-ftwwht-802145
# [2018-12-26 17:06:31] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-gym-red-gym-red-052807
# [2018-12-26 17:06:31] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-vapormax-flyknit-string-chrome-sunset-glow-802784
# [2018-12-26 17:06:31] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-max-1-prm-mtlc-pewter-mtlc-pewter-summit-wht-802914
# [2018-12-26 17:06:33] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-black-black-varsity-royal-804022
# [2018-12-26 17:06:36] [ERROR] error timer = 3, url = https://www.flightclub.com/bb2368-maroon-cburgu-ftwwht-802457
# [2018-12-26 17:06:36] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-pk-shock-pink-core-black-running-white-ftw-800772
# [2018-12-26 17:06:36] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-more-uptempo-dark-stucco-white-black-802794
# [2018-12-26 17:06:36] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-pk-sea-crystal-turquoise-sea-crystal-800910
# [2018-12-26 17:06:36] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-salmon-800036
# [2018-12-26 17:06:39] [ERROR] error timer = 3, url = https://www.flightclub.com/ultra-boost-w-ash-green-ash-green-real-teal-804645
# [2018-12-26 17:06:39] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-dark-grey-teal-052764
# [2018-12-26 17:06:39] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-mystery-blue-mystery-blue-vapour-grey-801987
# [2018-12-26 17:06:39] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-desert-sand-desert-sand-804212
# [2018-12-26 17:06:39] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-xr1-pk-w-icepur-midgre-ftwwht-800663
# [2018-12-26 17:06:42] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/232155/
# [2018-12-26 17:06:42] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-hi-prem-black-metallic-gold-803536
# [2018-12-26 17:06:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-pink-white-gum-803671
# [2018-12-26 17:06:42] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-ultra-boost-w-core-black-black-grey-201351
# [2018-12-26 17:06:42] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-pearl-pink-pearl-pink-803928
# [2018-12-26 17:06:45] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-purple-earth-white-803186
# [2018-12-26 17:06:45] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-xr1-w-white-white-pearl-grey-801270
# [2018-12-26 17:06:46] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-classic-cortez-leather-white-varsity-red-801434
# [2018-12-26 17:06:46] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-95-white-court-purple-803222
# [2018-12-26 17:06:46] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-green-201035
# [2018-12-26 17:06:49] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-93-white-sport-turq-black-803524
# [2018-12-26 17:06:49] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-summit-white-mtlc-red-bronze-801680
# [2018-12-26 17:06:49] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-x-parley-w-night-navy-intense-blue-800938
# [2018-12-26 17:06:49] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-sock-dart-prm-black-white-black-800766
# [2018-12-26 17:06:49] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-xr1-w-drkbur-drkbur-vappnk-802997
# [2018-12-26 17:06:52] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-plus-qs-metallic-gold-university-red-801048
# [2018-12-26 17:06:52] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r2-w-wonpnk-wonpnk-cblack-801683
# [2018-12-26 17:06:52] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-vapour-pink-light-onix-800410
# [2018-12-26 17:06:52] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-red-201385
# [2018-12-26 17:06:52] [ERROR] error timer = 3, url = https://www.flightclub.com/iniki-runner-w-purple-white-cream-800646
# [2018-12-26 17:06:55] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-white-black-wolf-grey-805083
# [2018-12-26 17:06:55] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-force-1-07-se-black-wheat-gold-805400
# [2018-12-26 17:06:55] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-pink-black-white-800368
# [2018-12-26 17:06:55] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-grey-mtllc-silver-201364
# [2018-12-26 17:06:55] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-presto-flyknit-ultra-hyper-turq-hyper-turq-053029
# [2018-12-26 17:06:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-black-tactile-rose-bold-red-804324
# [2018-12-26 17:06:58] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-5-white-fire-red-sunset-dark-cinder-010743
# [2018-12-26 17:06:58] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-grey-blue-804472
# [2018-12-26 17:06:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-trace-scarlet-trace-scarlet-running-white-804437
# [2018-12-26 17:06:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-binary-blue-binary-blue-black-800256
# [2018-12-26 17:07:01] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/242350/
# [2018-12-26 17:07:01] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-raw-pink-white-201307
# [2018-12-26 17:07:01] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-red-black-804187
# [2018-12-26 17:07:02] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-gold-black-804006
# [2018-12-26 17:07:02] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/243219/
# [2018-12-26 17:07:05] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-lx-total-orange-white-black-804430
# [2018-12-26 17:07:05] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-ash-pearl-ash-pearl-ash-pearl-803574
# [2018-12-26 17:07:05] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-high-zip-white-white-university-red-803772
# [2018-12-26 17:07:05] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-air-more-uptempo-white-chrome-blue-tint-803139
# [2018-12-26 17:07:05] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-light-aqua-white-metallic-gold-803146
# [2018-12-26 17:07:08] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-sol-sunblush-white-metallic-gold-803145
# [2018-12-26 17:07:08] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-plum-fog-plum-fog-803279
# [2018-12-26 17:07:08] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-midnight-fog-multi-color-black-802785
# [2018-12-26 17:07:08] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-volt-802753
# [2018-12-26 17:07:08] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-white-white-sail-light-bone-803067
# [2018-12-26 17:07:11] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-ice-peach-white-metallic-gold-803147
# [2018-12-26 17:07:11] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-black-black-white-racer-blue-802551
# [2018-12-26 17:07:11] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-xr1-pk-w-utiivy-utiivy-corred-802928
# [2018-12-26 17:07:11] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-footscape-woven-sail-white-red-stardust-802444
# [2018-12-26 17:07:11] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-metallic-silver-802634
# [2018-12-26 17:07:14] [ERROR] error timer = 3, url = https://www.flightclub.com/womens-roshe-one-black-black-dark-grey-802319
# [2018-12-26 17:07:14] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-black-carbon-running-white-802681
# [2018-12-26 17:07:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-90-prm-db-white-black-dynamic-yellow-801898
# [2018-12-26 17:07:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-bordeaux-tea-berry-black-802338
# [2018-12-26 17:07:14] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-raw-pink-trace-pink-legend-ink-801864
# [2018-12-26 17:07:18] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-black-white-801450
# [2018-12-26 17:07:18] [ERROR] error timer = 3, url = https://www.flightclub.com/w-s-air-huarache-run-max-orange-cool-grey-801387
# [2018-12-26 17:07:18] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-huarache-run-prm-txt-mahogany-mtlc-mahogany-802276
# [2018-12-26 17:07:18] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-huarache-run-dusted-clay-white-gum-yellow-801401
# [2018-12-26 17:07:18] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r2-w-clear-granite-vintage-white-801272
# [2018-12-26 17:07:21] [ERROR] error timer = 3, url = https://www.flightclub.com/iniki-runner-w-pink-blue-gum-801246
# [2018-12-26 17:07:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-plus-se-white-white-black-801882
# [2018-12-26 17:07:21] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-cs2-pk-w-peagre-peagre-ftw-801098
# [2018-12-26 17:07:21] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-hurache-run-sport-fuchsia-white-gum-yellow-801071
# [2018-12-26 17:07:21] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-grey-grey-801431
# [2018-12-26 17:07:24] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-zero-white-black-800987
# [2018-12-26 17:07:24] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-huarache-run-ember-glow-dark-cayenne-white-801233
# [2018-12-26 17:07:24] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-toki-slip-canvas-white-white-800992
# [2018-12-26 17:07:24] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-90-white-white-wolf-grey-black-801021
# [2018-12-26 17:07:26] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-cs2-pk-w-tragrn-tragrn-trapnk-801240
# [2018-12-26 17:07:29] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-dark-grey-black-wolf-grey-800867
# [2018-12-26 17:07:29] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-white-white-white-801004
# [2018-12-26 17:07:29] [ERROR] error timer = 3, url = https://www.flightclub.com/w-s-air-huarache-run-anthracite-oatmeal-cool-grey-800851
# [2018-12-26 17:07:29] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-black-blue-801055
# [2018-12-26 17:07:29] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-pk-green-pink-green-800909
# [2018-12-26 17:07:32] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r2-w-olive-white-800736
# [2018-12-26 17:07:32] [ERROR] error timer = 3, url = https://www.flightclub.com/air-max-zero-wolf-grey-wolf-grey-white-800986
# [2018-12-26 17:07:32] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-pk-black-pink-white-800788
# [2018-12-26 17:07:32] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-white-wolf-grey-800731
# [2018-12-26 17:07:32] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-pinnacle-silt-red-silt-red-sail-800897
# [2018-12-26 17:07:35] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-r1-w-grey-white-800601
# [2018-12-26 17:07:35] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-classic-cortez-str-ltr-black-black-black-800764
# [2018-12-26 17:07:35] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-white-grey-800653
# [2018-12-26 17:07:35] [ERROR] error timer = 3, url = https://www.flightclub.com/iniki-runner-w-orange-white-gum-800845
# [2018-12-26 17:07:35] [ERROR] error timer = 3, url = https://www.flightclub.com/iniki-runner-w-mint-white-gum-800645
# [2018-12-26 17:07:38] [ERROR] error timer = 3, url = https://www.flightclub.com/ultra-boost-w-black-black-met-800211
# [2018-12-26 17:07:38] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-xr1-w-midgre-nobink-grey-800338
# [2018-12-26 17:07:38] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-desert-ochre-desert-ochre-800257
# [2018-12-26 17:07:39] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-university-red-800690
# [2018-12-26 17:07:39] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-owhite-800325
# [2018-12-26 17:07:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-rl-w-black-sand-white-800062
# [2018-12-26 17:07:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-xr1-w-vapgre-icepur-owhite-800008
# [2018-12-26 17:07:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-se-mtlc-red-bronze-elm-053083
# [2018-12-26 17:07:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-huarache-run-se-mtlc-dark-sea-midnight-turq-053228
# [2018-12-26 17:07:42] [ERROR] error timer = 3, url = https://www.flightclub.com/nmd-cs2-pk-w-conavy-conavy-ftwwht-800689
# [2018-12-26 17:07:45] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-white-teal-sand-201550
# [2018-12-26 17:07:45] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-tubular-viral-w-metsil-cgrani-cwhite-201506
# [2018-12-26 17:07:45] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-force-1-hi-prm-flax-flax-outdoor-green-021534
# [2018-12-26 17:07:45] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-sf-air-force-one-high-light-bone-light-bone-sail-021538
# [2018-12-26 17:07:45] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-linen-linen-gum-lt-brown-053063
# [2018-12-26 17:07:48] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-blue-white-201365
# [2018-12-26 17:07:48] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmdxr1-pk-w-pink-white-201535
# [2018-12-26 17:07:48] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-white-white-201418
# [2018-12-26 17:07:48] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-black-white-201408
# [2018-12-26 17:07:48] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-navy-white-bergundy-201503
# [2018-12-26 17:07:51] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-blanch-purple-white-201259
# [2018-12-26 17:07:51] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-black-pink-201224
# [2018-12-26 17:07:51] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-anniversary-bronze-black-infrared-white-052624
# [2018-12-26 17:07:52] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-unity-blue-collegiate-navy-vivid-red-201414
# [2018-12-26 17:07:52] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-space-pink-challenge-red-space-pink-052760
# [2018-12-26 17:07:55] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-og-white-cool-grey-ntrl-grey-blk-052656
# [2018-12-26 17:07:55] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-beige-beige-white-201285
# [2018-12-26 17:07:55] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-pink-blast-white-052980
# [2018-12-26 17:07:55] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-zx-flux-w-cblack-cblack-coppmt-201377
# [2018-12-26 17:07:55] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-xr1-pk-w-grey-white-pink-201401
# [2018-12-26 17:07:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-atomic-pink-atomic-pink-052974
# [2018-12-26 17:07:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-sunset-gold-dart-white-black-053036
# [2018-12-26 17:07:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-052692
# [2018-12-26 17:07:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-presto-ttl-crmsn-brght-crmsn-wht-blck-053016
# [2018-12-26 17:07:58] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-essential-wolf-grey-infrared-black-white-053022
# [2018-12-26 17:08:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-island-green-islnd-grn-ftl-gld-052959
# [2018-12-26 17:08:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-black-black-mtllc-gold-white-052919
# [2018-12-26 17:08:01] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-ultra-boost-w-white-white-201180
# [2018-12-26 17:08:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-rdnt-emrld-sprt-fchs-smm-052966
# [2018-12-26 17:08:01] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-bronzine-bronzine-sail-black-052450
# [2018-12-26 17:08:04] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-white-white-052603
# [2018-12-26 17:08:04] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-cool-grey-052759
# [2018-12-26 17:08:04] [ERROR] error timer = 3, url = https://www.flightclub.com/womens-air-jordan-3-retro-white-harbor-blue-boarder-blue-010536
# [2018-12-26 17:08:04] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-qs-viola-fushia-glow-chilling-red-052763
# [2018-12-26 17:08:04] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-loyal-blue-loyal-blue-052879
# [2018-12-26 17:08:07] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-blue-legend-blue-legend-052625
# [2018-12-26 17:08:07] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-hot-lava-hot-lava-052613
# [2018-12-26 17:08:08] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-anniversary-gym-red-black-infrrd-mtllc-gld-052596
# [2018-12-26 17:08:08] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-prm-mtlc-gold-silk-blck-clssc-brwn-051857
# [2018-12-26 17:08:08] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-pure-platinum-052664
# [2018-12-26 17:08:11] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-lyon-blue-lyn-bl-smmt-wht-blk-052580
# [2018-12-26 17:08:11] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-university-red-maroon-white-800191
# [2018-12-26 17:08:11] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-white-052455
# [2018-12-26 17:08:11] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-vntg-sail-hypr-rd-strt-gry-icd-crmn-051833
# [2018-12-26 17:08:13] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-lib-qs-dp-brgndy-dp-brgndy-brght-mng-052420
# [2018-12-26 17:08:16] [ERROR] error timer = 3, url = https://www.flightclub.com/w-s-air-jordan-7-retro-white-varsity-maize-black-010314
# [2018-12-26 17:08:16] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-obsidian-obsidian-phantom-053216
# [2018-12-26 17:08:16] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-ultra-boost-uncage-w-teal-white-201428
# [2018-12-26 17:08:16] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-dk-electric-blu-clrwtr-white-053183
# [2018-12-26 17:08:16] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-blue-spark-coastel-blue-white-800190
# [2018-12-26 17:08:19] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-black-white-201242
# [2018-12-26 17:08:19] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-mayfly-woven-black-dark-grey-white-090189
# [2018-12-26 17:08:20] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-ultra-lotc-qs-ink-ink-summit-white-team-red-052612
# [2018-12-26 17:08:20] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-blanch-blue-collegiate-navy-201304
# [2018-12-26 17:08:20] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-pinnacle-black-black-sail-052970
# [2018-12-26 17:08:23] [ERROR] error timer = 3, url = https://www.flightclub.com/adidas-nmd-r1-w-white-blue-lt-blu-201240
# [2018-12-26 17:08:23] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-white-hot-lava-bl-legend-white-052609
# [2018-12-26 17:08:23] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-black-black-sail-052971
# [2018-12-26 17:08:23] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-roshe-one-flyknit-gym-red-brght-crimson-tm-rd-sl-052934
# [2018-12-26 17:08:23] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-dp-royal-vlt-blk-pr-pltnm-052924
# [2018-12-26 17:08:26] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-flyknit-zoom-agility-black-white-elctrc-grn-pnk-pw-052535
# [2018-12-26 17:08:26] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-menta-hot-lava-052437
# [2018-12-26 17:08:26] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-obsidian-obsidian-black-052568
# [2018-12-26 17:08:26] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-black-smmt-wht-052588
# [2018-12-26 17:08:26] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-essential-white-black-052871
# [2018-12-26 17:08:29] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-brnzn-smmt-wht-mtllc-gld-052586
# [2018-12-26 17:08:29] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-university-red-tr-yllw-sl-blck-052638
# [2018-12-26 17:08:29] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-cinnabar-lsr-orng-fbrlss-blk-052661
# [2018-12-26 17:08:29] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-lsr-crimson-lsr-crmsn-blk-vlt-052174
# [2018-12-26 17:08:34] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-chllng-rd-chllg-rd-smmt-wht-b-052600
# [2018-12-26 17:08:37] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-prm-mtllc-slvr-strng-snst-glw-grn-052723
# [2018-12-26 17:08:37] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-artisan-teal-sail-black-052597
# [2018-12-26 17:08:37] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-essential-black-gym-red-sail-gm-md-brown-052780
# [2018-12-26 17:08:37] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-volt-volt-obsidian-052571
# [2018-12-26 17:08:37] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-lt-retro-sail-blk-052589
# [2018-12-26 17:08:40] [ERROR] error timer = 3, url = https://www.flightclub.com/w-s-air-jordan-8-retro-white-varsity-red-bright-concord-aqua-tone-010598
# [2018-12-26 17:08:41] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-blue-force-blue-force-sail-052491
# [2018-12-26 17:08:41] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-grey-mint-052584
# [2018-12-26 17:08:41] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-white-white-wolf-grey-volt-052567
# [2018-12-26 17:08:41] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-court-purple-violet-wash-volt-051798
# [2018-12-26 17:08:44] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-black-black-anthracite-052359
# [2018-12-26 17:08:44] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-nike-rosherun-white-mtlc-platinum-052556
# [2018-12-26 17:08:44] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-force-one-hi-prm-qs-white-white-metallic-silver-021413
# [2018-12-26 17:08:44] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-huarache-run-black-hyper-crimson-space-blue-052466
# [2018-12-26 17:08:44] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-volt-light-bone-052322
# [2018-12-26 17:08:47] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-hyp-vlt-sh-vlt-shd-lsr-crmsn-vlt-052215
# [2018-12-26 17:08:47] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-roshe-run-hyp-bright-mango-dk-magnet-grey-052299
# [2018-12-26 17:08:47] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-print-anthracite-black-anthrct-vlt-052340
# [2018-12-26 17:08:47] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-lib-qs-blue-recall-white-lnn-atmc-mng-052408
# [2018-12-26 17:08:47] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-fv-qs-black-volt-white-052315
# [2018-12-26 17:08:50] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-sp-obsidian-tropical-teal-volt-052112
# [2018-12-26 17:08:51] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-prm-ivry-mtlc-gld-cn-hypr-pnch-gm-052235
# [2018-12-26 17:08:51] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-woven-qs-tropical-twist-white-white-052069
# [2018-12-26 17:08:51] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-pwm-n7-black-black-summit-white-dark-turquoise-052097
# [2018-12-26 17:08:51] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-cut-out-prm-mtlc-rd-brnz-mtlc-rd-brnz-lght-052280
# [2018-12-26 17:08:54] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-rosherun-total-crimson-sail-brght-ctrs-051890
# [2018-12-26 17:08:54] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-womens-air-max-97-vrsty-red-vrsty-red-white-050484
# [2018-12-26 17:08:54] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-force-1-supreme-black-black-engine-1-laser-pink-020954
# [2018-12-26 17:08:54] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-womens-air-max-90-classic-white-asian-concord-lz-pink-light-zen-grey-050337
# [2018-12-26 17:08:54] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-vt-qs-black-sail-052190
# [2018-12-26 17:08:57] [ERROR] error timer = 3, url = https://www.flightclub.com/womens-air-jordan-4-retro-white-border-blue-light-sand-010467
# [2018-12-26 17:08:57] [ERROR] error timer = 3, url = https://www.flightclub.com/w-s-air-jordan-8-retro-ice-blue-metallic-silver-orange-blaze-010613
# [2018-12-26 17:08:57] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-force-1-07-lx-particle-beige-805777
# [2018-12-26 17:08:57] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-w-s-air-max-1-charcoal-sail-gym-red-052013
# [2018-12-26 17:08:57] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-womens-dunk-low-premium-celery-papaya-med-mint-varsity-red-030338
# [2018-12-26 17:09:00] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-force-1-hi-prm-white-white-metallic-silver-805733
# [2018-12-26 17:09:00] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-hi-phantom-white-805480
# [2018-12-26 17:09:00] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-force-1-hi-se-elemental-gold-805583
# [2018-12-26 17:09:00] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-nrg-black-black-white-805692
# [2018-12-26 17:09:00] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-force1-hi-se-night-maroon-dark-cayenne-gum-medium-brown-805723
# [2018-12-26 17:09:03] [ERROR] error timer = 3, url = https://www.flightclub.com/catalog/product/view/id/262990/
# [2018-12-26 17:09:04] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-qs-black-silt-red-summit-white-805301
# [2018-12-26 17:09:04] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-desert-sand-phantom-805085
# [2018-12-26 17:09:04] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-90-lx-mushroom-mushroom-smokey-blue-805272
# [2018-12-26 17:09:04] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-court-force-hi-sali-wshd-green-cmt-rd-gm-yllw-804718
# [2018-12-26 17:09:07] [ERROR] error timer = 3, url = https://www.flightclub.com/workout-lo-plus-vintage-white-practical-pink-804535
# [2018-12-26 17:09:07] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-plus-tn-se-tartan-black-black-university-red-805081
# [2018-12-26 17:09:07] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-premium-sc-guava-ice-metallic-red-bronze-804665
# [2018-12-26 17:09:07] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-1-se-tartan-black-black-university-red-805178
# [2018-12-26 17:09:07] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-zoom-fly-sp-white-bright-crimson-sail-804502
# [2018-12-26 17:09:10] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-trainer-max-91-anthracite-ice-blue-obsidian-805026
# [2018-12-26 17:09:10] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-re-low-liftd-mtlc-red-bronze-804220
# [2018-12-26 17:09:10] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-plus-tn-se-black-volt-solar-red-804571
# [2018-12-26 17:09:10] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-max-plus-lx-particle-rose-vast-grey-804440
# [2018-12-26 17:09:10] [ERROR] error timer = 3, url = https://www.flightclub.com/ultra-boost-w-grey-five-carbon-ash-pearl-804487
# [2018-12-26 17:09:13] [ERROR] error timer = 3, url = https://www.flightclub.com/ultraboost-w-red-night-red-night-core-black-804388
# [2018-12-26 17:09:13] [ERROR] error timer = 3, url = https://www.flightclub.com/air-vapormax-97-mtlc-dark-sea-white-black-804039
# [2018-12-26 17:09:13] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-barely-grape-white-804382
# [2018-12-26 17:09:13] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-90-lx-particle-rose-particle-rose-804572
# [2018-12-26 17:09:14] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-air-max-90-lx-gunsmoke-gunsmoke-804075
# [2018-12-26 17:09:17] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-black-black-dark-grey-803877
# [2018-12-26 17:09:17] [ERROR] error timer = 3, url = https://www.flightclub.com/wmns-nike-epic-react-flyknit-light-cream-sail-lemon-wash-803929
# [2018-12-26 17:09:17] [ERROR] error timer = 3, url = https://www.flightclub.com/nike-wmns-blazer-mid-vintage-suede-blue-803868
# [2018-12-26 17:09:17] done