"""Private citizens' numbers that the AR published in free-text fields are masked.

Every number here is synthetic: built from a made-up prefix plus its check digit,
never copied from the data.
"""

import json

import pytest

from parlamento_aberto import privacy, sync
from parlamento_aberto.fetch import Response
from parlamento_aberto.normalise import dump_line, dump_record
from parlamento_aberto.sources import Source

M = privacy.MASK


def nif(first8: str) -> str:
    """Append the mod-11 check digit to eight digits."""
    total = sum(int(d) * w for d, w in zip(first8, range(9, 1, -1), strict=True))
    r = total % 11
    return first8 + str(0 if r < 2 else 11 - r)


def bad_check(n: str) -> str:
    return n[:8] + str((int(n[8]) + 1) % 10)


PERSON = [nif(p) for p in ("10000001", "23456780", "31111112", "45000003", "70000004")]
PERSON += [nif(p) for p in ("74000005", "75000006", "78000007")]
COMPANY = [nif(p) for p in ("50000001", "60000002", "71000005", "72000006", "79000008")]
# 8 (the old sole-trader range), 9x (condominiums, irregular companies, sole traders'
# estates) and 77 can identify a person, so they are masked like a personal NIF.
WIDER = [nif(p) for p in ("80000003", "81234560", "90000004", "91000009", "98000001")]
WIDER += [nif(p) for p in ("77000007",)]


def test_check_digit():
    for n in PERSON + COMPANY + WIDER:
        assert privacy.valid_nif(n)
        assert not privacy.valid_nif(bad_check(n))
    assert not privacy.valid_nif("12345")


@pytest.mark.parametrize("n", PERSON)
@pytest.mark.parametrize(
    "label",
    [
        "NIF",
        "nif",
        "NIF:",
        "NIF n.º",
        "NIF/NIPC",
        "NIF / NIPC",
        "número fiscal",
        "Número  Fiscal",
        "Contribuinte n.º",
        "contribuinte nº",
        "CONTRIBUINTE N.º",
    ],
)
def test_masks_personal_nif_after_a_label(label, n):
    text = f"O requerente, {label} {n}, residente em Lisboa."
    out, count = privacy.mask_text(text)
    assert n not in out
    assert out == f"O requerente, {label} {M}, residente em Lisboa."
    assert count == 1


@pytest.mark.parametrize("sep", [" ", "."])
def test_masks_personal_nif_written_in_groups_of_three(sep):
    n = PERSON[0]
    grouped = sep.join([n[:3], n[3:6], n[6:]])
    out, count = privacy.mask_text(f"contribuinte nº {grouped} de Braga")
    assert (out, count) == (f"contribuinte nº {M} de Braga", 1)
    longer = f"NIF {grouped}{sep}123"
    assert privacy.mask_text(longer) == (longer, 0)
    mixed = f"NIF {n[:3]} {n[3:6]}.{n[6:]}"
    assert privacy.mask_text(mixed) == (mixed, 0)


@pytest.mark.parametrize("n", COMPANY)
def test_leaves_company_nipc(n):
    text = f"A empresa X, NIF/NIPC {n}, com sede no Porto."
    assert privacy.mask_text(text) == (text, 0)


@pytest.mark.parametrize("n", WIDER)
@pytest.mark.parametrize("label", ["NIF", "NIF/NIPC", "Contribuinte n.º"])
def test_masks_sole_trader_condominium_and_77_numbers(label, n):
    text = f"A entidade, {label} {n}, com sede no Porto."
    out, count = privacy.mask_text(text)
    assert n not in out
    assert (out, count) == (f"A entidade, {label} {M}, com sede no Porto.", 1)


@pytest.mark.parametrize("n", WIDER)
def test_guard_fails_on_an_unmasked_sole_trader_condominium_or_77_number(n):
    bad = {"1/1.json": dump_record({"t": f"NIF/NIPC {n}"})}
    with pytest.raises(privacy.UnmaskedError) as e:
        privacy.guard(bad)
    assert n not in str(e.value)


@pytest.mark.parametrize("n", COMPANY)
def test_guard_passes_a_company_nipc(n):
    privacy.guard({"1/1.json": dump_record({"t": f"NIF/NIPC {n}"})})


def test_only_five_company_prefixes():
    assert privacy.COMPANY_PREFIXES == ("5", "6", "71", "72", "79")


def test_leaves_numbers_that_fail_the_check_or_have_no_label():
    n = PERSON[0]
    for text in [
        f"NIF {bad_check(n)}",
        f"Processo {n}",
        f"NIF {n}0",
        f"NIF 0{n}",
        "NIF 12345",
    ]:
        assert privacy.mask_text(text) == (text, 0)


@pytest.mark.parametrize(
    "text",
    ["Beneficiário n.º 1234567", "beneficiaria nº 42", "BENEFICIÁRIA N.º 98765432101"],
)
def test_masks_beneficiary_number(text):
    out, count = privacy.mask_text(f"Pedido do {text} da Segurança Social")
    assert count == 1
    assert not any(c.isdigit() for c in out)
    assert M in out


def test_masking_is_idempotent():
    text = f"NIF {PERSON[0]} e Beneficiário n.º 123 e NIPC {COMPANY[0]}"
    once, n1 = privacy.mask_text(text)
    twice, n2 = privacy.mask_text(once)
    assert (n1, n2) == (2, 0)
    assert once == twice


def test_masks_only_string_values_not_keys_or_numbers():
    n = PERSON[1]
    record = {"NIF": int(n), "Texto": f"NIF {n}", "Lista": [{"Obs": f"contribuinte n.º {n}"}]}
    out, count = privacy.mask_tree(record)
    assert count == 2
    assert out == {"NIF": int(n), "Texto": f"NIF {M}", "Lista": [{"Obs": f"contribuinte n.º {M}"}]}


def test_label_and_number_must_share_a_field():
    body = dump_record({"a": "NIF", "b": PERSON[2]})
    assert privacy.mask_file("1/1.json", body) == (body, 0)
    privacy.guard({"1/1.json": body})


def test_mask_file_handles_json_and_ndjson():
    n = PERSON[3]
    rec = dump_record({"id": 1, "t": f"NIF {n}"})
    lines = "\n".join(dump_line({"id": i, "t": f"NIF {n}"}) for i in range(3)) + "\n"
    out_rec, c1 = privacy.mask_file("1/1.json", rec)
    out_nd, c2 = privacy.mask_file("records.ndjson", lines.encode())
    assert (c1, c2) == (1, 3)
    assert n.encode() not in out_rec + out_nd
    assert privacy.mask_file("1/1.json", out_rec) == (out_rec, 0)
    assert privacy.mask_file("records.ndjson", out_nd) == (out_nd, 0)


def test_guard_fails_on_an_unmasked_match():
    good = {"1/1.json": dump_record({"t": f"NIF {M}"})}
    privacy.guard(good)
    bad = {"1/1.json": dump_record({"t": f"NIF {PERSON[4]}"})}
    with pytest.raises(privacy.UnmaskedError) as e:
        privacy.guard(bad)
    assert PERSON[4] not in str(e.value)
    assert "1/1.json" in str(e.value)


def src() -> Source:
    return Source(
        dataset="perguntas_requerimentos",
        legislature="XVII",
        part=None,
        url="https://example.test/p.json",
        layout="records",
        id_key="Id",
        ids={},
        names={},
        bucket=None,
    )


def test_sync_writes_masked_data(tmp_path):
    n = PERSON[5]
    body = json.dumps(
        [{"Id": 7, "Texto": f"Requerimento do cidadão com NIF {n}. Beneficiário n.º 55"}]
    ).encode()
    s = src()
    report = sync.sync_source(
        s, tmp_path, {}, get=lambda url: Response(200, "application/json", body), today="2026-10-20"
    )
    written = (tmp_path / s.key / "0" / "7.json").read_text(encoding="utf-8")
    assert n not in written and "55" not in written
    assert written.count(M) == 2
    assert report["masked"] == 2


def test_sync_fails_if_masking_misses(tmp_path, monkeypatch):
    n = PERSON[6]
    body = json.dumps([{"Id": 7, "Texto": f"NIF {n}"}]).encode()
    monkeypatch.setattr(privacy, "mask_tree", lambda obj: (obj, 0))
    with pytest.raises(privacy.UnmaskedError):
        sync.sync_source(
            src(),
            tmp_path,
            {},
            get=lambda url: Response(200, "application/json", body),
            today="2026-10-20",
        )
    assert not (tmp_path / src().key).exists()
