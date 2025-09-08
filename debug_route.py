#!/usr/bin/env python3
"""
Script de diagnostic pour tester la route des clients
"""

import requests
import sys
import time

def test_customers_route():
    """Test la route des clients"""
    print("🔍 Test de la route des clients")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5011"
    url = f"{base_url}/customers/"
    
    try:
        print(f"📡 Requête vers: {url}")
        response = requests.get(url, timeout=10)
        
        print(f"✅ Status code: {response.status_code}")
        print(f"📏 Taille de la réponse: {len(response.text)} caractères")
        
        # Rechercher la pagination dans la réponse
        pagination_found = "pagination" in response.text.lower()
        print(f"🔍 Pagination trouvée: {pagination_found}")
        
        # Rechercher des éléments spécifiques
        elements = [
            "clay-element",
            "customersCard", 
            "customers/_list.html",
            "page-link",
            "page-item",
            "has_prev",
            "has_next"
        ]
        
        print("\n🔍 Éléments recherchés:")
        for element in elements:
            found = element in response.text
            print(f"  {element}: {'✅' if found else '❌'}")
        
        # Vérifier les erreurs
        if "error" in response.text.lower() or "erreur" in response.text.lower():
            print("\n❌ Erreurs détectées dans la réponse")
            
        # Vérifier le template customers/_list.html
        if "customers/_list.html" in response.text:
            print("\n✅ Le template customers/_list.html est inclus")
        else:
            print("\n❌ Le template customers/_list.html n'est PAS inclus")
            
        # Essayer une requête avec paramètre page
        print("\n" + "=" * 50)
        print("Test avec paramètre page=2")
        url_page2 = f"{base_url}/customers/?page=2"
        response2 = requests.get(url_page2, timeout=10)
        print(f"✅ Status code page 2: {response2.status_code}")
        pagination_found2 = "pagination" in response2.text.lower()
        print(f"🔍 Pagination trouvée page 2: {pagination_found2}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Erreur de connexion - Le serveur n'est probablement pas démarré")
        print("   Démarrez le serveur avec: python3 app.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_customers_route()
