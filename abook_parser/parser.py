from __future__ import annotations
import re
import json
import configparser
import io

from typing import Literal, Dict, List, NamedTuple, Any, Tuple, TYPE_CHECKING, TextIO
from pathlib import Path

if TYPE_CHECKING:
    from pyfzf import FzfPrompt


OutputType = Literal["abook", "json"]


SEPS = [":", "="]


class Query(NamedTuple):
    key: str
    val: str
    ignore_case: bool

    @classmethod
    def from_str(cls, s: str, ignore_case: bool) -> "Query":
        for sep in SEPS:
            if sep not in s:
                continue
            key, val = s.split(sep, maxsplit=1)
            return cls(key.lower(), val, ignore_case=ignore_case)
        else:
            raise ValueError("Could not parse query: " + s)


def render_contact_io(key: int, val: Dict[str, Any], fp: TextIO) -> None:
    fp.write(f"\n[{key}]\n")
    for k, v in val.items():
        fp.write(f"{k}={v}\n")


def render_contact_str(key: int, val: Dict[str, Any]) -> str:
    buf = io.StringIO()
    render_contact_io(key, val, buf)
    return buf.getvalue()


class AbookData:
    __slots__ = ["items", "format"]

    def __init__(
        self, *, items: Dict[int, Dict[str, str]], format: Dict[str, str]
    ) -> None:
        self.items: Dict[int, Dict[str, str]] = items
        self.format: Dict[str, str] = format

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(items={self.items}, format={self.format})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(items=<{len(self.items)} items>, format={self.format})"

    def __getitem__(self, key: str | int) -> Dict[str, str]:
        return self.items[int(key)]

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, AbookData):
            return False
        return self.items == value.items and self.format == value.format

    @classmethod
    def from_text(cls, text: str) -> "AbookData":

        config = configparser.ConfigParser()
        config.read_string(text)

        data = {}
        for section in config.sections():
            data[section] = dict(config.items(section))

        assert "format" in data, f"format section not found in {data}"
        format = data.pop("format")

        return cls(items={int(k): v for k, v in data.items()}, format=format)

    def keys(self) -> List[str]:
        from collections import Counter

        c: Counter[str] = Counter()
        for val in self.items.values():
            for k in val:
                c[k] += 1
        return [k for k in dict(c.most_common()).keys()]

    def sort(self, sort_key: str) -> None:
        has_sort_key: List[Dict[str, str]] = []
        cant_sort: List[Dict[str, str]] = []

        for val in self.items.values():
            if sort_key in val:
                has_sort_key.append(val)
            else:
                cant_sort.append(val)

        has_sort_key.sort(key=lambda x: x[sort_key].casefold())

        self.items = {i: data for i, data in enumerate(has_sort_key + cant_sort)}

    def fzf_pick(self, fzf: FzfPrompt) -> Tuple[int, Dict[str, Any]]:
        possible_keys = self.keys()
        chosen: list[str] = fzf.prompt(possible_keys)
        if not chosen:
            raise RuntimeError("Aborted")
        assert len(chosen) == 1
        ch = chosen[0]
        possible_vals = {k: v for (k, v) in self.items.items() if ch in v}
        mem: Dict[str, int] = {}
        for k, v in possible_vals.items():
            prompt = f"{k}: {" ".join(f'{vk}={vv}' for vk, vv in v.items())}"
            mem[prompt] = k
        chosen = fzf.prompt(mem)
        if not chosen:
            raise RuntimeError("Aborted")
        found_key = mem[chosen[0]]
        found_val = possible_vals[found_key]
        return found_key, found_val

    def query(self, query: Query) -> Tuple[int, Dict[str, Any]]:
        for key, val in self.items.items():
            for vkey in val:
                vlower = vkey.lower()
                if query.key == vlower:
                    if query.ignore_case:
                        query_val, search_for_val = query.val.lower(), val[vkey].lower()
                    else:
                        query_val, search_for_val = query.val, val[vkey]
                    if re.search(query_val, search_for_val):
                        return key, val
        raise RuntimeError("Query not found")

    def to_abook_fmt(self) -> str:
        buf = io.StringIO()
        buf.write("# abook addressbook file\n\n[format]\n")
        for fkey, fval in self.format.items():
            buf.write(f"{fkey}={fval}\n")

        buf.write("\n")

        for key, val in self.items.items():
            render_contact_io(key, val, buf)

        return buf.getvalue()

    def to_json(self) -> str:
        combined = {"format": self.format, "contacts": self.items}
        return json.dumps(combined, indent=4)


class AbookFile(AbookData):
    __slots__ = ["path", "items", "format"]

    def __init__(self, *, path: Path | str) -> None:
        self.path = Path(path).expanduser()
        text = self.path.read_text()
        ab = AbookData.from_text(text)
        for key in AbookData.__slots__:
            setattr(self, key, getattr(ab, key))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path})"

    def __str__(self) -> str:
        return self.__repr__()

    def write(self) -> None:
        self.path.write_text(self.to_abook_fmt())
