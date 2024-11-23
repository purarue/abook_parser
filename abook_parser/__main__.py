import contextlib
from pathlib import Path
from typing import Literal, get_args, assert_never

from .parser import AbookData

import click


@click.group()
def main() -> None:
    pass


OutputType = Literal["abook", "json"]


@main.command()
@click.option(
    "-t",
    "--output-type",
    type=click.Choice(get_args(OutputType)),
    default="abook",
    help="output format type",
)
@click.option(
    "-k", "--sort-key", type=str, default=None, help="sort addressbook items by key"
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="output file path",
)
@click.argument(
    "FILE", type=click.Path(exists=True, path_type=Path, allow_dash=True), required=True
)
def parse(output_type: OutputType, output: Path, file: Path, sort_key: str) -> None:
    """
    Parse the addressbook file, and sort it by the name field
    """
    is_stdin = str(file) == "-"
    if is_stdin:
        text = click.get_text_stream("stdin").read()
    else:
        text = file.read_text()

    ab = AbookData.from_text(text)

    if sort_key is not None:
        ab.sort(sort_key)

    with contextlib.ExitStack() as ctx:
        match output_type:
            case "abook":
                data = ab.to_abook_fmt()
            case "json":
                data = ab.to_json()
            case _:
                assert_never(output_type)

        out = (
            ctx.enter_context(output.open("w"))
            if output is not None
            else click.get_text_stream("stdout")
        )

        out.write(data)


if __name__ == "__main__":
    main(prog_name="abook_parser")
