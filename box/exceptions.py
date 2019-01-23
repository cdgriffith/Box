#!/usr/bin/env python
# -*- coding: UTF-8 -*-


class BoxError(Exception):
    """Non standard dictionary exceptions"""


class BoxKeyError(BoxError, KeyError, AttributeError):
    """Key does not exist"""
