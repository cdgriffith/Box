#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import unittest
import json

try:
    import yaml
except ImportError:
    import ruamel.yaml as yaml

from box import Box, ConfigBox, LightBox, BoxList


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

    def test_light_box(self):
        test_dict = {'key1': 'value1',
                     'alist': [{'a': 1}],
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        box = LightBox(**test_dict)
        assert repr(box).startswith("<LightBox:")
        assert not isinstance(box.alist, BoxList)

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
        assert box['Key 2'].to_dict()['new_thing'] == "test2"
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

    def test_box_from_dict(self):
        ns = Box({"k1": "v1", "k2": {"k3": "v2"}})
        assert ns.k2.k3 == "v2"

    def test_box_from_bad_dict(self):
        try:
            Box('{"k1": "v1", "k2": {"k3": "v2"}}')
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

    def test_protected_box_methods(self):
        my_box = Box(a=3)
        try:
            my_box.to_dict = 'test'
        except AttributeError:
            pass
        else:
            raise AttributeError("Should not be able to set 'to_dict'")

        try:
            del my_box.to_json
        except AttributeError:
            pass
        else:
            raise AttributeError("Should not be able to delete 'to_dict'")

    def test_protected_lightbox_methods(self):
        my_box = LightBox(a=3)
        try:
            my_box.to_dict = 'test'
        except AttributeError:
            pass
        else:
            raise AttributeError("Should not be able to set 'to_dict'")

        try:
            del my_box.to_json
        except AttributeError:
            pass
        else:
            raise AttributeError("Should not be able to delete 'to_dict'")

    def test_bad_args(self):
        try:
            Box('123', '432')
        except TypeError:
            pass
        else:
            raise AssertionError("Shouldn't have worked")

    def test_box_inits(self):
        a = Box({'data': 2, 'count': 5})
        b = Box(data=2, count=5)
        c = Box({'data': 2, 'count': 1}, count=5)
        d = Box([('data', 2), ('count', 5)])
        e = Box({'a': [{'item': 3}, {'item': []}]})
        assert e.a[1].item == []
        assert a == b == c == d

    def test_lightbox_inits(self):
        a = LightBox({'data': 2, 'count': 5})
        b = LightBox(data=2, count=5)
        c = LightBox({'data': 2, 'count': 1}, count=5)
        d = LightBox([('data', 2), ('count', 5)])

        assert a == b == c == d

    def test_bad_inits(self):
        try:
            Box("testing")
        except ValueError:
            pass
        else:
            raise AssertionError("Should raise Value Error")

        try:
            Box(22)
        except ValueError:
            pass
        else:
            raise AssertionError("Should raise Value Error")

        try:
            Box(22, 33)
        except TypeError:
            pass
        else:
            raise AssertionError("Should raise Type Error")

    def test_bad_lightbox_inits(self):
        try:
            LightBox("testing")
        except ValueError:
            pass
        else:
            raise AssertionError("Should raise Value Error")

        try:
            LightBox(22)
        except ValueError:
            pass
        else:
            raise AssertionError("Should raise Value Error")

        try:
            LightBox(22, 33)
        except TypeError:
            pass
        else:
            raise AssertionError("Should raise Type Error")

    def test_create_subdicts(self):
        a = Box({'data': 2, 'count': 5})
        a.brand_new = {'subdata': 1}
        assert a.brand_new.subdata == 1
        a.new_list = [{'sub_list_item': 1}]
        assert a.new_list[0].sub_list_item == 1
        assert isinstance(a.new_list, BoxList)
        a.new_list2 = [[{'sub_list_item': 2}]]
        assert a.new_list2[0][0].sub_list_item == 2
        b = a.to_dict()
        assert not isinstance(b['new_list'], BoxList)

    def test_callable(self):
        a = Box({'data': 2, 'count': 5})
        assert a() == ('count', 'data')

    def test_to_json(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        a = Box(test_dict)
        assert json.loads(a.to_json(indent=0)) == test_dict

        a.to_json("test_json_file")
        with open("test_json_file") as f:
            data = json.load(f)
            assert data == test_dict

    def test_to_yaml(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        a = Box(test_dict)
        assert yaml.load(a.to_yaml()) == test_dict

    def test_to_yaml_file(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        a = Box(test_dict)
        a.to_yaml("test_yaml_file")
        with open("test_yaml_file") as f:
            data = yaml.load(f)
            assert data == test_dict

    def test_boxlist(self):
        new_list = BoxList({'item': x} for x in range(0, 10))
        new_list.extend([{'item': 22}])
        assert new_list[-1].item == 22
        new_list.append([{'bad_item': 33}])
        assert new_list[-1][0].bad_item == 33
        assert repr(new_list).startswith("<BoxList:")
        for x in new_list.to_list():
            assert not isinstance(x, (BoxList, Box, LightBox))
        new_list.insert(0, {'test': 5})
        new_list.insert(1, ['a', 'b'])
        new_list.append('x')
        assert new_list[0].test == 5
        assert isinstance(str(new_list), str)
        assert isinstance(new_list[1], BoxList)
        assert not isinstance(new_list.to_list(), BoxList)

    def test_dir(self):
        test_dict = {'key1': 'value1',
                     'not$allowed': 'fine_value',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        a = Box(test_dict)
        assert 'key1' in dir(a)
        assert 'not$allowed' not in dir(a)
        assert 'Key4' in a['Key 2']
        for item in ('to_yaml', 'to_dict', 'to_json'):
            assert item in dir(a)

        b = ConfigBox(test_dict)

        for item in ('to_yaml', 'to_dict', 'to_json', 'int', 'list', 'float'):
            assert item in dir(b)

    def test_update(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        a = Box(test_dict)
        a.update({'key1': {'new': 5}, 'Key 2': {"add_key": 6},
                  'lister': ['a']})
        a.update([('asdf', 'fdsa')])
        a.update(testkey=66)

        assert a.key1.new == 5
        assert a['Key 2'].add_key == 6
        assert "Key5" in a['Key 2'].Key4
        assert isinstance(a.key1, Box)
        assert isinstance(a.lister, BoxList)
        assert a.asdf == 'fdsa'
        assert a.testkey == 66

        b = LightBox(test_dict)
        b.update([('asdf', 'fdsa')])
        b.update(testkey=66)
        b.update({'key1': {'new': 5}, 'Key 2': {"add_key": 6}})

        assert b.key1.new == 5
        assert b['Key 2'].add_key == 6
        assert "Key5" in b['Key 2'].Key4
        assert isinstance(b.key1, LightBox)
        assert b.asdf == 'fdsa'
        assert b.testkey == 66

    def test_set_default(self):
        test_dict = {'key1': 'value1',
                     "Key 2": {"Key 3": "Value 3",
                               "Key4": {"Key5": "Value5"}}}
        a = Box(test_dict)

        new = a.setdefault("key3", {'item': 2})
        new_list = a.setdefault("lister", [{'gah': 7}])
        assert a.setdefault("key1", False) == 'value1'

        assert new == Box(item=2)
        assert new_list == BoxList([{'gah': 7}])
        assert a.key3.item == 2
        assert a.lister[0].gah == 7

        b = LightBox(test_dict)

        new = b.setdefault("key3", {'item': 2})
        new_list = b.setdefault("lister", [{'gah': 7}])

        assert b.setdefault("key1", False) == 'value1'
        assert new == Box(item=2)
        assert new_list == [{'gah': 7}]
        assert b.key3.item == 2
        assert b.lister[0]["gah"] == 7
        assert not isinstance(b.lister, BoxList)
