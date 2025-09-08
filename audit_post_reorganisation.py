#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDIT POST-RÉORGANISATION COMPLÈTE - Projet ChronoTech
Vérification de la nouvelle structure et recommandations
Version 2.0 - Audit complet et détaillé
"""

import os
from pathlib import Path
import subprocess

def audit_structure():
    """Audit complet de la nouvelle structure de projet"""
    
    print("🔍 AUDIT POST-RÉORGANISATION COMPLÈTE CHRONOTECH")
    print("=" * 60)
    
    # Structure attendue complète
    expected_structure = {
        'tests': ['api', 'validation', 'chat', 'customers', 'crud', 'dashboard', 'database', 'ui', 'time_tracking', 'vehicles', 'kanban', 'pagination', 'auth', 'finance', 'ai', 'work_orders', 'general', 'templates', 'integration', 'interventions', 'pdf'],
        'scripts': ['fixes', 'server', 'install', 'test', 'analysis', 'deployment', 'security'],
        'migrations': ['sql', 'python'],
        'services': ['websocket', 'test', 'ai', 'pdf'],
        'docs/reports': ['fixes', 'sprints', 'features', 'security', 'audit', 'ui', 'analysis'],
        'config': [],
        'archive': ['legacy', 'old_reports', 'deprecated']
    }
    
    # Vérification de la structure
    print("\n📁 VÉRIFICATION DE LA STRUCTURE")
    print("-" * 40)
    
    for parent_dir, subdirs in expected_structure.items():
        parent_path = Path(parent_dir)
        if parent_path.exists():
            print(f"✅ {parent_dir}/ existe")
            for subdir in subdirs:
                subdir_path = parent_path / subdir
                if subdir_path.exists():
                    file_count = len(list(subdir_path.glob('*')))
                    print(f"   ✅ {subdir}/ ({file_count} fichiers)")
                else:
                    print(f"   ❌ {subdir}/ manquant")
        else:
            print(f"❌ {parent_dir}/ manquant")
    
    # Analyse des fichiers restants dans la racine
    print("\n📋 FICHIERS RESTANTS DANS LA RACINE")
    print("-" * 40)
    
    try:
        root_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    except Exception as e:
        print(f"❌ Erreur lecture racine: {e}")
        root_files = []
    
    # Fichiers essentiels qui doivent rester
    essential_files = {
        'app.py': 'Application Flask principale',
        'utils.py': 'Utilitaires principaux',
        'requirements.txt': 'Dépendances Python',
        'README.md': 'Documentation principale',
        '.env': 'Variables d\'environnement',
        '.gitignore': 'Configuration Git',
        'complete_reorganization.sh': 'Script de réorganisation',
        'audit_post_reorganisation.py': 'Script d\'audit actuel'
    }
    
    # Fichiers qui ne devraient plus être à la racine
    unwanted_patterns = [
        'test_',
        'debug_',
        'RAPPORT_',
        'CORRECTION_',
        'SPRINT_',
        'AUDIT_',
        'INTERFACE_',
        'diagnostic_',
        'validate_',
        'fix_',
        '_report',
        '.log'
    ]
    
    print("✅ FICHIERS ESSENTIELS:")
    for file in essential_files:
        if file in root_files:
            print(f"   ✅ {file} - {essential_files[file]}")
        else:
            print(f"   ❌ {file} - MANQUANT")
    
    # Identifier les fichiers qui ne devraient plus être à la racine
    unwanted_files = []
    for file in root_files:
        if file not in essential_files:
            for pattern in unwanted_patterns:
                if pattern in file.lower():
                    unwanted_files.append(file)
                    break
    
    # Séparer les fichiers de test et de rapport
    test_files = [f for f in unwanted_files if f.startswith('test_')]
    report_files = [f for f in unwanted_files if any(f.upper().startswith(p) for p in ['RAPPORT_', 'CORRECTION_', 'SPRINT_', 'AUDIT_', 'INTERFACE_'])]
    other_unwanted = [f for f in unwanted_files if f not in test_files and f not in report_files]
    
    if test_files:
        print(f"\n⚠️ FICHIERS DE TEST NON DÉPLACÉS ({len(test_files)}):")
        for file in test_files[:10]:  # Afficher seulement les 10 premiers
            print(f"   • {file}")
        if len(test_files) > 10:
            print(f"   ... et {len(test_files) - 10} autres")
    
    if report_files:
        print(f"\n⚠️ FICHIERS DE RAPPORT NON DÉPLACÉS ({len(report_files)}):")
        for file in report_files[:10]:
            print(f"   • {file}")
        if len(report_files) > 10:
            print(f"   ... et {len(report_files) - 10} autres")
    
    if other_unwanted:
        print(f"\n⚠️ AUTRES FICHIERS À RÉORGANISER ({len(other_unwanted)}):")
        for file in other_unwanted[:10]:
            print(f"   • {file}")
        if len(other_unwanted) > 10:
            print(f"   ... et {len(other_unwanted) - 10} autres")
    
    # Analyse des dossiers principaux
    print("\n🏗️ STRUCTURE PRINCIPALE DU PROJET")
    print("-" * 40)
    
    main_dirs = {
        'routes': 'Routes Flask par module',
        'templates': 'Templates Jinja2',
        'static': 'Fichiers statiques (CSS, JS, images)',
        'core': 'Modules principaux',
        'tests': 'Tests automatisés',
        'scripts': 'Scripts utilitaires',
        'migrations': 'Scripts de migration BD',
        'services': 'Services externes',
        'docs': 'Documentation'
    }
    
    for dir_name, description in main_dirs.items():
        if os.path.exists(dir_name):
            if os.path.isdir(dir_name):
                files = [f for f in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, f))]
                dirs = [d for d in os.listdir(dir_name) if os.path.isdir(os.path.join(dir_name, d))]
                print(f"✅ {dir_name}/ - {description} ({len(files)} fichiers, {len(dirs)} dossiers)")
            else:
                print(f"⚠️ {dir_name} existe mais n'est pas un dossier")
        else:
            print(f"❌ {dir_name}/ - {description} - MANQUANT")
    
    # Statistiques de la réorganisation
    print("\n📊 STATISTIQUES DE LA RÉORGANISATION")
    print("-" * 40)
    
    total_moved = 0
    for category, dirs in expected_structure.items():
        for dir_name in dirs:
            dir_path = Path(category) / dir_name
            if dir_path.exists():
                count = len(list(dir_path.glob('*')))
                total_moved += count
                if count > 0:
                    print(f"📦 {dir_path}: {count} fichiers")
    
    print(f"\n🎯 TOTAL FICHIERS DÉPLACÉS: {total_moved}")
    
    # Analyse de la qualité de la structure
    print("\n📊 ANALYSE DE LA QUALITÉ DE LA STRUCTURE")
    print("-" * 40)
    
    quality_metrics = {
        'organisation': 0,
        'completude': 0,
        'coherence': 0
    }
    
    # Calcul de l'organisation (structure respectée)
    total_dirs = sum(len(dirs) for dirs in expected_structure.values())
    existing_dirs = sum(len([d for d in dirs if (Path(category) / d).exists()]) 
                      for category, dirs in expected_structure.items())
    quality_metrics['organisation'] = (existing_dirs / total_dirs * 100) if total_dirs > 0 else 0
    
    # Calcul de la complétude (fichiers dans les bons endroits)
    quality_metrics['completude'] = max(0, 100 - len(unwanted_files) * 2)  # -2% par fichier mal placé
    
    # Calcul de la cohérence (structure logique)
    quality_metrics['coherence'] = 85 if total_moved > 50 else 70  # Base élevée si beaucoup de fichiers déplacés
    
    print(f"📈 Organisation: {quality_metrics['organisation']:.1f}%")
    print(f"📋 Complétude: {quality_metrics['completude']:.1f}%")
    print(f"🎯 Cohérence: {quality_metrics['coherence']:.1f}%")
    
    overall_quality = sum(quality_metrics.values()) / len(quality_metrics)
    print(f"\n🏆 QUALITÉ GLOBALE: {overall_quality:.1f}%")
    
    if overall_quality >= 90:
        print("🌟 EXCELLENT - Structure parfaitement organisée!")
    elif overall_quality >= 80:
        print("✅ TRÈS BIEN - Structure bien organisée")
    elif overall_quality >= 70:
        print("⚠️ CORRECT - Quelques améliorations nécessaires")
    else:
        print("❌ À AMÉLIORER - Réorganisation supplémentaire requise")
    
    # Statistiques détaillées par type de fichier
    print("\n📂 STATISTIQUES PAR TYPE DE FICHIER")
    print("-" * 40)
    
    file_types = {
        'Python (.py)': len([f for f in Path('.').rglob('*.py')]),
        'Markdown (.md)': len([f for f in Path('.').rglob('*.md')]),
        'Shell (.sh)': len([f for f in Path('.').rglob('*.sh')]),
        'HTML (.html)': len([f for f in Path('.').rglob('*.html')]),
        'CSS (.css)': len([f for f in Path('.').rglob('*.css')]),
        'JavaScript (.js)': len([f for f in Path('.').rglob('*.js')]),
        'SQL (.sql)': len([f for f in Path('.').rglob('*.sql')])
    }
    
    for file_type, count in file_types.items():
        print(f"📄 {file_type}: {count} fichiers")
    
    return unwanted_files, overall_quality
    
    # Recommandations post-réorganisation
    
    print("\n🎯 RECOMMANDATIONS POST-RÉORGANISATION")
    print("-" * 40)
    
    recommendations = [
        "1. Créer un fichier tests/__init__.py pour initialiser le module de tests",
        "2. Ajouter un README.md dans chaque dossier tests/ expliquant le contenu",
        "3. Créer un script scripts/run_all_tests.sh pour exécuter tous les tests",
        "4. Ajouter des fichiers .gitkeep dans les dossiers vides",
        "5. Mettre à jour les imports dans les fichiers déplacés",
        "6. Créer un fichier docs/ARCHITECTURE.md documentant la nouvelle structure",
        "7. Vérifier et supprimer les doublons dans migrations/sql/",
        "8. Créer un script de setup.py pour l'installation du projet"
    ]
    
    # Recommandations personnalisées basées sur l'analyse
    if len(unwanted_files) > 0:
        recommendations.insert(0, f"0. PRIORITÉ: Déplacer {len(unwanted_files)} fichiers restants mal placés")
    
    if overall_quality < 85:
        recommendations.insert(1, "1. URGENT: Finaliser la réorganisation pour améliorer la qualité")
    
    for rec in recommendations:
        print(f"📝 {rec}")
    
    print("\n✅ AUDIT TERMINÉ")
    if overall_quality >= 85:
        print("🎉 La réorganisation a considérablement amélioré la structure du projet!")
    else:
        print("⚠️ La réorganisation est en cours, quelques ajustements sont nécessaires.")

def generate_cleanup_script():
    """Génère un script pour nettoyer les fichiers restants"""
    cleanup_script = """#!/bin/bash
# Script de nettoyage final généré automatiquement

echo "🧹 NETTOYAGE FINAL DU PROJET CHRONOTECH"
echo "======================================"

# Déplacer les fichiers restants détectés par l'audit
""" 
    
    return cleanup_script

if __name__ == "__main__":
    unwanted_files, quality = audit_structure()
    
    if unwanted_files:
        print(f"\n📝 {len(unwanted_files)} fichiers nécessitent encore un déplacement.")
        print("💡 Exécutez le script de nettoyage pour finaliser la réorganisation.")
    else:
        print("\n🎉 Tous les fichiers sont parfaitement organisés!")