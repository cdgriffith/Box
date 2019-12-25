#!/usr/bin/env python
try:
    from test.common import *
except ImportError:
    from .common import *


class TestSBox:

    def test_property_box(self):
        td = test_dict.copy()
        td['inner'] = {'CamelCase': 'Item'}

        pbox = SBox(td, camel_killer_box=True)
        assert isinstance(pbox.inner, SBox)
        assert pbox.inner.camel_case == 'Item'
        assert json.loads(pbox.json)['inner']['CamelCase'] == 'Item'
        test_item = yaml.load(pbox.yaml, Loader=yaml.SafeLoader)
        assert test_item['inner']['CamelCase'] == 'Item'
        assert repr(pbox['inner']).startswith('<ShorthandBox')
        assert not isinstance(pbox.dict, Box)
        assert pbox.dict['inner']['CamelCase'] == 'Item'
        assert pbox.toml.startswith('key1 = "value1"')
