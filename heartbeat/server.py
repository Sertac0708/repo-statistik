#!/usr/bin/env python3
"""Heartbeat-Empfänger für Repo-Statistik. Läuft auf Railway, Code liegt offen im Repo.

Endpunkte:
  POST /ping       nimmt {"install_id": <uuid4>, "version": "x.y.z", "repos": <int>, "ok": <bool>} an
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


def badge(wert: int) -> bytes:
    label = "aktive Installationen diese Woche"
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
        elif pfad == "/badge.svg":
            self.antwort(200, badge(zahlen()["aktive_installationen_diese_woche"]), "image/svg+xml; charset=utf-8", cache=300)
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


if __name__ == "__main__":
    verbindung().close()
    print(f"Heartbeat-Empfaenger auf Port {PORT}, Datenbank {DATENBANK}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
