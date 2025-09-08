#!/usr/bin/env python3
"""
Script d'application de la migration département véhicules
Ajoute la colonne department à la table vehicles
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_connection
from core.logging_config import log_info, log_error
import traceback

def apply_vehicle_department_migration():
    """Applique la migration pour ajouter la colonne département aux véhicules"""
    
    print("🔧 Application de la migration département véhicules...")
    
    try:
        conn = get_db_connection()
        if not conn:
            log_error("❌ Impossible de se connecter à la base de données")
            return False
        
        cursor = conn.cursor()
        
        # Lire le fichier de migration
        migration_file = os.path.join(os.path.dirname(__file__), 'add_vehicle_department.sql')
        
        if not os.path.exists(migration_file):
            log_error(f"❌ Fichier de migration non trouvé: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Diviser le contenu en statements individuels
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print(f"📋 Exécution de {len(statements)} statements SQL...")
        
        for i, statement in enumerate(statements, 1):
            if statement.startswith('--') or not statement:
                continue
                
            try:
                print(f"   {i}. Exécution...")
                cursor.execute(statement)
                conn.commit()
                print(f"   ✅ Statement {i} exécuté avec succès")
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ℹ️ Statement {i}: Élément déjà existant (ignoré)")
                else:
                    log_error(f"❌ Erreur statement {i}: {e}")
                    print(f"   Statement: {statement[:100]}...")
        
        # Vérifier que la colonne a été ajoutée
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'vehicles' 
            AND column_name = 'department'
        """)
        
        col_exists = cursor.fetchone()[0]
        
        if col_exists:
            print("✅ Colonne 'department' ajoutée avec succès à la table vehicles")
            
            # Vérifier la table departments
            cursor.execute("SELECT COUNT(*) FROM departments")
            dept_count = cursor.fetchone()[0]
            print(f"✅ Table departments créée avec {dept_count} départements par défaut")
            
            log_info("Migration département véhicules appliquée avec succès")
            
        else:
            print("❌ La colonne 'department' n'a pas pu être ajoutée")
            return False
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        log_error(f"❌ Erreur lors de l'application de la migration: {e}")
        log_error(f"Traceback: {traceback.format_exc()}")
        return False

def verify_migration():
    """Vérifie que la migration a été appliquée correctement"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier la structure de la table vehicles
        cursor.execute("DESCRIBE vehicles")
        columns = cursor.fetchall()
        
        print("\n📋 Structure actuelle de la table vehicles:")
        for col in columns:
            print(f"   - {col['Field']}: {col['Type']} {col['Null']} {col['Key']} {col['Default']}")
        
        # Vérifier les départements disponibles
        cursor.execute("SELECT id, name, description, color FROM departments ORDER BY name")
        departments = cursor.fetchall()
        
        print(f"\n🏢 Départements disponibles ({len(departments)}):")
        for dept in departments:
            print(f"   - {dept['name']}: {dept['description']} (couleur: {dept['color']})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        log_error(f"❌ Erreur lors de la vérification: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage de la migration département véhicules...")
    
    if apply_vehicle_department_migration():
        print("\n🎉 Migration terminée avec succès!")
        verify_migration()
    else:
        print("\n💥 Échec de la migration")
        sys.exit(1)
