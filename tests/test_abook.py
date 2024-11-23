from abook_parser.parser import AbookData

example = """# abook addressbook file

[format]
program=abook
version=0.6.1


[0]
name=test
mobile=+1 333-333-3333
notes=something

[1]
name=name2
email=email1@example.com,email2@example.com
birthday=1990-01-01
mobile=+1 444-444-4444
"""


def test_abook():
    ab = AbookData.from_text(example)

    assert ab.format == {
        "program": "abook",
        "version": "0.6.1",
    }

    assert ab[0]["name"] == "test"
    assert ab[0]["mobile"] == "+1 333-333-3333"
    assert ab[0]["notes"] == "something"

    assert ab[1]["name"] == "name2"
    assert ab[1]["email"] == "email1@example.com,email2@example.com"
    assert ab[1]["birthday"] == "1990-01-01"
    assert ab[1]["mobile"] == "+1 444-444-4444"

    assert ab.to_abook_fmt() == example
