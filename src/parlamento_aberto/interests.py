"""Python model: read RegistoInteresses into declarations and declared items.

Every RegistoInteresses file lists the same people, one record each, with one of four
keys filled: RegistoInteressesV1 (XI), V2 (XII, XIII), V3 (Constituinte to X, XIV, XV)
or V5 (XIV, XV). Most records only name the person; declarations sit in cadRgi (V1, V2),
RecordInterests (V3) or the V5 form itself.

The parser knows every list each format carries and fails on one it does not know, so a
new field cannot be dropped silently. Names, spouse, marital status, property regime,
tax and contact fields are read past, not republished.
"""

import json
import tempfile
from pathlib import Path

import duckdb

VERSIONS = (
    "RegistoInteressesV1",
    "RegistoInteressesV2",
    "RegistoInteressesV3",
    "RegistoInteressesV5",
)

DECLARATION_COLUMNS = {
    "declaration_key": "VARCHAR",
    "cadastro_id": "BIGINT",
    "format_version": "VARCHAR",
    "declaration_id": "BIGINT",
    "declared_legislature": "VARCHAR",
    "position": "VARCHAR",
    "position_start_raw": "VARCHAR",
    "position_changed_raw": "VARCHAR",
    "position_end_raw": "VARCHAR",
    "version_date_raw": "VARCHAR",
    "is_exclusive": "BOOLEAN",
    "items": "INTEGER",
    "legislature": "VARCHAR",
    "source_file": "VARCHAR",
}
ITEM_COLUMNS = {
    "declaration_key": "VARCHAR",
    "item_number": "INTEGER",
    "category": "VARCHAR",
    "source_list": "VARCHAR",
    "item_id": "BIGINT",
    "type_code": "INTEGER",
    "description": "VARCHAR",
    "entity": "VARCHAR",
    "nature": "VARCHAR",
    "activity_area": "VARCHAR",
    "location": "VARCHAR",
    "share": "VARCHAR",
    "paid_raw": "VARCHAR",
    "start_date_raw": "VARCHAR",
    "end_date_raw": "VARCHAR",
    "date_raw": "VARCHAR",
    "legislature": "VARCHAR",
    "source_file": "VARCHAR",
}
FILE_COLUMNS = {
    "legislature": "VARCHAR",
    "source_file": "VARCHAR",
    "people": "INTEGER",
    "declarations": "INTEGER",
}


class InterestsError(ValueError):
    pass


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _id(value) -> int | None:
    return None if value in (None, "") else int(float(value))


def _list(value, what: str) -> list:
    if value is None:
        return []
    if isinstance(value, dict):  # XML converted to JSON turns one item into an object
        return [value]
    if not isinstance(value, list):
        raise InterestsError(f"{what}: expected a list, got {type(value).__name__}")
    return value


def _check_keys(body: dict, known: set[str], what: str) -> None:
    unknown = sorted(k for k, v in body.items() if k not in known and v not in (None, "", []))
    if unknown:
        raise InterestsError(f"{what}: unknown field {', '.join(unknown)}")


def _yes_no(value) -> bool | None:
    return {"S": True, "N": False}.get(_text(value) or "")


# --- V1 and V2: cadRgi -----------------------------------------------------------------

RGI_KEYS = {
    "rgiActividades",
    "rgiApoiosBeneficios",
    "rgiCadId",
    "rgiCargoData",
    "rgiCargoDes",
    "rgiCargosSociais",
    "rgiDataVersao",
    "rgiId",
    "rgiLegDes",
    "rgiOutrasSituacoes",
    "rgiRegimeBens",
    "rgiRegimeBensDes",
    "rgiRegimeBensId",
    "rgiServicosPrestados",
    "rgiSociedades",
}
CAD_KEYS = {
    "cadActividadeProfissional",
    "cadEstadoCivilCod",
    "cadEstadoCivilDes",
    "cadFamId",
    "cadId",
    "cadNomeCompleto",
    "cadNomeConjuge",
    "cadRgi",
}


def _free_text(category: str, source_list: str, value) -> list[dict]:
    text = _text(value)
    return [{"category": category, "source_list": source_list, "description": text}] if text else []


def _v12_items(rgi: dict) -> list[dict]:
    items = []
    acts = rgi.get("rgiActividades")
    if isinstance(acts, str):  # V1 publishes activities as one free-text field
        items += _free_text("activity", "rgiActividades", acts)
    else:
        for a in _list(acts, "rgiActividades"):
            items.append(
                {
                    "category": "activity",
                    "source_list": "rgiActividades",
                    "item_id": _id(a.get("rgaId")),
                    "description": _text(a.get("rgaActividade")),
                    "paid_raw": _text(a.get("rgaRemunerada")),
                    "start_date_raw": _text(a.get("rgaDataInicio")),
                    "end_date_raw": _text(a.get("rgaDataFim")),
                }
            )
    for c in _list(rgi.get("rgiCargosSociais"), "rgiCargosSociais"):
        items.append(
            {
                "category": "social_position",
                "source_list": "rgiCargosSociais",
                "item_id": _id(c.get("rgcId")),
                "description": _text(c.get("rgcCargo")),
                "entity": _text(c.get("rgcEntidade")),
                "activity_area": _text(c.get("rgcAreaActividade")),
                "location": _text(c.get("rgcLocalSede")),
                "start_date_raw": _text(c.get("rgcDataInicio")),
                "end_date_raw": _text(c.get("rgcDataFim")),
            }
        )
    for s in _list(rgi.get("rgiSociedades"), "rgiSociedades"):
        items.append(
            {
                "category": "society",
                "source_list": "rgiSociedades",
                "item_id": _id(s.get("rgsId")),
                "entity": _text(s.get("rgsEntidade")),
                "activity_area": _text(s.get("rgsAreaActividade")),
                "location": _text(s.get("rgsLocalSede")),
                "share": _text(s.get("rgsPartiSocial")),
            }
        )
    items += _free_text("support", "rgiApoiosBeneficios", rgi.get("rgiApoiosBeneficios"))
    items += _free_text("service", "rgiServicosPrestados", rgi.get("rgiServicosPrestados"))
    items += _free_text("other_situation", "rgiOutrasSituacoes", rgi.get("rgiOutrasSituacoes"))
    return items


def _v12(version: str, body: dict) -> tuple[int, list[tuple[dict, list[dict]]]]:
    _check_keys(body, CAD_KEYS, version)
    cadastro_id = _id(body.get("cadId"))
    out = []
    for rgi in _list(body.get("cadRgi"), f"{version}.cadRgi"):
        _check_keys(rgi, RGI_KEYS, f"{version}.cadRgi")
        decl = {
            "declaration_id": _id(rgi.get("rgiId")),
            "declared_legislature": _text(rgi.get("rgiLegDes")),
            "position": _text(rgi.get("rgiCargoDes")),
            "position_start_raw": _text(rgi.get("rgiCargoData")),
            "version_date_raw": _text(rgi.get("rgiDataVersao")),
        }
        out.append((decl, _v12_items(rgi)))
    return cadastro_id, out


# --- V3: RecordInterests ---------------------------------------------------------------

V3_KEYS = {
    "DGFNumber",
    "Exclusivity",
    "FullName",
    "MaritalStatus",
    "MatrimonialRegime",
    "RecordId",
    "RecordInterests",
    "SpouseName",
}
V3_RECORD_KEYS = {
    "Activities",
    "OtherSituations",
    "PositionBeginDate",
    "PositionChangedDate",
    "PositionDesignation",
    "PositionEndDate",
    "RecordId",
    "ServicesProvided",
    "SocialPositions",
    "Societies",
    "Supports",
}


def _v3_items(ri: dict) -> list[dict]:
    items = []
    for a in _list(ri.get("Activities"), "Activities"):
        items.append(
            {
                "category": "activity",
                "source_list": "Activities",
                "type_code": a.get("Type"),
                "description": _text(a.get("Activity")),
                "entity": _text(a.get("Entity")),
                "start_date_raw": _text(a.get("BeginDate")),
                "end_date_raw": _text(a.get("EndDate")),
            }
        )
    for p in _list(ri.get("SocialPositions"), "SocialPositions"):
        items.append(
            {
                "category": "social_position",
                "source_list": "SocialPositions",
                "type_code": p.get("Type"),
                "description": _text(p.get("Position")),
                "entity": _text(p.get("Entity")),
                "activity_area": _text(p.get("ActivityArea")),
                "location": _text(p.get("HeadOfficeLocation")),
            }
        )
    for s in _list(ri.get("Societies"), "Societies"):
        items.append(
            {
                "category": "society",
                "source_list": "Societies",
                "entity": _text(s.get("Entity")),
                "activity_area": _text(s.get("ActivityArea")),
                "location": _text(s.get("HeadOfficeLocation")),
                "share": _text(s.get("SocialParticipation")),
            }
        )
    for key, field, category in (
        ("Supports", "Support", "support"),
        ("ServicesProvided", "Service", "service"),
        ("OtherSituations", "Situation", "other_situation"),
    ):
        for x in _list(ri.get(key), key):
            items.append(
                {"category": category, "source_list": key, "description": _text(x.get(field))}
            )
    return items


def _v3(body: dict, legislature: str) -> tuple[int, list[tuple[dict, list[dict]]]]:
    _check_keys(body, V3_KEYS, "RegistoInteressesV3")
    exclusive = _yes_no(body.get("Exclusivity"))
    out = []
    for ri in _list(body.get("RecordInterests"), "RecordInterests"):
        _check_keys(ri, V3_RECORD_KEYS, "RegistoInteressesV3.RecordInterests")
        decl = {
            "declaration_id": _id(ri.get("RecordId")),
            # V3 declarations carry no legislature of their own.
            "declared_legislature": legislature,
            "position": _text(ri.get("PositionDesignation")),
            "position_start_raw": _text(ri.get("PositionBeginDate")),
            "position_changed_raw": _text(ri.get("PositionChangedDate")),
            "position_end_raw": _text(ri.get("PositionEndDate")),
            "is_exclusive": exclusive,
        }
        out.append((decl, _v3_items(ri)))
    return _id(body.get("RecordId")), out


# --- V5: one form per record -----------------------------------------------------------

V5_KEYS = {
    "Categoria",
    "Exclusividade",
    "FactoDeclaracao",
    "GenApoios",
    "GenCargosMaisTresAnos",
    "GenCargosMenosTresAnos",
    "GenDadosPessoais",
    "GenIncompatibilidade",
    "GenOutraSituacao",
    "GenServicoPrestado",
    "GenSociedade",
    "IdCadastroGODE",
    "Legislatura",
    "NomeIdentificacao",
    "Servico",
    "versao",
}


def _v5_items(body: dict) -> list[dict]:
    items = []
    for key in ("GenCargosMenosTresAnos", "GenCargosMaisTresAnos"):
        for c in _list(body.get(key), key):
            items.append(
                {
                    "category": "activity",
                    "source_list": key,
                    "item_id": _id(c.get("Id")),
                    "description": _text(c.get("CargoFuncaoAtividade")),
                    "entity": _text(c.get("Entidade")),
                    "nature": _text(c.get("Natureza")),
                    "location": _text(c.get("LocalSede")),
                    "paid_raw": _text(c.get("Remunerada")),
                    "start_date_raw": _text(c.get("DataInicio")),
                    "end_date_raw": _text(c.get("DataTermo")),
                }
            )
    for s in _list(body.get("GenSociedade"), "GenSociedade"):
        items.append(
            {
                "category": "society",
                "source_list": "GenSociedade",
                "item_id": _id(s.get("Id")),
                "entity": _text(s.get("Sociedade")),
                "nature": _text(s.get("Natureza")),
                "activity_area": _text(s.get("NaturezaArea")),
                "location": _text(s.get("LocalSede")),
                "share": _text(s.get("Participacao")),
            }
        )
    for a in _list(body.get("GenApoios"), "GenApoios"):
        items.append(
            {
                "category": "support",
                "source_list": "GenApoios",
                "item_id": _id(a.get("Id")),
                "description": _text(a.get("Apoio")),
                "entity": _text(a.get("Entidade")),
                "nature": _text(a.get("NaturezaBeneficio")),
                "activity_area": _text(a.get("NaturezaArea")),
                "date_raw": _text(a.get("Data")),
            }
        )
    for s in _list(body.get("GenServicoPrestado"), "GenServicoPrestado"):
        items.append(
            {
                "category": "service",
                "source_list": "GenServicoPrestado",
                "item_id": _id(s.get("Id")),
                "description": _text(s.get("Servico")),
                "entity": _text(s.get("Entidade")),
                "nature": _text(s.get("Natureza")),
                "location": _text(s.get("Local")),
                "date_raw": _text(s.get("Data")),
            }
        )
    for o in _list(body.get("GenOutraSituacao"), "GenOutraSituacao"):
        items.append(
            {
                "category": "other_situation",
                "source_list": "GenOutraSituacao",
                "item_id": _id(o.get("Id")),
                "description": _text(o.get("OutraSituacao")),
            }
        )
    return items


def _v5(body: dict) -> tuple[int, list[tuple[dict, list[dict]]]]:
    _check_keys(body, V5_KEYS, "RegistoInteressesV5")
    fact = body.get("FactoDeclaracao") or {}
    decl = {
        "declaration_id": _id(fact.get("Id")),
        "declared_legislature": _text(body.get("Legislatura")),
        "position": _text(fact.get("CargoFuncao")),
        "position_start_raw": _text(fact.get("DataInicioFuncao")),
        "position_changed_raw": _text(fact.get("DataAlteracaoFuncao")),
        "position_end_raw": _text(fact.get("DataCessacaoFuncao")),
        "is_exclusive": (body.get("Exclusividade") or {}).get("Exclusividade"),
    }
    return _id(body.get("IdCadastroGODE")), [(decl, _v5_items(body))]


def parse_record(
    record: dict, legislature: str
) -> tuple[int | None, list[tuple[dict, list[dict]]]]:
    """(cadastro_id, [(declaration, items), ...]) for one published record."""
    _check_keys(record, set(VERSIONS), "RegistoInteresses")
    filled = [k for k in VERSIONS if record.get(k)]
    if len(filled) > 1:
        raise InterestsError(f"RegistoInteresses: more than one format in a record: {filled}")
    if not filled:
        return None, []
    version = filled[0]
    body = record[version]
    if version in ("RegistoInteressesV1", "RegistoInteressesV2"):
        return _v12(version, body)
    if version == "RegistoInteressesV3":
        return _v3(body, legislature)
    return _v5(body)


def read_file(path: Path, legislature: str, source_file: str):
    """Rows for the declarations, items and files tables from one NDJSON file."""
    declarations, items = [], []
    people = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            version = next((k for k in VERSIONS if record.get(k)), None)
            cadastro_id, parsed = parse_record(record, legislature)
            people += cadastro_id is not None
            for n, (decl, decl_items) in enumerate(parsed, 1):
                key = f"{legislature}-{cadastro_id}-{n}"
                declarations.append(
                    {
                        **decl,
                        "declaration_key": key,
                        "cadastro_id": cadastro_id,
                        "format_version": version.removeprefix("RegistoInteresses"),
                        "items": len(decl_items),
                        "legislature": legislature,
                        "source_file": source_file,
                    }
                )
                for i, item in enumerate(decl_items, 1):
                    items.append(
                        {
                            **item,
                            "declaration_key": key,
                            "item_number": i,
                            "legislature": legislature,
                            "source_file": source_file,
                        }
                    )
    file_row = {
        "legislature": legislature,
        "source_file": source_file,
        "people": people,
        "declarations": len(declarations),
    }
    return declarations, items, file_row


def read_all(data_dir: Path | str):
    data_dir = Path(data_dir)
    declarations, items, files = [], [], []
    for path in sorted((data_dir / "registo_interesses").glob("*/records*.ndjson")):
        rel = path.relative_to(data_dir).as_posix()
        d, i, f = read_file(path, path.parent.name, rel)
        declarations += d
        items += i
        files.append(f)
    return declarations, items, files


def _write_table(con, name: str, rows: list[dict], columns: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{name}.ndjson"
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps({k: row.get(k) for k in columns}, ensure_ascii=False) + "\n")
        cols = ", ".join(f"{k}: '{v}'" for k, v in columns.items())
        source = path.as_posix().replace("'", "''")
        con.execute(
            f"create or replace table {name} as select {', '.join(columns)} from read_json("
            f"'{source}', format = 'newline_delimited', columns = {{{cols}}})"
        )


def build_interest_tables(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """Writes the three stg_registo_interesses__* tables in one pass."""
    declarations, items, files = read_all(data_dir)
    _write_table(con, "stg_registo_interesses__files", files, FILE_COLUMNS)
    _write_table(con, "stg_registo_interesses__declarations", declarations, DECLARATION_COLUMNS)
    _write_table(con, "stg_registo_interesses__items", items, ITEM_COLUMNS)
