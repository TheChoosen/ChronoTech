# Guide d'utilisation des patterns CRUD ChronoTech

## Templates créés

### _form.html
Template partiel factorisant add.html et edit.html.

**Usage dans add.html:**
```jinja
{% include 'module/_form.html' with context %}
{% set title = "Nouveau " + module %}
{% set submit_text = "Créer" %}
{% set cancel_url = url_for('module.index') %}
```

**Usage dans edit.html:**
```jinja
{% include 'module/_form.html' with context %}
{% set title = "Modifier " + item.name %}
{% set submit_text = "Mettre à jour" %}
{% set show_delete = true %}
```

### show.html
Template d'affichage détaillé uniforme.

**Variables requises:**
- title: Titre de la page
- subtitle: Sous-titre optionnel
- detail_content: Contenu principal (HTML)
- edit_url: URL d'édition
- back_url: URL de retour

## Avantages

✅ **Cohérence**: Templates uniformes
✅ **Maintenabilité**: Factorisation du code
✅ **Performance**: Moins de duplication
✅ **UX**: Interface utilisateur cohérente

## Prochaines étapes

1. Migrer les templates existants vers les nouveaux patterns
2. Personnaliser les form_fields selon chaque module
3. Implémenter la validation côté client
4. Ajouter les tests automatisés

