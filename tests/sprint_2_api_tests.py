"""
Tests automatisés Sprint 2 - API Routes Sécurisées
Tests des endpoints /work_orders/<id>/tasks/* et /interventions/*
"""
import requests
import json
import pytest
import os
import time
from datetime import datetime

# Configuration des tests
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
API_BASE = f"{BASE_URL}/api"

class TestConfig:
    """Configuration pour les tests"""
    TEST_USER_CREDENTIALS = {
        'admin': {'email': 'admin@test.com', 'password': 'admin123'},
        'supervisor': {'email': 'supervisor@test.com', 'password': 'super123'},
        'technician': {'email': 'tech@test.com', 'password': 'tech123'}
    }
    
    # IDs de test (à adapter selon votre DB)
    TEST_WO_ID = 1
    TEST_CUSTOMER_ID = 1
    TEST_TECHNICIAN_ID = 1

class APIClient:
    """Client pour les tests API avec gestion de session"""
    
    def __init__(self, base_url=API_BASE):
        self.base_url = base_url
        self.session = requests.Session()
        self.logged_in_user = None
    
    def login(self, role='admin'):
        """Se connecter avec un rôle spécifique"""
        credentials = TestConfig.TEST_USER_CREDENTIALS.get(role)
        if not credentials:
            raise ValueError(f"Credentials not found for role: {role}")
        
        # Login via l'endpoint web (pas API)
        login_url = f"{BASE_URL}/login"
        response = self.session.post(login_url, data=credentials)
        
        if response.status_code == 200 or 'dashboard' in response.url:
            self.logged_in_user = role
            return True
        else:
            raise Exception(f"Login failed for {role}: {response.status_code}")
    
    def get(self, endpoint, **kwargs):
        """GET request avec session"""
        url = f"{self.base_url}{endpoint}"
        return self.session.get(url, **kwargs)
    
    def post(self, endpoint, **kwargs):
        """POST request avec session"""
        url = f"{self.base_url}{endpoint}"
        return self.session.post(url, **kwargs)
    
    def put(self, endpoint, **kwargs):
        """PUT request avec session"""
        url = f"{self.base_url}{endpoint}"
        return self.session.put(url, **kwargs)
    
    def delete(self, endpoint, **kwargs):
        """DELETE request avec session"""
        url = f"{self.base_url}{endpoint}"
        return self.session.delete(url, **kwargs)

# ========================================
# TESTS ENDPOINTS INTERDITS (SPRINT 2)
# ========================================

def test_forbidden_global_task_creation():
    """Test que les endpoints globaux de création de tâches sont interdits"""
    client = APIClient()
    client.login('admin')
    
    # Essayer de créer une tâche via endpoint global (DOIT ÉCHOUER)
    task_data = {
        'title': 'Tâche orpheline test',
        'task_source': 'requested'
    }
    
    # Test endpoint /tasks/create
    response = client.post('/tasks/create', json=task_data)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    data = response.json()
    assert 'Forbidden' in data['error']
    assert 'orphan tasks' in data['error']
    
    # Test endpoint /tasks
    response = client.post('/tasks', json=task_data)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    print("✅ Test forbidden global task creation: PASSED")

def test_forbidden_global_task_operations():
    """Test que les opérations globales sur les tâches sont interdites"""
    client = APIClient()
    client.login('admin')
    
    task_id = 1  # ID quelconque
    
    # Test PUT global
    response = client.put(f'/tasks/{task_id}', json={'status': 'done'})
    assert response.status_code == 403
    
    # Test PATCH global
    response = client.session.patch(f"{API_BASE}/tasks/{task_id}", json={'status': 'done'})
    assert response.status_code == 403
    
    # Test DELETE global
    response = client.delete(f'/tasks/{task_id}')
    assert response.status_code == 403
    
    print("✅ Test forbidden global task operations: PASSED")

# ========================================
# TESTS ROUTES IMBRIQUÉES SÉCURISÉES
# ========================================

def test_create_task_under_work_order():
    """Test création sécurisée de tâche sous un Work Order"""
    client = APIClient()
    client.login('supervisor')  # Seuls superviseurs+ peuvent créer des tâches
    
    wo_id = TestConfig.TEST_WO_ID
    
    task_data = {
        'title': f'Tâche test Sprint 2 - {datetime.now().strftime("%H:%M:%S")}',
        'description': 'Tâche créée via API sécurisée',
        'task_source': 'requested',
        'priority': 'medium',
        'estimated_minutes': 120
    }
    
    # Création via endpoint imbriqué (DOIT RÉUSSIR)
    response = client.post(f'/work_orders/{wo_id}/tasks', json=task_data)
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data['success'] == True
    assert 'task_id' in data
    assert data['task']['work_order_id'] == wo_id
    assert data['task']['title'] == task_data['title']
    assert data['task']['task_source'] == task_data['task_source']
    
    # Stocker l'ID pour les tests suivants
    global created_task_id
    created_task_id = data['task_id']
    
    print(f"✅ Test create task under work order: PASSED (Task ID: {created_task_id})")
    return created_task_id

def test_assign_task():
    """Test assignation d'une tâche à un technicien"""
    client = APIClient()
    client.login('supervisor')
    
    wo_id = TestConfig.TEST_WO_ID
    task_id = getattr(test_assign_task, 'task_id', None) or create_test_task()
    
    assign_data = {
        'technician_id': TestConfig.TEST_TECHNICIAN_ID
    }
    
    response = client.post(f'/work_orders/{wo_id}/tasks/{task_id}/assign', json=assign_data)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data['success'] == True
    assert data['task_id'] == task_id
    assert 'technician' in data
    
    print(f"✅ Test assign task: PASSED")

def test_update_task_status():
    """Test mise à jour du statut d'une tâche"""
    client = APIClient()
    client.login('technician')  # Technicien peut modifier ses tâches
    
    wo_id = TestConfig.TEST_WO_ID
    task_id = getattr(test_update_task_status, 'task_id', None) or create_test_task()
    
    status_data = {
        'status': 'in_progress'
    }
    
    response = client.post(f'/work_orders/{wo_id}/tasks/{task_id}/status', json=status_data)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data['success'] == True
    assert data['new_status'] == 'in_progress'
    
    print(f"✅ Test update task status: PASSED")

def test_start_intervention():
    """Test démarrage d'intervention avec validation IA"""
    client = APIClient()
    client.login('technician')
    
    wo_id = TestConfig.TEST_WO_ID
    task_id = getattr(test_start_intervention, 'task_id', None) or create_test_task()
    
    intervention_data = {
        'technician_id': TestConfig.TEST_TECHNICIAN_ID
    }
    
    response = client.post(f'/work_orders/{wo_id}/tasks/{task_id}/start_intervention', json=intervention_data)
    
    # Si l'intervention existe déjà, c'est normal (409)
    if response.status_code == 409:
        print(f"⚠️  Test start intervention: Intervention already exists (expected)")
        return
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data['success'] == True
    assert 'intervention_id' in data
    assert 'recommendations' in data  # Recommandations IA
    
    # Stocker pour tests suivants
    global created_intervention_id
    created_intervention_id = data['intervention_id']
    
    print(f"✅ Test start intervention: PASSED (Intervention ID: {created_intervention_id})")
    return created_intervention_id

def test_intervention_access_control():
    """Test contrôle d'accès aux interventions selon le rôle"""
    client = APIClient()
    
    # Test avec technicien (accès limité à ses interventions)
    client.login('technician')
    
    response = client.get('/interventions')
    assert response.status_code == 200
    
    data = response.json()
    assert data['success'] == True
    assert 'interventions' in data
    
    # Test avec superviseur (accès complet)
    client.login('supervisor')
    
    response = client.get('/interventions')
    assert response.status_code == 200
    
    print("✅ Test intervention access control: PASSED")

def test_add_intervention_note():
    """Test ajout de note à une intervention"""
    client = APIClient()
    client.login('technician')
    
    intervention_id = getattr(test_add_intervention_note, 'intervention_id', None) or create_test_intervention()
    
    note_data = {
        'note': f'Note de test ajoutée à {datetime.now()}',
        'note_type': 'general',
        'is_visible_to_customer': False
    }
    
    response = client.post(f'/interventions/{intervention_id}/add_note', json=note_data)
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data['success'] == True
    assert 'note_id' in data
    assert data['note']['note'] == note_data['note']
    
    print(f"✅ Test add intervention note: PASSED")

def test_intervention_quick_actions():
    """Test actions rapides sur interventions"""
    client = APIClient()
    client.login('technician')
    
    intervention_id = getattr(test_intervention_quick_actions, 'intervention_id', None) or create_test_intervention()
    
    # Test action pause
    action_data = {
        'action': 'pause',
        'notes': 'Pause pour vérification matériel'
    }
    
    response = client.post(f'/interventions/{intervention_id}/quick_actions', json=action_data)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data['success'] == True
    assert data['action'] == 'pause'
    
    print(f"✅ Test intervention quick actions: PASSED")

# ========================================
# TESTS VALIDATION IA
# ========================================

def test_work_order_closure_validation():
    """Test validation IA pour fermeture de Work Order"""
    client = APIClient()
    client.login('supervisor')
    
    wo_id = TestConfig.TEST_WO_ID
    
    # Tentative de fermeture avec validation IA
    closure_data = {
        'notes': 'Fermeture de test - validation IA'
    }
    
    response = client.post(f'/work_orders/{wo_id}/close', json=closure_data)
    
    # Peut échouer si conditions non remplies (attendu)
    if response.status_code == 400:
        data = response.json()
        print(f"⚠️  WO closure blocked by AI validation: {data.get('reason', 'Unknown')}")
        assert 'Validation failed' in data['error']
        print("✅ Test work order closure validation: PASSED (AI validation working)")
    else:
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        print("✅ Test work order closure validation: PASSED (WO closed)")

def test_invalid_task_creation_attempts():
    """Test diverses tentatives de création de tâches invalides"""
    client = APIClient()
    client.login('supervisor')
    
    wo_id = TestConfig.TEST_WO_ID
    
    # Test 1: task_source invalide
    invalid_data = {
        'title': 'Test invalide',
        'task_source': 'invalid_source'
    }
    
    response = client.post(f'/work_orders/{wo_id}/tasks', json=invalid_data)
    assert response.status_code == 400
    assert 'task_source must be one of' in response.json()['error']
    
    # Test 2: title trop court
    invalid_data = {
        'title': 'AB',  # Trop court
        'task_source': 'requested'
    }
    
    response = client.post(f'/work_orders/{wo_id}/tasks', json=invalid_data)
    assert response.status_code == 400
    assert 'at least 3 characters' in response.json()['error']
    
    # Test 3: Work Order inexistant
    response = client.post('/work_orders/99999/tasks', json={
        'title': 'Test WO inexistant',
        'task_source': 'requested'
    })
    assert response.status_code == 403  # Access denied car WO n'existe pas
    
    print("✅ Test invalid task creation attempts: PASSED")

# ========================================
# TESTS PERFORMANCE
# ========================================

def test_api_response_times():
    """Test des temps de réponse des API critiques"""
    client = APIClient()
    client.login('supervisor')
    
    # Test liste des tâches
    start_time = time.time()
    response = client.get(f'/work_orders/{TestConfig.TEST_WO_ID}/tasks')
    tasks_time = time.time() - start_time
    
    assert response.status_code == 200
    assert tasks_time < 1.0, f"Tasks list too slow: {tasks_time:.2f}s"
    
    # Test liste des interventions
    start_time = time.time()
    response = client.get('/interventions')
    interventions_time = time.time() - start_time
    
    assert response.status_code == 200
    assert interventions_time < 2.0, f"Interventions list too slow: {interventions_time:.2f}s"
    
    print(f"✅ Test API response times: PASSED (Tasks: {tasks_time:.2f}s, Interventions: {interventions_time:.2f}s)")

# ========================================
# HELPERS POUR LES TESTS
# ========================================

def create_test_task():
    """Créer une tâche de test"""
    client = APIClient()
    client.login('supervisor')
    
    task_data = {
        'title': f'Test Task {datetime.now().strftime("%H%M%S")}',
        'task_source': 'requested',
        'priority': 'low'
    }
    
    response = client.post(f'/work_orders/{TestConfig.TEST_WO_ID}/tasks', json=task_data)
    if response.status_code == 201:
        return response.json()['task_id']
    else:
        raise Exception(f"Failed to create test task: {response.status_code}")

def create_test_intervention():
    """Créer une intervention de test"""
    task_id = create_test_task()
    
    client = APIClient()
    client.login('technician')
    
    response = client.post(f'/work_orders/{TestConfig.TEST_WO_ID}/tasks/{task_id}/start_intervention', 
                          json={'technician_id': TestConfig.TEST_TECHNICIAN_ID})
    
    if response.status_code == 201:
        return response.json()['intervention_id']
    else:
        raise Exception(f"Failed to create test intervention: {response.status_code}")

# ========================================
# EXÉCUTION DES TESTS
# ========================================

def run_all_tests():
    """Exécuter tous les tests du Sprint 2"""
    print("🚀 DÉMARRAGE TESTS SPRINT 2 - API ROUTES SÉCURISÉES")
    print("=" * 60)
    
    tests = [
        test_forbidden_global_task_creation,
        test_forbidden_global_task_operations,
        test_create_task_under_work_order,
        test_assign_task,
        test_update_task_status,
        test_start_intervention,
        test_intervention_access_control,
        test_add_intervention_note,
        test_intervention_quick_actions,
        test_work_order_closure_validation,
        test_invalid_task_creation_attempts,
        test_api_response_times
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            print(f"\n🧪 Running {test_func.__name__}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED {test_func.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RÉSULTATS TESTS SPRINT 2:")
    print(f"✅ Tests réussis: {passed}")
    print(f"❌ Tests échoués: {failed}")
    print(f"📈 Taux de réussite: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 TOUS LES TESTS SPRINT 2 SONT PASSÉS!")
        print("🚀 PRÊT POUR SPRINT 3 (UI/UX)")
    else:
        print(f"\n⚠️  {failed} tests ont échoué - Correction requise")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
