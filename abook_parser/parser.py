import json
import configparser
import io

from typing import Literal, Dict, List
from pathlib import Path

OutputType = Literal["abook", "json"]


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

    def to_abook_fmt(self) -> str:
        buf = io.StringIO()
        buf.write("# abook addressbook file\n\n[format]\n")
        for fkey, fval in self.format.items():
            buf.write(f"{fkey}={fval}\n")

        buf.write("\n")

        for key, val in self.items.items():
            buf.write(f"\n[{key}]\n")
            for k, v in val.items():
                buf.write(f"{k}={v}\n")

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
