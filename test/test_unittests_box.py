#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import absolute_import

try:
    from common import *
except ImportError:
    from .common import *


class TestBoxFunctional(unittest.TestCase):

    def test_safe_attrs(self):
        assert box._safe_attr("BAD!KEY!1", camel_killer=False) == "BAD_KEY_1"
        assert box._safe_attr("BAD!KEY!2", camel_killer=True) == "bad_key_2"
        assert box._safe_attr((5,6, 7), camel_killer=False) == "x5_6_7"
        assert box._safe_attr(356, camel_killer=False) == "x356"
