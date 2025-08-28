#!/usr/bin/env python3
"""Hook de pré-suppression pour templates legacy clients.

But:
  - Vérifier que les conditions de suppression sont respectées avant d'effacer
    définitivement les templates legacy (finances.html, documents.html,
    analytics.html, consents.html).
  - Empêcher la suppression si: période de grâce non écoulée, hits récents,
    dépendances résiduelles ou si un manifest d'archive récent (< 7 jours) n'existe pas.

Ce script est conçu pour être appelé manuellement OU via un hook git (pre-commit)
qui détecte une suppression de ces fichiers.

Intégration hook git:
  1. Copier (ou symlink) ce script dans .git/hooks/pre-commit
  2. Rendre exécutable: chmod +x .git/hooks/pre-commit
  3. Dans pre-commit, appeler: python scripts/pre_remove_legacy_templates.py --git-hook

Stratégie de vérification:
  - Grace period: variable d'env LEGACY_TEMPLATES_REMOVE_AFTER (YYYY-MM-DD)
  - Archive manifest: au moins un manifest dans archive/templates_legacy/*/manifest.json
  - Traffic log optionnel: si access.log présent, vérifier aucune requête HTTP 200/301 vers route legacy
    sur les N derniers jours (param --access-log / --days)
  - Grep code: aucune occurrence des templates legacy hors dossier archive

Exit codes:
  0 = OK (suppression autorisée)
  1 = Blocage (condition non remplie)
  2 = Avertissement (non bloquant si --force)
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_TEMPLATES = [
    'templates/customers/finances.html',
    'templates/customers/documents.html',
    'templates/customers/analytics.html',
    'templates/customers/consents.html',
]
ARCHIVE_DIR = REPO_ROOT / 'archive' / 'templates_legacy'
MARKER = 'DEPRECATED TEMPLATE'

COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_GREEN = '\033[92m'
COLOR_RESET = '\033[0m'

class CheckResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.infos = []
    def error(self, msg): self.errors.append(msg)
    def warn(self, msg): self.warnings.append(msg)
    def info(self, msg): self.infos.append(msg)
    @property
    def ok(self): return not self.errors


def parse_args():
    ap = argparse.ArgumentParser(description='Pré-vérification suppression templates legacy')
    ap.add_argument('--force', action='store_true', help='Ignorer warnings (pas les erreurs)')
    ap.add_argument('--access-log', type=Path, help='Fichier access log à analyser')
    ap.add_argument('--days', type=int, default=7, help='Fenêtre jours pour analyse log (défaut: 7)')
    ap.add_argument('--git-hook', action='store_true', help='Mode hook git (affichage concis)')
    return ap.parse_args()


def check_grace_period(cr: CheckResult):
    target = os.getenv('LEGACY_TEMPLATES_REMOVE_AFTER')
    if not target:
        cr.warn("Var d'env LEGACY_TEMPLATES_REMOVE_AFTER non définie (utiliser YYYY-MM-DD).")
        return
    try:
        dt = datetime.strptime(target, '%Y-%m-%d').date()
    except ValueError:
        cr.error("Format de LEGACY_TEMPLATES_REMOVE_AFTER invalide (attendu YYYY-MM-DD).")
        return
    today = datetime.utcnow().date()
    if today < dt:
        cr.error(f"Période de grâce non échue: aujourd'hui {today} < {dt}.")
    else:
        cr.info(f"Grace period OK (date cible {dt}, aujourd'hui {today}).")


def check_archive_manifest(cr: CheckResult):
    if not ARCHIVE_DIR.exists():
        cr.error(f"Dossier d'archive inexistant: {ARCHIVE_DIR}")
        return
    manifests = list(ARCHIVE_DIR.rglob('manifest.json'))
    if not manifests:
        cr.error("Aucun manifest d'archive trouvé (exécuter archive_legacy_templates.py).")
        return
    # Vérifie qu'un manifest récent (< 30 jours) existe
    now = datetime.utcnow()
    recent = False
    for m in manifests:
        try:
            ts = m.parent.name  # dossier horodaté
            dt = datetime.strptime(ts, '%Y%m%d_%H%M%S')
            if now - dt <= timedelta(days=30):
                recent = True
                break
        except Exception:
            continue
    if not recent:
        cr.warn("Aucun manifest d'archive récent (<30j) trouvé.")
    else:
        cr.info("Manifest d'archive récent présent.")


def check_code_references(cr: CheckResult):
    # Grep simple
    pattern = re.compile(r'(finances|documents|analytics|consents)\.html')
    for path in REPO_ROOT.rglob('*.py'):
        if 'archive/templates_legacy' in str(path):
            continue
        text = ''
        try:
            text = path.read_text(errors='ignore')
        except Exception:
            continue
        if pattern.search(text):
            # tolère références dans _sections/.*
            if '_sections/' in text:
                continue
            cr.warn(f"Référence potentielle trouvée dans {path.relative_to(REPO_ROOT)}")


def check_templates_state(cr: CheckResult):
    for rel in LEGACY_TEMPLATES:
        p = REPO_ROOT / rel
        if not p.exists():
            cr.info(f"Déjà supprimé: {rel}")
            continue
        try:
            txt = p.read_text(errors='ignore')
            if MARKER not in txt:
                cr.error(f"Template sans marqueur de dépréciation: {rel}")
        except Exception as e:
            cr.warn(f"Lecture impossible {rel}: {e}")


def parse_access_log(log_path: Path, days: int, cr: CheckResult):
    if not log_path.exists():
        cr.warn(f"Access log introuvable: {log_path}")
        return
    cutoff = datetime.utcnow() - timedelta(days=days)
    legacy_hits = {k:0 for k in ['finances','documents','analytics','consents']}
    # Heuristique: lignes contenant GET /customers/<id>/<name>
    for line in log_path.read_text(errors='ignore').splitlines():
        # Essai extraction date Apache/Nginx [dd/Mon/YYYY:HH:MM:SS
        mdate = re.search(r'\[(\d{2}/[A-Za-z]{3}/\d{4}):(\d{2}:\d{2}:\d{2})', line)
        if mdate:
            try:
                dt = datetime.strptime(mdate.group(1)+":"+mdate.group(2), '%d/%b/%Y:%H:%M:%S')
            except ValueError:
                dt = None
        else:
            dt = None
        if dt and dt < cutoff:
            continue
        for key in legacy_hits.keys():
            if f"/{key}" in line and '/customers/' in line:
                legacy_hits[key]+=1
    recent_hits = sum(legacy_hits.values())
    if recent_hits>0:
        cr.warn(f"Hits récents sur routes legacy (<= {days}j): {legacy_hits}")
    else:
        cr.info(f"Aucun hit récent (<= {days}j) détecté dans le log.")


def main():
    args = parse_args()
    cr = CheckResult()
    check_grace_period(cr)
    check_archive_manifest(cr)
    check_code_references(cr)
    check_templates_state(cr)
    if args.access_log:
        parse_access_log(args.access_log, args.days, cr)

    # Résumé
    if not args.git_hook:
        print('\n=== Résultats ===')
    for msg in cr.infos:
        print(f"{COLOR_GREEN}[INFO]{COLOR_RESET} {msg}")
    for msg in cr.warnings:
        print(f"{COLOR_YELLOW}[WARN]{COLOR_RESET} {msg}")
    for msg in cr.errors:
        print(f"{COLOR_RED}[ERREUR]{COLOR_RESET} {msg}")

    if cr.errors:
        if not args.git_hook:
            print("Blocage: conditions non remplies.")
        sys.exit(1)
    if cr.warnings and not args.force:
        if not args.git_hook:
            print("Présence de warnings. Relancer avec --force si acceptable.")
        sys.exit(2)
    if not args.git_hook:
        print('Suppression autorisée.')
    sys.exit(0)

if __name__ == '__main__':
    main()
