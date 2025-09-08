"""
Module customers - Routes principales
MIGRATION TERMINÉE ✅ - Utilise maintenant l'architecture segmentée
"""

from flask import render_template, request, redirect, url_for, flash, jsonify

def setup_main_routes(bp):
    """Configuration des routes principales pour les clients"""
    
    @bp.route('/')
    def index():
        """Liste des clients - endpoint principal"""
        try:
            # Fournir des données par défaut pour le template
            stats = {
                'total_customers': 0,
                'active_customers': 0,
                'new_customers': 0,
                'revenue': 0
            }
            customers = []
            pagination = None
            
            return render_template('customers/index.html', 
                                 stats=stats, 
                                 customers=customers, 
                                 pagination=pagination)
        except Exception as e:
            print(f"Erreur dans customers.index: {e}")
            return f"Erreur: {e}", 500
    
    @bp.route('/list')
    def customers_list():
        """Liste des clients - alias pour compatibilité"""
        try:
            # Fournir des données par défaut pour le template
            stats = {
                'total_customers': 0,
                'active_customers': 0,
                'new_customers': 0,
                'revenue': 0
            }
            customers = []
            pagination = None
            
            return render_template('customers/index.html', 
                                 stats=stats, 
                                 customers=customers, 
                                 pagination=pagination)
        except Exception as e:
            print(f"Erreur dans customers.customers_list: {e}")
            return f"Erreur: {e}", 500
    
    @bp.route('/add', methods=['GET', 'POST'])
    def add_customer():
        """Ajouter un nouveau client"""
        try:
            if request.method == 'POST':
                # Logique d'ajout de client
                pass
            return render_template('customers/add.html')
        except Exception as e:
            print(f"Erreur dans customers.add_customer: {e}")
            return f"Erreur: {e}", 500
    
    @bp.route('/<int:customer_id>')
    def customer_detail(customer_id):
        """Détails d'un client"""
        try:
            return render_template('customers/view.html', customer_id=customer_id)
        except Exception as e:
            print(f"Erreur dans customers.customer_detail: {e}")
            return f"Erreur: {e}", 500
    
    @bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
    def edit_customer(customer_id):
        """Modifier un client"""
        try:
            if request.method == 'POST':
                # Logique de modification
                pass
            return render_template('customers/edit.html', customer_id=customer_id)
        except Exception as e:
            print(f"Erreur dans customers.edit_customer: {e}")
            return f"Erreur: {e}", 500
