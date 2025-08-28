#!/usr/bin/env bash
# Git pre-commit hook (modèle) – Vérifie les conditions de suppression des templates legacy clients.
# Copier ou symlink ce fichier vers .git/hooks/pre-commit puis chmod +x .git/hooks/pre-commit
# Variables d'env utiles:
#   LEGACY_TEMPLATES_REMOVE_AFTER=2025-10-01

PYTHON_BIN="python"
[ -x "venv/bin/python" ] && PYTHON_BIN="venv/bin/python"

# Lancer le hook de pré-suppression uniquement si une suppression des templates legacy est détectée
LEGACY_FILES=(templates/customers/finances.html templates/customers/documents.html templates/customers/analytics.html templates/customers/consents.html)
CHANGED=$(git diff --cached --name-status || true)
NEED_CHECK=0
while IFS= read -r line; do
  status=$(echo "$line" | awk '{print $1}')
  file=$(echo "$line" | awk '{print $2}')
  if [ "$status" = "D" ]; then
    for legacy in "${LEGACY_FILES[@]}"; do
      if [ "$file" = "$legacy" ]; then
        NEED_CHECK=1
      fi
    done
  fi
done <<< "$CHANGED"

if [ $NEED_CHECK -eq 1 ]; then
  echo "[pre-commit] Vérification suppression templates legacy..."
  $PYTHON_BIN scripts/pre_remove_legacy_templates.py --git-hook || {
    echo "[pre-commit] Suppression legacy refusée (voir messages ci-dessus)." >&2
    exit 1
  }
fi

exit 0
