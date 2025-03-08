# abook_parser

parser for the [abook](https://abook.sourceforge.io/) CLI

## Installation

Requires `python3.12+`

To install with pip, run:

```
pip install abook_parser
```

## Usage

This can read the addressbook, sort it by some key, and print a formatted version (either `JSON` or the `abook` addressbook format).

```
Usage: abook_parser parse [OPTIONS] FILE

  Parse the addressbook file, and sort it by the name field

Options:
  -t, --output-type [abook|json]  output format type
  -k, --sort-key TEXT             sort addressbook items by key
  -o, --output PATH               output file path
  --help                          Show this message and exit.
```

It also has commands to `add` or `edit` and item with a [`fzf`](https://github.com/junegunn/fzf)-based interactive mode.

```
Usage: abook_parser edit [OPTIONS] FILE

  Edit a field in the addressbook file

Options:
  --ignore-case / --no-ignore-case
                                  ignore case in query
  -q, --query TEXT                query string to search for
  --help                          Show this message and exit.
```

## Library Usage

The `abook_parser.parser.AbookFile` class can be used to interact with your addressbook file in code. Here are some of my scripts:

- [`abz`](https://purarue.xyz/d/abz?redirect) - [`fzf`](https://github.com/junegunn/fzf) based addressbook search script
- [`abook-populate`](https://github.com/purarue/HPI-personal/blob/master/scripts/abook-populate) - interactively prompts me to add new contacts to my addressbook by parsing my [locally stored Mail](https://github.com/purarue/HPI/blob/master/doc/MAIL_SETUP.md) and [SMS exports](https://github.com/karlicoss/HPI/blob/master/my/smscalls.py)
- [`birthdays`](https://purarue.xyz/d/birthdays?redirect) - lists upcoming birthdays from my addressbook

### Tests

```bash
git clone 'https://github.com/purarue/abook_parser'
cd ./abook_parser
pip install '.[testing]'
pytest
flake8 ./abook_parser
mypy ./abook_parser
```
