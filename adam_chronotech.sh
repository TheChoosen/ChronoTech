#!/bin/bash

# ===================================
# ChronoTech - Script de démarrage complet
# ===================================

set -e  # Arrêt en cas d'erreur

# Configuration
PROJECT_NAME="ChronoTech"
PYTHON_VERSION="3.8"
VENV_NAME="venv"
DEFAULT_PORT=5011
DB_NAME="bdm"
DB_USER="gsicloud"
DB_PASSWORD="TCOChoosenOne204$"
DB_HOST="192.168.50.101"

# Délais et nombres de tentatives
PORT_KILL_ATTEMPTS=3
PORT_KILL_TIMEOUT=2
PORT_ALTERNATIVE_RANGE=20  # Chercher dans cette plage de ports alternatifs

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Fonctions utilitaires
print_header() {
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                    🚀 ChronoTech Setup                       ║${NC}"
    echo -e "${PURPLE}║           Système de gestion d'interventions avec IA        ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Kill process listening on given port (uses multiple detection methods + retry)
kill_port() {
    local port=${1:-$DEFAULT_PORT}
    local max_attempts=3
    local attempt=1
    local killed=false
    
    print_info "Tentative de libération du port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        print_info "Tentative $attempt/$max_attempts..."
        
        # Méthode 1: lsof (la plus courante)
        if command -v lsof &> /dev/null; then
            local pid
            pid=$(lsof -ti tcp:$port 2>/dev/null || true)
            if [ -n "$pid" ]; then
                local process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "Processus inconnu")
                print_warning "Port $port utilisé par PID $pid ($process_info) - tentative d'arrêt..."
                if kill -15 $pid 2>/dev/null; then
                    sleep 1
                    # Vérifier si le processus est toujours là
                    if ! lsof -ti tcp:$port 2>/dev/null | grep -q "$pid"; then
                        print_success "Processus sur le port $port arrêté proprement"
                        killed=true
                        break
                    else
                        print_warning "Échec de l'arrêt propre, tentative de kill -9..."
                        kill -9 $pid 2>/dev/null || true
                        sleep 1
                        if ! is_port_in_use $port; then
                            print_success "Processus sur le port $port arrêté avec kill -9"
                            killed=true
                            break
                        fi
                    fi
                else
                    print_warning "Impossible d'arrêter proprement le processus, tentative de kill -9..."
                    kill -9 $pid 2>/dev/null || true
                    sleep 1
                fi
            fi
        fi
        
        # Méthode 2: ss
        if ! $killed && command -v ss &> /dev/null; then
            local pids
            pids=$(ss -ltnp 2>/dev/null | awk -vP=":$port" '$4 ~ P {print $0}' | sed -n 's/.*pid=\([0-9]*\),.*/\1/p' | tr '\n' ' ')
            if [ -n "$pids" ]; then
                print_warning "Port $port utilisé par PID(s): $pids (détecté via ss) - tentative d'arrêt..."
                for pid in $pids; do
                    local process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "Processus inconnu")
                    print_info "Tentative d'arrêt du PID $pid ($process_info)..."
                    kill -15 $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
                done
                sleep 1
                if ! is_port_in_use $port; then
                    print_success "Processus sur le port $port arrêtés"
                    killed=true
                    break
                fi
            fi
        fi
        
        # Méthode 3: netstat (si disponible)
        if ! $killed && command -v netstat &> /dev/null; then
            local pids
            pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | sort -u | tr '\n' ' ')
            if [ -n "$pids" ]; then
                print_warning "Port $port utilisé par PID(s): $pids (détecté via netstat) - tentative d'arrêt..."
                for pid in $pids; do
                    [ -n "$pid" ] && kill -15 $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
                done
                sleep 1
                if ! is_port_in_use $port; then
                    print_success "Processus sur le port $port arrêtés"
                    killed=true
                    break
                fi
            fi
        fi
        
        # Vérifier si le port est maintenant libre
        if ! is_port_in_use $port; then
            print_success "Port $port libéré avec succès"
            killed=true
            break
        fi
        
        # Incrémentation et attente avant nouvelle tentative
        attempt=$((attempt+1))
        [ $attempt -le $max_attempts ] && sleep 2
    done
    
    if $killed; then
        return 0
    else
        print_warning "Impossible de libérer le port $port après $max_attempts tentatives"
        # Afficher plus d'informations de diagnostic
        print_info "Détails du processus utilisant le port $port:"
        if command -v lsof &> /dev/null; then
            lsof -i :$port 2>/dev/null || echo "  Aucune information disponible via lsof"
        elif command -v ss &> /dev/null; then
            ss -ltnp | grep ":$port " || echo "  Aucune information disponible via ss"
        elif command -v netstat &> /dev/null; then
            netstat -tlnp 2>/dev/null | grep ":$port " || echo "  Aucune information disponible via netstat"
        fi
        return 1
    fi
}

# Vérifier si un port est utilisé
is_port_in_use() {
    local port="$1"
    
    # Tester avec différentes méthodes
    if command -v lsof &> /dev/null; then
        if lsof -i ":$port" &>/dev/null; then
            return 0  # Port est utilisé
        fi
    fi
    
    if command -v ss &> /dev/null; then
        if ss -ltn | grep -q ":$port "; then
            return 0  # Port est utilisé
        fi
    fi
    
    if command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$port "; then
            return 0  # Port est utilisé
        fi
    fi
    
    # Tenter de se connecter au port pour voir s'il est ouvert
    if command -v nc &> /dev/null; then
        if timeout 1 nc -z localhost "$port" &>/dev/null; then
            return 0  # Port est utilisé
        fi
    fi
    
    return 1  # Port semble libre
}

# Trouver un port libre alternatif
find_free_port() {
    local base_port=$1
    local max_attempts=10
    local current_port=$base_port
    
    for (( i=0; i<max_attempts; i++ )); do
        if ! is_port_in_use "$current_port"; then
            echo "$current_port"
            return 0
        fi
        # Incrémenter le port et réessayer
        current_port=$((current_port + 1))
    done
    
    # Si aucun port libre n'est trouvé, retourner le port original
    echo "$base_port"
    return 1
}

# Fonction pour tester la connexion MySQL de façon sécurisée
test_mysql_connection() {
    local test_user="$1"
    local test_password="$2"
    local test_host="${3:-$DB_HOST}"
    
    # Créer un fichier de configuration temporaire
    local temp_config=$(mktemp)
    cat > "$temp_config" << EOF
[client]
user=$test_user
password=$test_password
host=$test_host
EOF
    
    # Tester la connexion
    if mysql --defaults-file="$temp_config" -e "SELECT 1;" &> /dev/null; then
        rm -f "$temp_config"
        return 0
    else
        rm -f "$temp_config"
        return 1
    fi
}

# Fonction pour exécuter une commande MySQL de façon sécurisée
execute_mysql_command() {
    local mysql_user="$1"
    local mysql_password="$2"
    local mysql_database="$3"
    local mysql_command="$4"
    
    local temp_config=$(mktemp)
    cat > "$temp_config" << EOF
[client]
user=$mysql_user
password=$mysql_password
host=$DB_HOST
EOF
    
    if [ -n "$mysql_database" ]; then
        mysql --defaults-file="$temp_config" "$mysql_database" -e "$mysql_command"
    else
        mysql --defaults-file="$temp_config" -e "$mysql_command"
    fi
    
    local result=$?
    rm -f "$temp_config"
    return $result
}

# Vérification des prérequis
check_prerequisites() {
    print_step "Vérification des prérequis système..."
    
    # Vérification Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        print_success "Python3 trouvé: $(python3 --version)"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        print_success "Python trouvé: $(python --version)"
    else
        print_error "Python n'est pas installé. Veuillez installer Python 3.8+"
        exit 1
    fi
    
    # Vérification MySQL
    if command -v mysql &> /dev/null; then
        print_success "MySQL trouvé: $(mysql --version | head -n1)"
    else
        print_warning "MySQL n'est pas trouvé. Assurez-vous qu'il est installé et accessible."
    fi
    
    # Vérification pip
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        print_success "pip3 trouvé"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
        print_success "pip trouvé"
    else
        print_error "pip n'est pas installé"
        exit 1
    fi
    
    echo ""
}

# Configuration de l'environnement virtuel
setup_virtual_environment() {
    print_step "Configuration de l'environnement virtuel Python..."
    
    if [ ! -d "$VENV_NAME" ]; then
        print_info "Création de l'environnement virtuel '$VENV_NAME'..."
        $PYTHON_CMD -m venv $VENV_NAME
        print_success "Environnement virtuel créé"
    else
        print_info "Environnement virtuel '$VENV_NAME' existe déjà"
    fi
    
    # Activation de l'environnement
    print_info "Activation de l'environnement virtuel..."
    source $VENV_NAME/bin/activate
    print_success "Environnement virtuel activé"
    
    # Mise à jour de pip
    print_info "Mise à jour de pip..."
    pip install --upgrade pip
    
    echo ""
}

# Installation des dépendances
install_dependencies() {
    print_step "Installation des dépendances Python..."
    
    if [ -f "requirements.txt" ]; then
        print_info "Installation depuis requirements.txt..."
        pip install -r requirements.txt
        print_success "Dépendances installées depuis requirements.txt"
    else
        print_info "Installation des dépendances essentielles..."
        pip install Flask==2.2.2 \
                   PyMySQL \
                   python-dotenv \
                   Werkzeug==2.2.3 \
                   PyYAML \
                   requests \
                   cryptography
        print_success "Dépendances essentielles installées"
    fi
    
    echo ""
}

# Configuration des fichiers de configuration
setup_configuration() {
    print_step "Configuration des fichiers de configuration..."
    
    # Création du fichier .env s'il n'existe pas ou s'il est incomplet
    if [ ! -f ".env" ]; then
        print_info "Création du fichier .env..."
        create_complete_env_file
        print_success "Fichier .env créé avec configuration par défaut"
    else
        print_info "Fichier .env existe déjà"
        # Vérifier si le fichier .env est complet
        if ! grep -q "FLASK_APP" .env || ! grep -q "SECRET_KEY" .env; then
            print_info "Mise à jour du fichier .env avec les paramètres manquants..."
            backup_and_update_env_file
            print_success "Fichier .env mis à jour"
        fi
    fi
    
    # Création du répertoire uploads
    mkdir -p static/uploads/interventions
    mkdir -p static/uploads/work_orders
    print_success "Répertoires uploads créés"
    
    echo ""
}

# Fonction pour créer un fichier .env complet
create_complete_env_file() {
    cat > .env << EOF
# Configuration ChronoTech
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True

# Base de données
MYSQL_HOST=$DB_HOST
MYSQL_USER=$DB_USER
MYSQL_PASSWORD=$DB_PASSWORD
MYSQL_DB=$DB_NAME
MYSQL_PORT=3306

# Sécurité
SECRET_KEY=$(openssl rand -hex 32)

# Serveur
PORT=$DEFAULT_PORT
HOST=0.0.0.0

# IA et APIs (à configurer selon vos besoins)
OPENAI_API_KEY=""
DEEPL_API_KEY=""
WHISPER_API_ENDPOINT=""

# Upload
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216

# Langues supportées
SUPPORTED_LANGUAGES=fr,en,es
DEFAULT_LANGUAGE=fr
EOF
}

# Fonction pour sauvegarder et mettre à jour le fichier .env existant
backup_and_update_env_file() {
    # Sauvegarder le fichier existant
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Ajouter les paramètres manquants s'ils n'existent pas
    if ! grep -q "FLASK_APP" .env; then
        echo "FLASK_APP=app.py" >> .env
    fi
    
    if ! grep -q "FLASK_ENV" .env; then
        echo "FLASK_ENV=development" >> .env
    fi
    
    if ! grep -q "FLASK_DEBUG" .env; then
        echo "FLASK_DEBUG=True" >> .env
    fi
    
    if ! grep -q "SECRET_KEY" .env; then
        echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
    fi
    
    if ! grep -q "PORT" .env; then
        echo "PORT=$DEFAULT_PORT" >> .env
    fi
    
    if ! grep -q "HOST" .env; then
        echo "HOST=0.0.0.0" >> .env
    fi
    
    if ! grep -q "UPLOAD_FOLDER" .env; then
        echo "UPLOAD_FOLDER=static/uploads" >> .env
    fi
    
    if ! grep -q "MAX_CONTENT_LENGTH" .env; then
        echo "MAX_CONTENT_LENGTH=16777216" >> .env
    fi
}

# Configuration de la base de données
setup_database() {
    print_step "Configuration de la base de données..."
    
    # Test de plusieurs configurations MySQL courantes
    declare -a mysql_configs=(
        "$DB_USER:$DB_PASSWORD"
        "root:"
        "root:root" 
        "root:password"
        "chronotech:chronotech"
        "$DB_USER:"
    )
    
    MYSQL_CONNECTED=false
    WORKING_USER=""
    WORKING_PASSWORD=""
    
    print_info "Test des configurations MySQL disponibles..."
    
    for config in "${mysql_configs[@]}"; do
        IFS=':' read -r test_user test_pass <<< "$config"
        print_info "Test de connexion avec l'utilisateur: $test_user sur $DB_HOST"
        
        if test_mysql_connection "$test_user" "$test_pass" "$DB_HOST"; then
            print_success "Connexion réussie avec l'utilisateur: $test_user sur $DB_HOST"
            MYSQL_CONNECTED=true
            WORKING_USER="$test_user"
            WORKING_PASSWORD="$test_pass"
            break
        fi
    done
    
    if [ "$MYSQL_CONNECTED" = false ]; then
        print_error "Aucune configuration MySQL fonctionnelle trouvée"
        print_info "Configurations testées:"
        for config in "${mysql_configs[@]}"; do
            IFS=':' read -r test_user test_pass <<< "$config"
            echo "  - Utilisateur: $test_user sur $DB_HOST"
        done
        echo ""
        print_info "Solutions possibles:"
        echo "  1. Vérifiez que MySQL est accessible sur $DB_HOST:3306"
        echo "  2. Vérifiez les credentials MySQL"
        echo "  3. Testez manuellement: mysql -h$DB_HOST -u$DB_USER -p"
        echo "  4. Vérifiez les règles de firewall"
        echo "  5. Vérifiez que MySQL accepte les connexions distantes"
        echo "  6. Modifier les paramètres DB_HOST, DB_USER et DB_PASSWORD en haut du script"
        exit 1
    fi
    
    # Utiliser la configuration qui fonctionne
    DB_USER="$WORKING_USER"
    DB_PASSWORD="$WORKING_PASSWORD"
    
    print_success "Utilisation de la configuration MySQL: $DB_USER@$DB_HOST"
    
    # Vérification de l'accès au schéma bdm
    print_info "Vérification de l'accès au schéma '$DB_NAME'..."
    if execute_mysql_command "$DB_USER" "$DB_PASSWORD" "" "USE $DB_NAME;"; then
        print_success "Accès au schéma '$DB_NAME' confirmé"
    else
        print_error "Impossible d'accéder au schéma '$DB_NAME'"
        exit 1
    fi

    # Création de la table users pour les tests
    print_info "Vérification/création de la table users pour les tests..."
    
    MYSQL_CONFIG_FILE=$(mktemp)
    cat > "$MYSQL_CONFIG_FILE" << EOF
[client]
user=$DB_USER
password=$DB_PASSWORD
host=$DB_HOST
EOF

    # Créer seulement la table users pour commencer
    mysql --defaults-file="$MYSQL_CONFIG_FILE" $DB_NAME << 'EOSQL'
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'manager', 'supervisor', 'technician') NOT NULL DEFAULT 'technician',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
EOSQL
    
    if [ $? -eq 0 ]; then
        print_success "Table 'users' prête pour les tests"
    else
        print_warning "Erreur lors de la vérification de la table users"
    fi
    
    # Nettoyage du fichier de configuration temporaire
    rm -f "$MYSQL_CONFIG_FILE"
    
    echo ""
}

# Ajout de données de test
setup_test_data() {
    print_step "Configuration des données de test..."
    
    # Création d'un fichier de configuration MySQL temporaire
    MYSQL_CONFIG_FILE=$(mktemp)
    cat > "$MYSQL_CONFIG_FILE" << EOF
[client]
user=$DB_USER
password=$DB_PASSWORD
host=$DB_HOST
EOF
    
    print_info "Création des utilisateurs de test..."
    mysql --defaults-file="$MYSQL_CONFIG_FILE" $DB_NAME << 'EOSQL'
-- Insertion des utilisateurs de test
INSERT IGNORE INTO users (id, name, email, password, role) VALUES
(1, 'Admin System', 'admin@chronotech.fr', 'hashed_password_admin', 'admin'),
(2, 'Marie Technicienne', 'marie@chronotech.fr', 'hashed_password_marie', 'technician'),
(3, 'Luc Superviseur', 'luc@chronotech.fr', 'hashed_password_luc', 'supervisor'),
(4, 'Sophie Manager', 'sophie@chronotech.fr', 'hashed_password_sophie', 'manager');

-- Insertion des clients de test
INSERT IGNORE INTO customers (id, name, phone, email, address) VALUES
(1, 'Entreprise ABC', '0123456789', 'contact@abc.fr', '123 Rue de la Paix, 75001 Paris'),
(2, 'Société XYZ', '0987654321', 'info@xyz.fr', '456 Avenue des Champs, 69002 Lyon'),
(3, 'SARL Tech Plus', '0555123456', 'support@techplus.fr', '789 Boulevard Tech, 13001 Marseille');

-- Insertion de bons de travail d'exemple
INSERT IGNORE INTO work_orders (id, claim_number, customer_name, customer_address, customer_phone, description, priority, status, assigned_technician_id, created_by_user_id, estimated_duration, scheduled_date) VALUES
(1, 'WO-2025-001', 'Entreprise ABC', '123 Rue de la Paix, 75001 Paris', '0123456789', 'Maintenance préventive système climatisation - Vérification et nettoyage complet', 'medium', 'assigned', 2, 1, 180, '2025-08-15 09:00:00'),
(2, 'WO-2025-002', 'Société XYZ', '456 Avenue des Champs, 69002 Lyon', '0987654321', 'Réparation urgente - Panne électrique système principal', 'urgent', 'in_progress', 2, 3, 120, '2025-08-12 14:00:00'),
(3, 'WO-2025-003', 'SARL Tech Plus', '789 Boulevard Tech, 13001 Marseille', '0555123456', 'Installation nouveau matériel - Configuration réseau', 'high', 'pending', NULL, 3, 240, '2025-08-16 08:30:00');
EOSQL
    
    # Nettoyage du fichier de configuration temporaire
    rm -f "$MYSQL_CONFIG_FILE"
    
    print_success "Données de test ajoutées"
    echo ""
}

# Vérification de l'application
verify_application() {
    print_step "Vérification de l'application..."
    
    # Vérification de la structure des fichiers
    required_files=("app.py" "routes/" "templates/" "static/")
    missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -e "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_warning "Fichiers/dossiers manquants détectés:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        print_info "L'application peut ne pas fonctionner correctement"
    else
        print_success "Structure de l'application complète"
    fi
    
    echo ""
}

# Test de l'application
test_application() {
    print_step "Test de l'application ChronoTech..."
    
    # Activation de l'environnement virtuel
    source $VENV_NAME/bin/activate
    
    # Test de syntaxe Python
    print_info "Vérification de la syntaxe de app.py..."
    if python -m py_compile app.py; then
        print_success "Syntaxe Python valide"
    else
        print_error "Erreur de syntaxe dans app.py"
        return 1
    fi
    
    # Test de l'import des modules principaux
    print_info "Test des imports Python..."
    if python -c "import app; print('✓ app.py importé avec succès')" 2>/dev/null; then
        print_success "Imports des modules principaux réussis"
    else
        print_warning "Problème avec l'import des modules - vérifiez les dépendances"
    fi
    
    # Test de connexion à la base de données
    print_info "Test de connexion à la base de données..."
    python -c "
import sys
sys.path.append('.')
try:
    from database import DatabaseManager
    db = DatabaseManager()
    db.connect()
    print('✓ Connexion à la base de données réussie')
    db.close()
except Exception as e:
    print(f'⚠ Problème de connexion DB: {e}')
    sys.exit(1)
" && print_success "Base de données accessible" || print_warning "Problème de connexion à la base de données"
    
    echo ""
}

# Démarrage de l'application
start_application() {
    print_step "Démarrage de l'application ChronoTech..."
    
    # Activation de l'environnement virtuel
    source $VENV_NAME/bin/activate
    
    # Variables d'environnement
    export FLASK_APP=app.py
    export FLASK_ENV=development
    export FLASK_DEBUG=True
    
    # Gestion du port d'écoute
    local RUNNING_PORT=$DEFAULT_PORT
    
    # Vérifier si le port est libre, sinon tenter de le libérer
    if is_port_in_use "$DEFAULT_PORT"; then
        print_warning "Port $DEFAULT_PORT est déjà en utilisation"
        
        # Tenter de libérer le port
        if ! kill_port "$DEFAULT_PORT"; then
            print_warning "Impossible de libérer le port $DEFAULT_PORT"
            
            # Chercher un port alternatif
            local alt_port=$(find_free_port $((DEFAULT_PORT + 1)))
            if [ "$alt_port" != "$DEFAULT_PORT" ] && [ -n "$alt_port" ]; then
                print_info "Port alternatif trouvé: $alt_port"
                RUNNING_PORT=$alt_port
                # Mettre à jour les variables d'environnement
                export FLASK_RUN_PORT=$RUNNING_PORT
                # Modifier le fichier .env pour la prochaine exécution
                if [ -f ".env" ]; then
                    sed -i "s/^PORT=.*/PORT=$RUNNING_PORT/" .env || true
                fi
            else
                print_error "Aucun port alternatif trouvé dans la plage acceptable"
                print_info "Solutions possibles:"
                echo "  1. Redémarrez le serveur après avoir arrêté les applications utilisant le port $DEFAULT_PORT"
                echo "  2. Spécifiez un autre port manuellement avec --port XXXX"
                echo "  3. Trouvez et arrêtez le processus utilisant le port $DEFAULT_PORT"
                print_info "Tentative de démarrage avec le port par défaut, mais cela peut échouer..."
            fi
        else
            print_success "Port $DEFAULT_PORT libéré avec succès"
            # Donner le temps au système d'exploitation de libérer complètement le port
            sleep 2
        fi
    else
        print_info "Port $DEFAULT_PORT est disponible"
    fi
    
    print_success "Application ChronoTech prête à démarrer!"
    print_info "URL locale: http://localhost:$RUNNING_PORT"
    print_info "URL réseau: http://0.0.0.0:$RUNNING_PORT"
    echo ""
    echo -e "${YELLOW}===========================================${NC}"
    echo -e "${YELLOW}  🚀 ChronoTech est maintenant en cours d'exécution${NC}"
    echo -e "${YELLOW}  📱 Interface mobile optimisée disponible${NC}"
    echo -e "${YELLOW}  🤖 Fonctionnalités IA intégrées${NC}"
    echo -e "${YELLOW}  ⚡ Port: $RUNNING_PORT${NC}"
    echo -e "${YELLOW}===========================================${NC}"
    echo ""
    echo -e "${CYAN}Appuyez sur Ctrl+C pour arrêter le serveur${NC}"
    
    # Démarrage du serveur Flask avec gestion d'erreur
    {
        python -c "
import sys
from app import app
import os
import logging
import signal
import threading
import time
from datetime import datetime
import json
from flask import jsonify, request

# Configurer le port et l'hôte
port = int(os.environ.get('FLASK_RUN_PORT', $RUNNING_PORT))
host = '0.0.0.0'

# Statistiques de l'application
app_stats = {
    'start_time': datetime.now(),
    'request_count': 0,
    'error_count': 0,
    'last_error': None
}

# Compteur de requêtes et journal d'erreurs
@app.before_request
def before_request():
    app_stats['request_count'] += 1
    
@app.errorhandler(Exception)
def handle_exception(e):
    app_stats['error_count'] += 1
    app_stats['last_error'] = {
        'time': datetime.now().isoformat(),
        'path': request.path,
        'error': str(e)
    }
    return jsonify({'error': str(e)}), 500

# Endpoint /health pour le monitoring
@app.route('/health')
def health_check():
    uptime = datetime.now() - app_stats['start_time']
    return jsonify({
        'status': 'ok',
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'uptime_seconds': uptime.total_seconds(),
        'requests': app_stats['request_count'],
        'errors': app_stats['error_count'],
        'started_at': app_stats['start_time'].isoformat(),
        'checked_at': datetime.now().isoformat(),
        'env': os.environ.get('FLASK_ENV', 'development')
    })

# Gestionnaire de signal pour arrêt propre
def signal_handler(sig, frame):
    print('Signal reçu, arrêt propre en cours...')
    # Autres opérations de nettoyage si nécessaire
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Journalisation détaillée pour le démarrage
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

try:
    logging.info(f'Démarrage de ChronoTech sur {host}:{port} (debug: {os.environ.get(\"FLASK_DEBUG\", True)})')
    app.run(host=host, port=port, debug=True, use_reloader=False)
except OSError as e:
    if 'Address already in use' in str(e):
        logging.error(f'ERREUR: Port {port} déjà utilisé. Utilisez un autre port ou arrêtez le processus qui l\\'utilise.')
        sys.exit(1)
    else:
        logging.error(f'ERREUR: {e}')
        sys.exit(2)
except Exception as e:
    logging.error(f'ERREUR inattendue: {e}')
    sys.exit(3)
"
    } || {
        code=$?
        if [ $code -eq 1 ]; then
            print_error "Échec du démarrage de l'application ChronoTech (erreur port occupé)"
            if lsof -i ":$RUNNING_PORT" &>/dev/null; then
                print_info "Processus utilisant le port $RUNNING_PORT:"
                lsof -i ":$RUNNING_PORT" | tail -n +2
            fi
            print_info "Essayez avec un port différent: ./start_chronotech.sh --port $((RUNNING_PORT + 1))"
        elif [ $code -eq 2 ]; then
            print_error "Échec du démarrage de l'application ChronoTech (erreur OS)"
            print_info "Vérifiez les permissions et la configuration système"
        elif [ $code -eq 3 ]; then
            print_error "Échec du démarrage de l'application ChronoTech (erreur application)"
            print_info "Consultez les logs pour plus de détails"
        else
            print_error "Échec du démarrage de l'application ChronoTech (code d'erreur: $code)"
        fi
        return 1
    }
    
    # Stocker le PID du processus Flask
    FLASK_PID=$!
    
    # Option pour activer le monitoring (désactivé par défaut)
    if [ "${ENABLE_MONITORING:-false}" = "true" ]; then
        monitor_application $FLASK_PID $RUNNING_PORT &
    fi
}

# Fonction d'aide
show_help() {
    echo -e "${BLUE}Usage: $0 [OPTIONS]${NC}"
    echo ""
    echo "Options:"
    echo "  --help, -h          Afficher cette aide"
    echo "  --setup-only        Effectuer seulement la configuration sans démarrer"
    echo "  --skip-db           Ignorer la configuration de la base de données"
    echo "  --skip-test-data    Ignorer l'insertion des données de test"
    echo "  --port PORT         Spécifier un port différent (défaut: 5010)"
    echo "  --db-user USER      Spécifier l'utilisateur MySQL (défaut: root)"
    echo "  --db-password PASS  Spécifier le mot de passe MySQL"
    echo ""
    echo "Exemples:"
    echo "  $0                           # Configuration complète et démarrage"
    echo "  $0 --setup-only              # Configuration uniquement"
    echo "  $0 --port 8080               # Démarrage sur le port 8080"
    echo "  $0 --db-user chronotech      # Utiliser un utilisateur MySQL différent"
    echo ""
}

# Recherche et arrête tous les processus Python associés au projet
kill_python_processes() {
    local py_search_pattern="$1"  # Motif pour identifier les processus (ex: "app.py")
    local killed=0
    
    print_info "Recherche des processus Python liés à ChronoTech..."
    
    # Trouver les processus Python exécutant app.py
    local python_pids
    
    if command -v pgrep &> /dev/null; then
        python_pids=$(pgrep -f "python.*$py_search_pattern" | tr '\n' ' ')
    else
        python_pids=$(ps aux | grep "python.*$py_search_pattern" | grep -v grep | awk '{print $2}' | tr '\n' ' ')
    fi
    
    if [ -z "$python_pids" ]; then
        print_info "Aucun processus Python associé trouvé"
        return 0
    fi
    
    print_warning "Processus Python trouvés: $python_pids"
    
    # Arrêter les processus trouvés
    for pid in $python_pids; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            local process_info=$(ps -p "$pid" -o comm= 2>/dev/null || echo "Python")
            print_info "Arrêt du processus $pid ($process_info)..."
            
            # Tentative d'arrêt propre
            if kill -15 "$pid" 2>/dev/null; then
                sleep 1
                if ! kill -0 "$pid" 2>/dev/null; then
                    print_success "Processus $pid arrêté proprement"
                    killed=$((killed + 1))
                else
                    print_warning "Le processus $pid ne répond pas, envoi de SIGKILL..."
                    kill -9 "$pid" 2>/dev/null
                    killed=$((killed + 1))
                fi
            else
                print_warning "Impossible d'arrêter proprement le processus $pid, envoi de SIGKILL..."
                kill -9 "$pid" 2>/dev/null || true
                killed=$((killed + 1))
            fi
        fi
    done
    
    if [ $killed -gt 0 ]; then
        print_success "$killed processus Python arrêtés"
        return 0
    else
        print_warning "Impossible d'arrêter les processus Python"
        return 1
    fi
}

# Fonction de nettoyage en cas d'interruption
cleanup() {
    echo ""
    print_info "Arrêt de ChronoTech..."
    
    # Arrêter les processus Python associés
    kill_python_processes "app.py"
    
    # Libérer le port
    kill_port "$DEFAULT_PORT" >/dev/null 2>&1 || true
    
    # Désactivation de l'environnement virtuel si activé
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        deactivate
    fi
    
    print_success "ChronoTech arrêté proprement"
    exit 0
}

# Vérifie l'état de l'application et redémarre si nécessaire
monitor_application() {
    local app_pid=$1
    local port=$2
    local monitoring_interval=30  # Vérifier toutes les 30 secondes
    local max_restarts=3
    local restart_count=0
    
    print_info "Démarrage de la surveillance de l'application (PID: $app_pid, Port: $port)"
    
    while true; do
        sleep $monitoring_interval
        
        # Vérifier si le processus est toujours en cours d'exécution
        if ! kill -0 "$app_pid" 2>/dev/null; then
            print_warning "Application arrêtée de manière inattendue (PID: $app_pid)"
            
            if [ $restart_count -lt $max_restarts ]; then
                restart_count=$((restart_count + 1))
                print_info "Tentative de redémarrage ($restart_count/$max_restarts)..."
                
                # Libérer le port si nécessaire
                kill_port "$port" >/dev/null 2>&1
                
                # Redémarrage de l'application
                start_application
                return $?
            else
                print_error "Nombre maximal de redémarrages atteint ($max_restarts)"
                return 1
            fi
        fi
        
        # Vérifier que l'application répond toujours sur le port
        if ! curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
            print_warning "L'application ne répond plus sur le port $port"
            
            if [ $restart_count -lt $max_restarts ]; then
                restart_count=$((restart_count + 1))
                print_info "Tentative de redémarrage ($restart_count/$max_restarts)..."
                
                # Arrêter le processus actuel
                kill -15 "$app_pid" 2>/dev/null || kill -9 "$app_pid" 2>/dev/null
                
                # Libérer le port
                kill_port "$port" >/dev/null 2>&1
                
                # Redémarrage de l'application
                start_application
                return $?
            else
                print_error "Nombre maximal de redémarrages atteint ($max_restarts)"
                return 1
            fi
        fi
    done
}

# Piégeage des signaux d'interruption
trap cleanup SIGINT SIGTERM

# Traitement des arguments de ligne de commande
SETUP_ONLY=false
SKIP_DB=false
SKIP_TEST_DATA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --setup-only)
            SETUP_ONLY=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-test-data)
            SKIP_TEST_DATA=true
            shift
            ;;
        --port)
            DEFAULT_PORT="$2"
            shift 2
            ;;
        --db-user)
            DB_USER="$2"
            shift 2
            ;;
        --db-password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        *)
            print_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Exécution principale
main() {
    print_header
    
    check_prerequisites
    setup_virtual_environment
    install_dependencies
    setup_configuration
    
    if [ "$SKIP_DB" = false ]; then
        setup_database
        if [ "$SKIP_TEST_DATA" = false ]; then
            setup_test_data
        fi
    fi
    
    verify_application
    test_application
    
    if [ "$SETUP_ONLY" = false ]; then
        start_application
    else
        print_success "Configuration terminée! Utilisez 'python app.py' pour démarrer l'application."
    fi
}

# Point d'entrée
main
