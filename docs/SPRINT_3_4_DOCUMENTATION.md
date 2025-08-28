# Documentation Sprint 3-4 - Finances Client & Documents

## Vue d'ensemble

Le Sprint 3-4 de ChronoTech Customer 360 v1.6 introduit deux modules majeurs :

### 🏦 Module Finances Client
- **Profils financiers** : Limites de crédit, conditions de paiement, niveaux de prix
- **Méthodes de paiement** : Gestion tokenisée des moyens de paiement (Stripe, PayPal, etc.)
- **Historique des soldes** : Suivi des transactions et soldes clients
- **Comptes à recevoir** : Vue consolidée des factures et paiements

### 📄 Module Documents & Signature
- **Gestion de documents** : Upload, catégorisation, stockage sécurisé
- **Signature électronique** : Intégration avec fournisseurs de signature
- **Audit et sécurité** : Traçabilité des accès et intégrité des fichiers
- **Prévisualisation** : Aperçu intégré des documents

## Architecture Technique

### Nouvelles Tables de Base de Données

#### 1. customer_finances
Profil financier par client :
```sql
- customer_id (PK)
- credit_limit : Limite de crédit autorisée
- available_credit : Crédit disponible calculé
- payment_terms : Conditions (net15, net30, net45, etc.)
- price_tier : Niveau (standard, vip, wholesale, government)
- discount_percent : Rabais contractuel
- tax_exempt : Exemption de taxes
- hold_status : Statut de blocage (none, review, credit_hold, blocked)
```

#### 2. customer_payment_methods
Méthodes de paiement tokenisées :
```sql
- id (PK)
- customer_id
- provider : Fournisseur (stripe, paypal, square, moneris)
- token : Token sécurisé du fournisseur
- method_type : Type (credit_card, debit_card, bank_account)
- masked_number : Numéro masqué pour affichage
- is_default : Méthode par défaut
```

#### 3. customer_documents
Documents client avec signature :
```sql
- id (PK)
- customer_id
- document_type : Type (contract, invoice, id_proof, etc.)
- file_path : Chemin de stockage
- hash_sha256 : Empreinte pour intégrité
- is_signed : Document signé
- signature_provider : Fournisseur de signature
- access_level : Niveau d'accès (public, customer, staff, admin)
```

#### 4. customer_balance_history
Historique des transactions :
```sql
- id (PK)
- customer_id
- event_type : Type d'événement (invoice_created, payment_received, etc.)
- amount : Montant de la transaction
- balance_before/balance_after : Soldes avant/après
```

### API Endpoints

#### Finances
```
GET    /customers/{id}/finances              # Récupérer profil financier
POST   /customers/{id}/finances              # Mettre à jour profil
GET    /customers/{id}/payment-methods       # Lister méthodes de paiement
POST   /customers/{id}/payment-methods       # Ajouter méthode de paiement
DELETE /customers/payment-methods/{id}       # Supprimer méthode
GET    /customers/{id}/balance-history       # Historique des soldes
POST   /customers/{id}/balance-history       # Ajouter entrée historique
```

#### Documents
```
GET    /customers/{id}/documents             # Lister documents
POST   /customers/{id}/documents             # Upload document
GET    /customers/documents/{id}             # Télécharger/prévisualiser
POST   /customers/documents/{id}/signature   # Signer document
DELETE /customers/documents/{id}             # Supprimer document
```

## Fonctionnalités Utilisateur

### Interface Finances

#### 📊 Tableau de Bord Financier
- **Métriques clés** : Limite de crédit, crédit disponible, solde ouvert, score de paiement
- **Profil financier** : Conditions, niveaux de prix, exemptions fiscales
- **Méthodes de paiement** : Cartes et comptes enregistrés de façon sécurisée
- **Comptes à recevoir** : Factures ouvertes, montants en retard
- **Historique** : Timeline des transactions et ajustements

#### 🔧 Gestion du Profil
- **Limite de crédit** : Définition et suivi automatique du crédit disponible
- **Conditions de paiement** : Net 15/30/45, immédiat, personnalisé
- **Niveaux de prix** : Standard, VIP, Gros, Gouvernement avec rabais associés
- **Statuts de blocage** : Gestion des restrictions de compte
- **Exemptions fiscales** : Configuration avec numéros officiels

### Interface Documents

#### 📁 Gestionnaire de Documents
- **Upload par glisser-déposer** : Interface moderne avec aperçu
- **Catégorisation** : Types prédéfinis (contrat, facture, garantie, etc.)
- **Prévisualisation** : Aperçu intégré pour images et PDFs
- **Métadonnées** : Titre, catégorie, niveau d'accès, confidentialité
- **Recherche et filtres** : Par type, date, statut de signature

#### ✍️ Signature Électronique
- **Fournisseurs multiples** : Support DocuSign, Adobe Sign, signature interne
- **Traçabilité complète** : Horodatage, IP, nom du signataire
- **Statut visuel** : Badges et indicateurs de signature
- **Audit** : Historique des accès et modifications

### Intégration Client 360

#### 🎯 Onglets Enrichis
Le Client 360 s'enrichit de nouveaux onglets :

- **Finances** : Vue synthétique du profil financier avec chargement AJAX
- **Documents** : Aperçu des documents récents avec actions rapides
- **Métriques temps réel** : KPIs financiers dans l'en-tête client

#### ⚡ Chargement Dynamique
- **AJAX intelligent** : Contenu chargé à la demande lors du clic sur l'onglet
- **Mise en cache** : Évite les rechargements inutiles
- **Performance optimisée** : Interfaces responsives sous 500ms

## Sécurité et Conformité

### 🔐 Sécurité des Documents
- **Hachage SHA-256** : Vérification d'intégrité des fichiers
- **Niveaux d'accès** : Contrôle granulaire (public, client, staff, admin)
- **Chiffrement** : Stockage sécurisé des tokens de paiement
- **Audit complet** : Logs d'accès avec IP et user-agent

### 🛡️ Protection des Données Financières
- **Tokenisation** : Aucune donnée de carte stockée en clair
- **Conformité PCI** : Respect des standards de sécurité
- **Séparation des rôles** : RBAC pour accès aux données sensibles
- **Soft delete** : Conservation de l'historique sans exposition

### 📋 Audit et Traçabilité
- **Logs d'activité** : Toute action tracée dans customer_activity
- **Historique des modifications** : Suivi des changements de profil financier
- **Accès aux documents** : Log de chaque consultation/téléchargement
- **Signatures** : Preuve légale avec métadonnées complètes

## Déploiement et Migration

### 📦 Migration Base de Données
Exécuter le script `migrate_customers_v1_6_sprint_3_4.sql` :

```bash
mysql -u username -p chronotech_db < scripts/migrate_customers_v1_6_sprint_3_4.sql
```

Le script inclut :
- ✅ Création des nouvelles tables
- ✅ Triggers automatiques pour cohérence des données
- ✅ Vues pour reporting
- ✅ Fonctions utilitaires (score de crédit)
- ✅ Index pour performance
- ✅ Migration des données existantes

### 🚀 Configuration Application

#### Variables d'Environment
```bash
# Stockage de fichiers
UPLOAD_FOLDER=/path/to/uploads
MAX_UPLOAD_SIZE=52428800  # 50MB

# Fournisseurs de paiement (optionnel)
STRIPE_PUBLIC_KEY=pk_...
STRIPE_SECRET_KEY=sk_...

# Signature électronique (optionnel)
DOCUSIGN_INTEGRATION_KEY=...
ADOBE_SIGN_API_KEY=...
```

#### Permissions Fichiers
```bash
# Répertoire uploads accessible en écriture
chmod 755 uploads/
chown www-data:www-data uploads/

# Sous-répertoires clients
mkdir -p uploads/customers
chmod 755 uploads/customers/
```

### 🧪 Tests et Validation

#### Script de Test Automatisé
```bash
python test_sprint_3_4.py
```

Tests inclus :
- ✅ Structure de base de données
- ✅ Endpoints API finances
- ✅ Endpoints API documents
- ✅ Intégration Client 360
- ✅ Performance (< 500ms)

#### Tests Manuels
1. **Finances** : Créer profil, ajouter méthode de paiement, consulter historique
2. **Documents** : Upload, prévisualisation, signature, suppression
3. **Client 360** : Navigation entre onglets, chargement AJAX
4. **Sécurité** : Vérifier restrictions d'accès selon les rôles

## Maintenance et Monitoring

### 📈 Métriques à Surveiller
- **Performance** : Temps de réponse des endpoints (<500ms)
- **Stockage** : Espace disque utilisé par les documents
- **Intégrité** : Vérification périodique des hash SHA-256
- **Utilisation** : Adoption des nouvelles fonctionnalités

### 🔧 Maintenance Préventive
- **Archivage** : Documents anciens selon politique de rétention
- **Nettoyage** : Suppression des tokens de paiement expirés
- **Sauvegarde** : Backup régulier des documents et métadonnées
- **Optimisation** : Analyse des requêtes lentes

### 🆘 Dépannage

#### Problèmes Courants
1. **Upload bloqué** : Vérifier permissions et espace disque
2. **AJAX non fonctionnel** : Contrôler en-têtes HTTP et CORS
3. **Calculs financiers incorrects** : Revoir triggers de mise à jour
4. **Documents corrompus** : Valider via hash SHA-256

#### Logs à Consulter
- **Application** : Erreurs dans les routes finances/documents
- **Base de données** : Échecs de triggers ou contraintes
- **Serveur web** : Erreurs 500 sur endpoints API
- **Stockage** : Permissions et accès fichiers

## Évolutions Futures

### 🔮 Roadmap Sprint 5-6
- **Intégrations** : Connexion ERP/comptabilité externe
- **IA/ML** : Scoring crédit automatique et détection de fraude
- **Mobile** : Application dédiée pour consultation documents
- **Workflow** : Approbations multi-niveaux pour crédits

### 🌟 Améliorations Suggérées
- **Signature en lot** : Signer plusieurs documents simultanément
- **Templates** : Génération automatique de contrats
- **Notifications** : Alertes email pour documents à signer
- **Intégration comptable** : Synchronisation automatique factures/paiements

---

## Support et Contact

Pour toute question sur l'implémentation du Sprint 3-4 :
- **Documentation technique** : Consulter les commentaires dans le code
- **Tests** : Exécuter `test_sprint_3_4.py` avant déploiement
- **Problèmes** : Vérifier logs application et base de données

**🚀 Sprint 3-4 complet et prêt pour déploiement !**
