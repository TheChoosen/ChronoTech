# Module Travaux Demandés - ChronoTech

## Vue d'ensemble

Le module "Travaux Demandés" est un système CRUD complet pour la gestion des tâches et interventions dans ChronoTech. Il permet de créer, consulter, modifier et supprimer des travaux demandés avec leurs produits associés.

## Fonctionnalités

### 🎯 Gestion des Travaux
- **Création** : Nouveaux travaux avec toutes les informations client et technique
- **Consultation** : Liste complète avec filtres et recherche avancée
- **Modification** : Édition complète avec validation métier
- **Suppression** : Suppression sécurisée avec contrôles d'intégrité

### 🔍 Recherche et Filtrage
- Recherche textuelle sur numéro, client, description
- Filtres par statut, priorité, technicien
- Tri et pagination automatique
- Navigation clavier (F4, F8, F9, Enter)

### 📦 Gestion des Produits
- Ajout/modification/suppression de produits par travail
- Calcul automatique des prix totaux
- Références et notes pour chaque produit
- Contrôle d'intégrité avant suppression

### 📊 Tableau de Bord
- Statistiques en temps réel
- Indicateurs de performance
- États d'avancement des travaux
- Alertes priorités urgentes

## Structure des Données

### Table `work_orders`
```sql
- id (PK, AUTO_INCREMENT)
- claim_number (VARCHAR, UNIQUE) - Numéro de réclamation
- customer_name (VARCHAR) - Nom du client
- customer_address (TEXT) - Adresse du client
- customer_phone (VARCHAR) - Téléphone
- customer_email (VARCHAR) - Email
- description (TEXT) - Description du travail
- priority (ENUM) - low, medium, high, urgent
- status (ENUM) - draft, pending, assigned, in_progress, completed, cancelled
- assigned_technician_id (FK) - Technicien assigné
- created_by_user_id (FK) - Créateur du travail
- estimated_duration (INT) - Durée estimée (minutes)
- estimated_cost (DECIMAL) - Coût estimé
- actual_duration (INT) - Durée réelle
- actual_cost (DECIMAL) - Coût réel
- scheduled_date (DATETIME) - Date prévue
- completion_date (DATETIME) - Date de completion
- notes (TEXT) - Notes complémentaires
- created_at, updated_at (TIMESTAMP)
```

### Table `work_order_products`
```sql
- id (PK, AUTO_INCREMENT)
- work_order_id (FK) - Référence au travail
- product_name (VARCHAR) - Nom du produit
- product_reference (VARCHAR) - Référence produit
- quantity (DECIMAL) - Quantité
- unit_price (DECIMAL) - Prix unitaire
- total_price (DECIMAL) - Prix total
- notes (TEXT) - Notes sur le produit
- created_at (TIMESTAMP)
```

### Table `work_order_status_history`
```sql
- id (PK, AUTO_INCREMENT)
- work_order_id (FK) - Référence au travail
- old_status (VARCHAR) - Ancien statut
- new_status (VARCHAR) - Nouveau statut
- changed_by_user_id (FK) - Utilisateur ayant effectué le changement
- change_reason (TEXT) - Raison du changement
- created_at (TIMESTAMP)
```

## API Routes

### Travaux Demandés
- `GET /work_orders` - Liste des travaux avec filtres
- `GET /work_orders/new` - Formulaire de création
- `POST /work_orders/new` - Création d'un nouveau travail
- `GET /work_orders/<id>/edit` - Formulaire d'édition
- `POST /work_orders/<id>/edit` - Modification d'un travail
- `POST /work_orders/<id>/delete` - Suppression d'un travail
- `GET /api/work_orders/search` - API de recherche

### Produits
- `GET /work_orders/<id>/products` - Gestion des produits
- `POST /work_orders/<id>/products/add` - Ajout d'un produit
- `POST /work_orders/<id>/products/<product_id>/edit` - Modification
- `POST /work_orders/<id>/products/<product_id>/delete` - Suppression
- `GET /api/work_orders/<id>/products/<product_id>` - Détails produit

## Interface Utilisateur

### Page Principale (`/work_orders`)
- **Header** : Titre, actions (Nouveau, Actualiser)
- **Filtres** : Recherche, Statut, Priorité, Technicien
- **Tableau** : Liste des travaux avec actions
- **Statistiques** : Compteurs par statut

### Formulaire de Travail
- **Sections** : Informations principales, Client, Assignation, Estimations, Notes
- **Validation** : Temps réel avec messages d'erreur
- **Navigation** : Clavier et boutons

### Gestion des Produits
- **Liste** : Tableau avec quantités et prix
- **Modal** : Ajout/modification de produits
- **Calculs** : Prix totaux automatiques
- **Résumé** : Statistiques des produits

## Raccourcis Clavier

| Touche | Action |
|--------|--------|
| F4 | Nouveau travail / Modifier sélectionné |
| F8 | Recherche / Voir produits |
| F9 | Supprimer le travail sélectionné |
| Enter | Modifier le travail sélectionné |
| Escape | Fermer les modals |
| Ctrl+S | Sauvegarder (dans les formulaires) |

## Règles Métier

### Validations
- **Numéro de réclamation** : Unique et obligatoire
- **Client** : Nom et adresse obligatoires
- **Description** : Obligatoire, longueur minimale
- **Email/Téléphone** : Format validé si renseigné
- **Quantités/Prix** : Valeurs numériques positives

### Contraintes d'Intégrité
- **Suppression travail** : Impossible si produits associés
- **Suppression technicien** : Vérification des travaux assignés
- **Historique** : Conservation des changements de statut
- **Références** : Clés étrangères avec contraintes CASCADE/RESTRICT

### Statuts et Transitions
```
draft → pending → assigned → in_progress → completed
  ↓       ↓         ↓           ↓
cancelled ← cancelled ← cancelled ← cancelled
```

## Sécurité

### Contrôles d'Accès
- **Lecture** : Tous les utilisateurs connectés
- **Création/Modification** : Rôle admin ou manager
- **Suppression** : Rôle admin uniquement
- **Assignation** : Vérification des techniciens actifs

### Validation des Données
- **Sanitisation** : Nettoyage des entrées utilisateur
- **CSRF Protection** : Protection contre les attaques CSRF
- **SQL Injection** : Requêtes préparées avec paramètres
- **XSS Protection** : Échappement automatique dans les templates

## Performance

### Optimisations
- **Index** : Sur statut, priorité, dates, technicien
- **Pagination** : Limite de 100 résultats par défaut
- **Cache** : Mise en cache des listes de techniciens
- **AJAX** : Recherche asynchrone sans rechargement

### Monitoring
- **Logs** : Historique des actions critiques
- **Erreurs** : Capture et affichage des erreurs
- **Performance** : Métriques de temps de réponse

## Installation et Configuration

### Prérequis
```bash
# Base de données
mysql -h host -u user -p database < work_orders_tables.sql

# Données de test (optionnel)
python insert_sample_work_orders.py
```

### Variables d'Environnement
```bash
MYSQL_HOST=192.168.50.101
MYSQL_USER=gsicloud
MYSQL_PASSWORD=TCOChoosenOne204$
MYSQL_DB=gsi
```

### Navigation Menu
Le module est accessible via le menu principal pour les utilisateurs non-techniciens :
```html
<a class="nav-link" href="{{ url_for('work_orders') }}">
    <i class="fa-solid fa-clipboard-list me-1"></i> Travaux Demandés
</a>
```

## Maintenance

### Sauvegarde
- Sauvegarder régulièrement les tables `work_orders*`
- Conserver l'historique des statuts pour audit
- Archiver les travaux terminés anciens

### Mises à Jour
- Migrations de schéma avec scripts SQL
- Tests de régression sur les fonctionnalités critiques
- Validation des contraintes d'intégrité

### Dépannage
- Vérifier les logs Flask pour les erreurs
- Contrôler la connectivité base de données
- Valider les permissions utilisateurs

## Support

Pour toute question ou problème :
1. Consulter cette documentation
2. Vérifier les logs d'erreur
3. Tester avec des données de démonstration
4. Contacter l'équipe de développement

---

**Version** : 1.0.0  
**Dernière mise à jour** : Juillet 2025  
**Compatibilité** : Flask 2.x, MySQL 8.x, Python 3.8+
