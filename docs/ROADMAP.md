# Fahrplan

Jeder Punkt aus der Anforderungsliste vom 28.10.2026 mit Stand.
✅ umgesetzt · 🟡 teilweise · 🔜 geplant (Stufe) · ❌ gratis nicht machbar

**Stufen:** 1–2 Ereignisse, Ketten, Earnings (fertig) · 3 Backtests & Kennzahlen · 4 Faktoren, Signale & Fundamentaldaten · 5 Risiko & Portfolio · 6 weitere Datenquellen & Lieferketten

## Denkweise
| Punkt | Stand |
|---|---|
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
| Overfitting | ✅ Ereignis-Studien ohne optimierte Parameter · 🔜 3: Strategie-Parameter mit Strafe |
| Data Snooping | ✅ Benjamini-Hochberg je Bericht, Regel „jede Variante zählt“ (CLAUDE.md) · 🔜 3: Versuchsprotokoll über alle Läufe |
| Out-of-Sample | 🟡 Hälften-Test · 🔜 3: fester Holdout-Zeitraum, der nie zum Entwickeln genutzt wird |
| Walk-Forward | 🔜 3 |
| Zeitreihen-Cross-Validation (Purging, Embargo) | 🔜 3 |
| Deflated Sharpe Ratio | 🔜 3 |
| Regime-Wechsel | 🟡 `--von/--bis`, Hälften, Zins- vs. Info-Schock · 🔜 4: Regime automatisch (VIX, Zinskurve, Trend) |
| Ökonomische Begründung | ✅ Pflichtfeld „warum“ je Kettenglied |
| Robustheit (Zeiträume, Märkte, Parameter) | 🟡 Zeiträume, Märkte · 🔜 3: Parameter-Gitter |

## Kennzahlen (Stufe 3)
Sharpe, Sortino, Max Drawdown, Calmar, annualisierte Volatilität, Schiefe/Kurtosis, Gewinn/Verlust-Verhältnis, IC, Information Ratio, Turnover – 🔜 3.
Beta ✅ (Marktbereinigung) · Hit Rate ✅ („% ↑“ in den Berichten) · Alpha nach Fama-French 🔜 4 (French Library) · Krisen-Korrelationen 🔜 5.
Transaktionskosten, Slippage 🔜 3 (Annahmen je Markt) · Market Impact, Kapazität 🟡 3 (grob über Volumen) · Liquidität 🟡 (Volumen gratis, historische Spreads ❌) · Leerverkaufskosten ❌ · Steuern 🔜 5 (einfache Annahme Abgeltungsteuer).

## Risiko und Portfolio (Stufe 5)
Positionsgrößen (Volatility Targeting, Risk Parity), Kelly (Bruchteil), Diversifikation, Stop-Loss und Limits, Stresstests (2000, 2008, März 2020, 2022), VaR und Expected Shortfall, Hebel und Margin – alle 🔜 5.

## Faktoren und Signale (Stufe 4)
| Punkt | Stand |
|---|---|
| Momentum, Value, Quality, Size, Low Vol, Investment | 🔜 4: Faktor-Renditen aus French Library / AQR; Einzelaktien-Kennzahlen aus SEC XBRL (nur US) |
| Kurzfristige Mean Reversion, Time-Series-Momentum | 🔜 4 |
| Carry | 🔜 4: Währungen über Zinsdifferenzen (FRED/EZB) · 🟡 Futures-Roll: Yahoo ohne Roll-Daten |
| Saisonalität | 🔜 4 |
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
