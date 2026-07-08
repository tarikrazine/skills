# Automating the daily run

The daily run (fetch → diff → classify → report → archive) is designed to be
scheduled. The fetch/diff/archive steps are plain scripts; the classify/report
steps need an agent. Three proven setups, in order of simplicity:

## 1. Claude Code scheduled routine (recommended when available)

If the user's Claude Code has scheduled agents/routines (`/schedule`), create a
daily routine whose prompt is:

> Run the daily competitor homepage watch for the workspace at `<workspace>`,
> using the competitor-homepage-watch skill. Follow the full daily run:
> fetch, diff, classify, write the report, update the calendar. If nothing
> changed, say so briefly.

Pick a consistent hour (early morning local time — homepages usually switch
operations overnight or at 00:00). The routine's transcript is the alert; the
report file is the archive.

## 2. cron + `claude -p` (headless)

```cron
# every day at 07:30
30 7 * * * cd /path/to/workspace && claude -p "Run the daily competitor homepage watch for this workspace using the competitor-homepage-watch skill. Fetch, diff, classify, write reports/$(date +\%Y-\%m-\%d).md and update the calendar." >> watch.log 2>&1
```

Requirements: `claude` CLI authenticated on the machine, `FIRECRAWL_API_KEY`
exported in the cron environment (cron does not read the shell profile —
set it in the crontab or a sourced env file). Check `watch.log` and the
`reports/` directory to confirm the first scheduled runs succeeded.

For alerting beyond the log file, append a mail step:
`... && mail -s "Veille concurrentielle $(date +%F)" user@example.com < reports/$(date +%F).md`
(or any CLI mailer/Slack webhook curl the user already has).

## 3. n8n / workflow engine

Schedule Trigger (daily) → Execute Command node running the fetch script →
an agent step (Claude API or n8n AI Agent node) given the diff JSON and the
classification rules from `references/promo-detection.md` → Execute Command
node for `update_calendar.py` → Email/Slack node sending the report. Use this
when the client already standardizes automation on n8n and wants the alert in
a channel out of the box.

## Operational advice

- Run manually for 2–3 days before scheduling — this validates the target URLs
  and tunes expectations about noise before anyone trusts the alerts.
- Keep the workspace under version control (private repo) or backup: the
  snapshots + calendar ARE the competitive-intelligence asset; losing them
  loses the year's history.
- Weekend gaps are fine (the diff uses the latest earlier day), but a daily
  schedule gives day-accurate start/end dates — that precision is the point of
  the calendar.
- If Firecrawl quota is a concern: one scrape per target per day; size the plan
  to `targets × 31` scrapes/month.
