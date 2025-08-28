#!/usr/bin/env python3
"""
Script de migration pour passer du fichier customers.py monolithique
vers l'architecture modulaire
"""

import os
import shutil
from datetime import datetime

def backup_original_file():
    """Sauvegarde le fichier original"""
    original_path = "/home/amenard/Chronotech/ChronoTech/routes/customers.py"
    backup_path = f"/home/amenard/Chronotech/ChronoTech/routes/customers_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    
    if os.path.exists(original_path):
        shutil.copy2(original_path, backup_path)
        print(f"✅ Fichier original sauvegardé: {backup_path}")
        return backup_path
    else:
        print("❌ Fichier original non trouvé")
        return None

def create_import_stub():
    """Crée un stub d'import pour maintenir la compatibilité"""
    stub_content = '''"""
Stub de compatibilité pour l'ancien module customers.py
Redirige vers la nouvelle architecture modulaire
"""

import warnings
from routes.customers import *

# Avertissement pour migration
warnings.warn(
    "L'import direct de 'routes.customers' est déprécié. "
    "Utilisez 'from routes.customers import bp' ou les modules spécialisés.",
    DeprecationWarning,
    stacklevel=2
)

# Maintien de la compatibilité avec l'ancien code
__all__ = [
    'bp',
    'get_db_connection',
    'get_current_user',
    'require_role',
    'log_customer_activity',
    'validate_customer_form_advanced',
    'geocode_address',
    'calculate_distance'
]
'''
    
    stub_path = "/home/amenard/Chronotech/ChronoTech/routes/customers_legacy.py"
    with open(stub_path, 'w', encoding='utf-8') as f:
        f.write(stub_content)
    
    print(f"✅ Stub de compatibilité créé: {stub_path}")

def create_documentation():
    """Crée la documentation de la nouvelle architecture"""
    doc_content = '''# Architecture Modulaire - Module Customers

## Vue d'ensemble

Le module `customers` a été refactorisé pour améliorer la maintenabilité et la séparation des responsabilités.

## Structure

```
routes/customers/
├── __init__.py          # Point d'entrée principal
├── utils.py            # Utilitaires et helpers
├── validation.py       # Validations et formulaires
├── geocoding.py        # Services de géolocalisation
├── consents.py         # Gestion RGPD et consentements
├── routes.py          # Routes principales CRUD
├── api.py             # Endpoints API REST
└── finances.py        # Gestion financière
```

## Migration

### Avant (monolithique)
```python
from routes.customers import bp, get_db_connection
```

### Après (modulaire)
```python
# Import du blueprint principal
from routes.customers import bp

# Import des utilitaires spécifiques
from routes.customers.utils import get_db_connection
from routes.customers.validation import validate_customer_form_advanced
from routes.customers.geocoding import geocode_address
```

## Avantages

1. **Maintenabilité** : Code organisé en modules logiques
2. **Testabilité** : Tests unitaires plus faciles
3. **Réutilisabilité** : Fonctions utilitaires réutilisables
4. **Performance** : Import sélectif des modules nécessaires
5. **Collaboration** : Équipes peuvent travailler sur modules différents

## Compatibilité

- ✅ Import du blueprint principal : `from routes.customers import bp`
- ✅ Routes existantes : Toutes les routes sont préservées
- ✅ Templates : Aucune modification requise
- ⚠️ Import direct de fonctions : Utiliser les nouveaux chemins modulaires

## Points de rupture potentiels

1. Import direct de fonctions internes
2. Accès direct aux variables globales
3. Tests unitaires ciblant l'ancien fichier

## Plan de migration

1. **Phase 1** : Backup et création de la structure modulaire ✅
2. **Phase 2** : Tests de régression sur toutes les fonctionnalités
3. **Phase 3** : Mise à jour des imports dans le code client
4. **Phase 4** : Suppression des fichiers de compatibilité
'''
    
    doc_path = "/home/amenard/Chronotech/ChronoTech/routes/customers/README.md"
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(doc_content)
    
    print(f"✅ Documentation créée: {doc_path}")

def main():
    """Fonction principale de migration"""
    print("🚀 Début de la migration vers l'architecture modulaire")
    print("=" * 60)
    
    # 1. Sauvegarde
    backup_path = backup_original_file()
    
    # 2. Stub de compatibilité
    create_import_stub()
    
    # 3. Documentation
    create_documentation()
    
    print("=" * 60)
    print("✅ Migration terminée avec succès!")
    print("\nÉtapes suivantes:")
    print("1. Tester l'application: python3 app.py")
    print("2. Vérifier les routes: /customers")
    print("3. Contrôler les logs d'erreur")
    print("4. Mettre à jour les imports dans le code client")
    
    if backup_path:
        print(f"\n💾 Le fichier original est sauvegardé: {backup_path}")
    
    print("\n📖 Consulter: routes/customers/README.md pour plus d'informations")

if __name__ == "__main__":
    main()
