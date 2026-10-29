"""Projects, chats, artifacts, own commands, memory and instructions – one virtual file system.

Layout inside the workspace store:
    <projekt>/projekt.json              name, description, created
    <projekt>/…                         any files: strategies, chains (.json), notes (.md), trades (.csv), scripts (.py)
    <projekt>/chats/<id>.json           Copilot conversations
    <projekt>/artefakte/<zeit>_<x>.md   every result of a command, kept
    <projekt>/befehle/<name>.md         commands of this project
    _konto/befehle/<name>.md            own commands for all projects
    _konto/gedaechtnis.json             what the Copilot remembers (visible, editable, deletable, can be switched off)
    _konto/anweisungen.md               own instructions, sent with every chat, never changed by the Copilot
The community store holds published projects (projekte/<name>/…) and commands (befehle/<name>.md).

Where it lives: WORKSPACE_REPO + GITHUB_TOKEN set → a (private) GitHub repository, shared by website and Mac;
otherwise the folder workspace/ next to the code (git-ignored – projects and memory are personal).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from qa.cache import ROOT
from qa.store import GitHubStore, LocalStore, clean

ACCOUNT = "_konto"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
PRIVATE_DIRS = ("chats/", ".ziele/")              # never published


@lru_cache(maxsize=1)
def store():
    load_dotenv(ROOT / ".env")
    repo, token = os.getenv("WORKSPACE_REPO", ""), os.getenv("GITHUB_TOKEN", "")
    if repo and token:
        return GitHubStore(repo, token)
    return LocalStore(Path(os.getenv("QA_WORKSPACE", ROOT / "workspace")))


@lru_cache(maxsize=1)
def community():
    load_dotenv(ROOT / ".env")
    repo, token = os.getenv("COMMUNITY_REPO", ""), os.getenv("GITHUB_TOKEN", "")
    if repo and token:
        return GitHubStore(repo, token, prefix="community")
    return LocalStore(ROOT / "community")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def check_name(name: str) -> str:
    name = str(name).strip()
    if not NAME.match(name):
        raise SystemExit(f"Ungültiger Name '{name}': 1–40 Zeichen, Buchstaben, Ziffern, - und _")
    return name


# ---------------------------------------------------------------- projects and files
def projects(st=None) -> list[str]:
    st = st or store()
    return sorted({p.split("/")[0] for p in st.list() if p.endswith("/projekt.json") and p.count("/") == 1})


def create(name: str, description: str = "", st=None) -> str:
    st, name = st or store(), check_name(name)
    if name == ACCOUNT or st.exists(f"{name}/projekt.json"):
        raise SystemExit(f"Projekt '{name}' gibt es schon")
    st.write(f"{name}/projekt.json", json.dumps({"name": name, "beschreibung": description, "erstellt": _now()}, ensure_ascii=False, indent=1),
             f"new project {name}")
    st.write(f"{name}/README.md", f"# {name}\n\n{description}\n", f"new project {name}")
    return name


def info(name: str, st=None) -> dict:
    raw = (st or store()).read(f"{check_name(name)}/projekt.json")
    if raw is None:
        raise SystemExit(f"Projekt '{name}' gibt es nicht")
    return json.loads(raw)


def files(name: str, st=None) -> list[str]:
    st = st or store()
    cut = len(check_name(name)) + 1
    return [p[cut:] for p in st.list(name)]


def read(name: str, path: str, st=None) -> str:
    text = (st or store()).read(f"{check_name(name)}/{clean(path)}")
    if text is None:
        raise SystemExit(f"Datei '{path}' gibt es in Projekt '{name}' nicht")
    return text


def write(name: str, path: str, data: str | bytes, st=None) -> None:
    (st or store()).write(f"{check_name(name)}/{clean(path)}", data, f"{name}: {path}")


def delete(name: str, path: str, st=None) -> None:
    (st or store()).delete(f"{check_name(name)}/{clean(path)}", f"{name}: delete {path}")


def save_artifact(name: str, command: str, text: str, st=None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", command.lower()).strip("-")[:40] or "ergebnis"
    path = f"artefakte/{datetime.now():%Y%m%d-%H%M%S}_{slug}.md"
    write(name, path, text, st)
    return path


# ---------------------------------------------------------------- chats
def chats(name: str, st=None) -> list[str]:
    return sorted((p[len("chats/"):-5] for p in files(name, st) if p.startswith("chats/") and p.endswith(".json")), reverse=True)


def load_chat(name: str, chat: str, st=None) -> list[dict]:
    raw = (st or store()).read(f"{check_name(name)}/chats/{clean(chat)}.json")
    return json.loads(raw) if raw else []


def save_chat(name: str, chat: str, messages: list[dict], st=None) -> None:
    write(name, f"chats/{chat}.json", json.dumps(messages, ensure_ascii=False, indent=1), st)


def new_chat_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------- own commands (.md with a small header)
def parse_command(text: str) -> dict:
    """'---\\nname: x\\nbeschreibung: y\\n---\\n/befehl …' -> {name, beschreibung, zeilen, text}."""
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if v:
                meta[k.strip().lower()] = v.strip()
        body = m.group(2)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip().startswith("/")]
    return {"name": meta.get("name", ""), "beschreibung": meta.get("beschreibung", meta.get("description", "")),
            "zeilen": lines, "text": text}


def command_text(name: str, description: str, lines: list[str]) -> str:
    return f"---\nname: {name}\nbeschreibung: {description}\n---\n" + "\n".join(lines) + "\n"


def own_commands(project: str | None = None, st=None) -> dict[str, dict]:
    """Global commands, overridden by the project's own."""
    st = st or store()
    out = {}
    for folder in [f"{ACCOUNT}/befehle"] + ([f"{project}/befehle"] if project else []):
        for p in st.list(folder):
            if p.endswith(".md"):
                cmd = parse_command(st.read(p) or "")
                cmd["name"] = cmd["name"] or p.rsplit("/", 1)[-1][:-3]
                cmd["ort"] = "Projekt" if not folder.startswith(ACCOUNT) else "alle Projekte"
                out[cmd["name"]] = cmd
    return out


def save_command(name: str, description: str, lines: list[str], project: str | None = None, st=None) -> str:
    name = check_name(name)
    if not lines or not all(ln.startswith("/") for ln in lines):
        raise SystemExit("Ein Befehl besteht aus Zeilen, die mit / beginnen, z. B. /walk-forward $1 is=24 oos=6 schritt=3")
    path = f"{project}/befehle/{name}.md" if project else f"{ACCOUNT}/befehle/{name}.md"
    (st or store()).write(path, command_text(name, description, lines), f"command {name}")
    return path


# ---------------------------------------------------------------- memory and instructions
def settings(st=None) -> dict:
    raw = (st or store()).read(f"{ACCOUNT}/einstellungen.json")
    return {"gedaechtnis_an": True} | (json.loads(raw) if raw else {})


def set_setting(key: str, value, st=None) -> None:
    s = settings(st) | {key: value}
    (st or store()).write(f"{ACCOUNT}/einstellungen.json", json.dumps(s, indent=1), "settings")


def memory(st=None) -> list[dict]:
    raw = (st or store()).read(f"{ACCOUNT}/gedaechtnis.json")
    return json.loads(raw) if raw else []


def _save_memory(items: list[dict], st=None) -> None:
    (st or store()).write(f"{ACCOUNT}/gedaechtnis.json", json.dumps(items, ensure_ascii=False, indent=1), "memory")


def remember(text: str, project: str | None = None, st=None) -> dict:
    text = " ".join(str(text).split())
    if not text:
        raise SystemExit("Nichts zum Merken angegeben")
    if not settings(st)["gedaechtnis_an"]:
        raise SystemExit("Das Gedächtnis ist ausgeschaltet (Konto → Gedächtnis)")
    items = memory(st)
    entry = {"id": max([m["id"] for m in items], default=0) + 1, "text": text[:500], "projekt": project or "", "zeit": _now()}
    _save_memory(items + [entry], st)
    return entry


def forget(entry_id: int, st=None) -> bool:
    items = memory(st)
    kept = [m for m in items if m["id"] != int(entry_id)]
    _save_memory(kept, st)
    return len(kept) < len(items)


def edit_memory(entry_id: int, text: str, st=None) -> None:
    _save_memory([m | {"text": text} if m["id"] == int(entry_id) else m for m in memory(st)], st)


def instructions(st=None) -> str:
    return (st or store()).read(f"{ACCOUNT}/anweisungen.md") or ""


def set_instructions(text: str, st=None) -> None:
    (st or store()).write(f"{ACCOUNT}/anweisungen.md", text, "instructions")


def context_for_ai(project: str | None = None, st=None) -> str:
    """Instructions and memory as a text block for the model (empty when there is nothing)."""
    parts = []
    instr = instructions(st).strip()
    if instr:
        parts.append("## Anweisungen des Nutzers (immer befolgen, nie ändern)\n" + instr)
    if settings(st)["gedaechtnis_an"]:
        items = [m for m in memory(st) if not m["projekt"] or m["projekt"] == project]
        if items:
            parts.append("## Gedächtnis (vom Nutzer einsehbar und löschbar)\n" + "\n".join(
                f"- [{m['id']}] {m['text']}" + (f" (Projekt {m['projekt']})" if m["projekt"] else "") for m in items))
    if project:
        parts.append(f"## Aktuelles Projekt: {project}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- community
def publish_project(name: str, st=None, com=None) -> int:
    st, com = st or store(), com or community()
    n = 0
    for f in files(name, st):
        if f.startswith(PRIVATE_DIRS):
            continue
        com.write(f"projekte/{name}/{f}", st.read_bytes(f"{name}/{f}"), f"publish {name}")
        n += 1
    return n


def publish_command(name: str, project: str | None = None, st=None, com=None) -> None:
    cmd = own_commands(project, st).get(name)
    if not cmd:
        raise SystemExit(f"Befehl '{name}' gibt es nicht")
    (com or community()).write(f"befehle/{name}.md", cmd["text"], f"publish command {name}")


def community_projects(com=None) -> list[str]:
    com = com or community()
    return sorted({p.split("/")[1] for p in com.list("projekte") if p.count("/") >= 2})


def community_commands(com=None) -> dict[str, dict]:
    com = com or community()
    out = {}
    for p in com.list("befehle"):
        if p.endswith(".md"):
            cmd = parse_command(com.read(p) or "")
            out[cmd["name"] or p.rsplit("/", 1)[-1][:-3]] = cmd
    return out


def import_project(source: str, target: str | None = None, st=None, com=None) -> str:
    st, com = st or store(), com or community()
    target = check_name(target or source)
    if st.exists(f"{target}/projekt.json"):
        raise SystemExit(f"Projekt '{target}' gibt es schon – anderen Namen wählen")
    base = f"projekte/{check_name(source)}/"
    paths = [p for p in com.list(f"projekte/{source}")]
    if not paths:
        raise SystemExit(f"Veröffentlichtes Projekt '{source}' gibt es nicht")
    for p in paths:
        st.write(f"{target}/{p[len(base):]}", com.read_bytes(p), f"import {source}")
    if not st.exists(f"{target}/projekt.json"):
        st.write(f"{target}/projekt.json", json.dumps({"name": target, "beschreibung": f"importiert aus {source}", "erstellt": _now()}), "import")
    return target


def import_command(name: str, project: str | None = None, st=None, com=None) -> str:
    cmd = community_commands(com).get(name)
    if not cmd:
        raise SystemExit(f"Veröffentlichten Befehl '{name}' gibt es nicht")
    path = f"{project}/befehle/{check_name(name)}.md" if project else f"{ACCOUNT}/befehle/{check_name(name)}.md"
    (st or store()).write(path, cmd["text"], f"import command {name}")
    return path


# ---------------------------------------------------------------- first start
def seed(st=None) -> None:
    """A first project with the bundled strategies and chains, plus an example command."""
    st = st or store()
    if projects(st):
        return
    create("start", "Beispiele: Strategien, Ketten und eine Vorlage für eigene Trades.", st)
    for folder in ("strategies", "chains"):
        for f in sorted((ROOT / folder).glob("*.json")):
            write("start", f.name, f.read_text(encoding="utf-8"), st)
    write("start", "trades_vorlage.csv", "datum,symbol,richtung\n", st)
    if not own_commands(None, st):
        save_command("wf-quartal", "Walk-Forward: 2 Jahre Entwicklung, 6 Monate Test, quartalsweise gerollt",
                     ["/walk-forward $1 is=24 oos=6 schritt=3"], None, st)
