"""
Routes principales CRUD pour les clients
"""

import pymysql
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from core.forms import CustomerForm
from core.utils import log_info, log_error, validate_customer_data, ValidationError
from .utils import get_db_connection, require_role, get_current_user, MiniPagination, _debug


def setup_main_routes(bp):
    """Configure les routes principales du module clients"""
    
    @bp.route('/')
    @require_role('admin', 'manager', 'staff', 'readonly')
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
            
            # Récupérer les clients avec pagination
            query = f"""
                SELECT id, name, email, phone, company, city, status, created_at, last_activity_date,
                       CASE WHEN is_active IS NOT NULL THEN is_active ELSE 1 END as is_active
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
    @require_role('admin', 'manager', 'staff')
    def add_customer():
        """Ajouter un nouveau client avec validation complète"""
        form = CustomerForm()
        
        if request.method == 'POST':
            try:
                # Validation des données avec la nouvelle fonction
                customer_data = {
                    'name': request.form.get('name', '').strip(),
                    'email': request.form.get('email', '').strip(),
                    'phone': request.form.get('phone', '').strip(),
                    'mobile': request.form.get('mobile', '').strip(),
                    'company': request.form.get('company', '').strip(),
                    'customer_type': request.form.get('customer_type', 'individual'),
                    'siret': request.form.get('siret', '').strip(),
                    'address': request.form.get('address', '').strip(),
                    'city': request.form.get('city', '').strip(),
                    'postal_code': request.form.get('postal_code', '').strip(),
                    'status': request.form.get('status', 'active'),
                    'birth_date': request.form.get('birth_date', ''),
                    'billing_address_different': request.form.get('billing_address_different', 'false'),
                    'billing_address': request.form.get('billing_address', '').strip(),
                    'billing_city': request.form.get('billing_city', '').strip(),
                    'billing_postal_code': request.form.get('billing_postal_code', '').strip(),
                    'notes': request.form.get('notes', '').strip()
                }
                
                # Validation métier
                validate_customer_data(customer_data, is_update=False)
                
                conn = get_db_connection()
                if not conn:
                    flash('Erreur de connexion à la base de données', 'error')
                    return render_template('customers/add.html', form=form)
                
                cursor = conn.cursor()
                
                # Vérifier l'unicité de l'email si fourni
                if customer_data['email']:
                    cursor.execute("SELECT id FROM customers WHERE email = %s", (customer_data['email'],))
                    if cursor.fetchone():
                        flash('Un client avec cet email existe déjà', 'error')
                        cursor.close()
                        conn.close()
                        return render_template('customers/add.html', form=form)
                
                # Insérer le nouveau client
                cursor.execute("""
                    INSERT INTO customers (
                        name, email, phone, mobile, company, customer_type, siret,
                        address, city, postal_code, status,
                        billing_address, notes, created_at, updated_at, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 1)
                """, (
                    customer_data['name'],
                    customer_data['email'] or None,
                    customer_data['phone'] or None,
                    customer_data['mobile'] or None,
                    customer_data['company'] or None,
                    customer_data['customer_type'],
                    customer_data['siret'] or None,
                    customer_data['address'] or None,
                    customer_data['city'] or None,
                    customer_data['postal_code'] or None,
                    customer_data['status'],
                    customer_data['billing_address'] or None,
                    customer_data['notes'] or None
                ))
                
                customer_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                conn.close()
                
                log_info(f"Nouveau client créé: {customer_data['name']} (ID: {customer_id})")
                flash('Client ajouté avec succès', 'success')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
                
            except ValidationError as e:
                flash(f'Erreur de validation: {str(e)}', 'error')
                log_error(f"Erreur de validation client: {e}")
            except pymysql.IntegrityError as e:
                log_error(f"Erreur d'intégrité lors de l'ajout du client: {e}")
                flash('Erreur d\'intégrité des données (doublon détecté)', 'error')
            except Exception as e:
                log_error(f"Erreur lors de l'ajout du client: {e}")
                flash('Erreur lors de l\'ajout du client', 'error')
        
        return render_template('customers/add.html', form=form)

    @bp.route('/<int:customer_id>')
    @require_role('admin', 'manager', 'staff', 'readonly')
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
            
            if request.method == 'POST':
                # Extraire et préparer les données du formulaire
                customer_data = {
                    'name': request.form.get('name', '').strip(),
                    'email': request.form.get('email', '').strip(),
                    'phone': request.form.get('phone', '').strip(),
                    'mobile': request.form.get('mobile', '').strip(),
                    'company': request.form.get('company', '').strip(),
                    'address': request.form.get('address', '').strip(),
                    'city': request.form.get('city', '').strip(),
                    'postal_code': request.form.get('postal_code', '').strip(),
                    'country': request.form.get('country', 'FR').strip(),
                    'customer_type': request.form.get('customer_type', 'particulier').strip(),
                    'siret': request.form.get('siret', '').strip(),
                    'tax_number': request.form.get('tax_number', '').strip(),
                    'notes': request.form.get('notes', '').strip(),
                    'is_active': request.form.get('is_active') == '1',
                    'preferred_contact': request.form.get('preferred_contact', 'email')
                }
                
                # Validation des données avec la nouvelle fonction
                try:
                    # Valider les données avec les règles métier
                    validate_customer_data(customer_data)
                    
                    # Vérifier l'unicité de l'email (sauf pour ce client)
                    if customer_data['email']:
                        cursor.execute(
                            "SELECT id FROM customers WHERE email = %s AND id != %s", 
                            (customer_data['email'], customer_id)
                        )
                        if cursor.fetchone():
                            raise ValidationError("Cette adresse email est déjà utilisée par un autre client")
                    
                    
                    # Mettre à jour les informations avec gestion complète des champs
                    cursor.execute("""
                        UPDATE customers SET 
                        name = %s, email = %s, phone = %s, mobile = %s,
                        company = %s, address = %s, city = %s, postal_code = %s,
                        country = %s, customer_type = %s, siret = %s, tax_number = %s,
                        notes = %s, is_active = %s,
                        preferred_contact_method = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (
                        customer_data['name'],
                        customer_data['email'] or None,
                        customer_data['phone'] or None,
                        customer_data['mobile'] or None,
                        customer_data['company'] or None,
                        customer_data['address'] or None,
                        customer_data['city'] or None,
                        customer_data['postal_code'] or None,
                        customer_data['country'],
                        customer_data['customer_type'],
                        customer_data['siret'] or None,
                        customer_data['tax_number'] or None,
                        customer_data['notes'] or None,
                        customer_data['is_active'],
                        customer_data['preferred_contact'],
                        customer_id
                    ))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    log_info(f"Client modifié: {customer_data['name']} (ID: {customer_id})")
                    flash('Client modifié avec succès', 'success')
                    return redirect(url_for('customers.view_customer', customer_id=customer_id))
                    
                except ValidationError as e:
                    cursor.close()
                    conn.close()
                    flash(f'Erreur de validation: {str(e)}', 'error')
                    return render_template('customers/edit.html', customer=customer, errors=[str(e)])
                    
                except Exception as e:
                    cursor.close()
                    conn.close()
                    log_error(f"Erreur modification client: {e}")
                    flash('Erreur lors de la modification du client', 'error')
                    return render_template('customers/edit.html', customer=customer, errors=[str(e)])
            
            # GET request - afficher le formulaire
            cursor.close()
            conn.close()
            
            return render_template('customers/edit.html', customer=customer)
            
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
    @require_role('admin', 'manager', 'staff', 'readonly')
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
    @require_role('admin', 'manager', 'staff', 'readonly')
    def view_customer_legacy(id):
        """Route de compatibilité pour l'ancien système"""
        return redirect(url_for('customers.view_customer', customer_id=id))

    @bp.route('/<int:id>/actions/delete', methods=['POST'])
    @require_role('admin', 'manager')
    def delete_customer_legacy(id):
        """Route de compatibilité pour la suppression"""
        return delete_customer(id)

    @bp.route('/<int:id>/export', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def export_customer_legacy(id):
        """Route de compatibilité pour l'export"""
        return redirect(url_for('customers.view_customer', customer_id=id))

    @bp.route('/alt')
    @require_role('admin', 'manager', 'staff', 'readonly')
    def alt_index():
        """Vue alternative de la liste des clients"""
        return index()
