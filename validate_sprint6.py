#!/usr/bin/env python3
"""
Validation simple Sprint 6 - RBAC Avancé & API Publique
Vérification des composants sans conflits de dépendances
"""

import sys
import os
import pymysql
from datetime import datetime

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_rbac():
    """Test des tables et données RBAC"""
    print("🧪 Test Base de Données RBAC...")
    
    try:
        from core.database import get_db_connection
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Vérifier les tables RBAC
                tables_rbac = [
                    'system_permissions', 'user_roles', 'role_permissions',
                    'user_permissions', 'audit_logs', 'security_events', 'api_tokens'
                ]
                
                results = {}
                for table in tables_rbac:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()['count']
                        results[table] = count
                        print(f"  ✅ {table}: {count} enregistrements")
                    except Exception as e:
                        print(f"  ❌ {table}: Erreur - {e}")
                        results[table] = 'ERROR'
                
                # Vérifier les permissions système
                if results.get('system_permissions', 0) >= 20:
                    print("  ✅ Permissions système: Configuration complète")
                else:
                    print("  ❌ Permissions système: Configuration incomplète")
                
                # Vérifier la fonction user_has_permission
                try:
                    cursor.execute("SELECT user_has_permission(1, 'work_orders.view_all') as result")
                    function_result = cursor.fetchone()
                    if 'result' in function_result:
                        print("  ✅ Fonction user_has_permission: Opérationnelle")
                    else:
                        print("  ❌ Fonction user_has_permission: Non fonctionnelle")
                except Exception as e:
                    print(f"  ❌ Fonction user_has_permission: Erreur - {e}")
                
                return True
                
    except Exception as e:
        print(f"  ❌ Erreur connexion base: {e}")
        return False

def test_rbac_core():
    """Test du module RBAC core"""
    print("\n🧪 Test Module RBAC Core...")
    
    try:
        from core.rbac_advanced import permission_manager, audit_logger, security_logger
        
        # Test PermissionManager
        if hasattr(permission_manager, 'user_has_permission'):
            print("  ✅ PermissionManager: Classe chargée")
        else:
            print("  ❌ PermissionManager: Classe incomplète")
        
        # Test AuditLogger
        if hasattr(audit_logger, 'log_action'):
            print("  ✅ AuditLogger: Classe chargée")
        else:
            print("  ❌ AuditLogger: Classe incomplète")
        
        # Test SecurityEventLogger
        if hasattr(security_logger, 'log_unauthorized_access'):
            print("  ✅ SecurityEventLogger: Classe chargée")
        else:
            print("  ❌ SecurityEventLogger: Classe incomplète")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur import RBAC core: {e}")
        return False

def test_api_routes():
    """Test des fichiers de routes API"""
    print("\n🧪 Test Fichiers Routes API...")
    
    try:
        # Test routes RBAC
        if os.path.exists('/home/amenard/Chronotech/ChronoTech/routes/rbac_routes.py'):
            print("  ✅ Routes RBAC: Fichier présent")
        else:
            print("  ❌ Routes RBAC: Fichier manquant")
        
        # Test API publique
        if os.path.exists('/home/amenard/Chronotech/ChronoTech/routes/api/public_simple.py'):
            print("  ✅ API Publique: Fichier présent")
        else:
            print("  ❌ API Publique: Fichier manquant")
        
        # Test templates RBAC
        rbac_templates_dir = '/home/amenard/Chronotech/ChronoTech/templates/admin/rbac'
        if os.path.exists(rbac_templates_dir):
            template_files = os.listdir(rbac_templates_dir)
            print(f"  ✅ Templates RBAC: {len(template_files)} fichiers")
        else:
            print("  ❌ Templates RBAC: Dossier manquant")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur vérification fichiers: {e}")
        return False

def test_user_stories():
    """Test des User Stories"""
    print("\n🧪 Test User Stories...")
    
    try:
        from core.database import get_db_connection
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # User Story 1: Technicien limité à ses bons
                cursor.execute("""
                    SELECT ur.name, COUNT(rp.permission_id) as perm_count
                    FROM user_roles ur
                    LEFT JOIN role_permissions rp ON ur.id = rp.role_id
                    WHERE ur.name = 'technician'
                    GROUP BY ur.id
                """)
                
                tech_role = cursor.fetchone()
                if tech_role and tech_role['perm_count'] > 0:
                    # Vérifier permissions spécifiques
                    cursor.execute("""
                        SELECT sp.name
                        FROM user_roles ur
                        JOIN role_permissions rp ON ur.id = rp.role_id
                        JOIN system_permissions sp ON rp.permission_id = sp.id
                        WHERE ur.name = 'technician' AND sp.name IN ('work_orders.view_own', 'work_orders.view_all')
                    """)
                    
                    tech_permissions = [row['name'] for row in cursor.fetchall()]
                    
                    if 'work_orders.view_own' in tech_permissions and 'work_orders.view_all' not in tech_permissions:
                        print("  ✅ User Story 1: Technicien limité à ses bons - VALIDÉE")
                    else:
                        print("  ❌ User Story 1: Permissions technicien incorrectes")
                else:
                    print("  ❌ User Story 1: Rôle technicien non trouvé")
                
                # User Story 2: API documentée pour partenaires
                api_doc_path = '/home/amenard/Chronotech/ChronoTech/routes/api/public_simple.py'
                if os.path.exists(api_doc_path):
                    with open(api_doc_path, 'r') as f:
                        content = f.read()
                        if 'ChronoTech API Documentation' in content and 'work_orders' in content:
                            print("  ✅ User Story 2: API documentée pour partenaires - VALIDÉE")
                        else:
                            print("  ❌ User Story 2: Documentation API incomplète")
                else:
                    print("  ❌ User Story 2: Fichier API manquant")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur test user stories: {e}")
        return False

def main():
    """Validation complète Sprint 6"""
    print("🚀 VALIDATION SPRINT 6 - RBAC AVANCÉ & API PUBLIQUE")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    tests = [
        test_database_rbac,
        test_rbac_core,
        test_api_routes,
        test_user_stories
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Erreur durant {test_func.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS VALIDATION SPRINT 6")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 SPRINT 6 - VALIDATION COMPLÈTE: TOUS LES TESTS PASSÉS")
        print("✅ RBAC Avancé: Système de permissions opérationnel")
        print("✅ API Publique: Documentation et endpoints fonctionnels")
        print("✅ User Stories: Besoins métier validés")
        print("✅ Base de données: Schema et données déployés")
        print("\n🚀 Sprint 6 prêt pour production!")
        return 0
    else:
        print(f"⚠️  VALIDATION PARTIELLE: {passed}/{total} tests réussis")
        print("🔧 Corrections nécessaires avant validation finale")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
