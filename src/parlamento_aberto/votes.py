"""Parser for the `detalhe` string on Iniciativas votes.

A `detalhe` string lists who voted which way, one position per `<BR>`-separated segment:

    A Favor: <I>PS</I>, <I> 2-PSD</I>, <I> Carlos Silva (PSD)</I><BR>Contra:<I>PCP</I>

Each `<I>` item is one of:

- a group code (`PS`): the group took that position;
- a count and a group (`2-PSD`): that many deputies of the group took that position;
- a deputy name and a group (`Carlos Silva (PSD)`): that deputy took that position.

The parser either consumes the whole string or raises `VoteDetailError`. It never drops
anything silently.
"""

import re
from dataclasses import dataclass

POSITIONS = {
    "A Favor": "favour",
    "Contra": "against",
    "Abstenção": "abstention",
    "Ausência": "absent",
}

_GROUP = r"[A-Z][A-Za-z]*(?:[-/][A-Z][A-Za-z]*)*"
_SEGMENT = re.compile(r"(?P<label>[^:<>]+):\s*(?P<items>.*)", re.DOTALL)
_ITEM = re.compile(r"<I>(?P<body>[^<>]*)</I>")
_SEPARATOR = re.compile(r",\s*")
_GROUP_ONLY = re.compile(rf"(?P<group>{_GROUP})")
_COUNT = re.compile(rf"(?P<count>[1-9][0-9]*)-(?P<group>{_GROUP})")
_NAMED = re.compile(rf"(?P<name>[^()\d]+?) ?\((?P<group>{_GROUP})\)")


class VoteDetailError(ValueError):
    """The string does not match the known `detalhe` format."""


@dataclass(frozen=True)
class GroupPosition:
    group: str
    position: str


@dataclass(frozen=True)
class GroupCount:
    group: str
    position: str
    count: int


@dataclass(frozen=True)
class NamedDeputy:
    name: str
    group: str
    position: str


@dataclass(frozen=True)
class VoteDetail:
    groups: tuple[GroupPosition, ...]
    counts: tuple[GroupCount, ...]
    deputies: tuple[NamedDeputy, ...]


def parse_detalhe(text: str) -> VoteDetail:
    """Parse a `detalhe` string into group positions, counts and named deputies."""
    groups: list[GroupPosition] = []
    counts: list[GroupCount] = []
    deputies: list[NamedDeputy] = []
    seen: set[str] = set()

    for segment in text.split("<BR>"):
        match = _SEGMENT.fullmatch(segment)
        if not match:
            raise VoteDetailError(f"segment without a position: {segment!r}")
        label = match["label"].strip()
        position = POSITIONS.get(label)
        if position is None:
            raise VoteDetailError(f"unknown position: {label!r}")
        if position in seen:
            raise VoteDetailError(f"position listed twice: {label!r}")
        seen.add(position)

        for body in _items(match["items"]):
            item = " ".join(body.split())
            if m := _GROUP_ONLY.fullmatch(item):
                groups.append(GroupPosition(m["group"], position))
            elif m := _COUNT.fullmatch(item):
                counts.append(GroupCount(m["group"], position, int(m["count"])))
            elif m := _NAMED.fullmatch(item):
                deputies.append(NamedDeputy(m["name"], m["group"], position))
            else:
                raise VoteDetailError(f"unknown item: {body!r}")

    return VoteDetail(tuple(groups), tuple(counts), tuple(deputies))


def _items(text: str) -> list[str]:
    """Split `<I>a</I>, <I>b</I>` into item bodies, requiring the whole text to match."""
    bodies = []
    pos = 0
    while True:
        item = _ITEM.match(text, pos)
        if not item:
            raise VoteDetailError(f"expected an <I> item at {text[pos:]!r}")
        bodies.append(item["body"])
        pos = item.end()
        if pos == len(text):
            return bodies
        separator = _SEPARATOR.match(text, pos)
        if not separator:
            raise VoteDetailError(f"unexpected text after an item: {text[pos:]!r}")
        pos = separator.end()
