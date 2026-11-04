#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""to_yaml writes keys in insertion order with every YAML backend (#104)."""

import pytest

import box.converters as converters
from box import Box, BoxList

DATA = {"zlast": 1, "afirst": {"z": 1, "a": 2}}
IN_ORDER = "zlast: 1\nafirst:\n  z: 1\n  a: 2\n"
SORTED = "afirst:\n  a: 2\n  z: 1\nzlast: 1\n"


@pytest.fixture(params=["ruamel-rt", "ruamel-safe", "pyyaml"])
def backend(request, monkeypatch):
    if request.param == "pyyaml":
        if not converters.pyyaml_available:
            pytest.skip("PyYAML is not installed")
        monkeypatch.setattr(converters, "ruamel_available", False)
        return {}
    if not converters.ruamel_available:
        pytest.skip("ruamel.yaml is not installed")
    return {"ruamel_typ": request.param.split("-")[1]}


class TestYamlOrder:
    def test_insertion_order_by_default(self, backend):
        assert Box(DATA).to_yaml(**backend) == IN_ORDER

    def test_sort_keys_opt_in(self, backend):
        if backend.get("ruamel_typ", "safe") == "rt":
            pytest.skip("the ruamel round trip dumper never sorts")
        assert Box(DATA).to_yaml(sort_keys=True, **backend) == SORTED

    def test_file_output_and_box_list(self, backend, tmp_path):
        path = tmp_path / "order.yaml"
        Box(DATA).to_yaml(filename=path, **backend)
        assert path.read_text() == IN_ORDER
        assert BoxList([DATA]).to_yaml(**backend) == "- zlast: 1\n  afirst:\n    z: 1\n    a: 2\n"

    def test_round_trip_keeps_order(self, backend):
        assert list(Box.from_yaml(Box(DATA).to_yaml(**backend)).keys()) == ["zlast", "afirst"]
