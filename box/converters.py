#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Abstract converter functions for use in any Box class

import sys
import json
from pathlib import Path

import ruamel.yaml as yaml
import toml

from box.exceptions import BoxError

BOX_PARAMETERS = ('default_box', 'default_box_attr', 'conversion_box',
                  'frozen_box', 'camel_killer_box', 'box_it_up',
                  'box_safe_prefix', 'box_duplicates', 'ordered_box',
                  'default_box_none_transform')


def _exists(filename, create=False):
    path = Path(filename)
    if create:
        try:
            path.touch(exist_ok=True)
        except OSError as err:
            raise BoxError(f'Could not create file {filename} - {err}')
        else:
            return
    if not path.exists():
        raise BoxError(f'File "{filename}" does not exist')
    if not path.is_file():
        raise BoxError(f'{filename} is not a file')


def _to_json(obj, filename=None, encoding="utf-8", errors="strict", **json_kwargs):
    json_dump = json.dumps(obj, ensure_ascii=False, **json_kwargs)
    if filename:
        _exists(filename, create=True)
        with open(filename, 'w', encoding=encoding, errors=errors) as f:
            f.write(json_dump if sys.version_info >= (3, 0) else json_dump.decode("utf-8"))
    else:
        return json_dump


def _from_json(json_string=None, filename=None, encoding="utf-8", errors="strict", multiline=False, **kwargs):
    if filename:
        _exists(filename)
        with open(filename, 'r', encoding=encoding, errors=errors) as f:
            if multiline:
                data = [json.loads(line.strip(), **kwargs) for line in f
                        if line.strip() and not line.strip().startswith("#")]
            else:
                data = json.load(f, **kwargs)
    elif json_string:
        data = json.loads(json_string, **kwargs)
    else:
        raise BoxError('from_json requires a string or filename')
    return data


def _to_yaml(obj, filename=None, default_flow_style=False, encoding="utf-8", errors="strict", **yaml_kwargs):
    if filename:
        _exists(filename, create=True)
        with open(filename, 'w',
                  encoding=encoding, errors=errors) as f:
            yaml.dump(obj, stream=f, default_flow_style=default_flow_style, **yaml_kwargs)
    else:
        return yaml.dump(obj, default_flow_style=default_flow_style, **yaml_kwargs)


def _from_yaml(yaml_string=None, filename=None, encoding="utf-8", errors="strict", **kwargs):
    if 'Loader' not in kwargs:
        kwargs['Loader'] = yaml.SafeLoader
    if filename:
        _exists(filename)
        with open(filename, 'r', encoding=encoding, errors=errors) as f:
            data = yaml.load(f, **kwargs)
    elif yaml_string:
        data = yaml.load(yaml_string, **kwargs)
    else:
        raise BoxError('from_yaml requires a string or filename')
    return data


def _to_toml(obj, filename=None, encoding="utf-8", errors="strict"):
    if filename:
        _exists(filename, create=True)
        with open(filename, 'w', encoding=encoding, errors=errors) as f:
            toml.dump(obj, f)
    else:
        return toml.dumps(obj)


def _from_toml(toml_string=None, filename=None, encoding="utf-8", errors="strict"):
    if filename:
        _exists(filename)
        with open(filename, 'r', encoding=encoding, errors=errors) as f:
            data = toml.load(f)
    elif toml_string:
        data = toml.loads(toml_string)
    else:
        raise BoxError('from_toml requires a string or filename')
    return data
