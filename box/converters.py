#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Abstract converter functions for use in any Box class

import csv
import json
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Union

from box.exceptions import BoxError

yaml_available = True
toml_available = True
msgpack_available = True

try:
    import ruamel.yaml as yaml
except ImportError:
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None  # type: ignore
        yaml_available = False

try:
    import toml
except ImportError:
    toml = None  # type: ignore
    toml_available = False
try:
    import msgpack  # type: ignore
except ImportError:
    msgpack = None  # type: ignore
    msgpack_available = False

BOX_PARAMETERS = (
    "default_box",
    "default_box_attr",
    "conversion_box",
    "frozen_box",
    "camel_killer_box",
    "box_safe_prefix",
    "box_duplicates",
    "ordered_box",
    "default_box_none_transform",
    "box_dots",
    "modify_tuples_box",
    "box_intact_types",
    "box_recast",
)


def _exists(filename: Union[str, PathLike], create: bool = False) -> Path:
    path = Path(filename)
    if create:
        try:
            path.touch(exist_ok=True)
        except OSError as err:
            raise BoxError(f"Could not create file {filename} - {err}")
        else:
            return path
    if not path.exists():
        raise BoxError(f'File "{filename}" does not exist')
    if not path.is_file():
        raise BoxError(f"{filename} is not a file")
    return path


def _to_json(
    obj, filename: Union[str, PathLike] = None, encoding: str = "utf-8", errors: str = "strict", **json_kwargs
):
    if filename:
        _exists(filename, create=True)
        with open(filename, "w", encoding=encoding, errors=errors) as f:
            json.dump(obj, f, ensure_ascii=False, **json_kwargs)
    else:
        return json.dumps(obj, ensure_ascii=False, **json_kwargs)


def _from_json(
    json_string: str = None,
    filename: Union[str, PathLike] = None,
    encoding: str = "utf-8",
    errors: str = "strict",
    multiline: bool = False,
    **kwargs,
):
    if filename:
        with open(filename, "r", encoding=encoding, errors=errors) as f:
            if multiline:
                data = [
                    json.loads(line.strip(), **kwargs)
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
            else:
                data = json.load(f, **kwargs)
    elif json_string:
        data = json.loads(json_string, **kwargs)
    else:
        raise BoxError("from_json requires a string or filename")
    return data


def _to_yaml(
    obj,
    filename: Union[str, PathLike] = None,
    default_flow_style: bool = False,
    encoding: str = "utf-8",
    errors: str = "strict",
    **yaml_kwargs,
):
    if filename:
        _exists(filename, create=True)
        with open(filename, "w", encoding=encoding, errors=errors) as f:
            yaml.dump(obj, stream=f, default_flow_style=default_flow_style, **yaml_kwargs)
    else:
        return yaml.dump(obj, default_flow_style=default_flow_style, **yaml_kwargs)


def _from_yaml(
    yaml_string: str = None,
    filename: Union[str, PathLike] = None,
    encoding: str = "utf-8",
    errors: str = "strict",
    **kwargs,
):
    if "Loader" not in kwargs:
        kwargs["Loader"] = yaml.SafeLoader
    if filename:
        _exists(filename)
        with open(filename, "r", encoding=encoding, errors=errors) as f:
            data = yaml.load(f, **kwargs)
    elif yaml_string:
        data = yaml.load(yaml_string, **kwargs)
    else:
        raise BoxError("from_yaml requires a string or filename")
    return data


def _to_toml(obj, filename: Union[str, PathLike] = None, encoding: str = "utf-8", errors: str = "strict"):
    if filename:
        _exists(filename, create=True)
        with open(filename, "w", encoding=encoding, errors=errors) as f:
            toml.dump(obj, f)
    else:
        return toml.dumps(obj)


def _from_toml(
    toml_string: str = None, filename: Union[str, PathLike] = None, encoding: str = "utf-8", errors: str = "strict"
):
    if filename:
        _exists(filename)
        with open(filename, "r", encoding=encoding, errors=errors) as f:
            data = toml.load(f)
    elif toml_string:
        data = toml.loads(toml_string)
    else:
        raise BoxError("from_toml requires a string or filename")
    return data


def _to_msgpack(obj, filename: Union[str, PathLike] = None, **kwargs):
    if filename:
        _exists(filename, create=True)
        with open(filename, "wb") as f:
            msgpack.pack(obj, f, **kwargs)
    else:
        return msgpack.packb(obj, **kwargs)


def _from_msgpack(msgpack_bytes: bytes = None, filename: Union[str, PathLike] = None, **kwargs):
    if filename:
        _exists(filename)
        with open(filename, "rb") as f:
            data = msgpack.unpack(f, **kwargs)
    elif msgpack_bytes:
        data = msgpack.unpackb(msgpack_bytes, **kwargs)
    else:
        raise BoxError("from_msgpack requires a string or filename")
    return data


def _to_csv(box_list, filename: Union[str, PathLike] = None, encoding: str = "utf-8", errors: str = "strict", **kwargs):
    csv_column_names = list(box_list[0].keys())
    for row in box_list:
        if list(row.keys()) != csv_column_names:
            raise BoxError("BoxList must contain the same dictionary structure for every item to convert to csv")

    if filename:
        _exists(filename, create=True)
        out_data = open(filename, "w", encoding=encoding, errors=errors, newline="")
    else:
        out_data = StringIO("")
    writer = csv.DictWriter(out_data, fieldnames=csv_column_names, **kwargs)
    writer.writeheader()
    for data in box_list:
        writer.writerow(data)
    if not filename:
        return out_data.getvalue()  # type: ignore
    out_data.close()


def _from_csv(
    csv_string: str = None,
    filename: Union[str, PathLike] = None,
    encoding: str = "utf-8",
    errors: str = "strict",
    **kwargs,
):
    if csv_string:
        with StringIO(csv_string) as cs:
            reader = csv.DictReader(cs)
            return [row for row in reader]
    _exists(filename)  # type: ignore
    with open(filename, "r", encoding=encoding, errors=errors, newline="") as f:  # type: ignore
        reader = csv.DictReader(f, **kwargs)
        return [row for row in reader]
