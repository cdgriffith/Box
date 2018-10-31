#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import absolute_import

try:
    from test.common import *
except ImportError:
    from .common import *


class TestBoxUnit(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            os.mkdir(tmp_dir)
        except OSError:
            pass

    def tearDown(self):
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_safe_attrs(self):
        assert box._safe_attr("BAD!KEY!1", camel_killer=False) == "BAD_KEY_1"
        assert box._safe_attr("BAD!KEY!2", camel_killer=True) == "bad_key_2"
        assert box._safe_attr((5, 6, 7), camel_killer=False) == "x5_6_7"
        assert box._safe_attr(356, camel_killer=False) == "x356"

    def test_camel_killer(self):
        assert box._camel_killer("CamelCase") == "camel_case"
        assert box._camel_killer("Terrible321KeyA") == "terrible321_key_a"

    def test_safe_key(self):
        assert box._safe_key(("wer", "ah", 3)) == "('wer', 'ah', 3)"

    def test_recursive_tuples(self):
        out = box._recursive_tuples(({'test': 'a'},
                                     ({'second': 'b'},
                                      {'third': 'c'}, ('fourth',))),
                                    dict, recreate_tuples=True)
        assert isinstance(out, tuple)
        assert isinstance(out[0], dict)
        assert out[0] == {'test': 'a'}
        assert isinstance(out[1], tuple)
        assert isinstance(out[1][2], tuple)
        assert out[1][0] == {'second': 'b'}

    def test_to_json(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        movie_string = box._to_json(movie_data)
        assert "Rick Moranis" in movie_string
        box._to_json(movie_data, filename=m_file)
        assert "Rick Moranis" in open(m_file).read()
        assert json.load(open(m_file)) == json.loads(movie_string)

    def test_to_yaml(self):
        m_file = os.path.join(tmp_dir, "movie_data")
        movie_string = box._to_yaml(movie_data)
        assert "Rick Moranis" in movie_string
        box._to_yaml(movie_data, filename=m_file)
        assert "Rick Moranis" in open(m_file).read()
        assert yaml.load(open(m_file), Loader=yaml.SafeLoader) == yaml.load(
            movie_string, Loader=yaml.SafeLoader)
