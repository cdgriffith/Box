#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Test files gathered from json.org and yaml.org

import pytest


try:
    from test.common import *
except ImportError:
    from .common import *


class TestBoxList:

    def test_box_list(self):
        new_list = BoxList({'item': x} for x in range(0, 10))
        new_list.extend([{'item': 22}])
        assert new_list[-1].item == 22
        new_list.append([{'bad_item': 33}])
        assert new_list[-1][0].bad_item == 33
        assert repr(new_list).startswith("<BoxList:")
        for x in new_list.to_list():
            assert not isinstance(x, (BoxList, Box))
        new_list.insert(0, {'test': 5})
        new_list.insert(1, ['a', 'b'])
        new_list.append('x')
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
            bl.append('test')
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
        bl = BoxList([{'item': 1, 'CamelBad': 2}])
        assert json.loads(bl.to_json())[0]['item'] == 1

    def test_box_list_from_json(self):
        alist = [{'item': 1}, {'CamelBad': 2}]
        json_list = json.dumps(alist)
        bl = BoxList.from_json(json_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_json(json.dumps({'a': 2}))

    def test_box_list_to_yaml(self):
        bl = BoxList([{'item': 1, 'CamelBad': 2}])
        assert yaml.load(bl.to_yaml(), Loader=yaml.SafeLoader)[0]['item'] == 1

    def test_box_list_from_yaml(self):
        alist = [{'item': 1}, {'CamelBad': 2}]
        yaml_list = yaml.dump(alist)
        bl = BoxList.from_yaml(yaml_list, camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_yaml(yaml.dump({'a': 2}))

    def test_box_list_to_toml(self):
        bl = BoxList([{'item': 1, 'CamelBad': 2}])
        assert toml.loads(bl.to_toml(key_name='test'))['test'][0]['item'] == 1

    def test_box_list_from_tml(self):
        alist = [{'item': 1}, {'CamelBad': 2}]
        toml_list = toml.dumps({'key': alist})
        bl = BoxList.from_toml(toml_string=toml_list, key_name='key', camel_killer_box=True)
        assert bl[0].item == 1
        assert bl[1].camel_bad == 2

        with pytest.raises(BoxError):
            BoxList.from_toml(toml.dumps({'a': 2}), 'a')

    def test_box_list_box_it_up(self):
        bxl = BoxList([extended_test_dict])
        bxl.box_it_up()
        assert "Key 3" in bxl[0].Key_2._box_config['__converted']

    def test_intact_types_list(self):
        class MyList(list):
            pass

        bl = BoxList([[1, 2], MyList([3, 4])], box_intact_types=(MyList,))
        assert isinstance(bl[0], BoxList)
