"""A publicação e o aviso ao Fiscaliza (#112): o aviso sai depois de publicar, não antes."""

import re
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
RELEASE = WORKFLOWS / "data-release.yml"
DISPATCH = WORKFLOWS / "fiscaliza-dispatch.yml"


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def evaluate(expr, ctx):
    """Uma condição `if:` do GitHub com ==, !=, && e ||. Um contexto que falta vale ''."""
    expr = expr.strip().removeprefix("${{").removesuffix("}}")
    names = r"\b(?:github|inputs|vars|steps|needs)(?:\.[A-Za-z_][\w-]*)+"
    expr = re.sub(names, lambda m: repr(ctx.get(m.group(0), "")), expr)
    return eval(expr.replace("&&", " and ").replace("||", " or "))  # noqa: S307


def release_steps():
    return {s.get("name"): s for s in load(RELEASE)["jobs"]["release"]["steps"]}


def publishes(event, data_releases, ref="refs/heads/main"):
    ctx = {
        "github.event_name": event,
        "github.ref": ref,
        "vars.DATA_RELEASES": data_releases,
        "steps.data.outputs.present": "true",
    }
    return evaluate(release_steps()["Publish"]["if"], ctx)


def test_runs_on_push_to_main_or_by_hand():
    on = load(RELEASE)[True]
    assert on["push"]["branches"] == ["main"]
    assert on["workflow_dispatch"] is None


def test_publishes_only_on_main_with_data_releases_on():
    assert publishes("push", "on")
    assert publishes("workflow_dispatch", "on")
    assert not publishes("push", "")
    assert not publishes("workflow_dispatch", "")
    assert not publishes("workflow_dispatch", "on", ref="refs/heads/outro")


def test_the_publish_step_says_it_published():
    job = load(RELEASE)["jobs"]["release"]
    publish = release_steps()["Publish"]
    assert publish["id"] == "publish"
    assert publish["run"].rstrip().endswith('echo "published=true" >> "$GITHUB_OUTPUT"')
    assert job["outputs"]["published"] == "${{ steps.publish.outputs.published }}"


def test_fiscaliza_is_told_after_the_release_with_its_commit():
    job = load(RELEASE)["jobs"]["fiscaliza"]
    assert job["needs"] == "release"
    assert evaluate(job["if"], {"needs.release.outputs.published": "true"})
    assert not evaluate(job["if"], {})
    assert job["uses"] == "./.github/workflows/fiscaliza-dispatch.yml"
    assert job["with"] == {"sha": "${{ github.sha }}"}
    # Só o secret do aviso, nunca secrets: inherit.
    assert job["secrets"] == {"FISCALIZA_DISPATCH_TOKEN": "${{ secrets.FISCALIZA_DISPATCH_TOKEN }}"}
    assert job["permissions"] == {}


def test_the_dispatch_can_be_called_with_the_commit_and_the_secret():
    call = load(DISPATCH)[True]["workflow_call"]
    assert call["inputs"]["sha"]["required"] is True
    assert call["secrets"]["FISCALIZA_DISPATCH_TOKEN"]["required"] is False


def dispatches(event, data_releases, sha=""):
    (job,) = load(DISPATCH)["jobs"].values()
    ctx = {"github.event_name": event, "vars.DATA_RELEASES": data_releases, "inputs.sha": sha}
    return "if" not in job or evaluate(job["if"], ctx)


def test_a_data_push_dispatches_only_while_data_releases_is_off():
    assert dispatches("push", "")
    assert dispatches("push", "off")
    assert not dispatches("push", "on")


def test_the_release_and_a_manual_run_always_dispatch():
    # Chamado pelo data-release.yml, o evento é o do push ou o da execução à mão.
    assert dispatches("push", "on", sha="a" * 40)
    assert dispatches("workflow_dispatch", "on", sha="a" * 40)
    assert dispatches("workflow_dispatch", "on")
    assert dispatches("workflow_dispatch", "")


def test_source_row_drops_use_the_lock_at_the_previous_release_commit():
    run = release_steps()["Source row drops"]["run"]
    assert "jq -r .data_commit" in run
    assert "contents/data/_meta/sources.lock.json?ref=$commit" in run
    assert "parlamento_aberto.release source-drops" in run
    assert '--previous "$RUNNER_TEMP/previous"' in run
