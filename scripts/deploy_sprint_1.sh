#!/bin/bash

# ========================================
# SCRIPT D'EXÉCUTION SPRINT 1
# ========================================
# Objectif: Déployer l'architecture sécurisée
# Date: 2025-08-27
# Version: 1.0
# ========================================

set -e  # Arrêter en cas d'erreur

# Configuration
DB_NAME="${MYSQL_DB:-chronotech}"
DB_USER="${MYSQL_USER:-root}"  
DB_HOST="${MYSQL_HOST:-localhost}"
BACKUP_DIR="./backups"
MIGRATION_DIR="./migrations"
TESTS_DIR="./tests"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # MySQL client
    if ! command -v mysql &> /dev/null; then
        log_error "MySQL client non trouvé. Installation requise."
        exit 1
    fi
    
    # Connexion DB
    if ! mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" -e "USE $DB_NAME;" 2>/dev/null; then
        log_error "Impossible de se connecter à la base de données $DB_NAME"
        exit 1
    fi
    
    # Fichiers migration
    if [ ! -f "$MIGRATION_DIR/sprint_1_work_order_tasks_implementation.sql" ]; then
        log_error "Fichier de migration Sprint 1 introuvable"
        exit 1
    fi
    
    log_success "Prérequis validés"
}

# Backup de sécurité
create_backup() {
    log_info "Création du backup de sécurité..."
    
    mkdir -p "$BACKUP_DIR"
    
    local backup_file="$BACKUP_DIR/pre_sprint1_$(date +%Y%m%d_%H%M%S).sql"
    
    if mysqldump -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" \
        --single-transaction --routines --triggers \
        "$DB_NAME" > "$backup_file"; then
        log_success "Backup créé: $backup_file"
        echo "$backup_file" > "$BACKUP_DIR/latest_backup.txt"
    else
        log_error "Échec création backup"
        exit 1
    fi
}

# Vérification état actuel
check_current_state() {
    log_info "Vérification de l'état actuel de la base..."
    
    # Vérifier si les tables Sprint 1 existent déjà
    local tables_exist=$(mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" -s -N -e \
        "SELECT COUNT(*) FROM information_schema.tables 
         WHERE table_schema='$DB_NAME' 
         AND table_name IN ('work_order_tasks', 'work_order_status_history');" 2>/dev/null || echo "0")
    
    if [ "$tables_exist" -gt 0 ]; then
        log_warning "Certaines tables Sprint 1 existent déjà"
        read -p "Continuer avec la migration (les tables seront mises à jour) ? [y/N]: " confirm
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            log_info "Migration annulée par l'utilisateur"
            exit 0
        fi
    fi
    
    # Vérifier les données existantes
    local wo_count=$(mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" -s -N -e \
        "SELECT COUNT(*) FROM work_orders;" 2>/dev/null || echo "0")
    
    log_info "État actuel: $wo_count bons de travail dans la base"
}

# Exécution de la migration
execute_migration() {
    log_info "Exécution de la migration Sprint 1..."
    
    local migration_file="$MIGRATION_DIR/sprint_1_work_order_tasks_implementation.sql"
    
    # Afficher un résumé de ce qui va être fait
    log_info "La migration va:"
    log_info "  • Créer work_order_tasks avec contraintes strictes"
    log_info "  • Refactorer interventions (relation 1-1 avec tasks)"
    log_info "  • Mettre à jour intervention_notes et intervention_media"
    log_info "  • Créer triggers de garde-fous"
    log_info "  • Créer vues optimisées"
    log_info "  • Ajouter données de test"
    
    read -p "Confirmer l'exécution de la migration ? [y/N]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_info "Migration annulée par l'utilisateur"
        exit 0
    fi
    
    # Exécuter la migration avec gestion d'erreur
    if mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" < "$migration_file"; then
        log_success "Migration Sprint 1 exécutée avec succès"
    else
        log_error "Échec de la migration"
        log_error "Consultez les logs MySQL pour plus de détails"
        
        # Proposer restauration
        read -p "Restaurer le backup automatiquement ? [y/N]: " restore
        if [[ $restore =~ ^[Yy]$ ]]; then
            restore_backup
        fi
        exit 1
    fi
}

# Tests de validation
run_validation_tests() {
    log_info "Exécution des tests de validation..."
    
    local test_file="$TESTS_DIR/sprint_1_validation_tests.sql"
    
    if [ ! -f "$test_file" ]; then
        log_warning "Fichier de tests non trouvé: $test_file"
        return 0
    fi
    
    # Créer un fichier temporaire pour les résultats
    local test_output="/tmp/sprint1_test_results_$(date +%s).txt"
    
    if mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" < "$test_file" > "$test_output" 2>&1; then
        log_success "Tests de validation exécutés"
        
        # Analyser les résultats
        local failed_tests=$(grep -c "FAIL" "$test_output" 2>/dev/null || echo "0")
        local total_tests=$(grep -c "test_name" "$test_output" 2>/dev/null || echo "0")
        
        if [ "$failed_tests" -eq 0 ]; then
            log_success "Tous les tests sont passés ($total_tests/$total_tests)"
        else
            log_error "$failed_tests tests ont échoué sur $total_tests"
            log_info "Consultez $test_output pour les détails"
        fi
        
        # Afficher le résumé final
        grep -A 5 "RAPPORT TESTS SPRINT 1" "$test_output" 2>/dev/null || true
        grep "validation_finale" "$test_output" 2>/dev/null || true
        
    else
        log_error "Échec des tests de validation"
    fi
}

# Vérification post-migration
verify_installation() {
    log_info "Vérification de l'installation..."
    
    # Vérifier les tables créées
    local tables_created=$(mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" -s -N -e \
        "SELECT COUNT(*) FROM information_schema.tables 
         WHERE table_schema='$DB_NAME' 
         AND table_name IN ('work_order_tasks', 'work_order_status_history');" 2>/dev/null || echo "0")
    
    if [ "$tables_created" -eq 2 ]; then
        log_success "Tables principales créées"
    else
        log_error "Tables principales manquantes"
        return 1
    fi
    
    # Vérifier les triggers
    local triggers_created=$(mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" -s -N -e \
        "SELECT COUNT(*) FROM information_schema.triggers 
         WHERE trigger_schema='$DB_NAME' 
         AND trigger_name LIKE 'tr_%';" 2>/dev/null || echo "0")
    
    if [ "$triggers_created" -gt 0 ]; then
        log_success "$triggers_created triggers créés"
    else
        log_warning "Aucun trigger détecté"
    fi
    
    # Vérifier les vues
    local views_created=$(mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" -s -N -e \
        "SELECT COUNT(*) FROM information_schema.views 
         WHERE table_schema='$DB_NAME' 
         AND table_name LIKE 'v_%';" 2>/dev/null || echo "0")
    
    if [ "$views_created" -gt 0 ]; then
        log_success "$views_created vues créées"
    else
        log_warning "Aucune vue détectée"
    fi
    
    log_success "Installation Sprint 1 vérifiée"
}

# Restauration backup
restore_backup() {
    log_info "Restauration du backup..."
    
    if [ ! -f "$BACKUP_DIR/latest_backup.txt" ]; then
        log_error "Aucun backup récent trouvé"
        return 1
    fi
    
    local backup_file=$(cat "$BACKUP_DIR/latest_backup.txt")
    
    if [ ! -f "$backup_file" ]; then
        log_error "Fichier backup introuvable: $backup_file"
        return 1
    fi
    
    log_warning "Restauration de $backup_file"
    read -p "Confirmer la restauration (PERTE DES MODIFICATIONS) ? [y/N]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_info "Restauration annulée"
        return 0
    fi
    
    if mysql -h"$DB_HOST" -u"$DB_USER" -p"$MYSQL_PASSWORD" "$DB_NAME" < "$backup_file"; then
        log_success "Backup restauré avec succès"
    else
        log_error "Échec de la restauration"
        return 1
    fi
}

# Affichage de l'aide
show_help() {
    echo "SCRIPT D'EXÉCUTION SPRINT 1 - ChronoTech"
    echo "========================================"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --check-only     Vérifier l'état sans migration"
    echo "  --backup-only    Créer uniquement le backup"  
    echo "  --migrate-only   Exécuter uniquement la migration"
    echo "  --test-only      Exécuter uniquement les tests"
    echo "  --restore        Restaurer le dernier backup"
    echo "  --help           Afficher cette aide"
    echo ""
    echo "Variables d'environnement:"
    echo "  MYSQL_HOST       Host MySQL (défaut: localhost)"
    echo "  MYSQL_USER       Utilisateur MySQL (défaut: root)"
    echo "  MYSQL_PASSWORD   Mot de passe MySQL"
    echo "  MYSQL_DB         Base de données (défaut: chronotech)"
    echo ""
    echo "Exemple:"
    echo "  MYSQL_PASSWORD=secret $0"
    echo "  $0 --check-only"
}

# ========================================
# PROGRAMME PRINCIPAL
# ========================================

main() {
    log_info "========================================="
    log_info "DÉPLOIEMENT SPRINT 1 - ChronoTech"
    log_info "Architecture Sécurisée Work Orders/Tasks"
    log_info "========================================="
    
    # Gestion des paramètres
    case "${1:-}" in
        --help)
            show_help
            exit 0
            ;;
        --check-only)
            check_prerequisites
            check_current_state
            exit 0
            ;;
        --backup-only)
            check_prerequisites
            create_backup
            exit 0
            ;;
        --migrate-only)
            check_prerequisites
            execute_migration
            verify_installation
            exit 0
            ;;
        --test-only)
            check_prerequisites
            run_validation_tests
            exit 0
            ;;
        --restore)
            check_prerequisites
            restore_backup
            exit 0
            ;;
        --*)
            log_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
    
    # Vérifier le mot de passe
    if [ -z "$MYSQL_PASSWORD" ]; then
        log_error "Variable MYSQL_PASSWORD requise"
        echo "Exemple: MYSQL_PASSWORD=secret $0"
        exit 1
    fi
    
    # Exécution complète
    log_info "Démarrage de la procédure complète..."
    
    check_prerequisites
    check_current_state
    create_backup
    execute_migration
    verify_installation
    run_validation_tests
    
    log_success "========================================="
    log_success "SPRINT 1 DÉPLOYÉ AVEC SUCCÈS"
    log_success "Architecture sécurisée opérationnelle"
    log_success "Prêt pour Sprint 2 (API sécurisées)"
    log_success "========================================="
    
    # Instructions post-déploiement
    log_info ""
    log_info "Prochaines étapes:"
    log_info "1. Vérifier les logs d'application"
    log_info "2. Tester la création de bons de travail"
    log_info "3. Valider les contraintes de sécurité"
    log_info "4. Préparer le développement Sprint 2"
    log_info ""
    log_info "En cas de problème:"
    log_info "  $0 --restore  # Restaurer le backup"
    log_info "  $0 --test-only # Re-exécuter les tests"
}

# Exécution du programme principal
main "$@"
