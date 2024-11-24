import contextlib
from pathlib import Path
from typing import Literal, get_args, assert_never, Dict

from .parser import AbookData, AbookFile, Query, parse_contact_str, render_contact_str

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


@main.command(short_help="Edit an item in the addressbook")
@click.option(
    "--ignore-case/--no-ignore-case",
    default=True,
    help="ignore case in query",
)
@click.option(
    "-q",
    "--query",
    type=str,
    default=None,
    help="query string to search for",
)
@click.argument(
    "FILE",
    type=click.Path(exists=True, path_type=Path, allow_dash=False),
    required=True,
)
def edit(file: Path, query: str, ignore_case: bool) -> None:
    from pyfzf import FzfPrompt

    ab = AbookFile(path=file)

    fzf = FzfPrompt(default_options=["--no-multi"])

    changes = False

    found_key: int | None = None
    found_val: Dict[str, str] | None = None

    if query:
        try:
            found_key, found_val = ab.query(
                Query.from_str(query, ignore_case=ignore_case)
            )
        except RuntimeError as e:
            return click.echo(str(e), err=True)
    else:
        try:
            found_key, found_val = ab.fzf_pick(fzf)
        except RuntimeError as e:
            return click.echo(str(e), err=True)

    rendered = render_contact_str(found_key, found_val).strip()
    fixed = click.edit(rendered)
    if fixed is not None:
        found = parse_contact_str(fixed)
        assert len(found) == 1, "expected exactly one item in edited text"
        fkey = list(found)[0]
        assert fkey == found_key, f"expected key {fkey} to match {found_key}"
        new_found_val = found[found_key]

        if new_found_val != found_val:
            ab.items[found_key] = new_found_val
            changes = True

    if changes:
        click.echo(f"Writing changes to {file}", err=True)
        ab.write()


if __name__ == "__main__":
    main(prog_name="abook_parser")
