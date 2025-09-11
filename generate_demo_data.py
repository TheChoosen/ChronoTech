#!/usr/bin/env python3
"""
GÉNÉRATEUR DE DONNÉES DE DÉMONSTRATION CHRONOTECH
Génération complète de données réalistes pour montrer le plein potentiel de la plateforme
MySQL Server: 192.168.50.101 | User: gsicloud | DB: bdm
"""

import pymysql
import random
import json
from datetime import datetime, timedelta

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
            'Montpellier', 'Bordeaux', 'Lille', 'Rennes', 'Reims', 'Le Havre',
            'Saint-Étienne', 'Toulon', 'Grenoble', 'Dijon', 'Angers', 'Nîmes'
        ]
        
        self.streets = [
            'Avenue de la République', 'Rue Victor Hugo', 'Boulevard Saint-Michel',
            'Place de la Liberté', 'Rue des Fleurs', 'Avenue Jean Jaurès',
            'Rue de la Paix', 'Boulevard Voltaire', 'Avenue Charles de Gaulle'
        ]
    
    def name(self):
        return f"{random.choice(self.first_names)} {random.choice(self.last_names)}"
    
    def email(self):
        domains = ['email.com', 'mail.fr', 'exemple.fr', 'test.org']
        name_part = f"{random.choice(self.first_names).lower()}.{random.choice(self.last_names).lower()}"
        return f"{name_part}@{random.choice(domains)}"
    
    def company(self):
        return random.choice(self.companies)
    
    def phone_number(self):
        return f"0{random.randint(1,9)}.{random.randint(10,99)}.{random.randint(10,99)}.{random.randint(10,99)}.{random.randint(10,99)}"
    
    def address(self):
        return f"{random.randint(1,999)} {random.choice(self.streets)}, {random.randint(10000,99999)} {random.choice(self.cities)}"
    
    def city(self):
        return random.choice(self.cities)
    
    def text(self, max_nb_chars=200):
        sentences = [
            "Problème détecté sur l'équipement principal.",
            "Maintenance préventive nécessaire pour éviter les pannes.",
            "Réparation urgente suite à dysfonctionnement.",
            "Installation de nouveaux composants selon les normes.",
            "Vérification complète du système demandée par le client.",
            "Mise à jour des paramètres de configuration.",
            "Remplacement de pièces défectueuses identifiées.",
            "Optimisation des performances du système."
        ]
        return " ".join(random.sample(sentences, random.randint(1, 3)))[:max_nb_chars]
    
    def sha256(self):
        return f"{''.join(random.choices('abcdef0123456789', k=64))}"
    
    def vat_id(self):
        return f"FR{random.randint(10,99)}{random.randint(100000000,999999999)}"
    
    def date_time_between(self, start_date='-1y', end_date='now'):
        if start_date == '-1y':
            start = datetime.now() - timedelta(days=365)
        elif start_date == '-2y':
            start = datetime.now() - timedelta(days=730)
        elif start_date == '-5y':
            start = datetime.now() - timedelta(days=1825)
        elif start_date == '-60d':
            start = datetime.now() - timedelta(days=60)
        elif start_date == '-30d':
            start = datetime.now() - timedelta(days=30)
        elif start_date == '-7d':
            start = datetime.now() - timedelta(days=7)
        elif start_date == '-1d':
            start = datetime.now() - timedelta(days=1)
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date == 'now':
            end = datetime.now()
        elif end_date == '+30d':
            end = datetime.now() + timedelta(days=30)
        elif end_date == '-1m':
            end = datetime.now() - timedelta(days=30)
        else:
            end = datetime.now()
        
        time_diff = end - start
        random_seconds = random.randint(0, int(time_diff.total_seconds()))
        return start + timedelta(seconds=random_seconds)
    
    def date_between(self, start_date='-5y', end_date='-1m'):
        dt = self.date_time_between(start_date, end_date)
        return dt.date()
    
    def unique_email(self):
        """Générer un email unique (simulation)"""
        domains = ['email.com', 'mail.fr', 'exemple.fr', 'test.org']
        name_part = f"{random.choice(self.first_names).lower()}.{random.choice(self.last_names).lower()}{random.randint(1,999)}"
        return f"{name_part}@{random.choice(domains)}"

fake = SimpleFaker()

# Configuration base de données
DB_CONFIG = {
    'host': '192.168.50.101',
    'user': 'gsicloud', 
    'password': 'TCOChoosenOne204$',
    'database': 'bdm',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

fake = SimpleFaker()

class ChronoTechDataGenerator:
    """Générateur de données pour ChronoTech"""
    
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
    
    def create_tables(self):
        """Créer les tables nécessaires"""
        print("\n🏗️ CRÉATION DES TABLES")
        print("="*30)
        
        tables = {
            'users': '''
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255),
                    role ENUM('admin', 'manager', 'technician', 'customer') DEFAULT 'customer',
                    phone VARCHAR(20),
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''',
            
            'customers': '''
                CREATE TABLE IF NOT EXISTS customers (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT,
                    company_name VARCHAR(200),
                    contact_person VARCHAR(100),
                    customer_type ENUM('company', 'individual', 'government') DEFAULT 'individual',
                    industry VARCHAR(100),
                    tax_number VARCHAR(50),
                    billing_address TEXT,
                    shipping_address TEXT,
                    credit_limit DECIMAL(10,2) DEFAULT 0,
                    payment_terms INT DEFAULT 30,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''',
            
            'technicians': '''
                CREATE TABLE IF NOT EXISTS technicians (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT,
                    employee_id VARCHAR(50) UNIQUE,
                    department VARCHAR(100),
                    specialization VARCHAR(200),
                    certification_level ENUM('junior', 'senior', 'expert') DEFAULT 'junior',
                    hourly_rate DECIMAL(8,2),
                    status ENUM('available', 'busy', 'pause', 'offline') DEFAULT 'available',
                    skills JSON,
                    location VARCHAR(200),
                    hired_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''',
            
            'work_orders': '''
                CREATE TABLE IF NOT EXISTS work_orders (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    customer_id INT,
                    technician_id INT,
                    title VARCHAR(200) NOT NULL,
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
                    location VARCHAR(200),
                    equipment_needed JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id),
                    FOREIGN KEY (technician_id) REFERENCES technicians(id)
                )
            ''',
            
            'interventions': '''
                CREATE TABLE IF NOT EXISTS interventions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    work_order_id INT,
                    technician_id INT,
                    intervention_type ENUM('maintenance', 'repair', 'installation', 'inspection') DEFAULT 'repair',
                    status ENUM('scheduled', 'in_progress', 'completed', 'cancelled') DEFAULT 'scheduled',
                    scheduled_start DATETIME,
                    actual_start DATETIME,
                    actual_end DATETIME,
                    description TEXT,
                    findings TEXT,
                    actions_taken TEXT,
                    parts_used JSON,
                    photos JSON,
                    customer_signature TEXT,
                    satisfaction_rating INT CHECK (satisfaction_rating >= 1 AND satisfaction_rating <= 5),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
                    FOREIGN KEY (technician_id) REFERENCES technicians(id)
                )
            ''',
            
            'products': '''
                CREATE TABLE IF NOT EXISTS products (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(200) NOT NULL,
                    sku VARCHAR(100) UNIQUE,
                    category VARCHAR(100),
                    brand VARCHAR(100),
                    model VARCHAR(100),
                    description TEXT,
                    unit_price DECIMAL(10,2),
                    cost_price DECIMAL(10,2),
                    stock_quantity INT DEFAULT 0,
                    min_stock_level INT DEFAULT 5,
                    supplier VARCHAR(200),
                    warranty_period INT DEFAULT 12,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'inventory_movements': '''
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    product_id INT,
                    movement_type ENUM('in', 'out', 'adjustment') NOT NULL,
                    quantity INT NOT NULL,
                    reference_id INT,
                    reference_type ENUM('work_order', 'intervention', 'purchase', 'adjustment'),
                    notes TEXT,
                    performed_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (performed_by) REFERENCES users(id)
                )
            ''',
            
            'time_tracking': '''
                CREATE TABLE IF NOT EXISTS time_tracking (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    technician_id INT,
                    work_order_id INT,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    duration_minutes INT,
                    activity_type VARCHAR(100),
                    description TEXT,
                    billable BOOLEAN DEFAULT TRUE,
                    hourly_rate DECIMAL(8,2),
                    total_cost DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (technician_id) REFERENCES technicians(id),
                    FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
                )
            ''',
            
            'appointments': '''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    customer_id INT,
                    technician_id INT,
                    work_order_id INT,
                    title VARCHAR(200),
                    description TEXT,
                    appointment_date DATETIME,
                    duration_minutes INT DEFAULT 60,
                    status ENUM('scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled') DEFAULT 'scheduled',
                    location VARCHAR(200),
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id),
                    FOREIGN KEY (technician_id) REFERENCES technicians(id),
                    FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
                )
            ''',
            
            'vehicles': '''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    plate_number VARCHAR(20) UNIQUE NOT NULL,
                    brand VARCHAR(100),
                    model VARCHAR(100),
                    year INT,
                    vehicle_type ENUM('van', 'truck', 'car', 'motorcycle') DEFAULT 'van',
                    assigned_technician_id INT,
                    fuel_type ENUM('gasoline', 'diesel', 'electric', 'hybrid') DEFAULT 'diesel',
                    mileage INT DEFAULT 0,
                    last_maintenance DATE,
                    next_maintenance DATE,
                    insurance_expiry DATE,
                    status ENUM('available', 'in_use', 'maintenance', 'retired') DEFAULT 'available',
                    gps_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (assigned_technician_id) REFERENCES technicians(id)
                )
            '''
        }
        
        for table_name, query in tables.items():
            try:
                self.execute_query(query)
                print(f"   ✅ Table {table_name} créée/vérifiée")
            except Exception as e:
                print(f"   ❌ Erreur table {table_name}: {e}")
    
    def generate_users(self, count=50):
        """Générer des utilisateurs"""
        print(f"\n👥 GÉNÉRATION DE {count} UTILISATEURS")
        print("="*35)
        
        roles = ['admin', 'manager', 'technician', 'customer']
        role_weights = [2, 5, 15, 78]  # Pourcentages
        
        users_data = []
        
        for i in range(count):
            role = random.choices(roles, weights=role_weights)[0]
            
            user_data = {
                'name': fake.name(),
                'email': fake.unique_email(),
                'password_hash': fake.sha256(),
                'role': role,
                'phone': fake.phone_number(),
                'address': fake.address(),
                'created_at': fake.date_time_between(start_date='-2y', end_date='now')
            }
            
            query = '''
                INSERT INTO users (name, email, password_hash, role, phone, address, created_at)
                VALUES (%(name)s, %(email)s, %(password_hash)s, %(role)s, %(phone)s, %(address)s, %(created_at)s)
            '''
            
            user_id = self.execute_query(query, user_data)
            if user_id:
                users_data.append({**user_data, 'id': user_id})
        
        print(f"   ✅ {len(users_data)} utilisateurs créés")
        return users_data
    
    def generate_customers(self, users_data):
        """Générer des clients"""
        customer_users = [u for u in users_data if u['role'] == 'customer']
        
        print(f"\n🏢 GÉNÉRATION DE {len(customer_users)} CLIENTS")
        print("="*35)
        
        industries = [
            'Manufacturing', 'Healthcare', 'Education', 'Retail', 'Construction',
            'Technology', 'Finance', 'Transportation', 'Hospitality', 'Real Estate'
        ]
        
        customer_types = ['company', 'individual', 'government']
        type_weights = [60, 35, 5]
        
        customers_data = []
        
        for user in customer_users:
            customer_type = random.choices(customer_types, weights=type_weights)[0]
            
            customer_data = {
                'user_id': user['id'],
                'company_name': fake.company() if customer_type == 'company' else None,
                'contact_person': user['name'],
                'customer_type': customer_type,
                'industry': random.choice(industries) if customer_type == 'company' else None,
                'tax_number': fake.vat_id() if customer_type != 'individual' else None,
                'billing_address': fake.address(),
                'shipping_address': fake.address() if random.choice([True, False]) else None,
                'credit_limit': round(random.uniform(1000, 50000), 2),
                'payment_terms': random.choice([15, 30, 45, 60])
            }
            
            query = '''
                INSERT INTO customers (user_id, company_name, contact_person, customer_type, 
                                     industry, tax_number, billing_address, shipping_address, 
                                     credit_limit, payment_terms)
                VALUES (%(user_id)s, %(company_name)s, %(contact_person)s, %(customer_type)s,
                        %(industry)s, %(tax_number)s, %(billing_address)s, %(shipping_address)s,
                        %(credit_limit)s, %(payment_terms)s)
            '''
            
            customer_id = self.execute_query(query, customer_data)
            if customer_id:
                customers_data.append({**customer_data, 'id': customer_id})
        
        print(f"   ✅ {len(customers_data)} clients créés")
        return customers_data
    
    def generate_technicians(self, users_data):
        """Générer des techniciens"""
        tech_users = [u for u in users_data if u['role'] == 'technician']
        
        print(f"\n🔧 GÉNÉRATION DE {len(tech_users)} TECHNICIENS")
        print("="*38)
        
        departments = ['Electrical', 'Plumbing', 'HVAC', 'IT Support', 'Mechanical', 'General Maintenance']
        specializations = [
            'Industrial Electrical Systems', 'Residential Plumbing', 'Commercial HVAC',
            'Network Infrastructure', 'Hydraulic Systems', 'Preventive Maintenance',
            'Emergency Repairs', 'Installation Services', 'Quality Control'
        ]
        
        skills_pool = [
            'Electrical Installation', 'Pipe Fitting', 'Air Conditioning', 'Networking',
            'Welding', 'Carpentry', 'Painting', 'Troubleshooting', 'Safety Protocols',
            'Equipment Calibration', 'Project Management', 'Customer Service'
        ]
        
        statuses = ['available', 'busy', 'pause', 'offline']
        status_weights = [50, 30, 10, 10]
        
        technicians_data = []
        
        for user in tech_users:
            skills = random.sample(skills_pool, random.randint(3, 7))
            
            tech_data = {
                'user_id': user['id'],
                'employee_id': f"TECH{random.randint(1000, 9999)}",
                'department': random.choice(departments),
                'specialization': random.choice(specializations),
                'certification_level': random.choices(['junior', 'senior', 'expert'], weights=[40, 45, 15])[0],
                'hourly_rate': round(random.uniform(25, 85), 2),
                'status': random.choices(statuses, weights=status_weights)[0],
                'skills': json.dumps(skills),
                'location': fake.city(),
                'hired_date': fake.date_between(start_date='-5y', end_date='-1m')
            }
            
            query = '''
                INSERT INTO technicians (user_id, employee_id, department, specialization,
                                       certification_level, hourly_rate, status, skills,
                                       location, hired_date)
                VALUES (%(user_id)s, %(employee_id)s, %(department)s, %(specialization)s,
                        %(certification_level)s, %(hourly_rate)s, %(status)s, %(skills)s,
                        %(location)s, %(hired_date)s)
            '''
            
            tech_id = self.execute_query(query, tech_data)
            if tech_id:
                technicians_data.append({**tech_data, 'id': tech_id})
        
        print(f"   ✅ {len(technicians_data)} techniciens créés")
        return technicians_data
    
    def generate_work_orders(self, customers_data, technicians_data, count=100):
        """Générer des bons de travail"""
        print(f"\n📋 GÉNÉRATION DE {count} BONS DE TRAVAIL")
        print("="*40)
        
        priorities = ['low', 'medium', 'high', 'urgent']
        priority_weights = [20, 50, 25, 5]
        
        statuses = ['pending', 'assigned', 'in_progress', 'review', 'completed', 'cancelled']
        status_weights = [15, 20, 25, 10, 25, 5]
        
        work_types = [
            'Equipment Repair', 'System Installation', 'Preventive Maintenance',
            'Emergency Service', 'Inspection', 'Upgrade', 'Troubleshooting',
            'Calibration', 'Cleaning', 'Replacement'
        ]
        
        equipment_types = [
            'HVAC System', 'Electrical Panel', 'Plumbing Fixture', 'Computer Network',
            'Industrial Machine', 'Security System', 'Lighting', 'Generator',
            'Pump', 'Motor', 'Sensor', 'Control System'
        ]
        
        work_orders_data = []
        
        for i in range(count):
            customer = random.choice(customers_data)
            technician = random.choice(technicians_data) if random.choice([True, False]) else None
            priority = random.choices(priorities, weights=priority_weights)[0]
            status = random.choices(statuses, weights=status_weights)[0]
            
            work_type = random.choice(work_types)
            equipment = random.choice(equipment_types)
            
            estimated_hours = round(random.uniform(1, 16), 2)
            cost_estimate = round(estimated_hours * random.uniform(50, 120), 2)
            
            # Générer des heures réelles et coût final pour les tâches terminées
            actual_hours = None
            final_cost = None
            started_at = None
            completed_at = None
            
            if status in ['in_progress', 'review', 'completed']:
                actual_hours = round(estimated_hours * random.uniform(0.8, 1.3), 2)
                final_cost = round(cost_estimate * random.uniform(0.9, 1.2), 2)
                started_at = fake.date_time_between(start_date='-30d', end_date='-1d')
                
                if status == 'completed':
                    completed_at = started_at + timedelta(hours=actual_hours)
            
            equipment_needed = random.sample([
                'Multimeter', 'Screwdriver Set', 'Drill', 'Wire Strippers',
                'Pipe Wrench', 'Safety Equipment', 'Replacement Parts',
                'Diagnostic Tools', 'Cleaning Supplies', 'Lubricants'
            ], random.randint(2, 5))
            
            wo_data = {
                'customer_id': customer['id'],
                'technician_id': technician['id'] if technician else None,
                'title': f"{work_type} - {equipment}",
                'description': fake.text(max_nb_chars=300),
                'priority': priority,
                'status': status,
                'estimated_hours': estimated_hours,
                'actual_hours': actual_hours,
                'cost_estimate': cost_estimate,
                'final_cost': final_cost,
                'scheduled_date': fake.date_time_between(start_date='-7d', end_date='+30d'),
                'started_at': started_at,
                'completed_at': completed_at,
                'location': fake.address(),
                'equipment_needed': json.dumps(equipment_needed),
                'created_at': fake.date_time_between(start_date='-60d', end_date='now')
            }
            
            query = '''
                INSERT INTO work_orders (customer_id, technician_id, title, description,
                                       priority, status, estimated_hours, actual_hours,
                                       cost_estimate, final_cost, scheduled_date,
                                       started_at, completed_at, location,
                                       equipment_needed, created_at)
                VALUES (%(customer_id)s, %(technician_id)s, %(title)s, %(description)s,
                        %(priority)s, %(status)s, %(estimated_hours)s, %(actual_hours)s,
                        %(cost_estimate)s, %(final_cost)s, %(scheduled_date)s,
                        %(started_at)s, %(completed_at)s, %(location)s,
                        %(equipment_needed)s, %(created_at)s)
            '''
            
            wo_id = self.execute_query(query, wo_data)
            if wo_id:
                work_orders_data.append({**wo_data, 'id': wo_id})
        
        print(f"   ✅ {len(work_orders_data)} bons de travail créés")
        return work_orders_data
    
    def close(self):
        """Fermer la connexion"""
        if self.connection:
            self.connection.close()

def main():
    """Fonction principale"""
    print("🚀 CHRONOTECH - GÉNÉRATEUR DE DONNÉES DE DÉMONSTRATION")
    print("="*60)
    print("📊 MySQL Server: 192.168.50.101")
    print("👤 User: gsicloud")
    print("🗄️ Database: bdm")
    print()
    
    try:
        # Initialiser le générateur
        generator = ChronoTechDataGenerator()
        
        # Créer les tables
        generator.create_tables()
        
        # Générer les données
        users_data = generator.generate_users(50)
        customers_data = generator.generate_customers(users_data)
        technicians_data = generator.generate_technicians(users_data)
        work_orders_data = generator.generate_work_orders(customers_data, technicians_data, 100)
        
        print("\n" + "="*60)
        print("✅ GÉNÉRATION DE DONNÉES TERMINÉE")
        print("="*60)
        
        print(f"\n📊 RÉSUMÉ:")
        print(f"   • {len(users_data)} utilisateurs")
        print(f"   • {len(customers_data)} clients")
        print(f"   • {len(technicians_data)} techniciens")
        print(f"   • {len(work_orders_data)} bons de travail")
        
        print(f"\n🎯 LA PLATEFORME EST PRÊTE POUR LA DÉMONSTRATION!")
        print(f"🌐 Accès: http://localhost:5021")
        
        generator.close()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
