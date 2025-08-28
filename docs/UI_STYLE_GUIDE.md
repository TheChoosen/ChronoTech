# Guide de Style UI - ChronoTech Customer 360

## Conventions de Nommage

### 1. IDs HTML

Tous les IDs doivent suivre le pattern `kebab-case` avec préfixe de section :

#### Pattern Principal
```
{section}-{element}-{type}
```

#### Exemples par Section
- **Onglets** : `tab-{section}` (ex: `tab-profile`, `tab-activity`)
- **Contenu** : `tab-content-{section}` (ex: `tab-content-profile`)
- **Placeholders** : `placeholder-{section}` (ex: `placeholder-activity`)

#### Section Activity
- `activity-search` : Champ de recherche d'activité
- `activity-type-filter` : Filtre par type d'activité
- `activity-period-filter` : Filtre par période
- `activity-timeline` : Conteneur de la timeline
- `activity-loading` : État de chargement
- `activity-total` : Statistique total des activités

#### Section Documents
- `documents-search` : Champ de recherche de documents
- `documents-type-filter` : Filtre par type de document
- `documents-status-filter` : Filtre par statut
- `documents-grid` : Vue grille des documents
- `documents-list` : Vue liste des documents

#### Section Finances
- `finances-revenue-chart` : Graphique de revenus
- `finances-chart-6m` : Bouton période 6 mois
- `finances-invoice-status-filter` : Filtre statut factures

#### Section Analytics
- `analytics-period` : Sélecteur de période
- `analytics-revenue-time-chart` : Graphique revenus temporel
- `analytics-services-chart` : Graphique des services

### 2. Classes CSS

#### Classes Clay (Design System)
Toutes les classes personnalisées utilisent le préfixe `clay-` :

- `clay-card` : Cartes avec effet glassmorphism
- `clay-button` : Boutons avec style clay
- `clay-input` : Champs de saisie stylisés
- `clay-select` : Listes déroulantes stylisées
- `clay-element` : Élément générique avec style clay

#### Classes Bootstrap
Utilisation standard de Bootstrap 5 pour la structure :
- `container`, `row`, `col-*`
- `card`, `card-body`, `card-header`
- `btn`, `form-control`, `nav-tabs`

### 3. Attributs d'Accessibilité

#### ARIA Labels
Tous les onglets et contenus doivent avoir des attributs ARIA appropriés :

```html
<!-- Onglet -->
<button class="nav-link" 
        id="tab-profile" 
        data-bs-toggle="tab" 
        data-bs-target="#tab-content-profile"
        aria-controls="tab-content-profile"
        aria-selected="true">

<!-- Contenu -->
<div class="tab-pane" 
     id="tab-content-profile"
     aria-labelledby="tab-profile">
```

#### Rôles
- `role="tablist"` pour les conteneurs d'onglets
- `role="tab"` pour les onglets individuels
- `role="tabpanel"` pour les panneaux de contenu

### 4. Structure JavaScript

#### Variables CamelCase
```javascript
const customerId = {{ customer.id }};
const customerName = "{{ customer.display_name }}";
const loadedSections = new Set();
```

#### Fonctions descriptives
```javascript
function loadSectionIfNeeded(sectionName) { }
function preloadNextSection() { }
function filterActivity() { }
function updateAnalytics() { }
```

#### Sélecteurs correspondants
```javascript
// Nouveau pattern standardisé
document.getElementById(`placeholder-${sectionName}`)
document.getElementById(`tab-content-${sectionName}`)
document.getElementById(`activity-search`)
```

### 5. Structure des Templates

#### Sections
Chaque section suit cette structure :
```
templates/customers/_sections/
├── profile.html      # Section profil
├── activity.html     # Section activité
├── finances.html     # Section finances
├── documents.html    # Section documents
├── analytics.html    # Section analytics
└── consents.html     # Section consentements
```

#### Macros
Composants réutilisables dans `_components/macros.html` :
```jinja
customer_360_tabs()
customer_info_card()
stats_card()
timeline_item()
loading_skeleton()
```

### 6. Conventions de Couleurs

#### Variables CSS
```css
:root {
    --primary-color: #667eea;
    --success-color: #48bb78;
    --warning-color: #ed8936;
    --info-color: #4299e1;
    --danger-color: #f56565;
}
```

#### Usage dans les templates
```html
<h3 style="color: var(--primary-color);" id="activity-total">
<div class="text-success">Statut OK</div>
<span class="badge bg-warning">En attente</span>
```

### 7. Responsive Design

#### Breakpoints Bootstrap
- `xs` : < 576px
- `sm` : ≥ 576px  
- `md` : ≥ 768px
- `lg` : ≥ 992px
- `xl` : ≥ 1200px

#### Colonnes adaptatives
```html
<div class="col-12 col-md-6 col-lg-4">
<div class="col-md-8 col-lg-9">
```

### 8. Performance et Lazy Loading

#### Placeholders
Tous les contenus non-critiques utilisent des placeholders :
```html
<div id="placeholder-{section}" class="loading-placeholder">
    {{ loading_skeleton() }}
</div>
```

#### Chargement différé
```javascript
// Chargement automatique au clic d'onglet
loadSectionIfNeeded(sectionName);

// Préchargement intelligent
preloadNextSection();
```

### 9. Tests et Validation

#### IDs uniques
- Vérifier l'unicité des IDs dans chaque page
- Utiliser des préfixes de section pour éviter les conflits

#### Accessibilité
- Validation WCAG 2.1 AA
- Navigation au clavier fonctionnelle
- Lecteurs d'écran compatibles

#### Performance
- Lazy loading des sections non-visibles
- Chargement progressif des données
- Optimisation des requêtes AJAX

### 10. Outils de Développement

#### Validation HTML
```bash
# Validation W3C
w3c-validator templates/customers/view_360_unified.html
```

#### Tests accessibilité
```bash
# axe-core pour les tests d'accessibilité
npm install @axe-core/cli
axe http://localhost:5000/customers/1/view
```

#### Linting CSS
```bash
# stylelint pour la validation CSS
npm install stylelint
stylelint static/css/**/*.css
```

---

## Résumé des Changements Appliqués

### ✅ Standardisation Complétée

1. **Onglets** : Migration vers `tab-{section}`
2. **Contenu** : Migration vers `tab-content-{section}`
3. **Placeholders** : Migration vers `placeholder-{section}`
4. **JavaScript** : Mise à jour des sélecteurs
5. **Sections** : Standardisation des IDs internes

### 🔄 En Cours

1. Application complète aux sections restantes
2. Validation des fonctions JavaScript
3. Tests d'accessibilité

### 📋 Prochaines Étapes

1. Finaliser la standardisation des sections consents
2. Valider le bon fonctionnement de l'interface
3. Documenter les patterns pour les futures développements
4. Créer des tests automatisés pour maintenir la cohérence

---

Cette standardisation améliore significativement la maintenabilité, l'accessibilité et la cohérence de l'interface Customer 360.
