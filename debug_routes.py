#!/usr/bin/env python3

"""Test des routes disponibles dans l'application"""

import os
import sys

# Configurer l'environnement
os.chdir('/home/amenard/Chronotech/ChronoTech')
sys.path.insert(0, '/home/amenard/Chronotech/ChronoTech')

def test_routes():
    """Teste les routes disponibles dans l'application"""
    print("🔍 Analyse des routes de l'application ChronoTech")
    print("=" * 60)
    
    try:
        # Importer l'application
        from app import app
        
        print("✅ Application importée avec succès")
        print(f"📦 Blueprints enregistrés: {len(app.blueprints)}")
        
        for bp_name, bp in app.blueprints.items():
            print(f"   📁 {bp_name}")
        
        print("\n🔗 Routes disponibles:")
        print("-" * 40)
        
        # Afficher toutes les routes
        api_routes = []
        customer_routes = []
        
        for rule in app.url_map.iter_rules():
            route_str = f"{rule.methods} {rule.rule}"
            
            if '/api/customers/' in rule.rule:
                api_routes.append(route_str)
            elif '/customers/' in rule.rule:
                customer_routes.append(route_str)
        
        print("🏪 Routes Customer:")
        for route in sorted(customer_routes):
            print(f"   {route}")
        
        print("\n🔌 Routes API Customer:")
        for route in sorted(api_routes):
            print(f"   {route}")
            
        # Chercher spécifiquement nos nouvelles routes
        print("\n🎯 Recherche des nouvelles routes CRUD:")
        crud_routes = [
            "/api/customers/<int:customer_id>/vehicles",
            "/api/customers/<int:customer_id>/contacts", 
            "/api/customers/<int:customer_id>/addresses"
        ]
        
        for crud_route in crud_routes:
            found = False
            for rule in app.url_map.iter_rules():
                if crud_route.replace('<int:customer_id>', '<customer_id>') in rule.rule:
                    print(f"   ✅ {crud_route} - {rule.methods}")
                    found = True
                    break
            if not found:
                print(f"   ❌ {crud_route} - NON TROUVÉE")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_routes()
    sys.exit(0 if success else 1)
