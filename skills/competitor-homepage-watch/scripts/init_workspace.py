#!/usr/bin/env python3
"""init_workspace.py — [bootstrap] Create a ready-to-use watch workspace in one command.

Creates the directory structure, installs a starter watch.config.json (from the
bundled example unless --config points to a real one), and writes a CLAUDE.md
into the workspace so the agent maps everyday phrases ("lancer la veille",
"run the daily watch") to the full daily procedure automatically.

Safe to re-run: never overwrites an existing watch.config.json or CLAUDE.md.

Exit codes: 0 = workspace ready, 1 = bad usage.
Python 3.8+, standard library only.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

AGENT_MEMORY = """# Veille concurrentielle — instructions pour l'agent

Ce dossier est un workspace du skill `competitor-homepage-watch`
(config : `./watch.config.json`).

Quand l'utilisateur dit « lancer la veille », « lance la veille », « veille du
jour », « quoi de neuf chez les concurrents », « run the daily watch » ou toute
formulation équivalente, exécuter SANS reposer de question la procédure
quotidienne complète du skill competitor-homepage-watch sur ce workspace :

1. Fetch des snapshots du jour (`fetch_homepage.py --config ./watch.config.json`)
2. Diff contre la veille (`diff_snapshots.py . --out diffs/<date>.json`)
3. Classification des changements en événements (`events/<date>.json`)
4. Rapports : markdown (`reports/<date>.md`) ET version lisible
   (`render_report.py --workspace .`) — proposer d'ouvrir le HTML
5. Archivage calendrier (`update_calendar.py --workspace . --events events/<date>.json`)

Présenter ensuite le résumé du rapport en FRANÇAIS. Si rien n'a changé, le dire
simplement. Si une cible est bloquée ou en échec, le signaler dans la réponse.

Autres raccourcis à comprendre :
- « ouvre le rapport » → ouvrir le dernier `reports/<date>.html`
- « le calendrier » → `calendar/calendar.md` (analyses depuis `calendar/calendar.json`)
- « exporte vers Google Agenda » → indiquer `calendar/calendar.ics` (régénéré à
  chaque archivage ; s'importe dans Google Calendar / Outlook)
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="./competitor-watch", help="workspace directory to create")
    ap.add_argument("--config", default=None, help="existing watch.config.json to install (default: bundled example)")
    args = ap.parse_args()

    ws = Path(args.dir).expanduser().resolve()
    for sub in ("snapshots", "diffs", "events", "reports", "calendar"):
        (ws / sub).mkdir(parents=True, exist_ok=True)

    config_dest = ws / "watch.config.json"
    if config_dest.exists():
        print(f"kept existing config: {config_dest}")
    else:
        src = Path(args.config).expanduser().resolve() if args.config else \
            Path(__file__).resolve().parent.parent / "assets" / "watch.config.example.json"
        if not src.exists():
            print(f"ERROR: config source not found: {src}", file=sys.stderr)
            return 1
        shutil.copyfile(src, config_dest)
        print(f"config installed: {config_dest}")

    memory_dest = ws / "CLAUDE.md"
    if memory_dest.exists():
        print(f"kept existing agent memory: {memory_dest}")
    else:
        memory_dest.write_text(AGENT_MEMORY, encoding="utf-8")
        print(f"agent memory written: {memory_dest} (enables « lancer la veille »)")

    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    print(f"firecrawl key: {'OK (set)' if key else 'MISSING — exporter FIRECRAWL_API_KEY (indispensable pour les sites protégés + captures)'}")

    print()
    print("Workspace prêt. Prochaines étapes :")
    print(f"  1. Éditer {config_dest.name} (marques, pays, URLs, vos propres sites)")
    print("  2. Dire à l'agent : « lancer la veille »")
    print("     (jour 1 = photo de référence ; les alertes commencent au jour 2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
