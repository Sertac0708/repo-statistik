#!/usr/bin/env python3
"""Sammelt GitHub-Zugriffszahlen für die Repos aus repos.txt und hebt sie dauerhaft auf.

GitHub zeigt Traffic (Aufrufe, Klone, Verweise) nur für die letzten 14 Tage. Dieses Werkzeug
holt die Tageswerte, verschmilzt sie nach Datum mit dem Bestand in daten/<repo>.json und
zeichnet je Repo eine Wochengrafik (grafik/<repo>.svg, hell und dunkel) und schreibt den
Zahlenblock zwischen den Markern <!-- statistik:start --> und <!-- statistik:end --> in
README.md (englisch) und README.de.md (deutsch) neu. Der übrige Text der READMEs bleibt
unberührt. Zum Schluss ein anonymer Heartbeat an den Autor (Install-ID, Version, Anzahl Repos,
ok), abschaltbar mit DO_NOT_TRACK=1. Läuft wöchentlich als GitHub Action, geht aber auch lokal:

    STATISTIK_TOKEN=$(gh auth token) python3 werkzeuge/sammeln.py

Nur Python-Standardbibliothek. Der Token kommt ausschließlich aus der Umgebung und wird
nirgends gespeichert oder ausgegeben.
"""

import json
import os
import re
import sys
import uuid
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
REPOS_DATEI = WURZEL / "repos.txt"
READMES = ((WURZEL / "README.md", "en"), (WURZEL / "README.de.md", "de"))
MARKER_START = "<!-- statistik:start -->"
MARKER_ENDE = "<!-- statistik:end -->"
VERSION = "1.1.0"
# Heartbeat-Empfänger (Code: heartbeat/server.py). Abschalten: DO_NOT_TRACK=1 oder STATISTIK_HEARTBEAT=aus.
HEARTBEAT_URL = "https://heartbeat-production-40b4.up.railway.app/ping"
INSTALL_ID_DATEI = DATEN / "install-id.txt"
GRAFIK = WURZEL / "grafik"
API = "https://api.github.com"
WOCHEN_IM_BERICHT = 8
WOCHEN_IN_GRAFIK = 16


def token() -> str:
    wert = os.environ.get("STATISTIK_TOKEN", "").strip()
    if not wert:
        sys.exit(
            "STATISTIK_TOKEN fehlt. Fein abgestuften Token anlegen (Administration: read, "
            "Metadata: read auf den Repos aus repos.txt) und als Secret STATISTIK_TOKEN hinterlegen."
        )
    return wert


def api(pfad: str, tok: str):
    anfrage = urllib.request.Request(
        API + pfad,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "repo-statistik",
        },
    )
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        return json.load(antwort)


def repos_lesen() -> list[str]:
    repos = []
    for zeile in REPOS_DATEI.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile and not zeile.startswith("#"):
            repos.append(zeile)
    if not repos:
        sys.exit("repos.txt enthält kein Repo.")
    return repos


def datei_fuer(repo: str) -> Path:
    return DATEN / (repo.split("/", 1)[1] + ".json")


def laden(repo: str) -> dict:
    pfad = datei_fuer(repo)
    if pfad.exists():
        return json.loads(pfad.read_text(encoding="utf-8"))
    return {
        "repo": repo,
        "aufzeichnung_seit": None,
        "aktualisiert": None,
        "tage": {},
        "verlauf": [],
        "verweise": {},
        "pfade": {},
    }


def speichern(repo: str, d: dict) -> None:
    DATEN.mkdir(exist_ok=True)
    datei_fuer(repo).write_text(
        json.dumps(d, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def sammeln(repo: str, tok: str, heute: str, jetzt: str) -> dict:
    d = laden(repo)
    meta = api(f"/repos/{repo}", tok)
    aufrufe = api(f"/repos/{repo}/traffic/views", tok)
    klone = api(f"/repos/{repo}/traffic/clones", tok)
    verweise = api(f"/repos/{repo}/traffic/popular/referrers", tok)
    pfade = api(f"/repos/{repo}/traffic/popular/paths", tok)

    # Tageswerte nach Datum verschmelzen. Der jüngste Tag kann beim nächsten Lauf noch
    # wachsen, deshalb gewinnt immer der neu geholte Wert.
    for eintrag in aufrufe.get("views", []):
        tag = d["tage"].setdefault(eintrag["timestamp"][:10], {})
        tag["aufrufe"] = eintrag["count"]
        tag["aufrufe_eindeutig"] = eintrag["uniques"]
    for eintrag in klone.get("clones", []):
        tag = d["tage"].setdefault(eintrag["timestamp"][:10], {})
        tag["klone"] = eintrag["count"]
        tag["klone_eindeutig"] = eintrag["uniques"]
    d["tage"] = dict(sorted(d["tage"].items()))

    # Momentaufnahme je Lauf: Sterne usw. plus die echten 14-Tage-Eindeutigkeitszahlen von GitHub.
    d["verlauf"] = [v for v in d["verlauf"] if v["datum"] != heute]
    d["verlauf"].append(
        {
            "datum": heute,
            "sterne": meta["stargazers_count"],
            "forks": meta["forks_count"],
            "beobachter": meta["subscribers_count"],
            "issues_offen": meta["open_issues_count"],
            "aufrufe_14t": aufrufe.get("count", 0),
            "aufrufe_eindeutig_14t": aufrufe.get("uniques", 0),
            "klone_14t": klone.get("count", 0),
            "klone_eindeutig_14t": klone.get("uniques", 0),
        }
    )
    d["verlauf"].sort(key=lambda v: v["datum"])
    d["verweise"][heute] = [
        {"quelle": v["referrer"], "aufrufe": v["count"], "eindeutig": v["uniques"]} for v in verweise
    ]
    d["pfade"][heute] = [
        {"pfad": p["path"], "aufrufe": p["count"], "eindeutig": p["uniques"]} for p in pfade
    ]
    # GitHub füllt das 14-Tage-Fenster mit Null-Tagen auf, auch vor dem Anlegedatum des Repos.
    erstellt = meta["created_at"][:10]
    d["erstellt"] = erstellt
    d["aufzeichnung_seit"] = d["aufzeichnung_seit"] or max(erstellt, min(d["tage"]) if d["tage"] else heute)
    d["aktualisiert"] = jetzt
    speichern(repo, d)
    return d


def wochen(d: dict) -> list[dict]:
    """Tageswerte zu Kalenderwochen (Montag bis Sonntag) aufsummieren, jüngste zuerst.

    Wochen, die ganz vor dem Aufzeichnungsbeginn liegen, fallen weg: GitHub füllt das
    14-Tage-Fenster mit Null-Tagen auf, auch für Zeiten, in denen das Repo noch nicht existierte.
    """
    seit = date.fromisoformat(d["aufzeichnung_seit"])
    summen: dict[date, dict] = {}
    for tag, werte in d["tage"].items():
        t = date.fromisoformat(tag)
        montag = t - timedelta(days=t.weekday())
        if montag + timedelta(days=6) < seit:
            continue
        w = summen.setdefault(montag, {"aufrufe": 0, "klone": 0, "tage": 0})
        w["aufrufe"] += werte.get("aufrufe", 0)
        w["klone"] += werte.get("klone", 0)
        w["tage"] += 1
    return [{"montag": m, **w} for m, w in sorted(summen.items(), reverse=True)]


# Farben nach der Diagramm-Richtlinie (dataviz-Skill), je Modus eigens gestuft und gegen
# GitHubs Seitenhintergrund geprüft (hell #ffffff, dunkel #0d1117): alle Prüfungen bestanden.
FARBEN = {
    "hell": {
        "text": "#0b0b0b", "text2": "#52514e", "muted": "#6b6a66",
        "raster": "#e6e5e1", "achse": "#c9c8c3", "klone": "#2a78d6", "aufrufe": "#eb6834",
    },
    "dunkel": {
        "text": "#ffffff", "text2": "#c3c2b7", "muted": "#8f8e86",
        "raster": "#2a2f36", "achse": "#3d434b", "klone": "#3987e5", "aufrufe": "#d95926",
    },
}
SCHRIFT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'


def _schritt(maximum: int) -> int:
    """Runde Achsenschritte, höchstens vier Rasterlinien."""
    for s in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000, 10000):
        if maximum / s <= 4:
            return s
    return 20000


def _tafel(reihe: list[dict], feld: str, titel: str, farbe: str, f: dict, y0: int) -> list[str]:
    """Eine Tafel: Säulen je Woche, Raster, Achsenwerte, Beschriftung der letzten und höchsten Säule."""
    links, rechts, oben, unten = 44, 16, 36, 24
    breite, hoehe = 720, 110
    plot_b = breite - links - rechts
    grund = y0 + oben + hoehe
    werte = [w[feld] for w in reihe]
    maximum = max(werte) if werte else 0
    schritt = _schritt(max(maximum, 1))
    decke = max(schritt, -(-maximum // schritt) * schritt)
    out = [f'<text x="{links}" y="{y0 + 16}" font-size="13" font-weight="600" fill="{f["text"]}">{titel}</text>']
    tick = 0
    while tick <= decke:
        y = grund - tick / decke * hoehe
        out.append(f'<line x1="{links}" x2="{breite - rechts}" y1="{y:.1f}" y2="{y:.1f}" '
                   f'stroke="{f["achse"] if tick == 0 else f["raster"]}" stroke-width="1"/>')
        out.append(f'<text x="{links - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end" '
                   f'fill="{f["muted"]}">{tick:,}</text>'.replace(",", "."))
        tick += schritt
    n = len(reihe)
    if n == 0:
        out.append(f'<text x="{links + plot_b / 2:.1f}" y="{grund - hoehe / 2:.1f}" font-size="12" '
                   f'text-anchor="middle" fill="{f["muted"]}">Noch keine Daten</text>')
        return out
    band = plot_b / n
    sb = min(24, band * 0.6)
    index_max = werte.index(maximum) if maximum > 0 else -1
    jede = 1 if n <= 8 else 2
    for i, w in enumerate(reihe):
        x = links + i * band + (band - sb) / 2
        v = w[feld]
        if v > 0:
            h = v / decke * hoehe
            r = min(4, sb / 2, h)
            y = grund - h
            out.append(
                f'<path fill="{farbe}" d="M{x:.1f},{grund} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
                f'H{x + sb - r:.1f} Q{x + sb:.1f},{y:.1f} {x + sb:.1f},{y + r:.1f} V{grund} Z"/>'
            )
            if i == n - 1 or i == index_max:
                out.append(f'<text x="{x + sb / 2:.1f}" y="{y - 5:.1f}" font-size="11" text-anchor="middle" '
                           f'fill="{f["text2"]}">{v:,}</text>'.replace(",", "."))
        if (n - 1 - i) % jede == 0:
            m = w["montag"]
            out.append(f'<text x="{x + sb / 2:.1f}" y="{grund + 16}" font-size="11" text-anchor="middle" '
                       f'fill="{f["muted"]}">{m.day:02d}.{m.month:02d}.</text>')
    return out


def svg_schreiben(d: dict) -> None:
    """Je Repo zwei Grafiken (hell/dunkel): Klone je Woche und Aufrufe je Woche, zwei Tafeln."""
    GRAFIK.mkdir(exist_ok=True)
    reihe = list(reversed(wochen(d)[:WOCHEN_IN_GRAFIK]))
    name = d["repo"].split("/", 1)[1]
    tafel_h = 36 + 110 + 24
    gesamt_h = 2 * tafel_h + 8
    for modus, f in FARBEN.items():
        teile = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{gesamt_h}" '
            f'viewBox="0 0 720 {gesamt_h}" role="img" font-family=\'{SCHRIFT}\'>',
            f'<title>Klone und Aufrufe je Woche für {d["repo"]}</title>',
        ]
        teile += _tafel(reihe, "klone", "Klone je Woche", f["klone"], f, 0)
        teile += _tafel(reihe, "aufrufe", "Aufrufe je Woche", f["aufrufe"], f, tafel_h + 8)
        teile.append("</svg>")
        datei = GRAFIK / (name + (".svg" if modus == "hell" else "-dunkel.svg"))
        datei.write_text("\n".join(teile) + "\n", encoding="utf-8")


TEXTE = {
    "de": {
        "stand": "Stand: {jetzt}. Dieser Block wird vom Werkzeug geschrieben, Änderungen von Hand gehen verloren.",
        "kopf": "Sterne {sterne} · Forks {forks} · Beobachter {beobachter} · offene Issues {issues}",
        "vierzehn": "Letzte 14 Tage laut GitHub: {klone} Klone von {klone_e} Rechnern, {aufrufe} Aufrufe von {aufrufe_e} Besuchern",
        "seit": "Seit Aufzeichnungsbeginn ({seit}): {klone} Klone, {aufrufe} Aufrufe",
        "alt": "Klone und Aufrufe je Woche für {name}",
        "tabelle": "| Woche ab | Klone | Aufrufe | Tage mit Daten |",
        "verweise": "Verweise (eindeutige Besucher, 14 Tage): {quellen}",
    },
    "en": {
        "stand": "As of {jetzt}. This block is written by the tool; manual edits will be overwritten.",
        "kopf": "Stars {sterne} · Forks {forks} · Watchers {beobachter} · open issues {issues}",
        "vierzehn": "Last 14 days per GitHub: {klone} clones from {klone_e} machines, {aufrufe} views from {aufrufe_e} visitors",
        "seit": "Since recording began ({seit}): {klone} clones, {aufrufe} views",
        "alt": "Clones and views per week for {name}",
        "tabelle": "| Week of | Clones | Views | Days with data |",
        "verweise": "Referrers (unique visitors, 14 days): {quellen}",
    },
}


def block(alle: list[dict], jetzt: str, sprache: str) -> str:
    """Der generierte Zahlenblock für eine README-Sprache."""
    t = TEXTE[sprache]
    zeilen = [t["stand"].format(jetzt=jetzt), ""]
    for d in alle:
        name = d["repo"].split("/", 1)[1]
        letzter = d["verlauf"][-1]
        gesamt_aufrufe = sum(x.get("aufrufe", 0) for x in d["tage"].values())
        gesamt_klone = sum(x.get("klone", 0) for x in d["tage"].values())
        zeilen += [
            f"### {d['repo']}",
            "",
            "- " + t["kopf"].format(sterne=letzter["sterne"], forks=letzter["forks"],
                                   beobachter=letzter["beobachter"], issues=letzter["issues_offen"]),
            "- " + t["vierzehn"].format(klone=letzter["klone_14t"], klone_e=letzter["klone_eindeutig_14t"],
                                       aufrufe=letzter["aufrufe_14t"], aufrufe_e=letzter["aufrufe_eindeutig_14t"]),
            "- " + t["seit"].format(seit=d["aufzeichnung_seit"], klone=gesamt_klone, aufrufe=gesamt_aufrufe),
            "",
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="grafik/{name}-dunkel.svg">',
            f'  <img alt="{t["alt"].format(name=name)}" src="grafik/{name}.svg" width="720">',
            "</picture>",
            "",
            t["tabelle"],
            "|---|---:|---:|---:|",
        ]
        for w in wochen(d)[:WOCHEN_IM_BERICHT]:
            zeilen.append(f"| {w['montag'].isoformat()} | {w['klone']} | {w['aufrufe']} | {w['tage']} |")
        verweise = d["verweise"].get(letzter["datum"], [])
        if verweise:
            quellen = ", ".join(f"{v['quelle']} ({v['eindeutig']})" for v in verweise)
            zeilen += ["", t["verweise"].format(quellen=quellen)]
        zeilen.append("")
    return "\n".join(zeilen).rstrip() + "\n"


def readmes_schreiben(alle: list[dict], jetzt: str) -> None:
    """Ersetzt in jeder README nur den Text zwischen den Markern. Fehlt eine Datei oder ein Marker,
    wird sie übersprungen und gemeldet; der Lauf schlägt deshalb nicht fehl."""
    for datei, sprache in READMES:
        if not datei.exists():
            print(f"Hinweis: {datei.name} fehlt, Zahlenblock nicht geschrieben.")
            continue
        text = datei.read_text(encoding="utf-8")
        a, e = text.find(MARKER_START), text.find(MARKER_ENDE)
        if a < 0 or e < 0 or e < a:
            print(f"Hinweis: Marker in {datei.name} fehlen, Zahlenblock nicht geschrieben.")
            continue
        neu = text[: a + len(MARKER_START)] + "\n" + block(alle, jetzt, sprache) + text[e:]
        if neu != text:
            datei.write_text(neu, encoding="utf-8")


def heartbeat_aus() -> bool:
    dnt = os.environ.get("DO_NOT_TRACK", "").strip().lower()
    hb = os.environ.get("STATISTIK_HEARTBEAT", "").strip().lower()
    return dnt in ("1", "true", "ja", "yes", "on") or hb in ("0", "aus", "off", "false", "nein", "no")


def install_id() -> str:
    """Zufällige ID, beim ersten Lauf erzeugt und in daten/ abgelegt (wird mit eingecheckt)."""
    DATEN.mkdir(exist_ok=True)
    if INSTALL_ID_DATEI.exists():
        wert = INSTALL_ID_DATEI.read_text(encoding="utf-8").strip()
        if re.fullmatch(r"[0-9a-f-]{36}", wert):
            return wert
    wert = str(uuid.uuid4())
    INSTALL_ID_DATEI.write_text(wert + "\n", encoding="utf-8")
    return wert


def heartbeat(anzahl_repos: int, ok: bool) -> None:
    """Ein anonymer Ping pro Lauf: Install-ID, Version, Anzahl Repos, ok. Keine Repo-Namen, keine
    Zahlen. Darf den Lauf nie scheitern lassen. Abschalten: DO_NOT_TRACK=1 oder STATISTIK_HEARTBEAT=aus."""
    if heartbeat_aus():
        print("Heartbeat: aus")
        return
    daten = json.dumps(
        {"install_id": install_id(), "version": VERSION, "repos": anzahl_repos, "ok": ok}
    ).encode("utf-8")
    anfrage = urllib.request.Request(
        HEARTBEAT_URL,
        data=daten,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": f"repo-statistik/{VERSION}"},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=5):
            pass
        print("Heartbeat gesendet (anonym: Install-ID, Version, Anzahl Repos, ok · abschalten: DO_NOT_TRACK=1)")
    except Exception as e:  # noqa: BLE001
        print(f"Heartbeat nicht gesendet ({type(e).__name__}), Lauf läuft weiter")


def main() -> int:
    tok = token()
    jetzt_dt = datetime.now(timezone.utc)
    heute = jetzt_dt.date().isoformat()
    jetzt = jetzt_dt.strftime("%Y-%m-%d %H:%M UTC")
    alle = []
    fehler = 0
    repos = repos_lesen()
    for repo in repos:
        try:
            d = sammeln(repo, tok, heute, jetzt)
        except urllib.error.HTTPError as e:
            fehler += 1
            grund = {
                401: "Token ungültig oder abgelaufen",
                403: "Token darf Traffic nicht lesen (Administration: read fehlt?)",
                404: "Repo nicht gefunden oder Token hat keinen Zugriff darauf",
            }.get(e.code, f"HTTP {e.code}")
            print(f"FEHLER {repo}: {grund}")
            continue
        svg_schreiben(d)
        letzter = d["verlauf"][-1]
        print(
            f"{repo}: {len(d['tage'])} Tage gespeichert, 14 Tage: {letzter['klone_14t']} Klone /"
            f" {letzter['klone_eindeutig_14t']} Rechner, Sterne {letzter['sterne']}"
        )
        alle.append(d)
    if alle:
        readmes_schreiben(alle, jetzt)
    heartbeat(len(repos), fehler == 0)
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
