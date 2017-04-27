import unittest
import json
import os

try:
    import yaml
except ImportError:
    import ruamel.yaml as yaml

import box
from box import *
test_root = os.path.abspath(os.path.dirname(__file__))

test_dict = {'key1': 'value1',
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
    'tuples_galore': ({'item': 3}, ({'item': 4}, 5))}
extended_test_dict.update(test_dict)


