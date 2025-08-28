"""
Routes principales CRUD pour les clients
"""

import pymysql
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from core.forms import CustomerForm
from core.utils import log_info, log_error
from .utils import get_db_connection, require_role, get_current_user, MiniPagination, _debug


def setup_main_routes(bp):
    """Configure les routes principales du module clients"""
    
    @bp.route('/')
    def index():
        """Liste des clients avec pagination et recherche"""
        try:
            # Paramètres de recherche et pagination
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '')
            sort_by = request.args.get('sort', 'name')
            sort_dir = request.args.get('dir', 'asc')
            
            # Validation des paramètres
            if sort_by not in ['name', 'email', 'created_at', 'last_activity_date']:
                sort_by = 'name'
            if sort_dir not in ['asc', 'desc']:
                sort_dir = 'asc'
            
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return render_template('customers/index.html', customers=[], pagination=None)
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Construction de la requête
            where_clause = "WHERE 1=1"
            params = []
            
            if search:
                where_clause += " AND (name LIKE %s OR email LIKE %s OR company LIKE %s)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            # Compter le total
            count_query = f"SELECT COUNT(*) as total FROM customers {where_clause}"
            cursor.execute(count_query, params)
            total_customers = cursor.fetchone()['total']
            
            # Créer la pagination
            pagination = MiniPagination(page=page, per_page=per_page, total=total_customers)
            
            # Récupérer les clients
            query = f"""
                SELECT id, name, email, phone, company, city, status, created_at, last_activity_date
                FROM customers 
                {where_clause}
                ORDER BY {sort_by} {sort_dir.upper()}
                LIMIT %s OFFSET %s
            """
            params.extend([per_page, pagination.offset])
            
            cursor.execute(query, params)
            customers = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Statistiques basiques avec gestion d'erreurs
            try:
                stats = {
                    'total_customers': len(customers),
                    'active_customers': len([c for c in customers if len(c) > 9 and c[9] == 1]),  # is_active
                    'inactive_customers': len([c for c in customers if len(c) > 9 and c[9] == 0]),
                    'new_this_month': 0,  # TODO: calculer vraiment
                    'total_work_orders': 0,  # TODO: ajouter vraie requête
                    'total_revenue': 0.0  # TODO: ajouter vraie requête
                }
            except:
                stats = {
                    'total_customers': len(customers) if customers else 0,
                    'active_customers': 0,
                    'inactive_customers': 0,
                    'new_this_month': 0,
                    'total_work_orders': 0,
                    'total_revenue': 0.0
                }
            
            return render_template('customers/index.html', 
                                 customers=customers,
                                 pagination=pagination,
                                 search=search,
                                 sort_by=sort_by,
                                 sort_dir=sort_dir,
                                 stats=stats)
                                 
        except Exception as e:
            log_error(f"Erreur liste clients: {e}")
            flash('Erreur lors du chargement de la liste des clients', 'error')
            
            # Stats par défaut en cas d'erreur
            stats = {
                'total_customers': 0,
                'active_customers': 0,
                'inactive_customers': 0,
                'new_this_month': 0,
                'total_work_orders': 0,
                'total_revenue': 0.0
            }
            
            return render_template('customers/index.html', 
                                 customers=[], 
                                 pagination=None, 
                                 stats=stats)

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
                
                # Insérer le nouveau client
                cursor.execute("""
                    INSERT INTO customers (name, email, phone, mobile, company, address, city, postal_code, notes, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    form.name.data,
                    form.email.data,
                    form.phone.data,
                    form.mobile.data if hasattr(form, 'mobile') else None,
                    form.company.data,
                    form.address.data,
                    form.city.data,
                    form.postal_code.data,
                    form.notes.data
                ))
                
                customer_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                conn.close()
                
                log_info(f"Nouveau client créé: {form.name.data} (ID: {customer_id})")
                flash('Client ajouté avec succès', 'success')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
                
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
            # Récupérer le paramètre tab de l'URL
            active_tab = request.args.get('tab', 'profile')
            
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.index'))
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Récupérer les informations du client
            cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                flash('Client non trouvé', 'error')
                return redirect(url_for('customers.index'))
            
            # Assurer la compatibilité avec les anciens templates
            if 'customer_type' not in customer:
                customer['customer_type'] = 'individual'
            
            # Récupérer les bons de travail associés
            cursor.execute("""
                SELECT id, claim_number, description, status, priority, created_at, scheduled_date
                FROM work_orders 
                WHERE customer_id = %s 
                ORDER BY created_at DESC
                LIMIT 10
            """, (customer_id,))
            work_orders = cursor.fetchall()
            
            # Récupérer les véhicules
            cursor.execute("""
                SELECT id, make, model, year, vin, license_plate, notes 
                FROM vehicles 
                WHERE customer_id = %s 
                ORDER BY created_at DESC
            """, (customer_id,))
            vehicles = cursor.fetchall()
            
            # Récupérer les contacts
            cursor.execute("""
                SELECT * FROM customer_contacts 
                WHERE customer_id = %s 
                ORDER BY is_primary DESC, role, first_name, last_name
            """, (customer_id,))
            contacts = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Statistiques pour le template
            stats = {
                'total_work_orders': len(work_orders),
                'completed_work_orders': len([w for w in work_orders if w.get('status') == 'completed']),
                'total_spent': 0,
                'last_order_date': work_orders[0]['created_at'] if work_orders else None
            }
            
            # Données pour les onglets Customer 360
            customer_stats = {
                'total_orders': len(work_orders),
                'total_revenue': stats['total_spent'],
                'total_interventions': stats['total_work_orders'],
                'avg_rating': 4.2  # Placeholder
            }
            
            # Données analytics
            analytics_data = {
                'lifetime_value': stats['total_spent'],
                'avg_frequency': 2.5,  # Placeholder
                'avg_order_value': stats['total_spent'] / max(len(work_orders), 1),
                'satisfaction_score': 8.5,  # Placeholder
                'retention_rate': 85.0,  # Placeholder
                'repeat_rate': 65.0,  # Placeholder
                'churn_risk': 15.0,  # Placeholder
                'days_since_last_order': 30  # Placeholder
            }
            
            # Données pour les templates
            recent_work_orders = work_orders[:5]
            recent_activities = []
            customer_contacts = contacts
            monthly_orders_data = []
            priority_distribution = []
            activities = []  # Pour la section activity
            
            # Données pour l'onglet activity
            activity_stats = {
                'total_activities': len(recent_activities),
                'this_month': 0,
                'pending_tasks': 0
            }
            
            # Données pour l'onglet finances
            financial_summary = {
                'total_invoices': 0,
                'total_amount': stats['total_spent'],
                'paid_amount': 0,
                'outstanding_amount': 0,
                'average_payment_delay': 0
            }
            
            # Données pour l'onglet consents
            gdpr_status = {
                'compliant': True,
                'consents_valid': 85,
                'data_retention_days': 1095,
                'last_review_days': 30,
                'data_processing': True,
                'marketing': False,
                'third_party': False,
                'last_updated': '2024-01-15'
            }
            
            return render_template('customers/view.html',
                                 customer=customer,
                                 work_orders=work_orders,
                                 vehicles=vehicles,
                                 contacts=contacts,
                                 stats=stats,
                                 customer_stats=customer_stats,
                                 analytics_data=analytics_data,
                                 activity_stats=activity_stats,
                                 financial_summary=financial_summary,
                                 gdpr_status=gdpr_status,
                                 recent_work_orders=recent_work_orders,
                                 recent_activities=recent_activities,
                                 customer_contacts=customer_contacts,
                                 monthly_orders_data=monthly_orders_data,
                                 priority_distribution=priority_distribution,
                                 activities=activities,
                                 active_tab=active_tab)
                                 
        except Exception as e:
            log_error(f"Erreur affichage client {customer_id}: {e}")
            flash('Erreur lors du chargement du client', 'error')
            return redirect(url_for('customers.index'))

    @bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
    @require_role('admin', 'manager', 'staff')
    def edit_customer(customer_id):
        """Modifier un client"""
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Récupérer les informations actuelles
            cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                flash('Client non trouvé', 'error')
                return redirect(url_for('customers.index'))
            
            form = CustomerForm(obj=customer)
            
            if form.validate_on_submit():
                # Mettre à jour les informations
                cursor.execute("""
                    UPDATE customers SET 
                    name = %s, email = %s, phone = %s, mobile = %s,
                    company = %s, address = %s, city = %s, postal_code = %s,
                    notes = %s, updated_at = NOW()
                    WHERE id = %s
                """, (
                    form.name.data,
                    form.email.data,
                    form.phone.data,
                    form.mobile.data if hasattr(form, 'mobile') else None,
                    form.company.data,
                    form.address.data,
                    form.city.data,
                    form.postal_code.data,
                    form.notes.data,
                    customer_id
                ))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                log_info(f"Client modifié: {form.name.data} (ID: {customer_id})")
                flash('Client modifié avec succès', 'success')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
            
            cursor.close()
            conn.close()
            
            return render_template('customers/edit.html', form=form, customer=customer)
            
        except Exception as e:
            log_error(f"Erreur modification client {customer_id}: {e}")
            flash('Erreur lors de la modification du client', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))

    @bp.route('/<int:customer_id>/delete', methods=['POST'])
    @require_role('admin', 'manager')
    def delete_customer(customer_id):
        """Supprimer un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Vérifier que le client existe
            cursor.execute("SELECT name FROM customers WHERE id = %s", (customer_id,))
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Supprimer le client (attention aux contraintes de clés étrangères)
            cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_info(f"Client supprimé: {customer['name']} (ID: {customer_id})")
            
            return jsonify({
                'success': True,
                'message': f"Client {customer['name']} supprimé avec succès"
            })
            
        except pymysql.IntegrityError as e:
            log_error(f"Erreur contrainte lors suppression client {customer_id}: {e}")
            return jsonify({
                'success': False,
                'message': 'Impossible de supprimer le client : des données liées existent'
            }), 400
        except Exception as e:
            log_error(f"Erreur suppression client {customer_id}: {e}")
            return jsonify({'success': False, 'message': 'Erreur lors de la suppression'}), 500

    @bp.route('/api/search')
    def search_customers_api():
        """API de recherche de clients"""
        try:
            query = request.args.get('q', '')
            limit = min(request.args.get('limit', 10, type=int), 50)
            
            if len(query) < 2:
                return jsonify({'customers': []})
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'error': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("""
                SELECT id, name, email, company, city
                FROM customers
                WHERE name LIKE %s OR email LIKE %s OR company LIKE %s
                ORDER BY name
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            customers = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({'customers': customers})
            
        except Exception as e:
            log_error(f"Erreur recherche clients: {e}")
            return jsonify({'error': 'Erreur lors de la recherche'}), 500

    # Routes de compatibilité pour les anciens templates
    @bp.route('/<int:id>/view')
    def view_customer_legacy(id):
        """Route de compatibilité pour l'ancien système"""
        return redirect(url_for('customers.view_customer', customer_id=id))

    @bp.route('/<int:id>/actions/delete', methods=['POST'])
    @require_role('admin', 'manager')
    def delete_customer_legacy(id):
        """Route de compatibilité pour la suppression"""
        return delete_customer(id)

    @bp.route('/<int:id>/export', methods=['GET'])
    def export_customer_legacy(id):
        """Route de compatibilité pour l'export"""
        return redirect(url_for('customers.view_customer', customer_id=id))

    @bp.route('/alt')
    def alt_index():
        """Vue alternative de la liste des clients"""
        return index()
