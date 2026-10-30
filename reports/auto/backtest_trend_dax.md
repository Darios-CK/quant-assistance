# Backtest: Trendfolge DAX

> Begründung: Märkte laufen in Trends, weil Anleger Nachrichten langsam verarbeiten und Verluste spät begrenzen; außerhalb des Trends meidet die Regel lange Abwärtsphasen.

- **Markt:** DAX · **Regel:** trend (nur long) · **Kosten:** 5,0 Bp je Positionswechsel
- **Gewählte Parameter:** {"schnell": 50, "langsam": 150} – ausgewählt nur auf Daten vor 01.01.2017
- **Getestete Varianten:** 9 in diesem Lauf, 9 insgesamt für dax/trend (Versuchsprotokoll) · 100 % der Varianten mit positivem Sharpe vor dem Testzeitraum
- **Erstellt:** 30.10.2026 11:30

## Einordnung: ✅ hält der Prüfung stand, schlägt Kaufen-und-Halten aber nicht

- **Sharpe Entwicklung → Test:** 0,71 → 0,21 (-71 %) · Kaufen-und-Halten im Test: 0,54
- **Deflated Sharpe** (Entwicklungsdaten, 9 Versuche berücksichtigt): 1,00 – Wahrscheinlichkeit, dass der echte Sharpe über 0 liegt (Ziel > 0,95)
- **PBO** (Entwicklungsdaten, 8 Blöcke): 0,09 – Anteil der Aufteilungen, in denen die beste Variante danach unter dem Median lag (Ziel < 0,5)

## Ergebnisse nach Kosten

| Zeitraum | Jahre | Rendite p. a. | Sharpe | Sortino | Max Drawdown | Calmar | Volatilität | Investiert |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Entwicklung (Parameterwahl) | 1988–2016 | +9,9 % | 0,71 | 1,00 | -29,0 % | 0,34 | +14,9 % | +66 % |
| **Test (nie zur Wahl genutzt)** | 2017–2026 | +1,9 % | 0,21 | 0,27 | -46,3 % | 0,04 | +13,9 % | +72 % |
| Kaufen-und-Halten im Test | 2017–2026 | +8,6 % | 0,54 | 0,76 | -38,8 % | 0,22 | +18,2 % | – |
| Walk-Forward (jährlich neu gewählt) | 1993–2026 | +7,5 % | 0,57 | 0,78 | -46,3 % | 0,16 | +14,7 % | – |

## Risiko im Testzeitraum

Schiefe -1,96 · Kurtosis (Überschuss) 22,1 · Trefferquote 53 % · Gewinn/Verlust-Verhältnis 0,92 · VaR 95 % (1 Tag) -1,35 % · Expected Shortfall 95 % -2,29 % · Turnover 1,8 Wechsel p. a. · Beta 0,59 · Alpha p. a. -2,9 % · Korrelation an den 10 % schlechtesten Markttagen 0,66

## Stresstests (gewählte Parameter, Gesamtrendite in der Phase)

| Phase | Strategie | Kaufen-und-Halten |
|---|---:|---:|
| Dotcom-Crash 2000–2002 | -18,6 % | -66,2 % |
| Finanzkrise 2007–2009 | -15,2 % | -53,7 % |
| Corona-Crash 2020 | -38,3 % | -36,1 % |
| Zinswende 2022 | -4,7 % | -12,3 % |

## Walk-Forward: gewählte Variante je Jahr

1993: {"schnell": 50, "langsam": 150}, 1994: {"schnell": 50, "langsam": 150}, 1995: {"schnell": 50, "langsam": 150}, 1996: {"schnell": 50, "langsam": 150}, 1997: {"schnell": 50, "langsam": 150}, 1998: {"schnell": 50, "langsam": 150}, 1999: {"schnell": 20, "langsam": 150}, 2000: {"schnell": 50, "langsam": 150}, 2001: {"schnell": 50, "langsam": 150}, 2002: {"schnell": 50, "langsam": 150}, 2003: {"schnell": 50, "langsam": 150}, 2004: {"schnell": 50, "langsam": 150}, 2005: {"schnell": 50, "langsam": 150}, 2006: {"schnell": 50, "langsam": 150}, 2007: {"schnell": 50, "langsam": 150}, 2008: {"schnell": 50, "langsam": 150}, 2009: {"schnell": 50, "langsam": 150}, 2010: {"schnell": 50, "langsam": 150}, 2011: {"schnell": 50, "langsam": 150}, 2012: {"schnell": 50, "langsam": 150}, 2013: {"schnell": 50, "langsam": 150}, 2014: {"schnell": 50, "langsam": 150}, 2015: {"schnell": 50, "langsam": 150}, 2016: {"schnell": 50, "langsam": 150}, 2017: {"schnell": 50, "langsam": 150}, 2018: {"schnell": 50, "langsam": 150}, 2019: {"schnell": 50, "langsam": 150}, 2020: {"schnell": 50, "langsam": 150}, 2021: {"schnell": 20, "langsam": 200}, 2022: {"schnell": 50, "langsam": 150}, 2023: {"schnell": 50, "langsam": 150}, 2024: {"schnell": 50, "langsam": 150}, 2025: {"schnell": 50, "langsam": 150}, 2026: {"schnell": 20, "langsam": 200}

## Hinweise

- Signal aus Schlusskursen bis Tag t, Ertrag ab Tag t+1; Ereignisse ab Schluss des Reaktionstags. Keine Zinsen auf Cash, keine Steuern, Slippage nur über die Kostenannahme.
- Yahoo: Kurse bereinigt um Splits/Dividenden; Futures ohne Roll-Bereinigung; delistete Werte fehlen.
- Stresstests nur, soweit die Strategie in der Phase Daten hat. Vergangene Ergebnisse sind keine Vorhersage und keine Empfehlung.
