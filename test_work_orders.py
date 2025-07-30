#!/usr/bin/env python3
"""
Script de test pour vérifier le bon fonctionnement du module Travaux Demandés
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:5050"
TEST_CREDENTIALS = {
    "email": "admin@chronotech.com",  # Adaptez selon vos données
    "password": "admin123"
}

def test_login():
    """Test de connexion"""
    print("🔐 Test de connexion...")
    
    session = requests.Session()
    
    # Récupérer la page de login pour obtenir le token CSRF (si nécessaire)
    login_page = session.get(f"{BASE_URL}/login")
    if login_page.status_code != 200:
        print(f"❌ Impossible d'accéder à la page de login: {login_page.status_code}")
        return None
    
    # Tentative de connexion
    login_response = session.post(f"{BASE_URL}/login", data=TEST_CREDENTIALS)
    
    if login_response.status_code == 200 and "dashboard" in login_response.url:
        print("✅ Connexion réussie")
        return session
    else:
        print(f"❌ Échec de connexion: {login_response.status_code}")
        return None

def test_work_orders_page(session):
    """Test d'accès à la page des travaux demandés"""
    print("📋 Test d'accès à la page des travaux demandés...")
    
    response = session.get(f"{BASE_URL}/work_orders")
    
    if response.status_code == 200:
        if "Travaux Demandés" in response.text:
            print("✅ Page des travaux demandés accessible")
            return True
        else:
            print("⚠️  Page accessible mais contenu inattendu")
            return False
    else:
        print(f"❌ Erreur d'accès: {response.status_code}")
        return False

def test_search_api(session):
    """Test de l'API de recherche"""
    print("🔍 Test de l'API de recherche...")
    
    response = session.get(f"{BASE_URL}/api/work_orders/search?q=WO-2025")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if "work_orders" in data:
                count = len(data["work_orders"])
                print(f"✅ API de recherche fonctionnelle - {count} résultats trouvés")
                return True
            else:
                print("⚠️  Structure de réponse inattendue")
                return False
        except json.JSONDecodeError:
            print("❌ Réponse JSON invalide")
            return False
    else:
        print(f"❌ Erreur API: {response.status_code}")
        return False

def test_work_order_creation(session):
    """Test de création d'un travail (si possible)"""
    print("➕ Test de création d'un travail...")
    
    # Données de test
    test_data = {
        "claim_number": f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "customer_name": "Client Test",
        "customer_address": "123 Rue de Test\n00000 Testville",
        "description": "Travail de test automatisé",
        "priority": "low",
        "notes": "Créé par le script de test automatique"
    }
    
    response = session.post(f"{BASE_URL}/work_orders/new", data=test_data)
    
    if response.status_code in [200, 302]:  # 302 = redirection après création
        print("✅ Création de travail testée avec succès")
        return True
    else:
        print(f"⚠️  Test de création échoué: {response.status_code}")
        return False

def test_database_connection():
    """Test de connexion à la base de données"""
    print("🗄️  Test de connexion à la base de données...")
    
    try:
        import pymysql
        
        conn = pymysql.connect(
            host='192.168.50.101',
            port=3306,
            user='gsicloud',
            password='TCOChoosenOne204$',
            db='gsi',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with conn.cursor() as cur:
            # Test de lecture des travaux
            cur.execute("SELECT COUNT(*) as count FROM work_orders")
            result = cur.fetchone()
            count = result['count']
            
            # Test de lecture des produits
            cur.execute("SELECT COUNT(*) as count FROM work_order_products")
            result = cur.fetchone()
            products_count = result['count']
            
            print(f"✅ Base de données accessible - {count} travaux, {products_count} produits")
            return True
            
    except Exception as e:
        print(f"❌ Erreur de connexion à la base: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def run_all_tests():
    """Exécuter tous les tests"""
    print("🧪 === TESTS DU MODULE TRAVAUX DEMANDÉS ===")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Base de données
    results['database'] = test_database_connection()
    print()
    
    # Test 2: Connexion utilisateur
    session = test_login()
    results['login'] = session is not None
    print()
    
    if session:
        # Test 3: Page des travaux
        results['work_orders_page'] = test_work_orders_page(session)
        print()
        
        # Test 4: API de recherche
        results['search_api'] = test_search_api(session)
        print()
        
        # Test 5: Création (optionnel)
        results['creation'] = test_work_order_creation(session)
        print()
    else:
        results['work_orders_page'] = False
        results['search_api'] = False
        results['creation'] = False
    
    # Résumé
    print("📊 === RÉSUMÉ DES TESTS ===")
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    for test_name, success in results.items():
        status = "✅ PASSÉ" if success else "❌ ÉCHOUÉ"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print()
    print(f"🎯 Résultat global: {passed_tests}/{total_tests} tests réussis")
    
    if passed_tests == total_tests:
        print("🎉 TOUS LES TESTS SONT PASSÉS - Module opérationnel !")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  Module majoritairement opérationnel - quelques ajustements nécessaires")
    else:
        print("❌ Module nécessite des corrections importantes")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrompus par l'utilisateur")
        exit(1)
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {str(e)}")
        exit(1)
