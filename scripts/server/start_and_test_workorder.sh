#!/bin/bash

echo "🚀 Démarrage de ChronoTech pour tester work-orders/5"
echo "===================================================="

# Arrêter tous les processus Flask existants
echo "🧹 Nettoyage des processus existants..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 2

# Définir les variables d'environnement comme dans start_chronotech.sh
export MYSQL_HOST="192.168.50.101"
export MYSQL_USER="gsicloud"
export MYSQL_PASSWORD="TCOChoosenOne204$"
export MYSQL_DATABASE="bdm"
export FLASK_PORT=5011

echo "📊 Configuration:"
echo "  - Host DB: $MYSQL_HOST"
echo "  - User: $MYSQL_USER"
echo "  - Database: $MYSQL_DATABASE"
echo "  - Port Flask: $FLASK_PORT"

# Démarrer l'application Flask
echo ""
echo "🚀 Démarrage de l'application Flask..."
cd /home/amenard/Chronotech/ChronoTech

# Démarrer en arrière-plan et capturer le PID
/home/amenard/Chronotech/ChronoTech/venv/bin/python app.py &
FLASK_PID=$!

echo "📋 PID du processus Flask: $FLASK_PID"

# Attendre que le serveur démarre
echo "⏳ Attente du démarrage (10 secondes)..."
sleep 10

# Tester l'URL
echo ""
echo "🧪 Test de l'URL work-orders/5..."

# Test avec timeout court
if timeout 5 curl -s "http://192.168.50.147:5011/work-orders/5" > /tmp/work_order_test.html 2>/dev/null; then
    HTTP_SIZE=$(wc -c < /tmp/work_order_test.html)
    if [ "$HTTP_SIZE" -gt 100 ]; then
        echo "✅ SUCCESS - La page work-orders/5 fonctionne!"
        echo "   Taille du contenu: $HTTP_SIZE bytes"
        
        # Vérifier le contenu
        if grep -q -i "work.order\|bon.de.travail" /tmp/work_order_test.html 2>/dev/null; then
            echo "✅ Le contenu semble être une page de work order"
        else
            echo "⚠️ Le contenu ne contient pas les mots-clés attendus"
        fi
        
        echo ""
        echo "🌐 L'URL http://192.168.50.147:5011/work-orders/5 est maintenant accessible!"
        
    else
        echo "❌ La page retourne un contenu vide ou une erreur"
    fi
else
    echo "❌ Impossible de se connecter à l'URL"
fi

# Nettoyer
rm -f /tmp/work_order_test.html

echo ""
echo "🏁 Test terminé. Le serveur continue de fonctionner en arrière-plan (PID: $FLASK_PID)"
echo "   Pour l'arrêter: kill $FLASK_PID"
echo "   URL disponible: http://192.168.50.147:5011/work-orders/5"
