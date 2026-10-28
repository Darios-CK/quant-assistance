# Quant-Analyst

Ereignis-Analysen auf kostenlosen Daten: **Wie haben Märkte in der Vergangenheit auf EZB-, Fed- oder Konjunktur-Überraschungen reagiert?** Nur für den Eigengebrauch.

## Einrichten

```bash
cd ~/quant-analyst
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # nur für Konjunkturdaten: kostenlosen FRED-Schlüssel eintragen
```

## Benutzen

```bash
.venv/bin/python -m qa ereignis ezb                              # EZB-Sitzungen seit 1999
.venv/bin/python -m qa ereignis ezb --art info-schock            # nur Sitzungen, bei denen die EZB "Konjunktur-News" lieferte
.venv/bin/python -m qa ereignis ezb --von 2014 --bis 2022        # nur Negativzins-Zeit
.venv/bin/python -m qa ereignis fed --maerkte sp500,dax,us2y     # Fed-Sitzungen seit 1988
.venv/bin/python -m qa ereignis fred:PPIFIS                      # Erzeugerpreise (braucht FRED-Schlüssel)
.venv/bin/python -m qa maerkte                                   # alle Kürzel für Märkte
```

```bash
.venv/bin/python -m qa ereignis kurs:CL=F --richtung hoch        # Tage mit Öl-Schock nach oben (≥ 2 Standardabweichungen)
.venv/bin/python -m qa earnings NVDA --maerkte AMD,TSM,bitcoin   # wer reagiert auf Nvidias Quartalszahlen?
.venv/bin/python -m qa earnings AAPL,MSFT,GOOGL,AMZN             # Muster über viele Firmen und Jahre
.venv/bin/python -m qa kette chains/oel_transport.json           # Kausalkette Glied für Glied prüfen
```

In Claude Code geht es auch in Worten:
- `/kette Ölpreis steigt stark` – die KI denkt die Kettenreaktion über mehrere Ebenen durch und lässt jedes Glied messen
- `/ereignis Wie reagieren Vonovia und Banken auf EZB-Überraschungen seit 2015?`

Was schon umgesetzt ist und was noch kommt: [docs/ROADMAP.md](docs/ROADMAP.md).

## Weboberfläche

```bash
.venv/bin/streamlit run app.py      # öffnet http://localhost:8501
```

Bereiche: automatische Berichte lesen, Ereignis-Analyse, Kette prüfen, Quartalszahlen.

## Betrieb ohne eigenen Rechner (kostenlos)

| Teil | Dienst | Kosten |
|---|---|---|
| Tägliche Berichte (`routine.json` → `reports/auto/`) | GitHub Actions, Workflow `.github/workflows/routine.yml`, Mo–Fr 05:30 UTC | privates Repository: im Gratis-Kontingent (2.000 Min./Monat) |
| Weboberfläche | Streamlit Community Cloud, Hauptdatei `app.py` | 1 private App gratis, schläft nach Inaktivität ein |

Einrichten:
1. Auf GitHub ein **privates** Repository `quant-analyst` anlegen und diesen Ordner hochladen (der Code bleibt privat, auch wenn die App öffentlich ist).
2. Repository → Settings → Secrets and variables → Actions → `FRED_API_KEY` eintragen.
3. Reiter „Actions“ → „Tägliche Berichte“ → „Run workflow“ für den ersten Lauf. Danach läuft er jeden Werktag selbst; die Übersicht steht in `reports/auto/README.md` (auch in der GitHub-App lesbar).
4. [share.streamlit.io](https://share.streamlit.io) → mit GitHub anmelden → „Create app“ → Repository `quant-analyst`, Branch `main`, Datei `app.py`, unter „Advanced settings“ Python 3.12 und die Secrets aus `.streamlit/secrets.example.toml` (FRED-Schlüssel, Impressum-Angaben). Öffentlich schalten: in der App oben rechts „Share“ → „Make this app public“. Hinweis: Yahoo erlaubt nur private Nutzung – öffentlich ist ein Testbetrieb auf eigenes Risiko.

Welche Analysen täglich laufen, steht in `routine.json` (Name, Titel, Befehl).

## Was die Tabelle bedeutet

| Spalte | Bedeutung |
|---|---|
| Je typ. Überraschung | Durchschnittliche Bewegung, wenn die Überraschung um eine typische Größe (1 Standardabweichung) höher war |
| Oberes / unteres Drittel | Ereignisse mit den größten / kleinsten Überraschungen: Ø Bewegung, Anteil steigend, Fälle |
| Normal | Durchschnittliche Bewegung über gleich viele Tage, ohne Ereignis |
| p / q | Wahrscheinlichkeit für Zufall; q ist korrigiert, weil viele Tests gleichzeitig laufen |
| Einordnung | belastbar (q < 0,10, ≥ 20 Fälle) · Tendenz (p < 0,10) · kein Muster · zu wenig Fälle |

## Datenquellen

| Daten | Quelle | Kosten |
|---|---|---|
| EZB-Überraschungen 1999–heute | [EA-MPD](https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx) (EZB) | frei |
| Fed-Überraschungen 1988–2023 | [Bauer & Swanson](https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/) (SF Fed) | frei |
| Konjunkturdaten als Erstveröffentlichung | [ALFRED](https://alfred.stlouisfed.org/) | frei (Schlüssel) |
| Tageskurse | Yahoo Finance über `yfinance`, US-Renditen über FRED | frei, nur privat |
| Bund-Renditen, EZB-Referenzkurse, Euro-Renditen | Bundesbank, EZB Data Portal | frei |
| Quartalszahlen mit Analysten-Konsens | Yahoo Finance (Gewinntermine) | frei, nur privat |

## Grenzen

Tagesschlusskurse (keine Minuten), Yahoo ohne von der Börse genommene Firmen, Futures ohne Roll-Bereinigung, bei Konjunkturdaten keine Analystenprognosen (die Überraschung wird angenähert). Vergangene Reaktionen sind keine Vorhersage.
