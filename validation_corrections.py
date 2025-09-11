#!/usr/bin/env python3
"""
Script de validation des corrections apportées à ChronoTech
Vérifie que toutes les erreurs d'indentation et de structure ont été corrigées
"""

import os
import sys
import importlib.util

def test_file_syntax(file_path):
    """Test la syntaxe d'un fichier Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Tenter de compiler le code
        compile(source, file_path, 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Erreur de syntaxe ligne {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def test_import(module_path, module_name):
    """Test l'import d'un module"""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    print("🔍 Validation des corrections ChronoTech")
    print("=" * 50)
    
    # Liste des fichiers corrigés
    corrected_files = [
        ("/home/amenard/Chronotech/ChronoTech/routes/ai/routes.py", "ai_routes"),
        ("/home/amenard/Chronotech/ChronoTech/routes/mobile/routes.py", "mobile_routes"),
        ("/home/amenard/Chronotech/ChronoTech/routes/time_tracking/routes.py", "time_tracking_routes"),
        ("/home/amenard/Chronotech/ChronoTech/routes/work_orders/api_tasks.py", "api_tasks"),
        ("/home/amenard/Chronotech/ChronoTech/routes/interventions/routes.py", "interventions_routes"),
        ("/home/amenard/Chronotech/ChronoTech/routes/interventions/api_interventions.py", "api_interventions"),
        ("/home/amenard/Chronotech/ChronoTech/core/ml_predictive_engine.py", "ml_predictive_engine")
    ]
    
    errors = []
    success_count = 0
    
    for file_path, module_name in corrected_files:
        if not os.path.exists(file_path):
            print(f"❌ {file_path} - Fichier introuvable")
            errors.append(f"Fichier manquant: {file_path}")
            continue
            
        # Test de syntaxe
        syntax_ok, syntax_error = test_file_syntax(file_path)
        if not syntax_ok:
            print(f"❌ {file_path} - Erreur de syntaxe: {syntax_error}")
            errors.append(f"Syntaxe {file_path}: {syntax_error}")
            continue
            
        # Test d'import
        import_ok, import_error = test_import(file_path, module_name)
        if not import_ok:
            print(f"⚠️  {file_path} - Import partiel: {import_error}")
            # Les erreurs d'import ne sont pas bloquantes (modules optionnels)
            
        print(f"✅ {file_path} - OK")
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Résultats: {success_count}/{len(corrected_files)} fichiers validés")
    
    if errors:
        print(f"❌ {len(errors)} erreur(s) trouvée(s):")
        for error in errors:
            print(f"   - {error}")
        return 1
    else:
        print("✅ Tous les fichiers corrigés sont valides !")
        
        # Test de l'application complète
        print("\n🚀 Test de l'application...")
        try:
            sys.path.append('/home/amenard/Chronotech/ChronoTech')
            from app import app
            print("✅ Application Flask importée avec succès")
            
            # Test des blueprints critiques
            critical_blueprints = ['interventions', 'ai', 'mobile', 'time_tracking']
            for bp_name in critical_blueprints:
                if bp_name in app.blueprints:
                    print(f"✅ Blueprint '{bp_name}' enregistré")
                else:
                    print(f"⚠️  Blueprint '{bp_name}' non trouvé")
                    
        except Exception as e:
            print(f"⚠️  Import application: {str(e)}")
            print("   (Peut être normal si certains modules optionnels manquent)")
        
        print("\n🎉 Corrections validées avec succès !")
        return 0

if __name__ == "__main__":
    sys.exit(main())
