#!/usr/bin/env python3
import pymysql

try:
    # Connexion à la base de données
    connection = pymysql.connect(
        host='192.168.50.101',
        user='gsicloud',
        password='TCOChoosenOne204$',
        database='bdm',
        charset='utf8mb4'
    )
    
    cursor = connection.cursor()
    
    # Vérifier la structure de la table work_orders
    print("📋 Structure de la table work_orders:")
    cursor.execute("DESCRIBE work_orders")
    columns = cursor.fetchall()
    
    for column in columns:
        print(f"  {column[0]} - {column[1]}")
    
    # Voir si customer_name existe déjà
    customer_name_exists = any(col[0] == 'customer_name' for col in columns)
    print(f"\n❓ Colonne 'customer_name' existe: {customer_name_exists}")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"❌ Erreur: {e}")
