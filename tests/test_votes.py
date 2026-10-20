import json
from pathlib import Path

import pytest

from parlamento_aberto.votes import (
    GroupCount,
    GroupPosition,
    NamedDeputy,
    VoteDetail,
    VoteDetailError,
    parse_detalhe,
)

SAMPLES = json.loads(
    (Path(__file__).parent / "fixtures" / "detalhe_samples.json").read_text(encoding="utf-8")
)
LEGISLATURES = ["IA", "IB", "II", "III", "IV", "V", "VI", "VII", "VIII"]
LEGISLATURES += ["IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII"]


def test_samples_cover_every_legislature():
    assert {s["legislature"] for s in SAMPLES} == set(LEGISLATURES)


@pytest.mark.parametrize(
    "sample", SAMPLES, ids=[f"{s['legislature']}-{s['vote_id']}" for s in SAMPLES]
)
def test_real_strings_parse_fully(sample):
    text = sample["detalhe"]
    detail = parse_detalhe(text)
    parsed = len(detail.groups) + len(detail.counts) + len(detail.deputies)
    assert parsed == text.count("<I>")


def test_groups_only():
    text = "A Favor: <I>PS</I>, <I> PSD</I><BR>Contra:<I>PCP</I>"
    assert parse_detalhe(text) == VoteDetail(
        groups=(
            GroupPosition("PS", "favour"),
            GroupPosition("PSD", "favour"),
            GroupPosition("PCP", "against"),
        ),
        counts=(),
        deputies=(),
    )


def test_counts_and_named_deputies():
    # XVII, vote 140185
    text = (
        "A Favor: <I>PSD</I>, <I> CH</I>, <I> PS</I>, <I> CDS-PP</I><BR>"
        "Abstenção:<I>1-PS</I>, <I> IL</I>, <I> L</I>, <I> PCP</I>, <I> PAN</I>, <I> JPP</I>, "
        "<I> Pedro Delgado Alves (PS)</I>"
    )
    detail = parse_detalhe(text)
    assert detail.counts == (GroupCount("PS", "abstention", 1),)
    assert detail.deputies == (NamedDeputy("Pedro Delgado Alves", "PS", "abstention"),)
    assert GroupPosition("PS", "favour") in detail.groups
    assert len(detail.groups) == 9


def test_all_four_positions():
    # IX, vote 29130
    text = (
        "A Favor: <I>PSD</I>, <I> CDS-PP</I><BR>Contra:<I>PS</I><BR>Abstenção:<I>PCP</I>"
        "<BR>Ausência: <I>BE</I>, <I> PEV</I>"
    )
    positions = [g.position for g in parse_detalhe(text).groups]
    assert positions == ["favour", "favour", "against", "abstention", "absent", "absent"]


def test_odd_whitespace_in_names_is_collapsed():
    # XIII, vote 79231
    text = "A Favor: <I>PSD</I>, <I> Lúcia  Araújo Silva (PS)</I><BR>Abstenção:<I>PS</I>"
    assert parse_detalhe(text).deputies == (NamedDeputy("Lúcia Araújo Silva", "PS", "favour"),)


def test_old_group_codes():
    # IB, vote 48247
    text = "A Favor: <I>PSD</I><BR>Contra:<I>Francisco De Sousa Tavares (DR)</I><BR>"
    text += "Abstenção:<I>PS</I>, <I> MDP/CDE</I>"
    detail = parse_detalhe(text)
    assert GroupPosition("MDP/CDE", "abstention") in detail.groups
    assert detail.deputies == (NamedDeputy("Francisco De Sousa Tavares", "DR", "against"),)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Presente: <I>PS</I>",
        "A Favor <I>PS</I>",
        "A Favor: PS",
        "A Favor: <I>PS</I> PSD",
        "A Favor: <I>PS</I>,",
        "A Favor: <I>PS</I>, , <I>PSD</I>",
        "A Favor: <I>PS</I><I>PSD</I>",
        "A Favor: <I></I>",
        "A Favor: <B>PS</B>",
        "A Favor: <I>PS</I><BR>",
        "A Favor: <I>PS</I><BR>A Favor: <I>PSD</I>",
        "A Favor: <I>0-PS</I>",
        "A Favor: <I>2-</I>",
        "A Favor: <I>Carlos Silva ()</I>",
        "A Favor: <I>ps</I>",
    ],
)
def test_anything_else_raises(text):
    with pytest.raises(VoteDetailError):
        parse_detalhe(text)
