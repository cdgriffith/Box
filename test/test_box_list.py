#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test files gathered from json.org and yaml.org

import json
import os
import shutil
from pathlib import Path
from test.common import test_root, tmp_dir

import pytest
import ruamel.yaml as yaml
import toml

from box import Box, BoxError, BoxList


class TestBoxList:
    @pytest.fixture(autouse=True)
    def temp_dir_cleanup(self):
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        try:
            os.mkdir(str(tmp_dir))
        except OSError:
            pass
        yield
        shutil.rmtree(str(tmp_dir), ignore_errors=True)

    def test_box_list(self):
        new_list = BoxList({"item": x} for x in range(0, 10))
        new_list.extend([{"item": 22}])
        assert new_list[-1].item == 22
        new_list.append([{"bad_item": 33}])
        assert new_list[-1][0].bad_item == 33
        assert repr(new_list).startswith("<BoxList:")
        for x in new_list.to_list():
            assert not isinstance(x, (BoxList, Box))
        new_list.insert(0, {"test": 5})
        new_list.insert(1, ["a", "b"])
        new_list.append("x")
        assert new_list[0].test == 5
        assert isinstance(str(new_list), str)
        assert isinstance(new_list[1], BoxList)
        assert not isinstance(new_list.to_list(), BoxList)

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
            bl.append("test")
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

    def test_box_list_to_json(self):
        bl = BoxList([{"item": 1, "CamelBad": 2}])
        assert json.loads(bl.to_json())[0]["item"] == 1

    def test_box_list_from_json(self):
        alist = [{"item": 1}, {"CamelBad": 2}]
        json_list = json.dumps(alist)
        bl = BoxList.from_json(json_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_json(json.dumps({"a": 2}))

    def test_box_list_to_yaml(self):
        bl = BoxList([{"item": 1, "CamelBad": 2}])
        assert yaml.load(bl.to_yaml(), Loader=yaml.SafeLoader)[0]["item"] == 1

    def test_box_list_from_yaml(self):
        alist = [{"item": 1}, {"CamelBad": 2}]
        yaml_list = yaml.dump(alist)
        bl = BoxList.from_yaml(yaml_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_yaml(yaml.dump({"a": 2}))

    def test_box_list_to_toml(self):
        bl = BoxList([{"item": 1, "CamelBad": 2}])
        assert toml.loads(bl.to_toml(key_name="test"))["test"][0]["item"] == 1
        with pytest.raises(BoxError):
            BoxList.from_toml("[[test]]\nitem = 1\nCamelBad = 2\n\n", key_name="does not exist")

    def test_box_list_from_tml(self):
        alist = [{"item": 1}, {"CamelBad": 2}]
        toml_list = toml.dumps({"key": alist})
        bl = BoxList.from_toml(toml_string=toml_list, key_name="key", camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_toml(toml.dumps({"a": 2}), "a")

        with pytest.raises(BoxError):
            BoxList.from_toml(toml_list, "bad_key")

    def test_intact_types_list(self):
        class MyList(list):
            pass

        bl = BoxList([[1, 2], MyList([3, 4])], box_intact_types=(MyList,))
        assert isinstance(bl[0], BoxList)

    def test_to_csv(self):
        data = BoxList(
            [
                {"Number": 1, "Name": "Chris", "Country": "US"},
                {"Number": 2, "Name": "Sam", "Country": "US"},
                {"Number": 3, "Name": "Jess", "Country": "US"},
                {"Number": 4, "Name": "Frank", "Country": "UK"},
                {"Number": 5, "Name": "Demo", "Country": "CA"},
            ]
        )

        file = Path(tmp_dir, "csv_file.csv")
        data.to_csv(filename=file)
        assert file.read_text().startswith("Number,Name,Country\n1,Chris,US")
        assert data.to_csv().endswith("2,Sam,US\r\n3,Jess,US\r\n4,Frank,UK\r\n5,Demo,CA\r\n")

    def test_from_csv(self):
        bl = BoxList.from_csv(filename=Path(test_root, "data", "csv_file.csv"))
        assert bl[1].Name == "Sam"
        b2 = BoxList.from_csv(
            "Number,Name,Country\r\n1,Chris,US\r\n2,Sam" ",US\r\n3,Jess,US\r\n4,Frank,UK\r\n5,Demo,CA\r\n"
        )
        assert b2[2].Name == "Jess"

    def test_bad_csv(self):
        data = BoxList([{"test": 1}, {"bad": 2, "data": 3}])
        file = Path(tmp_dir, "csv_file.csv")
        with pytest.raises(BoxError):
            data.to_csv(file)

    def test_box_list_dots(self):
        data = BoxList(
            [
                {"test": 1},
                {"bad": 2, "data": 3},
                [[[0, -1], [77, 88]], {"inner": "one", "lister": [[{"down": "rabbit"}]]}],
                4,
            ],
            box_dots=True,
        )

        assert data["[0].test"] == 1
        assert data["[1].data"] == 3
        assert data[1].data == 3
        data["[1].data"] = "new_data"
        assert data["[1].data"] == "new_data"
        assert data["[2][0][0][1]"] == -1
        assert data[2][0][0][1] == -1
        data["[2][0][0][1]"] = 1_000_000
        assert data["[2][0][0][1]"] == 1_000_000
        assert data[2][0][0][1] == 1_000_000
        assert data["[2][1].lister[0][0].down"] == "rabbit"
        data["[2][1].lister[0][0].down"] = "hole"
        assert data["[2][1].lister[0][0].down"] == "hole"
        assert data[2][1].lister[0][0].down == "hole"

        db = Box(a=data, box_dots=True)
        keys = db.keys(dotted=True)
        assert keys == [
            "a[0].test",
            "a[1].bad",
            "a[1].data",
            "a[2][0][0][0]",
            "a[2][0][0][1]",
            "a[2][0][1][0]",
            "a[2][0][1][1]",
            "a[2][1].inner",
            "a[2][1].lister[0][0].down",
            "a[3]",
        ]
        for key in keys:
            db[key]

    def test_box_config_propagate(self):
        structure = Box(a=[Box(default_box=False)], default_box=True, box_inherent_settings=True)
        assert structure._box_config["default_box"] is True
        assert structure.a[0]._box_config["default_box"] is True

        base = BoxList([BoxList([Box(default_box=False)])], default_box=True)
        assert base[0].box_options["default_box"] is True

        base2 = BoxList((BoxList([Box()], default_box=False),), default_box=True)
        assert base2[0][0]._box_config["default_box"] is True

        base3 = Box(
            a=[Box(default_box=False)], default_box=True, box_inherent_settings=True, box_intact_types=[Box, BoxList]
        )
        base3.a.append(Box(default_box=False))
        base3.a.append(BoxList(default_box=False))

        for item in base3.a:
            if isinstance(item, Box):
                assert item._box_config["default_box"] is True
            elif isinstance(item, BoxList):
                assert item.box_options["default_box"] is True
