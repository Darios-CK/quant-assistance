# Backtest: Kurzfristige Umkehr S&P 500

> Begründung: Nach starken Verkäufen in wenigen Tagen erholen sich Indizes oft, weil Zwangsverkäufe und Überreaktionen nachlassen (Liquiditätsprämie).

- **Markt:** S&P 500 · **Regel:** umkehr (nur long) · **Kosten:** 3,0 Bp je Positionswechsel
- **Gewählte Parameter:** {"tage": 5, "schwelle": 2.0, "halten": 5} – ausgewählt nur auf Daten vor 01.01.2015
- **Getestete Varianten:** 8 in diesem Lauf, 8 insgesamt für sp500/umkehr (Versuchsprotokoll) · 100 % der Varianten mit positivem Sharpe vor dem Testzeitraum
- **Erstellt:** 29.10.2026 00:43

## Einordnung: ❌ hält nicht stand: Deflated Sharpe ≤ 0,95 (Glück nicht auszuschließen)

- **Sharpe Entwicklung → Test:** 0,22 → 0,07 (-70 %) · Kaufen-und-Halten im Test: 0,73
- **Deflated Sharpe** (Entwicklungsdaten, 8 Versuche berücksichtigt): 0,92 – Wahrscheinlichkeit, dass der echte Sharpe über 0 liegt (Ziel > 0,95)
- **PBO** (Entwicklungsdaten, 8 Blöcke): 0,26 – Anteil der Aufteilungen, in denen die beste Variante danach unter dem Median lag (Ziel < 0,5)

## Ergebnisse nach Kosten

| Zeitraum | Jahre | Rendite p. a. | Sharpe | Sortino | Max Drawdown | Calmar | Volatilität | Investiert |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Entwicklung (Parameterwahl) | 1928–2014 | +1,6 % | 0,22 | 0,32 | -42,3 % | 0,04 | +9,3 % | +9 % |
| **Test (nie zur Wahl genutzt)** | 2015–2026 | +0,1 % | 0,07 | 0,09 | -34,0 % | 0,00 | +10,6 % | +7 % |
| Kaufen-und-Halten im Test | 2015–2026 | +11,9 % | 0,73 | 1,02 | -33,9 % | 0,35 | +17,6 % | – |
| Walk-Forward (jährlich neu gewählt) | 1933–2026 | +1,2 % | 0,17 | 0,24 | -43,5 % | 0,03 | +9,8 % | – |

## Risiko im Testzeitraum

Schiefe -0,67 · Kurtosis (Überschuss) 110,3 · Trefferquote 53 % · Gewinn/Verlust-Verhältnis 0,95 · VaR 95 % (1 Tag) -0,00 % · Expected Shortfall 95 % -0,06 % · Turnover 4,7 Wechsel p. a. · Beta 0,36 · Alpha p. a. -3,9 % · Korrelation an den 10 % schlechtesten Markttagen 0,74

## Stresstests (gewählte Parameter, Gesamtrendite in der Phase)

| Phase | Strategie | Kaufen-und-Halten |
|---|---:|---:|
| Dotcom-Crash 2000–2002 | +37,4 % | -49,1 % |
| Finanzkrise 2007–2009 | +6,7 % | -56,4 % |
| Corona-Crash 2020 | -30,7 % | -33,6 % |
| Zinswende 2022 | +10,5 % | -19,4 % |

## Walk-Forward: gewählte Variante je Jahr

1933: {"tage": 3, "schwelle": 2.0, "halten": 10}, 1934: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1935: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1936: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1937: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1938: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1939: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1940: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1941: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1942: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1943: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1944: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1945: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1946: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1947: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1948: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1949: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1950: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1951: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1952: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1953: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1954: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1955: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1956: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1957: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1958: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1959: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1960: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1961: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1962: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1963: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1964: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1965: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1966: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1967: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1968: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1969: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1970: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1971: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1972: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1973: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1974: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1975: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1976: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1977: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1978: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1979: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1980: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1981: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1982: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1983: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1984: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1985: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1986: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1987: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1988: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1989: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1990: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1991: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1992: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1993: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1994: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1995: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1996: {"tage": 3, "schwelle": 1.5, "halten": 10}, 1997: {"tage": 3, "schwelle": 1.5, "halten": 10}, 1998: {"tage": 5, "schwelle": 2.0, "halten": 5}, 1999: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2000: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2001: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2002: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2003: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2004: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2005: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2006: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2007: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2008: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2009: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2010: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2011: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2012: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2013: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2014: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2015: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2016: {"tage": 5, "schwelle": 2.0, "halten": 5}, 2017: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2018: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2019: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2020: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2021: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2022: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2023: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2024: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2025: {"tage": 3, "schwelle": 1.5, "halten": 10}, 2026: {"tage": 3, "schwelle": 1.5, "halten": 10}

## Hinweise

- S&P 500: 1 Datenlücke(n) über 10 Tage.
- Signal aus Schlusskursen bis Tag t, Ertrag ab Tag t+1; Ereignisse ab Schluss des Reaktionstags. Keine Zinsen auf Cash, keine Steuern, Slippage nur über die Kostenannahme.
- Yahoo: Kurse bereinigt um Splits/Dividenden; Futures ohne Roll-Bereinigung; delistete Werte fehlen.
- Stresstests nur, soweit die Strategie in der Phase Daten hat. Vergangene Ergebnisse sind keine Vorhersage und keine Empfehlung.
