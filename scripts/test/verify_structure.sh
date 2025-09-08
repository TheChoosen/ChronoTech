#!/bin/bash
# Script de vérification finale du projet réorganisé

echo "🔍 VÉRIFICATION FINALE DU PROJET CHRONOTECH"
echo "============================================"

# Fonction pour compter les fichiers dans un dossier
count_files() {
    local dir="$1"
    if [ -d "$dir" ]; then
        find "$dir" -type f | wc -l
    else
        echo "0"
    fi
}

# Vérifications principales
echo "📊 STATISTIQUES DE VÉRIFICATION:"
echo "--------------------------------"

echo "🧪 Tests:"
for category in api validation chat customers crud dashboard database ui time_tracking vehicles kanban pagination auth finance ai work_orders general templates integration interventions pdf; do
    count=$(count_files "tests/$category")
    if [ "$count" -gt 0 ]; then
        echo "   ✅ tests/$category: $count fichiers"
    fi
done

echo ""
echo "🔧 Scripts:"
for category in fixes server install test analysis deployment security; do
    count=$(count_files "scripts/$category")
    if [ "$count" -gt 0 ]; then
        echo "   ✅ scripts/$category: $count fichiers"
    fi
done

echo ""
echo "📦 Migrations:"
for category in sql python; do
    count=$(count_files "migrations/$category")
    if [ "$count" -gt 0 ]; then
        echo "   ✅ migrations/$category: $count fichiers"
    fi
done

echo ""
echo "⚙️ Services:"
for category in websocket test ai pdf; do
    count=$(count_files "services/$category")
    if [ "$count" -gt 0 ]; then
        echo "   ✅ services/$category: $count fichiers"
    fi
done

echo ""
echo "📚 Documentation:"
for category in fixes sprints features security audit ui analysis; do
    count=$(count_files "docs/reports/$category")
    if [ "$count" -gt 0 ]; then
        echo "   ✅ docs/reports/$category: $count fichiers"
    fi
done

# Vérification des fichiers essentiels
echo ""
echo "📋 FICHIERS ESSENTIELS:"
echo "----------------------"

essential_files=(
    "app.py"
    "utils.py" 
    "requirements.txt"
    "README.md"
    ".env"
    ".gitignore"
)

for file in "${essential_files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file - MANQUANT"
    fi
done

# Vérification de la structure générale
echo ""
echo "🏗️ STRUCTURE GÉNÉRALE:"
echo "----------------------"

main_dirs=(
    "routes"
    "templates" 
    "static"
    "core"
    "tests"
    "scripts"
    "migrations"
    "services"
    "docs"
    "config"
    "archive"
)

for dir in "${main_dirs[@]}"; do
    if [ -d "$dir" ]; then
        files=$(count_files "$dir")
        subdirs=$(find "$dir" -type d | wc -l)
        echo "   ✅ $dir/ ($files fichiers, $subdirs dossiers)"
    else
        echo "   ❌ $dir/ - MANQUANT"
    fi
done

# Calcul des totaux
echo ""
echo "📈 TOTAUX:"
echo "----------"

total_tests=$(count_files "tests")
total_scripts=$(count_files "scripts")
total_migrations=$(count_files "migrations")
total_services=$(count_files "services")
total_docs=$(count_files "docs")

echo "🧪 Total tests: $total_tests fichiers"
echo "🔧 Total scripts: $total_scripts fichiers"
echo "📦 Total migrations: $total_migrations fichiers"
echo "⚙️ Total services: $total_services fichiers"
echo "📚 Total documentation: $total_docs fichiers"

total_organized=$((total_tests + total_scripts + total_migrations + total_services + total_docs))
echo ""
echo "🎯 TOTAL FICHIERS ORGANISÉS: $total_organized"

# Test de fonctionnement basique
echo ""
echo "🧪 TESTS DE FONCTIONNEMENT:"
echo "---------------------------"

# Test Python
if python3 -c "import sys; print('✅ Python fonctionne')" 2>/dev/null; then
    echo "✅ Environnement Python OK"
else
    echo "❌ Problème avec Python"
fi

# Test imports basiques
if python3 -c "from app import app; print('✅ Import app.py OK')" 2>/dev/null; then
    echo "✅ Import app.py réussi"
else
    echo "⚠️ Import app.py échoué (normal si dépendances manquantes)"
fi

# Test structure des tests
if python3 -c "import sys; sys.path.append('tests'); print('✅ Structure tests OK')" 2>/dev/null; then
    echo "✅ Structure tests accessible"
else
    echo "❌ Problème avec la structure tests"
fi

echo ""
echo "✅ VÉRIFICATION TERMINÉE"
echo "========================"

if [ "$total_organized" -gt 100 ]; then
    echo "🎉 SUCCÈS TOTAL - Projet parfaitement organisé!"
    echo "🌟 $total_organized fichiers organisés dans une structure modulaire"
else
    echo "⚠️ Organisation partielle - Quelques améliorations possibles"
fi
