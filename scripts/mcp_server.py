#!/usr/bin/env python3
"""Quant-Analyst as an MCP server: Claude (Claude Code, Claude Desktop) calls this project's analyses as tools.

Free with an existing Claude subscription – no API key: the model runs in the Claude app, the analyses run here.
Register once:
    claude mcp add --scope user quant -- "<quant-analyst>/.venv/bin/python" "<quant-analyst>/scripts/mcp_server.py"
Then ask, e.g. "Wie reagieren Banken auf harte EZB-Überraschungen bei hohem VIX?" – Claude calls the tools below.

Speaks the Model Context Protocol over stdin/stdout (JSON-RPC 2.0, one message per line).  Same tools and the same
instructions (think wide, measure hard, report honestly) as the in-app chat in qa/agent.py.  Read-only except for
the local data cache; nothing leaves this Mac except what Claude itself sends as part of the conversation.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qa.agent import SYSTEM, TOOLS, _run_tool  # noqa: E402  (one tool list for the chat and MCP)

OUT = sys.stdout


def _reply(msg_id, result=None, error=None) -> None:
    out = {"jsonrpc": "2.0", "id": msg_id}
    out["error" if error else "result"] = error or result
    OUT.write(json.dumps(out, ensure_ascii=False) + "\n")
    OUT.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, msg_id, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
        if msg_id is None:                                              # notifications (initialized, cancelled …)
            continue
        if method == "initialize":
            _reply(msg_id, {"protocolVersion": params.get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}},
                            "serverInfo": {"name": "quant-analyst", "version": "1.0"}, "instructions": SYSTEM})
        elif method == "tools/list":
            _reply(msg_id, {"tools": [{"name": t["name"], "description": t["description"], "inputSchema": t["input_schema"]} for t in TOOLS]})
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            if name not in {t["name"] for t in TOOLS}:
                _reply(msg_id, error={"code": -32602, "message": f"unbekanntes Werkzeug {name}"})
                continue
            with contextlib.redirect_stdout(sys.stderr):                 # library chatter must not corrupt the protocol
                text, err = _run_tool(name, args)
            _reply(msg_id, {"content": [{"type": "text", "text": text}], "isError": err})
        elif method == "ping":
            _reply(msg_id, {})
        else:
            _reply(msg_id, error={"code": -32601, "message": f"unbekannte Methode {method}"})


if __name__ == "__main__":
    main()
