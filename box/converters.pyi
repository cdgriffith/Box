from typing import Any, Callable, Optional, Union, Dict
from os import PathLike

yaml_available: bool
toml_available: bool
msgpack_available: bool
BOX_PARAMETERS: Any
toml_read_library: Optional[Any]
toml_write_library: Optional[Any]
toml_decode_error: Optional[Callable]

def _to_json(
    obj, filename: Optional[Union[str, PathLike]] = ..., encoding: str = ..., errors: str = ..., **json_kwargs
): ...
def _from_json(
    json_string: Optional[str] = ...,
    filename: Optional[Union[str, PathLike]] = ...,
    encoding: str = ...,
    errors: str = ...,
    multiline: bool = ...,
    **kwargs,
): ...
def _to_yaml(
    obj,
    filename: Optional[Union[str, PathLike]] = ...,
    default_flow_style: bool = ...,
    encoding: str = ...,
    errors: str = ...,
    ruamel_typ: str = ...,
    ruamel_attrs: Optional[Dict] = ...,
    **yaml_kwargs,
): ...
def _from_yaml(
    yaml_string: Optional[str] = ...,
    filename: Optional[Union[str, PathLike]] = ...,
    encoding: str = ...,
    errors: str = ...,
    ruamel_typ: str = ...,
    ruamel_attrs: Optional[Dict] = ...,
    **kwargs,
): ...
def _to_toml(obj, filename: Optional[Union[str, PathLike]] = ..., encoding: str = ..., errors: str = ...): ...
def _from_toml(
    toml_string: Optional[str] = ...,
    filename: Optional[Union[str, PathLike]] = ...,
    encoding: str = ...,
    errors: str = ...,
): ...
def _to_msgpack(obj, filename: Optional[Union[str, PathLike]] = ..., **kwargs): ...
def _from_msgpack(msgpack_bytes: Optional[bytes] = ..., filename: Optional[Union[str, PathLike]] = ..., **kwargs): ...
def _to_csv(
    box_list, filename: Optional[Union[str, PathLike]] = ..., encoding: str = ..., errors: str = ..., **kwargs
): ...
def _from_csv(
    csv_string: Optional[str] = ...,
    filename: Optional[Union[str, PathLike]] = ...,
    encoding: str = ...,
    errors: str = ...,
    **kwargs,
): ...
