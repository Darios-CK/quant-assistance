import base64
import json

import numpy as np
import pandas as pd
import pytest

from qa import commands, data, regimes, workflows, workspace
from qa.store import GitHubStore, LocalStore, clean


@pytest.fixture
def ws(tmp_path, monkeypatch):
    st = LocalStore(tmp_path / "ws")
    com = LocalStore(tmp_path / "community")
    monkeypatch.setattr(workspace, "store", lambda: st)
    monkeypatch.setattr(workspace, "community", lambda: com)
    return st, com


# ---------------------------------------------------------------- storage
def test_paths_cannot_leave_the_store(tmp_path):
    assert clean("a/./b.json") == "a/b.json"
    for bad in ("../x", "a/../../x", "", "a/b$c"):
        with pytest.raises(SystemExit):
            clean(bad)
    st = LocalStore(tmp_path)
    st.write("p/x.md", "hi")
    assert st.read("p/x.md") == "hi" and st.list("p") == ["p/x.md"]
    st.delete("p/x.md")
    assert st.read("p/x.md") is None


class FakeGitHub:
    """Minimal contents/trees API in memory."""
    def __init__(self):
        self.files, self.n = {}, 0

    def get(self, url, params=None, timeout=None):
        if "/git/trees/" in url:
            return _R({"tree": [{"path": p, "sha": s, "type": "blob"} for p, (s, _) in self.files.items()]})
        sha = url.rsplit("/", 1)[-1]
        content = next(c for s, c in self.files.values() if s == sha)
        return _R({"content": base64.b64encode(content).decode()})

    def put(self, url, json=None, timeout=None):
        path = url.split("/contents/", 1)[1]
        if path in self.files:
            assert json["sha"] == self.files[path][0]          # updates must name the current version
        self.n += 1
        self.files[path] = (f"sha{self.n}", base64.b64decode(json["content"]))
        return _R({})

    def delete(self, url, json=None, timeout=None):
        path = url.split("/contents/", 1)[1]
        assert json["sha"] == self.files[path][0]
        del self.files[path]
        return _R({})


class _R:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body

    def raise_for_status(self):
        pass


def test_github_store_roundtrip():
    gh = GitHubStore("me/repo", "token", prefix="community")
    gh.s = FakeGitHub()
    gh.write("befehle/x.md", "eins")
    gh.write("befehle/x.md", "zwei")
    assert gh.read("befehle/x.md") == "zwei" and gh.list("befehle") == ["befehle/x.md"]
    assert list(gh.s.files) == ["community/befehle/x.md"]
    gh.delete("befehle/x.md")
    assert gh.list() == []


# ---------------------------------------------------------------- projects, memory, commands, community
def test_projects_memory_and_instructions(ws):
    st, _ = ws
    workspace.create("alpha", "Test")
    with pytest.raises(SystemExit):
        workspace.create("alpha")
    with pytest.raises(SystemExit):
        workspace.create("../böse")
    workspace.write("alpha", "s.json", "{}")
    assert workspace.projects() == ["alpha"] and "s.json" in workspace.files("alpha")
    e = workspace.remember("arbeitet mit Tagesdaten", "alpha")
    workspace.remember("mag kurze Antworten")
    workspace.set_instructions("Immer Hälften zeigen.")
    ctx = workspace.context_for_ai("beta")
    assert "Hälften" in ctx and "kurze Antworten" in ctx and "Tagesdaten" not in ctx      # project memory stays in its project
    assert "Tagesdaten" in workspace.context_for_ai("alpha")
    workspace.set_setting("gedaechtnis_an", False)
    assert "kurze" not in workspace.context_for_ai() and "Hälften" in workspace.context_for_ai()
    with pytest.raises(SystemExit):
        workspace.remember("x")
    assert workspace.forget(e["id"]) and not workspace.forget(999)


def test_command_files_and_expansion(ws):
    cmd = workspace.parse_command("---\nname: wf\nbeschreibung: Test\n---\nNotiz\n/walk-forward $1 is=24\n/review $1\n")
    assert cmd["zeilen"] == ["/walk-forward $1 is=24", "/review $1"] and cmd["beschreibung"] == "Test"
    assert commands.expand(cmd["zeilen"], ["a b.json"]) == ["/walk-forward 'a b.json' is=24", "/review 'a b.json'"]
    assert commands.expand(["/x $ARGUMENTS"], ["1", "2"]) == ["/x 1 2"]
    with pytest.raises(SystemExit):
        workspace.save_command("y", "", ["kein befehl"])


def test_own_command_runs_its_lines_and_recursion_stops(ws):
    workspace.create("p")
    workspace.save_command("zwei", "", ["/schema kerzen", "/schema trades"], "p")
    out = commands.run("/zwei", commands.Ctx("p", save=False))
    assert [r.ok for r in out] == [True, True] and "kerzen" in out[0].text
    workspace.save_command("loop", "", ["/loop"])
    out = commands.run("/loop", commands.Ctx(None, save=False))
    assert not out[-1].ok and "zu tief" in out[-1].text


def test_unknown_command_and_errors_are_results(ws):
    assert not commands.run("/gibtsnicht")[0].ok
    with pytest.raises(SystemExit):
        commands.run("ohne schrägstrich")
    r = commands.run("/backtest .env", commands.Ctx(None, save=False))[0]     # repository files outside strategies/chains stay closed
    assert not r.ok and "nicht gefunden" in r.text


def test_results_are_kept_as_artifacts(ws):
    workspace.create("p")
    r = commands.run("/schema kerzen", commands.Ctx("p"))[0]
    assert r.artifact.startswith("artefakte/") and "kerzen" in workspace.read("p", r.artifact)


def test_create_command_and_compact(ws):
    workspace.create("p")
    r = commands.run("/create-command meins Prüfen :: /review $1 ; /walk-forward $1", commands.Ctx("p", save=False))[0]
    assert r.ok and workspace.own_commands("p")["meins"]["zeilen"] == ["/review $1", "/walk-forward $1"]
    assert not commands.run("/create-command backtest /x", commands.Ctx("p", save=False))[0].ok
    chat = [{"role": "user", "text": f"/schema {i}"} if i % 2 == 0 else {"role": "assistant", "text": f"# Titel {i}\n## Ergebnis: ok"}
            for i in range(10)]
    commands.run("/compact", commands.Ctx("p", chat, save=False))
    assert len(chat) == 5 and "Zusammenfassung" in chat[0]["text"] and "Ergebnis: ok" in chat[0]["text"]


def test_publish_and_import(ws):
    st, com = ws
    workspace.create("alpha")
    workspace.write("alpha", "s.json", "{}")
    workspace.save_chat("alpha", "c1", [{"role": "user", "text": "privat"}])
    workspace.write("alpha", ".ziele/aktuell.json", "{}")
    n = workspace.publish_project("alpha")
    assert not any("chats/" in p or ".ziele" in p for p in com.list())                # chats are never published
    assert n == len(com.list()) and workspace.community_projects() == ["alpha"]
    assert workspace.import_project("alpha", "kopie") == "kopie" and "s.json" in workspace.files("kopie")
    with pytest.raises(SystemExit):
        workspace.import_project("alpha", "kopie")
    workspace.save_command("wf", "x", ["/walk-forward $1"])
    workspace.publish_command("wf")
    assert "wf" in workspace.community_commands()


# ---------------------------------------------------------------- workflows
def test_overnight_split_drops_years_without_real_opens():
    idx = pd.bdate_range("2000-01-03", "2001-12-31")
    close = pd.Series(np.linspace(100, 120, len(idx)), index=idx)
    open_ = close.shift(1) * 1.001                                   # real opens: 0.1 % gap up every night
    open_[idx.year == 2000] = close[idx.year == 2000]               # first year: open = close (no real data)
    out = workflows.split_sessions(pd.DataFrame({"open": open_, "close": close}))
    assert out.index.min().year == 2001
    assert out["overnight"].iloc[5:].round(6).eq(0.001).all()
    assert np.allclose((1 + out["overnight"]) * (1 + out["handelszeit"]) - 1, out["gesamt"])


def test_before_entries_uses_only_closes_before_the_entry_day():
    idx = pd.bdate_range("2024-01-01", periods=60)
    c = pd.Series(100.0, index=idx)
    c.iloc[40:] = 110.0                                              # jump ON the entry day
    got = workflows.before_entries(c, pd.Series([idx[40]]))
    assert got["vorher_1T"].iloc[0] == 0.0 and got["danach_1T"].iloc[0] == pytest.approx(0.10)


def test_rolling_walk_forward_trades_every_day_once_and_chooses_from_the_past():
    idx = pd.bdate_range("2010-01-01", "2016-12-31")
    rng = np.random.default_rng(1)
    m = pd.DataFrame({0: rng.normal(0.001, 0.01, len(idx)), 1: rng.normal(-0.001, 0.01, len(idx))}, index=idx)
    wf, rows = workflows.rolling_walk_forward(m, 24, 6, 3)
    assert wf.index.is_unique and wf.index.min() >= idx[0] + pd.DateOffset(months=24)
    assert all(r["variante"] == 0 for r in rows[2:])                 # the variant that was good before


def test_phase_pnl_uses_the_previous_close(monkeypatch):
    idx = pd.bdate_range("2024-01-01", periods=10)
    monkeypatch.setitem(regimes.PHASES, "test", ("Test", lambda: pd.Series([False] * 5 + [True] * 5, index=idx)))
    r = pd.Series(0.01, index=idx)
    row = workflows.phase_pnl(r, r, ["test"])[0]
    assert row["tage"] == 4                                          # turned on at the 6th close: counts from the 7th day


def test_review_and_goal_parsing():
    bad = {"markt": "ES=F", "regel": "trend", "parameter": {"schnell": [1, 2, 3, 4, 5], "langsam": [10, 20, 30, 40, 50]}, "kosten_bp": 0}
    checks = dict((t.split(" ")[0], s) for s, t in workflows.review_spec(bad))
    assert checks["Kein"] == "❌" and checks["Kosten"] == "❌"
    assert any("Roll" in t for _, t in workflows.review_spec(bad))
    chain = {"glieder": [{"id": "a", "erwartung": "+", "warum": "x"}, {"id": "b", "erwartung": "?"}]}
    assert any(s == "❌" and "b" in t for s, t in workflows.review_spec(chain))
    assert workflows.parse_goal("sharpe >= 0,8") == ("sharpe", ">=", 0.8)
    assert workflows.parse_goal("cagr>5%") == ("cagr", ">", 0.05)
    with pytest.raises(SystemExit):
        workflows.parse_goal("gewinn>5")


def test_goal_tests_on_development_data_and_logs_every_try(monkeypatch, tmp_path):
    idx = pd.bdate_range("2000-01-01", "2010-12-31")
    good = pd.Series(np.r_[np.full(len(idx) - 500, 0.0005), np.full(500, -0.0005)], index=idx) + np.random.default_rng(0).normal(0, 0.005, len(idx))
    matrix = pd.DataFrame({0: good * 0 + np.random.default_rng(2).normal(0, 0.01, len(idx)), 1: good}, index=idx)
    mask = pd.Series(idx < idx[-500], index=idx)
    monkeypatch.setattr(workflows.backtest, "prepare", lambda spec: {"grid": [{"a": 1}, {"a": 2}], "matrix": matrix, "is_mask": mask})
    monkeypatch.setattr(workflows.backtest, "TRIALS", tmp_path / "t.jsonl")
    logged = []
    monkeypatch.setattr(workflows.backtest, "log_trials", lambda spec, grid: logged.extend(grid))
    state = {"datei": "x.json", "ziel": "sharpe>=1", "status": "läuft", "geprueft": [], "verlauf": [], "versuche": 0}
    state = workflows.goal_step(state, {"markt": "x", "regel": "trend"}, batch=1)
    assert state["status"] == "läuft" and state["versuche"] == 1
    state = workflows.goal_step(state, {"markt": "x", "regel": "trend"}, batch=1)
    assert state["status"] == "erreicht" and state["treffer"] == {"a": 2}
    assert state["test"]["sharpe"] < 0                               # the holdout tells the truth
    assert logged == [{"a": 1}, {"a": 2}]


# ---------------------------------------------------------------- data API
def test_data_limits_and_resolve():
    with pytest.raises(SystemExit):
        data.bars("es", "7m")
    with pytest.raises(SystemExit):
        data.bars("es", "1m", start=(pd.Timestamp.now() - pd.Timedelta(days=90)).strftime("%Y-%m-%d"))
    r = data.resolve("zn")
    assert r["symbol"] == "ZN=F" and r["art"] == "Future" and r["vergleichsindex"] == "–"
    assert data.resolve("bund10j")["einheit"] == "Basispunkte"


def test_preview_is_capped(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=2000, freq="5min")
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0.0}, index=idx)
    seen = {}
    monkeypatch.setattr(data, "bars", lambda name, interval, days=None: seen.setdefault("days", days) and df)
    assert len(data.preview_bars("es", "5m", 99)) == 500 and seen["days"] == 31


def test_mcp_tool_list_contains_data_and_workspace_tools():
    from qa.agent import TOOLS

    names = {t["name"] for t in TOOLS}
    assert {"symbole_suchen", "abdeckung", "symbol_aufloesen", "schema_erklaeren", "nutzung", "daten_anleitung", "kerzen_vorschau",
            "befehl", "projekte", "datei_lesen", "datei_schreiben", "merken", "gedaechtnis"} <= names
    assert all(json.dumps(t["input_schema"]) for t in TOOLS)
