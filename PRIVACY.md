# Privacy

Repo-Statistik is a GitHub Action and a Claude Code plugin created by Sertac and published by
[NetBoosting](https://netboosting.de). It runs inside your GitHub repository and, as a
plugin, on your machine.

## What it does with data

- It calls `api.github.com` with the token you created, and reads only what that token
  allows: traffic statistics (views, clones, referrers, popular paths) and public metadata
  (stars, forks, watchers, open issues) of the repos you listed in `repos.txt`.
- It stores the results in your repository: `daten/<repo>.json`, the charts in `grafik/`,
  and the numbers block in the READMEs.
- It sends one anonymous heartbeat per run to a receiver operated by the author (see below).
  Nothing else leaves your repo: no analytics, no error reports, no content.
- The Claude Code skill never asks you to paste a token into the chat. It points you to
  `gh secret set`, which prompts for the value in your terminal; the skill never reads,
  prints or stores the token.

## The heartbeat

Once per run the tool sends a POST request to `https://heartbeat-production-40b4.up.railway.app/ping` with exactly:
a random install id (created on the first run, stored in `daten/install-id.txt`), the tool
version, the number of watched repos, and whether the run succeeded. Never repo names, traffic
numbers or anything about a person.

The receiver (`heartbeat/server.py` in this repo, hosted on Railway) stores those four values
with the ISO week and the time of receipt in a SQLite database. It does not store IP addresses
or user agents, not even in its access log. Railway, like any host, sees connection metadata
in transit; the request comes from GitHub's Action runners, not from your machine. The
aggregated counts are public at `https://heartbeat-production-40b4.up.railway.app/zahlen`.

Turning it off: set the repository variable `DO_NOT_TRACK` to `1` (Settings → Secrets and
variables → Actions → Variables) or the environment variable `STATISTIK_HEARTBEAT=aus`. The
run then prints "Heartbeat: aus" and sends nothing.

## Your token

The token lives only in your repository's Actions secrets. The script reads it from the
environment and never writes it anywhere. GitHub masks it in the run logs.

Questions: <https://github.com/Sertac0708/repo-statistik/issues>.

---

# Datenschutz

Repo-Statistik ist eine GitHub Action und ein Claude-Code-Plugin, erstellt von Sertac und
herausgegeben von [NetBoosting](https://netboosting.de). Es läuft in deinem GitHub-Repo
und, als Plugin, auf deinem Rechner.

## Was es mit Daten macht

- Es ruft `api.github.com` mit dem Token auf, den du angelegt hast, und liest nur, was
  dieser Token erlaubt: Zugriffszahlen (Aufrufe, Klone, Verweise, meistbesuchte Seiten) und
  öffentliche Metadaten (Sterne, Forks, Beobachter, offene Issues) der Repos aus `repos.txt`.
- Es legt die Ergebnisse in deinem Repo ab: `daten/<repo>.json`, die Grafiken in `grafik/`
  und den Zahlenblock in den READMEs.
- Es sendet einmal pro Lauf einen anonymen Heartbeat an einen Empfänger des Autors (siehe
  unten). Sonst verlässt nichts dein Repo: keine Analyse-Dienste, keine Fehlerberichte, keine Inhalte.
- Der Claude-Code-Skill fragt den Token nie im Chat ab. Er verweist auf `gh secret set`,
  das den Wert im Terminal abfragt; der Skill liest, zeigt und speichert den Token nicht.

## Der Heartbeat

Einmal pro Lauf schickt das Werkzeug eine POST-Anfrage an `https://heartbeat-production-40b4.up.railway.app/ping` mit genau:
einer zufälligen Install-ID (beim ersten Lauf erzeugt, abgelegt in `daten/install-id.txt`),
der Version des Werkzeugs, der Anzahl beobachteter Repos und ob der Lauf geklappt hat. Nie
Repo-Namen, Zugriffszahlen oder etwas über eine Person.

Der Empfänger (`heartbeat/server.py` in diesem Repo, gehostet bei Railway) speichert diese vier
Werte mit ISO-Woche und Empfangszeit in einer SQLite-Datenbank. Er speichert keine IP-Adressen
und keine User-Agents, auch nicht im Zugriffslog. Railway sieht wie jeder Hoster Verbindungsdaten
beim Transport; die Anfrage kommt von GitHubs Action-Runnern, nicht von deinem Rechner. Die
Summen sind öffentlich unter `https://heartbeat-production-40b4.up.railway.app/zahlen`.

Abschalten: Repo-Variable `DO_NOT_TRACK` auf `1` setzen (Settings → Secrets and variables →
Actions → Variables) oder Umgebungsvariable `STATISTIK_HEARTBEAT=aus`. Der Lauf meldet dann
„Heartbeat: aus" und sendet nichts.

## Dein Token

Der Token liegt nur in den Actions-Secrets deines Repos. Das Skript liest ihn aus der
Umgebung und schreibt ihn nirgendwohin. GitHub maskiert ihn in den Lauf-Protokollen.

Fragen: <https://github.com/Sertac0708/repo-statistik/issues>.
