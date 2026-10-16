import pytest
from frontmatter import as_list, parse_frontmatter


def test_a_file_without_frontmatter_has_none():
    assert parse_frontmatter("# Título\n\ntexto") == {}
    assert parse_frontmatter("") == {}


def test_scalars_are_read_and_quotes_are_removed():
    text = "---\nname: revisor\ndescription: \"Revisa un diff\"\nmodel: 'sonnet'\n---\ncuerpo"
    assert parse_frontmatter(text) == {
        "name": "revisor",
        "description": "Revisa un diff",
        "model": "sonnet",
    }


def test_block_lists_are_read():
    text = '---\npaths:\n  - "**/tests/**/*.py"\n  - "**/test_*.py"\n---\n'
    assert parse_frontmatter(text)["paths"] == ["**/tests/**/*.py", "**/test_*.py"]


def test_inline_lists_are_read():
    text = "---\npaths: [a.py, 'b/*.py']\n---\n"
    assert parse_frontmatter(text)["paths"] == ["a.py", "b/*.py"]


def test_hyphenated_keys_and_comments_are_supported():
    text = "---\n# comentario\nallowed-tools: Read Grep Glob\nargument-hint: <ticket>\n---\n"
    data = parse_frontmatter(text)
    assert data["allowed-tools"] == "Read Grep Glob"
    assert data["argument-hint"] == "<ticket>"


def test_an_unterminated_frontmatter_is_ignored():
    assert parse_frontmatter("---\nname: x\nsin cierre") == {}


def test_the_body_is_not_parsed_as_frontmatter():
    text = "---\nname: x\n---\nclave: valor\n- item\n"
    assert parse_frontmatter(text) == {"name": "x"}


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Read, Grep, Glob", ["Read", "Grep", "Glob"]),
        ("Read Grep Glob", ["Read", "Grep", "Glob"]),
        (["Read", "Grep"], ["Read", "Grep"]),
        ("Bash(python scripts/verify.py*)", ["Bash(python scripts/verify.py*)"]),
        ("Read, Bash(git log *)", ["Read", "Bash(git log *)"]),
        ("", []),
        (None, []),
    ],
)
def test_as_list_splits_commas_and_spaces_but_keeps_parenthesized_specifiers(value, expected):
    assert as_list(value) == expected
