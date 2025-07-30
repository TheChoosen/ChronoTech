#!/usr/bin/env python3
"""
Script pour insérer des données de test dans les travaux demandés
"""

import pymysql
from datetime import datetime, timedelta
import random

# Configuration de la base de données
MYSQL_HOST = '192.168.50.101'
MYSQL_PORT = 3306
MYSQL_USER = 'gsicloud'
MYSQL_PASSWORD = 'TCOChoosenOne204$'
MYSQL_DB = 'gsi'

def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

def insert_sample_work_orders():
    """Insérer des travaux demandés d'exemple"""
    
    sample_work_orders = [
        {
            'claim_number': 'WO-2025-001',
            'customer_name': 'Entreprise Martin SARL',
            'customer_address': '123 Rue de la Paix\n75001 Paris',
            'customer_phone': '+33 1 23 45 67 89',
            'customer_email': 'contact@entreprise-martin.fr',
            'description': 'Maintenance préventive sur système de climatisation - vérification des filtres, nettoyage des conduits et contrôle du fluide frigorigène.',
            'priority': 'medium',
            'status': 'pending',
            'estimated_duration': 120,
            'estimated_cost': 350.00,
            'scheduled_date': datetime.now() + timedelta(days=2),
            'notes': 'Client préfère les interventions le matin entre 8h et 12h'
        },
        {
            'claim_number': 'WO-2025-002',
            'customer_name': 'Garage Dupont & Fils',
            'customer_address': '456 Avenue des Champs\n69000 Lyon',
            'customer_phone': '+33 4 78 90 12 34',
            'customer_email': 'garage.dupont@email.com',
            'description': 'Réparation urgente du pont élévateur - problème hydraulique, fuite au niveau du vérin principal.',
            'priority': 'urgent',
            'status': 'assigned',
            'estimated_duration': 180,
            'estimated_cost': 850.00,
            'scheduled_date': datetime.now() + timedelta(hours=4),
            'notes': 'Intervention prioritaire - garage à l\'arrêt sans le pont'
        },
        {
            'claim_number': 'WO-2025-003',
            'customer_name': 'Société TechnoServices',
            'customer_address': '789 Boulevard de l\'Innovation\n31000 Toulouse',
            'customer_phone': '+33 5 61 23 45 67',
            'customer_email': 'maintenance@technoservices.fr',
            'description': 'Installation d\'un nouveau compresseur d\'air dans l\'atelier de production.',
            'priority': 'low',
            'status': 'draft',
            'estimated_duration': 240,
            'estimated_cost': 1200.00,
            'scheduled_date': datetime.now() + timedelta(days=7),
            'notes': 'Prévoir une équipe de 2 techniciens pour la manutention'
        },
        {
            'claim_number': 'WO-2025-004',
            'customer_name': 'Restaurant Le Gourmet',
            'customer_address': '321 Place du Marché\n13000 Marseille',
            'customer_phone': '+33 4 91 12 34 56',
            'customer_email': 'legourmet@restaurant.com',
            'description': 'Dépannage de la chambre froide - température instable, alarme qui se déclenche régulièrement.',
            'priority': 'high',
            'status': 'in_progress',
            'estimated_duration': 90,
            'estimated_cost': 420.00,
            'scheduled_date': datetime.now() - timedelta(hours=2),
            'notes': 'Intervention en cours - denrées périssables à préserver'
        },
        {
            'claim_number': 'WO-2025-005',
            'customer_name': 'Centre Commercial Nova',
            'customer_address': '654 Zone Commerciale\n33000 Bordeaux',
            'customer_phone': '+33 5 56 78 90 12',
            'customer_email': 'maintenance@nova-shopping.fr',
            'description': 'Maintenance trimestrielle des escalators - graissage, vérification des sécurités et nettoyage.',
            'priority': 'medium',
            'status': 'completed',
            'estimated_duration': 300,
            'estimated_cost': 680.00,
            'actual_duration': 280,
            'actual_cost': 650.00,
            'scheduled_date': datetime.now() - timedelta(days=3),
            'completion_date': datetime.now() - timedelta(days=2),
            'notes': 'Maintenance effectuée selon planning - prochaine intervention dans 3 mois'
        }
    ]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Récupérer un utilisateur admin pour créer les travaux
            cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            admin_user = cur.fetchone()
            if not admin_user:
                print("❌ Aucun utilisateur admin trouvé")
                return
            
            created_by_user_id = admin_user['id']
            
            # Récupérer quelques techniciens pour les assignations
            cur.execute("SELECT id FROM users WHERE role = 'technician' LIMIT 3")
            technicians = cur.fetchall()
            
            for work_order in sample_work_orders:
                # Assigner un technicien aléatoirement pour certains travaux
                assigned_technician_id = None
                if work_order['status'] in ['assigned', 'in_progress', 'completed'] and technicians:
                    assigned_technician_id = random.choice(technicians)['id']
                
                # Insérer le travail
                cur.execute("""
                    INSERT INTO work_orders 
                    (claim_number, customer_name, customer_address, customer_phone, customer_email,
                     description, priority, status, assigned_technician_id, created_by_user_id,
                     estimated_duration, estimated_cost, actual_duration, actual_cost,
                     scheduled_date, completion_date, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (work_order['claim_number'], work_order['customer_name'], 
                      work_order['customer_address'], work_order['customer_phone'],
                      work_order['customer_email'], work_order['description'],
                      work_order['priority'], work_order['status'], assigned_technician_id,
                      created_by_user_id, work_order['estimated_duration'],
                      work_order['estimated_cost'], work_order.get('actual_duration'),
                      work_order.get('actual_cost'), work_order['scheduled_date'],
                      work_order.get('completion_date'), work_order['notes']))
                
                work_order_id = cur.lastrowid
                print(f"✅ Travail créé: {work_order['claim_number']}")
                
                # Ajouter l'historique de statut
                cur.execute("""
                    INSERT INTO work_order_status_history 
                    (work_order_id, new_status, changed_by_user_id, change_reason)
                    VALUES (%s, %s, %s, %s)
                """, (work_order_id, work_order['status'], created_by_user_id, 
                      'Création du travail avec données de test'))
            
            conn.commit()
            print(f"✅ {len(sample_work_orders)} travaux demandés créés avec succès")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def insert_sample_products():
    """Insérer des produits d'exemple pour certains travaux"""
    
    sample_products = [
        # Produits pour WO-2025-001 (Maintenance climatisation)
        {
            'claim_number': 'WO-2025-001',
            'products': [
                {'name': 'Filtre à air haute efficacité', 'reference': 'FILT-AC-001', 'quantity': 2, 'unit_price': 35.50, 'notes': 'Filtre HEPA pour améliorer la qualité de l\'air'},
                {'name': 'Fluide frigorigène R32', 'reference': 'FLUID-R32-5L', 'quantity': 1, 'unit_price': 120.00, 'notes': 'Fluide écologique nouvelle génération'},
                {'name': 'Joint d\'étanchéité', 'reference': 'JOINT-CLIM-STD', 'quantity': 4, 'unit_price': 8.75, 'notes': 'Joints en caoutchouc haute résistance'}
            ]
        },
        # Produits pour WO-2025-002 (Réparation pont élévateur)
        {
            'claim_number': 'WO-2025-002',
            'products': [
                {'name': 'Vérin hydraulique', 'reference': 'VER-HYD-1500', 'quantity': 1, 'unit_price': 450.00, 'notes': 'Vérin de remplacement certifié CE'},
                {'name': 'Huile hydraulique ISO 46', 'reference': 'HUILE-ISO46-20L', 'quantity': 1, 'unit_price': 85.00, 'notes': 'Huile haute performance pour équipements lourds'},
                {'name': 'Kit de joints pour vérin', 'reference': 'KIT-JOINT-VER', 'quantity': 1, 'unit_price': 35.00, 'notes': 'Kit complet de joints d\'étanchéité'}
            ]
        },
        # Produits pour WO-2025-005 (Maintenance escalators)
        {
            'claim_number': 'WO-2025-005',
            'products': [
                {'name': 'Graisse pour mécanismes', 'reference': 'GRAI-MECA-2KG', 'quantity': 2, 'unit_price': 28.50, 'notes': 'Graisse longue durée pour escalators'},
                {'name': 'Brosse de nettoyage industrielle', 'reference': 'BROS-IND-L', 'quantity': 4, 'unit_price': 15.20, 'notes': 'Brosses spéciales pour nettoyage des marches'}
            ]
        }
    ]
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for work_order_data in sample_products:
                # Récupérer l'ID du travail
                cur.execute("SELECT id FROM work_orders WHERE claim_number = %s", 
                           (work_order_data['claim_number'],))
                work_order = cur.fetchone()
                
                if not work_order:
                    print(f"⚠️  Travail {work_order_data['claim_number']} non trouvé")
                    continue
                
                work_order_id = work_order['id']
                
                for product in work_order_data['products']:
                    total_price = product['quantity'] * product['unit_price']
                    
                    cur.execute("""
                        INSERT INTO work_order_products
                        (work_order_id, product_name, product_reference, quantity,
                         unit_price, total_price, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (work_order_id, product['name'], product['reference'],
                          product['quantity'], product['unit_price'], total_price,
                          product['notes']))
                    
                    print(f"✅ Produit ajouté: {product['name']} pour {work_order_data['claim_number']}")
            
            conn.commit()
            print("✅ Produits d'exemple ajoutés avec succès")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion des produits: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Insertion des données de test pour les travaux demandés...")
    print()
    
    # Vérifier si les tables existent
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'work_orders'")
            if not cur.fetchone():
                print("❌ Table work_orders non trouvée. Exécutez d'abord work_orders_tables.sql")
                exit(1)
    finally:
        conn.close()
    
    # Insérer les données
    insert_sample_work_orders()
    print()
    insert_sample_products()
    print()
    print("✨ Données de test insérées avec succès !")
    print("📋 Vous pouvez maintenant tester le module des travaux demandés.")
