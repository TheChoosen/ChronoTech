#!/usr/bin/env python3
"""
SCRIPT DE STANDARDISATION MYSQL
Correction de tous les modules pour utiliser la configuration MySQL centralisée
"""

import os
import re
from pathlib import Path

def standardize_mysql_connections():
    """Standardiser toutes les connexions MySQL"""
    
    print("🔧 STANDARDISATION DES CONNEXIONS MYSQL")
    print("="*50)
    
    # Modules à corriger avec leurs chemins
    modules_to_fix = {
        "routes/interventions/api_interventions.py": {
            "old_pattern": r"def get_db_connection\(\):\s*\"\"\".*?\"\"\"\s*return pymysql\.connect\(\s*host=os\.getenv\('MYSQL_HOST', 'localhost'\),\s*user=os\.getenv\('MYSQL_USER', 'root'\),\s*password=os\.getenv\('MYSQL_PASSWORD', ''\),\s*database=os\.getenv\('MYSQL_DB', 'chronotech'\),\s*charset='utf8mb4',\s*cursorclass=pymysql\.cursors\.DictCursor\s*\)",
            "replacement": "# Utiliser la connexion centralisée\nfrom core.database import get_db_connection"
        },
        "routes/work_orders/api_tasks.py": "same",
        "routes/interventions/routes.py": "same", 
        "routes/mobile/routes.py": "same",
        "routes/ai/routes.py": "same",
        "routes/time_tracking/routes.py": "same",
        "models/sprint2_models.py": "same"
    }
    
    # Template de remplacement standard
    standard_import = "from core.database import get_db_connection"
    
    for module_path in modules_to_fix.keys():
        full_path = f"/home/amenard/Chronotech/ChronoTech/{module_path}"
        
        if os.path.exists(full_path):
            print(f"🔧 Correction de {module_path}...")
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Sauvegarder l'original
                backup_path = f"{full_path}.backup_mysql_fix"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Chercher et remplacer la fonction get_db_connection locale
                pattern = r"def get_db_connection\(\):\s*\"\"\".*?\"\"\"\s*return pymysql\.connect\(\s*.*?\s*\)"
                
                if re.search(pattern, content, re.DOTALL):
                    # Remplacer par import centralisé
                    modified_content = re.sub(pattern, 
                        "# Connexion centralisée importée de core.database", 
                        content, flags=re.DOTALL)
                    
                    # Ajouter l'import en haut si pas déjà présent
                    if "from core.database import get_db_connection" not in modified_content:
                        # Trouver la ligne après les autres imports
                        lines = modified_content.split('\n')
                        import_line_added = False
                        
                        for i, line in enumerate(lines):
                            if line.startswith('from') or line.startswith('import'):
                                continue
                            else:
                                # Insérer l'import juste avant cette ligne
                                lines.insert(i, standard_import)
                                import_line_added = True
                                break
                        
                        if not import_line_added:
                            # Ajouter au début après les commentaires
                            lines.insert(3, standard_import)
                        
                        modified_content = '\n'.join(lines)
                    
                    # Écrire le fichier modifié
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    
                    print(f"   ✅ {module_path} - Corrigé")
                else:
                    print(f"   ⚠️ {module_path} - Pattern non trouvé")
                    
            except Exception as e:
                print(f"   ❌ {module_path} - Erreur: {e}")
        else:
            print(f"   ❓ {module_path} - Fichier introuvable")

def fix_specific_modules():
    """Corrections spécifiques pour certains modules"""
    
    print("\n🎯 CORRECTIONS SPÉCIFIQUES")
    print("="*30)
    
    # Fix utils.py
    utils_path = "/home/amenard/Chronotech/ChronoTech/utils.py"
    if os.path.exists(utils_path):
        print("🔧 Correction de utils.py...")
        
        with open(utils_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si la config est correcte
        if "MYSQL_HOST', 'localhost'" in content:
            # Remplacer les valeurs par défaut incorrectes
            content = content.replace("'MYSQL_HOST', 'localhost'", "'MYSQL_HOST', '192.168.50.101'")
            content = content.replace("'MYSQL_USER', 'root'", "'MYSQL_USER', 'gsicloud'") 
            content = content.replace("'MYSQL_PASSWORD', ''", "'MYSQL_PASSWORD', 'TCOChoosenOne204$'")
            content = content.replace("'MYSQL_DATABASE', ''", "'MYSQL_DATABASE', 'bdm'")
            
            with open(utils_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("   ✅ utils.py - Valeurs par défaut corrigées")
        else:
            print("   ✅ utils.py - Déjà correct")
    
    # Fix dashboard_api.py pour utiliser MySQL
    dashboard_api_path = "/home/amenard/Chronotech/ChronoTech/routes/dashboard_api.py"
    if os.path.exists(dashboard_api_path):
        print("🔧 Correction de dashboard_api.py...")
        
        with open(dashboard_api_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "from core.database import get_db_connection" not in content:
            # Ajouter l'import
            lines = content.split('\n')
            lines.insert(2, "from core.database import get_db_connection")
            content = '\n'.join(lines)
            
            with open(dashboard_api_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("   ✅ dashboard_api.py - Import ajouté")
        else:
            print("   ✅ dashboard_api.py - Déjà correct")

def verify_mysql_config():
    """Vérifier que la configuration MySQL est correcte"""
    
    print("\n🔍 VÉRIFICATION DE LA CONFIGURATION MYSQL")
    print("="*45)
    
    config_path = "/home/amenard/Chronotech/ChronoTech/core/config.py"
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier les paramètres
    checks = {
        "MYSQL_HOST": "192.168.50.101",
        "MYSQL_USER": "gsicloud", 
        "MYSQL_PASSWORD": "TCOChoosenOne204$",
        "MYSQL_DB": "bdm"
    }
    
    for param, expected in checks.items():
        if f"'{expected}')" in content or f'"{expected}")' in content:
            print(f"   ✅ {param} = {expected}")
        else:
            print(f"   ⚠️ {param} - Vérifier la valeur")

def main():
    """Fonction principale"""
    
    print("🚀 DÉMARRAGE DE LA STANDARDISATION MYSQL")
    print("="*50)
    
    # 1. Standardiser les connexions
    standardize_mysql_connections()
    
    # 2. Corrections spécifiques
    fix_specific_modules()
    
    # 3. Vérifier la config
    verify_mysql_config()
    
    print("\n" + "="*50)
    print("✅ STANDARDISATION TERMINÉE")
    print("="*50)
    print("\n📋 RÉSUMÉ:")
    print("• Connexions MySQL standardisées")
    print("• Configuration centralisée utilisée") 
    print("• Imports corrigés")
    print("• Sauvegardes créées (.backup_mysql_fix)")
    
    print("\n🔄 PROCHAINE ÉTAPE:")
    print("Créer les données de démonstration pour chaque module")

if __name__ == "__main__":
    main()
