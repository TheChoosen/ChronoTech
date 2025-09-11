#!/usr/bin/env python3
"""
ANALYSE DES MODULES - UTILISATION MYSQL vs AUTRES
Identification des modules non-MySQL et standardisation
"""

import os
import re
from pathlib import Path

def analyze_db_usage():
    """Analyser l'utilisation des bases de données dans le projet"""
    
    print("🔍 ANALYSE DE L'UTILISATION DES BASES DE DONNÉES")
    print("="*60)
    
    # Modules utilisant MySQL correctement (avec config centralisée)
    mysql_correct_modules = [
        "core/database.py",
        "routes/customers/utils.py", 
        "routes/technicians/routes.py",
        "routes/work_orders/routes.py",
        "routes/analytics/routes.py",
        "migrations/apply_department_migration.py"
    ]
    
    # Modules utilisant MySQL avec config incorrecte (localhost, etc.)
    mysql_incorrect_modules = [
        "routes/interventions/api_interventions.py",
        "routes/work_orders/api_tasks.py", 
        "routes/interventions/routes.py",
        "routes/mobile/routes.py",
        "routes/ai/routes.py",
        "routes/time_tracking/routes.py",
        "models/sprint2_models.py",
        "utils.py"
    ]
    
    # Modules utilisant SQLite
    sqlite_modules = [
        "core/offline_sync.py",
        "core/optimized_mysql_sync.py", 
        "core/voice_to_action.py",
        "routes/api/sprint2_api.py"
    ]
    
    # Modules sans DB identifiée (potentiellement problématiques)  
    unknown_modules = [
        "routes/dashboard_api.py",
        "routes/api/contextual_chat.py",
        "services/websocket/websocket_server.py"
    ]
    
    print("\n✅ MODULES MYSQL CORRECTEMENT CONFIGURÉS:")
    for module in mysql_correct_modules:
        print(f"   • {module}")
    
    print("\n⚠️ MODULES MYSQL MAL CONFIGURÉS (localhost/root):")  
    for module in mysql_incorrect_modules:
        print(f"   • {module}")
    
    print("\n🗃️ MODULES UTILISANT SQLITE:")
    for module in sqlite_modules:
        print(f"   • {module}")
        
    print("\n❓ MODULES SANS DB CLAIRE:")
    for module in unknown_modules:
        print(f"   • {module}")
    
    return {
        'mysql_correct': mysql_correct_modules,
        'mysql_incorrect': mysql_incorrect_modules, 
        'sqlite': sqlite_modules,
        'unknown': unknown_modules
    }

def generate_standardization_plan():
    """Générer un plan de standardisation"""
    
    print("\n" + "="*60)
    print("📋 PLAN DE STANDARDISATION MYSQL")  
    print("="*60)
    
    print("\n🎯 OBJECTIFS:")
    print("1. Tous les modules utilisent MySQL 192.168.50.101")
    print("2. Configuration centralisée via core/config.py")
    print("3. Fonction get_db_connection() standardisée")
    print("4. SQLite conservé uniquement pour offline/cache")
    
    print("\n📝 ACTIONS REQUISES:")
    print("\n1. CORRIGER LES CONNEXIONS MYSQL:")
    print("   • Remplacer localhost par 192.168.50.101")
    print("   • Remplacer root par gsicloud") 
    print("   • Utiliser password TCOChoosenOne204$")
    print("   • Base de données: bdm")
    
    print("\n2. STANDARDISER get_db_connection():")
    print("   • Importer de core.database ou core.config")
    print("   • Supprimer les implémentations locales")
    print("   • Utiliser get_db_config() centralisé")
    
    print("\n3. MODULES SQLITE À CONSERVER:")  
    print("   • offline_sync.py - Synchronisation offline")
    print("   • voice_to_action.py - Cache vocal local")
    print("   • optimized_mysql_sync.py - Sync bidirectionnelle")
    
    print("\n4. DONNÉES DE DÉMONSTRATION:")
    print("   • Créer des scripts de seed par module")
    print("   • Peupler MySQL avec des données réalistes")
    print("   • Tester chaque fonctionnalité")

def main():
    """Fonction principale"""
    analysis = analyze_db_usage()
    generate_standardization_plan()
    
    print("\n🚀 PROCHAINES ÉTAPES:")
    print("1. Exécuter le script de standardisation")
    print("2. Créer les données de démonstration") 
    print("3. Tester tous les modules")
    print("4. Valider le fonctionnement complet")

if __name__ == "__main__":
    main()
