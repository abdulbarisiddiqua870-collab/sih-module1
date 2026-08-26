from __future__ import annotations

import re

_EDGE_JUNK = re.compile(r"^[\|`~^_=\s]+|[\|`~^_=\s]+$")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_QUOTE_MAP = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
    }
)


def clean_line(line: str) -> str:
    cleaned = line.translate(_QUOTE_MAP)
    cleaned = _EDGE_JUNK.sub("", cleaned)
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    return cleaned.strip()


def clean_text(text: str) -> str:
    lines = (clean_line(line) for line in text.splitlines())
    return "\n".join(line for line in lines if line)
