#!/usr/bin/env python3
"""Archive / restauration des templates legacy clients.

Objectif:
  - Déplacer les templates legacy (finances.html, documents.html, analytics.html, consents.html)
    vers un dossier d'archive horodaté: archive/templates_legacy/YYYYMMDD_HHMMSS/
  - Générer un manifest JSON pour tracer l'opération (fichiers, hash, chemin origine, chemin archive).
  - Option de dry-run pour voir ce qui serait fait.
  - Option de restauration à partir d'un manifest.

Usage:
  # Archiver les 4 templates legacy par défaut
  python scripts/archive_legacy_templates.py --archive

  # Archiver seulement finances et documents
  python scripts/archive_legacy_templates.py --archive finances documents

  # Dry-run (aucune modification sur disque)
  python scripts/archive_legacy_templates.py --archive --dry-run

  # Restaurer depuis un manifest
  python scripts/archive_legacy_templates.py --restore archive/templates_legacy/20250930_101500/manifest.json

Notes:
  - Le script vérifie que chaque template contient le commentaire "DEPRECATED TEMPLATE" avant de l'archiver (sécurité).
  - Un fichier README_ARCHIVE.txt est ajouté dans le dossier d'archive avec un résumé.
  - Pour supprimer la référence dans la documentation, une option --update-doc peut enlever les lignes listant les templates dans docs/UI_STYLE_GUIDE.md.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates" / "customers"
DOC_UI_GUIDE = REPO_ROOT / "docs" / "UI_STYLE_GUIDE.md"
ARCHIVE_BASE = REPO_ROOT / "archive" / "templates_legacy"
DEFAULT_TEMPLATES = [
    "finances.html",
    "documents.html",
    "analytics.html",
    "consents.html",
]
DEPRECATION_MARKER = "DEPRECATED TEMPLATE"

class ArchiveError(Exception):
    pass

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def validate_templates(files: List[str]) -> List[Path]:
    resolved = []
    for name in files:
        p = TEMPLATES_DIR / name
        if not p.exists():
            raise ArchiveError(f"Template introuvable: {p}")
        text = p.read_text(errors='ignore')
        if DEPRECATION_MARKER not in text:
            raise ArchiveError(f"Le template {name} ne contient pas le marqueur de dépréciation, archivage bloqué.")
        resolved.append(p)
    return resolved

def archive_templates(files: List[str], dry_run: bool=False, update_doc: bool=False) -> Path:
    targets = validate_templates(files)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_dir = ARCHIVE_BASE / ts
    manifest_path = archive_dir / "manifest.json"
    if dry_run:
        print(f"[DRY-RUN] Archive dir prévu: {archive_dir}")
    else:
        archive_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Dict[str, str]] = {
        "timestamp": ts,
        "templates": []
    }

    for src in targets:
        rel = src.relative_to(REPO_ROOT)
        dst = archive_dir / src.name
        file_hash = compute_sha256(src)
        print(f"Archiver {rel} -> {dst.relative_to(REPO_ROOT)} (sha256={file_hash[:12]}...)")
        if not dry_run:
            shutil.move(str(src), str(dst))
        manifest["templates"].append({
            "original_path": str(rel),
            "archived_path": str(dst.relative_to(REPO_ROOT)),
            "sha256": file_hash
        })

    if not dry_run:
        # README archive
        (archive_dir / "README_ARCHIVE.txt").write_text(
            "Templates legacy archivés\n" +
            "Ce dossier contient les templates dépréciés retirés du runtime.\n"
        )
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"Manifest créé: {manifest_path}")

    if update_doc:
        update_ui_style_guide(files, dry_run)

    return manifest_path

def update_ui_style_guide(files: List[str], dry_run: bool=False):
    if not DOC_UI_GUIDE.exists():
        print(f"[WARN] Fichier doc introuvable: {DOC_UI_GUIDE}")
        return
    content = DOC_UI_GUIDE.read_text().splitlines()
    lowered = [f.lower() for f in files]
    new_lines = []
    removed = 0
    for line in content:
        if any(name in line.lower() for name in lowered):
            if "DEPRECATED" in line.upper() or "LEGACY" in line.upper():
                # ligne déjà marquée, on la garde
                new_lines.append(line)
            else:
                print(f"Retrait ligne doc: {line}")
                removed += 1
                continue
        else:
            new_lines.append(line)
    if not dry_run and removed:
        DOC_UI_GUIDE.write_text("\n".join(new_lines) + "\n")
        print(f"Documentation mise à jour ({removed} lignes supprimées)")


def restore_from_manifest(manifest_file: Path, dry_run: bool=False):
    if not manifest_file.exists():
        raise ArchiveError(f"Manifest introuvable: {manifest_file}")
    data = json.loads(manifest_file.read_text())
    templates = data.get("templates", [])
    for entry in templates:
        archived = REPO_ROOT / entry["archived_path"]
        original = REPO_ROOT / entry["original_path"]
        if not archived.exists():
            print(f"[WARN] Archivé manquant: {archived}")
            continue
        if original.exists():
            print(f"[SKIP] Existe déjà: {original}")
            continue
        print(f"Restaurer {archived.relative_to(REPO_ROOT)} -> {original.relative_to(REPO_ROOT)}")
        if not dry_run:
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archived, original)


def parse_args():
    ap = argparse.ArgumentParser(description="Archive ou restaure des templates legacy")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--archive', nargs='*', metavar='TEMPLATE', help='Archiver les templates (liste facultative)')
    g.add_argument('--restore', metavar='MANIFEST', help='Restaurer depuis un manifest JSON')
    ap.add_argument('--dry-run', action='store_true', help='Ne rien écrire, montrer seulement les actions')
    ap.add_argument('--update-doc', action='store_true', help='Mettre à jour UI_STYLE_GUIDE.md pour retirer les références')
    return ap.parse_args()

def main():
    args = parse_args()
    try:
        if args.archive is not None:
            templates = args.archive if args.archive else DEFAULT_TEMPLATES
            manifest = archive_templates(templates, dry_run=args.dry_run, update_doc=args.update_doc)
            if args.dry_run:
                print("[DRY-RUN] Fin - aucune modification persistée")
            else:
                print(f"Archivage terminé. Manifest: {manifest}")
        elif args.restore:
            restore_from_manifest(Path(args.restore), dry_run=args.dry_run)
            if args.dry_run:
                print("[DRY-RUN] Restauration simulée terminée")
            else:
                print("Restauration terminée")
    except ArchiveError as e:
        print(f"[ERREUR] {e}")
        raise SystemExit(1)

if __name__ == '__main__':
    main()
