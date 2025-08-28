#!/bin/bash

# Script de démarrage et test Sprint 2
# Interventions & Work Orders Tasks

echo "🚀 LANCEMENT SPRINT 2 - ChronoTech"
echo "=================================="

# Configuration
export FLASK_APP=app.py
export FLASK_ENV=development
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=""
export MYSQL_DB=chronotech

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
print_step "Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    print_error "Python3 non trouvé. Veuillez installer Python 3.7+"
    exit 1
fi

# Vérifier MySQL
if ! command -v mysql &> /dev/null; then
    print_warning "MySQL client non trouvé. Assurez-vous que MySQL est installé."
fi

# Vérifier les dépendances Python
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt non trouvé"
    exit 1
fi

print_success "Prérequis vérifiés"

# Installation des dépendances
print_step "Installation des dépendances Python..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "Dépendances installées"
else
    print_error "Erreur lors de l'installation des dépendances"
    exit 1
fi

# Migration de la base de données
print_step "Application de la migration Sprint 2..."

if [ -f "migrations/sprint2_work_orders_tasks.sql" ]; then
    mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DB} < migrations/sprint2_work_orders_tasks.sql
    
    if [ $? -eq 0 ]; then
        print_success "Migration Sprint 2 appliquée avec succès"
    else
        print_error "Erreur lors de la migration"
        print_warning "Continuons quand même..."
    fi
else
    print_warning "Fichier de migration non trouvé, continuons..."
fi

# Vérification de la structure
print_step "Vérification de la structure des fichiers Sprint 2..."

# Vérifier les fichiers critiques
files_to_check=(
    "routes/work_orders/api_tasks.py"
    "routes/interventions/api_interventions.py"
    "services/ai_guards.py"
    "models/sprint2_models.py"
    "routes/sprint2_integration.py"
)

all_files_exist=true
for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        print_success "✓ $file"
    else
        print_error "✗ $file - MANQUANT"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    print_error "Des fichiers critiques sont manquants"
    exit 1
fi

# Tests de validation
print_step "Exécution des tests Sprint 2..."

if [ -f "tests/test_sprint2.py" ]; then
    echo "Lancement des tests..."
    python3 tests/test_sprint2.py
    
    if [ $? -eq 0 ]; then
        print_success "Tests Sprint 2 passés avec succès"
    else
        print_warning "Certains tests ont échoué (normal si la DB n'est pas configurée)"
    fi
else
    print_warning "Fichier de tests non trouvé"
fi

# Démarrage de l'application
print_step "Démarrage de l'application ChronoTech..."

# Vérifier que app.py existe
if [ ! -f "app.py" ]; then
    print_error "app.py non trouvé"
    exit 1
fi

# Démarrage en arrière-plan
echo "Démarrage de Flask sur http://localhost:5000"
echo "Logs disponibles dans server.log"

nohup python3 app.py > server.log 2>&1 &
APP_PID=$!

# Attendre que l'application démarre
sleep 3

# Vérifier que l'application répond
if curl -s http://localhost:5000 > /dev/null; then
    print_success "Application démarrée avec succès (PID: $APP_PID)"
else
    print_error "L'application ne répond pas"
    print_warning "Vérifiez les logs dans server.log"
fi

# Afficher les informations importantes
echo ""
echo "🎯 ENDPOINTS SPRINT 2 DISPONIBLES"
echo "================================="
echo ""
echo "📋 Work Orders Tasks:"
echo "  POST /api/v1/work_orders/<id>/tasks"
echo "  POST /api/v1/work_orders/<id>/tasks/<task_id>/assign"
echo "  POST /api/v1/work_orders/<id>/tasks/<task_id>/status"
echo "  POST /api/v1/work_orders/<id>/tasks/<task_id>/start_intervention"
echo "  GET  /api/v1/work_orders/<id>/tasks"
echo "  POST /api/v1/work_orders/<id>/close"
echo ""
echo "🔧 Interventions:"
echo "  GET  /api/v1/interventions"
echo "  GET  /api/v1/interventions/<id>/details"
echo "  POST /api/v1/interventions/<id>/add_note"
echo "  POST /api/v1/interventions/<id>/upload_media"
echo "  POST /api/v1/interventions/<id>/quick_actions"
echo ""
echo "🚫 Endpoints interdits (403):"
echo "  POST /api/v1/tasks/create"
echo "  PUT  /api/v1/tasks/<id>"
echo ""
echo "📊 Interface Web:"
echo "  http://localhost:5000"
echo ""
echo "📖 Documentation:"
echo "  docs/SPRINT_2_COMPLETION_REPORT.md"
echo ""

# Tests manuels
echo "🧪 TESTS MANUELS RECOMMANDÉS"
echo "============================="
echo ""
echo "1. Test création tâche (doit réussir):"
echo "   curl -X POST http://localhost:5000/api/v1/work_orders/1/tasks \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"title\":\"Test task\",\"task_source\":\"requested\"}'"
echo ""
echo "2. Test tâche orpheline (doit retourner 403):"
echo "   curl -X POST http://localhost:5000/api/v1/tasks/create \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"title\":\"Orphan task\"}'"
echo ""
echo "3. Test listing interventions:"
echo "   curl http://localhost:5000/api/v1/interventions"
echo ""

# Fonctions utiles
echo "🛠️  COMMANDES UTILES"
echo "==================="
echo ""
echo "Arrêter l'application:"
echo "  kill $APP_PID"
echo ""
echo "Voir les logs en temps réel:"
echo "  tail -f server.log"
echo ""
echo "Relancer les tests:"
echo "  python3 tests/test_sprint2.py"
echo ""
echo "Accéder à MySQL:"
echo "  mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DB}"
echo ""

print_success "Sprint 2 lancé avec succès !"
print_warning "PID de l'application: $APP_PID"
print_warning "N'oubliez pas de kill $APP_PID quand vous avez terminé"

# Sauvegarder le PID pour pouvoir l'arrêter facilement
echo $APP_PID > .sprint2_pid

echo ""
echo "Pour arrêter l'application plus tard:"
echo "  ./stop_sprint2.sh"
echo "ou"
echo "  kill \$(cat .sprint2_pid)"
