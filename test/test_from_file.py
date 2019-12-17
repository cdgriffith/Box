#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from pathlib import Path

import pytest
from box import box_from_file

from test.common import *


class TestFromFile:

    def test_from_all(self):
        assert isinstance(box_from_file(Path(test_root, "data", "json_file.json")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "toml_file.tml")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "yaml_file.yaml")), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "json_file.json"), file_type='json'), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "toml_file.tml"), file_type='toml'), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "yaml_file.yaml"), file_type='yaml'), Box)
        assert isinstance(box_from_file(Path(test_root, "data", "json_list.json")), BoxList)
        assert isinstance(box_from_file(Path(test_root, "data", "yaml_list.yaml")), BoxList)

    def test_bad_file(self):
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type='json')
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type='toml')
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type='yaml')
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"), file_type='unknown')
        with pytest.raises(BoxError):
            box_from_file(Path(test_root, "data", "bad_file.txt"))
        with pytest.raises(BoxError):
            box_from_file('does not exist')
