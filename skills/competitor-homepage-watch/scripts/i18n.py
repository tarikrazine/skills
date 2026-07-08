"""i18n.py — shared UI strings for the HTML report and dashboard.

The output language is chosen in watch.config.json (`"language": "fr" | "en" |
"es"`, default "fr"). Both render_report.py and build_dashboard.py import this
module so a single translation table drives every label. Add a language by
adding one entry to STRINGS and MONTHS — nothing else changes.
"""

MONTHS = {
    "fr": ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["", "January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "es": ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
}

STRINGS = {
    "fr": {
        # report
        "report_eyebrow": "Veille concurrentielle · Rapport quotidien",
        "report_title": "Ce qui a bougé le {date}",
        "report_meta": "Comparaison jour à jour{baseline}",
        "baseline": " · base {b}",
        "kpi_new": "Nouvelles", "kpi_ended": "Terminées",
        "kpi_modified": "Modifiées", "kpi_market": "En cours · marché",
        "sec_new": "Nouvelles opérations", "sec_ended": "Opérations terminées",
        "sec_modified": "Opérations modifiées", "sec_other": "Autres changements",
        "sec_result": "Résultat", "sec_issues": "Problèmes de surveillance",
        "no_change": "Aucun changement commercial détecté aujourd'hui.",
        "announced_end": "Fin annoncée · {end}",
        "tag_new": "Nouvelle opération", "tag_ended": "Opération terminée",
        "tag_modified": "Opération modifiée", "tag_other": "Changement notable",
        "chart_title": "Opérations en cours par enseigne",
        "chart_cap": "Nombre d'opérations actives",
        "chart_empty": "Aucune opération en cours dans le calendrier.",
        "footer": "competitor-homepage-watch · dates observées lors des passages quotidiens",
        "fetch_failed": "{slug} : capture en échec ({err})",
        # dashboard
        "dash_eyebrow": "Veille concurrentielle · Plan commercial du marché",
        "dash_meta": "Vue cumulée · {start} → {end} · {n} opérations",
        "dash_days": "{n} derniers jours",
        "dk_started": "Démarrées", "dk_ended": "Terminées",
        "dk_ongoing": "En cours", "dk_brands": "Enseignes actives",
        "dash_sec_gantt": "Frise des opérations", "dash_sec_detail": "Détail par enseigne",
        "th_op": "Opération", "th_disc": "Remise", "th_start": "Début", "th_end": "Fin",
        "ongoing": "en cours", "dash_empty": "Aucune opération.",
        "window_empty": "Aucune opération dans cette fenêtre.",
        "dash_footer": "competitor-homepage-watch · vue cumulée régénérée à la demande · dates observées lors des passages quotidiens",
    },
    "en": {
        "report_eyebrow": "Competitive intelligence · Daily report",
        "report_title": "What changed on {date}",
        "report_meta": "Day-over-day comparison{baseline}",
        "baseline": " · vs {b}",
        "kpi_new": "New", "kpi_ended": "Ended",
        "kpi_modified": "Modified", "kpi_market": "Live · market",
        "sec_new": "New operations", "sec_ended": "Ended operations",
        "sec_modified": "Modified operations", "sec_other": "Other changes",
        "sec_result": "Result", "sec_issues": "Monitoring issues",
        "no_change": "No commercial change detected today.",
        "announced_end": "Announced end · {end}",
        "tag_new": "New operation", "tag_ended": "Ended operation",
        "tag_modified": "Modified operation", "tag_other": "Notable change",
        "chart_title": "Live operations by brand",
        "chart_cap": "Number of active operations",
        "chart_empty": "No live operation in the calendar.",
        "footer": "competitor-homepage-watch · dates observed during daily runs",
        "fetch_failed": "{slug}: fetch failed ({err})",
        "dash_eyebrow": "Competitive intelligence · Market commercial plan",
        "dash_meta": "Cumulative view · {start} → {end} · {n} operations",
        "dash_days": "last {n} days",
        "dk_started": "Started", "dk_ended": "Ended",
        "dk_ongoing": "Live", "dk_brands": "Active brands",
        "dash_sec_gantt": "Operations timeline", "dash_sec_detail": "Breakdown by brand",
        "th_op": "Operation", "th_disc": "Discount", "th_start": "Start", "th_end": "End",
        "ongoing": "live", "dash_empty": "No operation.",
        "window_empty": "No operation in this window.",
        "dash_footer": "competitor-homepage-watch · cumulative view regenerated on demand · dates observed during daily runs",
    },
    "es": {
        "report_eyebrow": "Vigilancia competitiva · Informe diario",
        "report_title": "Lo que cambió el {date}",
        "report_meta": "Comparación día a día{baseline}",
        "baseline": " · vs {b}",
        "kpi_new": "Nuevas", "kpi_ended": "Finalizadas",
        "kpi_modified": "Modificadas", "kpi_market": "Activas · mercado",
        "sec_new": "Nuevas operaciones", "sec_ended": "Operaciones finalizadas",
        "sec_modified": "Operaciones modificadas", "sec_other": "Otros cambios",
        "sec_result": "Resultado", "sec_issues": "Problemas de seguimiento",
        "no_change": "Ningún cambio comercial detectado hoy.",
        "announced_end": "Fin anunciado · {end}",
        "tag_new": "Nueva operación", "tag_ended": "Operación finalizada",
        "tag_modified": "Operación modificada", "tag_other": "Cambio notable",
        "chart_title": "Operaciones activas por marca",
        "chart_cap": "Número de operaciones activas",
        "chart_empty": "Ninguna operación activa en el calendario.",
        "footer": "competitor-homepage-watch · fechas observadas en los pasos diarios",
        "fetch_failed": "{slug}: captura fallida ({err})",
        "dash_eyebrow": "Vigilancia competitiva · Plan comercial del mercado",
        "dash_meta": "Vista acumulada · {start} → {end} · {n} operaciones",
        "dash_days": "últimos {n} días",
        "dk_started": "Iniciadas", "dk_ended": "Finalizadas",
        "dk_ongoing": "Activas", "dk_brands": "Marcas activas",
        "dash_sec_gantt": "Cronología de operaciones", "dash_sec_detail": "Detalle por marca",
        "th_op": "Operación", "th_disc": "Descuento", "th_start": "Inicio", "th_end": "Fin",
        "ongoing": "activa", "dash_empty": "Ninguna operación.",
        "window_empty": "Ninguna operación en esta ventana.",
        "dash_footer": "competitor-homepage-watch · vista acumulada regenerada bajo demanda · fechas observadas en los pasos diarios",
    },
}


def resolve_lang(config):
    """Pick the output language from config: explicit `language`, else
    `language_hint`, else French. Unknown codes fall back to French."""
    lang = (config.get("language") or config.get("language_hint") or "fr").lower()[:2]
    return lang if lang in STRINGS else "fr"


def strings(lang):
    return STRINGS.get(lang, STRINGS["fr"])


def months(lang):
    return MONTHS.get(lang, MONTHS["fr"])
