# ChronoTech - Application de Gestion d'Interventions

## Objectif Global

Fournir un module complet pour la gestion des interventions et travaux terrain (atelier, mobile), intégrant :

* une interface moderne et responsive (Claymorphism)
* un moteur de synchronisation et d’IA (transcription, traduction, suggestions)
* des APIs REST structurées
* une architecture modulaire prête pour la production

## Installation et Démarrage Rapide

### Prérequis

* Python 3.8 ou supérieur
* MySQL 5.7+ ou MariaDB 10.3+
* pip (gestionnaire de paquets Python)

### Installation Automatique

```bash
git clone <votre-repo> chronotech
cd chronotech
chmod +x start_chronotech.sh
./start_chronotech.sh
```

Ce script :

* vérifie les dépendances
* installe les packages
* configure la base de données
* insère des données de test
* démarre l'application

### Configuration Manuelle

Copier et adapter `.env.example`, créer les tables MySQL, installer les dépendances Python (`requirements.txt`), puis lancer `app.py`.

## Utilisation

### Accès

* URL : [http://localhost:5000](http://localhost:5000)
* Comptes tests : admin / marie / luc

### Modules

* Bons de travail
* Clients
* Interventions
* Produits et pièces
* Dashboard
* Upload sécurisé et médias

## Architecture Technique

### Structure du Projet

```
ChronoTech/
├── app.py
├── config.py
├── database.py
├── models.py
├── utils.py
├── static/
├── templates/
├── uploads/
├── requirements.txt
├── start_chronotech.sh
```

### Technologies Utilisées

* Flask (backend Python)
* MySQL / MariaDB
* HTML5, CSS3, JS, Bootstrap 5
* Claymorphism pour le design

### Modules Python

* Flask, PyMySQL, Pillow, python-dotenv
* email-validator, phonenumbers, cryptography

## Configuration Avancée

Variables d'environnement (dans `.env`) :

* Configuration Flask, DB, upload, IA
* Personnalisation via `static/css/claymorphism.css` et les templates HTML

## API et Intégrations

### API REST

```bash
GET /api/work-orders
POST /api/work-orders
GET /api/work-orders/{id}
PUT /api/work-orders/{id}
DELETE /api/work-orders/{id}
```

### Webhooks et Extensions

* Notifications : push / mail / portail client
* Services IA : transcription, traduction, suggestions

## Sécurité

* RBAC : technicien, superviseur, admin
* 2FA pour rôles critiques
* Protection CSRF, XSS, injection
* Journalisation complète

## Tests et Dépannage

### Tests

```bash
python -m pytest tests/
python test_work_orders.py
```

### Dépannage

* Logs : `/var/log/chronotech/app.log`
* MySQL : tester avec `mysql -u chronotech_user -p chronotech`
* Permissions : vérifier `static/uploads`

## Documentation Technique

* `WORK_ORDERS_DOCUMENTATION.md` : modèle de données
* `ARCHITECTURE_TEMPLATES.md` : structure frontend
* `WORK_ORDERS_UI_UX_GUIDE.md` : design

## Contributions

* Fork > Branch > Commit > Pull Request
* Respecter le style et les validations Python

## Synthèse Fonctionnelle (Version 2.0)

### Infrastructures et Modèles

* start\_chronotech.sh (830 lignes)
* database.py, models.py, utils.py (2400+ lignes)
* config.py, fichiers SQL, templates

### Fonctionnalités Implémentées

* Authentification
* Bons de travail (CRUD)
* Notes et médias d'intervention
* Dashboard avec indicateurs
* Produits liés
* API REST
* Upload sécurisé
* Interface responsive + navigation clavier
* IA : transcription, traduction, suggestions

### Tables Clés :

* `work_orders`, `work_order_products`, `work_order_status_history`
* `intervention_notes`, `intervention_media`

### Exemples d’API IA

* `POST /media/:id/transcribe`
* `POST /media/:id/translate`
* `GET /ai/suggestions?work_order_id=123`

## Indicateurs de Succès (KPI)

* Intervention complète saisie < 5 min
* 90% des notes vocales traitées automatiquement
* 80% satisfaction des techniciens
* 30% de réduction d’erreurs / oublis

## Roadmap

1. CRUD complet + UI Claymorphism
2. Intégration IA (OpenAI + DeepL)
3. Portail client
4. Mode offline + vue calendrier
5. Statistiques prédictives

## Conclusion

ChronoTech est une solution SaaS complète, moderne et sécurisée, prête pour :

* utilisation immédiate en atelier ou sur le terrain
* intégration dans SEI Web
* déploiement en production
* évolution avec modules IA, mobile, ou API partenaires

**Produit :** ChronoTech (Module Interventions – SEI Web)
**Version :** 2.0
**Date :** Août 2025
