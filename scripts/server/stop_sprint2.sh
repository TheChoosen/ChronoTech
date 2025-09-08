#!/bin/bash

# Script d'arrêt Sprint 2
echo "🛑 Arrêt Sprint 2 - ChronoTech"

if [ -f ".sprint2_pid" ]; then
    PID=$(cat .sprint2_pid)
    if ps -p $PID > /dev/null; then
        echo "Arrêt de l'application (PID: $PID)..."
        kill $PID
        echo "✅ Application arrêtée"
    else
        echo "⚠️  L'application n'est plus en cours d'exécution"
    fi
    rm .sprint2_pid
else
    echo "⚠️  Fichier PID non trouvé"
    echo "Recherche des processus Python..."
    pkill -f "python.*app.py"
fi

echo "🏁 Sprint 2 arrêté"
