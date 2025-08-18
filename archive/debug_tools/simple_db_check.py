import pymysql

# Configuration directe
config = {
    'host': '192.168.50.101',
    'port': 3306,
    'user': 'gsicloud',
    'password': 'TCOChoosenOne204$',
    'database': 'bdm',
    'charset': 'utf8mb4'
}

try:
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    print("=== Structure de la table users ===")
    cursor.execute('DESCRIBE users')
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    print("\n=== Structure de la table customers ===")
    cursor.execute('DESCRIBE customers')
    for row in cursor.fetchall():
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    conn.close()
    
except Exception as e:
    print(f"Erreur : {e}")
