"""
Routes pour la gestion des bons de travail (Work Orders)
Basé sur le PRD Fusionné v2.0 - Architecture moderne avec IA
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from core.forms import WorkOrderForm
from core.config import get_db_config
import pymysql
import logging
from datetime import datetime, timedelta
import json
import os
from functools import wraps

# Import de l'utilitaire de pagination et authentification
from utils.pagination import Pagination, paginate_query
from utils.auth import login_required as requires_auth

# Configuration du logging
logger = logging.getLogger(__name__)

bp = Blueprint('work_orders', __name__)

def get_db_connection():
    """Connexion à la base de données avec configuration centralisée"""
    try:
        cfg = get_db_config()
        conn = pymysql.connect(**cfg)
        logger.debug("✅ Connexion DB work_orders établie")
        return conn
    except Exception as e:
        logger.error(f"❌ Erreur connexion DB work_orders: {e}")
        return None

@bp.route('/')
@requires_auth
def index():
    """Liste des bons de travail avec filtres avancés et pagination"""
    try:
        # Récupération des paramètres de filtre et pagination
        status_filter = request.args.get('status', 'all')
        priority_filter = request.args.get('priority', 'all')
        technician_filter = request.args.get('technician', 'all')
        search_query = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        view_mode = request.args.get('view', 'cards')  # cards ou table
        
        # Normalisation des paramètres vides vers 'all'
        if not status_filter or status_filter.strip() == '':
            status_filter = 'all'
        if not priority_filter or priority_filter.strip() == '':
            priority_filter = 'all' 
        if not technician_filter or technician_filter.strip() == '':
            technician_filter = 'all'
        if not search_query:
            search_query = ''
        
        # Paramètres de pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)  # 20 éléments par page par défaut
        per_page = max(5, min(100, per_page))  # Limite entre 5 et 100
        
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return render_template('error.html', message="Problème de connexion à la base de données")
        
        try:
            with conn.cursor() as cursor:
                # Construction de la requête avec filtres
                where_conditions = []
                params = []
                
                # Filtres de base - Vérification plus stricte
                if status_filter and status_filter != 'all' and status_filter.strip():
                    where_conditions.append("wo.status = %s")
                    params.append(status_filter)
                
                if priority_filter and priority_filter != 'all' and priority_filter.strip():
                    where_conditions.append("wo.priority = %s")
                    params.append(priority_filter)
                
                if technician_filter and technician_filter != 'all' and technician_filter.strip():
                    where_conditions.append("wo.assigned_technician_id = %s")
                    params.append(technician_filter)
                
                # Recherche textuelle
                if search_query and search_query.strip():
                    where_conditions.append("""
                        (wo.claim_number LIKE %s 
                         OR wo.customer_name LIKE %s 
                         OR wo.description LIKE %s
                         OR c.name LIKE %s)
                    """)
                    search_param = f"%{search_query.strip()}%"
                    params.extend([search_param, search_param, search_param, search_param])
                
                # Filtres de date
                if date_from and date_from.strip():
                    where_conditions.append("DATE(wo.created_at) >= %s")
                    params.append(date_from)
                
                if date_to and date_to.strip():
                    where_conditions.append("DATE(wo.created_at) <= %s")
                    params.append(date_to)
                
                # Restriction selon le rôle
                user_role = session.get('user_role')
                if user_role == 'technician':
                    where_conditions.append("wo.assigned_technician_id = %s")
                    params.append(session.get('user_id'))
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                # Debug temporaire pour la pagination
                logger.info(f"🔍 PAGINATION DEBUG: page={page}, per_page={per_page}")
                logger.info(f"🔍 FILTRES DEBUG: status='{status_filter}', priority='{priority_filter}', technician='{technician_filter}', search='{search_query}'")
                logger.info(f"🔍 WHERE DEBUG: {where_clause}")
                logger.info(f"🔍 PARAMS DEBUG: {params}")
                
                # Requête principale pour la pagination
                base_query = f"""
                    SELECT 
                        wo.*,
                        u.name as technician_name,
                        c.name as customer_full_name,
                        c.phone as customer_phone_contact,
                        c.email as customer_email_contact,
                        creator.name as created_by_name,
                        COUNT(wop.id) as products_count,
                        COUNT(wol.id) as lines_count,
                        COALESCE(SUM(wol.MONTANT), 0) as total_amount,
                        COUNT(CASE WHEN wol.STATUS = 'A' THEN 1 END) as active_lines,
                        DATEDIFF(NOW(), wo.created_at) as days_old,
                        CASE 
                            WHEN wo.scheduled_date IS NOT NULL THEN wo.scheduled_date
                            ELSE wo.created_at 
                        END as sort_date
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN users creator ON wo.created_by_user_id = creator.id
                    LEFT JOIN work_order_products wop ON wo.id = wop.work_order_id
                    LEFT JOIN work_order_lines wol ON wo.id = wol.work_order_id
                    {where_clause}
                    GROUP BY wo.id
                    ORDER BY 
                        FIELD(wo.priority, 'urgent', 'high', 'medium', 'low'),
                        sort_date DESC
                """
                
                # Requête de comptage spécifique pour la pagination
                count_query = f"""
                    SELECT COUNT(DISTINCT wo.id) as total
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN users creator ON wo.created_by_user_id = creator.id
                    LEFT JOIN work_order_products wop ON wo.id = wop.work_order_id
                    LEFT JOIN work_order_lines wol ON wo.id = wol.work_order_id
                    {where_clause}
                """
                
                # Application de la pagination
                pagination = paginate_query(cursor, base_query, params, page, per_page, count_query)
                work_orders = pagination.items
                
                # Récupération des données pour les filtres
                cursor.execute("SELECT id, name FROM users WHERE role IN ('technician', 'supervisor')")
                technicians = cursor.fetchall()
                
                # Statistiques pour le dashboard
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent,
                        AVG(actual_duration) as avg_duration,
                        SUM(actual_cost) as total_revenue
                    FROM work_orders
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                stats = cursor.fetchone()
                
                return render_template('work_orders/index.html',
                                     work_orders=work_orders,
                                     technicians=technicians,
                                     stats=stats,
                                     pagination=pagination,
                                     filters={
                                         'status': status_filter,
                                         'priority': priority_filter,
                                         'technician': technician_filter,
                                         'search': search_query,
                                         'date_from': date_from,
                                         'date_to': date_to,
                                         'view': view_mode,
                                         'per_page': per_page
                                     })
        
        except Exception as e:
            logger.error(f"❌ Erreur liste work_orders: {e}")
            flash('Erreur lors du chargement des bons de travail', 'error')
            return render_template('error.html', message="Erreur technique")
        finally:
            if conn:
                conn.close()
    
    except Exception as e:
        logger.error(f"❌ Erreur générale work_orders: {e}")
        flash('Erreur technique', 'error')
        return render_template('error.html', message="Problème technique")



# Alias de rétrocompatibilité
@bp.route('/list')
@requires_auth
def list_work_orders():
    """Alias de rétrocompatibilité pour list_work_orders"""
    return index()

@bp.route('/<int:id>/products', methods=['POST'])
def add_work_order_product(id):
    """Endpoint simple pour ajouter une pièce à un bon de travail via formulaire POST."""
    try:
        product_name = request.form.get('product_name')
        product_reference = request.form.get('product_reference')
        quantity = request.form.get('quantity') or 1
        unit_price = request.form.get('unit_price') or None
        notes = request.form.get('notes') or None

        if not product_name:
            flash('Le nom de la pièce est requis', 'error')
            return redirect(url_for('work_orders.view_work_order', id=id))

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO work_order_products (work_order_id, product_name, product_reference, quantity, unit_price, total_price, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    id,
                    product_name,
                    product_reference,
                    float(quantity),
                    float(unit_price) if unit_price else None,
                    (float(quantity) * float(unit_price)) if unit_price else None,
                    notes,
                ),
            )
            conn.commit()
        conn.close()
        flash('Pièce ajoutée au bon de travail', 'success')
        return redirect(url_for('work_orders.view_work_order', id=id))
    except Exception as e:
        flash(f"Erreur lors de l'ajout de la pièce: {e}", 'error')
        return redirect(url_for('work_orders.view_work_order', id=id))

@bp.route('/create', methods=['GET', 'POST'])
def create_work_order():
    """Créer un nouveau bon de travail"""
    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion à la base de données', 'error')
        return render_template('error.html', message="Problème de connexion à la base de données")
    
    form = WorkOrderForm()
    
    try:
        # Récupération des données pour les champs liés
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM customers ORDER BY name")
            customers = cursor.fetchall()
            cursor.execute("SELECT id, name FROM users WHERE role IN ('technician', 'supervisor')")
            technicians = cursor.fetchall()
        
        # Remplir les choices pour les champs liés
        form.customer_id.choices = [(c['id'], c['name']) for c in customers]
        form.technician_id.choices = [(0, '---')] + [(t['id'], t['name']) for t in technicians]
        
        # Pré-sélectionner le client si customer_id est fourni en query string
        req_customer_id = request.args.get('customer_id') or request.form.get('customer_id')
        if req_customer_id:
            # ensure the value exists in the choices
            choice_values = [c[0] for c in form.customer_id.choices]
            try:
                req_c_int = int(req_customer_id)
            except Exception:
                req_c_int = None
            if req_c_int is not None and req_c_int in choice_values:
                form.customer_id.data = req_c_int
                # Verify the customer has vehicle information before allowing creation
                try:
                    cursor.execute("SELECT vehicle_info FROM customers WHERE id = %s", (int(req_customer_id),))
                    cust_row = cursor.fetchone()
                    if not cust_row or not cust_row.get('vehicle_info'):
                        flash("Le client n'a pas de véhicule enregistré. Veuillez ajouter un véhicule avant de créer un bon de travail.", 'error')
                        return redirect(url_for('customers.edit_customer', customer_id=int(req_customer_id)))
                except Exception as e:
                    print(f"Erreur vérification véhicule: {e}")
                    pass
        
        # Load vehicles for the selected customer to populate the vehicle select in the form
        vehicles = []
        if req_customer_id:
            try:
                cursor.execute("SELECT id, make, model, year, vin, license_plate FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC", (int(req_customer_id),))
                vehicles = cursor.fetchall()
            except Exception as e:
                print(f"Erreur chargement véhicules: {e}")
                vehicles = []
        
        # Populate form vehicle choices and pre-select if vehicle_id provided in query
        try:
            # vehicle_id SelectField uses coerce=int, provide integer choice values; 0 means blank
            form.vehicle_id.choices = [(0, '---')] + [ (v['id'], f"{v.get('make','')} {v.get('model','')} {v.get('license_plate','')}") for v in vehicles ]
        except Exception:
            # If form.vehicle_id doesn't exist or choices assignment fails, ignore
            pass
            
        # Pre-select vehicle if provided (use int types)
        req_vehicle_id = request.args.get('vehicle_id') or request.form.get('vehicle_id')
        if req_vehicle_id:
            try:
                req_v_int = int(req_vehicle_id)
                if req_v_int in [c[0] for c in form.vehicle_id.choices]:
                    form.vehicle_id.data = req_v_int
            except Exception:
                pass
                
        # Pré-sélectionner le technicien si fourni
        req_technician_id = request.args.get('technician_id') or request.form.get('technician_id')
        if req_technician_id:
            try:
                req_t_int = int(req_technician_id)
            except Exception:
                req_t_int = None
            tech_values = [t[0] for t in form.technician_id.choices if t[0] != 0]
            if req_t_int is not None and req_t_int in tech_values:
                form.technician_id.data = req_t_int
                
        # Compute a preview claim number for the form (useful on GET)
        claim_number = None
        try:
            # Use a short-lived connection to count today's work orders
            cursor.execute("SELECT COUNT(*) as count FROM work_orders WHERE DATE(created_at) = CURDATE()")
            row = cursor.fetchone()
            daily_count = (row['count'] if row and 'count' in row and row['count'] is not None else 0) + 1
            claim_number = f"WO{datetime.now().strftime('%Y%m%d')}-{daily_count:03d}"
        except Exception:
            # Fallback to a deterministic default if DB is unavailable
            claim_number = f"WO{datetime.now().strftime('%Y%m%d')}-001"
            
    except Exception as e:
        flash(f'Erreur lors de la préparation du formulaire: {e}', 'error')
        claim_number = f"WO{datetime.now().strftime('%Y%m%d')}-001"
        customers = []
        technicians = []
        vehicles = []
    finally:
        if conn:
            conn.close()
    if form.validate_on_submit():
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return render_template('work_orders/add.html', form=form, 
                                 customers=customers, technicians=technicians, 
                                 vehicles=vehicles, claim_number=claim_number)
        
        try:
            with conn.cursor() as cursor:
                # Ensure the selected customer has vehicle information before creating the work order
                cust_id_int = int(form.customer_id.data) if form.customer_id.data else None
                if cust_id_int:
                    cursor.execute("SELECT vehicle_info FROM customers WHERE id = %s", (cust_id_int,))
                    cust_row = cursor.fetchone()
                    if not cust_row or not cust_row.get('vehicle_info'):
                        flash("Le client n'a pas de véhicule enregistré. Ajoutez un véhicule avant de créer un bon de travail.", 'error')
                        return redirect(url_for('customers.edit_customer', customer_id=cust_id_int))

                # Calculate claim number
                cursor.execute("SELECT COUNT(*) as count FROM work_orders WHERE DATE(created_at) = CURDATE()")
                daily_count = cursor.fetchone()['count'] + 1
                claim_number = f"WO{datetime.now().strftime('%Y%m%d')}-{daily_count:03d}"
                internal_notes_value = request.form.get('internal_notes') if request.form.get('internal_notes') is not None else ''
                
                # capture vehicle selection if present
                vehicle_id_to_save = request.form.get('vehicle_id') or None
                try:
                    vehicle_id_to_save = int(vehicle_id_to_save) if vehicle_id_to_save else None
                except Exception:
                    vehicle_id_to_save = None
                    
                cursor.execute("""
                    INSERT INTO work_orders (
                        claim_number, customer_id, vehicle_id, description, priority, 
                        estimated_duration, estimated_cost, scheduled_date,
                        assigned_technician_id, created_by_user_id, notes, internal_notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    claim_number,
                    form.customer_id.data,
                    vehicle_id_to_save,
                    form.description.data,
                    form.status.data or 'medium',
                    None,  # estimated_duration
                    None,  # estimated_cost
                    form.due_date.data,
                    form.technician_id.data or None,
                    session.get('user_id'),
                    form.notes.data or '',
                    internal_notes_value or ''
                ))
                work_order_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO work_order_status_history (
                        work_order_id, old_status, new_status, 
                        changed_by_user_id, change_reason
                    ) VALUES (%s, NULL, 'draft', %s, 'Création initiale')
                """, (work_order_id, session.get('user_id')))
                if form.technician_id.data:
                    cursor.execute("""
                        INSERT INTO notifications (
                            user_id, title, message, type, related_id, related_type
                        ) VALUES (%s, %s, %s, 'work_order', %s, 'work_order')
                    """, (
                        form.technician_id.data,
                        'Nouveau travail assigné',
                        f'Le bon de travail {claim_number} vous a été assigné',
                        work_order_id
                    ))
                conn.commit()
                flash(f'Bon de travail {claim_number} créé avec succès', 'success')
                is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
                if is_ajax:
                    return jsonify({'success': True, 'id': work_order_id, 'url': url_for('work_orders.view_work_order', id=work_order_id)})
                return redirect(url_for('work_orders.view_work_order', id=work_order_id))
        except Exception as e:
            flash(f'Erreur lors de la création: {str(e)}', 'error')
        finally:
            conn.close()
    return render_template('work_orders/add.html', form=form, customers=customers, technicians=technicians, vehicles=vehicles, claim_number=claim_number)

@bp.route('/<int:id>')
def view_work_order(id):
    """Affichage détaillé d'un bon de travail"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupération du bon de travail
            cursor.execute("""
                SELECT 
                    wo.*,
                    u.name as technician_name,
                    u.email as technician_email,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.email as customer_email,
                    c.address as customer_address,
                    creator.name as created_by_name
                FROM work_orders wo
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users creator ON wo.created_by_user_id = creator.id
                WHERE wo.id = %s
            """, (id,))
            
            work_order = cursor.fetchone()
            if not work_order:
                flash('Bon de travail non trouvé', 'error')
                return redirect(url_for('work_orders.index'))
            
            # Vérification des permissions
            user_role = session.get('user_role')
            if user_role == 'technician' and work_order['assigned_technician_id'] != session.get('user_id'):
                flash('Accès non autorisé', 'error')
                return redirect(url_for('work_orders.index'))
            
            # Lignes du bon de travail
            cursor.execute("""
                SELECT * FROM work_order_lines 
                WHERE work_order_id = %s 
                ORDER BY line_order, id
            """, (id,))
            work_order_lines = cursor.fetchall()
            
            # Produits associés
            cursor.execute("""
                SELECT * FROM work_order_products 
                WHERE work_order_id = %s 
                ORDER BY created_at
            """, (id,))
            products = cursor.fetchall()
            
            # Notes d'intervention
            cursor.execute("""
                SELECT 
                    in_.*,
                    u.name as technician_name
                FROM intervention_notes in_
                JOIN users u ON in_.technician_id = u.id
                WHERE in_.work_order_id = %s
                ORDER BY in_.created_at DESC
            """, (id,))
            notes = cursor.fetchall()
            
            # Médias (photos, vidéos, audio)
            cursor.execute("""
                SELECT 
                    im.*,
                    u.name as technician_name
                FROM intervention_media im
                JOIN users u ON im.technician_id = u.id
                WHERE im.work_order_id = %s
                ORDER BY im.created_at DESC
            """, (id,))
            media = cursor.fetchall()
            
            # Historique des statuts
            cursor.execute("""
                SELECT 
                    wsh.*,
                    u.name as changed_by_name
                FROM work_order_status_history wsh
                JOIN users u ON wsh.changed_by_user_id = u.id
                WHERE wsh.work_order_id = %s
                ORDER BY wsh.created_at DESC
            """, (id,))
            status_history = cursor.fetchall()
            
            # Calculs financiers
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_lines,
                    SUM(MONTANT) as total_amount,
                    SUM(CASE WHEN STATUS = 'A' THEN MONTANT ELSE 0 END) as active_amount,
                    SUM(CASE WHEN STATUS = 'F' THEN MONTANT ELSE 0 END) as billed_amount
                FROM work_order_lines 
                WHERE work_order_id = %s
            """, (id,))
            financial_summary = cursor.fetchone()
            
            # Fetch full customer record if available for template convenience
            customer = None
            try:
                if work_order.get('customer_id'):
                    cursor.execute("SELECT * FROM customers WHERE id = %s", (work_order.get('customer_id'),))
                    customer = cursor.fetchone()
            except Exception:
                customer = None

            # Compute simple progress percentage based on status (fallback)
            status_map = {
                'draft': 0,
                'pending': 10,
                'assigned': 40,
                'in_progress': 70,
                'completed': 100,
                'cancelled': 0
            }
            progress_percentage = status_map.get(work_order.get('status'), 0)

            # derive durations and cost summaries
            actual_duration = work_order.get('actual_duration') if work_order.get('actual_duration') is not None else 0
            total_estimated_cost = financial_summary.get('total_amount') if financial_summary and financial_summary.get('total_amount') is not None else 0
            total_actual_cost = work_order.get('actual_cost') if work_order.get('actual_cost') is not None else 0

            return render_template('work_orders/view.html',
                                 work_order=work_order,
                                 work_order_lines=work_order_lines,
                                 products=products,
                                 intervention_notes=notes,
                                 media_files=media,
                                 status_history=status_history,
                                 financial_summary=financial_summary,
                                 customer=customer,
                                 progress_percentage=progress_percentage,
                                 actual_duration=actual_duration,
                                 total_estimated_cost=total_estimated_cost,
                                 total_actual_cost=total_actual_cost)
    finally:
        conn.close()

@bp.route('/delete_media', methods=['POST'])
def delete_media():
    """Supprimer un fichier média d'un bon de travail"""
    try:
        media_id = request.json.get('media_id')
        if not media_id:
            return jsonify({'success': False, 'message': 'ID du média manquant'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les informations du fichier avant suppression
        cursor.execute("""
            SELECT file_path, work_order_id 
            FROM work_order_media 
            WHERE id = %s
        """, (media_id,))
        
        media_info = cursor.fetchone()
        if not media_info:
            return jsonify({'success': False, 'message': 'Média non trouvé'})
        
        file_path, work_order_id = media_info
        
        # Supprimer le fichier physique
        try:
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Erreur suppression fichier: {e}")
        
        # Supprimer l'enregistrement de la base de données
        cursor.execute("DELETE FROM work_order_media WHERE id = %s", (media_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Média supprimé avec succès'})
        
    except Exception as e:
        print(f"Erreur lors de la suppression du média: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression'})


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_work_order(id):
    """Modifier un bon de travail existant"""
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            # Traitement de la modification
            description = request.form.get('description')
            priority = request.form.get('priority', 'medium')
            status = request.form.get('status')
            assigned_technician_id = request.form.get('assigned_technician_id')
            customer_id = request.form.get('customer_id')
            scheduled_date = request.form.get('scheduled_date')
            location_address = request.form.get('location_address')
            location_latitude = request.form.get('location_latitude')
            location_longitude = request.form.get('location_longitude')
            internal_notes = request.form.get('internal_notes')
            public_notes = request.form.get('notes')
            estimated_duration = request.form.get('estimated_duration')
            estimated_cost = request.form.get('estimated_cost')
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE work_orders 
                    SET description = %s, priority = %s, status = %s, assigned_technician_id = %s, 
                        customer_id = %s, scheduled_date = %s, location_address = %s,
                        location_latitude = %s, location_longitude = %s, internal_notes = %s,
                        notes = %s, estimated_duration = %s, estimated_cost = %s, updated_at = NOW()
                    WHERE id = %s
                """, (description, priority, status, assigned_technician_id or None, 
                      customer_id or None, scheduled_date or None, location_address,
                      location_latitude or None, location_longitude or None, internal_notes,
                      public_notes or '', estimated_duration or None, estimated_cost or None, id))
                conn.commit()
                
            flash('Bon de travail modifié avec succès', 'success')
            return redirect(url_for('work_orders.view_work_order', id=id))
        
        # GET - Affichage du formulaire d'édition
        with conn.cursor() as cursor:
            # Récupération du bon de travail avec toutes les informations
            cursor.execute("""
                SELECT wo.*, c.name as customer_name, u.name as technician_name,
                       creator.name as created_by_name
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                LEFT JOIN users creator ON wo.created_by_user_id = creator.id
                WHERE wo.id = %s
            """, (id,))
            work_order = cursor.fetchone()
            
            if not work_order:
                flash('Bon de travail introuvable', 'error')
                return redirect(url_for('work_orders.index'))
            
            # Récupération des techniciens actifs
            cursor.execute("""
                SELECT id, name, email, 
                       CASE 
                           WHEN role = 'technician' THEN 'Technicien'
                           WHEN role = 'supervisor' THEN 'Superviseur'
                           ELSE role 
                       END as specialization
                FROM users 
                WHERE role IN ('technician', 'supervisor') AND is_active = 1
                ORDER BY name
            """)
            technicians = cursor.fetchall()
            
            # Récupération des clients actifs
            cursor.execute("""
                SELECT id, name, email, phone, address 
                FROM customers 
                WHERE is_active = 1 
                ORDER BY name
            """)
            customers = cursor.fetchall()
            
            # Récupération des fichiers médias associés (avec gestion d'erreur)
            media_files = []
            try:
                cursor.execute("""
                    SELECT id, filename, original_filename, file_type, created_at
                    FROM work_order_media 
                    WHERE work_order_id = %s
                    ORDER BY created_at DESC
                """, (id,))
                media_files = cursor.fetchall()
            except Exception as e:
                print(f"Erreur lors de la récupération des médias: {e}")
                media_files = []
            
            # Création d'un objet form factice pour compatibilité avec le template
            class FakeForm:
                def __init__(self):
                    self.hidden_tag = lambda: ''
                    
                def create_field(self, name, value=''):
                    class Field:
                        def __init__(self, name, value):
                            self.name = name
                            self.data = value
                            self.errors = []
                        def __call__(self, **kwargs):
                            attrs = ' '.join([f'{k}="{v}"' for k, v in kwargs.items()])
                            if 'class' in kwargs and 'form-control' in kwargs['class']:
                                return f'<input name="{self.name}" value="{self.data}" {attrs}>'
                            elif 'class' in kwargs and 'form-select' in kwargs['class']:
                                return f'<select name="{self.name}" {attrs}></select>'
                            else:
                                return f'<textarea name="{self.name}" {attrs}>{self.data}</textarea>'
                        def label(self, **kwargs):
                            label_text = self.name.replace('_', ' ').title()
                            return f'<label for="{self.name}" {" ".join([f"{k}=\"{v}\"" for k, v in kwargs.items()])}>{label_text}</label>'
                    return Field(name, value)
                    
            form = FakeForm()
            form.claim_number = form.create_field('claim_number', work_order.get('claim_number', ''))
            form.customer_id = form.create_field('customer_id', work_order.get('customer_id', ''))
            form.priority = form.create_field('priority', work_order.get('priority', 'medium'))
            form.status = form.create_field('status', work_order.get('status', 'pending'))
            form.assigned_technician_id = form.create_field('assigned_technician_id', work_order.get('assigned_technician_id', ''))
            form.scheduled_date = form.create_field('scheduled_date', work_order.get('scheduled_date', ''))
            form.description = form.create_field('description', work_order.get('description', ''))
            form.internal_notes = form.create_field('internal_notes', work_order.get('internal_notes', ''))
            form.location_address = form.create_field('location_address', work_order.get('location_address', ''))
            form.location_latitude = form.create_field('location_latitude', work_order.get('location_latitude', ''))
            form.location_longitude = form.create_field('location_longitude', work_order.get('location_longitude', ''))
            form.estimated_duration = form.create_field('estimated_duration', work_order.get('estimated_duration', ''))
            form.estimated_cost = form.create_field('estimated_cost', work_order.get('estimated_cost', ''))
            
            return render_template('work_orders/edit.html',
                                 work_order=work_order,
                                 form=form,
                                 technicians=technicians,
                                 customers=customers,
                                 media_files=media_files)
    finally:
        conn.close()

@bp.route('/<int:id>/update_status', methods=['POST'])
def update_status(id):
    """Mettre à jour le statut d'un bon de travail"""
    new_status = request.form.get('status')
    reason = request.form.get('reason', '')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Récupération du statut actuel
            cursor.execute("SELECT status, assigned_technician_id FROM work_orders WHERE id = %s", (id,))
            current = cursor.fetchone()
            if not current:
                return jsonify({'success': False, 'message': 'Bon de travail non trouvé'})
            
            old_status = current['status']
            
            # Mise à jour du statut
            update_data = {'status': new_status}
            
            # Actions automatiques selon le statut
            if new_status == 'in_progress':
                update_data['start_time'] = datetime.now()
            elif new_status == 'completed':
                update_data['completion_date'] = datetime.now()
                # Calculer la durée réelle si pas déjà définie
                cursor.execute("SELECT start_time FROM work_orders WHERE id = %s", (id,))
                wo = cursor.fetchone()
                if wo and wo['start_time']:
                    duration = datetime.now() - wo['start_time']
                    update_data['actual_duration'] = int(duration.total_seconds() / 60)
            
            # Mise à jour des champs
            set_clause = ', '.join([f"{k} = %s" for k in update_data.keys()])
            values = list(update_data.values()) + [id]
            
            cursor.execute(f"""
                UPDATE work_orders 
                SET {set_clause}
                WHERE id = %s
            """, values)
            
            # Historique de statut
            cursor.execute("""
                INSERT INTO work_order_status_history (
                    work_order_id, old_status, new_status, 
                    changed_by_user_id, change_reason
                ) VALUES (%s, %s, %s, %s, %s)
            """, (id, old_status, new_status, session.get('user_id'), reason))
            
            # Notification du technicien si changement par superviseur
            if (current['assigned_technician_id'] and 
                current['assigned_technician_id'] != session.get('user_id')):
                cursor.execute("""
                    INSERT INTO notifications (
                        user_id, title, message, type, related_id, related_type
                    ) VALUES (%s, %s, %s, 'status_change', %s, 'work_order')
                """, (
                    current['assigned_technician_id'],
                    'Statut de travail modifié',
                    f'Le statut est passé de "{old_status}" à "{new_status}"',
                    id
                ))
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Statut mis à jour vers "{new_status}"',
                'new_status': new_status,
                'old_status': old_status
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@bp.route('/today')
def today_tasks():
    """Vue "Aujourd'hui" pour les techniciens - Interface rapide et optimisée"""
    if session.get('user_role') != 'technician':
        return redirect(url_for('work_orders.index'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Tâches du jour pour le technicien connecté
            cursor.execute("""
                SELECT 
                    wo.*,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.address as customer_address,
                    COUNT(wol.id) as lines_count,
                    COALESCE(SUM(wol.MONTANT), 0) as estimated_amount,
                    CASE 
                        WHEN wo.scheduled_date IS NOT NULL THEN wo.scheduled_date
                        ELSE wo.created_at 
                    END as task_time
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN work_order_lines wol ON wo.id = wol.work_order_id
                WHERE wo.assigned_technician_id = %s
                AND wo.status NOT IN ('completed', 'cancelled')
                AND (
                    DATE(wo.scheduled_date) = CURDATE()
                    OR (wo.scheduled_date IS NULL AND DATE(wo.created_at) <= CURDATE())
                )
                GROUP BY wo.id
                ORDER BY 
                    FIELD(wo.priority, 'urgent', 'high', 'medium', 'low'),
                    task_time ASC
            """, (session.get('user_id'),))
            
            today_tasks = cursor.fetchall()
            
            # Statistiques du technicien
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_today,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                    SUM(CASE WHEN status = 'completed' THEN actual_duration END) as total_time_today
                FROM work_orders 
                WHERE assigned_technician_id = %s 
                AND DATE(updated_at) = CURDATE()
            """, (session.get('user_id'),))
            
            my_stats = cursor.fetchone()
            
            return render_template('work_orders/index.html',
                                 today_tasks=today_tasks,
                                 my_stats=my_stats)
    finally:
        conn.close()

# Routes API pour les interactions AJAX
@bp.route('/api/search')
def api_search():
    """API de recherche rapide pour les work orders"""
    query = request.args.get('q', '')
    limit = min(int(request.args.get('limit', 10)), 50)
    
    if len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    wo.id, wo.claim_number, wo.status, wo.priority,
                    c.name as customer_name,
                    u.name as technician_name
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users u ON wo.assigned_technician_id = u.id
                WHERE wo.claim_number LIKE %s 
                   OR c.name LIKE %s 
                   OR wo.description LIKE %s
                ORDER BY wo.created_at DESC
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            results = cursor.fetchall()
            return jsonify(results)
    finally:
        conn.close()

@bp.route('/api/stats')
def api_stats():
    """API pour les statistiques en temps réel"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Statistiques générales
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(actual_duration) as avg_duration,
                    SUM(actual_cost) as total_cost
                FROM work_orders 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY status
            """)
            status_stats = cursor.fetchall()
            
            # Performance des techniciens
            cursor.execute("""
                SELECT 
                    u.name,
                    COUNT(wo.id) as total_orders,
                    AVG(wo.actual_duration) as avg_duration,
                    COUNT(CASE WHEN wo.status = 'completed' THEN 1 END) as completed
                FROM users u
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id
                WHERE u.role = 'technician'
                AND wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY u.id, u.name
            """)
            technician_stats = cursor.fetchall()
            
            return jsonify({
                'status_distribution': status_stats,
                'technician_performance': technician_stats,
                'last_updated': datetime.now().isoformat()
            })
    finally:
        conn.close()
