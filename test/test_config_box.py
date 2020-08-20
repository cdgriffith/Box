#!/usr/bin/env python
# -*- coding: utf-8 -*-

from test.common import test_dict

from box import Box, ConfigBox


class TestConfigBox:
    def test_config_box(self):
        g = {
            "b0": "no",
            "b1": "yes",
            "b2": "True",
            "b3": "false",
            "b4": True,
            "i0": "34",
            "f0": "5.5",
            "f1": "3.333",
            "l0": "4,5,6,7,8",
            "l1": "[2 3 4 5 6]",
        }

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

    def test_dir(self):
        b = ConfigBox(test_dict)

        for item in ("to_yaml", "to_dict", "to_json", "int", "list", "float"):
            assert item in dir(b)

    def test_config_default(self):
        bx4 = Box(default_box=True, default_box_attr=ConfigBox)
        assert isinstance(bx4.bbbbb, ConfigBox)
