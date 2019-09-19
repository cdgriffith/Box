import unittest
import json
import os
import shutil
import sys
import copy

try:
    import yaml
except ImportError:
    import ruamel.yaml as yaml

import box
from box import *

PY3 = sys.version_info >= (3, 0)

test_root = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(test_root, "data")
tmp_dir = os.path.join(test_root, "tmp")

try:
    os.makedirs(data_dir)
except OSError:
    pass

try:
    os.makedirs(tmp_dir)
except OSError:
    pass


test_dict = {'key1': 'value1',
             'not$allowed': 'fine_value',
             'BigCamel': 'hi',
             'alist': [{'a': 1}],
             "Key 2": {"Key 3": "Value 3",
                       "Key4": {"Key5": "Value5"}}}

extended_test_dict = {
    3: 'howdy',
    'not': 'true',
    (3, 4): 'test',
    '_box_config': True,
    'CamelCase': '21',
    '321CamelCase': 321,
    False: 'tree',
    'tuples_galore': ({'item': 3}, ({'item': 4}, 5))}
extended_test_dict.update(test_dict)

data_json_file = os.path.join(test_root, "data", "json_file.json")
data_yaml_file = os.path.join(test_root, "data", "yaml_file.yaml")
data_hearthstone = os.path.join(test_root, "data", "hearthstone_cards.json")
tmp_json_file = os.path.join(test_root, "tmp", "tmp_json_file.json")
tmp_yaml_file = os.path.join(test_root, "tmp", "tmp_yaml_file.yaml")

movie_data = {
    "movies": {
        "Spaceballs": {
            "imdb_stars": 7.1,
            "rating": "PG",
            "length": 96,
            "Director": "Mel Brooks",
            "Stars": [{"name": "Mel Brooks", "imdb": "nm0000316",
                       "role": "President Skroob"},
                      {"name": "John Candy", "imdb": "nm0001006",
                       "role": "Barf"},
                      {"name": "Rick Moranis", "imdb": "nm0001548",
                       "role": "Dark Helmet"}
                      ]
        },
        "Robin Hood: Men in Tights": {
            "imdb_stars": 6.7,
            "rating": "PG-13",
            "length": 104,
            "Director": "Mel Brooks",
            "Stars": [
                {"name": "Cary Elwes", "imdb": "nm0000144",
                 "role": "Robin Hood"},
                {"name": "Richard Lewis", "imdb": "nm0507659",
                 "role": "Prince John"},
                {"name": "Roger Rees", "imdb": "nm0715953",
                 "role": "Sheriff of Rottingham"},
                {"name": "Amy Yasbeck", "imdb": "nm0001865",
                 "role": "Marian"}
            ]
        }
    }
}


def function_example(value):
    yield value


class ClassExample(object):
    def __init__(self):
        self.a = 'a'
        self.b = 2


python_example_objects = (
    None,
    True,
    False,
    1,
    3.14,
    'abc',
    [1, 2, 3],
    {},
    ([], {}),
    lambda x: x ** 2,
    function_example,
    ClassExample()
)
