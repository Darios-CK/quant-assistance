# FEATURES – Stand jedes Faktors

Stand: 29.10.2026 · Etappe 1 (Datenschicht) läuft – erster Schwung: Adapter-Schnittstelle, FRED ohne Schlüssel, Cboe, leere Adapter für blockierte Quellen.

**Status:** offen · in Arbeit · fertig · blockiert
**„fertig“ nur, wenn alle vier Punkte erfüllt sind:** (1) Daten werden geladen, (2) daraus entsteht ein Event oder Feature,
(3) der Faktor ist in Ereignisstudie und Kettenreaktions-Analyse nutzbar, (4) ein Test läuft mit echten Daten durch
(`pytest -m live`, lokal und sonntags in GitHub Actions). Was (1)–(3) erfüllt, aber noch keinen Live-Test hat, steht auf „in Arbeit“.

**blockiert** = keine kostenlose Quelle (oder nur mit Nutzungsbedingungen, die das Auslesen verbieten). Für jeden
blockierten Faktor wird trotzdem eine Schnittstelle mit leerem Adapter gebaut (Etappe 1), damit später eine bezahlte
Quelle eingesteckt werden kann. 🔑 = kostenlos, aber Schlüssel/Registrierung nötig (siehe `.env.example`).

## Architektur (Entscheidung mit Begründung)

Der Vorschlag wird übernommen, aber **innerhalb des bestehenden Pakets `qa/`** statt als Ordner auf oberster Ebene:
- `qa/adapters/` statt `data/`: `data/` ist schon der Cache-Ordner (Parquet, nicht in Git); Website, MCP-Server, Befehle und
  tägliche Routine importieren alle `qa.*` – ein zweites Paket würde alles doppelt verdrahten.
- `qa/events/` (einheitlicher Event-Speicher: Parquet + DuckDB), `qa/features/`, `qa/graph/` (networkx),
  `qa/analysis/`, `qa/chain/` (heutiges `qa/chain.py` zieht dorthin), `qa/backtest/` (heutiges `qa/backtest.py`),
  `qa/reports/`, Oberfläche bleibt `app.py` + `web/`, Tests in `tests/` (Unit) und `tests/live/` (echte Daten).
- Backtests: **eigene Engine** (besteht schon, mit Kosten, Holdout, Walk-Forward, Deflated Sharpe, PBO) statt vectorbt –
  vectorbt bringt viele Abhängigkeiten (numba) und rechnet auf Streamlit Cloud schlecht; quantstats nur zum Gegenprüfen.
- Zeitplaner: GitHub Actions (läuft schon täglich, kostenlos, ohne eigenen Rechner).

## 6.1 Geldpolitik und Zentralbanken

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.1.1 | Zinsentscheidung Fed | in Arbeit | SF Fed (Bauer/Swanson-Überraschungen), FRED | qa/sources/shocks.py | tests/live/test_shocks.py (fehlt) | Überraschungen nur bis 2023; danach aus 2J-Rendite um den Termin schätzen |
| 6.1.2 | Zinsentscheidung EZB | in Arbeit | EA-MPD (EZB), EZB Data Portal | qa/sources/shocks.py | tests/live/test_shocks.py (fehlt) | Zins- und Ausblick-Überraschung, Info-Schocks getrennt |
| 6.1.3 | Zinsentscheidungen BoE, BoJ, SNB, PBoC und weitere | offen | BIS Policy Rates (täglich, frei), FRED | qa/adapters/bis.py | tests/live/test_bis.py | Event = Leitzinsänderung; Überraschung aus 2J-Rendite des Landes, wo frei verfügbar |
| 6.1.4 | Notenbank-Statements, Tonfall hawkish/dovish | offen | federalreserve.gov, ecb.europa.eu (Text) | qa/adapters/cb_text.py, qa/features/tone.py | tests/live/test_cb_text.py | Tonfall per Wörterbuch (offen nachvollziehbar), FinBERT optional lokal |
| 6.1.5 | FOMC-Protokolle (Minutes) | offen | federalreserve.gov | qa/adapters/cb_text.py | tests/live/test_cb_text.py | Veröffentlichung 3 Wochen nach Sitzung, Zeitpunkt 14:00 ET |
| 6.1.6 | Dot Plot / Zinsprojektionen | offen | FRED (FEDTARMD u. a., Median-Projektion seit 2015), federalreserve.gov | qa/adapters/fred.py | tests/live/test_fred.py | Überraschung = Änderung des Medians gegenüber letzter Projektion |
| 6.1.7 | Reden von Notenbankern | offen | BIS Central Bankers' Speeches | qa/adapters/bis.py | tests/live/test_bis.py | Termine + Tonfall |
| 6.1.8 | Fed Beige Book | offen | federalreserve.gov | qa/adapters/cb_text.py | tests/live/test_cb_text.py | Tonfall-Veränderung als Stärke |
| 6.1.9 | Erwartete Zinspfade aus dem Markt | offen | Yahoo ZQ=F (Fed-Funds-Future, vorderster), FRED-Zinskurve | qa/features/rate_path.py | tests/live/test_rate_path.py | Historische Kontraktmonate nicht frei → Näherung über 3M/2J-Renditen, gekennzeichnet |
| 6.1.10 | Zentralbank-Bilanzsummen (QE/QT) | in Arbeit | FRED WALCL (ohne Schlüssel, fertig), EZB Data Portal (offen) | qa/adapters/fred.py | tests/live/test_series_factors.py | Fed fertig (`fed_bilanz_h41`); EZB-Bilanz fehlt |
| 6.1.11 | Geldmengenwachstum M1, M2 | in Arbeit | FRED (M1SL, M2SL), EZB (M3) | qa/sources/fred.py | tests/live/test_fred.py | M2 ✅ (ALFRED 🔑), M1 und Euro-M3 fehlen |
| 6.1.12 | Liquidität: Reverse Repo, TGA, Bankreserven | fertig | FRED RRPONTSYD, WTREGEN, WRESBAL | qa/adapters/fred.py | tests/live/test_series_factors.py | Ereigniszeit = Veröffentlichung (H.4.1: Donnerstag 16:30 ET); Netto-Liquidität folgt mit den Features (Etappe 3) |
| 6.1.13 | Geldmarktzinsen SOFR, €STR | in Arbeit | FRED SOFR (fertig), EZB Data Portal (€STR offen) | qa/adapters/fred.py | tests/live/test_series_factors.py | SOFR veröffentlicht am nächsten Werktag 8:00 ET |
| 6.1.14 | Devisenmarkt-Interventionen | offen | Japanisches Finanzministerium (Interventionsdaten, frei), SNB-Mitteilungen | qa/adapters/mof_japan.py | tests/live/test_mof_japan.py | andere Länder nur aus Nachrichten (GDELT), gekennzeichnet |

## 6.2 Makrodaten

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.2.1 | Inflation CPI | in Arbeit | ALFRED 🔑 (Erstveröffentlichung), BLS-API | qa/sources/fred.py | tests/live/test_fred.py | Konsens nicht frei → Überraschung gegen Trend, gekennzeichnet |
| 6.2.2 | Inflation PCE | in Arbeit | ALFRED 🔑, BEA-API 🔑 | qa/sources/fred.py | tests/live/test_fred.py | |
| 6.2.3 | Erzeugerpreise PPI | in Arbeit | ALFRED 🔑, BLS-API | qa/sources/fred.py | tests/live/test_fred.py | täglicher Bericht scheitert, bis FRED-Schlüssel gesetzt ist |
| 6.2.4 | Inflationserwartungen (Breakeven, Umfragen) | in Arbeit | FRED T5YIE, T10YIE, T5YIFR (ohne Schlüssel); Umfrage MICH (ALFRED 🔑) | qa/adapters/fred.py | tests/live/test_series_factors.py | Breakeven fertig (`breakeven5j`, `breakeven10j`, `inflation5j5j`); Umfrage fehlt (FRED-Schlüssel) |
| 6.2.5 | Realzinsen (TIPS) | fertig | FRED DFII5, DFII10 | qa/adapters/fred.py | tests/live/test_series_factors.py | `realzins5j`, `realzins10j` |
| 6.2.6 | Arbeitsmarkt (NFP, Arbeitslosenquote, Löhne) | in Arbeit | ALFRED 🔑, BLS | qa/sources/fred.py | tests/live/test_fred.py | Löhne (CES0500000003) fehlen noch |
| 6.2.7 | Erstanträge Arbeitslosenhilfe | in Arbeit | ALFRED 🔑 (ICSA) | qa/sources/fred.py | tests/live/test_fred.py | |
| 6.2.8 | JOLTS (offene Stellen) | offen | ALFRED 🔑 (JTSJOL), BLS | qa/adapters/fred.py | tests/live/test_fred.py | |
| 6.2.9 | BIP-Wachstum | in Arbeit | ALFRED 🔑, BEA 🔑, Eurostat | qa/sources/fred.py | tests/live/test_fred.py | USA ✅; Euroraum (Eurostat) fehlt |
| 6.2.10 | Echtzeit-BIP (GDPNow) | offen | Atlanta Fed (Excel, frei) | qa/adapters/atlanta_fed.py | tests/live/test_atlanta_fed.py | |
| 6.2.11 | PMI (ISM, S&P Global) | blockiert | – | qa/adapters/blocked.py | tests/test_adapters.py | Historie lizenziert (ISM, S&P Global); frei nur Regionalumfragen der Fed (Philly, Empire, Richmond, Dallas) → werden als Ersatz eingebaut |
| 6.2.12 | Industrieproduktion, Kapazitätsauslastung | in Arbeit | ALFRED 🔑 (INDPRO, TCU) | qa/sources/fred.py | tests/live/test_fred.py | TCU fehlt |
| 6.2.13 | Auftragseingänge langlebiger Güter | offen | ALFRED 🔑 (DGORDER), Census | qa/adapters/fred.py | tests/live/test_fred.py | |
| 6.2.14 | Einzelhandelsumsätze | in Arbeit | ALFRED 🔑 (RSAFS) | qa/sources/fred.py | tests/live/test_fred.py | |
| 6.2.15 | Verbrauchervertrauen | in Arbeit | ALFRED 🔑 (UMCSENT) | qa/sources/fred.py | tests/live/test_fred.py | Uni Michigan ✅; Conference Board blockiert (lizenziert) |
| 6.2.16 | Immobilienmarkt (Baubeginne, Genehmigungen, Verkäufe, Preise) | in Arbeit | ALFRED 🔑 (HOUST, PERMIT, HSN1F), FRED CSUSHPINSA | qa/sources/fred.py | tests/live/test_fred.py | Baubeginne ✅, Rest fehlt; Bestandsverkäufe (NAR) auf FRED nur kurze Historie |
| 6.2.17 | Konsumentenkredite | offen | ALFRED 🔑 (TOTALSL) | qa/adapters/fred.py | tests/live/test_fred.py | |
| 6.2.18 | Handelsbilanz | in Arbeit | ALFRED 🔑 (BOPGSTB) | qa/sources/fred.py | tests/live/test_fred.py | |
| 6.2.19 | Leistungsbilanz, Kapitalflüsse (TIC) | offen | US Treasury TIC (frei) | qa/adapters/treasury.py | tests/live/test_treasury.py | |
| 6.2.20 | Staatshaushalt, Staatsverschuldung | offen | Fiscal Data API (frei) | qa/adapters/treasury.py | tests/live/test_treasury.py | |
| 6.2.21 | Staatsanleihe-Auktionen (Bid-to-Cover) | offen | TreasuryDirect API (frei) | qa/adapters/treasury.py | tests/live/test_treasury.py | Überraschung = Bid-to-Cover gegen Schnitt der letzten Auktionen gleicher Laufzeit |
| 6.2.22 | Makrodaten Europa (Eurostat, EZB, Bundesbank, ifo, ZEW) | offen | Eurostat-API, EZB, Bundesbank (frei); ifo-Zeitreihen (frei); ZEW nur Schlagzeile | qa/adapters/eurostat.py, qa/adapters/ifo.py | tests/live/test_eurostat.py | ZEW-Historie prüfen, sonst blockiert |
| 6.2.23 | Makrodaten China und Schwellenländer | offen | IMF, Weltbank, OECD (frei) | qa/adapters/imf.py, qa/adapters/worldbank.py, qa/adapters/oecd.py | tests/live/test_intl.py | meist monatlich/quartalsweise, Veröffentlichungsdatum oft nicht gespeichert → nur verzögert nutzen |
| 6.2.24 | Wirtschaftskalender mit Konsens und Überraschung | in Arbeit | Konsens: blockiert (lizenziert); Überraschung gegen Trend aus ALFRED | qa/sources/fred.py, qa/events/calendar.py | tests/live/test_fred.py | Überraschung gegen Trend ist klar als Schätzung gekennzeichnet; Konsens-Adapter leer vorbereiten |
| 6.2.25 | Frühindikatoren (OECD CLI, Conference Board LEI) | offen | OECD CLI (frei); LEI blockiert (lizenziert) | qa/adapters/oecd.py | tests/live/test_intl.py | |
| 6.2.26 | Rezessionswahrscheinlichkeit | offen | FRED RECPROUSM156N; eigene Rechnung aus Zinskurve (Probit) | qa/features/recession.py | tests/test_recession.py | Probit nur mit Daten bis zum jeweiligen Zeitpunkt schätzen |

## 6.3 Unternehmensereignisse

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.3.1 | Quartalszahlen (Umsatz, Gewinn, Margen, Überraschung) | in Arbeit | Yahoo (EPS-Konsens), SEC XBRL (Umsatz, Marge), Finnhub 🔑 | qa/sources/earnings.py | tests/live/test_earnings.py | heute nur EPS-Überraschung; Umsatz/Marge aus XBRL fehlen |
| 6.3.2 | Earnings-Kalender | in Arbeit | Yahoo, Finnhub 🔑 | qa/sources/earnings.py | tests/live/test_earnings.py | |
| 6.3.3 | Erwartete vs. tatsächliche Bewegung (implizite Bewegung) | offen | Yahoo-Optionsketten (nur aktuell) | qa/features/implied_move.py | tests/live/test_options.py | Historie blockiert (Options-Historie lizenziert); täglich selbst mitschreiben, dann wächst eine eigene Historie |
| 6.3.4 | Earnings-Call-Transkripte, Tonfall | blockiert | – | qa/adapters/blocked.py | tests/test_adapters.py | keine freie, erlaubte Quelle gefunden; wird nochmals geprüft |
| 6.3.5 | Gewinnwarnungen | offen | SEC 8-K (Item 2.02, 7.01, Ex. 99.1) | qa/adapters/edgar.py, qa/events/corporate.py | tests/live/test_edgar.py | Einstufung über Textregeln; unsichere Fälle als unklar |
| 6.3.6 | Guidance hoch/runter | offen | SEC 8-K Ex. 99.1 | qa/adapters/edgar.py | tests/live/test_edgar.py | Textauswertung, Genauigkeit wird gemessen und ausgewiesen |
| 6.3.7 | M&A (Übernahmen, Fusionen, Abspaltungen) | offen | SEC 8-K 1.01/2.01, SC TO, DEFM14A | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.8 | Management-Wechsel | offen | SEC 8-K Item 5.02 | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.9 | Aktienrückkäufe und Dividenden | in Arbeit | Yahoo (Dividenden), SEC 8-K/10-Q (Rückkäufe) | qa/sources/corporate.py | tests/live/test_corporate.py | Dividenden ✅, Rückkäufe fehlen |
| 6.3.10 | Aktiensplits | in Arbeit | Yahoo, EDGAR | qa/sources/corporate.py | tests/live/test_corporate.py | |
| 6.3.11 | Kapitalerhöhungen, Verwässerung | offen | SEC S-3, 424B | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.12 | Schulden-Emissionen, Refinanzierung | offen | SEC 8-K, 424B | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.13 | Produktankündigungen | offen | GDELT | qa/adapters/gdelt.py | tests/live/test_gdelt.py | GDELT erst ab 2015 (Version 2) |
| 6.3.14 | Medikamentenzulassungen, Studienergebnisse | offen | openFDA, ClinicalTrials.gov | qa/adapters/fda.py | tests/live/test_fda.py | Zuordnung Firma → Ticker über Namensabgleich, Fehlerquote ausweisen |
| 6.3.15 | Patente | offen | USPTO PatentsView 🔑 | qa/adapters/uspto.py | tests/live/test_uspto.py | |
| 6.3.16 | Klagen, Gerichtsverfahren | offen | SEC 8-K/10-K, CourtListener 🔑 | qa/adapters/courtlistener.py | tests/live/test_courtlistener.py | |
| 6.3.17 | Skandale, Bilanzbetrug, Short-Seller-Reports | offen | GDELT | qa/adapters/gdelt.py | tests/live/test_gdelt.py | nur bei mehreren unabhängigen Quellen als bestätigt |
| 6.3.18 | Cyberangriffe, Datenlecks | offen | SEC 8-K Item 1.05 (seit 12/2023), GDELT | qa/adapters/edgar.py | tests/live/test_edgar.py | wenige Fälle |
| 6.3.19 | Streiks, Arbeitskonflikte | offen | BLS Work Stoppages (frei) | qa/adapters/bls.py | tests/live/test_bls.py | |
| 6.3.20 | Insolvenzen | offen | SEC 8-K Item 1.03 | qa/adapters/edgar.py | tests/live/test_edgar.py | danach oft kein Kurs mehr bei Yahoo (Survivorship-Warnung) |
| 6.3.21 | Prüfer-Wechsel, verspätete Berichte | offen | SEC 8-K Item 4.01, NT 10-K/10-Q | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.22 | Aktionärsversammlungen, Abstimmungen | offen | SEC DEF 14A, 8-K Item 5.07 | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.23 | Aktivistische Investoren | offen | SEC SC 13D | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.3.24 | Blackout-Perioden vor Earnings | offen | abgeleitet aus Earnings-Kalender | qa/events/calendar.py | tests/test_calendar_events.py | |
| 6.3.25 | Lieferketten-, Kunden-/Zulieferer-Ereignisse | offen | Beziehungsgraph (Abschnitt 3) | qa/graph/ | tests/live/test_graph.py | |

## 6.4 Politik, Geopolitik, Regulierung

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.4.1 | Wahlen, Regierungswechsel (weltweit) | in Arbeit | feste Termine (USA, DE); weltweit: ParlGov/Wikidata (frei) | qa/sources/calendar.py | tests/live/test_elections.py | heute nur US-Präsident, US-Zwischenwahl, Bundestag |
| 6.4.2 | Kriege, Konflikte | offen | GDELT; ACLED 🔑 (Forschungszugang) | qa/adapters/gdelt.py, qa/adapters/acled.py | tests/live/test_gdelt.py | |
| 6.4.3 | Sanktionen | offen | OFAC (SDN, Recent Actions), EU-Sanktionsliste | qa/adapters/sanctions.py | tests/live/test_sanctions.py | |
| 6.4.4 | Handelskriege, Zölle | offen | Federal Register API, USTR | qa/adapters/federal_register.py | tests/live/test_federal_register.py | |
| 6.4.5 | Regulatorische Änderungen | offen | Federal Register API, EUR-Lex | qa/adapters/federal_register.py, qa/adapters/eurlex.py | tests/live/test_federal_register.py | |
| 6.4.6 | Branchenregulierung | offen | Federal Register (nach Behörde gefiltert) | qa/adapters/federal_register.py | tests/live/test_federal_register.py | |
| 6.4.7 | Kartell- und Wettbewerbsverfahren | offen | FTC, DOJ (Pressemitteilungen), EU-Kommission (Wettbewerbsfälle) | qa/adapters/antitrust.py | tests/live/test_antitrust.py | |
| 6.4.8 | Steuerreformen | offen | congress.gov API 🔑 | qa/adapters/congress.py | tests/live/test_congress.py | wenige große Fälle |
| 6.4.9 | Länderratings | blockiert | – | qa/adapters/blocked.py | tests/test_adapters.py | keine freie Historie der Agenturen; Ersatz: termine: mit Quelle |
| 6.4.10 | Shutdowns, Schuldenobergrenze | offen | Fiscal Data API, Wikipedia-Tabellen | qa/adapters/treasury.py | tests/live/test_treasury.py | |
| 6.4.11 | Exportkontrollen | offen | Federal Register (BIS-Regeln, Entity List) | qa/adapters/federal_register.py | tests/live/test_federal_register.py | |
| 6.4.12 | Economic Policy Uncertainty | fertig | FRED USEPUINDXD (ohne Schlüssel) | qa/adapters/fred.py | tests/live/test_series_factors.py | `faktor:epu`, Markt `epu`; Veröffentlichung angenommen nächster Werktag 9:00 ET |
| 6.4.13 | Geopolitischer Risiko-Index (GPR) | offen | matteoiacoviello.com (frei) | qa/adapters/gpr.py | tests/live/test_gpr.py | |

## 6.5 Marktstruktur und Kapitalflüsse

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.5.1 | Angebot und Nachfrage (Volumen, Orderbuch) | offen | Yahoo-Volumen; Krypto-Orderbücher (Kraken, Coinbase) | qa/features/volume.py | tests/live/test_volume.py | Aktien-Orderbuch blockiert (lizenziert) |
| 6.5.2 | Liquidität (Spread, Volumen, Markttiefe) | offen | Yahoo (Volumen, Tagesspanne als Spread-Schätzer), Krypto-Orderbücher | qa/features/liquidity.py | tests/live/test_volume.py | historische Spreads Aktien blockiert → Schätzer (Corwin-Schultz), gekennzeichnet |
| 6.5.3 | Positionierung großer Marktteilnehmer (COT) | offen | CFTC COT (frei) | qa/adapters/cftc.py | tests/live/test_cftc.py | Veröffentlichung freitags für Dienstag – Zeitversatz beachten |
| 6.5.4 | 13F-Filings | offen | SEC 13F | qa/adapters/edgar.py | tests/live/test_edgar.py | 45 Tage verzögert |
| 6.5.5 | Optionsverfall (monatlich, Triple Witching) | in Arbeit | Kalender berechnet | qa/sources/calendar.py | tests/live/test_calendar.py | |
| 6.5.6 | 0DTE-Optionen | offen | CBOE (prüfen) | qa/adapters/cboe.py | tests/live/test_cboe.py | voraussichtlich blockiert (Volumen nach Laufzeit lizenziert) |
| 6.5.7 | Gamma-/Dealer-Hedging | offen | Yahoo-Optionsketten (nur aktuell) | qa/features/gamma.py | tests/live/test_options.py | Annahmen dokumentiert; Historie nur durch eigenes tägliches Mitschreiben |
| 6.5.8 | Put/Call-Ratio, Options-Skew | in Arbeit | Cboe SKEW (fertig), Cboe P/C-Archiv (nur 2006–2019) | qa/adapters/cboe.py | tests/live/test_series_factors.py | aktuelle Put/Call-Werte nach 2019 fehlen noch (Quelle prüfen) |
| 6.5.9 | VIX-Laufzeitstruktur | fertig | Cboe VIX, VIX9D, VIX3M, VIX6M | qa/adapters/cboe.py | tests/live/test_series_factors.py | `vix_struktur` = VIX/VIX3M (über 1 = Backwardation) |
| 6.5.10 | Dark-Pool-Aktivität | offen | FINRA OTC/ATS Transparency | qa/adapters/finra.py | tests/live/test_finra.py | wöchentlich, verzögert |
| 6.5.11 | Short Interest, tägliches Short Volume | offen | FINRA (Short Interest, Reg-SHO-Tagesdateien) | qa/adapters/finra.py | tests/live/test_finra.py | |
| 6.5.12 | Leerverkaufskosten (Borrow Fee) | blockiert | – | qa/adapters/blocked.py | tests/test_adapters.py | nur kostenpflichtig (z. B. S3, IHS Markit) |
| 6.5.13 | Short Squeezes (Erkennung) | offen | FINRA + Kurse + Volumen | qa/features/squeeze.py | tests/live/test_finra.py | |
| 6.5.14 | Analysten-Up-/Downgrades, Kursziele | offen | Finnhub 🔑 (Free-Tier prüfen) | qa/adapters/finnhub.py | tests/live/test_finnhub.py | falls nicht im Free-Tier → blockiert |
| 6.5.15 | Analystenrevisionen Gewinnschätzungen | offen | Finnhub 🔑 (prüfen) | qa/adapters/finnhub.py | tests/live/test_finnhub.py | voraussichtlich blockiert |
| 6.5.16 | Index-Aufnahme/-Ausschluss | offen | Wikipedia-Änderungstabellen (S&P 500), S&P-Mitteilungen | qa/adapters/wikipedia.py | tests/live/test_wikipedia.py | Ankündigungs- und Wirksamkeitsdatum getrennt |
| 6.5.17 | Index-Rebalancing (S&P, Russell, MSCI, Nasdaq-100) | in Arbeit | Kalender (Regeln der Anbieter) | qa/sources/calendar.py | tests/live/test_calendar.py | heute nur Quartalsverfall; Russell-Juni, MSCI, Nasdaq-Dezember fehlen |
| 6.5.18 | ETF-Zu-/Abflüsse | offen | Yahoo/Anbieter: ausstehende Anteile (prüfen) | qa/adapters/etf_flows.py | tests/live/test_etf_flows.py | Historie voraussichtlich nicht frei → dann blockiert, tägliches Mitschreiben |
| 6.5.19 | Fonds-Zu-/Abflüsse | offen | ICI (wöchentlich) | qa/adapters/ici.py | tests/live/test_ici.py | |
| 6.5.20 | IPOs | offen | SEC S-1, F-1, 424B | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.5.21 | Lock-up-Ablauf | offen | aus IPO-Datum + Prospekt | qa/events/corporate.py | tests/live/test_edgar.py | |
| 6.5.22 | SPACs | offen | SEC EDGAR | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.5.23 | Insiderhandel | offen | SEC Form 4 | qa/adapters/edgar.py | tests/live/test_edgar.py | |
| 6.5.24 | Algorithmic/HFT-Trading | offen | Näherung aus Intraday-Volatilität und Volumen (Yahoo, nur jüngste 60 Tage) | qa/features/microstructure.py | tests/live/test_volume.py | klar als Näherung gekennzeichnet, kurze Historie |
| 6.5.25 | Trendfolger/CTA-Positionierung | offen | geschätzt aus Trendsignalen der Futures | qa/features/cta.py | tests/test_cta.py | Schätzung, gekennzeichnet |
| 6.5.26 | Vol-gesteuerte Fonds, Risk Parity | offen | geschätzt aus realisierter Volatilität | qa/features/vol_control.py | tests/test_vol_control.py | Schätzung, gekennzeichnet |
| 6.5.27 | Pensionsfonds-Rebalancing | in Arbeit | Kalender (Monats-/Quartalsende) + Aktien/Anleihen-Performance | qa/sources/calendar.py | tests/live/test_calendar.py | Performance-Schätzung fehlt |
| 6.5.28 | Quartalsende-Effekte (Window Dressing) | offen | Kalender | qa/sources/calendar.py | tests/live/test_calendar.py | |
| 6.5.29 | Tax-Loss-Selling | offen | Kalender + Jahresverlierer | qa/features/tax_loss.py | tests/live/test_calendar.py | |
| 6.5.30 | Aktienrückkauf-Fenster | offen | abgeleitet aus Earnings-Kalender | qa/events/calendar.py | tests/test_calendar_events.py | |
| 6.5.31 | Margin-Schulden | offen | FINRA Margin Statistics | qa/adapters/finra.py | tests/live/test_finra.py | monatlich |
| 6.5.32 | Privatanleger-Ströme | blockiert | – | qa/adapters/blocked.py | tests/test_adapters.py | nur kostenpflichtig |

## 6.6 Anleihen, Kredit, Währungen

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.6.1 | Zinsstrukturkurve (Inversion, Steilheit) | in Arbeit | FRED T10Y2Y, US Treasury | qa/regimes.py | tests/live/test_fred.py | |
| 6.6.2 | Anleihemarkt-Bewegungen | in Arbeit | FRED, Bundesbank, EZB | qa/sources/prices.py | tests/live/test_prices.py | |
| 6.6.3 | Term Premium | in Arbeit | FRED THREEFYTP10 (Kim-Wright, fertig geladen), NY Fed ACM (offen) | qa/adapters/fred.py | tests/live/test_series_factors.py | Kim-Wright wird neu geschätzt → nicht point-in-time, darum nicht „fertig“; ACM folgt |
| 6.6.4 | Kreditspreads (IG, HY) | fertig | FRED BAA10Y (ab 1986), ICE BofA HY/IG (nur 3 Jahre frei) | qa/adapters/fred.py | tests/live/test_series_factors.py | `baa_spread`, `hy_spread`, `ig_spread`; HY/IG wenige Fälle (Bericht warnt) |
| 6.6.5 | Finanzstress-Indizes | fertig | FRED STLFSI4, NFCI | qa/adapters/fred.py | tests/live/test_series_factors.py | NFCI wird rückwirkend neu geschätzt (im Bericht gewarnt) |
| 6.6.6 | Bankenstress, Interbankenmarkt | offen | FRED (z. B. SOFR − T-Bill, Bankaktien-Index) | qa/features/bank_stress.py | tests/live/test_fred.py | TED-Spread eingestellt; Ersatz dokumentieren |
| 6.6.7 | Währungsbewegungen (FX) | in Arbeit | Yahoo, EZB-Referenzkurse, FRED | qa/sources/prices.py | tests/live/test_prices.py | Stooq: siehe offene Frage (Bot-Schutz) |
| 6.6.8 | Dollar-Index | fertig | FRED DTWEXBGS, Yahoo DX-Y.NYB | qa/adapters/fred.py, qa/sources/prices.py | tests/live/test_series_factors.py | `dollar_breit`, `dollar` |
| 6.6.9 | Carry-Trades | offen | Zinsdifferenzen (FRED, EZB, BIS) + FX | qa/features/carry.py | tests/live/test_carry.py | |
| 6.6.10 | Schwellenländer-Anleihen und -Währungen | offen | FRED (EM-Spreads), Yahoo-FX | qa/adapters/fred.py | tests/live/test_fred.py | |

## 6.7 Rohstoffe und Energie

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.7.1 | Rohstoffpreise (Öl, Gas, Gold, Silber, Kupfer, Agrar) | in Arbeit | Yahoo-Futures, FRED, EIA 🔑 | qa/sources/prices.py | tests/live/test_prices.py | Futures ohne Roll-Bereinigung |
| 6.7.2 | Öl-/Gaslagerberichte (EIA) | in Arbeit | ALFRED 🔑 (Öl), EIA-API 🔑 (Gas) | qa/sources/fred.py | tests/live/test_eia.py | Gas fehlt |
| 6.7.3 | OPEC-Entscheidungen | offen | OPEC-Pressemitteilungen | qa/adapters/opec.py | tests/live/test_opec.py | Termine mit Quelle; Richtung (Kürzung/Erhöhung) aus Text |
| 6.7.4 | Rohstoff-Angebotsschocks | in Arbeit | Kurs-Schocks (Yahoo); EIA, GDELT | qa/sources/moves.py | tests/live/test_moves.py | Angebots-/Nachfrageschock noch nicht getrennt |
| 6.7.5 | Raffineriemargen (Crack Spread) | offen | berechnet aus CL=F, RB=F, HO=F | qa/features/crack.py | tests/live/test_crack.py | 3-2-1-Spread |
| 6.7.6 | Strompreise | offen | EIA 🔑 | qa/adapters/eia.py | tests/live/test_eia.py | |
| 6.7.7 | Kupfer/Gold-Verhältnis | offen | berechnet (HG=F, GC=F) | qa/features/ratios.py | tests/live/test_ratios.py | |
| 6.7.8 | Agrar-Berichte (WASDE, Ernteschätzungen) | offen | USDA (WASDE-Archiv, NASS 🔑) | qa/adapters/usda.py | tests/live/test_usda.py | Konsens nicht frei → Termine + Kursreaktion |
| 6.7.9 | Frachtraten, Baltic Dry | offen | Näherung über Reederei-Aktien/ETF (frei) | qa/features/shipping.py | tests/live/test_shipping.py | Baltic Dry selbst lizenziert → Näherung gekennzeichnet |
| 6.7.10 | Lieferketten-Druck (GSCPI) | offen | New York Fed (frei) | qa/adapters/nyfed.py | tests/live/test_nyfed.py | |
| 6.7.11 | Futures-Kurvenform | offen | Yahoo (einzelne Kontraktmonate, nur aktuell) | qa/features/futures_curve.py | tests/live/test_futures_curve.py | Historie der Kurve nicht frei → tägliches Mitschreiben |

## 6.8 Natur, Wetter, Gesundheit, Extremereignisse

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.8.1 | Wetterereignisse | offen | NOAA 🔑, Open-Meteo (frei) | qa/adapters/weather.py | tests/live/test_weather.py | Event = Abweichung vom langjährigen Mittel (z. B. Heizgradtage) |
| 6.8.2 | Hurrikane, Stürme | offen | NOAA NHC (HURDAT2) | qa/adapters/noaa_nhc.py | tests/live/test_noaa_nhc.py | |
| 6.8.3 | Dürre, Ernteausfälle | offen | US Drought Monitor, USDA | qa/adapters/drought.py | tests/live/test_drought.py | |
| 6.8.4 | Naturkatastrophen (Erdbeben, Fluten, Vulkane) | offen | USGS, GDACS | qa/adapters/usgs.py, qa/adapters/gdacs.py | tests/live/test_disasters.py | |
| 6.8.5 | Pandemien, Krankheitsausbrüche | offen | WHO, Our World in Data | qa/adapters/owid.py | tests/live/test_owid.py | wenige Fälle → als Fallstudie gekennzeichnet |
| 6.8.6 | Black-Swan-Ereignisse | in Arbeit | Kurs-Schocks > 4 σ (Yahoo) + GDELT-Abgleich | qa/sources/moves.py | tests/live/test_moves.py | Nachrichten-Abgleich fehlt |
| 6.8.7 | Infrastruktur-Ausfälle (Strom, Kanäle, Häfen) | offen | GDELT | qa/adapters/gdelt.py | tests/live/test_gdelt.py | |

## 6.9 Sentiment, soziale Medien, Aufmerksamkeit

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.9.1 | Marktsentiment / VIX | fertig | Cboe VIX (Adapter), Yahoo ^VIX | qa/adapters/cboe.py | tests/live/test_series_factors.py | `vix_cboe`, Phasen vix_hoch/vix_niedrig |
| 6.9.2 | Fear-and-Greed-Indikatoren | offen | eigene Berechnung (VIX, Put/Call, Momentum, Spreads); Krypto: alternative.me | qa/features/fear_greed.py | tests/live/test_fear_greed.py | |
| 6.9.3 | AAII-Anlegerumfrage | offen | AAII (prüfen) | qa/adapters/aaii.py | tests/live/test_aaii.py | Download evtl. nur für Mitglieder → dann blockiert |
| 6.9.4 | Reddit (wallstreetbets) | offen | Reddit-API 🔑 (nichtkommerziell frei) | qa/adapters/reddit.py | tests/live/test_reddit.py | Historie nur kurz rückwärts |
| 6.9.5 | Stocktwits | offen | Stocktwits-API (prüfen) | qa/adapters/stocktwits.py | tests/live/test_stocktwits.py | Neuregistrierungen waren geschlossen → voraussichtlich blockiert |
| 6.9.6 | Twitter/X | blockiert | X-API kostenpflichtig | qa/adapters/blocked.py | tests/test_adapters.py | |
| 6.9.7 | Finfluencer | offen | YouTube Data API 🔑, Reddit 🔑 | qa/adapters/youtube.py | tests/live/test_youtube.py | |
| 6.9.8 | Meme-Stock-Trends | offen | Erwähnungen (Reddit, Wikipedia-Aufrufe) + Volumen + Short Interest | qa/features/meme.py | tests/live/test_meme.py | |
| 6.9.9 | Koordinierte Short-Squeeze-Aktionen | offen | Erwähnungen + Short Interest + Optionsvolumen | qa/features/squeeze.py | tests/live/test_meme.py | Optionsvolumen nur aktuell |
| 6.9.10 | Sentiment-Analyse-Tools | offen | Wörterbuch (Loughran-McDonald, frei) ; FinBERT lokal (optional) | qa/features/tone.py | tests/test_tone.py | FinBERT braucht PyTorch (groß) → nur lokal, nicht auf Streamlit |
| 6.9.11 | Fake News | offen | GDELT: bestätigt nur bei mehreren unabhängigen Quellen | qa/features/confirmation.py | tests/live/test_gdelt.py | widerrufene Meldungen getrennt auswerten |
| 6.9.12 | CEO-/Politiker-Posts | blockiert | X-API kostenpflichtig; andere Plattformen ohne freie Historie | qa/adapters/blocked.py | tests/test_adapters.py | Ersatz: termine: mit Quelle |
| 6.9.13 | Google-Suchtrends | offen | pytrends (inoffiziell) | qa/adapters/google_trends.py | tests/live/test_google_trends.py | siehe offene Frage (Nutzungsbedingungen) |
| 6.9.14 | Wikipedia-Seitenaufrufe | offen | Wikimedia-API (frei) | qa/adapters/wikipedia.py | tests/live/test_wikipedia.py | ab 2015 |
| 6.9.15 | Nachrichtenvolumen und Tonfall | offen | GDELT | qa/adapters/gdelt.py | tests/live/test_gdelt.py | |
| 6.9.16 | App-Downloads, Web-Traffic | blockiert | – | qa/adapters/blocked.py | tests/test_adapters.py | nur kostenpflichtig |

## 6.10 Krypto

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.10.1 | Korrelation zu Aktien, Nasdaq, Gold, Dollar | offen | berechnet (rollierend) | qa/features/correlation.py | tests/live/test_correlation.py | |
| 6.10.2 | Kurse und Volumen | in Arbeit | Yahoo (BTC-USD …); Kraken, Coinbase, CoinGecko | qa/sources/prices.py | tests/live/test_crypto.py | Binance sperrt US-Server (GitHub, Streamlit) → Kraken/Coinbase bevorzugt |
| 6.10.3 | Funding Rates, Open Interest | offen | Börsen-APIs (Kraken Futures, Bybit, OKX) | qa/adapters/crypto_derivs.py | tests/live/test_crypto.py | |
| 6.10.4 | Stablecoin-Angebot | offen | DefiLlama (frei) | qa/adapters/defillama.py | tests/live/test_crypto.py | |
| 6.10.5 | On-Chain-Daten | offen | Blockchain.com Charts-API (frei) | qa/adapters/onchain.py | tests/live/test_crypto.py | Börsen-Zuflüsse nur kostenpflichtig → Teil blockiert |
| 6.10.6 | Bitcoin-ETF-Zu-/Abflüsse | offen | Anbieter-Websites (prüfen) | qa/adapters/etf_flows.py | tests/live/test_etf_flows.py | |
| 6.10.7 | Krypto-Regulierung | offen | Federal Register, SEC | qa/adapters/federal_register.py | tests/live/test_federal_register.py | |
| 6.10.8 | Halving-Zyklen, Token-Unlocks | offen | Halving berechnet (Blockhöhe); Unlocks: DefiLlama (prüfen) | qa/events/crypto_calendar.py | tests/live/test_crypto.py | |

## 6.11 Kalender und Saisonalität

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.11.1 | Saisonalität (Januar, Santa, Sell in May, Monatsanfang, Wochentage) | in Arbeit | aus Kursdaten | qa/sources/calendar.py | tests/live/test_calendar.py | Sell in May fehlt |
| 6.11.2 | Feiertage, verkürzte Handelstage | offen | pandas_market_calendars | qa/events/trading_calendar.py | tests/test_trading_calendar.py | heute nur über tatsächliche Handelstage |
| 6.11.3 | Präsidentschaftszyklus | offen | berechnet | qa/sources/calendar.py | tests/live/test_calendar.py | |
| 6.11.4 | Gemeinsamer Ereigniskalender im Voraus | offen | alle Termin-Quellen | qa/events/calendar.py | tests/test_calendar_events.py | |

## 6.12 Technik und Preis

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.12.1 | Technische Marken (Unterstützung, Widerstand, Durchschnitte, Allzeithoch, runde Zahlen) | in Arbeit | aus Kursdaten | qa/sources/moves.py | tests/live/test_moves.py | 200-Tage-Linie, 52-Wochen-Hoch/-Tief ✅; Rest fehlt |
| 6.12.2 | Momentum und Trend | in Arbeit | berechnet | qa/backtest.py | tests/live/test_backtest.py | als Feature für Ereignisse fehlt |
| 6.12.3 | Mean Reversion | in Arbeit | berechnet | qa/backtest.py | tests/live/test_backtest.py | |
| 6.12.4 | Volatilitäts-Regime | offen | berechnet | qa/features/vol_regime.py | tests/test_vol_regime.py | |
| 6.12.5 | Marktbreite | offen | aus Kursen der Indexmitglieder | qa/features/breadth.py | tests/live/test_breadth.py | Mitglieder-Historie lückenhaft → Survivorship-Warnung |
| 6.12.6 | Gaps, Kurslücken | offen | berechnet (Eröffnung/Schluss) | qa/features/gaps.py | tests/live/test_gaps.py | |
| 6.12.7 | Korrelationen zwischen Anlageklassen | offen | berechnet | qa/features/correlation.py | tests/live/test_correlation.py | |

## 6.13 Bewertung und Fundamentaldaten

| # | Faktor | Status | Datenquelle | Modul-Datei | Test-Datei | Notiz |
|---|---|---|---|---|---|---|
| 6.13.1 | Value, Quality, Size, Low Vol, Investment, Momentum | offen | SEC XBRL + Kurse; Fama-French, AQR, Open Source Asset Pricing zum Vergleich | qa/adapters/french.py, qa/features/factors.py | tests/live/test_factors.py | XBRL mit Einreichungsdatum (Point-in-Time) |
| 6.13.2 | Bewertung des Gesamtmarkts (CAPE) | offen | Shiller-Daten (frei) | qa/adapters/shiller.py | tests/live/test_shiller.py | |
| 6.13.3 | Gewinnrevisions-Trend der Branche | offen | Finnhub 🔑 (prüfen) | qa/adapters/finnhub.py | tests/live/test_finnhub.py | voraussichtlich blockiert |
| 6.13.4 | Verschuldung, Zinslast | offen | SEC XBRL | qa/adapters/edgar.py | tests/live/test_edgar.py | |

## Pflicht-Bausteine außerhalb der Faktorenliste

| Baustein | Status | Modul | Notiz |
|---|---|---|---|
| Einheitlicher Adapter (load, update, cache, meta mit Veröffentlichungszeit), Retry mit Backoff, Rate-Limits | in Arbeit | qa/adapters/base.py | fertig für FRED/Cboe/blockierte; ältere Quellen in qa/sources/ ziehen nach und nach um |
| Event-Speicher (Typ, Veröffentlichungszeitpunkt, Assets, Stärke, Quelle), Parquet + DuckDB | offen | qa/events/store.py | heute EventSet je Lauf, nicht gespeichert |
| Beziehungsgraph: Töchter (Exhibit 21, Wikidata), Großkunden > 10 %, SIC, Kostenabhängigkeit, 13F-Eigentümer, BEA-Input-Output, Quelle + Datum je Kante | offen | qa/graph/ | |
| Faktor-Betas (rollierend: Öl, Zinsen, Dollar, VIX, Spreads …) | offen | qa/features/betas.py | |
| Kettenreaktions-Engine (Stufen einstellbar, Stärke + Unsicherheit je Stufe, Abschwächung, „Hypothese, unbestätigt“) | in Arbeit | qa/chain.py → qa/chain/ | heute: Glieder per Hand, jedes gemessen; Graph-Lauf, Abschwächung und Stärke-Fortpflanzung fehlen |
| Analog-Suche | offen | qa/analysis/analogs.py | |
| Earnings-Muster (Umsatz, Gewinn, Guidance; Firma, Branche, alle; Spillover auf Kollegen, Zulieferer, Kunden) | in Arbeit | qa/sources/earnings.py | EPS-Überraschung und weitere Märkte ✅; Umsatz, Guidance, Branche, Graph-Spillover fehlen |
| Ereignisstudien-Standard: Markt- und Faktormodell, Fenster −5…+20, CAR, Treffer, Mittel/Median, KI, p, Mehrfachtest, Regime | in Arbeit | qa/study.py | Markt ✅, Mehrfachtest ✅, Regime ✅; Faktormodell (Fama-French), Vorlauf-Fenster, CAR-Kurve, Median, Konfidenzintervall fehlen |
| Qualitätsregeln (Survivorship, Look-ahead, Point-in-Time, Adjusted Close, Datenfehler, Zeitzonen, Renditen, Overfitting, Snooping, OOS, Walk-Forward, Purged CV, DSR, Regime, Begründung, Robustheit) | in Arbeit | qa/quality.py, qa/backtest.py | Purged/Embargo-CV fehlt |
| Kennzahlen (inkl. Fama-French-Alpha, IC, IR, Kapazität) | in Arbeit | qa/metrics.py | FF-Alpha, IC, IR, Kapazität fehlen |
| Kosten (Gebühren, Spreads, Slippage, Impact, Liquidität, Leihe, Steuern) | in Arbeit | qa/backtest.py | heute eine Pauschale je Wechsel |
| Risiko (Vol-Targeting, Risk Parity, Bruchteil-Kelly, Diversifikation, Stops, Stresstests, VaR, ES, Hebel) | in Arbeit | qa/metrics.py | Stresstests, VaR, ES ✅; Rest fehlt |
| Faktor-Strategien (Momentum, Value, Quality, Size, Low Vol, Investment, Umkehr, Trend, Carry, Pairs/Kointegration, Vol-Prämie) | in Arbeit | qa/backtest.py | Momentum, Umkehr, Trend ✅ |
| „Wenig Daten“ unter 20 Fällen, zu gute Backtests markieren | in Arbeit | qa/study.py, qa/backtest.py | unter 20 ✅; Warnung „zu gut“ fehlt |
| Bericht nach Abschnitt 8 (Baum, je Stufe Statistik, Analogien, Earnings, Regime, Gegenargumente, Datenwarnungen) | offen | qa/reports/ | |
| Zeitplaner für Daten-Updates | in Arbeit | .github/workflows/routine.yml, .github/workflows/live-tests.yml | Berichte täglich, Live-Tests sonntags; Daten-Update je Adapter fehlt |
| Abnahme-Durchläufe: Öl stark, Earnings-Beat mit Spillover, Zinsentscheidung über alle Anlageklassen | offen | tests/live/test_acceptance.py | |
| README: Installation, Schlüssel, Oberfläche, Daten-Update | in Arbeit | README.md | |
