# 📈 Repo-Statistik — Zugriffszahlen deiner GitHub-Repos, dauerhaft statt 14 Tage

> **Erstellt von Sertac · Made by [NetBoosting](https://netboosting.de)** · Frei nutzbar unter MIT-Lizenz · 🇬🇧 [English guide](README.md)

![Aktive Installationen diese Woche](grafik/installationen.svg)

GitHub zeigt dir für jedes Repo, wie oft es aufgerufen und geklont wurde. Aber nur für die
letzten 14 Tage, danach ist es weg. Repo-Statistik ist eine GitHub Action, die diese Zahlen
jeden Montag abholt, in deinem eigenen Repo speichert und als Tabelle und Grafik anzeigt.

Das reicht, um zu sehen, ob deine Werkzeuge benutzt werden. Du musst dafür keinen Heartbeat
und keine Telemetrie in deine Programme einbauen: Jede Installation eines Claude-Code-Plugins,
jedes `git clone`, jeder Besuch der Repo-Seite steht in GitHubs Zahlen. Dieses Werkzeug hebt
sie nur auf, bevor GitHub sie wegwirft.

Das Werkzeug selbst schickt uns einen anonymen Heartbeat. Der Abschnitt „Was das Werkzeug
sendet" sagt genau, was drinsteht und wie du ihn abschaltest.

## Das sind unsere echten Zahlen

Dieses Repo ist Anleitung und Ergebnis zugleich. Der Block unten wird jeden Montag vom
Werkzeug neu geschrieben, mit den Zahlen unserer öffentlichen Repos.

<!-- statistik:start -->
Stand: 2026-10-07 11:50 UTC. Dieser Block wird vom Werkzeug geschrieben, Änderungen von Hand gehen verloren.

### Sertac0708/feature-scout

- Sterne 2 · Forks 0 · Beobachter 1 · offene Issues 0
- Letzte 14 Tage laut GitHub: 115 Klone von 75 Rechnern, 8 Aufrufe von 6 Besuchern
- Seit Aufzeichnungsbeginn (2026-09-28): 115 Klone, 8 Aufrufe

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="grafik/feature-scout-dunkel.svg">
  <img alt="Klone und Aufrufe je Woche für feature-scout" src="grafik/feature-scout.svg" width="720">
</picture>

| Woche ab | Klone | Aufrufe | Tage mit Daten |
|---|---:|---:|---:|
| 2026-10-05 | 2 | 2 | 2 |
| 2026-09-28 | 113 | 6 | 7 |

Verweise (eindeutige Besucher, 14 Tage): github.com (1)

### Sertac0708/siteground-deploy

- Sterne 0 · Forks 0 · Beobachter 0 · offene Issues 0
- Letzte 14 Tage laut GitHub: 49 Klone von 37 Rechnern, 0 Aufrufe von 0 Besuchern
- Seit Aufzeichnungsbeginn (2026-10-02): 49 Klone, 0 Aufrufe

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="grafik/siteground-deploy-dunkel.svg">
  <img alt="Klone und Aufrufe je Woche für siteground-deploy" src="grafik/siteground-deploy.svg" width="720">
</picture>

| Woche ab | Klone | Aufrufe | Tage mit Daten |
|---|---:|---:|---:|
| 2026-10-05 | 0 | 0 | 2 |
| 2026-09-28 | 49 | 0 | 7 |

### Sertac0708/github-repo-pruefer

- Sterne 1 · Forks 0 · Beobachter 0 · offene Issues 0
- Letzte 14 Tage laut GitHub: 126 Klone von 81 Rechnern, 19 Aufrufe von 4 Besuchern
- Seit Aufzeichnungsbeginn (2026-09-27): 126 Klone, 19 Aufrufe

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="grafik/github-repo-pruefer-dunkel.svg">
  <img alt="Klone und Aufrufe je Woche für github-repo-pruefer" src="grafik/github-repo-pruefer.svg" width="720">
</picture>

| Woche ab | Klone | Aufrufe | Tage mit Daten |
|---|---:|---:|---:|
| 2026-10-05 | 7 | 0 | 2 |
| 2026-09-28 | 43 | 9 | 7 |
| 2026-09-21 | 76 | 10 | 5 |

Verweise (eindeutige Besucher, 14 Tage): github.com (1)

### Sertac0708/repo-statistik

- Sterne 0 · Forks 0 · Beobachter 0 · offene Issues 0
- Letzte 14 Tage laut GitHub: 0 Klone von 0 Rechnern, 0 Aufrufe von 0 Besuchern
- Seit Aufzeichnungsbeginn (2026-10-07): 0 Klone, 0 Aufrufe

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="grafik/repo-statistik-dunkel.svg">
  <img alt="Klone und Aufrufe je Woche für repo-statistik" src="grafik/repo-statistik.svg" width="720">
</picture>

| Woche ab | Klone | Aufrufe | Tage mit Daten |
|---|---:|---:|---:|
| 2026-10-05 | 0 | 0 | 3 |
<!-- statistik:end -->

## So funktioniert es

- `werkzeuge/sammeln.py` fragt für jedes Repo aus `repos.txt` GitHubs Traffic-Schnittstelle ab:
  Aufrufe und Klone je Tag, Verweise, meistbesuchte Seiten, dazu Sterne, Forks und Beobachter.
- Die Tageswerte werden nach Datum mit dem Bestand in `daten/<repo>.json` verschmolzen. Fällt
  ein Lauf aus, deckt der nächste die Lücke noch ab: GitHub liefert 14 Tage, das Werkzeug läuft
  wöchentlich.
- Daraus entstehen je Repo zwei Grafiken in `grafik/` (hell und dunkel, GitHub wählt die
  passende) und der Zahlenblock in dieser README.
- Die Action `.github/workflows/statistik.yml` läuft montags um 06:00 UTC, checkt die
  Änderungen als Bot ein und meldet sich per Mail nur, wenn etwas schiefgeht.

Nur Python-Standardbibliothek, keine Abhängigkeiten, kein Fremddienst, kein JavaScript.

## Einrichten

### Weg A: Repo als Vorlage benutzen (ohne Claude)

Du brauchst ein GitHub-Konto. Die GitHub-CLI `gh` ist praktisch, aber nicht nötig.

1. Oben rechts **Use this template → Create a new repository**. Privat oder öffentlich,
   wie du willst.
2. In der Kopie `repos.txt` öffnen und deine Repos eintragen, eins je Zeile als
   `Eigentümer/Name`. Unsere Daten raus: die Ordner `daten/` und `grafik/` leeren. Den
   Zahlenblock in den READMEs lässt du stehen, er wird beim ersten Lauf überschrieben.
3. Token anlegen: GitHub → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens** → Generate new token. Repository access: **Only select
   repositories**, dort die Repos aus `repos.txt` auswählen. Repository permissions:
   **Administration: Read-only**, Metadata wird automatisch ergänzt. Mehr nicht. Laufzeit
   nach Geschmack, GitHub mailt vor dem Ablauf.
4. Token als Secret hinterlegen: Repo → Settings → Secrets and variables → Actions →
   **New repository secret**, Name `STATISTIK_TOKEN`. Oder im Terminal:

   ```bash
   gh secret set STATISTIK_TOKEN -R DEIN-NAME/DEIN-REPO
   ```

   Der Befehl fragt den Wert ab: einmal einfügen, Enter. Es wird dabei nichts angezeigt.
5. Ersten Lauf starten: Actions → **Statistik sammeln** → Run workflow. Nach einer Minute
   stehen Tabelle und Grafik in der README.

Danach läuft es jeden Montag von allein. Willst du ein weiteres Repo beobachten, trägst du
es in `repos.txt` ein **und** schaltest es im Token frei, sonst meldet der Lauf 404.

Ein eigener Token ist nötig, weil die Traffic-Schnittstelle die Berechtigung „Administration:
lesen" verlangt, die der automatische Token einer Action nicht hat. Der Token kann nur lesen
und nur die Repos sehen, die du ausgewählt hast.

### Weg B: als Claude-Code-Plugin

```bash
claude plugin marketplace add Sertac0708/repo-statistik
```
```bash
claude plugin install repo-statistik@repo-statistik
```

Danach Claude Code neu starten und sagen: *„Richte Repo-Statistik für meine Repos ein."*
Claude legt die Kopie an, trägt deine Repos ein und erklärt dir den Token-Schritt. Den Token
selbst gibst du nie im Chat ein, Claude lässt dich ihn im Terminal einfügen. Später fragst du:
*„Wie laufen meine Repos?"*, und Claude liest die Zahlen aus deinem Statistik-Repo und
ordnet sie ein.

Updates holen:

```bash
claude plugin marketplace update repo-statistik
```

### Weg C: Skill von Hand kopieren

Den Ordner `skills/repo-statistik` nach `~/.claude/skills/` kopieren. Gleiche Wirkung wie
Weg B, nur ohne Updates.

## Lokal laufen lassen

```bash
STATISTIK_TOKEN=$(gh auth token) python3 werkzeuge/sammeln.py
```

Dasselbe Ergebnis wie in der Action, nur auf deinem Rechner. Praktisch, um vor dem ersten
Push zu sehen, ob Token und `repos.txt` stimmen.

## Zahlen richtig lesen

- **Klone** sind der beste Anhaltspunkt für Nutzung. Jede Plugin-Installation über einen
  Claude-Code-Marktplatz ist ein `git clone`. Aber auch Bots, Spiegeldienste und CI-Läufe
  klonen, und deine eigenen Klone zählen mit. Viele Klone bei wenigen Aufrufen heißt meist,
  dass vor allem Automaten geklont haben.
- **Aufrufe** sind Menschen, die die Repo-Seite angeschaut haben.
- **Eindeutig** stimmt nur für die 14-Tage-Zahl, die GitHub selbst liefert. Tageswerte
  lassen sich nicht aufsummieren, derselbe Rechner zählt jeden Tag neu. Deshalb speichert
  das Werkzeug die 14-Tage-Zahl bei jedem Lauf separat.
- **Auf den Verlauf schauen.** Eine Woche sagt wenig. Nach zwei Monaten siehst du, ob es
  Interesse gibt oder nur Rauschen.

## Was das Werkzeug sendet und speichert

An GitHub: die Abfragen mit deinem Token, in deiner Action. Die Ergebnisse legt es in deinem
Repo ab.

An uns: einen Heartbeat, einmal pro Lauf. Er ist der einzige Weg, auf dem wir erfahren, wie
viele Installationen des Werkzeugs laufen, und er ist so gebaut, wie wir uns einen Heartbeat
in fremder Software wünschen. Er enthält genau vier Dinge:

- eine zufällige Install-ID, beim ersten Lauf erzeugt und in `daten/install-id.txt` abgelegt
- die Version des Werkzeugs
- die Anzahl der beobachteten Repos, nur die Zahl
- ob der Lauf geklappt hat

Keine Repo-Namen, keine Zugriffszahlen, keine Personen. Der Empfänger läuft auf Railway,
speichert keine IP-Adressen, auch nicht im Zugriffslog, und sein Code liegt offen in
[`heartbeat/`](heartbeat/). Die Summe siehst du oben im Abzeichen, das die Montags-Action als
Datei ins Repo legt, und jederzeit unter <https://heartbeat-production-40b4.up.railway.app/zahlen>. Der
Empfänger schläft, wenn nichts ankommt, die erste Anfrage weckt ihn und dauert ein paar Sekunden.

Abschalten: im Repo unter Settings → Secrets and variables → Actions → Variables die Variable
`DO_NOT_TRACK` auf `1` setzen. Lokal reicht dieselbe Umgebungsvariable. Der Lauf meldet dann
„Heartbeat: aus" und sendet nichts. Alles andere funktioniert unverändert. Mehr dazu in
[PRIVACY.md](PRIVACY.md).

## Grenzen

- GitHub gibt Traffic nur für Repos heraus, in denen du Admin bist. Fremde Repos lassen sich
  nicht beobachten.
- Was vor der Einrichtung älter als 14 Tage war, ist weg.
- Ein Lauf braucht unter einer Minute Actions-Zeit. Bei öffentlichen Repos ist das kostenlos,
  bei privaten zählt es aufs monatliche Kontingent.
- Läuft der Token ab, wird der Lauf rot und GitHub mailt dich an. Dann neuen Token setzen.

## Lizenz und Kontakt

MIT-Lizenz. Erstellt von Sertac, herausgegeben von [NetBoosting](https://netboosting.de).
Fragen und Fehler: [Issues](https://github.com/Sertac0708/repo-statistik/issues).
