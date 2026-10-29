# Fahrplan

Jeder Punkt aus der Anforderungsliste vom 28.10.2026 mit Stand.
✅ umgesetzt · 🟡 teilweise · 🔜 geplant (Stufe) · ❌ gratis nicht machbar

**Stufen:** 1–2 Ereignisse, Ketten, Earnings (fertig) · 3 Backtests & Kennzahlen (Kern fertig) · 4 Faktoren, Signale & Fundamentaldaten · 5 Risiko & Portfolio · 6 weitere Datenquellen & Lieferketten

## Plattform wie QuantPad (Grundbausteine, 29.10.2026)
| Punkt | Stand |
|---|---|
| Navigation Projekte · Quant Copilot · Community, Website-Aufbau, Hellblau | ✅ `app.py`, `web/` |
| Projekte: virtuelles Dateisystem, Dateien ausführen, Chats und Artefakte | ✅ (.json überall, .py nur lokal) |
| Quant Copilot: Agent mit Werkzeugen, Stufen wählbar | ✅ Befehle gratis; freie Fragen gratis über Claude Code (MCP), auf der Website mit API-Schlüssel (Stufe = effort) |
| Community: veröffentlichen, Projekte und Befehle übernehmen | ✅ Ordner `community/` (öffentliches Repository) |
| Widgets/Artifacts | ✅ Diagramme (Kapitalkurven, Kerzen), Tabellen, Downloads, Artefakte je Projekt |
| Beispiel-Workflows: Einstiege, P&L nach Regime, Über Nacht vs. Handelszeit, Optionsrecherche | ✅ `/trades`, `/regime-pnl`, `/overnight`, `/optionen` · ❌ Orderflow vor dem Einstieg (Ticks/Orderbuch gratis nicht verfügbar; Ersatz: Tagesverlauf vorher) |
| Slash-Befehle /review, /compact, /create-command, /goal, /commands, eigener /walk-forward | ✅ (`/goal` prüft Varianten auf Entwicklungsdaten, Test einmal) |
| Befehle als .md importierbar | ✅ |
| Memory (einsehbar, korrigierbar, löschbar, abschaltbar) und Instructions | ✅ Konto; MCP-Werkzeuge `merken`, `gedaechtnis` |
| Daten-API über MCP: search_symbols, get_coverage, resolve_symbology, describe_schema, get_usage, get_api_usage_guide, preview_bars | ✅ `symbole_suchen`, `abdeckung`, `symbol_aufloesen`, `schema_erklaeren`, `nutzung`, `daten_anleitung`, `kerzen_vorschau` (500 Kerzen/31 Tage) |
| Python-SDK | ✅ `qa.data` · 🟡 Futures ohne Roll-Bereinigung |
| Kerzen 1 Sekunde bis 1 Jahr | 🟡 1 Minute bis 1 Monat (Yahoo); Intraday nur 30/60/730 Tage zurück |
| Trades, Quotes, Orderbuch (10 Level), Options-Historie | ❌ gratis nicht verfügbar |
| 40+ CME-Futures | 🟡 29 Märkte (Yahoo, vorderster Kontrakt) |
| SEC EDGAR | 🔜 Stufe 4 |
| Cloud-Rechner je Projekt mit Schlafmodus | 🟡 Streamlit-Server (schläft bei Inaktivität), tägliche Läufe über GitHub Actions; eigene Skripte lokal |
| Pine-Script / pine-runner | 🔜 später |
| Abo, Stripe, API-Schlüssel-Verwaltung | – nicht nötig (Eigengebrauch, kostenlos) |

## Denkweise
| Punkt | Stand |
|---|---|
| KI-Chat wie bei QuantPad, alle Analysen als Werkzeuge | ✅ Quant Copilot: Befehle gratis, freie Fragen gratis über Claude Code (MCP) oder mit API-Schlüssel; `qa chat` |
| Kombinationen mehrerer Muster | ✅ Marktphasen + `--zusammen-mit` / `--ohne` (±Tage), Ketten über mehrere Ebenen |
| Alle ~70 Markttreiber der Liste vom 29.10. | ✅ Katalog `qa katalog` / App „Abdeckung“: 16 ✅, 8 ✅🔑, 23 🟡, 14 🔜, 10 ❌ |
| Kettenreaktionen über mehrere Ebenen (Öl → Transport → Reifen …) | ✅ `/kette`, `qa kette` – KI denkt weit, jedes Glied wird gemessen |
| Verflechtungen (Sparten, Töchter, Kunden) | 🟡 KI liest Geschäftsberichte und nennt Fundstelle · 🔜 6: Kunden > 10 % Umsatz automatisch aus 10-K |
| Earnings-Muster über Jahre und viele Firmen | ✅ `qa earnings` (Konsens von Yahoo, einzeln und zusammen, bis 60 Tage danach) |
| Wer reagiert noch auf die Zahlen einer Firma (Aktien, Währungen, Krypto) | ✅ `qa earnings NVDA --maerkte AMD,TSM,bitcoin` |
| Langsame Ausbreitung (A heute → B in einigen Tagen) | 🔜 6: Lead-Lag-Test je Kettenglied |

## Verzerrungen und Datenqualität
| Punkt | Stand |
|---|---|
| Survivorship Bias | 🟡 Warnung in jedem Bericht, Indizes/ETFs möglich · ❌ Kurse delisteter Firmen gibt es gratis nicht (Profis: CRSP) |
| Look-ahead Bias | ✅ Reaktion ab Vortagesschluss, Beta nur aus der Zeit vor dem Ereignis, Schock-Schwelle aus dem Vorjahr, Erwartung nur aus früheren Werten |
| Point-in-Time / Revisionen | ✅ Makro als Erstveröffentlichung (ALFRED) · 🔜 4: Fundamentaldaten mit Einreichungsdatum (SEC XBRL `filed`) |
| Adjusted Close (Splits, Dividenden) | ✅ yfinance `auto_adjust` |
| Datenfehler (Ausreißer, fehlende Tage, falsche Kurse) | ✅ `qa/quality.py` meldet, repariert nicht still · 🟡 Tickerwechsel nur über Ausreißer-Warnung |
| Zeitzonen, Handelskalender | ✅ Reaktionstag je Börse (Frankfurt 17:30, New York 16:00, Krypto UTC), Feiertage über echte Handelstage |
| Renditen statt Preise | ✅ |
| Log- vs. einfache Renditen | ✅ einfache Renditen in Ereignis-Studien (bewusst: über Firmen addierbar) · 🔜 3: Log-Renditen für Zeitreihen-Modelle |
| Overfitting | ✅ Ereignis-Studien ohne optimierte Parameter · ✅ Backtests: wenige Parameter je Regel, Auswahl nur auf Entwicklungsdaten |
| Data Snooping | ✅ Benjamini-Hochberg je Bericht, Regel „jede Variante zählt“ (CLAUDE.md) · ✅ Versuchsprotokoll `data/trials.jsonl` über alle Läufe |
| Out-of-Sample | ✅ Hälften-Test (Ereignisse) · ✅ Backtests: `holdout_ab`, nie zur Parameterwahl genutzt |
| Walk-Forward | ✅ jährlich neu gewählt, nur aus Vorjahren |
| Zeitreihen-Cross-Validation (Purging, Embargo) | 🟡 PBO über zeitliche Blöcke (CSCV) · 🔜 Purging/Embargo für Modelle mit überlappenden Zielen (Stufe 4) |
| Deflated Sharpe Ratio | ✅ mit Zahl aller je getesteten Varianten |
| Regime-Wechsel | ✅ Marktphasen als Bedingung (`--bedingung` vix_hoch, trend_ab, zinskurve_invers, kreditstress, zinsen_hoch …), Hälften, Zins- vs. Info-Schock |
| Ökonomische Begründung | ✅ Pflichtfeld „warum“ je Kettenglied |
| Robustheit (Zeiträume, Märkte, Parameter) | ✅ Zeiträume, Märkte, Parameter-Gitter (Anteil positiver Varianten, PBO) |

## Kennzahlen (Stufe 3)
✅ Sharpe, Sortino, Max Drawdown, Calmar, annualisierte Volatilität, Schiefe/Kurtosis, Trefferquote, Gewinn/Verlust-Verhältnis, Turnover, Beta, Alpha zum Markt, Krisen-Korrelation, VaR/Expected Shortfall, PSR, Stresstests (2000, 2008, März 2020, 2022) – `qa/metrics.py`, `qa backtest`. 🔜 IC und Information Ratio (bei Signalen über viele Titel, Stufe 4).
Beta ✅ (Marktbereinigung) · Hit Rate ✅ („% ↑“ in den Berichten) · Alpha nach Fama-French 🔜 4 (French Library) · Krisen-Korrelationen 🔜 5.
Transaktionskosten, Slippage ✅ als Kosten je Positionswechsel (`kosten_bp`) · Market Impact, Kapazität 🟡 3 (grob über Volumen) · Liquidität 🟡 (Volumen gratis, historische Spreads ❌) · Leerverkaufskosten ❌ · Steuern 🔜 5 (einfache Annahme Abgeltungsteuer).

## Risiko und Portfolio (Stufe 5)
Positionsgrößen (Volatility Targeting, Risk Parity), Kelly (Bruchteil), Diversifikation, Stop-Loss und Limits, Stresstests (2000, 2008, März 2020, 2022), VaR und Expected Shortfall, Hebel und Margin – alle 🔜 5.

## Faktoren und Signale (Stufe 4)
| Punkt | Stand |
|---|---|
| Momentum, Value, Quality, Size, Low Vol, Investment | 🔜 4: Faktor-Renditen aus French Library / AQR; Einzelaktien-Kennzahlen aus SEC XBRL (nur US) |
| Kurzfristige Mean Reversion, Time-Series-Momentum | 🔜 4 |
| Carry | 🔜 4: Währungen über Zinsdifferenzen (FRED/EZB) · 🟡 Futures-Roll: Yahoo ohne Roll-Daten |
| Saisonalität | ✅ `kalender:` januar, santa, monatsanfang/-ende, Wochentage, Optionsverfall, Hexensabbat |
| Earnings-Effekte, Post-Earnings-Drift | ✅ `qa earnings` (60-Tage-Horizont) |
| Analystenrevisionen | ❌ gratis keine Historie |
| Insider-Käufe | 🔜 4: SEC Form 4 |
| Index-Aufnahmen/-Ausschlüsse | 🟡 4: Historie nur lückenhaft frei |
| Short Interest | 🔜 4: FINRA |
| Pairs Trading / Kointegration | 🔜 4 |
| Volatilitätsrisikoprämie | 🔜 4: VIX vs. realisierte Volatilität |
| Makro-Regime, Sentiment (VIX, Put/Call, COT) | 🔜 4: FRED, CBOE, CFTC |

## Datenquellen
| Quelle | Stand |
|---|---|
| Yahoo (yfinance), FRED, ALFRED, EZB EA-MPD, SF Fed | ✅ |
| Yahoo-Gewinntermine mit Konsens | ✅ |
| Bundesbank (Bund-Renditen 2J/10J seit 1997), EZB Data Portal (Referenzkurse, Euro-Renditen) | ✅ `bund2j`, `bund10j`, `euro_aaa_10j`, `eurusd_ezb`, beliebige Reihen über `BBK:`/`EZB:` |
| Eurostat, US Treasury | 🔜 6 |
| Stooq | ❌ blockiert automatische Abfragen inzwischen mit einer Browser-Prüfung |
| investing.com | ❌ Auslesen laut Nutzungsbedingungen verboten und technisch gesperrt (Cloudflare) – wird nicht umgangen |
| SEC EDGAR, XBRL, Financial Statement Data Sets, 13F, Form 4 | 🔜 4/6 |
| French Library, Open Source Asset Pricing, AQR, Shiller | 🔜 4 |
| CFTC COT, CBOE, FINRA | 🔜 4 |
| GDELT, Google Trends, Wikipedia-Aufrufe, Reddit | 🔜 6 |
| Binance/Coinbase/Kraken (Krypto-Minuten, Trades) | 🔜 6 |
| Alpha Vantage, Twelve Data, Massive, Finnhub, Tiingo, EODHD | nur auf Wunsch (Schlüssel, Tageslimits) |
| Historische Optionsdaten | ❌ gratis kaum vorhanden |
| CRSP, Compustat | ❌ kostenpflichtig – Grenze aller Gratis-Ergebnisse |

## Werkzeuge
pandas, numpy, scipy ✅ · statsmodels 🔜 3 (robuste Standardfehler, Local Projections) · scikit-learn 🔜 4 · Backtester: eigener, schlanker in Stufe 3 (volle Kontrolle über Look-ahead), vectorbt als Gegenprobe · quantstats für Berichte 🔜 3.

**Faustregel im Code und in jedem Bericht:** Zu gute Ergebnisse auf Gratisdaten sind zuerst ein Hinweis auf einen Fehler.
