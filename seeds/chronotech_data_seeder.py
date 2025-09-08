#!/usr/bin/env python3
"""
ChronoTech Data Seeder & QA Agent
Générateur de données réalistes pour tests et démos (FR-CA/Québec)
Conformité Loi 25 - Données synthétiques uniquement
"""

import os
import sys
import json
import csv
import random
import logging
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
import pymysql
from faker import Faker
from faker.providers import automotive
import pytz

# Configuration Faker pour le Québec
fake = Faker('fr_CA')
fake.add_provider(automotive)

# Timezone Québec
quebec_tz = pytz.timezone('America/Toronto')

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/seeding.log', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChronoTechDataSeeder:
    """Générateur de données réalistes pour ChronoTech"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'bdm'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'charset': 'utf8mb4'
        }
        
        # Paramètres de volumétrie
        self.volumes = {
            'customers': 750,
            'users': 45,
            'vehicles': 900,  # 1.2 × customers
            'work_orders': 2250,  # 2.5 × vehicles
            'interventions': 6750,  # 3 × work_orders
            'inventory_items': 2500,
            'appointments': 1350  # 30 jours × 45 users
        }
        
        # Données de référence Québec
        self.quebec_cities = [
            ('Montréal', 'H1A 1A1'), ('Québec', 'G1A 1A1'), ('Laval', 'H7A 1A1'),
            ('Gatineau', 'J8A 1A1'), ('Longueuil', 'J4A 1A1'), ('Sherbrooke', 'J1A 1A1'),
            ('Trois-Rivières', 'G8A 1A1'), ('Saguenay', 'G7A 1A1'), ('Lévis', 'G6A 1A1'),
            ('Terrebonne', 'J6W 1A1'), ('Saint-Jean-sur-Richelieu', 'J2W 1A1'),
            ('Repentigny', 'J5Y 1A1'), ('Brossard', 'J4W 1A1'), ('Drummondville', 'J2A 1A1'),
            ('Saint-Jérôme', 'J7Y 1A1'), ('Granby', 'J2G 1A1'), ('Blainville', 'J7C 1A1'),
            ('Shawinigan', 'G9N 1A1'), ('Dollard-des-Ormeaux', 'H9A 1A1'), ('Rimouski', 'G5L 1A1')
        ]
        
        self.vehicle_makes = [
            'Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan', 'Hyundai', 'Kia', 
            'Mazda', 'Subaru', 'Volkswagen', 'BMW', 'Mercedes-Benz', 'Audi', 'Jeep'
        ]
        
        self.quebec_names = [
            'Tremblay', 'Gagnon', 'Roy', 'Côté', 'Bouchard', 'Gauthier', 'Morin', 
            'Lavoie', 'Fortin', 'Gagné', 'Ouellet', 'Pelletier', 'Bélanger', 'Lévesque'
        ]
        
        # Codes de défaut automobiles réalistes
        self.diagnostic_codes = [
            'P0300', 'P0301', 'P0302', 'P0420', 'P0440', 'P0171', 'P0174', 'P0128',
            'P0455', 'P0442', 'P0506', 'B1000', 'C1201', 'U0100', 'P0562', 'P0563'
        ]
        
        self.connection = None
        
    def connect_db(self) -> bool:
        """Établir connexion à la base de données"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            logger.info(f"✅ Connexion établie à {self.db_config['database']}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion DB: {e}")
            return False
    
    def disconnect_db(self):
        """Fermer connexion"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Connexion DB fermée")
    
    def generate_quebec_phone(self) -> str:
        """Générer numéro de téléphone québécois valide"""
        area_codes = ['514', '438', '450', '579', '418', '581', '819', '873', '367']
        area = random.choice(area_codes)
        return f"+1-{area}-{random.randint(200,999)}-{random.randint(1000,9999)}"
    
    def generate_quebec_postal_code(self) -> str:
        """Générer code postal québécois (format A1A 1A1)"""
        letters = 'ABCEGHJKLMNPRSTVWXYZ'  # Lettres valides pour codes postaux canadiens
        return f"{random.choice(letters)}{random.randint(0,9)}{random.choice(letters)} {random.randint(0,9)}{random.choice(letters)}{random.randint(0,9)}"
    
    def generate_quebec_license_plate(self) -> str:
        """Générer plaque d'immatriculation québécoise"""
        formats = [
            f"{random.randint(100,999)} {''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}",  # 123 ABC
            f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))} {random.randint(100,999)}",  # ABC 123
        ]
        return random.choice(formats)
    
    def generate_customers_data(self) -> List[Dict]:
        """Générer données clients québécois"""
        customers = []
        
        for i in range(self.volumes['customers']):
            city, postal_base = random.choice(self.quebec_cities)
            customer_type = random.choices(
                ['individual', 'company', 'government'],
                weights=[70, 25, 5],
                k=1
            )[0]
            
            if customer_type == 'individual':
                first_name = fake.first_name()
                last_name = random.choice(self.quebec_names)
                name = f"{first_name} {last_name}"
                company = None
                siret = None
            else:
                name = fake.company()
                company = name
                siret = f"{random.randint(10000000000000, 99999999999999)}" if customer_type == 'company' else None
            
            customer = {
                'name': name,
                'company': company,
                'email': fake.email(),
                'phone': self.generate_quebec_phone(),
                'mobile': self.generate_quebec_phone() if random.random() > 0.3 else None,
                'address': fake.street_address(),
                'postal_code': self.generate_quebec_postal_code(),
                'city': city,
                'country': 'CA',
                'customer_type': customer_type,
                'siret': siret,
                'status': random.choices(['active', 'inactive'], weights=[90, 10], k=1)[0],
                'is_active': 1 if random.random() > 0.1 else 0,
                'notes': fake.text(max_nb_chars=200) if random.random() > 0.5 else None,
                'language_code': 'fr-CA',
                'timezone': 'America/Montreal',
                'privacy_level': random.choices(['normal', 'restricted', 'confidential'], weights=[80, 15, 5], k=1)[0],
                'preferred_contact_method': random.choice(['email', 'phone', 'mobile']),
                'created_at': fake.date_time_between(start_date='-2y', end_date='now', tzinfo=quebec_tz),
                'payment_terms': random.choice(['30j', '60j', 'comptant']),
                'zone': random.choice(['Montreal', 'Quebec', 'Laval', 'Gatineau', 'Autre'])
            }
            customers.append(customer)
        
        return customers
    
    def generate_users_data(self) -> List[Dict]:
        """Générer données utilisateurs/employés"""
        users = []
        roles = [
            ('admin', 3), ('manager', 8), ('supervisor', 12), 
            ('technician', 18), ('receptionist', 4)
        ]
        
        user_id = 1
        for role, count in roles:
            for i in range(count):
                first_name = fake.first_name()
                last_name = random.choice(self.quebec_names)
                
                user = {
                    'id': user_id,
                    'name': f"{first_name} {last_name}",
                    'email': f"{first_name.lower()}.{last_name.lower()}@chronotech.ca",
                    'password': '$2b$12$dummy.hashed.password.for.testing',  # Hash factice
                    'role': role,
                    'is_active': 1,
                    'phone': self.generate_quebec_phone(),
                    'specialty': random.choice([
                        'Moteur', 'Transmission', 'Électrique', 'Climatisation', 
                        'Freins', 'Suspension', 'Diagnostic', 'Hybride/Électrique'
                    ]) if role == 'technician' else None,
                    'status': random.choices(['available', 'busy', 'break', 'offline'], weights=[40, 30, 20, 10], k=1)[0],
                    'experience_years': random.randint(1, 25) if role in ['technician', 'supervisor'] else random.randint(0, 15),
                    'hourly_rate': Decimal(str(random.uniform(18.0, 45.0))).quantize(Decimal('0.01')) if role == 'technician' else None,
                    'zone': random.choice(['Montreal', 'Quebec', 'Laval', 'Gatineau']),
                    'max_weekly_hours': 40,
                    'department': random.choice(['Service', 'Ventes', 'Administration', 'Direction']),
                    'created_at': fake.date_time_between(start_date='-3y', end_date='now', tzinfo=quebec_tz)
                }
                users.append(user)
                user_id += 1
        
        return users
    
    def generate_vehicles_data(self, customers: List[Dict]) -> List[Dict]:
        """Générer données véhicules"""
        vehicles = []
        vehicle_id = 1
        
        for _ in range(self.volumes['vehicles']):
            customer = random.choice(customers)
            make = random.choice(self.vehicle_makes)
            year = random.randint(2010, 2024)
            
            # Modèles réalistes par marque
            models_by_make = {
                'Toyota': ['Corolla', 'Camry', 'RAV4', 'Highlander', 'Prius'],
                'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'Fit'],
                'Ford': ['F-150', 'Escape', 'Focus', 'Explorer', 'Mustang'],
                'Chevrolet': ['Silverado', 'Cruze', 'Equinox', 'Malibu', 'Tahoe'],
                'Nissan': ['Sentra', 'Altima', 'Rogue', 'Pathfinder', 'Titan'],
            }
            
            model = random.choice(models_by_make.get(make, ['Sedan', 'SUV', 'Coupe', 'Truck']))
            
            vehicle = {
                'id': vehicle_id,
                'customer_id': customer['id'] if 'id' in customer else random.randint(1, len(customers)),
                'make': make,
                'model': model,
                'year': year,
                'mileage': random.randint(5000, 250000),
                'vin': fake.vin(),
                'license_plate': self.generate_quebec_license_plate(),
                'color': random.choice(['Blanc', 'Noir', 'Gris', 'Argent', 'Rouge', 'Bleu', 'Vert']),
                'fuel_type': random.choices(
                    ['essence', 'diesel', 'hybrid', 'electric', 'other'],
                    weights=[60, 20, 10, 8, 2],
                    k=1
                )[0],
                'notes': fake.text(max_nb_chars=150) if random.random() > 0.6 else None,
                'created_at': fake.date_time_between(start_date='-2y', end_date='now', tzinfo=quebec_tz)
            }
            vehicles.append(vehicle)
            vehicle_id += 1
        
        return vehicles
    
    def generate_work_orders_data(self, customers_data: List[Dict], vehicles_data: List[Dict], users_data: List[Dict]) -> List[Dict]:
        """Générer données work orders réalistes"""
        work_orders = []
        work_order_id = 1
        
        # Types de travaux québécois
        work_types = [
            'Changement d\'huile', 'Inspection SAAQ', 'Pneus d\'hiver', 'Pneus d\'été',
            'Freins avant', 'Freins arrière', 'Batterie', 'Alternateur', 'Démarreur',
            'Courroie de distribution', 'Transmission', 'Climatisation', 'Chauffage',
            'Système électrique', 'Suspension', 'Échappement', 'Radiateur'
        ]
        
        priorities = ['low', 'medium', 'high', 'urgent']
        statuses = ['pending', 'assigned', 'in_progress', 'completed', 'cancelled']
        
        # Générer work orders basés sur les véhicules
        target_work_orders = self.volumes['work_orders']
        
        for i in range(target_work_orders):
            # Choisir un véhicule existant
            vehicle = random.choice(vehicles_data)
            
            # Trouver le customer correspondant
            customer = next(c for c in customers_data if c['id'] == vehicle['customer_id'])
            
            # Choisir un technicien
            technician = random.choice([u for u in users_data if u['role'] in ['technician', 'admin']])
            
            created_date = fake.date_time_between(start_date='-6months', end_date='now', tzinfo=quebec_tz)
            
            work_order = {
                'id': work_order_id,
                'claim_number': f"WO-{work_order_id:06d}",
                'customer_name': customer.get('name', 'Client Inconnu'),
                'customer_address': customer.get('address', ''),
                'customer_phone': customer.get('phone', ''),
                'customer_email': customer.get('email', ''),
                'description': fake.text(max_nb_chars=200),
                'customer_id': customer['id'],
                'vehicle_id': vehicle['id'],
                'assigned_technician_id': technician['id'],
                'created_by_user_id': technician['id'],
                'priority': random.choice(priorities),
                'status': random.choices(statuses, weights=[20, 30, 30, 15, 5], k=1)[0],
                'estimated_duration': random.randint(30, 480),  # minutes
                'estimated_cost': Decimal(str(random.randint(50, 1500))),
                'actual_cost': Decimal(str(random.randint(45, 1600))) if random.random() > 0.3 else None,
                'location_latitude': Decimal(str(45.5017 + random.uniform(-0.5, 0.5))),  # Montréal area
                'location_longitude': Decimal(str(-73.5673 + random.uniform(-0.5, 0.5))),
                'created_at': created_date,
                'updated_at': created_date + timedelta(hours=random.randint(1, 72))
            }
            
            work_orders.append(work_order)
            work_order_id += 1
            
        return work_orders
    
    def generate_interventions_data(self, work_orders_data: List[Dict], users_data: List[Dict]) -> List[Dict]:
        """Générer données interventions"""
        interventions = []
        
        for work_order in work_orders_data:
            if work_order['status'] in ['in_progress', 'completed']:
                technician = random.choice([u for u in users_data if u['role'] in ['technician', 'admin']])
                
                intervention = {
                    'work_order_id': work_order['id'],
                    'task_id': work_order['id'],  # Utiliser le même ID pour simplifier
                    'technician_id': technician['id'],
                    'started_at': work_order['created_at'] + timedelta(hours=random.randint(1, 24)),
                    'ended_at': work_order['updated_at'] if work_order['status'] == 'completed' else None,
                    'result_status': random.choice(['ok', 'rework', 'cancelled']),
                    'summary': fake.text(max_nb_chars=150) if random.random() > 0.4 else None,
                    'created_at': work_order['created_at']
                }
                
                interventions.append(intervention)
        
        return interventions
    
    def seed_database(self):
        """Processus principal de peuplement"""
        try:
            logger.info("🚀 Début du processus de peuplement ChronoTech")
            
            # Générer toutes les données
            logger.info("📊 Génération des données...")
            customers_data = self.generate_customers_data()
            users_data = self.generate_users_data()
            vehicles_data = self.generate_vehicles_data(customers_data)
            
            # Insérer en base
            if self.connect_db():
                logger.info("💾 Insertion des données en base...")
                
                # Transaction globale
                cursor = self.connection.cursor()
                cursor.execute("START TRANSACTION")
                
                try:
                    # Customers (avec récupération des IDs)
                    customers_data = self.insert_customers(customers_data)
                    
                    # Users (avec récupération des IDs)
                    users_data = self.insert_users(users_data)
                    
                    # Vehicles (avec les bons customer_ids et récupération des IDs)
                    vehicles_data = self.generate_vehicles_data(customers_data)
                    vehicles_data = self.insert_vehicles(vehicles_data)
                    
                    # Work Orders (maintenant que tous les IDs existent)
                    work_orders_data = self.generate_work_orders_data(customers_data, vehicles_data, users_data)
                    work_orders_data = self.insert_work_orders(work_orders_data)
                    
                    # Interventions (skip for now due to SPRINT 1 GUARD)
                    # interventions_data = self.generate_interventions_data(work_orders_data, users_data)
                    # self.insert_interventions(interventions_data)
                    
                    # Commit final
                    cursor.execute("COMMIT")
                    logger.info("✅ Toutes les données insérées avec succès")
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    logger.error(f"❌ Erreur insertion: {e}")
                    raise
                finally:
                    cursor.close()
                    
                self.disconnect_db()
            
            logger.info("🎉 Processus de peuplement terminé avec succès")
            
        except Exception as e:
            logger.error(f"💥 Erreur fatale: {e}")
            logger.error(traceback.format_exc())
    
    def insert_customers(self, customers: List[Dict]):
        """Insérer les clients en base et récupérer les IDs"""
        cursor = self.connection.cursor()
        
        insert_sql = """
        INSERT INTO customers (
            name, company, email, phone, mobile, address, postal_code, city, country,
            customer_type, siret, status, is_active, notes, language_code, timezone,
            privacy_level, preferred_contact_method, payment_terms, zone, created_at
        ) VALUES (
            %(name)s, %(company)s, %(email)s, %(phone)s, %(mobile)s, %(address)s,
            %(postal_code)s, %(city)s, %(country)s, %(customer_type)s, %(siret)s,
            %(status)s, %(is_active)s, %(notes)s, %(language_code)s, %(timezone)s,
            %(privacy_level)s, %(preferred_contact_method)s, %(payment_terms)s,
            %(zone)s, %(created_at)s
        )
        """
        
        # Insérer un par un pour récupérer les IDs
        for i, customer in enumerate(customers):
            cursor.execute(insert_sql, customer)
            # Récupérer l'ID auto-généré et le stocker dans l'objet customer
            customer['id'] = cursor.lastrowid
            if (i + 1) % 100 == 0:
                logger.info(f"  ✅ Customers: {i + 1}/{len(customers)}")
        
        logger.info(f"  ✅ Customers: {len(customers)}/{len(customers)}")
        cursor.close()
        return customers  # Retourner les customers avec leurs IDs
    
    def insert_users(self, users: List[Dict]):
        """Insérer les utilisateurs en base et récupérer les IDs"""
        cursor = self.connection.cursor()
        
        insert_sql = """
        INSERT INTO users (
            name, email, password, role, is_active, phone, specialty, status,
            experience_years, hourly_rate, zone, max_weekly_hours, department, created_at
        ) VALUES (
            %(name)s, %(email)s, %(password)s, %(role)s, %(is_active)s, %(phone)s,
            %(specialty)s, %(status)s, %(experience_years)s, %(hourly_rate)s,
            %(zone)s, %(max_weekly_hours)s, %(department)s, %(created_at)s
        )
        """
        
        for i, user in enumerate(users):
            cursor.execute(insert_sql, user)
            user['id'] = cursor.lastrowid
            if (i + 1) % 10 == 0:
                logger.info(f"  ✅ Users: {i + 1}/{len(users)}")
        
        logger.info(f"  ✅ Users: {len(users)} insérés")
        cursor.close()
        return users
    
    def insert_vehicles(self, vehicles: List[Dict]):
        """Insérer les véhicules en base et récupérer les IDs"""
        cursor = self.connection.cursor()
        
        insert_sql = """
        INSERT INTO vehicles (
            customer_id, make, model, year, mileage, vin, license_plate,
            color, fuel_type, notes, created_at
        ) VALUES (
            %(customer_id)s, %(make)s, %(model)s, %(year)s, %(mileage)s,
            %(vin)s, %(license_plate)s, %(color)s, %(fuel_type)s,
            %(notes)s, %(created_at)s
        )
        """
        
        for i, vehicle in enumerate(vehicles):
            cursor.execute(insert_sql, vehicle)
            vehicle['id'] = cursor.lastrowid
            if (i + 1) % 100 == 0:
                logger.info(f"  ✅ Vehicles: {i + 1}/{len(vehicles)}")
        
        logger.info(f"  ✅ Vehicles: {len(vehicles)}/{len(vehicles)}")
        cursor.close()
        return vehicles
    
    def insert_work_orders(self, work_orders: List[Dict]):
        """Insérer les work orders en base et récupérer les IDs"""
        cursor = self.connection.cursor()
        
        insert_sql = """
        INSERT INTO work_orders (
            claim_number, customer_name, customer_address, customer_phone, customer_email,
            description, customer_id, vehicle_id, assigned_technician_id, created_by_user_id,
            priority, status, estimated_duration, estimated_cost, actual_cost,
            location_latitude, location_longitude, created_at, updated_at
        ) VALUES (
            %(claim_number)s, %(customer_name)s, %(customer_address)s, %(customer_phone)s,
            %(customer_email)s, %(description)s, %(customer_id)s, %(vehicle_id)s,
            %(assigned_technician_id)s, %(created_by_user_id)s, %(priority)s, %(status)s,
            %(estimated_duration)s, %(estimated_cost)s, %(actual_cost)s,
            %(location_latitude)s, %(location_longitude)s, %(created_at)s, %(updated_at)s
        )
        """
        
        for i, work_order in enumerate(work_orders):
            cursor.execute(insert_sql, work_order)
            work_order['id'] = cursor.lastrowid
            if (i + 1) % 100 == 0:
                logger.info(f"  ✅ Work Orders: {i + 1}/{len(work_orders)}")
        
        logger.info(f"  ✅ Work Orders: {len(work_orders)}/{len(work_orders)}")
        cursor.close()
        return work_orders
    
    def insert_interventions(self, interventions: List[Dict]):
        """Insérer les interventions en base"""
        cursor = self.connection.cursor()
        
        insert_sql = """
        INSERT INTO interventions (
            work_order_id, task_id, technician_id, started_at, ended_at, result_status, summary, created_at
        ) VALUES (
            %(work_order_id)s, %(task_id)s, %(technician_id)s, %(started_at)s,
            %(ended_at)s, %(result_status)s, %(summary)s, %(created_at)s
        )
        """
        
        cursor.executemany(insert_sql, interventions)
        logger.info(f"  ✅ Interventions: {len(interventions)} insérées")
        cursor.close()

def main():
    """Point d'entrée principal"""
    # Créer dossier logs si nécessaire
    os.makedirs('logs', exist_ok=True)
    
    # Lancer le seeder
    seeder = ChronoTechDataSeeder()
    seeder.seed_database()

if __name__ == "__main__":
    main()
