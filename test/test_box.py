#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import unittest

from box import Box, ConfigBox


class TestReuseBox(unittest.TestCase):

    def test_box(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        box = Box(**test_dict)
        assert box.key1 == test_dict['key1']
        assert dict(getattr(box, 'Key 2')) == test_dict['Key 2']
        setattr(box, 'TEST_KEY', 'VALUE')
        assert box.TEST_KEY == 'VALUE'
        delattr(box, 'TEST_KEY')
        assert 'TEST_KEY' not in box.to_dict(), box.to_dict()
        assert isinstance(box['Key 2'].Key4, Box)
        assert "'key1': 'value1'" in str(box)
        assert repr(box).startswith("<Box:")

    def test_box_modifiy_at_depth(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}

        box = Box(**test_dict)
        assert 'key1' in box
        assert 'key2' not in box
        box['Key 2'].new_thing = "test"
        assert box['Key 2'].new_thing == "test"
        box['Key 2'].new_thing += "2"
        assert box['Key 2'].new_thing == "test2"
        assert box['Key 2'].to_dict()['new_thing'] == "test2", box['Key 2'].to_dict()
        assert box.to_dict()['Key 2']['new_thing'] == "test2"
        box.__setattr__('key1', 1)
        assert box['key1'] == 1
        box.__delattr__('key1')
        assert 'key1' not in box

    def test_error_box(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}

        box = Box(**test_dict)
        try:
            getattr(box, 'hello')
        except AttributeError:
            pass
        else:
            raise AssertionError("Should not find 'hello' in the test dict")

    def test_box_tree(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        box = Box(**test_dict)
        result = box.tree_view(sep="    ")
        assert result.startswith("key1\n") or result.startswith("Key 2\n")
        assert "Key4" in result and "    Value5\n" not in result

    def test_box_from_dict(self):
        ns = Box({"k1": "v1", "k2": {"k3": "v2"}})
        assert ns.k2.k3 == "v2"

    def test_box_from_bad_dict(self):
        try:
            ns = Box('{"k1": "v1", '
                                               '"k2": {"k3": "v2"}}')
        except ValueError:
            assert True
        else:
            assert False, "Should have raised type error"

    def test_basic_box(self):
        a = Box(one=1, two=2, three=3)
        b = Box({'one': 1, 'two': 2, 'three': 3})
        c = Box((zip(['one', 'two', 'three'], [1, 2, 3])))
        d = Box(([('two', 2), ('one', 1), ('three', 3)]))
        e = Box(({'three': 3, 'one': 1, 'two': 2}))
        assert a == b == c == d == e

    def test_config_box(self):
        g = {"b0": 'no',
             "b1": 'yes',
             "b2": 'True',
             "b3": 'false',
             "b4": True,
             "i0": '34',
             "f0": '5.5',
             "f1": '3.333',
             "l0": '4,5,6,7,8',
             "l1": '[2 3 4 5 6]'}

        cns = ConfigBox(g)
        assert cns.list("l1", spliter=" ") == ["2", "3", "4", "5", "6"]
        assert cns.list("l0", mod=lambda x: int(x)) == [4, 5, 6, 7, 8]
        assert not cns.bool("b0")
        assert cns.bool("b1")
        assert cns.bool("b2")
        assert not cns.bool("b3")
        assert cns.int("i0") == 34
        assert cns.float("f0") == 5.5
        assert cns.float("f1") == 3.333
        assert cns.getboolean("b4"), cns.getboolean("b4")
        assert cns.getfloat("f0") == 5.5
        assert cns.getint("i0") == 34
        assert cns.getint("Hello!", 5) == 5
        assert cns.getfloat("Wooo", 4.4) == 4.4
        assert cns.getboolean("huh", True) is True
        assert cns.list("Waaaa", [1]) == [1]
        repr(cns)

    def test_protested_box(self):
        my_box = Box(a=3)
        try:
            my_box.to_dict = 'test'
        except AttributeError:
            pass
        else:
            raise AttributeError("Should not be able to set 'to_dict'")

    def test_bad_args(self):
        try:
            Box('123', '432')
        except TypeError:
            pass
        else:
            raise AssertionError("Shouldn't have worked")
