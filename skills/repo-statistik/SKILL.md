---
name: repo-statistik
description: >-
  Sets up and reads "Repo-Statistik": a weekly GitHub Action that keeps the view and clone
  numbers of the user's GitHub repos beyond GitHub's 14-day window, as table and chart in
  their own repo, with no telemetry in their tools. Use when the user asks how many people
  use, clone or visit their repos, wants repo traffic history, asks to "set up repo statistics",
  "how are my repos doing", "who uses my plugin", or mentions clones, views, GitHub traffic
  or Insights. Deutsch: „Repo-Statistik einrichten", „wie laufen meine Repos", „wie viele nutzen
  mein Plugin", „Klone", „Aufrufe", „Zugriffszahlen". Needs git and the GitHub CLI gh.
license: MIT
metadata:
  author: Sertac
  publisher: NetBoosting (https://netboosting.de)
  version: "1.0.0"
  created: "2026-10-07"
---

# Repo-Statistik (repo traffic history)

Created by **Sertac** · Made by [NetBoosting](https://netboosting.de). Keeps GitHub traffic
numbers (views, clones, referrers, stars) of the user's repos permanently, via a GitHub
Action in a repo of their own. Source and guide: <https://github.com/Sertac0708/repo-statistik>.

**Language:** answer in the user's language (German or English). Keep replies short; numbers
go in a table.

## Ground rules (always)

1. **Never ask for the token in chat, never read or print it.** The token goes in through
   `gh secret set STATISTIK_TOKEN -R owner/repo`, which prompts in the user's terminal. If
   the user pastes a token into the chat anyway, tell them to revoke it on GitHub and create
   a new one.
2. **Never invent numbers.** Everything you report comes from `daten/<repo>.json` or the
   GitHub API. If a file is missing, say so.
3. **Do not change the user's other repos.** The tool only needs a token with
   "Administration: read" on them; nothing is written there.
4. Check `gh auth status` first. Without `gh`, give the GitHub web steps from the README
   instead of commands.

## Job 1: set it up

Trigger: "set up repo statistics", "Repo-Statistik einrichten", "I want to see who uses my
repos".

1. Ask which repos to watch, or offer the list from `gh repo list --limit 50`. Only repos
   where the user is admin work (GitHub rule).
2. Create the copy from the template, private unless the user wants it public:
   ```bash
   gh repo create <owner>/repo-statistik --template Sertac0708/repo-statistik --private --clone
   ```
   Then in the clone: write the user's repos into `repos.txt` (one `owner/name` per line),
   empty `daten/` and `grafik/`, commit and push. Keep the marker comments in both READMEs.
3. Explain the token in the user's language, exactly these settings: Fine-grained token →
   Repository access "Only select repositories" (the repos from `repos.txt`) → Repository
   permissions "Administration: Read-only" (Metadata is added automatically). Nothing else.
4. Have the user run in their terminal (you do not run it, it prompts for the secret):
   ```bash
   gh secret set STATISTIK_TOKEN -R <owner>/repo-statistik
   ```
   Tell them: paste once, press Enter, nothing is echoed. Then verify with
   `gh secret list -R <owner>/repo-statistik`.
5. Start the first run and watch it:
   ```bash
   gh workflow run statistik.yml -R <owner>/repo-statistik
   ```
   Then `gh run list -R <owner>/repo-statistik --limit 1` and `gh run view <id> --log` on
   failure. Known failures: `401` = token invalid (often pasted twice), `403` = permission
   missing, `404` = repo not selected in the token. Report the fix, not just the error.
6. Report: link to the repo, what the user will see, that it now runs every Monday, and that
   GitHub emails only on failure.

## Job 2: read the numbers

Trigger: "how are my repos doing", "wie laufen meine Repos", "how many people cloned X".

1. Find the statistics repo: ask, or `gh repo list --limit 100 | grep -i statistik`. Read
   the data with `gh api repos/<owner>/repo-statistik/contents/daten/<repo>.json --jq .content | base64 -d`
   or from a local clone.
2. Per repo report: stars/forks now; last 14 days per GitHub (clones, unique machines, views,
   unique visitors) from the latest `verlauf` entry; this week vs. last week from `tage`
   summed by ISO week (Monday start); referrers if any.
3. Always add the caveats in one line: clones include bots, mirrors, CI and the user's own
   clones; "unique" is only valid for the 14-day figure; the trend matters more than one week.
4. If the user asks why there is no heartbeat in their tools: because every plugin install
   is a `git clone` that GitHub counts anyway; this tool only keeps the count. Pointing
   people to a heartbeat is not needed for "is anyone using this".

## Files in the template

- `repos.txt`: repos to watch · `werkzeuge/sammeln.py`: collector, Python standard library
  only · `.github/workflows/statistik.yml`: weekly Action · `daten/`: one JSON per repo with
  daily values · `grafik/`: SVG charts, light and dark · `README.md` / `README.de.md`: guide,
  with the generated block between `<!-- statistik:start -->` and `<!-- statistik:end -->`.
