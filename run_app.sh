#!/bin/bash
# Script de lancement de l'application Flask ChronoTech

cd "$(dirname "$0")"
echo "=== Lancement de ChronoTech (app.py) ==="

# Activer l'environnement virtuel si besoin
if [ -d "venv" ]; then
    source venv/bin/activate
fi

export FLASK_APP=app.py
export FLASK_ENV=development

python3 app.py

if [ $? -eq 0 ]; then
    echo "✅ Application ChronoTech lancée avec succès."
else
    echo "❌ Erreur lors du lancement de ChronoTech."
fi
