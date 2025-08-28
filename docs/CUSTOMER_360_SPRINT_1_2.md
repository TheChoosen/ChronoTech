# Customer 360 v1.5 - Sprint 1-2 Implementation Guide

## 📋 Vue d'ensemble

Cette implémentation du Sprint 1-2 introduit les fondations du système **Client 360** pour ChronoTech, en se concentrant sur:

1. **Timeline unifiée** des interactions client
2. **Profil enrichi** avec segmentation
3. **Consentements RGPD/Loi 25** conformes
4. **Interface utilisateur moderne** avec onglets

## 🗄️ Nouveaux schémas de base de données

### Table `customer_activity` (Timeline unifiée)
```sql
CREATE TABLE customer_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    activity_type ENUM('workorder', 'invoice', 'payment', 'quote', 'email', 'sms', 'call', 'document', 'appointment', 'note', 'consent', 'vehicle_added', 'system'),
    reference_id INT,
    reference_table VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSON,
    actor_id INT,
    actor_type ENUM('user', 'system', 'customer'),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Enrichissement table `customers`
```sql
ALTER TABLE customers ADD COLUMN
    language_code CHAR(5) DEFAULT 'fr-CA',
    timezone VARCHAR(64) DEFAULT 'America/Montreal',
    segments JSON,
    privacy_level ENUM('normal', 'restreint', 'confidentiel') DEFAULT 'normal',
    preferred_contact_channel ENUM('email', 'sms', 'phone', 'none') DEFAULT 'email',
    tax_exempt BOOLEAN DEFAULT FALSE;
```

### Table `customer_consents` (RGPD/Loi 25)
```sql
CREATE TABLE customer_consents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    consent_type ENUM('marketing_email', 'marketing_sms', 'analytics', 'profiling', 'data_sharing', 'service_notifications'),
    is_granted BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    collected_by INT,
    version INT NOT NULL DEFAULT 1,
    granted_at DATETIME,
    revoked_at DATETIME,
    expires_at DATETIME
);
```

## 🛠️ Nouveaux endpoints API

### Timeline client
```http
GET /customers/{id}/timeline
```
**Paramètres:**
- `page` (int): Numéro de page (défaut: 1)
- `per_page` (int): Éléments par page (défaut: 20)
- `type` (string): Filtrer par type d'activité

**Réponse JSON:**
```json
{
    "success": true,
    "activities": [...],
    "pagination": {
        "total": 150,
        "page": 1,
        "per_page": 20,
        "pages": 8,
        "has_next": true,
        "has_prev": false
    }
}
```

### Profil client enrichi
```http
GET /customers/{id}/profile
PATCH /customers/{id}/profile
```

**Exemple PATCH:**
```json
{
    "language_code": "en-CA",
    "timezone": "America/Toronto",
    "segments": ["VIP", "Entreprise"],
    "privacy_level": "confidentiel",
    "preferred_contact_channel": "email",
    "tax_exempt": true
}
```

### Consentements
```http
GET /customers/{id}/consents
POST /customers/{id}/consents
```

**Exemple POST:**
```json
{
    "consent_type": "marketing_email",
    "is_granted": true,
    "source": "web_form"
}
```

## 🎨 Nouvelles interfaces

### Vue Client 360 (`/customers/{id}/360`)
Interface unifiée avec onglets:
- **Profil**: Informations générales et segments
- **Contacts**: Gestion des contacts avec préférences
- **Adresses**: Adresses avec géolocalisation et fenêtres
- **Véhicules**: Liste des véhicules avec actions rapides
- **Activité**: Timeline des interactions
- **Consentements**: Gestion RGPD/Loi 25

### Timeline dédiée (`/customers/{id}/timeline`)
- Affichage chronologique des activités
- Filtres par type d'activité et date
- Pagination optimisée
- Enrichissement avec données de référence

### Gestion des consentements (`/customers/{id}/consents`)
- Vue d'ensemble des consentements actuels
- Historique complet avec audit trail
- Interface de modification avec confirmation
- Export des données (futur)

## 🔧 Fonctions utilitaires

### Logging d'activité
```python
from routes.customers import log_customer_activity

log_customer_activity(
    customer_id=123,
    activity_type='workorder',
    title='Nouveau bon de travail',
    description='Entretien préventif',
    reference_id=456,
    reference_table='work_orders',
    actor_id=1
)
```

### Vérification de consentement
```python
from routes.customers import has_valid_consent

if has_valid_consent(customer_id, 'marketing_email'):
    # Autorisation d'envoyer des emails marketing
    send_marketing_email(customer_id)
```

## 📱 Responsive Design

Toutes les nouvelles interfaces sont optimisées pour:
- **Desktop**: Interface complète avec tous les onglets
- **Tablet**: Adaptation automatique des colonnes
- **Mobile**: Navigation par onglets et actions simplifiées

## 🔒 Sécurité et conformité

### Protection des données
- Chiffrement des données sensibles
- Audit trail complet des modifications
- Respect des niveaux de confidentialité

### RGPD/Loi 25
- Consentements versionnés avec horodatage
- Traçabilité des sources et collecteurs
- Export complet des données client (futur)
- Révocation en un clic

## 🧪 Tests et validation

### Exécuter les tests
```bash
cd /home/amenard/Chronotech/ChronoTech
python test_sprint_1_2.py
```

### Migration de la base de données
```bash
mysql -u root -p chronotech < scripts/migrate_customers_v1_5.sql
```

## 📈 Métriques et KPIs

### Dashboard Client 360
- Nombre total de véhicules
- Bons de travail en cours
- Contacts et adresses configurés
- Statut des consentements
- Chiffre d'affaires 90 jours (futur)

### Analytics (Phase 2)
- Temps moyen de résolution des BT
- Taux de conversion devis→commande
- Satisfaction client (NPS)
- Récurrence des entretiens

## 🔄 Intégrations futures (Sprint 3-4)

### Module finances
- Profils de crédit et limites
- Méthodes de paiement tokenisées
- Historique des transactions

### Documents et signatures
- Upload sécurisé avec hash
- Signature électronique
- Preview et gestion des versions

### Automations
- Rappels d'entretien basés sur km/temps
- Relances de paiement
- Notifications de renouvellement

## 🚀 Déploiement

### Prérequis
1. MySQL 8.0+ ou MariaDB 10.5+
2. Python 3.8+ avec Flask
3. Bootstrap 5 et jQuery
4. Permissions de modification de schéma DB

### Étapes de déploiement
1. Sauvegarder la base de données existante
2. Exécuter le script de migration `migrate_customers_v1_5.sql`
3. Vérifier les nouvelles tables et colonnes
4. Tester les nouveaux endpoints
5. Former les utilisateurs aux nouvelles interfaces

### Vérification post-déploiement
- [ ] Timeline s'affiche correctement
- [ ] Profils client peuvent être modifiés
- [ ] Consentements fonctionnent end-to-end
- [ ] Interface responsive sur tous devices
- [ ] Pas de régressions sur les fonctionnalités existantes

## 📞 Support

Pour toute question technique sur cette implémentation:
1. Consulter les logs d'erreur dans `server.log`
2. Vérifier les erreurs JavaScript dans la console navigateur
3. Tester les endpoints API avec des outils comme Postman
4. Consulter la documentation des composants Bootstrap 5

---

**Version:** Customer 360 v1.5 Sprint 1-2  
**Date:** August 22, 2025  
**Statut:** ✅ Implémentation complète et testée
