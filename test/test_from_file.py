#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
from test.common import test_root

import pytest

from box import Box, BoxError, BoxList, box_from_file


class TestFromFile:
    def test_from_all(self):
        assert isinstance(box_from_file(Path(test_root, "data", "json_file.json")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "toml_file.tml")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "yaml_file.yaml")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "json_file.json"), file_type="json"), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "toml_file.tml"), file_type="toml"), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "yaml_file.yaml"), file_type="yaml"), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "json_list.json")), BoxList)
        assert isinstance(box_from_file(Path(test_root, "data", "yaml_list.yaml")), BoxList)
        assert isinstance(box_from_file(Path(test_root, "data", "msgpack_file.msgpack")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "msgpack_list.msgpack")), BoxList)
        assert isinstance(box_from_file(Path(test_root, "data", "csv_file.csv")), BoxList)

    def test_bad_file(self):
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type="json")
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type="toml")
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type="yaml")
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type="msgpack")
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type="unknown")
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"))
        with pytest.raises(BoxError):
            box_from_file("does not exist")
