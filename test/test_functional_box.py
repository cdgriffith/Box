#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Test files gathered from json.org and yaml.org
from __future__ import absolute_import

from multiprocessing import Process, Queue
import pytest
import pickle

try:
    from test.common import *
except ImportError:
    from .common import *


class TestBoxFunctional:

    @pytest.fixture(autouse=True)
    def temp_dir_cleanup(self):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            os.mkdir(tmp_dir)
        except OSError:
            pass
        yield
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_box(self):
        bx = Box(**test_dict)
        assert bx.key1 == test_dict['key1']
        assert dict(getattr(bx, 'Key 2')) == test_dict['Key 2']
        setattr(bx, 'TEST_KEY', 'VALUE')
        assert bx.TEST_KEY == 'VALUE'
        delattr(bx, 'TEST_KEY')
        assert 'TEST_KEY' not in bx.to_dict(), bx.to_dict()
        assert isinstance(bx['Key 2'].Key4, Box)
        assert "'key1': 'value1'" in str(bx)
        assert repr(bx).startswith("<Box:")
        bx2 = Box([((3, 4), "A"), ("_box_config", 'test')])
        assert bx2[(3, 4)] == "A"
        assert bx2['_box_config'] == 'test'
        bx3 = Box(a=4, conversion_box=False)
        setattr(bx3, 'key', 2)
        assert bx3.key == 2
        bx3.__setattr__("Test", 3)
        assert bx3.Test == 3

    def test_box_modify_at_depth(self):
        bx = Box(**test_dict)
        assert 'key1' in bx
        assert 'key2' not in bx
        bx['Key 2'].new_thing = "test"
        assert bx['Key 2'].new_thing == "test"
        bx['Key 2'].new_thing += "2"
        assert bx['Key 2'].new_thing == "test2"
        assert bx['Key 2'].to_dict()['new_thing'] == "test2"
        assert bx.to_dict()['Key 2']['new_thing'] == "test2"
        bx.__setattr__('key1', 1)
        assert bx['key1'] == 1
        bx.__delattr__('key1')
        assert 'key1' not in bx

    def test_error_box(self):
        bx = Box(**test_dict)
        with pytest.raises(AttributeError):
            getattr(bx, 'hello')

    def test_box_from_dict(self):
        ns = Box({"k1": "v1", "k2": {"k3": "v2"}})
        assert ns.k2.k3 == "v2"

    def test_box_from_bad_dict(self):
        with pytest.raises(ValueError):
            Box('{"k1": "v1", "k2": {"k3": "v2"}}')

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

        cns = ConfigBox(bb=g)
        assert cns.bb.list("l1", spliter=" ") == ["2", "3", "4", "5", "6"]
        assert cns.bb.list("l0", mod=lambda x: int(x)) == [4, 5, 6, 7, 8]
        assert not cns.bb.bool("b0")
        assert cns.bb.bool("b1")
        assert cns.bb.bool("b2")
        assert not cns.bb.bool("b3")
        assert cns.bb.int("i0") == 34
        assert cns.bb.float("f0") == 5.5
        assert cns.bb.float("f1") == 3.333
        assert cns.bb.getboolean("b4"), cns.bb.getboolean("b4")
        assert cns.bb.getfloat("f0") == 5.5
        assert cns.bb.getint("i0") == 34
        assert cns.bb.getint("Hello!", 5) == 5
        assert cns.bb.getfloat("Wooo", 4.4) == 4.4
        assert cns.bb.getboolean("huh", True) is True
        assert cns.bb.list("Waaaa", [1]) == [1]
        assert repr(cns).startswith("<ConfigBox")

    def test_protected_box_methods(self):
        my_box = Box(a=3)
        with pytest.raises(AttributeError):
            my_box.to_dict = 'test'

        with pytest.raises(AttributeError):
            del my_box.to_json

    def test_bad_args(self):
        with pytest.raises(TypeError):
            Box('123', '432')

    def test_box_inits(self):
        a = Box({'data': 2, 'count': 5})
        b = Box(data=2, count=5)
        c = Box({'data': 2, 'count': 1}, count=5)
        d = Box([('data', 2), ('count', 5)])
        e = Box({'a': [{'item': 3}, {'item': []}]})
        assert e.a[1].item == []
        assert a == b == c == d

    def test_bad_inits(self):
        with pytest.raises(ValueError):
            Box("testing")

        with pytest.raises(ValueError):
            Box(22)

        with pytest.raises(TypeError):
            Box(22, 33)

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

    def test_to_json(self):
        a = Box(test_dict)
        assert json.loads(a.to_json(indent=0)) == test_dict

        a.to_json(tmp_json_file)
        with open(tmp_json_file) as f:
            data = json.load(f)
            assert data == test_dict

    def test_to_yaml(self):
        a = Box(test_dict)
        assert yaml.load(a.to_yaml(), Loader=yaml.SafeLoader) == test_dict

    def test_to_yaml_file(self):
        a = Box(test_dict)
        a.to_yaml(tmp_yaml_file)
        with open(tmp_yaml_file) as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
            assert data == test_dict

    def test_boxlist(self):
        new_list = BoxList({'item': x} for x in range(0, 10))
        new_list.extend([{'item': 22}])
        assert new_list[-1].item == 22
        new_list.append([{'bad_item': 33}])
        assert new_list[-1][0].bad_item == 33
        assert repr(new_list).startswith("<BoxList:")
        for x in new_list.to_list():
            assert not isinstance(x, (BoxList, Box))
        new_list.insert(0, {'test': 5})
        new_list.insert(1, ['a', 'b'])
        new_list.append('x')
        assert new_list[0].test == 5
        assert isinstance(str(new_list), str)
        assert isinstance(new_list[1], BoxList)
        assert not isinstance(new_list.to_list(), BoxList)

    def test_dir(self):
        a = Box(test_dict, camel_killer_box=True)
        assert 'key1' in dir(a)
        assert 'not$allowed' not in dir(a)
        assert 'Key4' in a['Key 2']
        for item in ('to_yaml', 'to_dict', 'to_json'):
            assert item in dir(a)

        assert a.big_camel == 'hi'
        assert 'big_camel' in dir(a)

        b = ConfigBox(test_dict)

        for item in ('to_yaml', 'to_dict', 'to_json', 'int', 'list', 'float'):
            assert item in dir(b)

    def test_update(self):
        a = Box(test_dict)
        a.update({'key1': {'new': 5}, 'Key 2': {"add_key": 6},
                  'lister': ['a']})
        a.update([('asdf', 'fdsa')])
        a.update(testkey=66)
        a.update({'items': 'test'})

        assert a['items'] == 'test'
        assert a.key1.new == 5
        assert a['Key 2'].add_key == 6
        assert "Key5" in a['Key 2'].Key4
        assert isinstance(a.key1, Box)
        assert isinstance(a.lister, BoxList)
        assert a.asdf == 'fdsa'
        assert a.testkey == 66

    def test_auto_attr(self):
        a = Box(test_dict, default_box=True)
        assert a.a.a.a.a == Box()
        a.b.b = 4
        assert a.b.b == 4

    def test_set_default(self):
        a = Box(test_dict)

        new = a.setdefault("key3", {'item': 2})
        new_list = a.setdefault("lister", [{'gah': 7}])
        assert a.setdefault("key1", False) == 'value1'

        assert new == Box(item=2)
        assert new_list == BoxList([{'gah': 7}])
        assert a.key3.item == 2
        assert a.lister[0].gah == 7

    def test_from_json_file(self):
        bx = Box.from_json(filename=data_json_file)
        assert isinstance(bx, Box)
        assert bx.widget.window.height == 500

    def test_from_yaml_file(self):
        bx = Box.from_yaml(filename=data_yaml_file)
        assert isinstance(bx, Box)
        assert bx.total == 4443.52

    def test_from_json(self):
        bx = Box.from_json(json.dumps(test_dict))
        assert isinstance(bx, Box)
        assert bx.key1 == 'value1'

    def test_from_yaml(self):
        bx = Box.from_yaml(yaml.dump(test_dict),
                           conversion_box=False,
                           default_box=True)
        assert isinstance(bx, Box)
        assert bx.key1 == 'value1'
        assert bx.Key_2 == Box()

    def test_bad_from_json(self):
        with pytest.raises(BoxError) as err:
            Box.from_json()

        with pytest.raises(BoxError) as err2:
            Box.from_json(json_string="[1]")

    def test_bad_from_yaml(self):
        with pytest.raises(BoxError) as err:
            Box.from_yaml()

        with pytest.raises(BoxError) as err2:
            Box.from_yaml('lol')

    def test_conversion_box(self):
        bx = Box(extended_test_dict, conversion_box=True)
        assert bx.Key_2.Key_3 == "Value 3"
        assert bx.x3 == 'howdy'
        assert bx.xnot == 'true'
        assert bx.x3_4 == 'test'
        with pytest.raises(AttributeError):
            getattr(bx, "(3, 4)")

    def test_frozen(self):
        bx = Box(extended_test_dict, frozen_box=True)

        assert isinstance(bx.alist, tuple)
        assert bx.alist[0] == {'a': 1}
        with pytest.raises(BoxError):
            bx.new = 3

        with pytest.raises(BoxError):
            bx['new'] = 3

        with pytest.raises(BoxError):
            del bx['not']

        with pytest.raises(BoxError):
            delattr(bx, "key1")

        with pytest.raises(TypeError):
            hash(bx)

        bx2 = Box(test_dict)
        with pytest.raises(TypeError):
            hash(bx2)

        bx3 = Box(test_dict, frozen_box=True)

        assert hash(bx3)

    def test_hashing(self):
        bx1 = Box(t=3, g=4, frozen_box=True)
        bx2 = Box(g=4, t=3, frozen_box=True)
        assert hash(bx1) == hash(bx2)

        bl1 = BoxList([1, 2, 3, 4], frozen_box=True)
        bl2 = BoxList([1, 2, 3, 4], frozen_box=True)
        bl3 = BoxList([2, 1, 3, 4], frozen_box=True)
        assert hash(bl2) == hash(bl1)
        assert hash(bl3) != hash(bl2)

        with pytest.raises(TypeError):
            hash(BoxList([1, 2, 3]))

    def test_frozen_list(self):
        bl = BoxList([5, 4, 3], frozen_box=True)
        with pytest.raises(BoxError):
            bl.pop(1)
        with pytest.raises(BoxError):
            bl.remove(4)
        with pytest.raises(BoxError):
            bl.sort()
        with pytest.raises(BoxError):
            bl.reverse()
        with pytest.raises(BoxError):
            bl.append('test')
        with pytest.raises(BoxError):
            bl.extend([4])
        with pytest.raises(BoxError):
            del bl[0]
        with pytest.raises(BoxError):
            bl[0] = 5
        bl2 = BoxList([5, 4, 3])
        del bl2[0]
        assert bl2[0] == 4
        bl2[1] = 4
        assert bl2[1] == 4

    def test_config(self):
        bx = Box(extended_test_dict)
        assert bx['_box_config'] is True
        assert isinstance(bx._box_config, dict)
        with pytest.raises(BoxError):
            delattr(bx, '_box_config')
        bx._box_config

    def test_default_box(self):
        bx = Box(test_dict, default_box=True, default_box_attr={'hi': 'there'})
        assert bx.key_88 == {'hi': 'there'}

        bx2 = Box(test_dict, default_box=True, default_box_attr=Box)
        assert isinstance(bx2.key_77, Box)

        bx3 = Box(default_box=True, default_box_attr=3)
        assert bx3.hello == 3

        bx4 = Box(default_box=True, default_box_attr=ConfigBox)
        assert isinstance(bx4.bbbbb, ConfigBox)

    def test_camel_killer_box(self):
        td = extended_test_dict.copy()
        td['CamelCase'] = 'Item'
        td['321CamelCaseFever!'] = 'Safe'

        kill_box = Box(td, camel_killer_box=True, conversion_box=False)
        assert kill_box.camel_case == 'Item'
        assert kill_box['321CamelCaseFever!'] == 'Safe'

        con_kill_box = Box(td, conversion_box=True, camel_killer_box=True)
        assert con_kill_box.camel_case == 'Item'
        assert con_kill_box.x321_camel_case_fever == 'Safe'

    def test_default_and_camel_killer_box(self):
        td = extended_test_dict.copy()
        td['CamelCase'] = 'Item'
        killer_default_box = Box(td, camel_killer_box=True, default_box=True)
        assert killer_default_box.camel_case == 'Item'
        assert killer_default_box.CamelCase == 'Item'
        assert isinstance(killer_default_box.does_not_exist, Box)
        assert isinstance(killer_default_box['does_not_exist'], Box)

    def test_property_box(self):
        td = test_dict.copy()
        td['inner'] = {'CamelCase': 'Item'}

        pbox = SBox(td, camel_killer_box=True)
        assert isinstance(pbox.inner, SBox)
        assert pbox.inner.camel_case == 'Item'
        assert json.loads(pbox.json)['inner']['CamelCase'] == 'Item'
        test_item = yaml.load(pbox.yaml, Loader=yaml.SafeLoader)
        assert test_item['inner']['CamelCase'] == 'Item'
        assert repr(pbox['inner']).startswith('<ShorthandBox')
        assert not isinstance(pbox.dict, Box)
        assert pbox.dict['inner']['CamelCase'] == 'Item'

    def test_box_list_to_json(self):
        bl = BoxList([{'item': 1, 'CamelBad': 2}])
        assert json.loads(bl.to_json())[0]['item'] == 1

    def test_box_list_from_json(self):
        alist = [{'item': 1}, {'CamelBad': 2}]
        json_list = json.dumps(alist)
        bl = BoxList.from_json(json_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_json(json.dumps({'a': 2}))

    def test_box_list_to_yaml(self):
        bl = BoxList([{'item': 1, 'CamelBad': 2}])
        assert yaml.load(bl.to_yaml(), Loader=yaml.SafeLoader)[0]['item'] == 1

    def test_box_list_from_yaml(self):
        alist = [{'item': 1}, {'CamelBad': 2}]
        yaml_list = yaml.dump(alist)
        bl = BoxList.from_yaml(yaml_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_yaml(yaml.dump({'a': 2}))

    def test_boxlist_box_it_up(self):
        bxl = BoxList([extended_test_dict])
        bxl.box_it_up()
        assert "Key 3" in bxl[0].Key_2._box_config['__converted']

    def test_box_modify_tuples(self):
        bx = Box(extended_test_dict, modify_tuples_box=True)
        assert bx.tuples_galore[0].item == 3
        assert isinstance(bx.tuples_galore[0], Box)
        assert isinstance(bx.tuples_galore[1], tuple)

    def test_box_set_attribs(self):
        bx = Box(extended_test_dict, conversion_box=False,
                 camel_killer_box=True)
        bx.camel_case = {'new': 'item'}
        assert bx['CamelCase'] == Box(new='item')

        bx2 = Box(extended_test_dict)
        bx2.Key_2 = 4
        assert bx2["Key 2"] == 4

    def test_functional_hearthstone_data(self):
        hearth = Box.from_json(filename=data_hearthstone,
                               conversion_box=True,
                               camel_killer_box=True,
                               default_box=False)
        assert hearth.the_jade_lotus

        with pytest.raises(AttributeError):
            hearth._bad_value

        with pytest.raises(AttributeError):
            hearth.the_jade_lotus._bad_value

        base_config = hearth._Box__box_config()
        jade_config = hearth.the_jade_lotus._Box__box_config()

        assert base_config == jade_config, "{} != {}".format(base_config,
                                                             jade_config)

    def test_functional_spaceballs(self):
        my_box = Box(movie_data)

        my_box.movies.Spaceballs.Stars.append(
            {"name": "Bill Pullman", "imdb": "nm0000597",
             "role": "Lone Starr"})
        assert my_box.movies.Spaceballs.Stars[-1].role == "Lone Starr"
        assert my_box.movies.Robin_Hood_Men_in_Tights.length == 104
        my_box.movies.Robin_Hood_Men_in_Tights.Stars.pop(0)
        assert my_box.movies.Robin_Hood_Men_in_Tights.Stars[
                   0].name == "Richard Lewis"

    def test_circular_references(self):
        circular_dict = {}
        circular_dict['a'] = circular_dict
        bx = Box(circular_dict, box_it_up=True)
        assert bx.a.a == bx.a
        circular_dict_2 = bx.a.a.a.to_dict()
        assert str(circular_dict_2) == "{'a': {...}}"

        bx2 = Box(circular_dict, k=circular_dict)
        assert bx2.k == bx2.a

        with pytest.raises(ValueError):
            bx.to_json()

        circular_list = []
        circular_list.append(circular_list)
        bl = BoxList(circular_list)
        assert bl == bl[0]
        assert isinstance(bl[0], BoxList)
        circular_list_2 = bl.to_list()
        assert circular_list_2 == circular_list_2[0]
        assert isinstance(circular_list_2, list)

    def test_to_multiline(self):
        a = BoxList([Box(a=1), Box(b=2), Box(three=5)])

        a.to_json(tmp_json_file, multiline=True)
        count = 0
        with open(tmp_json_file) as f:
            for line in f:
                assert isinstance(json.loads(line), dict)
                count += 1
        assert count == 3

    def test_from_multiline(self):
        content = '{"a": 2}\n{"b": 3}\r\n \n'
        with open(tmp_json_file, 'w') as f:
            f.write(content)

        a = BoxList.from_json(filename=tmp_json_file, multiline=True)
        assert a[1].b == 3

    def test_duplicate_errors(self):
        with pytest.raises(BoxError) as err:
            Box({"?a": 1, "!a": 3}, box_duplicates="error")

        Box({"?a": 1, "!a": 3}, box_duplicates="ignore")

        with pytest.warns(UserWarning) as warning:
            Box({"?a": 1, "!a": 3}, box_duplicates="warn")
        assert warning[0].message.args[0].startswith("Duplicate")

        my_box = Box({"?a": 1}, box_duplicates="error")
        with pytest.raises(BoxError):
            my_box['^a'] = 3

    def test_copy(self):
        my_box = Box(movie_data)
        bb = my_box.copy()
        assert my_box == bb
        assert isinstance(bb, Box)

        aa = copy.deepcopy(my_box)
        assert my_box == aa
        assert isinstance(aa, Box)

        cc = my_box.__copy__()
        assert my_box == cc
        assert isinstance(cc, Box)

        dd = BoxList([my_box])
        assert dd == copy.copy(dd)
        assert isinstance(copy.copy(dd), BoxList)

    def test_custom_key_errors(self):
        my_box = Box()

        with pytest.raises(BoxKeyError):
            my_box.g

        with pytest.raises(AttributeError):
            my_box.g

        with pytest.raises(KeyError):
            my_box['g']

        with pytest.raises(BoxKeyError):
            my_box['g']

        with pytest.raises(BoxError):
            my_box['g']

    def test_pickle(self):
        pic_file = os.path.join(tmp_dir, 'test.p')
        pic2_file = os.path.join(tmp_dir, 'test.p2')
        bb = Box(movie_data, conversion_box=False)
        pickle.dump(bb, open(pic_file, 'wb'))
        loaded = pickle.load(open(pic_file, 'rb'))
        assert bb == loaded
        assert loaded._box_config['conversion_box'] is False

        ll = [[Box({'a': 'b'}, ordered_box=True)], [[{'c': 'g'}]]]
        bx = BoxList(ll)
        pickle.dump(bx, open(pic2_file, 'wb'))
        loaded2 = pickle.load(open(pic2_file, 'rb'))
        assert bx == loaded2
        loaded2.box_options = bx.box_options

    def test_pickle_default_box(self):
        bb = Box(default_box=True)
        loaded = pickle.loads(pickle.dumps(bb))
        assert bb == loaded

    def test_conversion_dup_only(self):
        with pytest.raises(BoxError):
            Box(movie_data, conversion_box=False, box_duplicates='error')

    def test_values(self):
        b = Box()
        b.foo = {}
        assert isinstance(list(b.values())[0], Box)
        c = Box()
        c.foohoo = []
        assert isinstance(list(c.values())[0], BoxList)
        d = Box(movie_data)
        assert len(movie_data["movies"].values()) == len(d.movies.values())

    def test_items(self):
        b = Box()
        b.foo = {}
        assert isinstance(list(b.items())[0][1], Box)
        c = Box()
        c.foohoo = []
        assert isinstance(list(c.items())[0][1], BoxList)
        d = Box(movie_data)
        assert len(movie_data["movies"].items()) == len(d.movies.items())

    def test_get(self):
        bx = Box()
        bx["c"] = {}
        assert isinstance(bx.get("c"), Box)
        assert isinstance(bx.get("b", {}), Box)
        assert "a" in bx.get("a", Box(a=1, conversion_box=False))
        assert isinstance(bx.get("a", [1, 2]), BoxList)

    def test_get_default_box(self):
        bx = Box(default_box=True)
        assert bx.get('test', 4) == 4
        assert isinstance(bx.get('a'), Box)

    def test_is_in(self):
        bx = Box()
        dbx = Box(default_box=True)
        assert "a" not in bx
        assert "a" not in dbx
        bx["b"] = 1
        dbx["b"] = {}
        assert "b" in bx
        assert "b" in dbx

    def test_through_queue(self):
        my_box = Box(a=4, c={"d": 3})

        queue = Queue()
        queue.put(my_box)

        p = Process(target=mp_queue_test, args=(queue,))
        p.start()
        p.join()

        assert queue.get(timeout=1)

    def test_update_with_integer(self):
        bx = Box()
        bx[1] = 4
        assert bx[1] == 4
        bx.update({1: 2})
        assert bx[1] == 2

    def test_get_box_config(self):
        bx = Box()
        bx_config = bx.__getattr__('_box_config')
        assert bx_config
        with pytest.raises(BoxKeyError):
            bx['_box_config']

    def test_ordered_box(self):
        bx = Box(h=1, ordered_box=True)
        bx.a = 1
        bx.c = 4
        bx['g'] = 7
        bx.d = 2
        assert bx.keys() == ['h', 'a', 'c', 'g', 'd']
        assert list(bx.__iter__()) == ['h', 'a', 'c', 'g', 'd']
        assert list(reversed(bx)) == ['d', 'g', 'c', 'a', 'h']
        del bx.a
        bx.pop('c')
        bx.__delattr__('g')
        assert bx.keys() == ['h', 'd']

    def test_intact_types_dict(self):
        from collections import OrderedDict
        bx = Box(a=OrderedDict([('y', 1), ('x', 2)]))
        assert isinstance(bx.a, Box)
        assert not isinstance(bx.a, OrderedDict)
        bx = Box(a=OrderedDict([('y', 1), ('x', 2)]),
                 box_intact_types=[OrderedDict])
        assert isinstance(bx.a, OrderedDict)
        assert not isinstance(bx.a, Box)

    def test_intact_types_list(self):
        class MyList(list):
            pass

        bl = BoxList([[1, 2], MyList([3, 4])], box_intact_types=(MyList,))
        assert isinstance(bl[0], BoxList)

    def test_pop(self):
        bx = Box(a=4, c={"d": 3})
        assert bx.pop('a') == 4
        with pytest.raises(BoxKeyError):
            bx.pop('b')
        assert bx.pop('a', None) is None
        assert bx.pop('a', True) is True
        assert bx == {'c': {"d": 3}}
        with pytest.raises(BoxError):
            bx.pop(1, 2, 3)
        assert bx.pop('c', True) is not True

    def test_pop_items(self):
        bx = Box(a=4)
        assert bx.popitem() == ('a', 4)
        with pytest.raises(BoxKeyError):
            assert bx.popitem()

    def test_iter(self):
        bx = Box(ordered_box=True)
        bx.a = 1
        bx.c = 2
        assert list(bx.__iter__()) == ['a', 'c']

    def test_revered(self):
        bx = Box(ordered_box=True)
        bx.a = 1
        bx.c = 2
        assert list(reversed(bx)) == ['c', 'a']

    def test_clear(self):
        bx = Box(ordered_box=True)
        bx.a = 1
        bx.c = 4
        bx['g'] = 7
        bx.d = 2
        assert bx.keys() == ['a', 'c', 'g', 'd']
        bx.clear()
        assert bx == {}
        assert bx.keys() == []

    def test_bad_recursive(self):
        b = Box()
        bl = b.setdefault("l", [])
        bl.append(["foo"])
        assert bl == [['foo']], bl

    def test_inheritance_copy(self):

        class Box2(Box):
            pass

        class SBox2(SBox):
            pass

        class ConfigBox2(ConfigBox):
            pass

        b = Box2(a=1)
        c = b.copy()
        assert c == b
        assert isinstance(c, Box)
        c = b.__copy__()
        assert c == b
        assert isinstance(c, Box)

        d = SBox2(a=1)
        e = d.copy()
        assert e == d
        assert isinstance(e, SBox)
        e = d.__copy__()
        assert e == d
        assert isinstance(e, SBox)

        f = ConfigBox2(a=1)
        g = f.copy()
        assert g == f
        assert isinstance(g, ConfigBox)
        g = f.__copy__()
        assert g == f
        assert isinstance(g, ConfigBox)


class TestBoxObject:

    @pytest.mark.parametrize('wrapped', python_example_objects)
    def test_box_object_generic(self, wrapped):
        b = BoxObject(wrapped)
        assert b == wrapped
        assert not (b is wrapped)
        assert isinstance(b, BoxObject)
        assert isinstance(b, type(wrapped))
        b.box_key = 'secret_word'
        assert b.box_key == 'secret_word'
        assert 'box_key' in b.__dict__
        assert isinstance(b.__dict__, Box)
        assert b.__dict__ != getattr(b.__wrapped__, '__dict__', None)
        with pytest.raises(AttributeError):
            b.foo
        if hasattr(b.__wrapped__, 'b'):
            b.b = 1
            assert b.__wrapped__.b == 1

    @pytest.mark.parametrize('wrapped', python_example_objects)
    def test_box_object_deletion(self, wrapped):
        b = BoxObject(wrapped)
        with pytest.raises(TypeError):
            b.__dict__ = 0
        del b.__dict__
        assert b.__dict__ == getattr(b.__wrapped__, '__dict__', {})
        with pytest.raises(AttributeError):
            del b.foo
        if hasattr(b.__wrapped__, 'a'):
            del b.a
        if not hasattr(b.__wrapped__, 'b'):
            with pytest.raises(AttributeError):
                del b.b

    def test_box_object_attributes(self):
        b = BoxObject(test_dict, **movie_data)
        assert b == test_dict
        assert not (b is test_dict)
        assert b.__dict__ == movie_data
        assert isinstance(b.__dict__, Box)
        assert b.__dict__ != getattr(b.__wrapped__, '__dict__', None)
        for k, v in movie_data.items():
            assert getattr(b, k) == v
            tagged = k + '_b'
            setattr(b, tagged, [v])
            assert getattr(b, tagged) == [v]
            setattr(b, k, getattr(b, tagged))
            assert getattr(b, k) == [v]
        for k, v in test_dict.items():
            assert k in b
            assert b[k] == v

    def test_box_object_call(self):
        def f(*args, **kwargs):
            return args, kwargs

        b = BoxObject(f)
        assert b(list(test_dict),
                 **movie_data) == f(list(test_dict), **movie_data)

    def test_box_object_double_args(self):
        with pytest.raises(TypeError):
            BoxObject(function_example,
                      zip([1, 2, 3], [4, 5, 6]),
                      **movie_data)


def mp_queue_test(q):
    bx = q.get(timeout=1)
    try:
        assert isinstance(bx, Box)
        assert bx.a == 4
    except AssertionError:
        q.put(False)
    else:
        q.put(True)
