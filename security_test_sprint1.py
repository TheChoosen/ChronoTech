#!/usr/bin/env python3
"""
Tests de Sécurité - Sprint 1
Validation des garde-fous critiques implémentés
"""
import requests
import json
import time
import subprocess
import os
from urllib.parse import urlencode

class SecurityTestSuite:
    def __init__(self, base_url="http://localhost:5013"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'sql_injection': {'status': 'PENDING', 'details': []},
            'csrf_protection': {'status': 'PENDING', 'details': []},
            'rate_limiting': {'status': 'PENDING', 'details': []},
            'file_upload_security': {'status': 'PENDING', 'details': []},
            'rbac_verification': {'status': 'PENDING', 'details': []},
            'xss_protection': {'status': 'PENDING', 'details': []}
        }
    
    def run_all_tests(self):
        """Exécuter tous les tests de sécurité"""
        print("🔒 DÉMARRAGE DES TESTS DE SÉCURITÉ - SPRINT 1")
        print("=" * 60)
        
        try:
            self.test_sql_injection_protection()
            self.test_csrf_protection()
            self.test_rate_limiting()
            self.test_file_upload_security()
            self.test_rbac_verification()
            self.test_xss_protection()
            
            self.generate_report()
            
        except Exception as e:
            print(f"❌ Erreur critique lors des tests: {str(e)}")
    
    def test_sql_injection_protection(self):
        """Test S1-SEC-01: Protection contre injection SQL"""
        print("\n🧪 Test SQL Injection Protection...")
        
        # Payloads SQL injection
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE work_orders; --",
            "' UNION SELECT * FROM users --",
            "1' OR 1=1 --",
            "admin'/*",
            "' AND (SELECT COUNT(*) FROM users) > 0 --"
        ]
        
        vulnerable = False
        
        for payload in sql_payloads:
            try:
                # Test sur différents endpoints
                endpoints = [
                    f"/interventions/",
                    f"/interventions/1/details"
                ]
                
                for endpoint in endpoints:
                    # Test via paramètres GET
                    response = self.session.get(
                        f"{self.base_url}{endpoint}",
                        params={'search': payload},
                        timeout=5
                    )
                    
                    # Vérifier si injection réussie
                    if any(error in response.text.lower() for error in 
                          ['mysql error', 'sql syntax', 'database error', 'table']):
                        vulnerable = True
                        self.results['sql_injection']['details'].append(
                            f"VULNÉRABLE: {endpoint} avec payload: {payload}"
                        )
                    
            except Exception as e:
                self.results['sql_injection']['details'].append(f"Erreur test: {str(e)}")
        
        if vulnerable:
            self.results['sql_injection']['status'] = 'FAIL'
            self.results['sql_injection']['details'].append("⚠️ INJECTIONS SQL DÉTECTÉES")
        else:
            self.results['sql_injection']['status'] = 'PASS'
            self.results['sql_injection']['details'].append("✅ Protection SQL active")
    
    def test_csrf_protection(self):
        """Test S1-SEC-02: Protection CSRF"""
        print("\n🧪 Test CSRF Protection...")
        
        try:
            # Test POST sans token CSRF
            response = self.session.post(
                f"{self.base_url}/interventions/1/add_note",
                data={'content': 'Test sans CSRF'},
                timeout=5
            )
            
            if response.status_code == 400 and 'csrf' in response.text.lower():
                self.results['csrf_protection']['status'] = 'PASS'
                self.results['csrf_protection']['details'].append("✅ CSRF protection active")
            else:
                self.results['csrf_protection']['status'] = 'FAIL'
                self.results['csrf_protection']['details'].append(
                    f"⚠️ POST sans CSRF autorisé (code: {response.status_code})"
                )
                
        except Exception as e:
            self.results['csrf_protection']['details'].append(f"Erreur test CSRF: {str(e)}")
            self.results['csrf_protection']['status'] = 'ERROR'
    
    def test_rate_limiting(self):
        """Test S1-SEC-02: Rate Limiting"""
        print("\n🧪 Test Rate Limiting...")
        
        try:
            # Tenter de dépasser les limites
            rate_limited = False
            
            for i in range(25):  # 25 requêtes rapides
                response = self.session.get(f"{self.base_url}/interventions/", timeout=2)
                
                if response.status_code == 429:
                    rate_limited = True
                    break
                    
                time.sleep(0.1)  # Petite pause
            
            if rate_limited:
                self.results['rate_limiting']['status'] = 'PASS'
                self.results['rate_limiting']['details'].append("✅ Rate limiting actif")
            else:
                self.results['rate_limiting']['status'] = 'FAIL'
                self.results['rate_limiting']['details'].append("⚠️ Pas de rate limiting détecté")
                
        except Exception as e:
            self.results['rate_limiting']['details'].append(f"Erreur test rate limit: {str(e)}")
            self.results['rate_limiting']['status'] = 'ERROR'
    
    def test_file_upload_security(self):
        """Test S1-SEC-03: Sécurité upload fichiers"""
        print("\n🧪 Test File Upload Security...")
        
        try:
            # Fichiers malveillants
            malicious_files = [
                ('script.php', '<?php echo "XSS"; ?>', 'application/x-php'),
                ('malware.exe', 'MZ\x90\x00', 'application/octet-stream'),
                ('xss.html', '<script>alert("XSS")</script>', 'text/html'),
                ('huge.txt', 'A' * (60 * 1024 * 1024), 'text/plain')  # 60MB
            ]
            
            blocked_count = 0
            
            for filename, content, mime_type in malicious_files:
                files = {'photos': (filename, content, mime_type)}
                
                response = self.session.post(
                    f"{self.base_url}/interventions/1/upload_photos",
                    files=files,
                    timeout=10
                )
                
                if response.status_code in [400, 403] or 'erreur' in response.text.lower():
                    blocked_count += 1
                    self.results['file_upload_security']['details'].append(
                        f"✅ Fichier malveillant bloqué: {filename}"
                    )
                else:
                    self.results['file_upload_security']['details'].append(
                        f"⚠️ Fichier malveillant accepté: {filename}"
                    )
            
            if blocked_count >= len(malicious_files) * 0.8:  # 80% bloqués
                self.results['file_upload_security']['status'] = 'PASS'
            else:
                self.results['file_upload_security']['status'] = 'FAIL'
                
        except Exception as e:
            self.results['file_upload_security']['details'].append(f"Erreur test upload: {str(e)}")
            self.results['file_upload_security']['status'] = 'ERROR'
    
    def test_rbac_verification(self):
        """Test S1-SEC-04: Vérification RBAC"""
        print("\n🧪 Test RBAC Verification...")
        
        try:
            # Test accès sans authentification
            protected_endpoints = [
                "/interventions/",
                "/interventions/1/details",
                "/interventions/1/add_note",
                "/interventions/1/upload_photos"
            ]
            
            unauthorized_count = 0
            
            # Session sans authentification
            unauth_session = requests.Session()
            
            for endpoint in protected_endpoints:
                response = unauth_session.get(f"{self.base_url}{endpoint}", timeout=5)
                
                if response.status_code in [401, 403] or 'login' in response.url:
                    unauthorized_count += 1
                    self.results['rbac_verification']['details'].append(
                        f"✅ Accès non autorisé bloqué: {endpoint}"
                    )
                else:
                    self.results['rbac_verification']['details'].append(
                        f"⚠️ Accès non autorisé autorisé: {endpoint}"
                    )
            
            if unauthorized_count >= len(protected_endpoints) * 0.9:  # 90% protégés
                self.results['rbac_verification']['status'] = 'PASS'
            else:
                self.results['rbac_verification']['status'] = 'FAIL'
                
        except Exception as e:
            self.results['rbac_verification']['details'].append(f"Erreur test RBAC: {str(e)}")
            self.results['rbac_verification']['status'] = 'ERROR'
    
    def test_xss_protection(self):
        """Test S1-SEC-03: Protection XSS"""
        print("\n🧪 Test XSS Protection...")
        
        try:
            # Payloads XSS
            xss_payloads = [
                '<script>alert("XSS")</script>',
                '<img src="x" onerror="alert(1)">',
                'javascript:alert("XSS")',
                '<svg onload="alert(1)">',
                '"><script>alert("XSS")</script>'
            ]
            
            protected_count = 0
            
            for payload in xss_payloads:
                # Test via formulaire de note
                response = self.session.post(
                    f"{self.base_url}/interventions/1/add_note",
                    data={'content': payload},
                    timeout=5
                )
                
                # Vérifier si payload est échappé dans la réponse
                if payload not in response.text or '&lt;' in response.text:
                    protected_count += 1
                    self.results['xss_protection']['details'].append(
                        f"✅ Payload XSS échappé: {payload[:30]}..."
                    )
                else:
                    self.results['xss_protection']['details'].append(
                        f"⚠️ Payload XSS non échappé: {payload[:30]}..."
                    )
            
            if protected_count >= len(xss_payloads) * 0.8:  # 80% protégés
                self.results['xss_protection']['status'] = 'PASS'
            else:
                self.results['xss_protection']['status'] = 'FAIL'
                
        except Exception as e:
            self.results['xss_protection']['details'].append(f"Erreur test XSS: {str(e)}")
            self.results['xss_protection']['status'] = 'ERROR'
    
    def generate_report(self):
        """Générer le rapport final"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT DE SÉCURITÉ - SPRINT 1")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['status'] == 'PASS')
        failed_tests = sum(1 for r in self.results.values() if r['status'] == 'FAIL')
        error_tests = sum(1 for r in self.results.values() if r['status'] == 'ERROR')
        
        print(f"\n🎯 RÉSUMÉ:")
        print(f"   ✅ Tests réussis: {passed_tests}/{total_tests}")
        print(f"   ❌ Tests échoués: {failed_tests}/{total_tests}")
        print(f"   ⚠️ Erreurs tests: {error_tests}/{total_tests}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"   📈 Taux de réussite: {success_rate:.1f}%")
        
        print(f"\n📋 DÉTAILS PAR TEST:")
        
        for test_name, result in self.results.items():
            status_icon = {
                'PASS': '✅',
                'FAIL': '❌',
                'ERROR': '⚠️',
                'PENDING': '⏳'
            }.get(result['status'], '❓')
            
            print(f"\n{status_icon} {test_name.upper()}: {result['status']}")
            for detail in result['details']:
                print(f"   {detail}")
        
        # Recommandations
        print(f"\n🔧 RECOMMANDATIONS:")
        if failed_tests > 0:
            print("   • Corriger les vulnérabilités détectées avant mise en production")
            print("   • Revoir la configuration de sécurité")
            print("   • Effectuer un audit complémentaire")
        else:
            print("   • Configuration de sécurité satisfaisante")
            print("   • Maintenir la surveillance continue")
            print("   • Planifier audits réguliers")
        
        # Sauvegarde du rapport
        report_file = f"security_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Rapport sauvegardé: {report_file}")
        
        return success_rate >= 80  # Seuil de réussite

def main():
    """Fonction principale de test"""
    print("🔒 ChronoTech Security Test Suite - Sprint 1")
    print("Validation des garde-fous critiques")
    
    # Vérifier que l'app est démarrée
    try:
        response = requests.get("http://localhost:5013", timeout=5)
        print("✅ Application accessible")
    except:
        print("❌ Application non accessible sur localhost:5013")
        print("Démarrez l'application avant de lancer les tests")
        return False
    
    # Lancer les tests
    test_suite = SecurityTestSuite()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 SPRINT 1 SÉCURITÉ: VALIDÉ")
        return True
    else:
        print("\n⚠️ SPRINT 1 SÉCURITÉ: CORRECTIONS REQUISES")
        return False

if __name__ == "__main__":
    main()
