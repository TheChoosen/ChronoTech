#!/bin/bash
# Script de finalisation de la réorganisation - Déplacement des fichiers de test restants

echo "🔄 FINALISATION DE LA RÉORGANISATION - FICHIERS DE TEST RESTANTS"
echo "=================================================================="

# Créer le dossier migrations/sql s'il n'existe pas
mkdir -p migrations/sql

# Déplacer les fichiers SQL restants dans migrations/sql
echo "📦 Déplacement des fichiers SQL vers migrations/sql..."
mv *.sql migrations/sql/ 2>/dev/null

# Déplacer les fichiers de test restants vers des catégories appropriées
echo "📁 Déplacement des fichiers de test restants..."

# Tests spécifiques (à classer manuellement)
mv test_vehicles_harmonization.py tests/vehicles/ 2>/dev/null
mv test_notes_authentication_fix.py tests/auth/ 2>/dev/null
mv test_onclick_functions.py tests/ui/ 2>/dev/null
mv test_finance_buttons.py tests/finance/ 2>/dev/null
mv test_ia_suggestions.py tests/ai/ 2>/dev/null
mv test_work_orders_final.py tests/work_orders/ 2>/dev/null
mv test_corrections.py tests/general/ 2>/dev/null
mv test_latitude_fix.py tests/validation/ 2>/dev/null
mv test_web_access.py tests/general/ 2>/dev/null
mv test_sprint_1_validation.py tests/validation/ 2>/dev/null
mv test_corrections_finales.py tests/general/ 2>/dev/null
mv test_corrections_summary.py tests/general/ 2>/dev/null
mv test_edit_template.py tests/templates/ 2>/dev/null
mv test_final_validation.py tests/validation/ 2>/dev/null
mv test_final.py tests/general/ 2>/dev/null
mv test_icons.py tests/ui/ 2>/dev/null
mv test_integration_canada.py tests/integration/ 2>/dev/null
mv test_intervention_routes_fix.py tests/interventions/ 2>/dev/null
mv test_interventions_direct.py tests/interventions/ 2>/dev/null
mv test_interventions_ui.py tests/interventions/ 2>/dev/null
mv test_invoice_creation.py tests/finance/ 2>/dev/null
mv test_js_only.py tests/ui/ 2>/dev/null
mv test_legacy_redirects.py tests/general/ 2>/dev/null
mv test_notes_tables.py tests/database/ 2>/dev/null
mv test_pdf_generation.py tests/pdf/ 2>/dev/null
mv test_quick_actions.py tests/ui/ 2>/dev/null
mv test_simple_interface.py tests/ui/ 2>/dev/null
mv test_sprint_1_2.py tests/validation/ 2>/dev/null
mv test_sprint_3_4.py tests/validation/ 2>/dev/null
mv test_sprint3_completion.py tests/validation/ 2>/dev/null
mv test_status_change.py tests/general/ 2>/dev/null
mv test_tax_number_consistency.py tests/validation/ 2>/dev/null
mv test_vehicles_templates_final.py tests/vehicles/ 2>/dev/null
mv test_work_order_url.py tests/work_orders/ 2>/dev/null
mv test_work_orders_basic.py tests/work_orders/ 2>/dev/null

# Créer les dossiers manquants pour les tests
mkdir -p tests/{auth,finance,ai,work_orders,general,templates,integration,interventions,pdf}

# Redéplacer les fichiers dans les bons dossiers après création
mv test_notes_authentication_fix.py tests/auth/ 2>/dev/null
mv test_finance_buttons.py tests/finance/ 2>/dev/null
mv test_invoice_creation.py tests/finance/ 2>/dev/null
mv test_ia_suggestions.py tests/ai/ 2>/dev/null
mv test_work_orders_final.py tests/work_orders/ 2>/dev/null
mv test_work_order_url.py tests/work_orders/ 2>/dev/null
mv test_work_orders_basic.py tests/work_orders/ 2>/dev/null
mv test_corrections.py tests/general/ 2>/dev/null
mv test_web_access.py tests/general/ 2>/dev/null
mv test_corrections_finales.py tests/general/ 2>/dev/null
mv test_corrections_summary.py tests/general/ 2>/dev/null
mv test_final.py tests/general/ 2>/dev/null
mv test_legacy_redirects.py tests/general/ 2>/dev/null
mv test_status_change.py tests/general/ 2>/dev/null
mv test_edit_template.py tests/templates/ 2>/dev/null
mv test_integration_canada.py tests/integration/ 2>/dev/null
mv test_intervention_routes_fix.py tests/interventions/ 2>/dev/null
mv test_interventions_direct.py tests/interventions/ 2>/dev/null
mv test_interventions_ui.py tests/interventions/ 2>/dev/null
mv test_pdf_generation.py tests/pdf/ 2>/dev/null

# Déplacer les rapports Python restants
echo "📄 Déplacement des rapports Python restants..."
mv CORRECTION_LATITUDE_REPORT.py docs/reports/fixes/ 2>/dev/null
mv CORRECTION_FINALE_REPORT.py docs/reports/fixes/ 2>/dev/null
mv rapport_final_corrections.py docs/reports/ 2>/dev/null

# Créer un fichier __init__.py dans tests
touch tests/__init__.py

# Créer des fichiers README.md dans les dossiers de tests
echo "📝 Création des fichiers README.md dans les dossiers de tests..."

cat > tests/README.md << 'EOF'
# Tests ChronoTech

Ce dossier contient tous les tests automatisés du projet ChronoTech, organisés par catégorie.

## Structure

- `api/` - Tests des APIs REST
- `auth/` - Tests d'authentification
- `chat/` - Tests du système de chat
- `customers/` - Tests des fonctionnalités client
- `dashboard/` - Tests du tableau de bord
- `database/` - Tests de la base de données
- `finance/` - Tests des fonctionnalités financières
- `interventions/` - Tests des interventions
- `kanban/` - Tests du système Kanban
- `ui/` - Tests de l'interface utilisateur
- `validation/` - Tests de validation générale
- `vehicles/` - Tests des véhicules
- `work_orders/` - Tests des bons de travail

## Exécution

```bash
# Exécuter tous les tests
python -m pytest tests/

# Exécuter les tests d'une catégorie
python -m pytest tests/api/
```
EOF

echo "✅ FINALISATION TERMINÉE"
echo "📊 Nouvelle structure de tests créée avec catégories spécialisées"
