"""Personal pages: projects (files, chats, artifacts), the Copilot and the account (memory, instructions, commands)."""

from __future__ import annotations

import streamlit as st

from qa import agent, commands, workspace
from web import ui

EXAMPLES = ["/commands", "/phasen", "/overnight es", "/review trend_dax.json", "/regime-pnl trend_dax.json",
            "/walk-forward trend_dax.json is=24 oos=6 schritt=3", "/goal momentum_sp500.json sharpe>=0.6", "/kerzen nq 1h 5"]


def _project_picker(key: str) -> str | None:
    names = workspace.projects()
    if not names:
        return None
    current = st.session_state.get("project")
    idx = names.index(current) if current in names else 0
    name = st.selectbox("Projekt", names, index=idx, key=key)
    st.session_state["project"] = name
    return name


# ---------------------------------------------------------------- projects
def projekte() -> None:
    ui.require_owner("Projekte")
    ui.header("Projekte", "Jedes Projekt ist ein eigener Ordner: Strategien, Ketten, Trades, Skripte – Ergebnisse und Chats bleiben gespeichert.")
    left, right = st.columns([1, 3])
    with left:
        name = _project_picker("p_pick")
        with st.popover("Neues Projekt", width="stretch"):
            new = st.text_input("Name", key="p_new", help="Buchstaben, Ziffern, - und _")
            desc = st.text_input("Beschreibung", key="p_desc")
            if st.button("Anlegen", type="primary", key="p_create"):
                try:
                    st.session_state["project"] = workspace.create(new, desc)
                    st.rerun()
                except SystemExit as exc:
                    st.error(str(exc))
        st.caption(f"Speicher: {workspace.store().kind}")
    if not name:
        right.info("Noch kein Projekt – links anlegen.")
        return
    with right:
        info = workspace.info(name)
        st.markdown(f"### {name}")
        if info.get("beschreibung"):
            st.caption(info["beschreibung"])
        files = workspace.files(name)
        own = [f for f in files if not f.startswith(("chats/", "artefakte/", ".ziele/", "befehle/"))]
        arts = sorted((f for f in files if f.startswith("artefakte/")), reverse=True)
        chats = workspace.chats(name)
        t = st.tabs([f"Dateien ({len(own)})", f"Artefakte ({len(arts)})", f"Chats ({len(chats)})", "Befehle", "Veröffentlichen"])
        with t[0]:
            _files_tab(name, own)
        with t[1]:
            if not arts:
                st.info("Noch keine Ergebnisse – Befehle im Copilot speichern hier automatisch.")
            else:
                pick = st.selectbox("Artefakt", arts, format_func=lambda p: p.split("/", 1)[1])
                text = workspace.read(name, pick)
                c1, c2 = st.columns(2)
                c1.download_button("Herunterladen", text, pick.split("/")[-1], "text/markdown")
                if c2.button("Löschen", key="a_del"):
                    workspace.delete(name, pick)
                    st.rerun()
                st.markdown(text)
        with t[2]:
            if not chats:
                st.info("Noch keine Chats.")
            for c in chats:
                msgs = workspace.load_chat(name, c)
                first = next((m["text"] for m in msgs if m["role"] == "user"), "")
                a, b, d = st.columns([5, 1, 1])
                a.markdown(f"**{c}** · {len(msgs)} Nachrichten · `{first[:70]}`")
                if b.button("Öffnen", key=f"co_{c}"):
                    st.session_state["chat_id"] = c
                    st.switch_page(ui.PAGES["copilot"])
                if d.button("Löschen", key=f"cd_{c}"):
                    workspace.delete(name, f"chats/{c}.json")
                    st.rerun()
        with t[3]:
            own_cmds = {k: v for k, v in workspace.own_commands(name).items() if v["ort"] == "Projekt"}
            st.caption("Befehle nur für dieses Projekt (für alle Projekte: Konto → Befehle).")
            for k, v in own_cmds.items():
                st.markdown(f"- `/{k}` – {v['beschreibung']}: `{' ; '.join(v['zeilen'])}`")
            _command_editor(name, "pc")
        with t[4]:
            st.markdown("Veröffentlicht alle Dateien außer Chats in die öffentliche Community. Andere können das Projekt dann ansehen und übernehmen.")
            st.warning("Öffentlich heißt öffentlich: keine persönlichen Daten oder eigenen Trades veröffentlichen, die privat bleiben sollen.")
            if st.checkbox("Ich habe die Dateien geprüft", key="pub_ok") and st.button("Veröffentlichen", type="primary"):
                try:
                    n = workspace.publish_project(name)
                    st.success(f"{n} Dateien veröffentlicht.")
                except Exception as exc:
                    st.error(f"Veröffentlichen fehlgeschlagen: {exc}")


def _files_tab(name: str, own: list[str]) -> None:
    c1, c2 = st.columns([2, 1])
    with c2:
        up = st.file_uploader("Datei hochladen", key=f"up_{name}", help="z. B. trades.csv, strategie.json, skript.py")
        if up is not None and st.button("Speichern", key="up_save"):
            workspace.write(name, up.name, up.getvalue())
            st.rerun()
        with st.popover("Neue Datei", width="stretch"):
            fn = st.text_input("Dateiname", "notizen.md", key="nf_name")
            if st.button("Anlegen", key="nf_go"):
                try:
                    workspace.write(name, fn, "")
                    st.session_state["file_pick"] = fn
                    st.rerun()
                except SystemExit as exc:
                    st.error(str(exc))
    with c1:
        if not own:
            st.info("Noch keine Dateien.")
            return
        cur = st.session_state.get("file_pick")
        pick = st.selectbox("Datei", own, index=own.index(cur) if cur in own else 0, key="f_pick")
        st.session_state["file_pick"] = pick
    raw = workspace.store().read_bytes(f"{name}/{pick}") or b""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        st.info("Binärdatei – nur herunterladen.")
        st.download_button("Herunterladen", raw, pick)
        return
    edited = st.text_area("Inhalt", text, height=340, key=f"edit_{name}_{pick}")
    b = st.columns(4)
    if b[0].button("Speichern", type="primary", key="f_save"):
        workspace.write(name, pick, edited)
        st.success("Gespeichert")
    runnable = pick.endswith((".json", ".py"))
    if runnable and b[1].button("Ausführen", key="f_run"):
        st.session_state["copilot_run"] = f"/ausfuehren {pick}"
        st.switch_page(ui.PAGES["copilot"])
    if pick.endswith(".json") and b[2].button("Review", key="f_rev"):
        st.session_state["copilot_run"] = f"/review {pick}"
        st.switch_page(ui.PAGES["copilot"])
    if b[3].button("Löschen", key="f_del"):
        workspace.delete(name, pick)
        st.session_state.pop("file_pick", None)
        st.rerun()


def _command_editor(project: str | None, key: str) -> None:
    with st.expander("Neuen Befehl anlegen"):
        n = st.text_input("Name (ohne /)", key=f"{key}_n")
        d = st.text_input("Beschreibung", key=f"{key}_d")
        body = st.text_area("Zeilen (je eine Befehlszeile; $1 … $9 und $ARGUMENTS für Eingaben)", "/walk-forward $1 is=24 oos=6 schritt=3\n/review $1",
                            key=f"{key}_b")
        if st.button("Speichern", key=f"{key}_s"):
            try:
                if n in commands.BUILTINS:
                    raise SystemExit(f"/{n} ist eingebaut – anderen Namen wählen")
                st.success(workspace.save_command(n, d, [ln.strip() for ln in body.splitlines() if ln.strip()], project))
            except SystemExit as exc:
                st.error(str(exc))
        up = st.file_uploader("…oder .md-Datei importieren", type=["md"], key=f"{key}_u")
        if up is not None and st.button("Importieren", key=f"{key}_i"):
            cmd = workspace.parse_command(up.getvalue().decode("utf-8"))
            try:
                st.success(workspace.save_command(cmd["name"] or up.name[:-3], cmd["beschreibung"], cmd["zeilen"], project))
            except SystemExit as exc:
                st.error(str(exc))


# ---------------------------------------------------------------- copilot
def _ai_ready() -> bool:
    ok, _ = agent.available()
    return ok


def copilot() -> None:
    ui.require_owner("Quant Copilot")
    top = st.columns([2, 2, 1.3, 1])
    with top[0]:
        project = _project_picker("cp_pick")
    if not project:
        st.info("Erst ein Projekt anlegen (Projekte).")
        return
    chats = workspace.chats(project)
    chat_id = st.session_state.get("chat_id")
    chat_id = chat_id if chat_id in chats else None                   # default: a fresh chat
    with top[1]:
        options = ["neu"] + chats
        sel = st.selectbox("Chat", options, index=options.index(chat_id) if chat_id else 0,
                           format_func=lambda c: "Neuer Chat" if c == "neu" else c)
        chat_id = None if sel == "neu" else sel
    ai = _ai_ready()
    with top[2]:
        level = st.selectbox("Stufe", list(agent.LEVELS), index=2, key="cp_level", disabled=not ai,
                             help="Wie gründlich die KI nachdenkt (nur mit API-Schlüssel). Befehle sind immer gleich gründlich.")
    with top[3]:
        st.write("")
        if st.button("Neuer Chat", width="stretch"):
            st.session_state["chat_id"] = None
            st.session_state.pop("ai_history", None)
            st.rerun()
    st.session_state["chat_id"] = chat_id
    messages = workspace.load_chat(project, chat_id) if chat_id else []
    cache = st.session_state.setdefault("results", {})

    if not messages:
        st.markdown('<div class="qa-hero" style="padding:18px 0 6px"><h1 style="font-size:2.2rem"><span>Quant Copilot</span></h1>'
                    '<p>Befehle mit <code>/</code> laufen sofort und kostenlos. Freie Fragen beantwortet Claude – gratis über Claude Code '
                    'bzw. die Claude-App (Daten → Python & MCP)' + (', hier mit dem hinterlegten API-Schlüssel' if ai else '') + '.</p></div>',
                    unsafe_allow_html=True)
        cols = st.columns(4)
        for i, ex in enumerate(EXAMPLES):
            if cols[i % 4].button(ex, key=f"ex_{i}", width="stretch"):
                st.session_state["copilot_run"] = ex
                st.rerun()
    for i, m in enumerate(messages):
        with st.chat_message(m["role"], avatar=":material/person:" if m["role"] == "user" else ":material/bolt:"):
            if m["role"] == "user":
                st.markdown(f"`{m['text']}`" if m["text"].startswith("/") else m["text"])
            elif (chat_id, i) in cache:
                ui.show_result(cache[(chat_id, i)], f"{chat_id}_{i}")
            else:
                st.markdown(m["text"])
                if m.get("artifact"):
                    st.caption(f"Gespeichert: {m['artifact']}")

    with st.popover("Befehle", width="content"):
        st.markdown(commands.c_commands([], commands.Ctx(project)).text)
    line = st.chat_input("Befehl mit / oder Frage …") or st.session_state.pop("copilot_run", None)
    if not line:
        return
    if not chat_id:
        chat_id = workspace.new_chat_id()
        st.session_state["chat_id"] = chat_id
    messages.append({"role": "user", "text": line})
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(f"`{line}`" if line.startswith("/") else line)
    with st.chat_message("assistant", avatar=":material/bolt:"):
        if line.strip().startswith("/"):
            with st.spinner("Rechne … (beim ersten Mal werden Daten geladen)"):
                ctx = commands.Ctx(project, messages)
                results = commands.run(line, ctx)
            messages = ctx.chat
            if line.strip().startswith("/compact"):                     # positions changed: drop shown results of this chat
                for k in [k for k in cache if k[0] == chat_id]:
                    del cache[k]
            for r in results:
                ui.show_result(r, f"new_{len(messages)}")
                cache[(chat_id, len(messages))] = r
                messages.append({"role": "assistant", "text": r.text, "artifact": r.artifact, "title": r.title})
        elif ai:
            status = st.status("Denke nach und rechne …", expanded=True)
            hist = st.session_state.setdefault("ai_history", {}).setdefault(chat_id, [])

            def on_step(name, i, out, err):
                status.write(f"{'⚠️' if err else '🔧'} {name}: {str(i.get('zeile') or i.get('quelle') or i.get('ticker') or '')[:80]}")

            try:
                text, hist[:], usage = agent.ask(line, hist, on_step, effort=agent.LEVELS[level],
                                                 context=workspace.context_for_ai(project))
                text += f"\n\n_{usage['steps']} Werkzeug-Aufrufe · ca. {usage['cost_usd']:.2f} $_"
            except Exception as exc:
                text = f"Fehler beim KI-Aufruf: {exc}"
            status.update(label="Fertig", state="complete", expanded=False)
            st.markdown(text)
            messages.append({"role": "assistant", "text": text})
        else:
            text = ("Freie Fragen beantwortet Claude. **Kostenlos:** in Claude Code oder der Claude-App fragen – dort sind alle "
                    "Werkzeuge dieses Projekts verbunden (Daten → Python & MCP). Hier direkt nutzbar sind Befehle, z. B. "
                    "`/overnight es`, `/review trend_dax.json`, `/commands` für alle.")
            st.info(text)
            messages.append({"role": "assistant", "text": text})
    workspace.save_chat(project, chat_id, messages)


# ---------------------------------------------------------------- account
def konto() -> None:
    ui.require_owner("Konto")
    ui.header("Konto", "Gedächtnis, eigene Anweisungen, eigene Befehle und die Verbindung zu Claude.")
    t = st.tabs(["Gedächtnis", "Anweisungen", "Befehle", "Verbindung"])
    with t[0]:
        on = workspace.settings()["gedaechtnis_an"]
        new_on = st.toggle("Gedächtnis an", on, help="Aus: der Copilot liest und schreibt nichts mehr ins Gedächtnis.")
        if new_on != on:
            workspace.set_setting("gedaechtnis_an", new_on)
            st.rerun()
        st.caption("Was der Copilot sich zwischen Chats merkt: wer du bist, wie du arbeitest, Entscheidungen je Projekt. "
                   "Alles hier einsehbar, korrigierbar und löschbar.")
        for m in workspace.memory():
            a, b, c = st.columns([6, 1, 1])
            txt = a.text_input(f"[{m['id']}] {m['projekt'] or 'alle Projekte'} · {m['zeit'][:10]}", m["text"], key=f"mem_{m['id']}")
            if b.button("Ändern", key=f"me_{m['id']}"):
                workspace.edit_memory(m["id"], txt)
                st.rerun()
            if c.button("Löschen", key=f"md_{m['id']}"):
                workspace.forget(m["id"])
                st.rerun()
        with st.form("mem_add", clear_on_submit=True):
            txt = st.text_input("Neuer Eintrag", placeholder="z. B. Ich handle DAX-Futures, Haltedauer Tage bis Wochen")
            if st.form_submit_button("Merken") and txt:
                try:
                    workspace.remember(txt)
                    st.rerun()
                except SystemExit as exc:
                    st.error(str(exc))
    with t[1]:
        st.caption("Wird bei jedem Chat mitgeschickt. Der Copilot befolgt sie und ändert sie nie.")
        text = st.text_area("Eigene Anweisungen", workspace.instructions(), height=220,
                            placeholder="z. B. Antworte knapp. Zeig immer die Hälften-Prüfung. Kosten mindestens 5 Bp.")
        if st.button("Speichern", type="primary", key="instr_save"):
            workspace.set_instructions(text)
            st.success("Gespeichert")
    with t[2]:
        own = {k: v for k, v in workspace.own_commands().items() if v["ort"] == "alle Projekte"}
        for k, v in own.items():
            with st.container(border=True):
                st.markdown(f"**/{k}** – {v['beschreibung']}")
                st.code("\n".join(v["zeilen"]), language=None)
                a, b, c = st.columns(3)
                a.download_button("Als .md", v["text"], f"{k}.md", key=f"dl_{k}")
                if b.button("Veröffentlichen", key=f"pub_{k}"):
                    try:
                        workspace.publish_command(k)
                        st.success("Veröffentlicht")
                    except Exception as exc:
                        st.error(str(exc))
                if c.button("Löschen", key=f"del_{k}"):
                    workspace.store().delete(f"{workspace.ACCOUNT}/befehle/{k}.md")
                    st.rerun()
        _command_editor(None, "gc")
    with t[3]:
        st.markdown(f"**Speicher:** {workspace.store().kind}" + (" (privates GitHub-Repository)" if workspace.store().kind == "github" else ""))
        st.markdown("""**Dauerhafter Speicher für die Website (kostenlos):**
1. Auf GitHub ein **privates** Repository anlegen, z. B. `quant-assistance-daten`.
2. GitHub → Settings → Developer settings → Fine-grained tokens → Token nur für dieses Repository (und optional
   `quant-assistance` für die Community) mit *Contents: Read and write*.
3. In Streamlit → App settings → Secrets eintragen:
```toml
APP_PASSWORD = "dein-passwort"
GITHUB_TOKEN = "github_pat_…"
WORKSPACE_REPO = "Darios-CK/quant-assistance-daten"
COMMUNITY_REPO = "Darios-CK/quant-assistance"
```
Lokal dieselben Zeilen (ohne APP_PASSWORD) in `~/quant-analyst/.env`, dann sehen Website und Mac dieselben Projekte.""")
        st.markdown("**Claude verbinden (kostenlos im Claude-Abo):**")
        st.code('claude mcp add --scope user quant -- ~/quant-analyst/.venv/bin/python ~/quant-analyst/scripts/mcp_server.py', language="bash")
        if commands.is_cloud() and st.button("Abmelden"):
            st.session_state["owner"] = False
            st.rerun()
