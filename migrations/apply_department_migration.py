#!/usr/bin/env python3
"""
Script pour appliquer la migration département véhicules
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from datetime import datetime

def get_db_connection():
    """Connexion à la base MySQL"""
    try:
        return mysql.connector.connect(
            host='192.168.50.101',
            user='gsicloud',
            password='TCOChoosenOne204$',
            database='bdm',
            port=3306,
            autocommit=False
        )
    except mysql.connector.Error as e:
        print(f"❌ Erreur connexion DB: {e}")
        return None

def apply_department_migration():
    """Applique la migration département véhicules"""
    print("📍 Application de la migration département véhicules...")
    
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # 1. Ajouter la colonne département
        print("🔧 Ajout colonne department...")
        cursor.execute("""
            ALTER TABLE vehicles 
            ADD COLUMN IF NOT EXISTS department VARCHAR(100) DEFAULT NULL 
            COMMENT 'Département ou emplacement du véhicule dans l\\'entreprise'
        """)
        
        # 2. Créer l'index
        print("🔧 Création index département...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_department ON vehicles(department)
        """)
        
        # 3. Créer la table departments
        print("🔧 Création table departments...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                location VARCHAR(255),
                manager_name VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # 4. Insérer les départements par défaut
        print("🔧 Insertion départements par défaut...")
        departments = [
            ('Maintenance', 'Département de maintenance véhicules', 'Atelier principal'),
            ('Commercial', 'Véhicules commerciaux et livraisons', 'Zone commerciale'),
            ('Direction', 'Véhicules de direction', 'Parking direction'),
            ('Service Client', 'Véhicules service après-vente', 'Zone SAV'),
            ('Technique', 'Véhicules équipe technique', 'Hangar technique'),
            ('Logistique', 'Transport et logistique', 'Zone logistique')
        ]
        
        for name, desc, location in departments:
            cursor.execute("""
                INSERT IGNORE INTO departments (name, description, location) 
                VALUES (%s, %s, %s)
            """, (name, desc, location))
        
        # 5. Mettre à jour quelques véhicules existants
        print("🔧 Mise à jour véhicules existants...")
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        vehicle_count = cursor.fetchone()[0]
        
        if vehicle_count > 0:
            cursor.execute("""
                UPDATE vehicles 
                SET department = 'Maintenance' 
                WHERE department IS NULL AND id % 3 = 0
            """)
            
            cursor.execute("""
                UPDATE vehicles 
                SET department = 'Commercial' 
                WHERE department IS NULL AND id % 3 = 1
            """)
            
            cursor.execute("""
                UPDATE vehicles 
                SET department = 'Technique' 
                WHERE department IS NULL AND id % 3 = 2
            """)
        
        conn.commit()
        print("✅ Migration département véhicules terminée!")
        
        # Vérification
        cursor.execute("DESCRIBE vehicles")
        columns = [col[0] for col in cursor.fetchall()]
        if 'department' in columns:
            print("✅ Colonne 'department' ajoutée avec succès")
        
        cursor.execute("SELECT COUNT(*) FROM departments")
        dept_count = cursor.fetchone()[0]
        print(f"✅ {dept_count} départements créés")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur migration: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    success = apply_department_migration()
    if success:
        print("🎉 Migration réussie!")
    else:
        print("💥 Migration échouée!")
        sys.exit(1)
