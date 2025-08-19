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

# Kill process listening on given port (uses lsof/ss fallback)
kill_port() {
    local port=${1:-$DEFAULT_PORT}
    # Try lsof first
    if command -v lsof &> /dev/null; then
        local pid
        pid=$(lsof -ti tcp:$port || true)
        if [ -n "$pid" ]; then
            print_warning "Port $port utilisé par PID(s): $pid — fermeture en cours..."
            kill -9 $pid || true
            sleep 0.5
            print_success "Processus sur le port $port tué"
            return 0
        fi
    fi

    # Fallback to ss
    if command -v ss &> /dev/null; then
        local pids
        pids=$(ss -ltnp 2>/dev/null | awk -vP=":$port" '$4 ~ P {print $0}' | sed -n 's/.*pid=\([0-9]*\),.*/\1/p' | tr '\n' ' ')
        if [ -n "$pids" ]; then
            print_warning "Port $port utilisé par PID(s): $pids — fermeture en cours..."
            kill -9 $pids || true
            sleep 0.5
            print_success "Processus sur le port $port tué"
            return 0
        fi
    fi

    # No process found
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
        # Forcer la valeur PORT dans .env pour que ce script utilise toujours DEFAULT_PORT
        if grep -q "^PORT=" .env; then
            sed -i.bak -E "s/^PORT=.*/PORT=$DEFAULT_PORT/" .env || true
        else
            echo "PORT=$DEFAULT_PORT" >> .env
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
    
    print_success "Application ChronoTech démarrée!"
    print_info "URL locale: http://localhost:$DEFAULT_PORT"
    print_info "URL réseau: http://0.0.0.0:$DEFAULT_PORT"
    echo ""
    echo -e "${YELLOW}===========================================${NC}"
    echo -e "${YELLOW}  🚀 ChronoTech est maintenant en cours d'exécution${NC}"
    echo -e "${YELLOW}  📱 Interface mobile optimisée disponible${NC}"
    echo -e "${YELLOW}  🤖 Fonctionnalités IA intégrées${NC}"
    echo -e "${YELLOW}  ⚡ Port: $DEFAULT_PORT${NC}"
    echo -e "${YELLOW}===========================================${NC}"
    echo ""
    echo -e "${CYAN}Appuyez sur Ctrl+C pour arrêter le serveur${NC}"
    
    # Démarrage du serveur Flask
        # Try to free the configured port before starting the app (if helper exists)
        if declare -f kill_port >/dev/null 2>&1; then
            print_info "Vérification du port $DEFAULT_PORT avant démarrage..."
            # Attempt to kill any process listening on the port; don't fail the script if this fails
            kill_port "$DEFAULT_PORT" || print_warning "Impossible de libérer le port $DEFAULT_PORT automatiquement"
            # Give the OS a moment to release the socket
            sleep 1
        fi

    python app.py
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
    echo "  --port PORT         Spécifier un port différent (défaut: 5011)"
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

# Fonction de nettoyage en cas d'interruption
cleanup() {
    echo ""
    print_info "Arrêt de ChronoTech..."
    # Désactivation de l'environnement virtuel si activé
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        deactivate
    fi
    print_success "ChronoTech arrêté proprement"
    exit 0
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
