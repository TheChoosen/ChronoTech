#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier les endpoints disponibles
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
import importlib.util

def diagnose_blueprints():
    """Diagnostic des blueprints et endpoints"""
    print("=== DIAGNOSTIC CHRONOTECH ===")
    
    try:
        # Test import du blueprint interventions
        print("\n1. Test import blueprint interventions...")
        
        # Import du module routes.py
        spec = importlib.util.spec_from_file_location(
            "interventions_module", 
            "/home/amenard/Chronotech/ChronoTech/routes/interventions/routes.py"
        )
        interventions_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(interventions_module)
        
        bp = interventions_module.bp
        print(f"✅ Blueprint trouvé: {bp.name}")
        
        # Créer une app Flask temporaire pour tester
        app = Flask(__name__)
        app.register_blueprint(bp, url_prefix='/interventions')
        
        print("\n2. Endpoints disponibles:")
        with app.app_context():
            for rule in app.url_map.iter_rules():
                if 'interventions' in rule.endpoint:
                    print(f"  - {rule.endpoint} → {rule.rule}")
        
        print("\n3. Test endpoint kanban_view...")
        if 'interventions.kanban_view' in [rule.endpoint for rule in app.url_map.iter_rules()]:
            print("✅ Endpoint interventions.kanban_view trouvé")
        else:
            print("❌ Endpoint interventions.kanban_view MANQUANT")
            
        print("\n4. Fonctions disponibles dans le module:")
        for name in dir(interventions_module):
            if not name.startswith('_') and callable(getattr(interventions_module, name)):
                print(f"  - {name}")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_blueprints()
