#!/usr/bin/env python3
"""
🔧 CORRECTION PRIORITÉ 3: Complétion des patterns CRUD
======================================================

Cette correction standardise les patterns CRUD en créant les templates manquants
_form.html et show.html pour améliorer la cohérence et la réutilisabilité.
"""

import os
from pathlib import Path

def create_crud_templates():
    """Créer les templates CRUD manquants selon les patterns standard"""
    
    print("🔧 CORRECTION PRIORITÉ 3: Complétion des patterns CRUD")
    print("=" * 60)
    
    # Modules à analyser
    modules = ['customers', 'work_orders', 'vehicles', 'products', 'technicians']
    templates_base = "/home/amenard/Chronotech/ChronoTech/templates"
    
    # 1. Analyser l'existant
    print("📝 1. Analyse des templates existants...")
    
    existing_templates = {}
    missing_patterns = {}
    
    for module in modules:
        module_path = os.path.join(templates_base, module)
        existing_templates[module] = []
        missing_patterns[module] = []
        
        if os.path.exists(module_path):
            for file in os.listdir(module_path):
                if file.endswith('.html'):
                    existing_templates[module].append(file)
            
            # Vérifier les patterns CRUD standard
            standard_patterns = ['index.html', 'add.html', 'edit.html', 'view.html', '_form.html', 'show.html']
            for pattern in standard_patterns:
                if pattern not in existing_templates[module]:
                    missing_patterns[module].append(pattern)
        else:
            missing_patterns[module] = ['Dossier manquant']
    
    # Afficher l'analyse
    for module in modules:
        status = "✅" if len(missing_patterns[module]) <= 2 else "⚠️" 
        print(f"   {status} {module}:")
        if existing_templates[module]:
            print(f"     Existants: {', '.join(existing_templates[module])}")
        if missing_patterns[module] and missing_patterns[module] != ['Dossier manquant']:
            print(f"     Manquants: {', '.join(missing_patterns[module])}")
        elif missing_patterns[module] == ['Dossier manquant']:
            print(f"     ❌ Dossier manquant")
    
    # 2. Créer les templates _form.html manquants
    print("\n📝 2. Création des templates _form.html...")
    
    # Template _form.html générique
    form_template = """<!-- Template formulaire générique pour {{ module }} -->
<!-- Inclusion partielle pour factoriser add.html et edit.html -->

<div class="row">
    <div class="col-md-8">
        <div class="card clay-card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fa-solid fa-{{ icon }} me-2"></i>
                    {{ title }}
                </h5>
            </div>
            <div class="card-body">
                <form method="POST" enctype="multipart/form-data" class="needs-validation" novalidate>
                    {% if csrf_token %}
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    {% endif %}
                    
                    <!-- Champs du formulaire à personnaliser selon le module -->
                    {{ form_fields|safe }}
                    
                    <hr>
                    <div class="row">
                        <div class="col-md-6">
                            <button type="submit" class="btn btn-primary clay-button">
                                <i class="fa-solid fa-save me-1"></i>{{ submit_text }}
                            </button>
                            <a href="{{ cancel_url }}" class="btn btn-outline-secondary clay-button ms-2">
                                <i class="fa-solid fa-times me-1"></i>Annuler
                            </a>
                        </div>
                        <div class="col-md-6 text-end">
                            {% if show_delete and item_id %}
                            <button type="button" class="btn btn-outline-danger" onclick="confirmDelete({{ item_id }})">
                                <i class="fa-solid fa-trash me-1"></i>Supprimer
                            </button>
                            {% endif %}
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card clay-card">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fa-solid fa-info-circle me-2"></i>Aide
                </h6>
            </div>
            <div class="card-body">
                {{ help_content|safe }}
            </div>
        </div>
    </div>
</div>

<script>
// Validation côté client
(function() {
    'use strict';
    window.addEventListener('load', function() {
        var forms = document.getElementsByClassName('needs-validation');
        var validation = Array.prototype.filter.call(forms, function(form) {
            form.addEventListener('submit', function(event) {
                if (form.checkValidity() === false) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }, false);
})();

// Fonction de confirmation de suppression
function confirmDelete(id) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) {
        // Soumettre le formulaire de suppression
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = window.location.pathname + '/delete';
        
        var csrf = document.createElement('input');
        csrf.type = 'hidden';
        csrf.name = 'csrf_token';
        csrf.value = '{{ csrf_token() }}';
        form.appendChild(csrf);
        
        document.body.appendChild(form);
        form.submit();
    }
}
</script>"""

    # 3. Créer template show.html générique
    show_template = """<!-- Template d'affichage détaillé pour {{ module }} -->
{% extends "base.html" %}

{% block title %}{{ title }} - ChronoTech{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h2 class="mb-0">{{ title }}</h2>
        <p class="text-muted">{{ subtitle }}</p>
    </div>
    <div>
        {% if can_edit %}
        <a href="{{ edit_url }}" class="btn btn-outline-primary clay-button">
            <i class="fa-solid fa-edit me-1"></i>Modifier
        </a>
        {% endif %}
        <a href="{{ back_url }}" class="btn btn-outline-secondary clay-button">
            <i class="fa-solid fa-arrow-left me-1"></i>Retour
        </a>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card clay-card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fa-solid fa-{{ icon }} me-2"></i>Informations détaillées
                </h5>
            </div>
            <div class="card-body">
                {{ detail_content|safe }}
            </div>
        </div>
        
        {% if has_history %}
        <div class="card clay-card mt-3">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fa-solid fa-history me-2"></i>Historique
                </h6>
            </div>
            <div class="card-body">
                {{ history_content|safe }}
            </div>
        </div>
        {% endif %}
    </div>
    
    <div class="col-md-4">
        {% if has_sidebar %}
        <div class="card clay-card">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fa-solid fa-list me-2"></i>Actions rapides
                </h6>
            </div>
            <div class="card-body">
                {{ sidebar_content|safe }}
            </div>
        </div>
        {% endif %}
        
        <div class="card clay-card mt-3">
            <div class="card-header">
                <h6 class="mb-0">
                    <i class="fa-solid fa-chart-bar me-2"></i>Statistiques
                </h6>
            </div>
            <div class="card-body">
                {{ stats_content|safe }}
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

    # 4. Créer les fichiers manquants
    print("📝 3. Création des fichiers manquants...")
    
    created_files = 0
    for module in modules:
        module_path = os.path.join(templates_base, module)
        
        if not os.path.exists(module_path):
            os.makedirs(module_path, exist_ok=True)
            print(f"   📁 Dossier créé: {module}/")
        
        # Créer _form.html si manquant
        form_file = os.path.join(module_path, '_form.html')
        if not os.path.exists(form_file):
            with open(form_file, 'w', encoding='utf-8') as f:
                f.write(form_template.replace('{{ module }}', module))
            print(f"   ✅ Créé: {module}/_form.html")
            created_files += 1
        
        # Créer show.html si manquant
        show_file = os.path.join(module_path, 'show.html')
        if not os.path.exists(show_file):
            with open(show_file, 'w', encoding='utf-8') as f:
                f.write(show_template.replace('{{ module }}', module))
            print(f"   ✅ Créé: {module}/show.html")
            created_files += 1
    
    # 5. Créer un guide d'utilisation
    print("\n📝 4. Création du guide d'utilisation...")
    
    guide_content = """# Guide d'utilisation des patterns CRUD ChronoTech

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

"""

    guide_file = os.path.join(templates_base, "CRUD_PATTERNS_GUIDE.md")
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"   ✅ Guide créé: templates/CRUD_PATTERNS_GUIDE.md")
    
    # 6. Résumé
    print("\n📊 RÉSUMÉ:")
    print(f"   ✅ {created_files} templates créés")
    print(f"   ✅ Patterns CRUD standardisés")
    print(f"   ✅ Guide d'utilisation fourni")
    print(f"   🎯 Prêt pour migration des templates existants")

if __name__ == "__main__":
    create_crud_templates()
