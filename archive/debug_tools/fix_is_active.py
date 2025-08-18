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
    
    print("=== Ajout des colonnes is_active ===")
    
    # Vérifier si la colonne existe déjà dans users
    cursor.execute("SHOW COLUMNS FROM users LIKE 'is_active'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL")
        print("✅ Colonne is_active ajoutée à la table users")
    else:
        print("ℹ️  Colonne is_active existe déjà dans users")
    
    # Vérifier si la colonne existe déjà dans customers
    cursor.execute("SHOW COLUMNS FROM customers LIKE 'is_active'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE customers ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL")
        print("✅ Colonne is_active ajoutée à la table customers")
    else:
        print("ℹ️  Colonne is_active existe déjà dans customers")
    
    # Mettre à jour les enregistrements existants
    cursor.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
    cursor.execute("UPDATE customers SET is_active = TRUE WHERE is_active IS NULL")
    
    # Vérifier les résultats
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
    users_count = cursor.fetchone()[0]
    print(f"📊 Utilisateurs actifs : {users_count}")
    
    cursor.execute("SELECT COUNT(*) FROM customers WHERE is_active = TRUE")
    customers_count = cursor.fetchone()[0]
    print(f"📊 Clients actifs : {customers_count}")
    
    conn.commit()
    conn.close()
    print("✅ Modifications appliquées avec succès")
    
except Exception as e:
    print(f"❌ Erreur : {e}")
