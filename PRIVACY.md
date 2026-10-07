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
- It sends **nothing** to the author, to NetBoosting or to any server operated by them.
  There is no heartbeat, no telemetry, no analytics.
- The Claude Code skill never asks you to paste a token into the chat. It points you to
  `gh secret set`, which prompts for the value in your terminal; the skill never reads,
  prints or stores the token.

## If a future version adds a heartbeat

It will be described here and in the README before it ships: anonymous (random install id,
tool version, number of watched repos, run succeeded or not; never repo names, numbers or
people), on by default, switchable off with one setting. There is none today.

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
- Es sendet **nichts** an den Autor, an NetBoosting oder an Server, die diese betreiben.
  Kein Heartbeat, keine Telemetrie, keine Analyse-Dienste.
- Der Claude-Code-Skill fragt den Token nie im Chat ab. Er verweist auf `gh secret set`,
  das den Wert im Terminal abfragt; der Skill liest, zeigt und speichert den Token nicht.

## Falls eine spätere Version einen Heartbeat bekommt

Er wird hier und in der README beschrieben, bevor er erscheint: anonym (zufällige
Install-ID, Version des Werkzeugs, Anzahl beobachteter Repos, Lauf geglückt oder nicht;
nie Repo-Namen, Zahlen oder Personen), standardmäßig an, mit einer Einstellung abschaltbar.
Heute gibt es keinen.

## Dein Token

Der Token liegt nur in den Actions-Secrets deines Repos. Das Skript liest ihn aus der
Umgebung und schreibt ihn nirgendwohin. GitHub maskiert ihn in den Lauf-Protokollen.

Fragen: <https://github.com/Sertac0708/repo-statistik/issues>.
