#!/usr/bin/env python3
"""Heartbeat-Empfänger für Repo-Statistik. Läuft auf Railway, Code liegt offen im Repo.

Endpunkte:
  POST /ping       nimmt {"install_id": <uuid4>, "version": "x.y.z", "repos": <int>, "ok": <bool>} an
  POST /ping/openseo  Heartbeat des OpenSEO-Forks (Sertac0708/open-seo), nur Felder einer festen Liste
  GET  /zahlen/openseo  aggregierte Zahlen des OpenSEO-Forks
  GET  /badge/openseo.svg  Abzeichen „aktive OpenSEO-Installationen diese Woche"
  GET  /zahlen     aggregierte Zahlen als JSON (aktive Installationen diese/letzte Woche, gesamt, Versionen)
  GET  /badge.svg  Abzeichen „aktive Installationen diese Woche" für die README
  GET  /healthz    Lebenszeichen
  GET  /           Kurzbeschreibung

Gespeichert wird je Ping: Install-ID, ISO-Woche, Version, Anzahl Repos, ok, Empfangszeit (UTC).
Keine IP-Adressen, kein User-Agent, keine Repo-Namen. Nur Python-Standardbibliothek.
"""

import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATENBANK = os.environ.get("DATENBANK", "/data/heartbeat.sqlite")
PORT = int(os.environ.get("PORT", "8080"))
MAX_BODY = 1024
UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
VERSION = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")
SCHREIBSPERRE = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS ping (
  id INTEGER PRIMARY KEY,
  install_id TEXT NOT NULL,
  woche TEXT NOT NULL,
  version TEXT NOT NULL,
  repos INTEGER NOT NULL,
  ok INTEGER NOT NULL,
  empfangen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ping_woche ON ping(woche);
CREATE INDEX IF NOT EXISTS ping_install ON ping(install_id);
CREATE TABLE IF NOT EXISTS openseo_ping (
  id INTEGER PRIMARY KEY,
  install_id TEXT NOT NULL,
  woche TEXT NOT NULL,
  event TEXT NOT NULL,
  version TEXT NOT NULL,
  deploy_target TEXT,
  db_backend TEXT,
  props TEXT NOT NULL,
  empfangen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS openseo_woche ON openseo_ping(woche);
-- Höchstens eine Zeile je Installation, Woche und Ereignis: Wiederholungen
-- überschreiben die Zeile, statt die Tabelle wachsen zu lassen.
CREATE UNIQUE INDEX IF NOT EXISTS openseo_eins_je_woche ON openseo_ping(install_id, woche, event);
"""


def verbindung() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DATENBANK) or ".", exist_ok=True)
    v = sqlite3.connect(DATENBANK, timeout=10)
    v.executescript(SCHEMA)
    return v


def iso_woche(zeit: datetime) -> str:
    jahr, woche, _ = zeit.isocalendar()
    return f"{jahr}-W{woche:02d}"


def zahlen() -> dict:
    jetzt = datetime.now(timezone.utc)
    diese = iso_woche(jetzt)
    letzte = iso_woche(jetzt - timedelta(days=7))
    with verbindung() as v:
        eins = lambda sql, *p: v.execute(sql, p).fetchone()[0]
        versionen = {
            zeile[0]: zeile[1]
            for zeile in v.execute(
                "SELECT version, COUNT(DISTINCT install_id) FROM ping WHERE woche = ? GROUP BY version ORDER BY version",
                (diese,),
            )
        }
        return {
            "aktive_installationen_diese_woche": eins("SELECT COUNT(DISTINCT install_id) FROM ping WHERE woche = ?", diese),
            "aktive_installationen_letzte_woche": eins("SELECT COUNT(DISTINCT install_id) FROM ping WHERE woche = ?", letzte),
            "installationen_gesamt": eins("SELECT COUNT(DISTINCT install_id) FROM ping"),
            "pings_gesamt": eins("SELECT COUNT(*) FROM ping"),
            "versionen_diese_woche": versionen,
            "woche": diese,
            "stand": jetzt.strftime("%Y-%m-%d %H:%M UTC"),
        }


# --- OpenSEO-Fork: feste Liste erlaubter Felder, alles andere wird verworfen ---
OPENSEO_EVENTS = {"self_host.heartbeat", "self_host.preflight_failed"}
OPENSEO_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
OPENSEO_VERSION = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}([-+][A-Za-z0-9.]{1,20})?$")
OPENSEO_ZAHLEN = ("userCount", "projectCount", "siteAuditCount", "rankTrackingKeywordCount",
                  "savedKeywordCount", "mcpToolCalls", "minutesSinceInstall")
OPENSEO_SCHALTER = ("gscConnected", "samChatUsed", "firstRun")
OPENSEO_AUSWAHL = {"deployTarget": {"cloudflare", "docker"}, "dbBackend": {"d1", "postgres"}}
# Prüfnamen kommen als "dataforseo:error" (Heartbeat) oder "AUTH_MODE" (Startprüfung).
OPENSEO_PRUEFUNG = re.compile(r"^[A-Za-z0-9_-]{1,40}(:[a-z]{2,10})?$")
# Schutz gegen Fluten: Anfragen je Absender-Adresse und Zeitfenster. Die Adresse
# lebt nur im Arbeitsspeicher und wird weder gespeichert noch protokolliert.
OPENSEO_LIMIT, OPENSEO_FENSTER = 30, 600
OPENSEO_MAX_STARTFEHLER_JE_WOCHE = 10_000
_anfragen: dict[str, list[float]] = {}
_anfragen_sperre = threading.Lock()


def openseo_erlaubt(absender: str, jetzt: float | None = None) -> bool:
    jetzt = time.monotonic() if jetzt is None else jetzt
    with _anfragen_sperre:
        if len(_anfragen) > 10_000:  # Speicher begrenzen: alte Einträge aufräumen
            for k in [k for k, v in _anfragen.items() if not v or jetzt - v[-1] > OPENSEO_FENSTER]:
                del _anfragen[k]
        zeiten = [t for t in _anfragen.get(absender, []) if jetzt - t < OPENSEO_FENSTER]
        if len(zeiten) >= OPENSEO_LIMIT:
            _anfragen[absender] = zeiten
            return False
        zeiten.append(jetzt)
        _anfragen[absender] = zeiten
        return True


def openseo_bereinigen(props: dict) -> dict:
    sauber = {}
    for k in OPENSEO_ZAHLEN:
        v = props.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1_000_000_000:
            sauber[k] = int(v)
    for k in OPENSEO_SCHALTER:
        if isinstance(props.get(k), bool):
            sauber[k] = props[k]
    for k, erlaubt in OPENSEO_AUSWAHL.items():
        if isinstance(props.get(k), str) and props[k] in erlaubt:
            sauber[k] = props[k]
    if isinstance(props.get("prevVersion"), str) and OPENSEO_VERSION.match(props["prevVersion"]):
        sauber["prevVersion"] = props["prevVersion"]
    for k in ("setupIssues", "failedChecks"):
        liste = props.get(k)
        if isinstance(liste, list):
            sauber[k] = [x for x in liste[:20] if isinstance(x, str) and OPENSEO_PRUEFUNG.match(x)]
    return sauber


_zahlen_cache: dict = {"bis": 0.0, "wert": None}
_zahlen_sperre = threading.Lock()


def openseo_zahlen_gepuffert(sekunden: int = 120) -> dict:
    """Zahlenseite und Abzeichen rechnen höchstens alle zwei Minuten neu."""
    with _zahlen_sperre:
        if _zahlen_cache["wert"] is None or time.monotonic() >= _zahlen_cache["bis"]:
            _zahlen_cache["wert"] = openseo_zahlen()
            _zahlen_cache["bis"] = time.monotonic() + sekunden
        return _zahlen_cache["wert"]


def openseo_zahlen() -> dict:
    jetzt = datetime.now(timezone.utc)
    diese, letzte = iso_woche(jetzt), iso_woche(jetzt - timedelta(days=7))
    with verbindung() as v:
        eins = lambda sql, *p: v.execute(sql, p).fetchone()[0]
        aktiv = "SELECT COUNT(DISTINCT install_id) FROM openseo_ping WHERE woche = ? AND event = 'self_host.heartbeat'"
        gruppe = lambda spalte: {
            (z[0] or "unbekannt"): z[1]
            for z in v.execute(
                f"SELECT {spalte}, COUNT(DISTINCT install_id) FROM openseo_ping WHERE woche = ? "
                "AND event = 'self_host.heartbeat' GROUP BY 1 ORDER BY 1", (diese,))
        }
        fehler = {}
        for (props,) in v.execute(
                "SELECT props FROM openseo_ping WHERE woche = ? AND event = 'self_host.preflight_failed'", (diese,)):
            for name in json.loads(props).get("failedChecks", []):
                fehler[name] = fehler.get(name, 0) + 1
        return {
            "aktive_installationen_diese_woche": eins(aktiv, diese),
            "aktive_installationen_letzte_woche": eins(aktiv, letzte),
            "installationen_gesamt": eins("SELECT COUNT(DISTINCT install_id) FROM openseo_ping WHERE event = 'self_host.heartbeat'"),
            "versionen_diese_woche": gruppe("version"),
            "betrieb_diese_woche": gruppe("deploy_target"),
            "fehlgeschlagene_starts_diese_woche": eins(
                "SELECT COUNT(*) FROM openseo_ping WHERE woche = ? AND event = 'self_host.preflight_failed'", diese),
            "haeufigste_startfehler": dict(sorted(fehler.items(), key=lambda x: -x[1])[:10]),
            "woche": diese,
            "stand": jetzt.strftime("%Y-%m-%d %H:%M UTC"),
        }


def badge(wert: int, lang: str = "de", label: str | None = None) -> bytes:
    label = label or ("active installs this week" if lang == "en" else "aktive Installationen diese Woche")
    text = str(wert)
    lb = int(len(label) * 6.3) + 10
    tb = int(len(text) * 7) + 10
    b = lb + tb
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{b}" height="20" role="img" aria-label="{label}: {text}">'
        f'<title>{label}: {text}</title>'
        f'<rect width="{lb}" height="20" rx="3" fill="#555"/>'
        f'<rect x="{lb}" width="{tb}" height="20" rx="3" fill="#2a78d6"/>'
        f'<rect x="{lb - 3}" width="6" height="20" fill="#2a78d6"/>'
        f'<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{lb / 2:.0f}" y="14">{label}</text>'
        f'<text x="{lb + tb / 2:.0f}" y="14" font-weight="bold">{text}</text>'
        f"</g></svg>"
    )
    return svg.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "repo-statistik-heartbeat"
    # Verbindungen, die einen Body ankündigen und dann nichts schicken, nach
    # 10 Sekunden schließen, statt einen Thread dauerhaft zu blockieren.
    timeout = 10

    def log_message(self, format, *args):  # noqa: A002 — Signatur der Basisklasse
        # Standard würde die Client-Adresse mitschreiben. Hier nur Methode, Pfad, Status.
        print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} {self.command} {self.path} {args[1] if len(args) > 1 else ''}")

    def antwort(self, status: int, body: bytes, typ: str = "application/json; charset=utf-8", cache: int = 0):
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", f"public, max-age={cache}" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        pfad = self.path.split("?", 1)[0]
        if pfad == "/healthz":
            try:
                with verbindung() as v:
                    v.execute("SELECT 1")
                self.antwort(200, b'{"ok": true}')
            except Exception as e:  # noqa: BLE001
                self.antwort(500, json.dumps({"ok": False, "fehler": type(e).__name__}).encode())
        elif pfad == "/zahlen":
            self.antwort(200, json.dumps(zahlen(), ensure_ascii=False, indent=2).encode("utf-8"), cache=300)
        elif pfad == "/zahlen/openseo":
            self.antwort(200, json.dumps(openseo_zahlen_gepuffert(), ensure_ascii=False, indent=2).encode("utf-8"), cache=300)
        elif pfad == "/badge/openseo.svg":
            en = "lang=en" in self.path
            label = "active OpenSEO installs this week" if en else "aktive OpenSEO-Installationen diese Woche"
            self.antwort(200, badge(openseo_zahlen_gepuffert()["aktive_installationen_diese_woche"], label=label),
                         "image/svg+xml; charset=utf-8", cache=300)
        elif pfad == "/badge.svg":
            lang = "en" if "lang=en" in self.path else "de"
            self.antwort(200, badge(zahlen()["aktive_installationen_diese_woche"], lang), "image/svg+xml; charset=utf-8", cache=300)
        elif pfad == "/":
            text = (
                "Heartbeat-Empfänger für Repo-Statistik (https://github.com/Sertac0708/repo-statistik).\n"
                "Nimmt anonyme Pings des Werkzeugs an und zählt aktive Installationen je Woche.\n"
                "Zahlen: /zahlen · Abzeichen: /badge.svg · Code: heartbeat/server.py im Repo.\n"
            )
            self.antwort(200, text.encode("utf-8"), "text/plain; charset=utf-8", cache=300)
        else:
            self.antwort(404, b'{"fehler": "unbekannter Pfad"}')

    def do_POST(self):
        if self.path.split("?", 1)[0] == "/ping/openseo":
            self.openseo_ping()
            return
        if self.path.split("?", 1)[0] != "/ping":
            self.antwort(404, b'{"fehler": "unbekannter Pfad"}')
            return
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = -1
        if laenge <= 0 or laenge > MAX_BODY:
            self.antwort(400, b'{"fehler": "Body fehlt oder zu gross"}')
            return
        try:
            d = json.loads(self.rfile.read(laenge).decode("utf-8"))
            install_id = str(d["install_id"]).lower()
            version = str(d["version"])
            repos = int(d["repos"])
            ok = bool(d["ok"])
            if not UUID4.match(install_id) or not VERSION.match(version) or not 0 <= repos <= 10000:
                raise ValueError("Werte ausserhalb des Erlaubten")
        except Exception:  # noqa: BLE001
            self.antwort(400, b'{"fehler": "ungueltiger Ping"}')
            return
        jetzt = datetime.now(timezone.utc)
        with SCHREIBSPERRE, verbindung() as v:
            v.execute(
                "INSERT INTO ping (install_id, woche, version, repos, ok, empfangen) VALUES (?, ?, ?, ?, ?, ?)",
                (install_id, iso_woche(jetzt), version, repos, int(ok), jetzt.strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
        self.antwort(200, b'{"ok": true}')


def _absender(handler) -> str:
    # Railways Proxy hängt die echte Client-Adresse hinten an X-Forwarded-For an.
    # Den letzten Eintrag nehmen: die vorderen kann der Absender selbst fälschen.
    weitergeleitet = handler.headers.get("X-Forwarded-For", "")
    return weitergeleitet.split(",")[-1].strip() or handler.client_address[0]


def _openseo_ping(self):
    if not openseo_erlaubt(_absender(self)):
        self.antwort(429, b'{"fehler": "zu viele Anfragen"}')
        return
    try:
        laenge = int(self.headers.get("Content-Length", "0"))
    except ValueError:
        laenge = -1
    if laenge <= 0 or laenge > 8192:
        self.antwort(400, b'{"fehler": "Body fehlt oder zu gross"}')
        return
    try:
        d = json.loads(self.rfile.read(laenge).decode("utf-8"))
        event, install_id, version = d["event"], str(d["install_id"]), str(d["version"])
        props = d.get("properties") or {}
        if event not in OPENSEO_EVENTS or not OPENSEO_ID.match(install_id) or not OPENSEO_VERSION.match(version) \
                or not isinstance(props, dict):
            raise ValueError("ungueltig")
        sauber = openseo_bereinigen(props)
    except Exception:  # noqa: BLE001
        self.antwort(400, b'{"fehler": "ungueltiger Ping"}')
        return
    jetzt = datetime.now(timezone.utc)
    woche = iso_woche(jetzt)
    with SCHREIBSPERRE, verbindung() as v:
        if event == "self_host.preflight_failed" and v.execute(
                "SELECT COUNT(*) FROM openseo_ping WHERE woche = ? AND event = ?", (woche, event),
        ).fetchone()[0] >= OPENSEO_MAX_STARTFEHLER_JE_WOCHE:
            self.antwort(200, b'{"ok": true}')  # Obergrenze erreicht: annehmen, nicht speichern
            return
        v.execute(
            "INSERT INTO openseo_ping (install_id, woche, event, version, deploy_target, db_backend, props, empfangen) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(install_id, woche, event) DO UPDATE SET version = excluded.version, "
            "deploy_target = excluded.deploy_target, db_backend = excluded.db_backend, "
            "props = excluded.props, empfangen = excluded.empfangen",
            (install_id, woche, event, version, sauber.get("deployTarget"), sauber.get("dbBackend"),
             json.dumps(sauber, ensure_ascii=False), jetzt.strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
    self.antwort(200, b'{"ok": true}')


Handler.openseo_ping = _openseo_ping


if __name__ == "__main__":
    verbindung().close()
    print(f"Heartbeat-Empfaenger auf Port {PORT}, Datenbank {DATENBANK}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
