---
description: Ereignis-Analyse – wie reagierten Märkte auf EZB, Fed oder Konjunkturdaten?
argument-hint: Frage in Worten, z. B. "Vonovia nach harten EZB-Überraschungen seit 2015"
---

Beantworte diese Frage mit dem Quant-Analysten in diesem Projekt: $ARGUMENTS

1. Übersetze die Frage in einen oder mehrere Aufrufe von `.venv/bin/python -m qa ereignis …`
   (Quelle ezb | fed | fred:<Reihe>, passende `--maerkte`, `--von/--bis`, `--art`). Kürzel: `.venv/bin/python -m qa maerkte`.
   Fehlt ein Markt in den Kürzeln, nimm das Yahoo-Symbol (z. B. SAP.DE) oder FRED:<Reihe> für Zinsreihen.
2. Führe die Aufrufe aus und lies die Berichte in `reports/`.
3. Prüfe wichtige Ergebnisse zusätzlich in Teilzeiträumen (z. B. vor/nach 2014), damit ein Muster nicht nur aus einer Phase stammt.
4. Antworte auf Deutsch, kurz:
   - was gemessen wurde (Ereignis, Überraschungsmaß, Zeitraum, Fallzahl),
   - die Ergebnisse mit Zahlen **nur aus den Berichten**, jeweils mit Fällen und Einordnung (belastbar / Tendenz / kein Muster),
   - die wichtigsten Grenzen (Tagesdaten, Yahoo, kein Konsens …),
   - wie viele Varianten du insgesamt gerechnet hast,
   - Pfad zu den Berichten.
Keine Kauf- oder Verkaufsempfehlung.
