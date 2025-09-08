/*
 * ChronoTech - JavaScript Dependencies Manifest
 * Guide pour l'optimisation du chargement des scripts
 */

/* SCRIPTS CORE (chargés sur toutes les pages) */
- Bootstrap 5 JS Bundle
- main.js (fonctions globales)
- ajax_helpers.js (utilitaires AJAX)

/* SCRIPTS MODULES (chargés conditionnellement) */
- work_orders.js (pages work_orders/* uniquement)
- vehicles.js (pages vehicles/* uniquement)  
- product_selector.js (formulaires avec sélection produits)

/* RECOMMANDATIONS D'OPTIMISATION */
1. Implémenter le chargement conditionnel basé sur request.endpoint
2. Minifier les scripts en production
3. Utiliser un bundler pour combiner les scripts fréquents
4. Implémenter le lazy loading pour les composants lourds

/* EXEMPLE D'IMPLÉMENTATION CONDITIONNELLE */
{% if 'work_orders' in request.endpoint %}
<script src="{{ url_for('static', filename='js/work_orders.js') }}"></script>
{% endif %}
