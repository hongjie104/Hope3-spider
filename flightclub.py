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


platform = 'flightclub'


url_list_1 = [
    'https://www.flightclub.com/air-jordan-5-retro-og-black-fire-red-mtllc-slvr-wht-012471',
    'https://www.flightclub.com/air-jordan-11-retro-low-binary-blue-binary-blue-sail-803915',
    'https://www.flightclub.com/air-jordan-8-retro-black-gym-red-black-wolf-grey-801785',
    'https://www.flightclub.com/adidas-pw-human-race-nmd-tr-noble-ink-bold-yellow-footwear-white-802504',
    'https://www.flightclub.com/air-jordan-8-retro-black-white-lt-graphite-012347',
    'https://www.flightclub.com/adidas-nmd-r1-black-white-201336',
    'https://www.flightclub.com/nmd-r1-core-black-core-black-clear-mint-804805',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-black-780023',
    'https://www.flightclub.com/nike-air-presto-mid-acronym-white-black-hot-lava-volt-053066',
    'https://www.flightclub.com/air-jordan-3-retro-hc-metallic-silver-cool-grey-802525',
    'https://www.flightclub.com/nike-sb-zoom-dunk-low-pro-binary-blue-binary-blue-801637',
    'https://www.flightclub.com/catalog/product/view/id/201031/',
    'https://www.flightclub.com/old-skool-primar-primary-check-rng-rd-w-803191',
    'https://www.flightclub.com/nike-huarache-run-habanero-red-black-white-805722',
    'https://www.flightclub.com/jason-markk-suede-cleaning-kit-2-piece-cleaning-kit-992178',
    'https://www.flightclub.com/the-ultimate-scuff-eraser-803338',
    'https://www.flightclub.com/air-vapormax-plus-cool-grey-team-orange-805411',
    'https://www.flightclub.com/air-force-1-high-black-black-white-805718',
    'https://www.flightclub.com/air-max-98-gundam-white-university-red-obsidian-803075',
    'https://www.flightclub.com/ultraboost-j-mulit-color-multi-color-801834',
    'https://www.flightclub.com/nike-little-posite-pro-dk-grey-heather-black-black-801222',
    'https://www.flightclub.com/air-jordan-1-black-black-white-gym-red-801367',
    'https://www.flightclub.com/creeper-white-black-white-black-800647',
    'https://www.flightclub.com/nike-sb-dunk-low-trd-qs-dune-twig-wheat-gum-med-brown-800964',
    'https://www.flightclub.com/rihanna-x-puma-fenty-bow-trinomic-sweet-lavender-800713',
    'https://www.flightclub.com/creeper-wrinkled-patent-black-black-800650',
    'https://www.flightclub.com/vapormax-fx-cdg-pure-platinum-white-wolf-grey-800612',
    'https://www.flightclub.com/legacy-crew-sock-ultramarine-800199',
    'https://www.flightclub.com/ultra-boost-reigning-champ-white-heather-800686',
    'https://www.flightclub.com/legacy-crew-sock-kelly-800200',
    'https://www.flightclub.com/flight-club-legacy-crew-sock-red-white-701119',
    'https://www.flightclub.com/crep-protect-the-ultimate-shoe-cleaner-cure-solution-200-ml-bottle-780040',
    'https://www.flightclub.com/flight-club-legacy-crew-sock-neon-green-black-701117',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-charcoal-grey-780026',
    'https://www.flightclub.com/catalog/product/view/id/156652/',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-grey-white-780027',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-athl-orange-780029',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-grape-780028',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-high-risk-red-780022',
    'https://www.flightclub.com/nike-air-presto-se-qs-neutral-grey-black-kmqt-strng-052942',
    'https://www.flightclub.com/air-jordan-5-retro-td-sail-orange-peel-black-hyper-royal-805092',
    'https://www.flightclub.com/nike-dunk-low-premium-sb-atomic-pink-black-white-081284',
    'https://www.flightclub.com/air-jordan-2-retro-black-varsity-red-012373',
    'https://www.flightclub.com/air-force-1-as-qs-white-white-white-803575',
    'https://www.flightclub.com/nike-air-max-1-97-vf-sw-td-lt-blue-fury-lemon-wash-803623',
    'https://www.flightclub.com/nike-little-posite-one-td-black-psn-green-pink-fl-gmm-bl-803882',
    'https://www.flightclub.com/jordan-5-retro-gp-td-black-black-deadly-pink-white-804208',
    'https://www.flightclub.com/nike-air-more-uptempo-island-green-white-802927',
    'https://www.flightclub.com/jason-markk-foam-803832',
    'https://www.flightclub.com/air-more-uptempo-chi-qs-university-red-university-red-802931',
    'https://www.flightclub.com/iniki-runner-pine-green-white-gum-803041',
    'https://www.flightclub.com/nike-sb-zoom-dunk-low-elite-qs-black-black-white-medium-grey-802761',
    'https://www.flightclub.com/futurecraft-4d-cblack-grefiv-ashgrn-803127',
    'https://www.flightclub.com/ultimate-gift-pack-802514',
    'https://www.flightclub.com/nike-dunk-high-sb-qs-blue-ribbon-blue-ribbon-802827',
    'https://www.flightclub.com/climacool-02-17-tacgrn-tacgrn-ftwwht-802069',
    'https://www.flightclub.com/jordan-13-retro-gp-black-metallic-gold-mint-foam-802250',
    'https://www.flightclub.com/cleated-creepersuede-wn-s-puma-black-801869',
    'https://www.flightclub.com/nmd-r1-grey-three-grey-three-801976',
    'https://www.flightclub.com/superstar-ftwwht-conavy-ftwwht-802455',
    'https://www.flightclub.com/crep-protect-the-ultimate-rain-stain-resistant-barrier-780004',
    'https://www.flightclub.com/leadcat-fenty-pink-pink-801429',
    'https://www.flightclub.com/foundation-sweatpants-black-fc-red-801292',
    'https://www.flightclub.com/nmd-r1-grey-raw-pink-801871',
    'https://www.flightclub.com/nikelab-air-force-1-low-cmft-tc-light-cognac-purple-agate-ivory-light-cognac-801541',
    'https://www.flightclub.com/jason-markk-travel-kit-800585',
    'https://www.flightclub.com/jordan-11-retro-low-gp-td-505835-010-801121',
    'https://www.flightclub.com/jordan-11-retro-low-gp-td-blue-moon-polarized-blue-801119',
    'https://www.flightclub.com/rihanna-x-puma-fenty-bow-trinomic-pink-tint-pink-tint-pink-tint-800714',
    'https://www.flightclub.com/nmd-r1w-sunglo-wwht-hzcor-800674',
    'https://www.flightclub.com/alumni-full-zip-ultramarine-800385',
    'https://www.flightclub.com/nikelab-air-max-plus-pearl-pink-cobblestone-sail-800980',
    'https://www.flightclub.com/alumni-full-zip-navy-800228',
    'https://www.flightclub.com/alumni-full-zip-heather-800226',
    'https://www.flightclub.com/nmd-r2-pk-collegiate-navy-running-white-800810',
    'https://www.flightclub.com/flight-club-legacy-crew-sock-black-red-701120',
    'https://www.flightclub.com/catalog/product/view/id/179239/',
    'https://www.flightclub.com/adidas-nmd-r1-w-brown-red-white-800052',
    'https://www.flightclub.com/flight-club-legacy-crew-sock-grey-white-701118',
    'https://www.flightclub.com/legacy-crew-sock-purple-800203',
    'https://www.flightclub.com/nike-air-presto-mid-acronym-black-black-bamboo-053065',
    'https://www.flightclub.com/reebok-question-mid-primal-red-ice-992279',
    'https://www.flightclub.com/nike-air-presto-mid-acronym-med-olive-black-dust-053067',
    'https://www.flightclub.com/new-balance-w990-v4-pink-grey-300840',
    'https://www.flightclub.com/crep-protect-the-ultimate-shoe-cleaner-cure-travel-pack-3-piece-cleaning-kit-780012',
    'https://www.flightclub.com/reebok-royal-nylon-black-black-carbon-992242',
    'https://www.flightclub.com/reebok-cl-lthr-black-gum-992156',
    'https://www.flightclub.com/nike-air-presto-black-black-black-052868',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-aqua-780030',
    'https://www.flightclub.com/flight-club-stealth-no-show-sock-ultramarine-780024',
    'https://www.flightclub.com/jordan-4-retro-td-black-vivid-pink-dynmc-bl-wht-012554',
    'https://www.flightclub.com/nike-lebron-10-honey-honey-041971',
    'https://www.flightclub.com/pure-boost-grey-black-800010',
    'https://www.flightclub.com/jordan-6-retro-gp-wht-frc-grn-dp-ryl-bl-hypr-pnk-012192',
    'https://www.flightclub.com/nike-air-presto-qs-black-zen-grey-habor-blue-052839',
    'https://www.flightclub.com/nike-air-presto-prsn-violet-blck-ntrl-gry-wht-053052',
    'https://www.flightclub.com/reebok-club-c-85-black-white-992230',
    'https://www.flightclub.com/new-balance-w530-steel-blue-rain-300827',
    'https://www.flightclub.com/nike-wnms-air-huarache-run-white-fchs-flsh-artsn-tl-fchs-052680',
    'https://www.flightclub.com/adidas-ultra-boost-uncaged-j-pink-white-201429',
    'https://www.flightclub.com/reebok-cl-nylon-team-navy-platinum-992249',
    'https://www.flightclub.com/reebok-cl-lthr-spirit-respect-energy-992182',
    'https://www.flightclub.com/reebok-cl-lthr-spirit-philosophic-white-energy-992183',
    'https://www.flightclub.com/nike-air-max-thea-lotc-qs-blacjk-black-white-052977',
    'https://www.flightclub.com/asics-gel-lyte-3-turquoise-white-991944',
    'https://www.flightclub.com/nike-free-flyknit-chukka-pr-qs-gm-royal-obsdn-hypr-pnch-ivry-052228',
    'https://www.flightclub.com/nike-air-presto-tp-qs-tumbled-grey-black-anthrct-wht-052744',
    'https://www.flightclub.com/nike-lil-posite-pro-cb-black-black-laser-crimson-042293',
    'https://www.flightclub.com/nike-air-presto-qs-black-yellow-streak-ntrl-grey-052805',
    'https://www.flightclub.com/asics-gel-lyte-3-dk-olive-black-991857',
    'https://www.flightclub.com/nike-air-presto-tp-qs-black-anthracite-black-052743',
    'https://www.flightclub.com/saucony-shadow-original-black-grey-991945',
    'https://www.flightclub.com/nike-air-presto-sp-black-black-cement-grey-052287',
    'https://www.flightclub.com/nike-air-max-1-prm-grain-orange-blaze-052074',
    'https://www.flightclub.com/air-jordan-10-retro-gp-white-verde-black-infrared-23-012182',
    'https://www.flightclub.com/air-jordan-14-retro-low-white-pacific-blu-mts-brt-ceramic-011177',
    'https://www.flightclub.com/adidas-glc-promo-black1-black1-black1-200804',
    'https://www.flightclub.com/girls-jordan-1-td-emerald-green-black-grp-ic-wht-011116',
    'https://www.flightclub.com/women-s-air-jordan-10-retro-white-medium-violet-light-graphite-010249',
    'https://www.flightclub.com/jordan-3-retro-td-white-black-metallic-silver-varsity-red-010677',
    'https://www.flightclub.com/wmns-air-jordan-4-retro-nrg-fire-red-summit-white-black-805694',
    'https://www.flightclub.com/wmns-air-jordan-8-vday-gym-red-ember-glow-team-red-803202',
    'https://www.flightclub.com/wmns-air-jordan-12-retro-vachetta-tan-metallic-gold-803392',
    'https://www.flightclub.com/wmns-air-max-plus-light-crimson-black-white-805436',
    'https://www.flightclub.com/wmns-air-force-1-high-white-white-white-805419',
    'https://www.flightclub.com/wmns-air-jordan-1-re-hi-og-sl-black-black-starfish-sail-803897',
    'https://www.flightclub.com/wmns-air-jordan-11-retros-neutral-olive-mtlc-stout-sail-805670',
    'https://www.flightclub.com/wmns-air-jordan-1-high-zip-particle-beige-mtlc-red-bronze-804550',
    'https://www.flightclub.com/wmns-air-jordan-13-retro-phantom-moon-particle-804534',
    'https://www.flightclub.com/w-s-air-huarache-run-black-black-801232',
    'https://www.flightclub.com/nmd-r1-w-ash-pearl-chalk-pearl-white-802615',
    'https://www.flightclub.com/wmns-air-jordan-11-retro-sail-mtlc-red-bronze-803590',
    'https://www.flightclub.com/nmd-r1-w-utiblk-ftwwht-mgsogr-800675',
    'https://www.flightclub.com/wmns-air-jordan-3-retro-se-particle-beige-mtlc-red-bronze-804251',
    'https://www.flightclub.com/wmns-air-jordan-3-retro-se-bordeaux-bordeaux-phantom-805066',
    'https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-black-light-cream-white-804927',
    'https://www.flightclub.com/wmns-air-max-plus-lx-dusty-peach-bio-beige-803889',
    'https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-white-black-university-red-804037',
    'https://www.flightclub.com/nmd-r1-w-clear-onix-light-onix-vapour-pink-800411',
    'https://www.flightclub.com/wmns-air-max-95-se-sail-arctic-pink-racer-blue-804584',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-white-white-052856',
    'https://www.flightclub.com/nmd-r1-w-white-pink-801145',
    'https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-802836',
    'https://www.flightclub.com/wmns-air-max-90-white-court-purple-wolf-grey-805350',
    'https://www.flightclub.com/wmns-air-max-1-lx-white-black-total-orange-804343',
    'https://www.flightclub.com/nmd-r1-w-black-mint-green-805489',
    'https://www.flightclub.com/ultraboost-w-blue-white-801432',
    'https://www.flightclub.com/wmns-lebron-xvi-lmtd-sail-white-light-bone-805019',
    'https://www.flightclub.com/nmd-r2-w-linen-linen-ftwwht-802145',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-gym-red-gym-red-052807',
    'https://www.flightclub.com/nike-air-vapormax-flyknit-string-chrome-sunset-glow-802784',
    'https://www.flightclub.com/wmns-nike-air-max-1-prm-mtlc-pewter-mtlc-pewter-summit-wht-802914',
    'https://www.flightclub.com/wmns-air-jordan-1-rebel-black-black-varsity-royal-804022',
    'https://www.flightclub.com/bb2368-maroon-cburgu-ftwwht-802457',
    'https://www.flightclub.com/nmd-r1-w-pk-shock-pink-core-black-running-white-ftw-800772',
    'https://www.flightclub.com/wmns-air-more-uptempo-dark-stucco-white-black-802794',
    'https://www.flightclub.com/nmd-r1-w-pk-sea-crystal-turquoise-sea-crystal-800910',
    'https://www.flightclub.com/nmd-r1-salmon-800036',
    'https://www.flightclub.com/ultra-boost-w-ash-green-ash-green-real-teal-804645',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-dark-grey-teal-052764',
    'https://www.flightclub.com/ultraboost-w-mystery-blue-mystery-blue-vapour-grey-801987',
    'https://www.flightclub.com/wmns-air-max-1-desert-sand-desert-sand-804212',
    'https://www.flightclub.com/nmd-xr1-pk-w-icepur-midgre-ftwwht-800663',
    'https://www.flightclub.com/catalog/product/view/id/232155/',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-hi-prem-black-metallic-gold-803536',
    'https://www.flightclub.com/nmd-r1-w-pink-white-gum-803671',
    'https://www.flightclub.com/adidas-ultra-boost-w-core-black-black-grey-201351',
    'https://www.flightclub.com/wmns-nike-epic-react-flyknit-pearl-pink-pearl-pink-803928',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-purple-earth-white-803186',
    'https://www.flightclub.com/nmd-xr1-w-white-white-pearl-grey-801270',
    'https://www.flightclub.com/wmns-classic-cortez-leather-white-varsity-red-801434',
    'https://www.flightclub.com/wmns-air-max-95-white-court-purple-803222',
    'https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-green-201035',
    'https://www.flightclub.com/wmns-air-max-93-white-sport-turq-black-803524',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-summit-white-mtlc-red-bronze-801680',
    'https://www.flightclub.com/ultraboost-x-parley-w-night-navy-intense-blue-800938',
    'https://www.flightclub.com/wmns-nike-sock-dart-prm-black-white-black-800766',
    'https://www.flightclub.com/nmd-xr1-w-drkbur-drkbur-vappnk-802997',
    'https://www.flightclub.com/wmns-air-max-plus-qs-metallic-gold-university-red-801048',
    'https://www.flightclub.com/nmd-r2-w-wonpnk-wonpnk-cblack-801683',
    'https://www.flightclub.com/nmd-r1-w-vapour-pink-light-onix-800410',
    'https://www.flightclub.com/adidas-nmd-r1-w-red-201385',
    'https://www.flightclub.com/iniki-runner-w-purple-white-cream-800646',
    'https://www.flightclub.com/wmns-air-max-1-white-black-wolf-grey-805083',
    'https://www.flightclub.com/wmns-air-force-1-07-se-black-wheat-gold-805400',
    'https://www.flightclub.com/ultraboost-w-pink-black-white-800368',
    'https://www.flightclub.com/adidas-nmd-r1-w-grey-mtllc-silver-201364',
    'https://www.flightclub.com/nike-w-s-air-presto-flyknit-ultra-hyper-turq-hyper-turq-053029',
    'https://www.flightclub.com/nmd-r1-w-black-tactile-rose-bold-red-804324',
    'https://www.flightclub.com/wmns-air-jordan-5-white-fire-red-sunset-dark-cinder-010743',
    'https://www.flightclub.com/ultraboost-w-grey-blue-804472',
    'https://www.flightclub.com/nmd-r1-w-trace-scarlet-trace-scarlet-running-white-804437',
    'https://www.flightclub.com/nike-w-s-sf-air-force-one-high-binary-blue-binary-blue-black-800256',
    'https://www.flightclub.com/catalog/product/view/id/242350/',
    'https://www.flightclub.com/adidas-nmd-r1-w-raw-pink-white-201307',
    'https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-red-black-804187',
    'https://www.flightclub.com/wmns-air-vapormax-fk-moc-2-university-gold-black-804006',
    'https://www.flightclub.com/catalog/product/view/id/243219/',
    'https://www.flightclub.com/wmns-air-max-1-lx-total-orange-white-black-804430',
    'https://www.flightclub.com/ultraboost-w-ash-pearl-ash-pearl-ash-pearl-803574',
    'https://www.flightclub.com/wmns-air-jordan-1-high-zip-white-white-university-red-803772',
    'https://www.flightclub.com/nike-air-more-uptempo-white-chrome-blue-tint-803139',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-light-aqua-white-metallic-gold-803146',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-high-sol-sunblush-white-metallic-gold-803145',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-plum-fog-plum-fog-803279',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-midnight-fog-multi-color-black-802785',
    'https://www.flightclub.com/wmns-nike-air-vapormax-fk-moc-black-anthracite-volt-802753',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-white-white-sail-light-bone-803067',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-ice-peach-white-metallic-gold-803147',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-black-black-white-racer-blue-802551',
    'https://www.flightclub.com/nmd-xr1-pk-w-utiivy-utiivy-corred-802928',
    'https://www.flightclub.com/wmns-nike-air-footscape-woven-sail-white-red-stardust-802444',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-metallic-silver-802634',
    'https://www.flightclub.com/womens-roshe-one-black-black-dark-grey-802319',
    'https://www.flightclub.com/nmd-r1-w-black-carbon-running-white-802681',
    'https://www.flightclub.com/wmns-air-max-90-prm-db-white-black-dynamic-yellow-801898',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-bordeaux-tea-berry-black-802338',
    'https://www.flightclub.com/nmd-r1-w-raw-pink-trace-pink-legend-ink-801864',
    'https://www.flightclub.com/ultraboost-w-black-white-801450',
    'https://www.flightclub.com/w-s-air-huarache-run-max-orange-cool-grey-801387',
    'https://www.flightclub.com/wmns-air-huarache-run-prm-txt-mahogany-mtlc-mahogany-802276',
    'https://www.flightclub.com/wmns-air-huarache-run-dusted-clay-white-gum-yellow-801401',
    'https://www.flightclub.com/nmd-r2-w-clear-granite-vintage-white-801272',
    'https://www.flightclub.com/iniki-runner-w-pink-blue-gum-801246',
    'https://www.flightclub.com/wmns-air-max-plus-se-white-white-black-801882',
    'https://www.flightclub.com/nmd-cs2-pk-w-peagre-peagre-ftw-801098',
    'https://www.flightclub.com/wmns-air-hurache-run-sport-fuchsia-white-gum-yellow-801071',
    'https://www.flightclub.com/ultraboost-w-grey-grey-801431',
    'https://www.flightclub.com/wmns-air-max-zero-white-black-800987',
    'https://www.flightclub.com/wmns-air-huarache-run-ember-glow-dark-cayenne-white-801233',
    'https://www.flightclub.com/wmns-toki-slip-canvas-white-white-800992',
    'https://www.flightclub.com/wmns-air-max-90-white-white-wolf-grey-black-801021',
    'https://www.flightclub.com/nmd-cs2-pk-w-tragrn-tragrn-trapnk-801240',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-dark-grey-black-wolf-grey-800867',
    'https://www.flightclub.com/ultraboost-w-white-white-white-801004',
    'https://www.flightclub.com/w-s-air-huarache-run-anthracite-oatmeal-cool-grey-800851',
    'https://www.flightclub.com/nmd-r1-w-black-blue-801055',
    'https://www.flightclub.com/nmd-r1-w-pk-green-pink-green-800909',
    'https://www.flightclub.com/nmd-r2-w-olive-white-800736',
    'https://www.flightclub.com/air-max-zero-wolf-grey-wolf-grey-white-800986',
    'https://www.flightclub.com/nmd-r1-w-pk-black-pink-white-800788',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-white-wolf-grey-800731',
    'https://www.flightclub.com/wmns-air-max-1-pinnacle-silt-red-silt-red-sail-800897',
    'https://www.flightclub.com/nmd-r1-w-grey-white-800601',
    'https://www.flightclub.com/wmns-classic-cortez-str-ltr-black-black-black-800764',
    'https://www.flightclub.com/ultraboost-w-white-grey-800653',
    'https://www.flightclub.com/iniki-runner-w-orange-white-gum-800845',
    'https://www.flightclub.com/iniki-runner-w-mint-white-gum-800645',
    'https://www.flightclub.com/ultra-boost-w-black-black-met-800211',
    'https://www.flightclub.com/adidas-nmd-xr1-w-midgre-nobink-grey-800338',
    'https://www.flightclub.com/nike-w-s-sf-air-force-one-high-desert-ochre-desert-ochre-800257',
    'https://www.flightclub.com/wmns-nike-air-vapormax-flyknit-pure-platinum-university-red-800690',
    'https://www.flightclub.com/adidas-stan-smith-w-ftwwht-ftwwht-owhite-800325',
    'https://www.flightclub.com/nmd-rl-w-black-sand-white-800062',
    'https://www.flightclub.com/nmd-xr1-w-vapgre-icepur-owhite-800008',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-se-mtlc-red-bronze-elm-053083',
    'https://www.flightclub.com/nike-w-s-huarache-run-se-mtlc-dark-sea-midnight-turq-053228',
    'https://www.flightclub.com/nmd-cs2-pk-w-conavy-conavy-ftwwht-800689',
    'https://www.flightclub.com/adidas-nmd-r1-w-white-teal-sand-201550',
    'https://www.flightclub.com/adidas-tubular-viral-w-metsil-cgrani-cwhite-201506',
    'https://www.flightclub.com/nike-w-s-air-force-1-hi-prm-flax-flax-outdoor-green-021534',
    'https://www.flightclub.com/nike-w-s-sf-air-force-one-high-light-bone-light-bone-sail-021538',
    'https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-linen-linen-gum-lt-brown-053063',
    'https://www.flightclub.com/adidas-nmd-r1-w-blue-white-201365',
    'https://www.flightclub.com/adidas-nmdxr1-pk-w-pink-white-201535',
    'https://www.flightclub.com/adidas-nmd-xr1-pk-w-white-white-201418',
    'https://www.flightclub.com/adidas-nmd-r1-w-black-white-201408',
    'https://www.flightclub.com/adidas-nmd-r1-w-navy-white-bergundy-201503',
    'https://www.flightclub.com/adidas-nmd-r1-w-blanch-purple-white-201259',
    'https://www.flightclub.com/adidas-nmd-r1-w-black-pink-201224',
    'https://www.flightclub.com/nike-w-s-air-max-90-anniversary-bronze-black-infrared-white-052624',
    'https://www.flightclub.com/adidas-nmd-xr1-pk-w-unity-blue-collegiate-navy-vivid-red-201414',
    'https://www.flightclub.com/nike-w-s-air-max-90-space-pink-challenge-red-space-pink-052760',
    'https://www.flightclub.com/nike-w-s-air-max-90-og-white-cool-grey-ntrl-grey-blk-052656',
    'https://www.flightclub.com/adidas-nmd-r1-w-beige-beige-white-201285',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-black-pink-blast-white-052980',
    'https://www.flightclub.com/adidas-zx-flux-w-cblack-cblack-coppmt-201377',
    'https://www.flightclub.com/adidas-nmd-xr1-pk-w-grey-white-pink-201401',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-atomic-pink-atomic-pink-052974',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-sunset-gold-dart-white-black-053036',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-052692',
    'https://www.flightclub.com/nike-w-s-air-presto-ttl-crmsn-brght-crmsn-wht-blck-053016',
    'https://www.flightclub.com/nike-w-s-air-max-90-essential-wolf-grey-infrared-black-white-053022',
    'https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-island-green-islnd-grn-ftl-gld-052959',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-prm-black-black-mtllc-gold-white-052919',
    'https://www.flightclub.com/adidas-ultra-boost-w-white-white-201180',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-white-rdnt-emrld-sprt-fchs-smm-052966',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-bronzine-bronzine-sail-black-052450',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-prm-white-white-052603',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-cool-grey-052759',
    'https://www.flightclub.com/womens-air-jordan-3-retro-white-harbor-blue-boarder-blue-010536',
    'https://www.flightclub.com/nike-w-s-air-max-90-qs-viola-fushia-glow-chilling-red-052763',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-loyal-blue-loyal-blue-052879',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-prm-blue-legend-blue-legend-052625',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-prm-hot-lava-hot-lava-052613',
    'https://www.flightclub.com/nike-w-s-air-max-90-anniversary-gym-red-black-infrrd-mtllc-gld-052596',
    'https://www.flightclub.com/nike-w-s-air-max-1-prm-mtlc-gold-silk-blck-clssc-brwn-051857',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-pure-platinum-052664',
    'https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-lyon-blue-lyn-bl-smmt-wht-blk-052580',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-university-red-maroon-white-800191',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-white-052455',
    'https://www.flightclub.com/nike-w-s-air-max-1-vntg-sail-hypr-rd-strt-gry-icd-crmn-051833',
    'https://www.flightclub.com/nike-w-s-air-max-1-lib-qs-dp-brgndy-dp-brgndy-brght-mng-052420',
    'https://www.flightclub.com/w-s-air-jordan-7-retro-white-varsity-maize-black-010314',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-print-obsidian-obsidian-phantom-053216',
    'https://www.flightclub.com/adidas-ultra-boost-uncage-w-teal-white-201428',
    'https://www.flightclub.com/nike-w-s-rosherun-dk-electric-blu-clrwtr-white-053183',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-blue-spark-coastel-blue-white-800190',
    'https://www.flightclub.com/adidas-nmd-r1-w-black-white-201242',
    'https://www.flightclub.com/nike-w-s-mayfly-woven-black-dark-grey-white-090189',
    'https://www.flightclub.com/nike-w-s-air-max-ultra-lotc-qs-ink-ink-summit-white-team-red-052612',
    'https://www.flightclub.com/adidas-nmd-r1-w-blanch-blue-collegiate-navy-201304',
    'https://www.flightclub.com/nike-w-s-air-max-90-pinnacle-black-black-sail-052970',
    'https://www.flightclub.com/adidas-nmd-r1-w-white-blue-lt-blu-201240',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-white-hot-lava-bl-legend-white-052609',
    'https://www.flightclub.com/nike-w-s-air-max-1-pinnacle-black-black-sail-052971',
    'https://www.flightclub.com/nike-w-s-roshe-one-flyknit-gym-red-brght-crimson-tm-rd-sl-052934',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-dp-royal-vlt-blk-pr-pltnm-052924',
    'https://www.flightclub.com/nike-w-s-flyknit-zoom-agility-black-white-elctrc-grn-pnk-pw-052535',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-black-black-menta-hot-lava-052437',
    'https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-obsidian-obsidian-black-052568',
    'https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-black-smmt-wht-052588',
    'https://www.flightclub.com/nike-w-s-air-max-90-essential-white-black-052871',
    'https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-brnzn-smmt-wht-mtllc-gld-052586',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-print-university-red-tr-yllw-sl-blck-052638',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-cinnabar-lsr-orng-fbrlss-blk-052661',
    'https://www.flightclub.com/nike-w-s-rosherun-hyp-lsr-crimson-lsr-crmsn-blk-vlt-052174',
    'https://www.flightclub.com/nike-w-s-air-max-1-ultra-lotc-qs-chllng-rd-chllg-rd-smmt-wht-b-052600',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-prm-mtllc-slvr-strng-snst-glw-grn-052723',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-print-black-artisan-teal-sail-black-052597',
    'https://www.flightclub.com/nike-w-s-air-max-1-essential-black-gym-red-sail-gm-md-brown-052780',
    'https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-volt-volt-obsidian-052571',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-lt-retro-sail-blk-052589',
    'https://www.flightclub.com/w-s-air-jordan-8-retro-white-varsity-red-bright-concord-aqua-tone-010598',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-blue-force-blue-force-sail-052491',
    'https://www.flightclub.com/nike-w-s-air-huarache-grey-mint-052584',
    'https://www.flightclub.com/nike-w-s-air-max-90-sp-sacai-white-white-wolf-grey-volt-052567',
    'https://www.flightclub.com/nike-w-s-rosherun-court-purple-violet-wash-volt-051798',
    'https://www.flightclub.com/nike-w-s-rosherun-black-black-anthracite-052359',
    'https://www.flightclub.com/nike-w-s-nike-rosherun-white-mtlc-platinum-052556',
    'https://www.flightclub.com/nike-w-s-air-force-one-hi-prm-qs-white-white-metallic-silver-021413',
    'https://www.flightclub.com/nike-w-s-air-huarache-run-black-hyper-crimson-space-blue-052466',
    'https://www.flightclub.com/nike-w-s-rosherun-hyp-volt-light-bone-052322',
    'https://www.flightclub.com/nike-w-s-rosherun-hyp-vlt-sh-vlt-shd-lsr-crmsn-vlt-052215',
    'https://www.flightclub.com/nike-w-s-roshe-run-hyp-bright-mango-dk-magnet-grey-052299',
    'https://www.flightclub.com/nike-w-s-rosherun-print-anthracite-black-anthrct-vlt-052340',
    'https://www.flightclub.com/nike-w-s-rosherun-lib-qs-blue-recall-white-lnn-atmc-mng-052408',
    'https://www.flightclub.com/nike-w-s-air-max-1-fv-qs-black-volt-white-052315',
    'https://www.flightclub.com/nike-w-s-air-max-1-sp-obsidian-tropical-teal-volt-052112',
    'https://www.flightclub.com/nike-w-s-air-max-1-prm-ivry-mtlc-gld-cn-hypr-pnch-gm-052235',
    'https://www.flightclub.com/nike-w-s-rosherun-woven-qs-tropical-twist-white-white-052069',
    'https://www.flightclub.com/nike-w-s-rosherun-pwm-n7-black-black-summit-white-dark-turquoise-052097',
    'https://www.flightclub.com/nike-w-s-air-max-1-cut-out-prm-mtlc-rd-brnz-mtlc-rd-brnz-lght-052280',
    'https://www.flightclub.com/nike-w-s-rosherun-total-crimson-sail-brght-ctrs-051890',
    'https://www.flightclub.com/nike-womens-air-max-97-vrsty-red-vrsty-red-white-050484',
    'https://www.flightclub.com/nike-w-s-air-force-1-supreme-black-black-engine-1-laser-pink-020954',
    'https://www.flightclub.com/nike-womens-air-max-90-classic-white-asian-concord-lz-pink-light-zen-grey-050337',
    'https://www.flightclub.com/nike-w-s-air-max-1-vt-qs-black-sail-052190',
    'https://www.flightclub.com/womens-air-jordan-4-retro-white-border-blue-light-sand-010467',
    'https://www.flightclub.com/w-s-air-jordan-8-retro-ice-blue-metallic-silver-orange-blaze-010613',
    'https://www.flightclub.com/wmns-air-force-1-07-lx-particle-beige-805777',
    'https://www.flightclub.com/nike-w-s-air-max-1-charcoal-sail-gym-red-052013',
    'https://www.flightclub.com/nike-womens-dunk-low-premium-celery-papaya-med-mint-varsity-red-030338',
    'https://www.flightclub.com/wmns-air-force-1-hi-prm-white-white-metallic-silver-805733',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-hi-phantom-white-805480',
    'https://www.flightclub.com/wmns-air-force-1-hi-se-elemental-gold-805583',
    'https://www.flightclub.com/wmns-air-jordan-1-rebel-xx-nrg-black-black-white-805692',
    'https://www.flightclub.com/wmns-air-force1-hi-se-night-maroon-dark-cayenne-gum-medium-brown-805723',
    'https://www.flightclub.com/catalog/product/view/id/262990/',
    'https://www.flightclub.com/wmns-air-max-1-qs-black-silt-red-summit-white-805301',
    'https://www.flightclub.com/wmns-air-max-1-desert-sand-phantom-805085',
    'https://www.flightclub.com/wmns-air-max-90-lx-mushroom-mushroom-smokey-blue-805272',
    'https://www.flightclub.com/wmns-court-force-hi-sali-wshd-green-cmt-rd-gm-yllw-804718',
    'https://www.flightclub.com/workout-lo-plus-vintage-white-practical-pink-804535',
    'https://www.flightclub.com/wmns-air-max-plus-tn-se-tartan-black-black-university-red-805081',
    'https://www.flightclub.com/wmns-air-max-1-premium-sc-guava-ice-metallic-red-bronze-804665',
    'https://www.flightclub.com/wmns-air-max-1-se-tartan-black-black-university-red-805178',
    'https://www.flightclub.com/wmns-zoom-fly-sp-white-bright-crimson-sail-804502',
    'https://www.flightclub.com/wmns-air-trainer-max-91-anthracite-ice-blue-obsidian-805026',
    'https://www.flightclub.com/wmns-air-jordan-1-re-low-liftd-mtlc-red-bronze-804220',
    'https://www.flightclub.com/wmns-air-max-plus-tn-se-black-volt-solar-red-804571',
    'https://www.flightclub.com/wmns-nike-max-plus-lx-particle-rose-vast-grey-804440',
    'https://www.flightclub.com/ultra-boost-w-grey-five-carbon-ash-pearl-804487',
    'https://www.flightclub.com/ultraboost-w-red-night-red-night-core-black-804388',
    'https://www.flightclub.com/air-vapormax-97-mtlc-dark-sea-white-black-804039',
    'https://www.flightclub.com/wmns-air-jordan-1-ret-high-soh-barely-grape-white-804382',
    'https://www.flightclub.com/wmns-air-max-90-lx-particle-rose-particle-rose-804572',
    'https://www.flightclub.com/wmns-air-max-90-lx-gunsmoke-gunsmoke-804075',
    'https://www.flightclub.com/wmns-nike-epic-react-flyknit-black-black-dark-grey-803877',
    'https://www.flightclub.com/wmns-nike-epic-react-flyknit-light-cream-sail-lemon-wash-803929',
    'https://www.flightclub.com/nike-wmns-blazer-mid-vintage-suede-blue-803868'
]


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
            helper.log('[ERROR] => ' + self.url, platform)
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
            if not pq:
                return
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
                size = div.find('div').find('meta').get('content').split('_')[-1]
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
                result = helper.downloadImg(img_url, os.path.join('.', 'imgs', platform, '%s.jpg' % number))
                if result == 1:
                    # 上传到七牛
                    qiniuUploader.upload_2_qiniu(platform, '%s.jpg' % number, './imgs/flightclub/%s.jpg' % number)
                    img_downloaded = True
                mongo.insert_pending_goods(name, number, self.url, size_price_arr, ['%s.jpg' % number], self.gender, color_value, platform, '5ac8592c48555b1ba318964a', self.crawl_counter, img_downloaded=img_downloaded)
        except Exception as e:
            global error_detail_url
            error_counter = error_detail_url.get(self.url, 1)
            error_detail_url[self.url] = error_counter + 1
            helper.log('[ERROR] error timer = %s, url = %s' % (error_counter, self.url), platform)
            helper.log(e, platform)
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
                url = q.get()
                if url in url_list_1:
                    goods_spider = GoodsSpider(url, gender, q, crawl_counter)
                    goods_spider.start()
                    goods_thread_list.append(goods_spider)
            for t in goods_thread_list:
                t.join()
            goods_thread_list = []
        else:
            break


def start(action):
    if action == 'common':
        crawl_counter = mongo.get_crawl_counter(platform)
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
    helper.log('done', platform)
