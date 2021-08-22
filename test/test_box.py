#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test files gathered from json.org and yaml.org
import copy
import json
import os
import pickle
import platform
import shutil
from multiprocessing import Queue
from pathlib import Path
from test.common import (
    data_json_file,
    data_yaml_file,
    extended_test_dict,
    movie_data,
    test_dict,
    test_root,
    tmp_dir,
    tmp_json_file,
    tmp_msgpack_file,
    tmp_yaml_file,
)

import pytest
import ruamel.yaml as yaml

from box import Box, BoxError, BoxKeyError, BoxList, ConfigBox, SBox, box
from box.box import _get_dot_paths  # type: ignore


def mp_queue_test(q):
    bx = q.get()
    try:
        assert isinstance(bx, Box)
        assert bx.a == 4
    except AssertionError:
        q.put(False)
    else:
        q.put(True)


class TestBox:
    @pytest.fixture(autouse=True)
    def temp_dir_cleanup(self):
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        try:
            os.mkdir(str(tmp_dir))
        except OSError:
            pass
        yield
        shutil.rmtree(str(tmp_dir), ignore_errors=True)

    def test_safe_attrs(self):
        assert Box()._safe_attr("BAD!KEY!1") == "BAD_KEY_1"
        assert Box(camel_killer_box=True)._safe_attr("BAD!KEY!2") == "bad_key_2"
        assert Box()._safe_attr((5, 6, 7)) == "x5_6_7"
        assert Box()._safe_attr(356) == "x356"

    def test_camel_killer(self):
        assert box._camel_killer("CamelCase") == "camel_case"
        assert box._camel_killer("Terrible321KeyA") == "terrible321_key_a"
        bx = Box(camel_killer_box=True, conversion_box=False)

        bx.DeadCamel = 3
        assert bx["dead_camel"] == 3
        assert bx.dead_camel == 3

        bx["BigCamel"] = 4
        assert bx["big_camel"] == 4
        assert bx.big_camel == 4
        assert bx.BigCamel == 4

        bx1 = Box(camel_killer_box=True, conversion_box=True)
        bx1["BigCamel"] = 4
        bx1.DeadCamel = 3
        assert bx1["big_camel"] == 4
        assert bx1["dead_camel"] == 3
        assert bx1.big_camel == 4
        assert bx1.dead_camel == 3
        assert bx1.BigCamel == 4
        assert bx1["BigCamel"] == 4

        del bx1.DeadCamel
        assert "dead_camel" not in bx1
        del bx1["big_camel"]
        assert "big_camel" not in bx1
        assert len(bx1.keys()) == 0

    def test_recursive_tuples(self):
        out = box._recursive_tuples(
            ({"test": "a"}, ({"second": "b"}, {"third": "c"}, ("fourth",))), dict, recreate_tuples=True
        )
        assert isinstance(out, tuple)
        assert isinstance(out[0], dict)
        assert out[0] == {"test": "a"}
        assert isinstance(out[1], tuple)
        assert isinstance(out[1][2], tuple)
        assert out[1][0] == {"second": "b"}

    def test_box(self):
        bx = Box(**test_dict)
        assert bx.key1 == test_dict["key1"]
        assert dict(getattr(bx, "Key 2")) == test_dict["Key 2"]
        setattr(bx, "TEST_KEY", "VALUE")
        assert bx.TEST_KEY == "VALUE"
        delattr(bx, "TEST_KEY")
        assert "TEST_KEY" not in bx.to_dict(), bx.to_dict()
        assert isinstance(bx["Key 2"].Key4, Box)
        assert "'key1': 'value1'" in str(bx)
        assert repr(bx).startswith("<Box:")
        bx2 = Box([((3, 4), "A"), ("_box_config", "test")])
        assert bx2[(3, 4)] == "A"
        assert bx2["_box_config"] == "test"
        bx3 = Box(a=4, conversion_box=False)
        setattr(bx3, "key", 2)
        assert bx3.key == 2
        bx3.__setattr__("Test", 3)
        assert bx3.Test == 3

    def test_box_modify_at_depth(self):
        bx = Box(**test_dict)
        assert "key1" in bx
        assert "key2" not in bx
        bx["Key 2"].new_thing = "test"
        assert bx["Key 2"].new_thing == "test"
        bx["Key 2"].new_thing += "2"
        assert bx["Key 2"].new_thing == "test2"
        assert bx["Key 2"].to_dict()["new_thing"] == "test2"
        assert bx.to_dict()["Key 2"]["new_thing"] == "test2"
        bx.__setattr__("key1", 1)
        assert bx["key1"] == 1
        bx.__delattr__("key1")
        assert "key1" not in bx

    def test_error_box(self):
        bx = Box(**test_dict)
        with pytest.raises(AttributeError):
            getattr(bx, "hello")

    def test_box_from_dict(self):
        ns = Box({"k1": "v1", "k2": {"k3": "v2"}})
        assert ns.k2.k3 == "v2"

    def test_box_from_bad_dict(self):
        with pytest.raises(ValueError):
            Box('{"k1": "v1", "k2": {"k3": "v2"}}')

    def test_basic_box(self):
        a = Box(one=1, two=2, three=3)
        b = Box({"one": 1, "two": 2, "three": 3})
        c = Box((zip(["one", "two", "three"], [1, 2, 3])))
        d = Box(([("two", 2), ("one", 1), ("three", 3)]))
        e = Box(({"three": 3, "one": 1, "two": 2}))
        assert a == b == c == d == e

    def test_protected_box_methods(self):
        my_box = Box(a=3)
        with pytest.raises(AttributeError):
            my_box.to_dict = "test"

        with pytest.raises(AttributeError):
            del my_box.to_json

    def test_bad_args(self):
        with pytest.raises(TypeError):
            Box("123", "432")

    def test_box_inits(self):
        a = Box({"data": 2, "count": 5})
        b = Box(data=2, count=5)
        c = Box({"data": 2, "count": 1}, count=5)
        d = Box([("data", 2), ("count", 5)])
        e = Box({"a": [{"item": 3}, {"item": []}]})
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
        a = Box({"data": 2, "count": 5})
        a.brand_new = {"subdata": 1}
        assert a.brand_new.subdata == 1
        a.new_list = [{"sub_list_item": 1}]
        assert a.new_list[0].sub_list_item == 1
        assert isinstance(a.new_list, BoxList)
        a.new_list2 = [[{"sub_list_item": 2}]]
        assert a.new_list2[0][0].sub_list_item == 2
        b = a.to_dict()
        assert not isinstance(b["new_list"], BoxList)

    def test_to_json_basic(self):
        a = Box(test_dict)
        assert json.loads(a.to_json(indent=0)) == test_dict

        a.to_json(tmp_json_file)
        with open(tmp_json_file) as f:
            data = json.load(f)
            assert data == test_dict

    def test_to_yaml_basic(self):
        a = Box(test_dict)
        assert yaml.load(a.to_yaml(), Loader=yaml.SafeLoader) == test_dict

    def test_to_yaml_file(self):
        a = Box(test_dict)
        a.to_yaml(tmp_yaml_file)
        with open(tmp_yaml_file) as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
            assert data == test_dict

    def test_dir(self):
        a = Box(test_dict, camel_killer_box=True)
        assert "key1" in dir(a)
        assert "not$allowed" not in dir(a)
        assert "key4" in a["key 2"]
        for item in ("to_yaml", "to_dict", "to_json"):
            assert item in dir(a)

        assert a.big_camel == "hi"
        assert "big_camel" in dir(a)

    def test_update(self):
        a = Box(test_dict)
        a.grand = 1000
        a.update({"key1": {"new": 5}, "Key 2": {"add_key": 6}, "lister": ["a"]})
        a.update([("asdf", "fdsa")])
        a.update(testkey=66)
        a.update({"items": {"test": "pme"}})
        a.update({"key1": {"gg": 4}})
        b = Box()
        b.update(item=1)
        b.update(E=1)
        b.update(__m=1)
        with pytest.raises(ValueError):
            b.update("test")

        assert a.grand == 1000
        assert a["grand"] == 1000
        assert isinstance(a["items"], Box)
        assert a["items"].test == "pme"
        assert a["Key 2"].add_key == 6
        assert isinstance(a.key1, Box)
        assert isinstance(a.lister, BoxList)
        assert a.asdf == "fdsa"
        assert a.testkey == 66
        assert a.key1.gg == 4
        assert "new" not in a.key1.keys()

    def test_merge_update(self):
        a = Box(test_dict)
        a.grand = 1000
        a.merge_update({"key1": {"new": 5}, "Key 2": {"add_key": 6}, "lister": ["a"]})
        a.merge_update([("asdf", "fdsa")])
        a.merge_update(testkey=66)
        a.merge_update({"items": {"test": "pme"}})
        a.merge_update({"key1": {"gg": 4}})
        b = Box()
        b.merge_update(item=1)
        b.merge_update(E=4)
        b.merge_update(__m=1)

        assert a.grand == 1000
        assert a["grand"] == 1000
        assert isinstance(a["items"], Box)
        assert a["items"].test == "pme"
        assert a.key1.new == 5
        assert a["Key 2"].add_key == 6
        assert isinstance(a.key1, Box)
        assert isinstance(a.lister, BoxList)
        assert a.asdf == "fdsa"
        assert a.testkey == 66
        assert a.key1.new == 5
        assert a.key1.gg == 4
        with pytest.raises(ValueError):
            b.merge_update("test")

    def test_auto_attr(self):
        a = Box(test_dict, default_box=True)
        assert isinstance(a.a.a.a.a, Box)
        a.b.b = 4
        assert a.b.b == 4

    def test_set_default_dict(self):
        a = Box(test_dict)
        new = a.setdefault("key3", {})
        new.yy = 8
        assert a.key3.yy == 8

    def test_set_default(self):
        a = Box(test_dict)

        new = a.setdefault("key3", {"item": 2})
        new_list = a.setdefault("lister", [{"gah": 7}])
        assert a.setdefault("key1", False) == "value1"

        assert new == Box(item=2)
        assert new_list == BoxList([{"gah": 7}])
        assert a.key3.item == 2
        assert a.lister[0].gah == 7

    def test_set_default_box_dots(self):
        a = Box(box_dots=True)
        a["x"] = {"y": 10}
        a.setdefault("x.y", 20)
        assert a["x.y"] == 10

        a["lists"] = [[[{"test": "here"}], {1, 2}], (4, 5)]
        assert list(_get_dot_paths(a)) == [
            "x",
            "x.y",
            "lists",
            "lists[0]",
            "lists[0][0]",
            "lists[0][0][0]",
            "lists[0][0][0].test",
            "lists[0][1]",
            "lists[1]",
        ]

        t = Box({"a": 1}, default_box=True, box_dots=True, default_box_none_transform=False)
        assert t.setdefault("b", [1, 2]) == [1, 2]
        assert t == Box(a=1, b=[1, 2])
        assert t.setdefault("c", [{"d": 2}]) == BoxList([{"d": 2}])

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
        assert bx.key1 == "value1"

    def test_from_yaml(self):
        bx = Box.from_yaml(yaml.dump(test_dict), conversion_box=False, default_box=True)
        assert isinstance(bx, Box)
        assert bx.key1 == "value1"
        assert bx.Key_2 == Box()

    def test_bad_from_json(self):
        with pytest.raises(BoxError):
            Box.from_json()

        with pytest.raises(BoxError):
            Box.from_json(json_string="[1]")

    def test_bad_from_yaml(self):
        with pytest.raises(BoxError):
            Box.from_yaml()

        with pytest.raises(BoxError):
            Box.from_yaml("lol")

    def test_conversion_box(self):
        bx = Box(extended_test_dict, conversion_box=True)
        assert bx.Key_2.Key_3 == "Value 3"
        assert bx.x3 == "howdy"
        assert bx.xnot == "true"
        assert bx.x3_4 == "test"
        with pytest.raises(AttributeError):
            getattr(bx, "(3, 4)")

    def test_frozen(self):
        bx = Box(extended_test_dict, frozen_box=True)

        assert isinstance(bx.alist, tuple)
        assert bx.alist[0] == {"a": 1}
        with pytest.raises(BoxError):
            bx.new = 3

        with pytest.raises(BoxError):
            bx["new"] = 3

        with pytest.raises(BoxError):
            del bx["not"]

        with pytest.raises(BoxError):
            delattr(bx, "key1")

        with pytest.raises(TypeError):
            hash(bx)

        with pytest.raises(BoxError):
            bx.clear()

        with pytest.raises(BoxError):
            bx.pop("alist")

        with pytest.raises(BoxError):
            bx.popitem()

        with pytest.raises(BoxError):
            bx.popitem()

        with pytest.raises(BoxError):
            bx.update({"another_list": []})

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

    def test_config(self):
        bx = Box(extended_test_dict)
        assert bx["_box_config"] is True
        assert isinstance(bx._box_config, dict)
        with pytest.raises(BoxError):
            delattr(bx, "_box_config")
        bx._box_config

    def test_default_box(self):
        bx = Box(test_dict, default_box=True, default_box_attr={"hi": "there"})
        assert bx.key_88 == {"hi": "there"}
        assert bx["test"] == {"hi": "there"}

        bx2 = Box(test_dict, default_box=True, default_box_attr=Box)
        assert isinstance(bx2.key_77, Box)

        bx3 = Box(default_box=True, default_box_attr=3)
        assert bx3.hello == 3

        bx4 = Box(default_box=True, default_box_attr=None)
        assert bx4.who_is_there is None

        bx5 = Box(default_box=True, default_box_attr=[])
        assert isinstance(bx5.empty_list_please, list)
        assert len(bx5.empty_list_please) == 0
        bx5.empty_list_please.append(1)
        assert bx5.empty_list_please[0] == 1

        bx6 = Box(default_box=True, default_box_attr=[])
        my_list = bx6.get("new_list")
        my_list.append(5)
        assert bx6.get("new_list")[0] == 5

        bx7 = Box(default_box=True, default_box_attr=False)
        assert bx7.nothing is False

        bx8 = Box(default_box=True, default_box_attr=0)
        assert bx8.nothing == 0

        # Tests __get_default's `copy` clause
        s = {1, 2, 3}
        bx9 = Box(default_box=True, default_box_attr=s)
        assert isinstance(bx9.test, set)
        assert bx9.test == s
        assert id(bx9.test) != id(s)

        bx10 = Box({"from": "here"}, default_box=True)
        assert bx10.xfrom == "here"
        bx10.xfrom = 5
        assert bx10.xfrom == 5
        assert bx10 == {"from": 5}

    # Issue#59 https://github.com/cdgriffith/Box/issues/59 "Treat None values as non existing keys for default_box"
    def test_default_box_none_transforms(self):
        bx4 = Box({"noneValue": None, "inner": {"noneInner": None}}, default_box=True, default_box_attr="issue#59")
        assert bx4.noneValue == "issue#59"
        assert bx4.inner.noneInner == "issue#59"

        bx5 = Box(
            {"noneValue": None, "inner": {"noneInner": None}},
            default_box=True,
            default_box_none_transform=False,
            default_box_attr="attr",
        )
        assert bx5.noneValue is None
        assert bx5.absentKey == "attr"
        assert bx5.inner.noneInner is None

    def test_camel_killer_box(self):
        td = extended_test_dict.copy()
        td["CamelCase"] = "Item"
        td["321CamelCaseFever!"] = "Safe"

        kill_box = Box(td, camel_killer_box=True, conversion_box=False)
        assert kill_box.camel_case == "Item"
        assert kill_box["321CamelCaseFever!"] == "Safe"

        con_kill_box = Box(td, conversion_box=True, camel_killer_box=True)
        assert con_kill_box.camel_case == "Item"
        assert con_kill_box.x321_camel_case_fever == "Safe"

    def test_default_and_camel_killer_box(self):
        td = extended_test_dict.copy()
        td["CamelCase"] = "Item"
        killer_default_box = Box(td, camel_killer_box=True, default_box=True)
        assert killer_default_box.camel_case == "Item"
        assert killer_default_box.CamelCase == "Item"
        assert isinstance(killer_default_box.does_not_exist, Box)
        assert isinstance(killer_default_box["does_not_exist"], Box)

    def test_box_modify_tuples(self):
        bx = Box(extended_test_dict, modify_tuples_box=True)
        assert bx.tuples_galore[0].item == 3
        assert isinstance(bx.tuples_galore[0], Box)
        assert isinstance(bx.tuples_galore[1], tuple)

    def test_box_set_attribs(self):
        bx = Box(extended_test_dict, conversion_box=False, camel_killer_box=True)
        bx.camel_case = {"new": "item"}
        assert bx["CamelCase"] == Box(new="item")

        bx["CamelCase"] = 4
        assert bx.camel_case == 4

        bx2 = Box(extended_test_dict)
        bx2.Key_2 = 4

        assert bx2["Key 2"] == 4

    def test_functional_data(self):
        data = Box.from_json(filename=data_json_file, conversion_box=True, camel_killer_box=True, default_box=False)
        assert data.widget

        with pytest.raises(AttributeError):
            data._bad_value

        with pytest.raises(AttributeError):
            data.widget._bad_value

        base_config = data._Box__box_config()
        widget_config = data.widget._Box__box_config()

        assert base_config == widget_config, "{} != {}".format(base_config, widget_config)

    def test_functional_spaceballs(self):
        my_box = Box(movie_data)

        my_box.movies.Spaceballs.Stars.append({"name": "Bill Pullman", "imdb": "nm0000597", "role": "Lone Starr"})
        assert my_box.movies.Spaceballs.Stars[-1].role == "Lone Starr"
        assert my_box.movies.Robin_Hood_Men_in_Tights.length == 104
        my_box.movies.Robin_Hood_Men_in_Tights.Stars.pop(0)
        assert my_box.movies.Robin_Hood_Men_in_Tights.Stars[0].name == "Richard Lewis"

    def test_circular_references(self):
        circular_dict = {}
        circular_dict["a"] = circular_dict
        bx = Box(circular_dict)
        assert bx.a == {}
        circular_dict_2 = bx.to_dict()
        assert str(circular_dict_2) == "{'a': {}}"

        bx2 = Box(circular_dict, k=circular_dict)
        assert bx2.k.a == bx2.a

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
        with open(tmp_json_file, "w") as f:
            f.write(content)

        a = BoxList.from_json(filename=tmp_json_file, multiline=True)
        assert a[1].b == 3

    def test_duplicate_errors(self):
        with pytest.raises(BoxError):
            Box({"?a": 1, "!a": 3}, box_duplicates="error")

        Box({"?a": 1, "!a": 3}, box_duplicates="ignore")

        with pytest.warns(UserWarning) as warning:
            Box({"?a": 1, "!a": 3}, box_duplicates="warn")
        assert warning[0].message.args[0].startswith("Duplicate")

        my_box = Box({"?a": 1}, box_duplicates="error")
        with pytest.raises(BoxError):
            my_box["^a"] = 3

    def test_copy(self):
        my_box = Box(movie_data, camel_killer_box=True)
        bb = my_box.copy()
        assert my_box == bb
        assert isinstance(bb, Box)
        assert bb._box_config["camel_killer_box"]

        aa = copy.deepcopy(my_box)
        assert my_box == aa
        assert isinstance(aa, Box)

        cc = my_box.__copy__()
        assert my_box == cc
        assert isinstance(cc, Box)
        assert cc._box_config["camel_killer_box"]

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
            my_box["g"]

        with pytest.raises(BoxKeyError):
            my_box["g"]

        with pytest.raises(BoxError):
            my_box["g"]

    def test_pickle(self):
        if platform.python_implementation() == "PyPy":
            pytest.skip("Pickling does not work correctly on PyPy")
        pic_file = os.path.join(tmp_dir, "test.p")
        pic2_file = os.path.join(tmp_dir, "test.p2")
        bb = Box(movie_data, conversion_box=False)
        pickle.dump(bb, open(pic_file, "wb"))
        loaded = pickle.load(open(pic_file, "rb"))
        assert bb == loaded
        assert loaded._box_config["conversion_box"] is False

        ll = [[Box({"a": "b"})], [[{"c": "g"}]]]
        bx = BoxList(ll)
        pickle.dump(bx, open(pic2_file, "wb"))
        loaded2 = pickle.load(open(pic2_file, "rb"))
        assert bx == loaded2
        loaded2.box_options = bx.box_options

    def test_pickle_default_box(self):
        if platform.python_implementation() == "PyPy":
            pytest.skip("Pickling does not work correctly on PyPy")
        bb = Box(default_box=True)
        loaded = pickle.loads(pickle.dumps(bb))
        assert bb == loaded

    def test_conversion_dup_only(self):
        with pytest.raises(BoxError):
            Box(movie_data, conversion_box=False, box_duplicates="error")

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
        e = Box(movie_data, box_dots=True)
        assert sorted(e.items(dotted=True), key=lambda x: x[0]) == sorted(
            [
                ("movies.Robin Hood: Men in Tights.Director", "Mel Brooks"),
                ("movies.Robin Hood: Men in Tights.Stars[0].imdb", "nm0000144"),
                ("movies.Robin Hood: Men in Tights.Stars[0].name", "Cary Elwes"),
                ("movies.Robin Hood: Men in Tights.Stars[0].role", "Robin Hood"),
                ("movies.Robin Hood: Men in Tights.Stars[1].imdb", "nm0507659"),
                ("movies.Robin Hood: Men in Tights.Stars[1].name", "Richard Lewis"),
                ("movies.Robin Hood: Men in Tights.Stars[1].role", "Prince John"),
                ("movies.Robin Hood: Men in Tights.Stars[2].imdb", "nm0715953"),
                ("movies.Robin Hood: Men in Tights.Stars[2].name", "Roger Rees"),
                ("movies.Robin Hood: Men in Tights.Stars[2].role", "Sheriff of Rottingham"),
                ("movies.Robin Hood: Men in Tights.Stars[3].imdb", "nm0001865"),
                ("movies.Robin Hood: Men in Tights.Stars[3].name", "Amy Yasbeck"),
                ("movies.Robin Hood: Men in Tights.Stars[3].role", "Marian"),
                ("movies.Robin Hood: Men in Tights.imdb_stars", 6.7),
                ("movies.Robin Hood: Men in Tights.length", 104),
                ("movies.Robin Hood: Men in Tights.rating", "PG-13"),
                ("movies.Spaceballs.Director", "Mel Brooks"),
                ("movies.Spaceballs.Stars[0].imdb", "nm0000316"),
                ("movies.Spaceballs.Stars[0].name", "Mel Brooks"),
                ("movies.Spaceballs.Stars[0].role", "President Skroob"),
                ("movies.Spaceballs.Stars[1].imdb", "nm0001006"),
                ("movies.Spaceballs.Stars[1].name", "John Candy"),
                ("movies.Spaceballs.Stars[1].role", "Barf"),
                ("movies.Spaceballs.Stars[2].imdb", "nm0001548"),
                ("movies.Spaceballs.Stars[2].name", "Rick Moranis"),
                ("movies.Spaceballs.Stars[2].role", "Dark Helmet"),
                ("movies.Spaceballs.imdb_stars", 7.1),
                ("movies.Spaceballs.length", 96),
                ("movies.Spaceballs.rating", "PG"),
            ],
            key=lambda x: x[0],
        )
        with pytest.raises(BoxError):
            Box(box_dots=False).items(dotted=True)

    def test_get(self):
        bx = Box()
        bx["c"] = {}
        assert bx.get("a") is None
        assert isinstance(bx.get("c"), Box)
        assert isinstance(bx.get("b", {}), Box)
        assert "a" in bx.get("a", Box(a=1, conversion_box=False))
        assert isinstance(bx.get("a", [1, 2]), BoxList)

    def test_get_default_box(self):
        bx = Box(default_box=True)
        assert bx.get("test", 4) == 4
        assert isinstance(bx.get("a"), Box)
        assert bx.get("test", None) is None

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

    def test_inheritance(self):
        data = {
            "users": [
                {"users": [{"name": "B"}]},
            ],
        }

        class UsersBoxList(BoxList):
            def find_by_name(self, name):
                return next((i for i in self if i.name == name), None)

        db = Box(data, box_recast={"users": UsersBoxList}, box_intact_types=[UsersBoxList])

        assert isinstance(db.users, UsersBoxList)
        assert isinstance(db.users[0].users, UsersBoxList)

    def test_underscore_removal(self):
        from box import Box

        b = Box(_out="preserved", test_="safe")
        b.update({"out": "updated", "test": "unsafe"})
        assert b.out == "updated"
        assert b._out == "preserved"
        assert b.to_dict() == {"out": "updated", "test": "unsafe", "_out": "preserved", "test_": "safe"}
        assert b.test == "unsafe"
        assert b.test_ == "safe"

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
        assert queue.get()

    def test_update_with_integer(self):
        bx = Box()
        bx[1] = 4
        assert bx[1] == 4
        bx.update({1: 2})
        assert bx[1] == 2

    def test_get_box_config(self):
        bx = Box()
        bx_config = bx.__getattr__("_box_config")
        assert bx_config
        with pytest.raises(BoxKeyError):
            bx["_box_config"]

    def test_pop(self):
        bx = Box(a=4, c={"d": 3}, sub_box=Box(test=1))
        assert bx.pop("a") == 4
        with pytest.raises(BoxKeyError):
            bx.pop("b")
        assert bx.pop("a", None) is None
        assert bx.pop("a", True) is True
        with pytest.raises(BoxError):
            bx.pop(1, 2, 3)
        bx.pop("sub_box").pop("test")
        assert bx == {"c": {"d": 3}}
        assert bx.pop("c", True) is not True

    def test_pop_items(self):
        bx = Box(a=4)
        assert bx.popitem() == ("a", 4)
        with pytest.raises(BoxKeyError):
            assert bx.popitem()

    def test_iter(self):
        bx = Box()
        bx.a = 1
        bx.c = 2
        assert list(bx.__iter__()) == ["a", "c"]

    def test_revered(self):
        bx = Box()
        bx.a = 1
        bx.c = 2
        assert list(reversed(bx)) == ["c", "a"]

    def test_clear(self):
        bx = Box()
        bx.a = 1
        bx.c = 4
        bx["g"] = 7
        bx.d = 2
        assert list(bx.keys()) == ["a", "c", "g", "d"]
        bx.clear()
        assert bx == {}
        assert not bx.keys()

    def test_bad_recursive(self):
        b = Box()
        bl = b.setdefault("l", [])
        bl.append(["foo"])
        assert bl == [["foo"]], bl

    def test_dots(self):
        b = Box(movie_data.copy(), box_dots=True)
        assert b["movies.Spaceballs.rating"] == "PG"
        b["movies.Spaceballs.rating"] = 4
        assert b["movies.Spaceballs.rating"] == 4
        del b["movies.Spaceballs.rating"]
        with pytest.raises(BoxKeyError):
            b["movies.Spaceballs.rating"]
        assert b["movies.Spaceballs.Stars[1].role"] == "Barf"
        b["movies.Spaceballs.Stars[1].role"] = "Testing"
        assert b["movies.Spaceballs.Stars[1].role"] == "Testing"
        assert b.movies.Spaceballs.Stars[1].role == "Testing"
        with pytest.raises(BoxError):
            b["."]
        with pytest.raises(BoxError):
            from box.box import _parse_box_dots

            _parse_box_dots({}, "-")

    def test_unicode(self):
        bx = Box()
        bx["\U0001f631"] = 4

        bx2 = Box(camel_killer_box=True)
        bx2["\U0001f631"] = 4

        assert bx == bx2 == {"😱": 4}

    def test_camel_killer_hashables(self):
        bx = Box(camel_killer_box=True)
        bx[(1, 2)] = 32
        assert bx == {(1, 2): 32}

    def test_intact_types_dict(self):
        from collections import OrderedDict

        bx = Box(a=OrderedDict([("y", 1), ("x", 2)]))
        assert isinstance(bx.a, Box)
        assert not isinstance(bx.a, OrderedDict)
        bx = Box(a=OrderedDict([("y", 1), ("x", 2)]), box_intact_types=[OrderedDict])
        assert isinstance(bx.a, OrderedDict)
        assert not isinstance(bx.a, Box)

    def test_delete_attributes(self):
        b = Box(notThief=1, sortaThief=0, reallyAThief=True, camel_killer_box=True)
        b["$OhNo!"] = 3
        c = Box(notThief=1, sortaThief=0, reallyAThief=True, camel_killer_box=True, conversion_box=False)
        del b.not_thief
        del b._oh_no_
        del b.really_a_thief
        with pytest.raises(KeyError):
            del b.really_a_thief
        with pytest.raises(KeyError):
            del b._oh_no_

        del c.not_thief
        del c.really_a_thief
        with pytest.raises(KeyError):
            del c.really_a_thief

    def test_add_boxes(self):
        b = Box(c=1, d={"sub": 1}, e=1)
        c = dict(d={"val": 2}, e=4)
        assert b + c == Box(c=1, d={"sub": 1, "val": 2}, e=4)
        with pytest.raises(BoxError):
            Box() + BoxList()

    def test_iadd_boxes(self):
        b = Box(c=1, d={"sub": 1}, e=1)
        c = dict(d={"val": 2}, e=4)
        b += c
        assert b == Box(c=1, d={"sub": 1, "val": 2}, e=4)
        with pytest.raises(BoxError):
            a = Box()
            a += BoxList()

    def test_radd_boxes(self):
        a = dict(a=1)
        d = Box(e=2)
        d | a
        b = dict(c=1, d={"sub": 1}, e=1)
        c = Box(d={"val": 2}, e=4)
        assert c.__radd__(b) == Box(c=1, d={"sub": 1, "val": 2}, e=1)
        assert c + b == Box(c=1, d={"sub": 1, "val": 2}, e=1)
        with pytest.raises(BoxError):
            BoxList() + Box()

    def test_or_boxes(self):
        b = Box(c=1, d={"sub": 1}, e=1)
        c = dict(d={"val": 2}, e=4)
        assert b | c == Box(c=1, d={"val": 2}, e=4)
        with pytest.raises(BoxError):
            Box() | BoxList()

    def test_ior_boxes(self):
        b = Box(c=1, d={"sub": 1}, e=1)
        c = dict(d={"val": 2}, e=4)
        b |= c
        assert b == Box(c=1, d={"val": 2}, e=4)
        with pytest.raises(BoxError):
            a = Box()
            a |= BoxList()

    def test_ror_boxes(self):
        b = dict(c=1, d={"sub": 1}, e=1)
        c = Box(d={"val": 2}, e=4)
        assert c.__ror__(b) == Box(c=1, d={"sub": 1}, e=1)
        assert c | b == Box(c=1, d={"sub": 1}, e=1)
        with pytest.raises(BoxError):
            BoxList() | Box()

    def test_type_recast(self):
        b = Box(id="6", box_recast={"id": int})
        assert isinstance(b.id, int)
        with pytest.raises(ValueError):
            b["sub_box"] = {"id": "bad_id"}

    def test_nontype_recast(self):
        class CustomError(ValueError):
            pass

        def cast_id(val) -> int:
            if val == "bad_id":
                raise CustomError()
            return int(val)

        b = Box(id="6", box_recast={"id": cast_id})
        assert isinstance(b.id, int)
        with pytest.raises(ValueError) as exc_info:
            b["sub_box"] = {"id": "bad_id"}
        assert isinstance(exc_info.value.__cause__, CustomError)

    def test_box_dots(self):
        b = Box(
            {"my_key": {"does stuff": {"to get to": "where I want"}}, "key.with.list": [[[{"test": "value"}]]]},
            box_dots=True,
        )
        for key in b.keys(dotted=True):
            b[key]

        c = Box(extended_test_dict.copy(), box_dots=True)
        for key in c.keys(dotted=True):
            c[key]

        assert b["my_key.does stuff.to get to"] == "where I want"
        b["my_key.does stuff.to get to"] = "test"
        assert b["my_key.does stuff.to get to"] == "test"
        del b["my_key.does stuff"]
        assert b["my_key"] == {}
        b[4] = 2
        assert b[4] == 2
        del b[4]
        assert b["key.with.list[0][0][0].test"] == "value"
        b["key.with.list[0][0][0].test"] = "new_value"
        assert b["key.with.list"][0][0][0]["test"] == "new_value"
        del b["key.with.list[0][0][0].test"]
        assert not b["key.with.list[0][0][0]"]
        del b["key.with.list[0][0]"]
        with pytest.raises(IndexError):
            b["key.with.list[0][0][0]"]
        del b["key.with.list[0]"]
        with pytest.raises(IndexError):
            b["key.with.list[0][0]"]

        d = Box()
        with pytest.raises(BoxError):
            d.keys(dotted=True)

    def test_toml(self):
        b = Box.from_toml(filename=Path(test_root, "data", "toml_file.tml"), default_box=True)
        assert b.database.server == "192.168.1.1"
        assert b.clients.hosts == ["alpha", "omega"]
        assert b.database.to_toml().startswith('server = "192.168.1.1"')
        assert b._box_config["default_box"] is True

    def test_parameter_pass_through(self):
        bx = Box.from_yaml(
            "uno: 2",
            box_dots=True,
            default_box=True,
            default_box_attr=None,
            default_box_none_transform=True,
            frozen_box=False,
            camel_killer_box=True,
            conversion_box=True,
            modify_tuples_box=True,
            box_safe_prefix="x",
            box_duplicates="warn",
            box_intact_types=(),
            box_recast=None,
        )
        assert bx.uno == 2

    def test_sub(self):
        difference = Box(extended_test_dict) - test_dict
        assert difference == {
            3: "howdy",
            "not": "true",
            (3, 4): "test",
            "_box_config": True,
            "CamelCase": "21",
            "321CamelCase": 321,
            False: "tree",
            "tuples_galore": ({"item": 3}, ({"item": 4}, 5)),
        }

    def test_sub_with_non_dict(self):
        with pytest.raises(BoxError):
            Box(extended_test_dict) - BoxList([1, 2, 3])

    def test_sub_with_frozen_box(self):
        difference = Box(extended_test_dict, frozen_box=True) - test_dict
        assert difference == {
            3: "howdy",
            "not": "true",
            (3, 4): "test",
            "_box_config": True,
            "CamelCase": "21",
            "321CamelCase": 321,
            False: "tree",
            "tuples_galore": ({"item": 3}, ({"item": 4}, 5)),
        }

    def test_no_key_error_pop(self):
        box1 = Box(default_box=True)
        box1.pop("non_exist_key")
        assert box1 == {}

    def test_key_error_popitem(self):
        box1 = Box(default_box=True)
        with pytest.raises(BoxKeyError):
            box1.popitem()

    def test_msgpack_strings(self):
        box1 = Box(test_dict)
        packed = box1.to_msgpack()
        assert Box.from_msgpack(packed) == box1

    def test_msgpack_strings_no_strick_keys(self):
        box1 = Box(test_dict)
        box1[5] = 2
        packed = box1.to_msgpack()
        assert Box.from_msgpack(packed, strict_map_key=False) == box1

    def test_msgpack_files(self):
        box1 = Box(test_dict)
        box1.to_msgpack(filename=tmp_msgpack_file)
        assert Box.from_msgpack(filename=tmp_msgpack_file) == box1

    def test_msgpack_no_input(self):
        with pytest.raises(BoxError):
            Box.from_msgpack()

    def test_value_view(self):
        a = Box()
        my_view = a.values()
        assert len(my_view) == 0
        a["test"] = "key_one"
        a.test2 = "key_two"
        assert len(my_view) == 2
        assert "key_one" in my_view
        assert "key_two" in my_view

    def test_key_view(self):
        a = Box()
        my_view = a.keys()
        assert len(my_view) == 0
        a["test"] = "key_one"
        a.test2 = "key_two"
        assert len(my_view) == 2
        assert "test" in my_view
        assert "test2" in my_view

    def test_item_view(self):
        a = Box()
        my_view = a.items()
        assert len(my_view) == 0
        a["test"] = "key_one"
        a.test2 = "key_two"
        assert len(my_view) == 2
        assert ("test", "key_one") in my_view
        assert ("test2", "key_two") in my_view

    def test_box_propagation(self):
        # Issue 150
        hash(Box({"x": Box({"y": 2})}, frozen_box=True))
        hash(Box({"x": [Box({"y": 2})]}, frozen_box=True))

    def test_box_safe_references(self):
        a = Box(c=5)
        b = Box(a=a)
        assert id(a) != id(b.a)

    def test_default_box_restricted_calls(self):
        a = Box(default_box=True)
        with pytest.raises(BoxKeyError):
            a._test_thing_
        assert len(list(a.keys())) == 0

        # Based on argparse.parse_args internal behavior, the following
        # creates the attribute in hasattr due to default_box=True, then
        # deletes it in delattr.
        if hasattr(a, "_unrecognized_args"):
            delattr(a, "_unrecognized_args")

        a._allowed_prefix
        a.allowed_postfix_
        assert len(list(a.keys())) == 2

    def test_default_dots(self):
        a = Box(default_box=True, box_dots=True)
        a["a.a.a"]
        assert a == {"a.a.a": {}}
        a["a.a.a."]
        a["a.a.a.."]
        assert a == {"a.a.a": {"": {"": {}}}}
        a["b.b"] = 3
        assert a == {"a.a.a": {"": {"": {}}}, "b.b": 3}
        a.b.b = 4
        assert a == {"a.a.a": {"": {"": {}}}, "b.b": 3, "b": {"b": 4}}
        assert a["non.existent.key"] == {}

    def test_merge_list_options(self):
        a = Box()
        a.merge_update({"lister": ["a"]})
        a.merge_update({"lister": ["a", "b", "c"]}, box_merge_lists="extend")
        assert a.lister == ["a", "a", "b", "c"]
        a.merge_update({"lister": ["a", "b", "c"]}, box_merge_lists="unique")
        assert a.lister == ["a", "a", "b", "c"]
        a.merge_update({"lister": ["a", "d", "b", "c"]}, box_merge_lists="unique")
        assert a.lister == ["a", "a", "b", "c", "d"]
        a.merge_update({"key1": {"new": 5}, "Key 2": {"add_key": 6}, "lister": ["a"]})
        assert a.lister == ["a"]

    def test_box_from_empty_yaml(self):
        out = Box.from_yaml("---")
        assert out == Box()

        out2 = BoxList.from_yaml("---")
        assert out2 == BoxList()

    def test_setdefault_simple(self):
        box = Box({"a": 1})
        box.setdefault("b", 2)
        box.setdefault("c", "test")
        box.setdefault("d", {"e": True})
        box.setdefault("f", [1, 2])

        assert box["b"] == 2
        assert box["c"] == "test"
        assert isinstance(box["d"], Box)
        assert box["d"]["e"] == True
        assert isinstance(box["f"], BoxList)
        assert box["f"][1] == 2

    def test_setdefault_dots(self):
        box = Box({"a": 1}, box_dots=True)
        box.setdefault("b", 2)
        box.c = {"d": 3}
        box.setdefault("c.e", "test")
        box.setdefault("d", {"e": True})
        box.setdefault("f", [1, 2])

        assert box.b == 2
        assert box.c.e == "test"
        assert isinstance(box["d"], Box)
        assert box.d.e == True
        assert isinstance(box["f"], BoxList)
        assert box.f[1] == 2

    def test_setdefault_dots_default(self):
        box = Box({"a": 1}, box_dots=True, default_box=True)
        box.b.c.d.setdefault("e", 2)
        box.c.setdefault("e", "test")
        box.d.e.setdefault("f", {"g": True})
        box.e.setdefault("f", [1, 2])

        assert box["b.c.d"].e == 2
        assert box.c.e == "test"
        assert isinstance(box["d.e.f"], Box)
        assert box.d.e["f.g"] == True
        assert isinstance(box["e.f"], BoxList)
        assert box.e.f[1] == 2
