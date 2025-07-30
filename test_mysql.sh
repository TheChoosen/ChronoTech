#!/bin/bash
# Test de connexion MySQL avec PyMySQL

cd "$(dirname "$0")"
echo "=== Test de connexion MySQL avec PyMySQL ==="
python3 test_mysql.py

if [ $? -eq 0 ]; then
    echo "✅ Test terminé : Connexion MySQL réussie."
else
    echo "❌ Test terminé : Échec de la connexion MySQL."
fi
