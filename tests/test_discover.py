"""Weekly discover job (#11): diff the AR open data pages against sources.yaml.

Runs on a synthetic copy of the pages in tests/fixtures/discover, never the network.
"""

import datetime as dt
import shutil
from pathlib import Path

import pytest
import yaml

from parlamento_aberto import discover, sources

FIX = Path(__file__).parent / "fixtures" / "discover"
BASE = "https://www.parlamento.pt/Cidadania/Paginas/"
INI17 = BASE + "DAIniciativas.aspx?t=fx17&Path=fxIni17"
IGNORE = discover.config(FIX / "sources.yaml")["ignore_pages"]
DOC = "https://app.parlamento.pt/webutils/docs/doc.txt?path={}&fich={}&Inline=true"


def item(href: str, text: str) -> str:
    href = href.replace("&", "&amp;")
    return f'<div class="archive-item"><a class="TextoRegular" href="{href}">{text}</a></div>'


@pytest.fixture
def site() -> dict[str, str]:
    mapping = yaml.safe_load((FIX / "site.yaml").read_text(encoding="utf-8"))
    return {url: (FIX / name).read_text(encoding="utf-8") for url, name in mapping.items()}


def add_items(page: str, *items: str) -> str:
    return page.replace(
        '<div class="archive-list">\n', '<div class="archive-list">\n' + "".join(items)
    )


def run(site, sources_path=FIX / "sources.yaml"):
    calls = []

    def get(url):
        calls.append(url)
        if url not in site:
            raise AssertionError(f"unexpected request {url}")
        return site[url]

    scan = discover.scan(get, sleep=lambda s: None, ignore_pages=IGNORE)
    return discover.diff(sources_path, scan), calls


def test_unchanged_pages_give_nothing(site):
    report, calls = run(site)
    assert report["added"] == []
    assert report["problems"] == []
    # One request per page, the ignored DAdar page is not fetched.
    assert sorted(calls) == sorted(site)


def test_new_legislature_link_is_an_addition(site):
    url = DOC.format("fxIni18json", "IniciativasXVIII_json.txt")
    folder = BASE + "DAIniciativas.aspx?t=fx18&Path=fxIni18"
    site[BASE + "DAIniciativas.aspx"] = add_items(
        site[BASE + "DAIniciativas.aspx"], item(folder, "XVIII Legislatura")
    )
    site[folder] = add_items(
        '<html><body><div class="archive-list">\n</div></body></html>',
        item(url, "IniciativasXVIII_json.txt"),
        item(DOC.format("fxIni18xml", "IniciativasXVIII.xml"), "IniciativasXVIII.xml"),
    )
    report, _ = run(site)
    assert report["problems"] == []
    assert report["added"] == [
        {"dataset": "iniciativas", "legislature": "XVIII", "part": None, "url": url}
    ]


def test_new_file_with_a_part_in_a_known_folder(site):
    url = DOC.format("fxOE2027json", "OE2027Or_json.txt")
    key = BASE + "DAOE.aspx?t=fx17&Path=fxOE17"
    site[key] = add_items(site[key], item(url, "OE2027Or_json.txt"))
    report, _ = run(site)
    assert report["problems"] == []
    assert report["added"] == [
        {"dataset": "orcamento_estado", "legislature": "XVII", "part": "2027Or", "url": url}
    ]


def test_split_legislature_files_get_parts(site):
    folder = BASE + "DAComposicaoOrgaos.aspx?t=fx1&Path=fxOrg1"
    url_a = DOC.format("fxOrg1a", "OrgaoComposicaoIA_json.txt")
    url_b = DOC.format("fxOrg1b", "OrgaoComposicaoIB_json.txt")
    site[folder] = add_items(site[folder], item(url_a, "a"), item(url_b, "b"))
    report, _ = run(site)
    assert report["problems"] == []
    assert report["added"] == [
        {"dataset": "composicao_orgaos", "legislature": "I", "part": "A", "url": url_a},
        {"dataset": "composicao_orgaos", "legislature": "I", "part": "B", "url": url_b},
    ]


def test_apply_adds_the_entry_and_is_idempotent(tmp_path):
    path = tmp_path / "sources.yaml"
    shutil.copy(FIX / "sources.yaml", path)
    before = path.read_text(encoding="utf-8")
    url = DOC.format("fxIni18json", "IniciativasXVIII_json.txt")
    report = {
        "added": [{"dataset": "iniciativas", "legislature": "XVIII", "part": None, "url": url}],
        "problems": [],
    }
    assert discover.apply(path, report) == 1
    after = path.read_text(encoding="utf-8")
    # Lines are only added, and the file still loads with the new current legislature.
    assert [line for line in before.splitlines() if line not in after.splitlines()] == []
    srcs = sources.load(path)
    assert "iniciativas/XVIII" in [s.key for s in srcs]
    assert sources.current_legislature(srcs) == "XVIII"
    assert next(s for s in srcs if s.key == "iniciativas/XVIII").url == url
    assert discover.apply(path, report) == 0
    assert path.read_text(encoding="utf-8") == after


def test_apply_keeps_a_part(tmp_path):
    path = tmp_path / "sources.yaml"
    shutil.copy(FIX / "sources.yaml", path)
    url = DOC.format("fxOE2027json", "OE2027Or_json.txt")
    added = {"dataset": "orcamento_estado", "legislature": "XVII", "part": "2027Or", "url": url}
    assert discover.apply(path, {"added": [added], "problems": []}) == 1
    assert "orcamento_estado/XVII-2027Or" in [s.key for s in sources.load(path)]


def test_removed_link_is_a_problem(site):
    site[INI17] = "\n".join(line for line in site[INI17].splitlines() if "XVII_json" not in line)
    report, _ = run(site)
    assert report["added"] == []
    assert [p["kind"] for p in report["problems"]] == ["removed"]
    assert "iniciativas/XVII" in report["problems"][0]["detail"]


def test_new_dataset_page_is_a_problem(site):
    top = BASE + "DadosAbertos.aspx"
    site[top] = site[top].replace(
        "</body>", '<p><a href="/Cidadania/Paginas/DANovo.aspx">Recursos</a></p></body>'
    )
    site[BASE + "DANovo.aspx"] = site[BASE + "DAOE.aspx"].replace("DAOE", "DANovo")
    site[BASE + "DANovo.aspx?t=fx17&Path=fxOE17"] = site[
        BASE + "DAOE.aspx?t=fx17&Path=fxOE17"
    ].replace("OE2026Or", "Novo")
    report, _ = run(site)
    assert report["added"] == []
    kinds = sorted(p["kind"] for p in report["problems"])
    assert kinds == ["new dataset"]
    assert "DANovo" in report["problems"][0]["detail"]
    assert "Novo_json.txt" in report["problems"][0]["detail"]


def test_unknown_file_in_a_known_page_is_a_new_dataset(site):
    site[INI17] = add_items(site[INI17], item(DOC.format("fxX", "PareceresXVII_json.txt"), "P"))
    report, _ = run(site)
    assert report["added"] == []
    assert [p["kind"] for p in report["problems"]] == ["new dataset"]


def test_new_link_token_for_a_listed_file_is_not_a_change(site):
    # AR renders a new path token on every page view; the file is the same.
    site[INI17] = site[INI17].replace("path=fxIni17json", "path=fxIni17other")
    report, _ = run(site)
    assert report == {"added": [], "problems": []}


def test_second_file_for_a_listed_legislature_is_a_problem(site):
    url = DOC.format("fxIni17bis", "Iniciativas_json.txt")
    site[INI17] = add_items(site[INI17], item(url, "Iniciativas_json.txt"))
    report, _ = run(site)
    assert report["added"] == []
    assert [p["kind"] for p in report["problems"]] == ["changed"]


def test_empty_subfolder_is_not_a_problem(site):
    sub = BASE + "DAIniciativas.aspx?t=fx17sub&Path=fxIni17sub"
    site[INI17] = add_items(site[INI17], item(sub, "I Legislatura"))
    site[sub] = '<html><body><div class="archive-list">\n</div></body></html>'
    report, _ = run(site)
    assert report == {"added": [], "problems": []}


def test_unreadable_section_page_is_a_layout_problem(site):
    site[BASE + "DAOE.aspx"] = (
        "<html><body><table><tr><td>novo layout</td></tr></table></body></html>"
    )
    report, _ = run(site)
    kinds = sorted(p["kind"] for p in report["problems"])
    assert "layout" in kinds
    assert report["added"] == []


def test_unreadable_top_page_is_a_layout_problem(site):
    site[BASE + "DadosAbertos.aspx"] = "<html><body><p>Em manutenção</p></body></html>"
    report, calls = run(site)
    assert calls == [BASE + "DadosAbertos.aspx"]
    assert [p["kind"] for p in report["problems"]] == ["layout"]
    # Without a readable page there is no removed-link noise.
    assert report["added"] == []


def test_unparsable_folder_name_is_a_layout_problem(site):
    page = BASE + "DAIniciativas.aspx"
    site[page] = site[page].replace(">XVI Legislatura<", ">Arquivo<")
    report, _ = run(site)
    assert "layout" in [p["kind"] for p in report["problems"]]


def test_ignored_link_is_not_reported(site):
    report, _ = run(site)
    assert not [p for p in report["problems"] if "OrgaoComposicaoII" in p["detail"]]


def test_scan_is_polite_and_retries(site):
    sleeps, attempts = [], {"n": 0}

    def get(url):
        if url.endswith("DadosAbertos.aspx") and attempts["n"] < 2:
            attempts["n"] += 1
            raise OSError("temporary")
        return site[url]

    discover.scan(get, sleep=sleeps.append, ignore_pages=IGNORE)
    assert attempts["n"] == 2
    assert all(s >= discover.DELAY for s in sleeps)
    assert len(sleeps) >= len(site)


def test_scan_gives_up_after_retries(site):
    def get(url):
        raise OSError("down")

    with pytest.raises(discover.ScanError):
        discover.scan(get, sleep=lambda s: None, ignore_pages=IGNORE)


def test_bodies():
    url = DOC.format("fxIni18json", "IniciativasXVIII_json.txt")
    report = {
        "added": [{"dataset": "iniciativas", "legislature": "XVIII", "part": None, "url": url}],
        "problems": [{"kind": "removed", "detail": "iniciativas/XVII: link gone"}],
    }
    pr = discover.pr_body(report)
    assert "iniciativas/XVIII" in pr and "hold: new-dataset" in pr
    issue = discover.issue_body(report, token=True)
    assert "iniciativas/XVII: link gone" in issue
    assert "iniciativas/XVIII" not in issue
    no_token = discover.issue_body(report, token=False)
    assert "DATA_BOT_TOKEN" in no_token and "iniciativas/XVIII" in no_token


UTC = dt.UTC


@pytest.mark.parametrize(
    "schedule, now, run_it",
    [
        (discover.SUMMER, dt.datetime(2026, 10, 19, 7, 0, tzinfo=UTC), True),
        (discover.WINTER, dt.datetime(2026, 10, 19, 8, 0, tzinfo=UTC), False),
        (discover.WINTER, dt.datetime(2026, 11, 2, 8, 0, tzinfo=UTC), True),
        (discover.SUMMER, dt.datetime(2026, 11, 2, 7, 0, tzinfo=UTC), False),
        # A late cron still runs once.
        (discover.SUMMER, dt.datetime(2026, 10, 19, 9, 40, tzinfo=UTC), True),
    ],
)
def test_plan_runs_once_at_eight_lisbon(schedule, now, run_it):
    assert discover.plan("schedule", schedule, now=now)["run"] is run_it


def test_plan_runs_on_manual_dispatch():
    now = dt.datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
    assert discover.plan("workflow_dispatch", "", now=now)["run"] is True


def test_workflow_crons_match_the_plan():
    wf = yaml.safe_load((Path(__file__).parents[1] / ".github/workflows/discover.yml").read_text())
    crons = [c["cron"] for c in wf[True]["schedule"]]
    assert sorted(crons) == sorted([discover.SUMMER, discover.WINTER])
