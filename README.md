# abook_parser

parser for the abook CLI

## Installation

Requires `python3.9+`

To install with pip, run:

```
pip install git+https://github.com/purarue/abook_parser
```

## Usage

```
abook_parser --help
```

### Tests

```bash
git clone 'https://github.com/purarue/abook_parser'
cd ./abook_parser
pip install '.[testing]'
pytest
flake8 ./abook_parser
mypy ./abook_parser
```
