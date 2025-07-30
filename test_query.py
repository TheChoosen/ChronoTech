#!/usr/bin/env python3
import sys
import os
sys.path.append('/home/masterapi/ChronoTech')

from app import get_db_connection

def test_intervention_query():
    try:
        print("Tentative de connexion à la base de données...")
        conn = get_db_connection()
        print("✅ Connexion réussie!")
        
        with conn.cursor() as cur:
            # Test basique
            cur.execute("SELECT 1 as test")
            print("✅ Requête de test réussie!")
            
            # Vérifier les tables
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            print("Tables disponibles:", [table for result in tables for table in result.values()])
            
            # Vérifier s'il y a des interventions
            cur.execute("SELECT COUNT(*) as count FROM interventions")
            count_result = cur.fetchone()
            print(f"Nombre d'interventions: {count_result['count']}")
            
            if count_result['count'] > 0:
                cur.execute("""
                    SELECT i.id, i.customer_name, i.customer_address, i.status, i.technician_id,
                           i.start_time, i.end_time, u.name as technician_name 
                    FROM interventions i 
                    LEFT JOIN users u ON i.technician_id = u.id 
                    ORDER BY i.start_time DESC
                    LIMIT 1
                """)
                intervention = cur.fetchone()
                if intervention:
                    print("✅ Requête d'intervention réussie!")
                    print("Champs disponibles:", list(intervention.keys()))
                    print("Exemple d'intervention:", intervention)
                else:
                    print("⚠️ Aucune intervention trouvée")
            else:
                print("ℹ️ La table interventions est vide")
                
        conn.close()
        print("✅ Test terminé avec succès!")
        
    except Exception as e:
        print("❌ Erreur:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_intervention_query()
