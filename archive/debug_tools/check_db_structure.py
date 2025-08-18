#!/usr/bin/env python3
import pymysql
from config import Config

try:
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    print("=== Structure de la table users ===")
    cursor.execute('DESCRIBE users')
    for row in cursor.fetchall():
        print(f"Column: {row[0]}, Type: {row[1]}, Null: {row[2]}, Key: {row[3]}, Default: {row[4]}, Extra: {row[5]}")
    
    print("\n=== Structure de la table customers ===")
    cursor.execute('DESCRIBE customers')
    for row in cursor.fetchall():
        print(f"Column: {row[0]}, Type: {row[1]}, Null: {row[2]}, Key: {row[3]}, Default: {row[4]}, Extra: {row[5]}")
    
    conn.close()
    
except Exception as e:
    print(f"Erreur : {e}")
