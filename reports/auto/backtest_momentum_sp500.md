# Backtest: Zeitreihen-Momentum S&P 500

> Begründung: Time-Series-Momentum (Moskowitz, Ooi, Pedersen 2012): die Rendite der letzten 6–12 Monate sagt etwas über den nächsten Monat; den letzten Monat auszulassen umgeht die kurzfristige Umkehr.

- **Markt:** S&P 500 · **Regel:** momentum (nur long) · **Kosten:** 3,0 Bp je Positionswechsel
- **Gewählte Parameter:** {"lookback": 126, "skip": 0} – ausgewählt nur auf Daten vor 01.01.2015
- **Getestete Varianten:** 4 in diesem Lauf, 4 insgesamt für sp500/momentum (Versuchsprotokoll) · 100 % der Varianten mit positivem Sharpe vor dem Testzeitraum
- **Erstellt:** 28.10.2026 20:42

## Einordnung: ❌ hält nicht stand: PBO ≥ 0,5 (Auswahl nicht besser als Zufall)

- **Sharpe Entwicklung → Test:** 0,51 → 0,65 (+27 %) · Kaufen-und-Halten im Test: 0,73
- **Deflated Sharpe** (Entwicklungsdaten, 4 Versuche berücksichtigt): 1,00 – Wahrscheinlichkeit, dass der echte Sharpe über 0 liegt (Ziel > 0,95)
- **PBO** (Entwicklungsdaten, 8 Blöcke): 0,54 – Anteil der Aufteilungen, in denen die beste Variante danach unter dem Median lag (Ziel < 0,5)

## Ergebnisse nach Kosten

| Zeitraum | Jahre | Rendite p. a. | Sharpe | Sortino | Max Drawdown | Calmar | Volatilität | Investiert |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Entwicklung (Parameterwahl) | 1928–2014 | +5,7 % | 0,51 | 0,71 | -72,4 % | 0,08 | +12,2 % | +65 % |
| **Test (nie zur Wahl genutzt)** | 2015–2026 | +7,2 % | 0,65 | 0,89 | -19,0 % | 0,38 | +11,6 % | +78 % |
| Kaufen-und-Halten im Test | 2015–2026 | +11,9 % | 0,73 | 1,02 | -33,9 % | 0,35 | +17,6 % | – |
| Walk-Forward (jährlich neu gewählt) | 1933–2026 | +6,1 % | 0,57 | 0,79 | -44,0 % | 0,14 | +11,7 % | – |

## Risiko im Testzeitraum

Schiefe -0,76 · Kurtosis (Überschuss) 5,7 · Trefferquote 54 % · Gewinn/Verlust-Verhältnis 0,97 · VaR 95 % (1 Tag) -1,22 % · Expected Shortfall 95 % -1,91 % · Turnover 7,8 Wechsel p. a. · Beta 0,43 · Alpha p. a. +2,1 % · Korrelation an den 10 % schlechtesten Markttagen 0,05

## Stresstests (gewählte Parameter, Gesamtrendite in der Phase)

| Phase | Strategie | Kaufen-und-Halten |
|---|---:|---:|
| Dotcom-Crash 2000–2002 | -19,6 % | -49,1 % |
| Finanzkrise 2007–2009 | -8,6 % | -56,4 % |
| Corona-Crash 2020 | -11,8 % | -33,6 % |
| Zinswende 2022 | -14,5 % | -19,4 % |

## Walk-Forward: gewählte Variante je Jahr

1933: {"lookback": 126, "skip": 21}, 1934: {"lookback": 252, "skip": 0}, 1935: {"lookback": 252, "skip": 0}, 1936: {"lookback": 252, "skip": 0}, 1937: {"lookback": 252, "skip": 0}, 1938: {"lookback": 252, "skip": 0}, 1939: {"lookback": 252, "skip": 0}, 1940: {"lookback": 252, "skip": 0}, 1941: {"lookback": 252, "skip": 0}, 1942: {"lookback": 252, "skip": 0}, 1943: {"lookback": 252, "skip": 0}, 1944: {"lookback": 252, "skip": 0}, 1945: {"lookback": 252, "skip": 0}, 1946: {"lookback": 252, "skip": 0}, 1947: {"lookback": 252, "skip": 0}, 1948: {"lookback": 252, "skip": 0}, 1949: {"lookback": 252, "skip": 0}, 1950: {"lookback": 252, "skip": 0}, 1951: {"lookback": 252, "skip": 0}, 1952: {"lookback": 252, "skip": 0}, 1953: {"lookback": 252, "skip": 0}, 1954: {"lookback": 252, "skip": 0}, 1955: {"lookback": 252, "skip": 0}, 1956: {"lookback": 252, "skip": 0}, 1957: {"lookback": 252, "skip": 0}, 1958: {"lookback": 252, "skip": 0}, 1959: {"lookback": 252, "skip": 0}, 1960: {"lookback": 252, "skip": 0}, 1961: {"lookback": 252, "skip": 0}, 1962: {"lookback": 252, "skip": 0}, 1963: {"lookback": 252, "skip": 0}, 1964: {"lookback": 252, "skip": 0}, 1965: {"lookback": 252, "skip": 0}, 1966: {"lookback": 252, "skip": 0}, 1967: {"lookback": 252, "skip": 0}, 1968: {"lookback": 252, "skip": 0}, 1969: {"lookback": 252, "skip": 0}, 1970: {"lookback": 252, "skip": 0}, 1971: {"lookback": 126, "skip": 0}, 1972: {"lookback": 126, "skip": 0}, 1973: {"lookback": 126, "skip": 0}, 1974: {"lookback": 126, "skip": 0}, 1975: {"lookback": 126, "skip": 0}, 1976: {"lookback": 126, "skip": 0}, 1977: {"lookback": 126, "skip": 0}, 1978: {"lookback": 126, "skip": 0}, 1979: {"lookback": 126, "skip": 0}, 1980: {"lookback": 126, "skip": 0}, 1981: {"lookback": 126, "skip": 0}, 1982: {"lookback": 126, "skip": 0}, 1983: {"lookback": 126, "skip": 0}, 1984: {"lookback": 126, "skip": 0}, 1985: {"lookback": 126, "skip": 0}, 1986: {"lookback": 126, "skip": 0}, 1987: {"lookback": 126, "skip": 0}, 1988: {"lookback": 126, "skip": 0}, 1989: {"lookback": 126, "skip": 0}, 1990: {"lookback": 126, "skip": 0}, 1991: {"lookback": 126, "skip": 0}, 1992: {"lookback": 126, "skip": 0}, 1993: {"lookback": 126, "skip": 0}, 1994: {"lookback": 126, "skip": 0}, 1995: {"lookback": 126, "skip": 0}, 1996: {"lookback": 126, "skip": 0}, 1997: {"lookback": 126, "skip": 0}, 1998: {"lookback": 126, "skip": 0}, 1999: {"lookback": 126, "skip": 0}, 2000: {"lookback": 126, "skip": 0}, 2001: {"lookback": 126, "skip": 0}, 2002: {"lookback": 126, "skip": 0}, 2003: {"lookback": 126, "skip": 0}, 2004: {"lookback": 126, "skip": 0}, 2005: {"lookback": 126, "skip": 0}, 2006: {"lookback": 126, "skip": 0}, 2007: {"lookback": 126, "skip": 0}, 2008: {"lookback": 126, "skip": 0}, 2009: {"lookback": 126, "skip": 0}, 2010: {"lookback": 126, "skip": 0}, 2011: {"lookback": 126, "skip": 0}, 2012: {"lookback": 126, "skip": 0}, 2013: {"lookback": 126, "skip": 0}, 2014: {"lookback": 126, "skip": 0}, 2015: {"lookback": 126, "skip": 0}, 2016: {"lookback": 126, "skip": 0}, 2017: {"lookback": 126, "skip": 0}, 2018: {"lookback": 126, "skip": 0}, 2019: {"lookback": 126, "skip": 0}, 2020: {"lookback": 126, "skip": 0}, 2021: {"lookback": 126, "skip": 0}, 2022: {"lookback": 126, "skip": 0}, 2023: {"lookback": 126, "skip": 0}, 2024: {"lookback": 126, "skip": 0}, 2025: {"lookback": 126, "skip": 0}, 2026: {"lookback": 126, "skip": 0}

## Hinweise

- S&P 500: 1 Datenlücke(n) über 10 Tage.
- Signal aus Schlusskursen bis Tag t, Ertrag ab Tag t+1; Ereignisse ab Schluss des Reaktionstags. Keine Zinsen auf Cash, keine Steuern, Slippage nur über die Kostenannahme.
- Yahoo: Kurse bereinigt um Splits/Dividenden; Futures ohne Roll-Bereinigung; delistete Werte fehlen.
- Stresstests nur, soweit die Strategie in der Phase Daten hat. Vergangene Ergebnisse sind keine Vorhersage und keine Empfehlung.
