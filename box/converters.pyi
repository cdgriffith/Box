from collections.abc import Callable
from os import PathLike
from typing import Any

yaml_available: bool
ruamel_available: bool
pyyaml_available: bool
toml_available: bool
msgpack_available: bool
toon_available: bool
BOX_PARAMETERS: Any
toml_read_library: Any | None
toml_write_library: Any | None
toml_decode_error: Callable | None

def _exists(filename: str | PathLike, create: bool = ...) -> Any: ...
def _ruamel_to_builtin(obj: Any) -> Any: ...
def _load_yaml(*args: Any, **kwargs: Any) -> Any: ...
def _from_yaml_with_comments(*args: Any, **kwargs: Any) -> tuple[Any, dict | None]: ...
def _to_json(obj, filename: str | PathLike | None = ..., encoding: str = ..., errors: str = ..., **json_kwargs): ...
def _from_json(
    json_string: str | None = ...,
    filename: str | PathLike | None = ...,
    encoding: str = ...,
    errors: str = ...,
    multiline: bool = ...,
    **kwargs,
): ...
def _to_yaml(
    obj,
    filename: str | PathLike | None = ...,
    default_flow_style: bool = ...,
    encoding: str = ...,
    errors: str = ...,
    ruamel_typ: str = ...,
    ruamel_attrs: dict | None = ...,
    width: int = ...,
    sort_keys: bool = ...,
    **yaml_kwargs,
): ...
def _from_yaml(
    yaml_string: str | None = ...,
    filename: str | PathLike | None = ...,
    encoding: str = ...,
    errors: str = ...,
    ruamel_typ: str = ...,
    ruamel_attrs: dict | None = ...,
    **kwargs,
): ...
def _to_toml(obj, filename: str | PathLike | None = ..., encoding: str = ..., errors: str = ...): ...
def _from_toml(
    toml_string: str | None = ...,
    filename: str | PathLike | None = ...,
    encoding: str = ...,
    errors: str = ...,
): ...
def _to_msgpack(obj, filename: str | PathLike | None = ..., **kwargs): ...
def _from_msgpack(msgpack_bytes: bytes | None = ..., filename: str | PathLike | None = ..., **kwargs): ...
def _to_toon(obj, filename: str | PathLike | None = ..., encoding: str = ..., errors: str = ..., **kwargs): ...
def _from_toon(
    toon_string: str | None = ...,
    filename: str | PathLike | None = ...,
    encoding: str = ...,
    errors: str = ...,
    **kwargs,
): ...
def _to_csv(box_list, filename: str | PathLike | None = ..., encoding: str = ..., errors: str = ..., **kwargs): ...
def _from_csv(
    csv_string: str | None = ...,
    filename: str | PathLike | None = ...,
    encoding: str = ...,
    errors: str = ...,
    **kwargs,
): ...
