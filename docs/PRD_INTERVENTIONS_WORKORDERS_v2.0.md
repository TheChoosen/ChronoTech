# PRD - MODULES INTERVENTION ET BON DE TRAVAIL v2.0
## ChronoTech - Architecture Sécurisée (Post-Sprint 1)

**Date :** 27 août 2025  
**Version :** 2.0 (Sprint 1 Complété)  
**Statut :** ✅ Architecture DB Sécurisée | 🚧 Sprint 2 en préparation

---

## 📋 RÉSUMÉ EXÉCUTIF

Le système ChronoTech fournit une solution complète pour gérer les bons de travail et les interventions techniques avec une interface moderne Claymorphism. **NOUVEAUTÉ SPRINT 1 :** Architecture sécurisée garantissant qu'aucune tâche ne peut exister sans être rattachée à un Bon de travail, avec sources normées et relation 1-1 stricte intervention ↔ tâche.

### 🎯 OBJECTIFS PRODUIT

- ✅ **Workflow sécurisé** : WO → Tâche → Intervention (Sprint 1)
- ✅ **Sources normées** : `requested | suggested | preventive` (Sprint 1)  
- 🚧 **API imbriquée** : Routes `/work_orders/<id>/tasks/*` (Sprint 2)
- 🚧 **Interface technicien** : Mobile-first avec actions rapides (Sprint 3)
- 🚧 **Suggestions IA** : Diagnostics et recommandations automatisées

---

## 🏗️ ARCHITECTURE TECHNIQUE (Sprint 1 ✅)

### 🔒 SÉCURITÉ PAR DESIGN

**Règle Métier Fondamentale :**
> Toute tâche doit être créée sous un Bon de travail ChronoTech, avec `task_source ∈ {requested, suggested, preventive}`. Aucune création autonome n'est possible.

### 📊 MODÈLE DE DONNÉES SÉCURISÉ

#### Tables Principales (Sprint 1)
- **`work_orders`** : Bons de travail avec historisation automatique
- **`work_order_tasks`** ⭐ : Travaux à faire (NOUVEAU - contraintes strictes)
- **`interventions`** 🔄 : Refactorée - relation 1-1 avec tasks
- **`intervention_notes`** 🔄 : Notes liées aux interventions
- **`intervention_media`** 🔄 : Médias (photos, docs) avec métadonnées
- **`work_order_status_history`** ⭐ : Historique automatique (NOUVEAU)

#### Contraintes de Sécurité Implémentées
```sql
-- Empêche les tâches orphelines
CONSTRAINT fk_wot_wo FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
CONSTRAINT chk_wot_wo CHECK (work_order_id IS NOT NULL)

-- Relation 1-1 stricte intervention ↔ tâche  
CONSTRAINT fk_int_task FOREIGN KEY (task_id) REFERENCES work_order_tasks(id)
CONSTRAINT UNIQUE (task_id) -- Une seule intervention par tâche
```

#### Triggers de Garde-fous
- **`tr_wot_check_wo_id`** : Rejet insertion tâche sans work_order_id
- **`tr_int_check_task_id`** : Validation cohérence intervention/tâche
- **`tr_wo_status_history`** : Historisation automatique changements WO
- **`tr_task_status_sync`** : Synchronisation statut tâche ↔ intervention

---

## 🔄 FLUX UTILISATEUR SÉCURISÉ

### 1. Création Bon de Travail → Tâches
```
POST /work_orders/create → WO créé
POST /work_orders/<id>/tasks → Tâche created (source normée)
POST /work_orders/<id>/tasks/<task_id>/assign → Assignation technicien
```

### 2. Démarrage Intervention
```
POST /work_orders/<id>/tasks/<task_id>/start_intervention → Intervention 1-1
POST /interventions/<id>/add_note → Notes techniques
POST /interventions/<id>/upload_photos → Médias avec métadonnées
```

### 3. Clôture Avec Garde-fous IA
```
Règles de clôture automatique :
- ✅ Heures technicien renseignées
- ✅ Pièces utilisées documentées  
- ✅ Au moins une tâche complétée
- ✅ Notes d'intervention obligatoires
```

---

## 🚀 ROADMAP DÉTAILLÉE

### ✅ Sprint 1 — Schéma & Migrations (TERMINÉ)
**Objectif :** Rendre techniquement impossible toute tâche hors Bon de travail

**Livrables Complétés :**
- ✅ Table `work_order_tasks` avec contraintes strictes
- ✅ Table `interventions` refactorée (relation 1-1)  
- ✅ Triggers de garde-fous automatiques
- ✅ Historisation complète des changements
- ✅ Vues optimisées pour performances
- ✅ Tests automatisés (13 tests - 100% pass)

**Critères d'Acceptation Validés :**
- ✅ 0 tâche orpheline possible (contrainte + trigger)
- ✅ 0 intervention sans tâche valide (contrainte unique) 
- ✅ 100% historisation changements WO
- ✅ Performances < 50ms requêtes filtrées

### 🚧 Sprint 2 — API & Flux (EN COURS)
**Objectif :** Routes imbriquées sécurisées + Guards IA

**Livrables Prévus :**
- Routes imbriquées : `/work_orders/<id>/tasks/*`  
- Endpoints sécurisés : assign, status, start_intervention
- Guards IA : Règles de clôture automatique
- Validation 403/409 pour actions non autorisées
- Tests API complets

**Critères d'Acceptation :**
- Aucun endpoint `/tasks/create` global
- 403 si tentative création tâche hors WO  
- Démarrage intervention impossible si tâche n'appartient pas au WO
- Clôture WO bloquée si heures/pièces manquent

### 🔜 Sprint 3 — UI/UX (PLANIFIÉ)
**Objectif :** Interface technicien mobile + Superviseur desktop

**Livrables :**
- Technicien mobile-first : "À faire aujourd'hui", Start/Stop, notes/photos
- Superviseur : Kanban/Gantt avec drag&drop assignation
- Documents : Génération PDF avant/après intervention
- Notifications temps réel

---

## 🛠️ SPÉCIFICATIONS TECHNIQUES

### Routes Work Orders (Sprint 2)
```python
# Routes imbriquées sécurisées
POST /work_orders/<id>/tasks                    # Création tâche
POST /work_orders/<id>/tasks/<task_id>/assign   # Assignation  
POST /work_orders/<id>/tasks/<task_id>/status   # Mise à jour statut
POST /work_orders/<id>/tasks/<task_id>/start_intervention  # Démarrage intervention

# Guards IA intégrés
def can_close_work_order(wo) -> (bool, str):
    # Validation heures, pièces, notes obligatoires
```

### Routes Interventions (Sprint 2)
```python  
GET  /interventions/                    # Liste filtrée par rôle
GET  /interventions/<id>/details        # Interface détaillée
POST /interventions/<id>/add_note       # Notes techniques
POST /interventions/<id>/upload_photos  # Gestion médias
POST /interventions/<id>/quick_actions  # Actions rapides
```

### Vues Optimisées (Sprint 1 ✅)
```sql
-- Vue tâches avec contexte complet
v_work_order_tasks_complete

-- Vue interventions enrichie  
v_interventions_complete
```

---

## 🔒 SÉCURITÉ ET PERMISSIONS

### Niveaux d'Accès
- **Technicien** : Lecture/écriture ses tâches/interventions uniquement
- **Superviseur** : Visibilité atelier, assignations, replanification
- **Admin** : Accès complet + exports + configuration

### Validation Uploads
- Contrôle type/poids fichiers
- Stockage sécurisé avec noms non-devinables
- Métadonnées complètes (taille, type MIME, utilisateur)

---

## 📊 MÉTRIQUES DE SUCCÈS

### Techniques (Sprint 1 ✅)
- ✅ **0 tâche orpheline** : Impossible par design
- ✅ **100% historisation** : Triggers automatiques  
- ✅ **Performances < 50ms** : Index optimisés
- ✅ **Intégrité référentielle** : Contraintes strictes

### Fonctionnelles (Sprint 2-3)
- Temps moyen complétion bon de travail
- Taux d'utilisation suggestions IA  
- Nombre notes/médias par intervention
- Satisfaction technicien (interface mobile)

### KPIs Cibles
- **Création tâche** : < 30 secondes
- **Démarrage intervention** : < 10 secondes  
- **Upload photo** : < 5 secondes
- **Génération rapport** : < 60 secondes

---

## 🔧 VALIDATION ET TESTS

### Tests Automatisés Sprint 1 ✅
- **13 tests complets** : Contraintes, triggers, vues, performance
- **100% success rate** : Toutes validations passées
- **Couverture** : Sécurité, intégrité, performance, cascade

### Tests Prévus Sprint 2
```python
# Tests API sécurisées
def test_cannot_create_orphan_task():
    response = POST("/tasks/create", {...})
    assert response.status_code == 404

def test_cannot_start_intervention_wrong_wo():
    response = POST("/work_orders/1/tasks/999/start_intervention")  
    assert response.status_code == 403
```

---

## 🌟 INNOVATIONS TECHNIQUES

### 1. Architecture Sécurisée par Design
- Impossible de créer des données incohérentes
- Contraintes DB + Triggers + Validation applicative
- Historisation automatique sans code métier

### 2. Guards IA Intégrés
- Règles métier intelligentes pour clôture  
- Validation automatique heures/pièces/notes
- Suggestions contextuelles pour techniciens

### 3. Interface Adaptive
- Mobile-first pour techniciens terrain
- Desktop riche pour superviseurs  
- Synchronisation temps réel entre vues

---

## ✅ STATUT ACTUEL

**Sprint 1 :** 🟢 **COMPLÉTÉ** - Architecture DB sécurisée opérationnelle
**Sprint 2 :** 🟡 **EN COURS** - API sécurisées et Guards IA  
**Sprint 3 :** ⚪ **PLANIFIÉ** - Interfaces utilisateur finales

**Prêt pour Production :** Sprint 2 (estimation 2 semaines)

---

*Ce PRD représente l'état post-Sprint 1 des modules intervention et bon de travail dans ChronoTech, démontrant une architecture sécurisée par design avec impossibilité technique de créer des données incohérentes.*
