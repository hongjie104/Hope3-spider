#!/usr/bin/env python
# -*- coding: utf-8 -*-


def read_csv(csv_name):
    f = open(csv_name)
    txt = f.read()
    f.close()
    return txt.split('\n')[1:]


def write_csv(csv_name, dict_value):
    txt = 'number, name'
    for key in dict_value:
        number_list = dict_value.get(key)
        txt += '\n%s,%s' % (key, ','.join(number_list))
    f = open(csv_name, 'w')
    f.write(txt.encode('utf-8'))
    f.close()


def get_repeat_number_dict(csv_name):
    repeat_number_dict = {}
    csv_list = read_csv(csv_name)
    num_line = len(csv_list)
    for i in range(0, num_line):
        number_list = csv_list[i].split(',')[1:]
        for j in range(i + 1, num_line):
            for number in number_list:
                # if number in csv_list[j]:
                if number == csv_list[j]:
                    # 有重复的
                    tmp_name_list = repeat_number_dict.get(number, None)
                    if tmp_name_list:
                        repeat_number_dict[number].append(csv_list[i].split(',')[0])
                        repeat_number_dict[number].append(csv_list[j].split(',')[0])
                    else:
                        repeat_number_dict[number] = [csv_list[i].split(',')[0], csv_list[j].split(',')[0]]
    return repeat_number_dict


def main():
    repeat_number_dict = get_repeat_number_dict('./nike.csv')
    write_csv('./nike_repeat.csv', repeat_number_dict)

    repeat_number_dict = get_repeat_number_dict('./jordan.csv')
    write_csv('./jordan_repeat.csv', repeat_number_dict)

if __name__ == '__main__':
    main()
    print('done')
