#!/usr/bin/env python3
"""
ChronoTech CRUD Smoke Tests & Quality Analyzer
Tests systématiques CRUD + détection des manques fonctionnels
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
import pymysql

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/crud_tests.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChronoTechCRUDTester:
    """Testeur CRUD complet pour ChronoTech"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'bdm'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'charset': 'utf8mb4'
        }
        
        # Tables principales à tester
        self.core_tables = [
            'customers', 'users', 'vehicles', 'work_orders', 
            'interventions', 'appointments', 'inventory_items'
        ]
        
        self.test_results = {}
        self.coverage_report = {}
        self.missing_features = []
        self.connection = None
        
    def connect_db(self) -> bool:
        """Connexion à la base de données"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion: {e}")
            return False
    
    def disconnect_db(self):
        """Fermer connexion"""
        if self.connection:
            self.connection.close()
    
    def run_crud_tests(self):
        """Exécuter tous les tests CRUD"""
        logger.info("🧪 Début des tests CRUD ChronoTech")
        
        if not self.connect_db():
            return False
        
        try:
            for table in self.core_tables:
                logger.info(f"🔍 Test CRUD table: {table}")
                self.test_results[table] = self.test_table_crud(table)
                
            # Tests spécifiques métier
            self.test_business_rules()
            
            # Analyse de couverture
            self.analyze_data_coverage()
            
            # Détection des manques
            self.detect_missing_features()
            
            # Génération des rapports
            self.generate_reports()
            
        finally:
            self.disconnect_db()
    
    def test_table_crud(self, table: str) -> Dict[str, Any]:
        """Tester opérations CRUD pour une table"""
        results = {
            'create': {'status': 'unknown', 'latency': 0, 'error': None},
            'read': {'status': 'unknown', 'latency': 0, 'error': None},
            'update': {'status': 'unknown', 'latency': 0, 'error': None},
            'delete': {'status': 'unknown', 'latency': 0, 'error': None}
        }
        
        cursor = self.connection.cursor()
        
        try:
            # Test CREATE
            results['create'] = self.test_create(cursor, table)
            
            # Test READ
            results['read'] = self.test_read(cursor, table)
            
            # Test UPDATE  
            results['update'] = self.test_update(cursor, table)
            
            # Test DELETE
            results['delete'] = self.test_delete(cursor, table)
            
        except Exception as e:
            logger.error(f"❌ Erreur test CRUD {table}: {e}")
        finally:
            cursor.close()
        
        return results
    
    def test_create(self, cursor, table: str) -> Dict[str, Any]:
        """Test opération CREATE"""
        start_time = time.time()
        
        try:
            # Obtenir structure de la table
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            
            # Préparer données de test minimales
            test_data = self.prepare_minimal_test_data(table, columns)
            
            if not test_data:
                return {'status': 'skip', 'latency': 0, 'error': 'No test data prepared'}
            
            # Construction de la requête INSERT
            cols = ', '.join(test_data.keys())
            placeholders = ', '.join(['%s'] * len(test_data))
            insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            
            cursor.execute(insert_sql, list(test_data.values()))
            
            latency = time.time() - start_time
            return {'status': 'pass', 'latency': latency, 'error': None}
            
        except Exception as e:
            latency = time.time() - start_time
            return {'status': 'fail', 'latency': latency, 'error': str(e)}
    
    def test_read(self, cursor, table: str) -> Dict[str, Any]:
        """Test opération READ avec filtres"""
        start_time = time.time()
        
        try:
            # Test basique: SELECT *
            cursor.execute(f"SELECT * FROM {table} LIMIT 10")
            basic_rows = cursor.fetchall()
            
            # Test avec WHERE si possible
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            
            # Chercher une colonne de statut ou état
            status_columns = [col[0] for col in columns if 'status' in col[0].lower() or 'state' in col[0].lower()]
            
            if status_columns:
                status_col = status_columns[0]
                cursor.execute(f"SELECT DISTINCT {status_col} FROM {table} LIMIT 5")
                status_values = [row[0] for row in cursor.fetchall() if row[0]]
                
                if status_values:
                    cursor.execute(f"SELECT * FROM {table} WHERE {status_col} = %s LIMIT 5", (status_values[0],))
                    filtered_rows = cursor.fetchall()
            
            # Test tri
            primary_key = self.get_primary_key(cursor, table)
            if primary_key:
                cursor.execute(f"SELECT * FROM {table} ORDER BY {primary_key} DESC LIMIT 5")
                sorted_rows = cursor.fetchall()
            
            latency = time.time() - start_time
            return {'status': 'pass', 'latency': latency, 'error': None}
            
        except Exception as e:
            latency = time.time() - start_time
            return {'status': 'fail', 'latency': latency, 'error': str(e)}
    
    def test_update(self, cursor, table: str) -> Dict[str, Any]:
        """Test opération UPDATE"""
        start_time = time.time()
        
        try:
            # Trouver un enregistrement existant
            cursor.execute(f"SELECT * FROM {table} LIMIT 1")
            record = cursor.fetchone()
            
            if not record:
                return {'status': 'skip', 'latency': 0, 'error': 'No records to update'}
            
            # Identifier la clé primaire
            primary_key = self.get_primary_key(cursor, table)
            if not primary_key:
                return {'status': 'skip', 'latency': 0, 'error': 'No primary key found'}
            
            # Obtenir l'index de la clé primaire
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            pk_index = next(i for i, col in enumerate(columns) if col[0] == primary_key)
            pk_value = record[pk_index]
            
            # Préparer UPDATE sur un champ sûr
            update_field = self.find_safe_update_field(cursor, table)
            if not update_field:
                return {'status': 'skip', 'latency': 0, 'error': 'No safe field to update'}
            
            # Exécuter UPDATE
            update_sql = f"UPDATE {table} SET {update_field} = %s WHERE {primary_key} = %s"
            test_value = f"TEST_UPDATE_{int(time.time())}"
            cursor.execute(update_sql, (test_value, pk_value))
            
            latency = time.time() - start_time
            return {'status': 'pass', 'latency': latency, 'error': None}
            
        except Exception as e:
            latency = time.time() - start_time
            return {'status': 'fail', 'latency': latency, 'error': str(e)}
    
    def test_delete(self, cursor, table: str) -> Dict[str, Any]:
        """Test opération DELETE (ou soft delete)"""
        start_time = time.time()
        
        try:
            # Vérifier si la table a un soft delete (is_active, deleted_at, etc.)
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            
            soft_delete_columns = [col[0] for col in columns 
                                 if col[0].lower() in ['is_active', 'deleted_at', 'is_deleted', 'status']]
            
            if soft_delete_columns and 'is_active' in soft_delete_columns:
                # Test soft delete
                primary_key = self.get_primary_key(cursor, table)
                cursor.execute(f"SELECT {primary_key} FROM {table} WHERE is_active = 1 LIMIT 1")
                record = cursor.fetchone()
                
                if record:
                    pk_value = record[0]
                    cursor.execute(f"UPDATE {table} SET is_active = 0 WHERE {primary_key} = %s", (pk_value,))
                    
            else:
                # Test DELETE (attention: dangereux!)
                # Pour les tests, on évite les vrais DELETE
                return {'status': 'skip', 'latency': 0, 'error': 'Hard delete avoided for safety'}
            
            latency = time.time() - start_time
            return {'status': 'pass', 'latency': latency, 'error': None}
            
        except Exception as e:
            latency = time.time() - start_time
            return {'status': 'fail', 'latency': latency, 'error': str(e)}
    
    def prepare_minimal_test_data(self, table: str, columns: List) -> Dict[str, Any]:
        """Préparer données de test minimales"""
        test_data = {}
        
        # Données de test par table
        test_templates = {
            'customers': {
                'name': 'Test Customer',
                'email': 'test@chronotech.ca',
                'customer_type': 'individual'
            },
            'users': {
                'name': 'Test User',
                'email': 'testuser@chronotech.ca',
                'password': '$2b$12$test.hash',
                'role': 'technician'
            },
            'vehicles': {
                'customer_id': 1,
                'make': 'Toyota',
                'model': 'Corolla',
                'year': 2020
            },
            'work_orders': {
                'claim_number': f'TEST-{int(time.time())}',
                'customer_name': 'Test Customer',
                'customer_address': '123 Test St',
                'description': 'Test work order',
                'created_by_user_id': 1
            }
        }
        
        template = test_templates.get(table, {})
        
        # Remplir seulement les champs NOT NULL
        for col in columns:
            col_name, col_type, nullable, key, default, extra = col
            
            if nullable == 'NO' and col_name not in ['id'] and 'auto_increment' not in extra.lower():
                if col_name in template:
                    test_data[col_name] = template[col_name]
                else:
                    # Valeur par défaut selon le type
                    if 'varchar' in col_type or 'text' in col_type:
                        test_data[col_name] = f'test_{col_name}'
                    elif 'int' in col_type:
                        test_data[col_name] = 1
                    elif 'decimal' in col_type:
                        test_data[col_name] = 0.00
                    elif 'enum' in col_type:
                        # Extraire les valeurs enum
                        enum_values = col_type.split("'")[1::2]
                        test_data[col_name] = enum_values[0] if enum_values else 'test'
                    elif 'datetime' in col_type or 'timestamp' in col_type:
                        test_data[col_name] = datetime.now()
        
        return test_data
    
    def get_primary_key(self, cursor, table: str) -> str:
        """Obtenir la clé primaire d'une table"""
        cursor.execute(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'")
        result = cursor.fetchone()
        return result[4] if result else None
    
    def find_safe_update_field(self, cursor, table: str) -> str:
        """Trouver un champ sûr pour les tests UPDATE"""
        safe_fields = ['notes', 'description', 'comments', 'updated_at']
        
        cursor.execute(f"DESCRIBE {table}")
        columns = [col[0] for col in cursor.fetchall()]
        
        for field in safe_fields:
            if field in columns:
                return field
        
        # Chercher un champ varchar/text nullable
        cursor.execute(f"DESCRIBE {table}")
        for col in cursor.fetchall():
            col_name, col_type, nullable = col[0], col[1], col[2]
            if nullable == 'YES' and ('varchar' in col_type or 'text' in col_type):
                return col_name
        
        return None
    
    def test_business_rules(self):
        """Tests spécifiques aux règles métier"""
        logger.info("🏢 Test des règles métier")
        
        cursor = self.connection.cursor()
        
        # Test 1: Intégrité référentielle work_orders -> customers
        cursor.execute("""
            SELECT COUNT(*) as orphaned_work_orders 
            FROM work_orders wo 
            LEFT JOIN customers c ON wo.customer_id = c.id 
            WHERE wo.customer_id IS NOT NULL AND c.id IS NULL
        """)
        orphaned_count = cursor.fetchone()[0]
        
        if orphaned_count > 0:
            self.missing_features.append({
                'type': 'data_integrity',
                'issue': f'{orphaned_count} work_orders sans customer valide',
                'table': 'work_orders',
                'severity': 'high'
            })
        
        # Test 2: Statuts work_orders cohérents
        cursor.execute("SELECT DISTINCT status FROM work_orders")
        statuses = [row[0] for row in cursor.fetchall()]
        expected_statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled']
        
        for status in statuses:
            if status not in expected_statuses:
                self.missing_features.append({
                    'type': 'business_rule',
                    'issue': f'Statut work_order non standard: {status}',
                    'table': 'work_orders',
                    'severity': 'medium'
                })
        
        cursor.close()
    
    def analyze_data_coverage(self):
        """Analyser la couverture des données"""
        logger.info("📊 Analyse couverture des données")
        
        cursor = self.connection.cursor()
        
        for table in self.core_tables:
            try:
                # Statistiques basiques
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_rows = cursor.fetchone()[0]
                
                # Analyse des colonnes
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                
                column_coverage = {}
                for col in columns:
                    col_name = col[0]
                    cursor.execute(f"SELECT COUNT(*) as filled FROM {table} WHERE {col_name} IS NOT NULL")
                    filled_count = cursor.fetchone()[0]
                    
                    coverage_pct = (filled_count / total_rows * 100) if total_rows > 0 else 0
                    column_coverage[col_name] = {
                        'filled_count': filled_count,
                        'total_rows': total_rows,
                        'coverage_percent': round(coverage_pct, 2)
                    }
                
                self.coverage_report[table] = {
                    'total_rows': total_rows,
                    'columns': column_coverage
                }
                
                # Identifier colonnes sous-utilisées
                for col_name, stats in column_coverage.items():
                    if stats['coverage_percent'] < 10 and total_rows > 0:
                        self.missing_features.append({
                            'type': 'data_coverage',
                            'issue': f'Colonne {col_name} remplie à seulement {stats["coverage_percent"]}%',
                            'table': table,
                            'severity': 'low'
                        })
                
            except Exception as e:
                logger.error(f"❌ Erreur analyse {table}: {e}")
        
        cursor.close()
    
    def detect_missing_features(self):
        """Détecter les fonctionnalités manquantes"""
        logger.info("🔍 Détection des manques fonctionnels")
        
        # Vérifications structure
        cursor = self.connection.cursor()
        
        # Vérifier index sur colonnes importantes
        important_indexes = [
            ('customers', 'email'),
            ('work_orders', 'status'),
            ('work_orders', 'customer_id'),
            ('vehicles', 'customer_id'),
            ('interventions', 'work_order_id')
        ]
        
        for table, column in important_indexes:
            cursor.execute(f"SHOW INDEX FROM {table} WHERE Column_name = '{column}'")
            if not cursor.fetchone():
                self.missing_features.append({
                    'type': 'performance',
                    'issue': f'Index manquant sur {table}.{column}',
                    'table': table,
                    'severity': 'medium'
                })
        
        cursor.close()
    
    def generate_reports(self):
        """Générer les rapports finaux"""
        logger.info("📄 Génération des rapports")
        
        # Rapport CRUD
        with open('seeds/smoke_crud_report.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        # Rapport couverture
        with open('seeds/data_coverage.json', 'w') as f:
            json.dump(self.coverage_report, f, indent=2, default=str)
        
        # Rapport manques
        missing_md = "# Fonctionnalités Manquantes - ChronoTech\n\n"
        
        by_severity = {}
        for item in self.missing_features:
            severity = item['severity']
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(item)
        
        for severity in ['high', 'medium', 'low']:
            if severity in by_severity:
                missing_md += f"## {severity.title()} Priority\n\n"
                for item in by_severity[severity]:
                    missing_md += f"- **{item['type']}** ({item['table']}): {item['issue']}\n"
                missing_md += "\n"
        
        with open('seeds/missing_features.md', 'w') as f:
            f.write(missing_md)
        
        # Guide de reproduction
        howto_md = """# Guide de Reproduction - ChronoTech Tests

## Prérequis
```bash
cd /home/amenard/Chronotech/ChronoTech
source venv/bin/activate
export MYSQL_HOST=192.168.50.101
export MYSQL_USER=gsicloud
export MYSQL_PASSWORD='TCOChoosenOne204$'
export MYSQL_DATABASE=bdm
```

## Lancer les tests CRUD
```bash
python3 seeds/chronotech_crud_tester.py
```

## Vérifier les résultats
```bash
cat seeds/smoke_crud_report.json
cat seeds/data_coverage.json
cat seeds/missing_features.md
```

## Peupler la base avec des données de test
```bash
python3 seeds/chronotech_data_seeder.py
```
"""
        
        with open('seeds/how_to_reproduce.md', 'w') as f:
            f.write(howto_md)
        
        logger.info("✅ Rapports générés dans /seeds/")

def main():
    """Point d'entrée principal"""
    os.makedirs('logs', exist_ok=True)
    os.makedirs('seeds', exist_ok=True)
    
    tester = ChronoTechCRUDTester()
    tester.run_crud_tests()

if __name__ == "__main__":
    main()
