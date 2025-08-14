"""
Module de gestion des clients - ChronoTech
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from forms import CustomerForm
import pymysql
from config import get_db_config
from utils import log_info, log_error, log_warning
import traceback

# Création du blueprint
bp = Blueprint('customers', __name__)

def get_db_connection():
    """Obtient une connexion à la base de données"""
    try:
        return pymysql.connect(**get_db_config())
    except Exception as e:
        log_error(f"Erreur de connexion à la base de données: {e}")
        return None

@bp.route('/')
def index():
    """Page principale des clients"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {
                'total_customers': 0,
                'active_customers': 0,
                'total_work_orders': 0,
                'total_revenue': 0
            }
            class DummyPagination:
                total = 0
                prev_num = None
                next_num = None
                pages = 1
            pagination = DummyPagination()
            return render_template('customers/index.html', customers=[], stats=stats, pagination=pagination)
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, company, email, phone, address, created_at, is_active
            FROM customers 
            WHERE is_active = TRUE
            ORDER BY name ASC
        """)
        
        customers = cursor.fetchall()
        cursor.close()
        conn.close()
        
        log_info(f"Récupération de {len(customers)} clients")
        # Statistiques basiques (à adapter selon tes besoins)
        stats = {
            'total_customers': len(customers),
            'active_customers': len([c for c in customers if c.get('is_active', True)]),
            'total_work_orders': 0,  # À calculer si besoin
            'total_revenue': 0      # À calculer si besoin
        }
        class DummyPagination:
            total = len(customers)
            prev_num = None
            next_num = None
            pages = 1
        pagination = DummyPagination()
        return render_template('customers/index.html', customers=customers, stats=stats, pagination=pagination)
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération des clients: {e}")
        flash('Erreur lors du chargement des clients', 'error')
        stats = {
            'total_customers': 0,
            'active_customers': 0,
            'total_work_orders': 0,
            'total_revenue': 0
        }
        class DummyPagination:
            total = 0
            prev_num = None
            next_num = None
            pages = 1
        pagination = DummyPagination()
        return render_template('customers/index.html', customers=[], stats=stats, pagination=pagination)

@bp.route('/add', methods=['GET', 'POST'])
def add_customer():
    """Ajouter un nouveau client"""
    form = CustomerForm()
    if form.validate_on_submit():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return render_template('customers/add.html', form=form)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customers (name, company, email, phone, address, siret, status, postal_code, city, country, billing_address, payment_terms, notes, tax_number, preferred_contact_method, zone)
                VALUES (%(name)s, %(company)s, %(email)s, %(phone)s, %(address)s, %(siret)s, %(status)s, %(postal_code)s, %(city)s, %(country)s, %(billing_address)s, %(payment_terms)s, %(notes)s, %(tax_number)s, %(preferred_contact_method)s, %(zone)s)
            """, {
                'name': form.name.data,
                'company': form.company.data,
                'email': form.email.data,
                'phone': form.phone.data,
                'address': form.address.data,
                'siret': form.siret.data,
                'status': form.status.data,
                'postal_code': form.postal_code.data,
                'city': form.city.data,
                'country': form.country.data,
                'billing_address': form.billing_address.data,
                'payment_terms': form.payment_terms.data,
                'notes': form.notes.data,
                'tax_number': form.tax_number.data,
                'preferred_contact_method': form.preferred_contact_method.data,
                'zone': form.zone.data
            })
            conn.commit()
            customer_id = cursor.lastrowid
            cursor.close()
            conn.close()
            log_info(f"Nouveau client créé: {form.name.data} (ID: {customer_id})")
            flash('Client ajouté avec succès', 'success')
            return redirect(url_for('customers.index'))
        except pymysql.IntegrityError as e:
            log_error(f"Erreur d'intégrité lors de l'ajout du client: {e}")
            flash('Un client avec cet email existe déjà', 'error')
        except Exception as e:
            log_error(f"Erreur lors de l'ajout du client: {e}")
            flash('Erreur lors de l\'ajout du client', 'error')
    return render_template('customers/add.html', form=form)

@bp.route('/<int:customer_id>')
def view_customer(customer_id):
    """Voir les détails d'un client"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.index'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Récupérer les informations du client
        cursor.execute("""
            SELECT * FROM customers WHERE id = %s AND is_active = TRUE
        """, (customer_id,))
        
        customer = cursor.fetchone()
        if not customer:
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))
        
        # Récupérer les bons de travail associés
        cursor.execute("""
            SELECT id, claim_number, description, status, priority, created_at, scheduled_date
            FROM work_orders 
            WHERE customer_id = %s 
            ORDER BY created_at DESC
        """, (customer_id,))
        
        work_orders = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('customers/view.html', customer=customer, work_orders=work_orders)
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération du client {customer_id}: {e}")
        flash('Erreur lors du chargement du client', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Modifier un client"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            conn = get_db_connection()
            if not conn:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})
                else:
                    flash('Erreur de connexion à la base de données', 'error')
                    return redirect(url_for('customers.view_customer', customer_id=customer_id))
            
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE customers 
                SET name = %(name)s, company = %(company)s, email = %(email)s, 
                    phone = %(phone)s, address = %(address)s, updated_at = NOW()
                WHERE id = %(id)s AND is_active = TRUE
            """, {
                'name': data.get('name'),
                'company': data.get('company', ''),
                'email': data.get('email'),
                'phone': data.get('phone', ''),
                'address': data.get('address', ''),
                'id': customer_id
            })
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_info(f"Client modifié: {data.get('name')} (ID: {customer_id})")
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Client modifié avec succès'})
            else:
                flash('Client modifié avec succès', 'success')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
                
        except Exception as e:
            log_error(f"Erreur lors de la modification du client {customer_id}: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la modification du client'})
            else:
                flash('Erreur lors de la modification du client', 'error')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
    
    # GET request - afficher le formulaire de modification
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('customers.index'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE id = %s AND is_active = TRUE", (customer_id,))
        customer = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not customer:
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))
        
        return render_template('customers/edit.html', customer=customer)
        
    except Exception as e:
        log_error(f"Erreur lors du chargement du formulaire d'édition pour le client {customer_id}: {e}")
        flash('Erreur lors du chargement du formulaire', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    """Supprimer un client (soft delete)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})
        
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE customers 
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s
        """, (customer_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        log_info(f"Client supprimé (soft delete): ID {customer_id}")
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Client supprimé avec succès'})
        else:
            flash('Client supprimé avec succès', 'success')
            return redirect(url_for('customers.index'))
            
    except Exception as e:
        log_error(f"Erreur lors de la suppression du client {customer_id}: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': 'Erreur lors de la suppression du client'})
        else:
            flash('Erreur lors de la suppression du client', 'error')
            return redirect(url_for('customers.index'))

@bp.route('/api/search')
def api_search():
    """API de recherche de clients"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'customers': []})
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erreur de connexion à la base de données'}), 500
        
        cursor = conn.cursor(dictionary=True)
        search_query = f"%{query}%"
        cursor.execute("""
            SELECT id, name, company, email, phone
            FROM customers 
            WHERE is_active = TRUE 
            AND (name LIKE %s OR company LIKE %s OR email LIKE %s OR phone LIKE %s)
            ORDER BY name ASC
            LIMIT 20
        """, (search_query, search_query, search_query, search_query))
        
        customers = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'customers': customers})
        
    except Exception as e:
        log_error(f"Erreur lors de la recherche de clients: {e}")
        return jsonify({'error': 'Erreur lors de la recherche'}), 500
