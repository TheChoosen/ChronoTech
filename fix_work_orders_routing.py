#!/usr/bin/env python3
"""
🔧 CORRECTION PRIORITÉ 1: Standardisation work_orders.list_work_orders → work_orders.index
========================================================================================

Cette correction résout le problème critique de convention CRUD brisée dans le module work_orders.
"""

import os
import re

def fix_work_orders_routing():
    """Corriger le problème de routage work_orders"""
    
    print("🔧 CORRECTION PRIORITÉ 1: work_orders.list_work_orders → work_orders.index")
    print("=" * 80)
    
    # 1. Corriger la route principale dans work_orders/__init__.py
    work_orders_file = "/home/amenard/Chronotech/ChronoTech/routes/work_orders/__init__.py"
    
    print("📝 1. Correction de la route principale...")
    
    if os.path.exists(work_orders_file):
        with open(work_orders_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer la fonction list_work_orders par index
        content = content.replace('def list_work_orders():', 'def index():')
        
        # Ajouter un alias pour rétrocompatibilité
        alias_code = '''
# Alias de rétrocompatibilité
@bp.route('/list')
@requires_auth
def list_work_orders():
    """Alias de rétrocompatibilité pour list_work_orders"""
    return index()
'''
        
        # Insérer l'alias après la fonction index
        if 'def index():' in content and '@bp.route(\'/list\')' not in content:
            # Trouver la fin de la fonction index
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'def index():' in line:
                    # Trouver la fin de cette fonction (prochaine fonction ou fin de fichier)
                    j = i + 1
                    indent_level = len(line) - len(line.lstrip())
                    while j < len(lines):
                        if lines[j].strip() and (len(lines[j]) - len(lines[j].lstrip())) <= indent_level and lines[j].strip().startswith(('def ', '@', 'class ')):
                            break
                        j += 1
                    
                    # Insérer l'alias
                    lines.insert(j, alias_code)
                    content = '\n'.join(lines)
                    break
        
        with open(work_orders_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ work_orders/__init__.py corrigé")
    else:
        print("   ⚠️  Fichier work_orders/__init__.py non trouvé")
    
    # 2. Identifier tous les fichiers contenant url_for('work_orders.list_work_orders')
    print("\n📝 2. Recherche des références à corriger...")
    
    files_to_fix = []
    search_patterns = [
        r"url_for\(['\"]work_orders\.list_work_orders['\"]",
        r"work_orders\.list_work_orders"
    ]
    
    # Rechercher dans les templates
    template_dirs = [
        "/home/amenard/Chronotech/ChronoTech/templates",
        "/home/amenard/Chronotech/ChronoTech/routes"
    ]
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith(('.html', '.py')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for pattern in search_patterns:
                                    if re.search(pattern, content):
                                        files_to_fix.append(file_path)
                                        break
                        except:
                            continue
    
    # Éliminer les doublons
    files_to_fix = list(set(files_to_fix))
    
    print(f"   📊 {len(files_to_fix)} fichiers trouvés nécessitant une correction")
    
    # 3. Appliquer les corrections
    print("\n📝 3. Application des corrections...")
    
    corrections_applied = 0
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Remplacer les occurrences
            content = re.sub(
                r"url_for\(['\"]work_orders\.list_work_orders['\"]",
                "url_for('work_orders.index'",
                content
            )
            
            content = content.replace(
                "work_orders.list_work_orders",
                "work_orders.index"
            )
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                corrections_applied += 1
                print(f"   ✅ {file_path.split('/')[-1]} corrigé")
            
        except Exception as e:
            print(f"   ❌ Erreur sur {file_path}: {e}")
    
    print(f"\n📊 RÉSUMÉ:")
    print(f"   • {corrections_applied} fichiers corrigés")
    print(f"   • Alias de rétrocompatibilité ajouté")
    print(f"   • Convention CRUD restaurée")
    
    return corrections_applied

if __name__ == "__main__":
    fix_work_orders_routing()
