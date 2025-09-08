#!/usr/bin/env python3
"""
Script de migration - Ajout colonne département pour véhicules
Date: 2025-09-04
"""

import mysql.connector
import sys

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
        # 1. Vérifier si la colonne department existe déjà
        print("🔍 Vérification existence colonne department...")
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'bdm' 
            AND TABLE_NAME = 'vehicles' 
            AND COLUMN_NAME = 'department'
        """)
        
        column_exists = cursor.fetchone()
        
        if not column_exists:
            print("🔧 Ajout colonne department...")
            cursor.execute("""
                ALTER TABLE vehicles 
                ADD COLUMN department VARCHAR(100) DEFAULT NULL 
                COMMENT 'Département ou emplacement du véhicule dans l\\'entreprise'
            """)
            print("✅ Colonne department ajoutée!")
        else:
            print("ℹ️ Colonne department existe déjà")
        
        # 2. Créer l'index (seulement s'il n'existe pas)
        print("🔧 Création index département...")
        try:
            cursor.execute("CREATE INDEX idx_vehicles_department ON vehicles(department)")
            print("✅ Index créé!")
        except mysql.connector.Error as e:
            if "Duplicate key name" in str(e):
                print("ℹ️ Index existe déjà")
            else:
                raise e
        
        # 3. Créer la table departments si elle n'existe pas
        print("🔧 Création table departments...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("✅ Table departments créée/vérifiée!")
        
        # 4. Ajouter les départements par défaut
        departments = [
            ('Maintenance', 'Véhicules d\'entretien et de maintenance'),
            ('Commercial', 'Véhicules des équipes commerciales'),
            ('Direction', 'Véhicules de direction'),
            ('Service Client', 'Véhicules du service client'),
            ('Technique', 'Véhicules techniques et d\'intervention'),
            ('Logistique', 'Véhicules de livraison et transport')
        ]
        
        print("🔧 Ajout départements par défaut...")
        for name, description in departments:
            try:
                cursor.execute("""
                    INSERT INTO departments (name, description) 
                    VALUES (%s, %s)
                """, (name, description))
            except mysql.connector.Error as e:
                if "Duplicate entry" in str(e):
                    print(f"ℹ️ Département '{name}' existe déjà")
                else:
                    raise e
        
        # 5. Mettre à jour quelques véhicules avec des exemples
        print("🔧 Mise à jour exemples véhicules...")
        cursor.execute("SELECT id FROM vehicles LIMIT 3")
        vehicle_ids = cursor.fetchall()
        
        if vehicle_ids:
            sample_departments = ['Maintenance', 'Commercial', 'Technique']
            for i, (vehicle_id,) in enumerate(vehicle_ids):
                if i < len(sample_departments):
                    cursor.execute("""
                        UPDATE vehicles 
                        SET department = %s 
                        WHERE id = %s AND department IS NULL
                    """, (sample_departments[i], vehicle_id))
        
        # Validation finale
        cursor.execute("DESCRIBE vehicles")
        columns = cursor.fetchall()
        department_found = any('department' in str(col) for col in columns)
        
        if department_found:
            cursor.execute("SELECT COUNT(*) FROM departments")
            dept_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE department IS NOT NULL")
            updated_vehicles = cursor.fetchone()[0]
            
            print("✅ Migration département réussie!")
            print(f"📊 {dept_count} départements disponibles")
            print(f"🚗 {updated_vehicles} véhicules avec département assigné")
            
            conn.commit()
            return True
        else:
            print("❌ Validation échouée")
            return False
            
    except mysql.connector.Error as e:
        print(f"❌ Erreur migration: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    success = apply_department_migration()
    if success:
        print("\n🎉 Migration terminée avec succès!")
        sys.exit(0)
    else:
        print("\n💥 Migration échouée!")
        sys.exit(1)
