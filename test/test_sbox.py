#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from test.common import test_dict

import ruamel.yaml as yaml

from box import Box, SBox


class TestSBox:
    def test_property_box(self):
        td = test_dict.copy()
        td["inner"] = {"CamelCase": "Item"}

        pbox = SBox(td, camel_killer_box=True)
        assert isinstance(pbox.inner, SBox)
        assert pbox.inner.camel_case == "Item"
        assert json.loads(pbox.json)["inner"]["camel_case"] == "Item"
        test_item = yaml.load(pbox.yaml, Loader=yaml.SafeLoader)
        assert test_item["inner"]["camel_case"] == "Item"
        assert repr(pbox["inner"]).startswith("<ShorthandBox")
        assert not isinstance(pbox.dict, Box)
        assert pbox.dict["inner"]["camel_case"] == "Item"
        assert pbox.toml.startswith('key1 = "value1"')
