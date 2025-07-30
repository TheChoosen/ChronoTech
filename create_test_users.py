#!/usr/bin/env python3
import pymysql
from werkzeug.security import generate_password_hash

conn = pymysql.connect(
    host='192.168.50.101',
    port=3306,
    user='gsicloud',
    password='TCOChoosenOne204$',
    db='gsi',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with conn.cursor() as cur:
        # Créer admin
        hashed_password = generate_password_hash('admin123')
        cur.execute('''
            INSERT IGNORE INTO users (name, email, password, role) 
            VALUES (%s, %s, %s, %s)
        ''', ('Admin Test', 'admin@chronotech.com', hashed_password, 'admin'))
        
        # Créer techniciens
        tech_password = generate_password_hash('tech123')
        technicians = [
            ('Jean Dupont', 'jean.dupont@chronotech.com'),
            ('Marie Martin', 'marie.martin@chronotech.com'), 
            ('Pierre Durand', 'pierre.durand@chronotech.com')
        ]
        
        for name, email in technicians:
            cur.execute('''
                INSERT IGNORE INTO users (name, email, password, role) 
                VALUES (%s, %s, %s, %s)
            ''', (name, email, tech_password, 'technician'))
        
        conn.commit()
        print('✅ Utilisateurs créés avec succès')
        
        # Vérifier
        cur.execute('SELECT name, email, role FROM users ORDER BY role, name')
        users = cur.fetchall()
        print('\n📋 Utilisateurs dans la base:')
        for user in users:
            print(f"  - {user['name']} ({user['email']}) - {user['role']}")
            
finally:
    conn.close()
