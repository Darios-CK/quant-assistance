"""Impressum and privacy policy for the public web app (German, same fields as PFMM's config/legal.toml).

Operator data comes from Streamlit secrets ([impressum], [privacy]) – locally .streamlit/secrets.toml, in the cloud
App settings → Secrets – so the address never lands in Git.  Missing fields are shown as visible gaps, never invented.
"""

from __future__ import annotations

FIELDS = {
    ("impressum", "name"): "Name",
    ("impressum", "street"): "Straße und Hausnummer",
    ("impressum", "city"): "PLZ und Ort",
    ("impressum", "country"): "Land",
    ("impressum", "email"): "E-Mail",
}


def _get(secrets, section: str, key: str) -> str:
    try:
        return str(secrets.get(section, {}).get(key, "") or "").strip()
    except Exception:
        return ""


def missing(secrets) -> list[str]:
    return [label for (sec, key), label in FIELDS.items() if not _get(secrets, sec, key)]


def _f(secrets, section: str, key: str, label: str) -> str:
    v = _get(secrets, section, key)
    return v if v else f"**[{label} – in den Secrets eintragen]**"


def impressum(secrets) -> str:
    f = lambda key, label: _f(secrets, "impressum", key, label)  # noqa: E731
    phone = _get(secrets, "impressum", "phone")
    return f"""# Impressum

## Angaben gemäß § 5 DDG
{f('name', 'Name')}
{f('street', 'Straße und Hausnummer')}
{f('city', 'PLZ und Ort')}
{f('country', 'Land')}

## Kontakt
E-Mail: {f('email', 'E-Mail')}{f"  {chr(10)}Telefon: {phone}" if phone else ""}

## Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV
{f('name', 'Name')}, Anschrift wie oben

## Hinweis zu den Inhalten
Quant Assistance ist ein Testbetrieb. Er zeigt, wie Märkte in der Vergangenheit auf Ereignisse reagiert haben – berechnet
aus frei zugänglichen Daten (Yahoo Finance, FRED/ALFRED, Bundesbank, EZB, Federal Reserve Bank of San Francisco).
Es handelt sich nicht um Anlageberatung, Anlagevermittlung oder eine Empfehlung zum Kauf oder Verkauf von
Finanzinstrumenten. Vergangene Reaktionen sind keine Vorhersage. Daten können verzögert, lückenhaft oder fehlerhaft sein.
Rechte an den Rohdaten liegen bei den jeweiligen Anbietern.
"""


def privacy(secrets) -> str:
    f = lambda key, label: _f(secrets, "impressum", key, label)  # noqa: E731
    authority = _f(secrets, "privacy", "supervisory_authority", "zuständige Datenschutz-Aufsichtsbehörde")
    return f"""# Datenschutzerklärung

## 1. Verantwortlicher
{f('name', 'Name')}, {f('street', 'Straße')}, {f('city', 'PLZ Ort')}, E-Mail: {f('email', 'E-Mail')}

## 2. Hosting
Diese Web-App läuft auf Streamlit Community Cloud, betrieben von Snowflake Inc. (USA). Beim Aufruf verarbeitet der
Anbieter technisch nötige Daten (u. a. IP-Adresse, Zeitpunkt, Browser), um die Seite auszuliefern und vor Missbrauch zu
schützen; dabei können Daten in die USA übermittelt werden. Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (sicherer
Betrieb). Einzelheiten: [Datenschutzhinweise von Streamlit](https://streamlit.io/privacy-policy) und
[Snowflake](https://www.snowflake.com/en/legal/privacy/privacy-policy/).

## 3. Was wir selbst verarbeiten
Es gibt keine Nutzerkonten und keine Analyse-, Werbe- oder Tracking-Werkzeuge; die Nutzungsstatistik von Streamlit ist
abgeschaltet. Der persönliche Bereich (Projekte, Copilot, Konto) ist nur für den Betreiber und passwortgeschützt; seine
Dateien liegen in einem privaten GitHub-Repository des Betreibers (GitHub Inc., USA). Was in der Community veröffentlicht
wird, ist öffentlich einsehbar. Was Sie in die Formulare eingeben (Ticker, Zeiträume), wird nur zum Rechnen der Analyse
verwendet und höchstens sechs Stunden zwischengespeichert, nicht Ihrer Person zugeordnet und nicht weitergegeben.
Für die Analysen ruft der Server Kursdaten bei den genannten Datenquellen ab; dabei werden keine Daten über Sie übermittelt.

## 4. Quant Copilot
Befehle im Copilot werden auf dem Server gerechnet, ohne Dritte. Nur wenn der Betreiber freie Fragen an die KI stellt,
werden diese zusammen mit den Analyse-Ergebnissen an Anthropic PBC (USA) übermittelt, die das Sprachmodell Claude
betreibt. Der Copilot ist passwortgeschützt und nur für den Betreiber. Rechtsgrundlage: Art. 6 Abs. 1
lit. f DSGVO. Einzelheiten: [Datenschutzhinweise von Anthropic](https://www.anthropic.com/legal/privacy).

## 5. Ihre Rechte
Sie haben das Recht auf Auskunft (Art. 15), Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung (Art. 18),
Datenübertragbarkeit (Art. 20) und Widerspruch (Art. 21 DSGVO). Sie können sich bei einer Datenschutz-Aufsichtsbehörde
beschweren, z. B. {authority}.
"""
