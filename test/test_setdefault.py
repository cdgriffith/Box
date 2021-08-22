#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Test files gathered from json.org and yaml.org

import json
import os
import pytest

from box import Box,BoxList

class TestSetdefault:
    def test_setdefault_simple(self):
        box = Box({ 'a' : 1 })
        box.setdefault('b',2)
        box.setdefault('c','test')
        box.setdefault('d',{ 'e' : True })
        box.setdefault('f',[ 1, 2 ])

        assert box['b'] == 2
        assert box['c'] == 'test'
        assert isinstance(box['d'],Box)
        assert box['d']['e'] == True
        assert isinstance(box['f'],BoxList)
        assert box['f'][1] == 2

    def test_setdefault_dots(self):
        box = Box({ 'a' : 1 },box_dots = True)
        box.setdefault('b',2)
        box.c = { 'd' : 3 }
        box.setdefault('c.e','test')
        box.setdefault('d',{ 'e' : True })
        box.setdefault('f',[ 1, 2 ])

        assert box.b == 2
        assert box.c.e == 'test'
        assert isinstance(box['d'],Box)
        assert box.d.e == True
        assert isinstance(box['f'],BoxList)
        assert box.f[1] == 2

    def test_setdefault_dots(self):
        box = Box({ 'a' : 1 },box_dots = True,default_box = True)
        box.b.c.d.setdefault('e',2)
        box.c.setdefault('e','test')
        box.d.e.setdefault('f',{ 'g' : True })
        box.e.setdefault('f',[ 1, 2 ])

        assert box['b.c.d'].e == 2
        assert box.c.e == 'test'
        assert isinstance(box['d.e.f'],Box)
        assert box.d.e['f.g'] == True
        assert isinstance(box['e.f'],BoxList)
        assert box.e.f[1] == 2
