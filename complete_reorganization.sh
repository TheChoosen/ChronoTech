#!/bin/bash
# Script de réorganisation COMPLÈTE du projet ChronoTech

echo "🚀 RÉORGANISATION COMPLÈTE DU PROJET CHRONOTECH"
echo "================================================"

# Création de la structure de dossiers complète
echo "📁 Création de la structure de dossiers..."
mkdir -p tests/{api,validation,chat,customers,crud,dashboard,database,ui,time_tracking,vehicles,kanban,pagination,auth,finance,ai,work_orders,general,templates,integration,interventions,pdf}
mkdir -p scripts/{fixes,server,install,test,analysis,deployment}
mkdir -p migrations/{sql,python}
mkdir -p services/{websocket,test,ai,pdf}
mkdir -p docs/reports/{fixes,sprints,features,security,audit,ui,analysis}
mkdir -p archive/{legacy,old_reports,deprecated}

echo "📦 Déplacement des fichiers restants..."

# 1. SCRIPTS D'ANALYSE ET DEBUG - vers scripts/analysis/
echo "🔍 Scripts d'analyse..."
mv analyse_problemes_structurels.py scripts/analysis/ 2>/dev/null
mv check_table_structure.py scripts/analysis/ 2>/dev/null
mv data_visibility_fix_report.py scripts/analysis/ 2>/dev/null
mv debug_kanban_dashboard.py scripts/analysis/ 2>/dev/null
mv debug_pagination.py scripts/analysis/ 2>/dev/null
mv debug_route.py scripts/analysis/ 2>/dev/null
mv debug_routes.py scripts/analysis/ 2>/dev/null
mv diagnostic_kanban_dashboard.py scripts/analysis/ 2>/dev/null
mv intervention_resolution_report.py scripts/analysis/ 2>/dev/null
mv validate_js.py scripts/analysis/ 2>/dev/null
mv vehicles_harmonization_report.py scripts/analysis/ 2>/dev/null
mv vehicles_modal_fix_report.py scripts/analysis/ 2>/dev/null

# 2. RAPPORTS TECHNIQUES - vers docs/reports/
echo "📄 Rapports techniques..."
mv AUTO_LOGIN_IMPLEMENTATION_REPORT.md docs/reports/features/ 2>/dev/null
mv CORRECTIONS_FINAL_REPORT.md docs/reports/fixes/ 2>/dev/null
mv CSP_FULLCALENDAR_RESOLUTION_FINAL.md docs/reports/fixes/ 2>/dev/null
mv CUSTOMERS_MODULE_ENHANCEMENT_REPORT.md docs/reports/features/ 2>/dev/null
mv DASHBOARD_JAVASCRIPT_FIXES_REPORT.md docs/reports/fixes/ 2>/dev/null
mv DASHBOARD_KANBAN_RESOLUTION_COMPLETE.md docs/reports/fixes/ 2>/dev/null
mv DRAGDROP_CORRECTIONS_COMPLETES.md docs/reports/fixes/ 2>/dev/null
mv FINAL_COMPLETION_REPORT.md docs/reports/features/ 2>/dev/null
mv INTERVENTIONS_UI_RESTAURATION_COMPLETE.md docs/reports/ui/ 2>/dev/null
mv JAVASCRIPT_ERRORS_RESOLUTION_REPORT.md docs/reports/fixes/ 2>/dev/null
mv LOCALISATION_ACTIONS_RAPIDES.md docs/reports/ui/ 2>/dev/null
mv PLAN_CORRECTION_CRITIQUE.md docs/reports/analysis/ 2>/dev/null

# 3. SCRIPTS PYTHON DE RAPPORT - vers scripts/analysis/
echo "🐍 Scripts Python de rapport..."
mv DASHBOARD_CORRECTIONS_REPORT.py scripts/analysis/ 2>/dev/null

# 4. FICHIERS HTML DE TEST - vers tests/
echo "🌐 Fichiers HTML de test..."
mv interventions_direct.html tests/interventions/ 2>/dev/null

# 5. SCRIPTS DE SÉCURITÉ - vers scripts/security/
echo "🔒 Scripts de sécurité..."
mkdir -p scripts/security
mv security_test_sprint1.py scripts/security/ 2>/dev/null

# 6. SCRIPTS DE DÉPLOIEMENT - vers scripts/deployment/
echo "🚀 Scripts de déploiement..."
mv adam_chronotech.sh scripts/deployment/ 2>/dev/null

# 7. FICHIERS DE CONFIGURATION JSON
echo "⚙️ Fichiers de configuration..."
mkdir -p config
mv sprint3_validation_report.json config/ 2>/dev/null

# 8. CRÉER DES FICHIERS __init__.py
echo "📝 Création des fichiers __init__.py..."
touch tests/__init__.py
touch scripts/__init__.py
touch services/__init__.py

# 9. FICHIERS GITKEEP POUR DOSSIERS VIDES
echo "📌 Ajout de .gitkeep dans les dossiers vides..."
find tests/ scripts/ migrations/ services/ docs/ -type d -empty -exec touch {}/.gitkeep \;

# 10. NETTOYAGE FINAL
echo "🧹 Nettoyage final..."
rm -f *.log 2>/dev/null
rm -f cookies.txt 2>/dev/null
rm -f server.log 2>/dev/null
rm -f app_backup.py 2>/dev/null

echo "✅ RÉORGANISATION COMPLÈTE TERMINÉE"
