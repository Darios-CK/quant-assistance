# Backtest: EUR/USD nach EZB-Überraschungen

> Begründung: Die Ereignis-Analyse zeigt: nach harten EZB-Überraschungen steigt EUR/USD auch noch in der Woche danach (langsame Verarbeitung). Gehandelt wird erst zum Schluss des Reaktionstags.

- **Markt:** EUR/USD · **Regel:** ereignis (auch short) · **Kosten:** 1,0 Bp je Positionswechsel
- **Gewählte Parameter:** {"halten": 1, "schwelle": 1.0} – ausgewählt nur auf Daten vor 01.01.2018
- **Getestete Varianten:** 12 in diesem Lauf, 12 insgesamt für eurusd/ereignis (Versuchsprotokoll) · 83 % der Varianten mit positivem Sharpe vor dem Testzeitraum
- **Erstellt:** 29.10.2026 01:25

## Einordnung: ❌ hält nicht stand: Deflated Sharpe ≤ 0,95 (Glück nicht auszuschließen); PBO ≥ 0,5 (Auswahl nicht besser als Zufall)

- **Sharpe Entwicklung → Test:** 0,32 → 0,41 (+25 %) · Kaufen-und-Halten im Test: -0,07
- **Deflated Sharpe** (Entwicklungsdaten, 12 Versuche berücksichtigt): 0,64 – Wahrscheinlichkeit, dass der echte Sharpe über 0 liegt (Ziel > 0,95)
- **PBO** (Entwicklungsdaten, 8 Blöcke): 0,90 – Anteil der Aufteilungen, in denen die beste Variante danach unter dem Median lag (Ziel < 0,5)

## Ergebnisse nach Kosten

| Zeitraum | Jahre | Rendite p. a. | Sharpe | Sortino | Max Drawdown | Calmar | Volatilität | Investiert |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Entwicklung (Parameterwahl) | 2003–2017 | +0,8 % | 0,32 | 0,42 | -7,9 % | 0,11 | +2,7 % | +1 % |
| **Test (nie zur Wahl genutzt)** | 2018–2026 | +0,4 % | 0,41 | 0,76 | -1,1 % | 0,34 | +0,9 % | +1 % |
| Kaufen-und-Halten im Test | 2018–2026 | -0,8 % | -0,07 | -0,10 | -23,3 % | -0,03 | +7,1 % | – |
| Walk-Forward (jährlich neu gewählt) | 2008–2026 | +0,8 % | 0,24 | 0,32 | -8,9 % | 0,09 | +3,6 % | – |

## Risiko im Testzeitraum

Schiefe 7,70 · Kurtosis (Überschuss) 284,1 · Trefferquote 69 % · Gewinn/Verlust-Verhältnis 1,02 · VaR 95 % (1 Tag) +0,00 % · Expected Shortfall 95 % -0,00 % · Turnover 3,5 Wechsel p. a. · Beta -0,00 · Alpha p. a. +0,4 % · Korrelation an den 10 % schlechtesten Markttagen -0,08

## Stresstests (gewählte Parameter, Gesamtrendite in der Phase)

| Phase | Strategie | Kaufen-und-Halten |
|---|---:|---:|
| Dotcom-Crash 2000–2002 | – | – |
| Finanzkrise 2007–2009 | -4,9 % | -10,2 % |
| Corona-Crash 2020 | +0,0 % | -1,3 % |
| Zinswende 2022 | +1,3 % | -5,9 % |

## Walk-Forward: gewählte Variante je Jahr

2008: {"halten": 1, "schwelle": 1.0}, 2009: {"halten": 20, "schwelle": 1.0}, 2010: {"halten": 20, "schwelle": 1.0}, 2011: {"halten": 20, "schwelle": 1.0}, 2012: {"halten": 20, "schwelle": 1.0}, 2013: {"halten": 20, "schwelle": 1.0}, 2014: {"halten": 1, "schwelle": 1.0}, 2015: {"halten": 1, "schwelle": 1.0}, 2016: {"halten": 1, "schwelle": 1.0}, 2017: {"halten": 1, "schwelle": 1.0}, 2018: {"halten": 1, "schwelle": 1.0}, 2019: {"halten": 1, "schwelle": 1.0}, 2020: {"halten": 1, "schwelle": 1.0}, 2021: {"halten": 1, "schwelle": 1.0}, 2022: {"halten": 1, "schwelle": 1.0}, 2023: {"halten": 1, "schwelle": 1.0}, 2024: {"halten": 1, "schwelle": 1.0}, 2025: {"halten": 1, "schwelle": 1.0}, 2026: {"halten": 1, "schwelle": 1.0}

## Hinweise

- EUR/USD: 1 Datenlücke(n) über 10 Tage.
- Signal aus Schlusskursen bis Tag t, Ertrag ab Tag t+1; Ereignisse ab Schluss des Reaktionstags. Keine Zinsen auf Cash, keine Steuern, Slippage nur über die Kostenannahme.
- Yahoo: Kurse bereinigt um Splits/Dividenden; Futures ohne Roll-Bereinigung; delistete Werte fehlen.
- Stresstests nur, soweit die Strategie in der Phase Daten hat. Vergangene Ergebnisse sind keine Vorhersage und keine Empfehlung.
