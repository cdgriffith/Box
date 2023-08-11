import box
from box.converters import (
    BOX_PARAMETERS as BOX_PARAMETERS,
    msgpack_available as msgpack_available,
    toml_read_library as toml_read_library,
    toml_write_library as toml_write_library,
    yaml_available as yaml_available,
)
from os import PathLike as PathLike
from typing import Any, Iterable, Optional, Type, Union, List

class BoxList(list):
    def __new__(cls, *args: Any, **kwargs: Any): ...
    box_options: Any
    box_org_ref: Any
    def __init__(self, iterable: Iterable = ..., box_class: Type[box.Box] = ..., **box_options: Any) -> None: ...
    def __getitem__(self, item: Any): ...
    def __delitem__(self, key: Any): ...
    def __setitem__(self, key: Any, value: Any): ...
    def append(self, p_object: Any) -> None: ...
    def extend(self, iterable: Any) -> None: ...
    def insert(self, index: Any, p_object: Any) -> None: ...
    def __copy__(self) -> "BoxList": ...
    def __deepcopy__(self, memo: Optional[Any] = ...) -> "BoxList": ...
    def __hash__(self) -> int: ...  # type: ignore[override]
    def to_list(self) -> List: ...
    def _dotted_helper(self) -> List[str]: ...
    def to_json(
        self,
        filename: Union[str, PathLike] = ...,
        encoding: str = ...,
        errors: str = ...,
        multiline: bool = ...,
        **json_kwargs: Any,
    ) -> Any: ...
    @classmethod
    def from_json(
        cls,
        json_string: str = ...,
        filename: Union[str, PathLike] = ...,
        encoding: str = ...,
        errors: str = ...,
        multiline: bool = ...,
        **kwargs: Any,
    ) -> Any: ...
    def to_yaml(
        self,
        filename: Union[str, PathLike] = ...,
        default_flow_style: bool = ...,
        encoding: str = ...,
        errors: str = ...,
        **yaml_kwargs: Any,
    ) -> Any: ...
    @classmethod
    def from_yaml(
        cls,
        yaml_string: str = ...,
        filename: Union[str, PathLike] = ...,
        encoding: str = ...,
        errors: str = ...,
        **kwargs: Any,
    ) -> Any: ...
    def to_toml(
        self, filename: Union[str, PathLike] = ..., key_name: str = ..., encoding: str = ..., errors: str = ...
    ) -> Any: ...
    @classmethod
    def from_toml(
        cls,
        toml_string: str = ...,
        filename: Union[str, PathLike] = ...,
        key_name: str = ...,
        encoding: str = ...,
        errors: str = ...,
        **kwargs: Any,
    ) -> Any: ...
    def to_msgpack(self, filename: Union[str, PathLike] = ..., **kwargs: Any) -> Any: ...
    @classmethod
    def from_msgpack(cls, msgpack_bytes: bytes = ..., filename: Union[str, PathLike] = ..., **kwargs: Any) -> Any: ...
    def to_csv(self, filename: Union[str, PathLike] = ..., encoding: str = ..., errors: str = ...) -> Any: ...
    @classmethod
    def from_csv(
        cls, csv_string: str = ..., filename: Union[str, PathLike] = ..., encoding: str = ..., errors: str = ...
    ) -> Any: ...
