#!/bin/bash
# Script pour exécuter tous les tests du projet ChronoTech

echo "🧪 EXÉCUTION DE TOUS LES TESTS CHRONOTECH"
echo "=========================================="

# Vérifier si pytest est installé
if ! command -v pytest &> /dev/null; then
    echo "⚠️ pytest n'est pas installé. Installation..."
    pip install pytest
fi

# Compter le nombre total de fichiers de test
test_count=$(find tests/ -name "test_*.py" | wc -l)
echo "📊 Nombre total de fichiers de test trouvés: $test_count"

# Exécuter les tests par catégorie
categories=(
    "api"
    "auth" 
    "chat"
    "customers"
    "crud"
    "dashboard"
    "database"
    "finance"
    "interventions"
    "kanban"
    "pagination"
    "ui"
    "validation"
    "vehicles"
    "work_orders"
    "time_tracking"
)

echo ""
echo "🎯 EXÉCUTION DES TESTS PAR CATÉGORIE"
echo "------------------------------------"

for category in "${categories[@]}"; do
    if [ -d "tests/$category" ]; then
        test_files=$(find "tests/$category" -name "test_*.py" | wc -l)
        if [ $test_files -gt 0 ]; then
            echo "📁 Tests $category ($test_files fichiers)..."
            python -m pytest "tests/$category" -v --tb=short 2>/dev/null || echo "   ⚠️ Certains tests ont échoué"
        fi
    fi
done

echo ""
echo "✅ EXÉCUTION TERMINÉE"
echo "📝 Pour des résultats détaillés, exécutez:"
echo "   python -m pytest tests/ -v"
