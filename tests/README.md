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
