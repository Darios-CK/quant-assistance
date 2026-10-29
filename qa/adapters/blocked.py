"""Factors without a free source: the interface is ready, the adapter stays empty until a (paid) source is plugged in."""

from __future__ import annotations

from qa.adapters.base import BlockedAdapter


def _blocked(name: str, title: str, reason: str, keys: tuple[str, ...] = ()) -> BlockedAdapter:
    a = BlockedAdapter()
    a.name, a.title, a.blocked, a.keys = name, title, reason, keys
    return a


BLOCKED = [
    _blocked("pmi", "PMI (ISM, S&P Global)", "Historie lizenziert (ISM, S&P Global); Ersatz: Regionalumfragen der Fed"),
    _blocked("transcripts", "Earnings-Call-Transkripte", "keine freie, erlaubte Quelle gefunden"),
    _blocked("ratings", "Länderratings", "keine freie Historie der Ratingagenturen"),
    _blocked("borrow", "Leerverkaufskosten", "nur kostenpflichtig (z. B. S3, IHS Markit)", ("BORROW_FEE_API_KEY",)),
    _blocked("retail_flows", "Privatanleger-Ströme", "nur kostenpflichtig"),
    _blocked("x", "Twitter/X", "X-API kostenpflichtig", ("X_BEARER_TOKEN",)),
    _blocked("posts", "CEO-/Politiker-Posts", "X-API kostenpflichtig, andere Plattformen ohne freie Historie", ("X_BEARER_TOKEN",)),
    _blocked("app_data", "App-Downloads, Web-Traffic", "nur kostenpflichtig"),
    _blocked("consensus", "Konsensschätzungen Makro", "Konsenswerte lizenziert", ("CONSENSUS_API_KEY",)),
    _blocked("crsp", "CRSP (inkl. delisteter Firmen)", "kostenpflichtig", ("CRSP_USER",)),
    _blocked("compustat", "Compustat", "kostenpflichtig", ("COMPUSTAT_USER",)),
]
