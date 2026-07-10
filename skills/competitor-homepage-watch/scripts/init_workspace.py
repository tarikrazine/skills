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

Présenter ensuite le résumé du rapport en FRANÇAIS, puis proposer la vue
d'ensemble du mois (`build_dashboard.py`, voir raccourci « tableau de bord »). Si rien n'a changé, le dire
simplement. Si une cible est bloquée ou en échec, le signaler dans la réponse.

Autres raccourcis à comprendre :
- « ouvre le rapport » → ouvrir le dernier `reports/<date>.html` (`open`)
- « tableau de bord » / « le plan du mois » / « vue d'ensemble » / « dashboard »
  → générer `dashboard.html` (`build_dashboard.py --workspace . --month <AAAA-MM>`,
  ou `--days N`) et l'ouvrir. C'est la vue CUMULÉE du mois (frise de toutes les
  opérations), à distinguer du rapport quotidien qui ne montre que les
  changements du jour. À proposer spontanément en fin de veille.
- « ouvre le dossier » → ouvrir ce workspace dans le gestionnaire de fichiers
  (`open .` sur macOS, `xdg-open .` sur Linux, `explorer .` sur Windows)
- « ouvre la config » / « ajouter un concurrent » → ouvrir `watch.config.json`
  dans un éditeur (`open -t`) et aider à remplir marque/pays/URL pendant que
  le fichier est sous les yeux de l'utilisateur
- « la clé firecrawl » / « où mettre la clé » → expliquer qu'elle vient de
  firecrawl.dev (menu API Keys), puis proposer de l'ajouter au profil shell
  (`echo 'export FIRECRAWL_API_KEY="fc-..."' >> ~/.zshrc`) avec l'accord
  explicite de l'utilisateur, jamais silencieusement ; vérifier ensuite avec
  un fetch d'une seule cible
- « Norauto est bloqué » / « site protégé » / « pas de screenshot sur X » /
  « la clé scrapfly » → certaines enseignes (Norauto, Midas, ATU…) sont derrière
  DataDome et bloquent tous les moteurs gratuits. Le fetch le détecte et affiche
  une note « SETUP NEEDED ». Solution par défaut : le Web Unlocker ScrapFly —
  inscription GRATUITE sans carte (scrapfly.io/register, 1000 crédits), copier
  la clé, l'ajouter au profil shell avec l'accord de l'utilisateur
  (`echo 'export SCRAPFLY_API_KEY="..."' >> ~/.zshrc`), puis relancer la veille.
  Une fois la clé posée, ces sites remontent automatiquement la VRAIE page +
  screenshot, sans config par cible.
- « le calendrier » → `calendar/calendar.md` (analyses depuis `calendar/calendar.json`)
- « exporte vers Google Agenda » → révéler `calendar/calendar.ics` dans le
  gestionnaire de fichiers (`open -R calendar/calendar.ics`) et guider
  l'import pas à pas : calendar.google.com → Paramètres → Importer et
  exporter → Importer, idéalement dans un agenda dédié « Veille concurrence »
  (réimport = mise à jour, pas de doublons)

Langue des rapports : le champ `"language"` de watch.config.json fixe la langue
du rapport quotidien ET du tableau de bord (`fr`, `en`, `es`). C'est la langue
des rapports de l'utilisateur, indépendante de la langue des sites surveillés.
Le demander au setup si ce n'est pas déjà réglé.

Style d'accompagnement : l'utilisateur n'est pas forcément technique. Ne jamais
se contenter de citer un chemin de fichier — proposer de l'ouvrir. Après
l'initialisation, proposer spontanément dans l'ordre : (1) ouvrir le dossier,
(2) ouvrir la config pour ajouter les enseignes à surveiller + choisir la langue
des rapports, (3) configurer la clé Firecrawl si elle manque, (4) lancer la
première veille.
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

    fc_cli = shutil.which("firecrawl")
    fc_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if fc_cli:
        firecrawl_state = "OK (firecrawl CLI installed — it self-authenticates; no key needed)"
    elif fc_key:
        firecrawl_state = "OK (FIRECRAWL_API_KEY set)"
    else:
        firecrawl_state = ("NOT SET UP — install the Firecrawl skill "
                           "(npx skills add firecrawl/cli@firecrawl) so the agent can crawl; "
                           "without it, protected competitor sites return 403")
    print(f"firecrawl: {firecrawl_state}")

    scrapfly_key = os.environ.get("SCRAPFLY_API_KEY", "").strip()
    if scrapfly_key:
        unlocker_state = "OK (SCRAPFLY_API_KEY set — DataDome-class sites auto-unlock with screenshots)"
    else:
        unlocker_state = ("not set — the watch works without it; hardened competitors "
                          "(Norauto/Midas/ATU-class) will print a one-time free signup note "
                          "(scrapfly.io/register, no card) the first time they're detected")
    print(f"web-unlocker: {unlocker_state}")

    print()
    print("Workspace prêt. Prochaines étapes :")
    print(f"  1. Éditer {config_dest.name} (marques, pays, URLs, vos propres sites)")
    print("  2. Dire à l'agent : « lancer la veille »")
    print("     (jour 1 = photo de référence ; les alertes commencent au jour 2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
