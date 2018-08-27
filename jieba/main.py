#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import re
import jieba


class Sentence(object):
    def __init__(self, content, id):
        self.content = content
        self.id = id
        # 精确模式分词
        self.seg_arr = '/'.join(jieba.cut(content, cut_all=False)).split('/')
        self.seg_set = set(self.seg_arr)
        # 根据相似度排好序的数组
        # 数据结构如下
        # { degree: float, id: int }
        self.similarity_degree_arr = []

    def __str__(self):
        return self.content.encode('utf-8')

    def similarity_degree(self, other_sentence):
        if self.id != other_sentence.id:
            molecular = len(self.seg_set & other_sentence.seg_set)
            denominator = len(self.seg_set | other_sentence.seg_set)
            degree = 0 if denominator == 0 else molecular / denominator
            inserted = False
            for i, degreeVal in enumerate(self.similarity_degree_arr):
                if degreeVal.get('degree') < degree:
                    self.similarity_degree_arr.insert(i, { 'degree': degree, 'id': other_sentence.id })
                    inserted = True
                    break
            if not inserted:
                self.similarity_degree_arr.append({ 'degree': degree, 'id': other_sentence.id })


def query_by_id(sentence_arr, id):
    left_index = 0
    middle_index = 0
    right_index = len(sentence_arr) - 1
    while right_index >= left_index:
        middle_index = (right_index + left_index) // 2
        if sentence_arr[middle_index].id > id:
            right_index = middle_index - 1
        else:
            left_index = middle_index + 1
    return sentence_arr[left_index - 1]


def split_by_punctuation(string):
    '''按照标点符号分割string'''
    # 按照标点分割
    p = re.compile(r'[\s+\.\!\/_,$%^*(+\"\')]+|[+——()?！，。？、]+'.decode('utf-8'))
    txt_arr = []
    txt_arr += p.split(string)
    return [txt for txt in txt_arr if txt != '']


if __name__ == '__main__':
    f = open('./txt.txt')
    txt = f.read().decode('utf-8')
    f.close()
    txt_arr = split_by_punctuation(txt.replace('\n', ''))
    sentence_arr = []
    for i, txt in enumerate(txt_arr):
        sentence_arr.append(Sentence(txt, i))
    for sentence1 in sentence_arr:
        for sentence2 in sentence_arr:
            sentence1.similarity_degree(sentence2)

    # 拿第一个语句测试
    print('和"%s"最相似的三条语句' % sentence_arr[0])
    for idx in range(0, 3):
        similarity_degree = sentence_arr[0].similarity_degree_arr[idx]
        sentence = query_by_id(sentence_arr, similarity_degree.get('id'))
        print('相似度:%f, 内容:%s' % (similarity_degree.get('degree'), sentence))
