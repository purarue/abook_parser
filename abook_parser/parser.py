from __future__ import annotations
import re
import json
import configparser
import io
from typing import Iterator
from functools import cache


import click
from typing import (
    Literal,
    NamedTuple,
    Tuple,
    TextIO,
    Optional,
)
from pathlib import Path

from pyfzf import FzfPrompt


OutputType = Literal["abook", "json"]


SEPS = [":", "="]


class Query(NamedTuple):
    key: str
    val: str
    ignore_case: bool

    @classmethod
    def from_str(cls, s: str, ignore_case: bool) -> "Query":
        """
        E.g. name:alex.*

        Value is treated as a regex
        """
        for sep in SEPS:
            if sep not in s:
                continue
            key, val = s.split(sep, maxsplit=1)
            return cls(key.lower(), val, ignore_case=ignore_case)
        else:
            raise ValueError("Could not parse query: " + s)


def render_contact_io(key: int, val: dict[str, str], fp: TextIO) -> None:
    fp.write(f"\n[{key}]\n")
    for k, v in val.items():
        fp.write(f"{k}={v}\n")


def render_contact_str(key: int, val: dict[str, str]) -> str:
    buf = io.StringIO()
    render_contact_io(key, val, buf)
    return buf.getvalue()


def parse_contact_str(s: str) -> dict[int, dict[str, str]]:
    config = configparser.ConfigParser()
    config.read_string(s)
    data = {}
    for section in config.sections():
        data[int(section)] = dict(config.items(section))
    return data


class AbookData:
    __slots__ = ["items", "format"]

    def __init__(
        self, *, items: dict[int, dict[str, str]], format: dict[str, str]
    ) -> None:
        self.items: dict[int, dict[str, str]] = items
        self.format: dict[str, str] = format

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(items={self.items}, format={self.format})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(items=<{len(self.items)} items>, format={self.format})"

    def __getitem__(self, key: str | int) -> dict[str, str]:
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

    # easier to use/consume contacts field
    @property
    def contacts(self) -> Iterator[dict[str, str]]:
        return iter(self.items.values())

    def abook_keys(self) -> list[str]:
        from collections import Counter

        c: Counter[str] = Counter()
        for val in self.contacts:
            for k in val:
                c[k] += 1
        return [k for k in dict(c.most_common()).keys()]

    def max_index(self) -> int:
        indices = list(self.items)
        if not indices:
            return 0
        return max(indices)

    def add_contact(self, data: dict[str, str]) -> None:
        self.items[self.max_index() + 1] = data

    def sort(self, sort_key: str) -> None:
        has_sort_key: list[dict[str, str]] = []
        cant_sort: list[dict[str, str]] = []

        for val in self.contacts:
            if sort_key in val:
                has_sort_key.append(val)
            else:
                cant_sort.append(val)

        has_sort_key.sort(key=lambda x: x[sort_key].casefold())

        self.items = {i: data for i, data in enumerate(has_sort_key + cant_sort)}

    def fzf_pick(self, fzf: FzfPrompt) -> Tuple[int, dict[str, str]]:
        mem: dict[str, int] = {}
        for k, v in self.items.items():
            prompt = f"{k}: {" ".join(f'{vk}={vv}' for vk, vv in v.items())}"
            mem[prompt] = k
        chosen = fzf.prompt(mem, "--no-multi")
        if not chosen:
            raise RuntimeError("Aborted")
        found_key: int = mem[chosen[0]]
        found_val = self.items[found_key]
        return found_key, found_val

    def query(self, query: Query) -> Tuple[int, dict[str, str]]:
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

    def pick(
        self, *, fzf: FzfPrompt, query: str | None = None, ignore_case: bool = True
    ) -> Optional[Tuple[int, dict[str, str]]]:
        """
        Picks an item in the addressbook

        Returns the integer index and the item, or None
        if it was cancelled
        """
        found_key: int | None = None
        found_val: dict[str, str] | None = None

        if query:
            try:
                found_key, found_val = self.query(
                    Query.from_str(query, ignore_case=ignore_case)
                )
            except RuntimeError as e:
                click.echo(str(e), err=True)
                return None
        else:
            try:
                found_key, found_val = self.fzf_pick(fzf)
            except RuntimeError as e:
                click.echo(str(e), err=True)
                return None

        return found_key, found_val

    def prompt_edit(
        self,
        *,
        fzf: FzfPrompt | None = None,
        query: str | None = None,
        ignore_case: bool = True,
    ) -> bool:
        """
        Edits an item in the addressbook

        Returns True if an edit was made
        """
        if fzf is None:
            fzf = Fzf()

        res = self.pick(fzf=fzf, query=query, ignore_case=ignore_case)
        if res is None:
            return False

        found_key, found_val = res
        rendered = render_contact_str(found_key, found_val).strip()
        fixed = click.edit(rendered)
        if fixed is not None:
            found = parse_contact_str(fixed)
            assert len(found) == 1, "expected exactly one item in edited text"
            fkey = list(found)[0]
            assert fkey == found_key, f"expected key {fkey} to match {found_key}"
            new_found_val = found[found_key]

            if new_found_val != found_val:
                self.items[found_key] = new_found_val
                return True

        return False

    def prompt_add(
        self,
        *,
        fzf: FzfPrompt | None = None,
        data: dict[str, str] | None = None,
    ) -> None:
        if fzf is None:
            fzf = Fzf()

        if data is not None:
            data_lines = [f"{key}={val}" for key, val in data.items()]
            chosen: list[str] = fzf.prompt(
                data_lines, "--multi", '--prompt="Select fields to add: "'
            )
            parsed = parse_contact_str("[0]\n" + "\n".join(chosen))
            assert len(parsed) == 1
            data = list(parsed.values())[0]
        else:
            data = {}

        data = {name.lower(): value.strip() for name, value in data.items()}

        if "name" not in data:
            data["name"] = click.prompt("Name", type=str)

        self.add_contact(data)

    def prompt_edit_or_add(
        self,
        *,
        fzf: FzfPrompt | None = None,
        query: str | None = None,
        ignore_case: bool = True,
    ) -> bool:
        """
        Returns a bool signifying if something was added/edited
        """
        if fzf is None:
            fzf = Fzf()
        res = self.prompt_edit(fzf=fzf, query=query, ignore_case=ignore_case)
        if res is True:
            return True

        old = len(self.items)
        self.prompt_add()
        return old != len(self.items)


@cache
def Fzf() -> FzfPrompt:
    return FzfPrompt(default_options=[])


class AbookFile(AbookData):
    __slots__ = ["path", "items", "format"]

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser()
        text = self.path.read_text()
        ab = AbookData.from_text(text)
        for key in AbookData.__slots__:
            assert key in self.__class__.__slots__
            setattr(self, key, getattr(ab, key))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path})"

    def __str__(self) -> str:
        return self.__repr__()

    def write(self) -> None:
        self.path.write_text(self.to_abook_fmt())
