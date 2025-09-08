#!/usr/bin/env python3
"""
Script de diagnostic pour le système Kanban du dashboard
"""

import requests
import json
from datetime import datetime

def test_dashboard_api():
    """Test des endpoints API du dashboard"""
    base_url = "http://127.0.0.1:5011"
    
    print("🔍 Diagnostic du Dashboard Kanban ChronoTech")
    print("=" * 60)
    
    # Test 1: Accès au dashboard
    print("\n1. Test d'accès au dashboard...")
    try:
        response = requests.get(f"{base_url}/dashboard", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard accessible")
            if "wo-kanban-column" in response.text:
                print("✅ Structure Kanban détectée dans le HTML")
            else:
                print("⚠️ Structure Kanban non trouvée")
        else:
            print(f"❌ Dashboard erreur: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur accès dashboard: {e}")
    
    # Test 2: API des work orders
    print("\n2. Test API work orders...")
    try:
        response = requests.get(f"{base_url}/api/work-orders", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API work orders: {len(data)} work orders trouvés")
            
            # Analyser la distribution par statut
            statuses = {}
            for wo in data:
                status = wo.get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
            
            print("📊 Distribution par statut:")
            for status, count in statuses.items():
                print(f"   - {status}: {count}")
        else:
            print(f"❌ API work orders erreur: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur API work orders: {e}")
    
    # Test 3: Test API update status avec un work order existant
    print("\n3. Test API update status...")
    try:
        # D'abord récupérer un work order existant
        response = requests.get(f"{base_url}/api/work-orders", timeout=5)
        if response.status_code == 200:
            work_orders = response.json()
            if work_orders:
                test_wo = work_orders[0]
                wo_id = test_wo['id']
                current_status = test_wo['status']
                
                print(f"📝 Test avec WO-{wo_id} (statut actuel: {current_status})")
                
                # Test avec le même statut (ne devrait pas causer d'erreur)
                test_data = {'status': current_status}
                response = requests.put(
                    f"{base_url}/api/work-orders/{wo_id}/status",
                    json=test_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    print("✅ API update status fonctionne")
                else:
                    print(f"❌ API update status erreur: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   Détails: {error_data}")
                    except:
                        print(f"   Réponse: {response.text}")
            else:
                print("⚠️ Aucun work order pour tester l'API update")
    except Exception as e:
        print(f"❌ Erreur test API update: {e}")
    
    # Test 4: Vérification des statuts valides
    print("\n4. Vérification des statuts Kanban...")
    expected_statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled']
    
    try:
        response = requests.put(
            f"{base_url}/api/work-orders/999999/status",  # ID inexistant
            json={'status': 'test_invalid'},
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 404:
            print("✅ Validation des statuts active (404 pour ID inexistant)")
        elif response.status_code == 400:
            error_data = response.json()
            if 'Invalid status' in error_data.get('error', ''):
                print("✅ Validation des statuts active (statut invalide rejeté)")
            else:
                print("✅ Validation active")
        else:
            print(f"⚠️ Réponse inattendue: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur test validation: {e}")
    
    print(f"\n🕒 Diagnostic terminé à {datetime.now().strftime('%H:%M:%S')}")

def analyze_kanban_html():
    """Analyse du HTML du dashboard pour les éléments Kanban"""
    print("\n" + "=" * 60)
    print("🔍 Analyse HTML Kanban")
    print("=" * 60)
    
    try:
        response = requests.get("http://127.0.0.1:5011/dashboard")
        html = response.text
        
        # Vérifications clés
        checks = [
            ("wo-kanban-column", "Colonnes Kanban"),
            ("wo-kanban-content", "Zones de contenu Kanban"),
            ("handleWorkOrderDrop", "Fonction drop handler"),
            ("allowDrop", "Fonction allow drop"),
            ("handleWorkOrderDragStart", "Fonction drag start"),
            ("draggable=\"true\"", "Attributs draggable"),
            ("data-status=", "Attributs data-status"),
            ("modal-column-", "IDs colonnes modales"),
        ]
        
        for search_term, description in checks:
            count = html.count(search_term)
            status = "✅" if count > 0 else "❌"
            print(f"{status} {description}: {count} occurrence(s)")
        
        # Recherche spécifique des colonnes
        print("\n📋 Analyse des colonnes Kanban:")
        statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled']
        for status in statuses:
            modal_id = f"modal-column-{status}"
            if modal_id in html:
                print(f"✅ Colonne {status}: présente")
            else:
                print(f"❌ Colonne {status}: manquante")
        
    except Exception as e:
        print(f"❌ Erreur analyse HTML: {e}")

if __name__ == "__main__":
    test_dashboard_api()
    analyze_kanban_html()
