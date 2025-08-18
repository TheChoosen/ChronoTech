#!/bin/bash

# Variables globales
MA_VAR="VALEUR_GLOBALE"

# Fonction de test
ma_fonction() {
    echo "Dans la fonction:"
    echo "  \$1 = '$1'"
    echo "  \$2 = '$2'"
    echo "  \$3 = '$3'"
    
    local var_locale="$1"
    echo "  var_locale = '$var_locale'"
}

echo "=== DÉMONSTRATION ==="
echo "Variable globale MA_VAR = '$MA_VAR'"
echo ""

echo "Appel : ma_fonction \"premier\" \"deuxième\" \"troisième\""
ma_fonction "premier" "deuxième" "troisième"

echo ""
echo "Appel : ma_fonction \"\$MA_VAR\" \"autre\" \"valeur\""
ma_fonction "$MA_VAR" "autre" "valeur"
