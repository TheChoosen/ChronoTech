#!/bin/bash
# Script de réorganisation du projet ChronoTech

echo "🚀 DÉBUT DE LA RÉORGANISATION DU PROJET CHRONOTECH"
echo "================================================="

# Création de la structure de dossiers
mkdir -p tests/{api,validation,chat,customers,crud,dashboard,database,ui,time_tracking,vehicles,kanban,pagination}
mkdir -p scripts/{fixes,server,install,test}
mkdir -p migrations/{sql}
mkdir -p services/{websocket,test}
mkdir -p docs/reports/{fixes,sprints,features,security,audit,ui}

# 1. DÉPLACEMENT DES FICHIERS DE TEST
echo "📁 Déplacement des fichiers de test..."

# Tests API
mv test_api.py tests/api/ 2>/dev/null
mv test_api_departments.py tests/api/ 2>/dev/null
mv test_api_endpoints.py tests/api/ 2>/dev/null
mv test_api_routes.py tests/api/ 2>/dev/null

# Tests validation
mv test_canadian_postal_codes.py tests/validation/ 2>/dev/null

# Tests chat
mv test_chat_*.py tests/chat/ 2>/dev/null

# Tests customers
mv test_customer_*.py tests/customers/ 2>/dev/null

# Tests CRUD
mv test_crud_complete.py tests/crud/ 2>/dev/null

# Tests dashboard
mv test_dashboard_*.py tests/dashboard/ 2>/dev/null

# Tests database
mv test_db_direct.py tests/database/ 2>/dev/null
mv test_data_connectivity.py tests/database/ 2>/dev/null

# Tests UI
mv test_dragdrop_*.py tests/ui/ 2>/dev/null

# Tests time tracking
mv test_time_*.py tests/time_tracking/ 2>/dev/null

# Tests vehicles
mv test_vehicle_*.py tests/vehicles/ 2>/dev/null

# Tests kanban
mv test_kanban_*.py tests/kanban/ 2>/dev/null

# Tests pagination
mv test_pagination_*.py tests/pagination/ 2>/dev/null

# 2. SCRIPTS DE CORRECTION
echo "🔧 Déplacement des scripts de correction..."
mv fix_*.py scripts/fixes/ 2>/dev/null
mv find_brace.py scripts/fixes/ 2>/dev/null
mv drive_permission_fixer.py scripts/fixes/ 2>/dev/null

# 3. SCRIPTS DE MIGRATION
echo "📦 Déplacement des scripts de migration..."
mv apply_department_migration*.py migrations/ 2>/dev/null
mv init_customer360_tables.py migrations/ 2>/dev/null
mv *.sql migrations/sql/ 2>/dev/null

# 4. SERVICES
echo "⚙️ Déplacement des services..."
mv websocket_server.py services/websocket/ 2>/dev/null
mv chat_websocket_server.py services/websocket/ 2>/dev/null
mv minimal_kanban_server.py services/test/ 2>/dev/null
mv test_server.py services/test/ 2>/dev/null

# 5. RAPPORTS ET DOCUMENTATION
echo "📄 Déplacement des rapports..."
mv RAPPORT_*.md docs/reports/ 2>/dev/null
mv CORRECTION_*.md docs/reports/fixes/ 2>/dev/null
mv SPRINT_*.md docs/reports/sprints/ 2>/dev/null
mv TEMPS_TRACKING_FINAL_REPORT.md docs/reports/features/ 2>/dev/null
mv SUMMARY_CSRF_FIXES.md docs/reports/security/ 2>/dev/null
mv URL_ENDPOINT_FIX_REPORT.md docs/reports/fixes/ 2>/dev/null
mv MODAL_FIXES_REPORT.md docs/reports/fixes/ 2>/dev/null
mv FORM_TEMPLATE_FIX_REPORT.md docs/reports/fixes/ 2>/dev/null
mv AUDIT_*.md docs/reports/audit/ 2>/dev/null
mv INTERFACE_*.md docs/reports/ui/ 2>/dev/null
mv COMPLETION_REPORT_QUICK_ACTIONS.md docs/reports/features/ 2>/dev/null

# 6. SCRIPTS DE SERVEUR
echo "🖥️ Déplacement des scripts de serveur..."
mv start_chronotech.sh scripts/server/ 2>/dev/null
mv start_and_test_workorder.sh scripts/server/ 2>/dev/null
mv start_sprint2.sh scripts/server/ 2>/dev/null
mv start_test.py scripts/server/ 2>/dev/null
mv stop_sprint2.sh scripts/server/ 2>/dev/null
mv test_url_simple.sh scripts/server/ 2>/dev/null
mv install_pdf_dependencies.sh scripts/install/ 2>/dev/null
mv test_kanban_api.sh scripts/test/ 2>/dev/null
mv test_kanban_final.sh scripts/test/ 2>/dev/null

# 7. SUPPRESSION DES FICHIERS OBSOLÈTES
echo "🗑️ Suppression des fichiers obsolètes..."
rm -f app_backup.py 2>/dev/null
rm -f calendar_migration_simple.sql 2>/dev/null
rm -f corrections_chronochat_fixed.sql 2>/dev/null
rm -f app.log app_test.log 2>/dev/null
rm -f cookies.txt 2>/dev/null
rm -f server.log 2>/dev/null

echo "✅ RÉORGANISATION TERMINÉE"
