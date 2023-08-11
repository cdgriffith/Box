from box.box import Box as Box
from box.box_list import BoxList as BoxList
from os import PathLike
from typing import Any, Union

def box_from_file(
    file: Union[str, PathLike],
    file_type: str = ...,
    encoding: str = ...,
    errors: str = ...,
    **kwargs: Any,
) -> Union[Box, BoxList]: ...
def box_from_string(
    content: str,
    string_type: str = ...,
) -> Union[Box, BoxList]: ...
