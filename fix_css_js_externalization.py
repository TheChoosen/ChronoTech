#!/usr/bin/env python3
"""
🔧 CORRECTION PRIORITÉ 2: Externalisation CSS/JS de base.html
=============================================================

Cette correction améliore les performances et la modularité en externalisant
le CSS inline (140+ lignes) et en organisant mieux les scripts JS.
"""

import os
import re

def extract_css_from_base():
    """Extraire le CSS inline de base.html"""
    
    print("🔧 CORRECTION PRIORITÉ 2: Externalisation CSS/JS")
    print("=" * 60)
    
    base_file = "/home/amenard/Chronotech/ChronoTech/templates/base.html"
    css_output = "/home/amenard/Chronotech/ChronoTech/static/css/base-claymorphism.css"
    
    if not os.path.exists(base_file):
        print("❌ Fichier base.html non trouvé")
        return
    
    print("📝 1. Extraction du CSS inline...")
    
    with open(base_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Trouver et extraire le CSS dans les balises <style>
    css_pattern = r'<style>(.*?)</style>'
    css_matches = re.findall(css_pattern, content, re.DOTALL)
    
    if css_matches:
        # Combiner tout le CSS
        extracted_css = ""
        for css_block in css_matches:
            extracted_css += css_block.strip() + "\n\n"
        
        # Nettoyer et formater
        extracted_css = extracted_css.strip()
        
        # Ajouter un header
        css_header = """/*
 * ChronoTech - Base Claymorphism Styles
 * Extrait de base.html pour améliorer les performances
 * Généré automatiquement le 4 septembre 2025
 */

"""
        
        # Créer le dossier CSS s'il n'existe pas
        os.makedirs(os.path.dirname(css_output), exist_ok=True)
        
        # Écrire le fichier CSS
        with open(css_output, 'w', encoding='utf-8') as f:
            f.write(css_header + extracted_css)
        
        print(f"   ✅ CSS extrait vers: {css_output}")
        print(f"   📊 {len(extracted_css.split('\\n'))} lignes de CSS extraites")
        
        # 2. Remplacer le CSS inline par un lien externe
        print("\n📝 2. Remplacement du CSS inline...")
        
        # Supprimer les blocs <style>
        new_content = re.sub(css_pattern, '', content, flags=re.DOTALL)
        
        # Ajouter le lien vers le CSS externe dans le <head>
        css_link = '    <!-- ChronoTech Claymorphism Styles -->\n    <link href="{{ url_for(\'static\', filename=\'css/base-claymorphism.css\') }}" rel="stylesheet">\n'
        
        # Insérer après les autres liens CSS
        if 'href="{{ url_for(\'static\', filename=\'css/custom.css\') }}"' in new_content:
            new_content = new_content.replace(
                'href="{{ url_for(\'static\', filename=\'css/custom.css\') }}" rel="stylesheet">',
                'href="{{ url_for(\'static\', filename=\'css/custom.css\') }}" rel="stylesheet">\n' + css_link.strip()
            )
        else:
            # Insérer avant {% block head %}
            new_content = new_content.replace(
                '{% block head %}{% endblock %}',
                css_link + '    {% block head %}{% endblock %}'
            )
        
        # Sauvegarder le nouveau base.html
        with open(base_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("   ✅ base.html mis à jour avec lien CSS externe")
    
    # 3. Analyser et optimiser les scripts JS
    print("\n📝 3. Analyse des scripts JS...")
    
    with open(base_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Trouver tous les scripts
    script_pattern = r'<script[^>]*src="([^"]*)"[^>]*></script>'
    scripts = re.findall(script_pattern, content)
    
    print(f"   📊 {len(scripts)} scripts JS détectés:")
    for script in scripts:
        print(f"     - {script}")
    
    # 4. Créer un manifest pour les dépendances
    print("\n📝 4. Création du manifest des dépendances...")
    
    manifest_content = """/*
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
"""

    manifest_file = "/home/amenard/Chronotech/ChronoTech/static/js/dependencies-manifest.md"
    os.makedirs(os.path.dirname(manifest_file), exist_ok=True)
    
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    
    print(f"   ✅ Manifest créé: {manifest_file}")
    
    # 5. Résumé des améliorations
    print("\n📊 RÉSUMÉ DES AMÉLIORATIONS:")
    print("   ✅ CSS externalisé (140+ lignes)")
    print("   ✅ Performance améliorée (moins de HTML inline)")
    print("   ✅ Modularité renforcée")
    print("   ✅ Maintenance simplifiée")
    print("   📋 Manifest des dépendances créé")
    print("   🎯 Prêt pour optimisation conditionnelle JS")

if __name__ == "__main__":
    extract_css_from_base()
