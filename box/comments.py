#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comments attached to Box keys and BoxList items (#184).

Every Box and BoxList keeps the comments for its own keys or indexes, outside the data, in a
store of ``{key: {"before": [lines], "eol": str | None}}``. The outermost container can also hold
document comments, ``{"start": [lines], "end": [lines]}``.

YAML loaded with the ruamel.yaml round trip loader fills the stores, ``to_yaml`` writes them
back. ruamel attaches a comment line above a key to the previous key's token while parsing, so
``extract_comments`` walks the document in order and hands those trailing lines to the next key.
"""

from __future__ import annotations

import re
from typing import Any

from box.converters import _ruamel_to_builtin
from box.exceptions import BoxValueError

__all__ = [
    "extract_comments",
    "apply_comments",
    "has_comments",
    "commented_tree",
    "dump_yaml",
    "get_comment",
    "set_comment",
    "del_comment",
]

POSITIONS = ("before", "eol")
# Every character YAML treats as a line break. A comment line must never contain one, or the text
# after it would be read back as YAML content.
_LINE_BREAKS = re.compile("\r\n|[\r\n\x85\u2028\u2029]")
_CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
DOCUMENT_POSITIONS = ("start", "end")


def _token_lines(value: str) -> list[str]:
    """Comment token text to comment lines without the "#", blank lines kept as ""."""
    out = []
    for line in _LINE_BREAKS.split(value):
        line = line.strip()
        out.append(line[1:].lstrip() if line.startswith("#") else line)
    return out


def _text_to_lines(text: str) -> list[str]:
    return [line[1:].lstrip() if line.strip().startswith("#") else line for line in _LINE_BREAKS.split(text)]


def normalize(position: Any, text: Any, document: bool = False) -> Any:
    """Validate a comment set through the API and turn it into its stored form."""
    allowed = DOCUMENT_POSITIONS if document else POSITIONS
    if position not in allowed:
        raise BoxValueError(f"position must be one of {', '.join(repr(p) for p in allowed)}, not {position!r}")
    if text is None or text == "":
        return None
    if not isinstance(text, str):
        raise BoxValueError(f"comment must be a string, not {type(text).__name__}")
    if _CONTROL.search(text):
        raise BoxValueError("comments can't contain control characters")
    if position == "eol":
        if _LINE_BREAKS.search(text):
            raise BoxValueError("an end of line comment must be a single line")
        return _text_to_lines(text)[0]
    return _text_to_lines(text)


def public(entry: dict | None) -> dict | None:
    """Stored comment entry to what get_comment returns: strings, missing positions as None."""
    if not entry:
        return None
    return {k: ("\n".join(v) if isinstance(v, list) else v) for k, v in entry.items()}


def get_comment(obj, key) -> dict | None:
    owner, key = obj._comment_owner(key)
    if key is None:
        return public(owner._comment_document(create=False))
    store = owner._comment_store(create=False)
    return public(store.get(key)) if store else None


def set_comment(obj, key, text, position=None) -> None:
    owner, key = obj._comment_owner(key)
    owner._comment_check_frozen()
    document = key is None
    position = position or ("start" if document else "eol")
    value = normalize(position, text, document=document)
    if document:
        entry = owner._comment_document()
    else:
        store = owner._comment_store()
        entry = store.setdefault(key, {})
    if value is None:
        entry.pop(position, None)
    else:
        entry[position] = value
    if not document and not entry:
        del store[key]


def del_comment(obj, key) -> None:
    owner, key = obj._comment_owner(key)
    owner._comment_check_frozen()
    if key is None:
        owner._comment_document().clear()
    else:
        store = owner._comment_store(create=False)
        if store:
            store.pop(key, None)


def extract_comments(root: Any) -> dict | None:
    """
    Collect the comments of a document loaded with the ruamel.yaml round trip loader.

    :return: ``{"start": lines, "end": lines, "keys": {path: {"before": lines, "eol": text}}}``,
        or None when the data carries no comments (other loaders, or a document without any).
    """
    try:
        from ruamel.yaml.comments import CommentedMap, CommentedSeq
    except ImportError:  # pragma: no cover (depends on installed packages)
        return None
    if not isinstance(root, (CommentedMap, CommentedSeq)):
        return None

    model: dict = {"start": None, "end": None, "keys": {}}
    seen: set[int] = set()
    pending: list[str] = []

    def entry(path):
        return model["keys"].setdefault(path, {"before": [], "eol": None})

    def take_lines(tokens):
        for token in tokens or []:
            if token is not None and id(token) not in seen:
                seen.add(id(token))
                pending.extend(_token_lines(token.value)[:-1])

    def handle(token, path):
        if token is None or id(token) in seen:
            return
        seen.add(id(token))
        value = token.value
        if value.startswith("\n"):
            rest = value[1:]
        else:
            # The first line is the end of line comment, the following lines belong to the next key
            first, _, rest = value.partition("\n")
            entry(path)["eol"] = first.strip()[1:].strip()
        if rest:
            pending.extend(_token_lines(rest)[:-1])  # comment tokens end with a newline

    root_comment = getattr(root.ca, "comment", None)
    if root_comment and len(root_comment) > 1 and root_comment[1]:
        model["start"] = [line for token in root_comment[1] for line in _token_lines(token.value)[:-1]]
        seen.update(id(token) for token in root_comment[1])

    def walk(node, path):
        if isinstance(node, CommentedMap):
            items = node.items()
            is_map = True
        elif isinstance(node, CommentedSeq):
            items = enumerate(node)
            is_map = False
        else:
            return
        node_comment = getattr(node.ca, "comment", None)
        if path and node_comment and len(node_comment) > 1:
            take_lines(node_comment[1])
        for key, value in items:
            item_path = path + (_ruamel_to_builtin(key),)
            if pending:
                entry(item_path)["before"].extend(pending)
                pending.clear()
            tokens = node.ca.items.get(key)
            if tokens:
                if is_map:
                    handle(tokens[2], item_path)
                    take_lines(tokens[3])  # comment lines between "key:" and its nested value
                else:
                    handle(tokens[0], item_path)
            walk(value, item_path)

    walk(root, ())
    if pending:
        model["end"] = list(pending)
    if not model["start"] and not model["end"] and not model["keys"]:
        return None
    return model


def _resolve_key(container, key):
    """The key in `container` the YAML key ended up as, or a sentinel when it isn't there."""
    if isinstance(container, list):
        return key if isinstance(key, int) and 0 <= key < len(container) else _MISSING
    if dict.__contains__(container, key):
        return key
    found = container._comment_resolve(key)  # only Box / BoxList containers get here
    return found if dict.__contains__(container, found) else _MISSING


_MISSING = object()


def apply_comments(root, model: dict | None) -> None:
    """Store the comments of an extracted model on the Box / BoxList tree built from the same document."""
    if not model:
        return
    for position in DOCUMENT_POSITIONS:
        if model.get(position):
            root._comment_document()[position] = list(model[position])
    for path, comment in model["keys"].items():
        node = root
        for segment in path[:-1]:
            found = _resolve_key(node, segment)
            if found is _MISSING:
                node = None
                break
            node = list.__getitem__(node, found) if isinstance(node, list) else dict.__getitem__(node, found)
            if not hasattr(node, "_comment_store"):
                node = None
                break
        if node is None:
            continue  # the key moved or disappeared when the Box was built (box_dots, camel_killer, ...)
        key = _resolve_key(node, path[-1])
        if key is _MISSING:
            continue
        stored = {}
        if comment["before"]:
            stored["before"] = list(comment["before"])
        if comment["eol"]:
            stored["eol"] = comment["eol"]
        if stored:
            node._comment_store()[key] = stored


def has_comments(obj, _seen=None) -> bool:
    """True when any Box / BoxList in the tree has a key, item or document comment."""
    store = getattr(obj, "_comment_store", None)
    if store is None:
        return False
    if obj._comment_store(create=False) or obj._comment_document(create=False):
        return True
    seen = _seen if _seen is not None else set()
    if id(obj) in seen:
        return False
    seen.add(id(obj))
    values = obj.values() if isinstance(obj, dict) else obj
    return any(has_comments(value, seen) for value in values)


def _add_eol_comment(out, key, text):
    """End of line comment two spaces after the value, wherever it is (ruamel otherwise aligns it
    with a neighbouring comment, or uses one space when there is none)."""
    try:
        from ruamel.yaml.error import CommentMark
        from ruamel.yaml.tokens import CommentToken

        out._yaml_add_eol_comment([CommentToken(f" # {text}", CommentMark(0)), None], key=key)
    except (ImportError, AttributeError, TypeError):  # pragma: no cover (other ruamel versions)
        out.yaml_add_eol_comment(text, key)


def _set_ruamel_comment(out, key, comment, indent):
    # ruamel quirk: on a CommentedSeq the end of line comment must be set before the before comment
    if comment.get("eol"):
        _add_eol_comment(out, key, comment["eol"])
    if comment.get("before"):
        out.yaml_set_comment_before_after_key(key, before="\n".join(comment["before"]), indent=indent)


def commented_tree(obj, plain, column=0, _seen=None):
    """
    Turn `plain` (the to_dict / to_list output of `obj`) into ruamel CommentedMap / CommentedSeq
    objects carrying the comments stored on `obj` and its nested boxes.

    `column` is where this container's keys (or list dashes) start with ruamel's default layout:
    nested mappings are indented by 2, sequences start at their parent key's column.
    """
    from ruamel.yaml.comments import CommentedMap, CommentedSeq

    seen = _seen if _seen is not None else set()
    if isinstance(plain, (dict, list)):
        if id(plain) in seen:
            return plain  # self references are written as they are
        seen = seen | {id(plain)}
    if isinstance(plain, dict):
        out = CommentedMap()
        for key, value in plain.items():
            child = dict.get(obj, key) if isinstance(obj, dict) else None
            out[key] = commented_tree(child, value, column if isinstance(value, list) else column + 2, seen)
        keys = list(out)
    elif isinstance(plain, list):
        out = CommentedSeq()
        for index, value in enumerate(plain):
            child = list.__getitem__(obj, index) if isinstance(obj, list) and index < len(obj) else None
            out.append(commented_tree(child, value, column + 2, seen))
        keys = list(range(len(out)))
    else:
        return plain
    store = obj._comment_store(create=False) if hasattr(obj, "_comment_store") else None
    if store:
        for key in keys:
            if key in store:
                _set_ruamel_comment(out, key, store[key], column)
    return out


def _document_lines(obj, position) -> str:
    document = obj._comment_document(create=False) if hasattr(obj, "_comment_document") else None
    if not document or not document.get(position):
        return ""
    return "".join((f"# {line}" if line else "") + "\n" for line in document[position])


def dump_yaml(obj, plain, filename=None, encoding: str = "utf-8", errors: str = "strict", **yaml_kwargs):
    """
    to_yaml for Box and BoxList: with comments and the ruamel round trip dumper, write them out,
    otherwise dump `plain` exactly as before.
    """
    from box import converters

    use_comments = converters.ruamel_available and yaml_kwargs.get("ruamel_typ", "rt") == "rt" and has_comments(obj)
    if not use_comments:
        return converters._to_yaml(plain, filename=filename, encoding=encoding, errors=errors, **yaml_kwargs)
    body = converters._to_yaml(commented_tree(obj, plain), encoding=encoding, errors=errors, **yaml_kwargs)
    # Document comments are written as text: ruamel drops a blank line after a start comment
    text = _document_lines(obj, "start") + body + _document_lines(obj, "end")
    if not filename:
        return text
    converters._exists(filename, create=True)
    with open(filename, "w", encoding=encoding, errors=errors) as f:
        f.write(text)
    return None
