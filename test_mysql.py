import pymysql

try:
    conn = pymysql.connect(
        host='192.168.50.101',
        port=3306,
        user='gsicloud',
        password='TCOChoosenOne204$',
        db='gsi'
    )
    print("Connexion MySQL OK !")
    conn.close()
except Exception as e:
    print("Erreur de connexion MySQL :", e)
