# Archive ChronoTech

## Debug Tools
Outils de débogage et de diagnostic de la base de données :

- `check_db_structure.py` - Vérification détaillée de la structure des tables
- `simple_db_check.py` - Vérification simple de la structure DB
- `fix_is_active.py` - Script de correction pour les colonnes is_active

## Tests
Fichiers de test et versions de développement :

- `test_standalone.py` - Version de test sans base de données

## Utilisation

Ces fichiers peuvent être utilisés ponctuellement pour le débogage ou la maintenance, mais ne sont pas nécessaires au fonctionnement quotidien de l'application.

### Pour utiliser un outil de debug :
```bash
cd /home/amenard/Chronotech/ChronoTech/archive/debug_tools
python check_db_structure.py
```

### Pour utiliser un test :
```bash
cd /home/amenard/Chronotech/ChronoTech/archive/tests
python test_standalone.py
```

## Structure des modules principaux

Après réorganisation, les modules principaux sont dans `/core/` :
- `config.py` - Configuration de l'application
- `database.py` - Gestionnaire de base de données
- `models.py` - Modèles de données
- `utils.py` - Utilitaires système
- `forms.py` - Formulaires Flask-WTF

Les routes restent dans `/routes/` avec imports mis à jour vers le module core.
