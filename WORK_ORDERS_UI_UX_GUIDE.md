# Guide UI/UX - Module Travaux Demandés avec Interventions

## 🎯 Vue d'ensemble

Le module CRUD des travaux demandés de ChronoTech offre une interface moderne et intuitive pour gérer les travaux avec ou sans interventions associées. L'interface claymorphisme assure une expérience utilisateur fluide et professionnelle.

## 🚀 Fonctionnalités principales

### 1. Création de travaux demandés

#### Création rapide (Modal)
- **Accès** : Bouton "Nouveau Travail" dans l'en-tête
- **Champs essentiels** : Réclamation, client, description, priorité
- **Option intervention** : Toggle pour associer une intervention
- **Validation temps réel** : Contrôle des champs obligatoires

#### Création avec intervention
- **Accès** : Menu déroulant "Travail avec intervention" 
- **Intervention automatique** : Section intervention pré-activée
- **Types d'intervention** :
  - **Nouvelle** : Créer une intervention en même temps
  - **Existante** : Associer à une intervention déjà planifiée

#### Formulaire complet
- **Accès** : Lien "Formulaire complet" ou bouton "Modifier"
- **Tous les champs** : Informations complètes client et techniques
- **Intervention détaillée** : Configuration avancée des interventions
- **Prévisualisation** : Aperçu en temps réel des informations

### 2. Affichage et navigation

#### Vue cartes (par défaut)
- **Affichage** : Grille de cartes avec informations essentielles
- **Indicateurs visuels** :
  - Badge d'intervention si associée
  - Couleurs par priorité et statut
  - Icônes pour actions rapides
- **Interactions** :
  - Clic : Sélection
  - Double-clic : Édition
  - Survol : Actions disponibles

#### Vue tableau
- **Bascule** : Bouton "Tableau" ou touche F2
- **Colonnes** : Toutes les informations en format compact
- **Colonne intervention** : Indicateur visuel avec date si planifiée
- **Tri** : Clic sur les en-têtes de colonnes
- **Sélection multiple** : Ctrl+clic pour sélectionner plusieurs lignes

### 3. Gestion des interventions

#### Indicateurs visuels
- **Cartes** : Section spéciale avec badge intervention
- **Tableau** : Colonne dédiée avec icône et date
- **Couleurs** : Bordure bleue pour les travaux avec intervention

#### Types d'association
1. **Nouvelle intervention**
   - Titre obligatoire
   - Date et description optionnelles
   - Création simultanée

2. **Intervention existante**
   - Sélection dans la liste
   - Informations pré-remplies
   - Liaison immédiate

#### Toggle intervention
- **Activation** : Case à cocher avec slider animé
- **Validation** : Champs requis selon le type
- **Prévisualisation** : Aperçu des informations saisies

### 4. Recherche et filtres

#### Barre de recherche
- **Champs indexés** : Réclamation, client, description
- **Temps réel** : Résultats avec délai de 300ms
- **Highlighting** : Mise en surbrillance des termes trouvés

#### Filtres avancés
- **Statut** : Tous les statuts disponibles
- **Priorité** : Faible à Urgente
- **Technicien** : Liste des techniciens assignés
- **Intervention** : Avec/Sans intervention
- **Combinaison** : Filtres cumulatifs

### 5. Actions et raccourcis

#### Raccourcis clavier
- **F2** : Basculer vue cartes/tableau
- **F4** : Modifier le travail sélectionné
- **F8** : Voir les produits associés
- **F9** : Supprimer (avec confirmation)
- **Ctrl+A** : Tout sélectionner
- **Ctrl+S** : Sauvegarder (dans formulaires)
- **Esc** : Annuler/Fermer

#### Actions rapides
- **Édition** : Formulaire complet ou modal rapide
- **Produits** : Gestion des produits associés
- **Suppression** : Confirmation avec détails
- **Duplication** : (Future fonctionnalité)

## 🎨 Design et UX

### Thème claymorphisme
- **Cartes** : Effet de profondeur avec ombres douces
- **Boutons** : Effet ripple au clic
- **Formulaires** : Validation visuelle en temps réel
- **Animations** : Transitions fluides et naturelles

### Responsive design
- **Desktop** : Grille 3-4 colonnes, toutes les informations
- **Tablette** : Grille 2 colonnes, informations essentielles
- **Mobile** : Liste verticale, navigation tactile optimisée

### Accessibilité
- **Contrastes** : Respect des normes WCAG
- **Navigation clavier** : Support complet
- **Aria labels** : Lecteurs d'écran compatibles
- **Focus visible** : Indicateurs clairs

## 🔧 Configuration technique

### Dépendances
- **Bootstrap 5** : Structure et composants
- **Font Awesome 6** : Iconographie
- **CSS custom** : Thème claymorphisme
- **JavaScript vanilla** : Interactions et validations

### API endpoints
- `GET /work_orders` : Liste des travaux
- `POST /work_orders/new` : Création nouveau travail
- `GET /work_orders/{id}/edit` : Formulaire d'édition
- `POST /work_orders/{id}/update` : Mise à jour
- `DELETE /work_orders/{id}` : Suppression
- `GET /work_orders/{id}/products` : Gestion produits

### Gestion des erreurs
- **Validation côté client** : Temps réel avec feedback visuel
- **Validation serveur** : Messages d'erreur contextuels
- **États de chargement** : Indicateurs pendant les opérations
- **Notifications** : Toast messages pour les actions

## 📱 Utilisation optimale

### Workflow recommandé
1. **Consultation** : Vue cartes pour aperçu rapide
2. **Recherche** : Filtres pour cibler les travaux
3. **Création** : Modal pour travaux simples, formulaire pour complexes
4. **Gestion** : Actions rapides depuis les cartes/tableau
5. **Suivi** : Colonnes intervention et produits pour monitoring

### Bonnes pratiques
- **Nommage** : Numéros de réclamation descriptifs
- **Priorités** : Usage cohérent des niveaux
- **Interventions** : Planification anticipée quand possible
- **Statuts** : Mise à jour régulière du workflow
- **Produits** : Association systématique pour traçabilité

## 🆕 Évolutions futures

### Fonctionnalités planifiées
- **Templates** : Modèles de travaux récurrents
- **Notifications** : Alertes automatiques par email/SMS
- **Calendrier** : Vue planning des interventions
- **Rapports** : Analytics et statistiques avancées
- **Mobile app** : Application dédiée pour techniciens

### Améliorations UX
- **Drag & drop** : Réorganisation des priorités
- **Collaboration** : Commentaires et suivi équipe
- **Historique** : Versioning des modifications
- **Export** : PDF, Excel, formats personnalisés
- **Intégrations** : APIs externes (facturation, CRM)

---

*Ce guide évolue avec les retours utilisateurs et les mises à jour du système.*
