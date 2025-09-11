#!/usr/bin/env python3
"""
GÉNÉRATEUR DE DONNÉES ADAPTÉ À LA STRUCTURE EXISTANTE
Utilise les tables existantes de ChronoTech avec leurs structures actuelles
"""

import pymysql
import random
import json
from datetime import datetime, timedelta

# Configuration base de données
DB_CONFIG = {
    'host': '192.168.50.101',
    'user': 'gsicloud', 
    'password': 'TCOChoosenOne204$',
    'database': 'bdm',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Générateur de données factices sans dépendance externe
class SimpleFaker:
    """Générateur simple de données factices"""
    
    def __init__(self):
        self.first_names = [
            'Jean', 'Marie', 'Pierre', 'Sophie', 'Paul', 'Anne', 'Michel', 'Catherine',
            'François', 'Isabelle', 'Philippe', 'Nathalie', 'Alain', 'Monique', 'Claude',
            'Sylvie', 'Bernard', 'Christine', 'Daniel', 'Martine', 'Jacques', 'Nicole',
            'André', 'Françoise', 'Louis', 'Brigitte', 'Robert', 'Dominique', 'Henri'
        ]
        
        self.last_names = [
            'Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit',
            'Durand', 'Leroy', 'Moreau', 'Simon', 'Laurent', 'Lefebvre', 'Michel',
            'Garcia', 'David', 'Bertrand', 'Roux', 'Vincent', 'Fournier', 'Morel',
            'Girard', 'André', 'Lefevre', 'Mercier', 'Dupont', 'Lambert', 'Bonnet'
        ]
        
        self.companies = [
            'Entreprise Générale du Bâtiment', 'Solutions Techniques Avancées',
            'Maintenance Industrielle Pro', 'Services Multi-Techniques',
            'Réparations Express SARL', 'TechnoFix Solutions', 'Expert Maintenance',
            'Dépannage Rapide', 'Installations Professionnelles', 'Rénovation Plus'
        ]
        
        self.cities = [
            'Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 'Nantes', 'Strasbourg',
            'Montpellier', 'Bordeaux', 'Lille', 'Rennes', 'Reims', 'Le Havre'
        ]
        
        self.streets = [
            'Avenue de la République', 'Rue Victor Hugo', 'Boulevard Saint-Michel',
            'Place de la Liberté', 'Rue des Fleurs', 'Avenue Jean Jaurès'
        ]
    
    def name(self):
        return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"
    
    def unique_email(self):
        domains = ['email.com', 'mail.fr', 'exemple.fr', 'test.org']
        name_part = f"{random.choice(self.first_names).lower()}.{random.choice(self.last_names).lower()}{random.randint(1,999)}"
        return f"{name_part}@{random.choice(domains)}"
    
    def company(self):
        return random.choice(self.companies)
    
    def phone_number(self):
        return f"0{random.randint(1,9)}.{random.randint(10,99)}.{random.randint(10,99)}.{random.randint(10,99)}.{random.randint(10,99)}"
    
    def text(self, max_nb_chars=200):
        sentences = [
            "Problème détecté sur l'équipement principal.",
            "Maintenance préventive nécessaire pour éviter les pannes.",
            "Réparation urgente suite à dysfonctionnement.",
            "Installation de nouveaux composants selon les normes.",
            "Vérification complète du système demandée par le client."
        ]
        return " ".join(random.sample(sentences, random.randint(1, 3)))[:max_nb_chars]
    
    def password_hash(self):
        return f"$2b$12${''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./', k=53))}"

fake = SimpleFaker()

class ChronoTechDataGenerator:
    """Générateur de données pour ChronoTech avec structure existante"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Connexion à la base de données"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            print("✅ Connexion MySQL établie")
        except Exception as e:
            print(f"❌ Erreur connexion MySQL: {e}")
            raise
    
    def execute_query(self, query, params=None, fetch=False):
        """Exécuter une requête"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                self.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ Erreur requête: {e}")
            self.connection.rollback()
            return None
    
    def check_table_structure(self, table_name):
        """Vérifier la structure d'une table"""
        try:
            query = f"DESCRIBE {table_name}"
            result = self.execute_query(query, fetch=True)
            if result:
                print(f"📋 Structure de {table_name}:")
                for row in result[:5]:  # Afficher seulement les 5 premiers champs
                    print(f"   • {row['Field']} ({row['Type']})")
                if len(result) > 5:
                    print(f"   ... et {len(result) - 5} autres champs")
            return result
        except Exception as e:
            print(f"❌ Erreur structure {table_name}: {e}")
            return None
    
    def clear_existing_data(self):
        """Nettoyer les données existantes pour la démonstration"""
        print("\n🧹 NETTOYAGE DES DONNÉES EXISTANTES")
        print("="*40)
        
        # Tables à nettoyer (dans l'ordre des dépendances)
        tables = [
            'time_tracking', 'inventory_movements', 'interventions', 
            'appointments', 'work_orders', 'vehicles', 'customers', 
            'technicians', 'products'
        ]
        
        # Ne pas supprimer les utilisateurs existants, juste ajouter
        for table in tables:
            try:
                self.execute_query(f"DELETE FROM {table}")
                print(f"   ✅ Table {table} nettoyée")
            except Exception as e:
                print(f"   ⚠️ {table} - {e}")
    
    def generate_demo_users(self, count=20):
        """Générer des utilisateurs de démonstration"""
        print(f"\n👥 GÉNÉRATION DE {count} UTILISATEURS DE DÉMONSTRATION")
        print("="*50)
        
        roles = ['technician', 'admin', 'manager']
        specialties = [
            'Électricité', 'Plomberie', 'Climatisation', 'Informatique',
            'Mécanique', 'Maintenance', 'Installation', 'Dépannage'
        ]
        
        departments = [
            'Électricité', 'Plomberie', 'HVAC', 'Support IT', 
            'Mécanique', 'Maintenance Générale'
        ]
        
        users_data = []
        
        for i in range(count):
            role = random.choice(roles) if i > 0 else 'admin'  # Premier utilisateur admin
            specialty = random.choice(specialties)
            department = random.choice(departments)
            
            # Générer les compétences
            skills = random.sample([
                'Installation électrique', 'Plomberie', 'Climatisation',
                'Réseau informatique', 'Soudure', 'Dépannage',
                'Maintenance préventive', 'Service client'
            ], random.randint(2, 5))
            
            user_data = {
                'name': fake.name(),
                'email': fake.unique_email(),
                'password': fake.password_hash(),
                'role': role,
                'phone': fake.phone_number(),
                'specialty': specialty,
                'department': department,
                'certification_level': random.choice(['junior', 'senior', 'expert']),
                'hourly_rate': round(random.uniform(25, 85), 2),
                'availability_status': random.choice(['available', 'busy', 'break']),
                'skills': json.dumps(skills),
                'zone': f"Zone {random.randint(1, 5)}"
            }
            
            query = '''
                INSERT INTO users (name, email, password, role, phone, specialty, 
                                 department, certification_level, hourly_rate, 
                                 availability_status, skills, zone)
                VALUES (%(name)s, %(email)s, %(password)s, %(role)s, %(phone)s, 
                        %(specialty)s, %(department)s, %(certification_level)s, 
                        %(hourly_rate)s, %(availability_status)s, %(skills)s, %(zone)s)
            '''
            
            user_id = self.execute_query(query, user_data)
            if user_id:
                users_data.append({**user_data, 'id': user_id})
        
        print(f"   ✅ {len(users_data)} utilisateurs créés")
        return users_data
    
    def create_work_orders_table(self):
        """Créer la table work_orders si elle n'existe pas"""
        query = '''
            CREATE TABLE IF NOT EXISTS work_orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                customer_name VARCHAR(200),
                customer_email VARCHAR(200),
                customer_phone VARCHAR(50),
                technician_id INT,
                title VARCHAR(300) NOT NULL,
                description TEXT,
                priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
                status ENUM('pending', 'assigned', 'in_progress', 'review', 'completed', 'cancelled') DEFAULT 'pending',
                estimated_hours DECIMAL(5,2),
                actual_hours DECIMAL(5,2),
                cost_estimate DECIMAL(10,2),
                final_cost DECIMAL(10,2),
                scheduled_date DATETIME,
                started_at DATETIME,
                completed_at DATETIME,
                location VARCHAR(300),
                equipment_needed JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (technician_id) REFERENCES users(id)
            )
        '''
        self.execute_query(query)
        print("   ✅ Table work_orders créée/vérifiée")
    
    def generate_work_orders(self, users_data, count=50):
        """Générer des bons de travail"""
        print(f"\n📋 GÉNÉRATION DE {count} BONS DE TRAVAIL")
        print("="*40)
        
        technicians = [u for u in users_data if u['role'] == 'technician']
        
        priorities = ['low', 'medium', 'high', 'urgent']
        priority_weights = [20, 50, 25, 5]
        
        statuses = ['pending', 'assigned', 'in_progress', 'review', 'completed']
        status_weights = [15, 20, 25, 15, 25]
        
        work_types = [
            'Réparation électrique', 'Installation plomberie', 'Maintenance HVAC',
            'Dépannage informatique', 'Réparation mécanique', 'Installation système',
            'Contrôle qualité', 'Maintenance préventive', 'Réparation urgente'
        ]
        
        locations = [
            'Bureau principal - Paris', 'Entrepôt - Lyon', 'Site industriel - Marseille',
            'Centre commercial - Toulouse', 'Résidence - Nice', 'Hôpital - Nantes'
        ]
        
        work_orders_data = []
        
        for i in range(count):
            technician = random.choice(technicians) if technicians and random.choice([True, False]) else None
            priority = random.choices(priorities, weights=priority_weights)[0]
            status = random.choices(statuses, weights=status_weights)[0]
            work_type = random.choice(work_types)
            
            estimated_hours = round(random.uniform(1, 12), 2)
            cost_estimate = round(estimated_hours * random.uniform(50, 120), 2)
            
            # Générer des données réalistes selon le statut
            actual_hours = None
            final_cost = None
            started_at = None
            completed_at = None
            
            if status in ['in_progress', 'review', 'completed']:
                actual_hours = round(estimated_hours * random.uniform(0.8, 1.3), 2)
                final_cost = round(cost_estimate * random.uniform(0.9, 1.2), 2)
                started_at = datetime.now() - timedelta(days=random.randint(1, 10))
                
                if status == 'completed':
                    completed_at = started_at + timedelta(hours=actual_hours)
            
            equipment_needed = random.sample([
                'Multimètre', 'Perceuse', 'Clés à molette', 'Matériel de sécurité',
                'Pièces de rechange', 'Outils de diagnostic', 'Équipement de nettoyage'
            ], random.randint(2, 4))
            
            wo_data = {
                'customer_name': fake.name(),
                'customer_email': fake.unique_email(),
                'customer_phone': fake.phone_number(),
                'technician_id': technician['id'] if technician else None,
                'title': work_type,
                'description': fake.text(250),
                'priority': priority,
                'status': status,
                'estimated_hours': estimated_hours,
                'actual_hours': actual_hours,
                'cost_estimate': cost_estimate,
                'final_cost': final_cost,
                'scheduled_date': datetime.now() + timedelta(days=random.randint(1, 30)),
                'started_at': started_at,
                'completed_at': completed_at,
                'location': random.choice(locations),
                'equipment_needed': json.dumps(equipment_needed)
            }
            
            query = '''
                INSERT INTO work_orders (customer_name, customer_email, customer_phone,
                                       technician_id, title, description, priority, status,
                                       estimated_hours, actual_hours, cost_estimate, final_cost,
                                       scheduled_date, started_at, completed_at, location,
                                       equipment_needed)
                VALUES (%(customer_name)s, %(customer_email)s, %(customer_phone)s,
                        %(technician_id)s, %(title)s, %(description)s, %(priority)s,
                        %(status)s, %(estimated_hours)s, %(actual_hours)s,
                        %(cost_estimate)s, %(final_cost)s, %(scheduled_date)s,
                        %(started_at)s, %(completed_at)s, %(location)s,
                        %(equipment_needed)s)
            '''
            
            wo_id = self.execute_query(query, wo_data)
            if wo_id:
                work_orders_data.append({**wo_data, 'id': wo_id})
        
        print(f"   ✅ {len(work_orders_data)} bons de travail créés")
        return work_orders_data
    
    def generate_summary_stats(self):
        """Générer des statistiques de résumé"""
        print("\n📊 STATISTIQUES DE LA PLATEFORME")
        print("="*35)
        
        queries = {
            'Utilisateurs total': 'SELECT COUNT(*) as count FROM users',
            'Techniciens actifs': "SELECT COUNT(*) as count FROM users WHERE role='technician' AND is_active=1",
            'Bons de travail': 'SELECT COUNT(*) as count FROM work_orders',
            'Tâches en cours': "SELECT COUNT(*) as count FROM work_orders WHERE status='in_progress'",
            'Tâches terminées': "SELECT COUNT(*) as count FROM work_orders WHERE status='completed'"
        }
        
        for label, query in queries.items():
            result = self.execute_query(query, fetch=True)
            if result:
                count = result[0]['count']
                print(f"   • {label}: {count}")
    
    def close(self):
        """Fermer la connexion"""
        if self.connection:
            self.connection.close()

def main():
    """Fonction principale"""
    print("🚀 CHRONOTECH - GÉNÉRATEUR DE DONNÉES ADAPTÉ")
    print("="*50)
    print("📊 MySQL Server: 192.168.50.101")
    print("👤 User: gsicloud")  
    print("🗄️ Database: bdm")
    print()
    
    try:
        generator = ChronoTechDataGenerator()
        
        # Vérifier les structures existantes
        print("🔍 VÉRIFICATION DES STRUCTURES EXISTANTES")
        print("="*45)
        generator.check_table_structure('users')
        
        # Nettoyer les anciennes données de démonstration
        generator.clear_existing_data()
        
        # Créer les tables manquantes
        generator.create_work_orders_table()
        
        # Générer les nouvelles données
        users_data = generator.generate_demo_users(30)
        work_orders_data = generator.generate_work_orders(users_data, 80)
        
        # Afficher les statistiques
        generator.generate_summary_stats()
        
        print("\n" + "="*50)
        print("✅ GÉNÉRATION TERMINÉE - PLATEFORME PRÊTE!")
        print("="*50)
        
        print(f"\n🎯 DONNÉES GÉNÉRÉES:")
        print(f"   • {len(users_data)} utilisateurs de démonstration")
        print(f"   • {len(work_orders_data)} bons de travail")
        print(f"   • Données réalistes avec différents statuts")
        print(f"   • Techniciens assignés aux tâches")
        
        print(f"\n🌐 ACCÈS À LA PLATEFORME:")
        print(f"   URL: http://localhost:5021")
        print(f"   Dashboard: http://localhost:5021/dashboard")
        print(f"   Kanban: http://localhost:5021/interventions/kanban")
        
        generator.close()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
