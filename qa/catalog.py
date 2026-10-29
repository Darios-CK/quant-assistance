"""Which market drivers can be analysed with free data – and how.  Shown in the app and given to the AI chat.

Status:  ✅ ready  ·  ✅🔑 ready with the free FRED key  ·  🟡 partly / via a stand-in or own date list
         🔜 free source exists, not built yet  ·  ❌ no free data (licensed, or a one-off event without statistics)
"""

from __future__ import annotations

CATALOG = [
    # (area, driver, status, how / source, note)
    ("Makro", "Zinsentscheidungen", "✅", "ezb · fed", "Überraschung aus Marktbewegung direkt um die Bekanntgabe; Fed-Daten bis 2023"),
    ("Makro", "Inflation (CPI/PCE/PPI)", "✅🔑", "makro:cpi · makro:kerninflation · makro:pce · makro:ppi", "Erstveröffentlichung (ALFRED); ohne Konsens – Überraschung angenähert"),
    ("Makro", "Arbeitsmarktdaten", "✅🔑", "makro:nfp · makro:arbeitslosenquote · makro:erstantraege", ""),
    ("Makro", "BIP-Wachstum", "✅🔑", "makro:bip", "quartalsweise, wenige Fälle"),
    ("Makro", "PMI", "❌", "Ersatz: makro:industrieproduktion", "ISM- und S&P-Global-PMI sind lizenziert"),
    ("Makro", "Einzelhandelsumsätze", "✅🔑", "makro:einzelhandel", ""),
    ("Makro", "Verbrauchervertrauen", "✅🔑", "makro:verbrauchervertrauen", "Uni Michigan; vorläufige und endgültige Werte vermischt"),
    ("Makro", "Handelsbilanz", "✅🔑", "makro:handelsbilanz", ""),
    ("Makro", "Geldmengenwachstum", "✅🔑", "makro:geldmenge_m2", ""),
    ("Makro", "Notenbank-Statements", "✅", "ezb --mass ausblick · fed", "Pressekonferenz getrennt messbar; Reden 🔜"),
    ("Makro", "Zentralbank-Bilanzsummen (QE/QT)", "✅🔑", "makro:fed_bilanz", "EZB-Bilanz 🔜 (EZB-Datenportal)"),
    ("Makro", "Naturgas-/Öllagerberichte (EIA)", "🟡", "makro:oel_lager (🔑)", "Gaslager 🔜 (EIA, Schlüssel nötig)"),
    ("Unternehmen", "Quartalszahlen/Earnings", "✅", "earnings:<Ticker> · qa earnings A,B,C", "Konsens von Yahoo; einzeln oder über viele Firmen"),
    ("Unternehmen", "Gewinnwarnungen", "🔜", "SEC 8-K (gratis)", "nicht eindeutig zu klassifizieren; bis dahin termine:"),
    ("Unternehmen", "Guidance", "❌", "", "keine freien strukturierten Daten"),
    ("Unternehmen", "M&A", "🔜", "SEC 8-K Item 1.01/2.01 (gratis)", "bis dahin termine:"),
    ("Unternehmen", "Management-Wechsel", "🔜", "SEC 8-K Item 5.02 (gratis)", "bis dahin termine:"),
    ("Unternehmen", "Aktienrückkäufe/Dividenden", "🟡", "dividende:<Ticker>", "Dividenden ✅; Rückkäufe 🔜 (SEC-Berichte)"),
    ("Unternehmen", "Produktankündigungen", "🟡", "termine:<Daten>", "keine Datenquelle – eigene Datumsliste"),
    ("Unternehmen", "Skandale", "🟡", "termine:<Daten>", "GDELT-Nachrichtenvolumen 🔜"),
    ("Unternehmen", "Aktiensplits", "✅", "split:<Ticker>", "wenige Fälle je Firma"),
    ("Unternehmen", "IPOs", "🔜", "SEC S-1/424B (gratis)", ""),
    ("Unternehmen", "Lock-up-Ablauf", "🟡", "termine:<IPO-Datum + 180 Tage>", ""),
    ("Unternehmen", "Insiderhandel", "🔜", "SEC Form 4 (gratis)", "nächste Ausbaustufe"),
    ("Unternehmen", "Aktionärsversammlungen/Abstimmungen", "🟡", "termine:<Daten>", "keine freie Terminhistorie"),
    ("Unternehmen", "Blackout-Perioden vor Earnings", "🔜", "aus earnings-Terminen ableitbar", ""),
    ("Unternehmen", "Rating-Entscheidungen", "🟡", "termine:<Daten>", "Agenturdaten lizenziert"),
    ("Politik & Welt", "Wahlen/Regierungswechsel", "✅", "wahl:us · wahl:us_zwischenwahl · wahl:de", "nur 6–7 Fälle je Wahl-Art"),
    ("Politik & Welt", "Kriege/Konflikte", "🟡", "termine:<Daten> · kurs:CL=F / GC=F / ^VIX als Stellvertreter", "meist Einzelereignisse"),
    ("Politik & Welt", "Sanktionen", "🟡", "termine:<Daten>", "GDELT 🔜"),
    ("Politik & Welt", "Handelskriege/Zölle", "🟡", "termine:<Daten>", ""),
    ("Politik & Welt", "Regulatorische Änderungen", "🟡", "termine:<Daten>", ""),
    ("Politik & Welt", "Branchenregulierung", "🟡", "termine:<Daten>", ""),
    ("Politik & Welt", "Staatsschulden-Rating", "🟡", "termine:<Daten>", "z. B. US-Herabstufungen 2011, 2023"),
    ("Politik & Welt", "Wetterereignisse", "🟡", "kurs:NG=F (Gaspreis-Schocks)", "NOAA-Daten 🔜"),
    ("Politik & Welt", "Naturkatastrophen", "🟡", "termine:<Daten>", "USGS/GDACS 🔜"),
    ("Politik & Welt", "Pandemien", "❌", "", "Einzelereignis (2020) – Fallstudie, keine Statistik"),
    ("Politik & Welt", "Black-Swan-Ereignisse", "🟡", "kurs:^GSPC --richtung runter --schwelle 4", "extreme Tage als Stellvertreter"),
    ("Marktstruktur", "Angebot und Nachfrage", "🟡", "kurs:<Symbol>", "Handelsvolumen 🔜"),
    ("Marktstruktur", "Liquidität", "🟡", "Phase kreditstress · makro:fed_bilanz", ""),
    ("Marktstruktur", "Positionierung großer Marktteilnehmer", "🔜", "CFTC Commitments of Traders (gratis)", ""),
    ("Marktstruktur", "Optionsverfall", "✅", "kalender:optionsverfall · kalender:hexensabbat", ""),
    ("Marktstruktur", "Technische Marken", "✅", "technik:<Symbol>:sma200_hoch|sma200_runter|hoch52|tief52", ""),
    ("Marktstruktur", "Marktsentiment/VIX", "✅", "kurs:^VIX · Phasen vix_hoch / vix_niedrig", ""),
    ("Marktstruktur", "Short Squeezes", "🔜", "FINRA Short Interest (gratis) + kurs:", ""),
    ("Marktstruktur", "Algorithmic/HFT-Trading", "❌", "", "braucht Tick- und Orderbuchdaten"),
    ("Marktstruktur", "Index-Aufnahme/-Ausschluss", "🔜", "Änderungslisten S&P 500 (gratis, lückenhaft)", ""),
    ("Marktstruktur", "Index-Rebalancing", "✅", "kalender:hexensabbat", "Quartals-Rebalancing am großen Verfall"),
    ("Marktstruktur", "ETF-Zu-/Abflüsse", "❌", "", "Flussdaten lizenziert"),
    ("Marktstruktur", "Gamma-/Dealer-Hedging", "❌", "", "historische Optionsdaten nicht gratis"),
    ("Marktstruktur", "Dark-Pool-Aktivität", "🔜", "FINRA ATS (gratis, wöchentlich, verzögert)", ""),
    ("Marktstruktur", "13F-Filings", "🔜", "SEC 13F (gratis)", "quartalsweise, 45 Tage verzögert"),
    ("Marktstruktur", "Pensionsfonds-Rebalancing", "🟡", "kalender:monatsende", "Quartalsende als Teilmenge"),
    ("Märkte", "Zinsstrukturkurve", "✅", "Phasen zinskurve_invers / zinskurve_normal · FRED:T10Y2Y", ""),
    ("Märkte", "Anleihemarkt-Bewegungen", "✅", "kurs:FRED:DGS10 · Märkte us2y, us10y, bund2j, bund10j", ""),
    ("Märkte", "Kreditspreads", "✅", "Phase kreditstress · kurs:FRED:BAA10Y", ""),
    ("Märkte", "Währungsbewegungen (FX)", "✅", "kurs:EURUSD=X · Märkte eurusd, usdjpy, dollar …", ""),
    ("Märkte", "Rohstoffpreise", "✅", "kurs:CL=F · GC=F · NG=F · HG=F", "Futures ohne Roll-Bereinigung"),
    ("Märkte", "Rohstoff-Angebotsschocks", "🟡", "kurs:CL=F --richtung hoch", "Angebots- und Nachfrageschock nicht getrennt"),
    ("Märkte", "Kryptomarkt-Korrelation", "✅", "kurs:BTC-USD · Markt bitcoin", ""),
    ("Märkte", "Saisonalität", "✅", "kalender:januar · santa · monatsanfang · montag … freitag", ""),
    ("Sentiment & Social", "Reddit/Stocktwits", "🔜", "Reddit (gratis, begrenzt)", "Stocktwits ❌"),
    ("Sentiment & Social", "Twitter/X", "❌", "", "X-API kostenpflichtig"),
    ("Sentiment & Social", "Finfluencer", "❌", "", "keine Datenquelle"),
    ("Sentiment & Social", "Meme-Stock-Trends", "🟡", "kurs:<Symbol> (Schocks)", "Reddit/Wikipedia-Aufrufe 🔜"),
    ("Sentiment & Social", "Sentiment-Analyse-Tools", "🔜", "GDELT-Nachrichtenton (gratis)", ""),
    ("Sentiment & Social", "Fake News", "❌", "", "nicht automatisch erkennbar"),
    ("Sentiment & Social", "CEO-/Politiker-Posts", "🟡", "termine:<Daten>", "X-API kostenpflichtig"),
    ("Sentiment & Social", "Google-Suchtrends", "🔜", "Google Trends (inoffiziell)", ""),
    ("Sentiment & Social", "Koordinierte Short-Squeeze-Aktionen", "🟡", "termine:<Daten>", ""),
    ("Sentiment & Social", "Analysten-Up-/Downgrades", "❌", "", "Historie nicht gratis"),
]


def as_markdown() -> str:
    counts = {s: sum(1 for r in CATALOG if r[2] == s) for s in ("✅", "✅🔑", "🟡", "🔜", "❌")}
    lines = ["# Abdeckung: welche Markttreiber analysiert werden können", "",
             f"✅ fertig: {counts['✅']} · ✅🔑 fertig mit kostenlosem FRED-Schlüssel: {counts['✅🔑']} · 🟡 teilweise / eigene Datumsliste: {counts['🟡']} · "
             f"🔜 gratis möglich, noch nicht gebaut: {counts['🔜']} · ❌ gratis nicht machbar: {counts['❌']}", ""]
    area = None
    for a, driver, status, how, note in CATALOG:
        if a != area:
            lines += ["", f"## {a}", "", "| Treiber | Stand | So geht es | Hinweis |", "|---|---|---|---|"]
            area = a
        lines.append(f"| {driver} | {status} | {f'`{how}`' if how else '–'} | {note or ''} |")
    lines += ["", "Kombinationen: jede Ereignis-Analyse mit `--bedingung <Phase>` (z. B. vix_hoch, trend_ab, zinskurve_invers, kreditstress) "
              "und `--zusammen-mit <Quelle>` / `--ohne <Quelle>` (±`--fenster` Tage)."]
    return "\n".join(lines) + "\n"
