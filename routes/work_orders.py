"""
Routes pour la gestion des bons de travail (Work Orders)
Basé sur le PRD Fusionné v2.0 - Architecture moderne avec IA
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from forms import WorkOrderForm
import pymysql
from datetime import datetime, timedelta
import json
import os
from functools import wraps

bp = Blueprint('work_orders', __name__)

def get_db_connection():
    """Connexion à la base de données"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DB', 'chronotech'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

@bp.route('/')
def list_work_orders():
    """Liste des bons de travail avec filtres avancés"""
    # Récupération des paramètres de filtre
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    technician_filter = request.args.get('technician', 'all')
    search_query = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    view_mode = request.args.get('view', 'cards')  # cards ou table
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Construction de la requête avec filtres
            where_conditions = []
            params = []
            
            # Filtres de base
            if status_filter != 'all':
                where_conditions.append("wo.status = %s")
                params.append(status_filter)
            
            if priority_filter != 'all':
                where_conditions.append("wo.priority = %s")
                params.append(priority_filter)
            
            if technician_filter != 'all':
                where_conditions.append("wo.assigned_technician_id = %s")
                params.append(technician_filter)
            
            # Recherche textuelle
            if search_query:
                where_conditions.append("""
                    (wo.claim_number LIKE %s 
                     OR wo.customer_name LIKE %s 
                     OR wo.description LIKE %s
                     OR c.name LIKE %s)
                """)
                search_param = f"%{search_query}%"
                params.extend([search_param, search_param, search_param, search_param])
            
            # Filtres de date
            if date_from:
                where_conditions.append("DATE(wo.created_at) >= %s")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("DATE(wo.created_at) <= %s")
                params.append(date_to)
            
            # Restriction selon le rôle
            user_role = session.get('user_role')
            if user_role == 'technician':
                where_conditions.append("wo.assigned_technician_id = %s")
                params.append(session.get('user_id'))
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Requête principale
            cursor.execute(f"""
                SELECT 
                    wo.*,
                    u.name as technician_name,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    c.email as customer_email,
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
            """, params)
            
            work_orders = cursor.fetchall()
            
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
                                 filters={
                                     'status': status_filter,
                                     'priority': priority_filter,
                                     'technician': technician_filter,
                                     'search': search_query,
                                     'date_from': date_from,
                                     'date_to': date_to,
                                     'view': view_mode
                                 })
    finally:
        conn.close()

@bp.route('/create', methods=['GET', 'POST'])
def create_work_order():
    """Créer un nouveau bon de travail"""
    form = WorkOrderForm()
    # Récupération des données pour les champs liés
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, name FROM customers ORDER BY name")
        customers = cursor.fetchall()
        cursor.execute("SELECT id, name FROM users WHERE role IN ('technician', 'supervisor')")
        technicians = cursor.fetchall()
    conn.close()
    # Remplir les choices pour les champs liés
    form.customer_id.choices = [(str(c['id']), c['name']) for c in customers]
    form.technician_id.choices = [('', '---')] + [(str(t['id']), t['name']) for t in technicians]
    if form.validate_on_submit():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM work_orders WHERE DATE(created_at) = CURDATE()")
                daily_count = cursor.fetchone()['count'] + 1
                claim_number = f"WO{datetime.now().strftime('%Y%m%d')}-{daily_count:03d}"
                cursor.execute("""
                    INSERT INTO work_orders (
                        claim_number, customer_id, description, priority, 
                        estimated_duration, estimated_cost, scheduled_date,
                        assigned_technician_id, created_by_user_id, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    claim_number,
                    form.customer_id.data,
                    form.description.data,
                    form.status.data or 'medium',
                    None,  # estimated_duration
                    None,  # estimated_cost
                    form.due_date.data,
                    form.technician_id.data or None,
                    session.get('user_id'),
                    form.notes.data or ''
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
                return redirect(url_for('work_orders.view_work_order', id=work_order_id))
        except Exception as e:
            flash(f'Erreur lors de la création: {str(e)}', 'error')
        finally:
            conn.close()
    return render_template('work_orders/add.html', form=form, customers=customers, technicians=technicians)

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
                return redirect(url_for('work_orders.list_work_orders'))
            
            # Vérification des permissions
            user_role = session.get('user_role')
            if user_role == 'technician' and work_order['assigned_technician_id'] != session.get('user_id'):
                flash('Accès non autorisé', 'error')
                return redirect(url_for('work_orders.list_work_orders'))
            
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
            
            return render_template('work_orders/view.html',
                                 work_order=work_order,
                                 work_order_lines=work_order_lines,
                                 products=products,
                                 notes=notes,
                                 media=media,
                                 status_history=status_history,
                                 financial_summary=financial_summary)
    finally:
        conn.close()

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit_work_order(id):
    """Modifier un bon de travail existant"""
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            # Traitement de la modification
            description = request.form.get('description')
            priority = request.form.get('priority', 'medium')
            assigned_technician_id = request.form.get('assigned_technician_id')
            customer_id = request.form.get('customer_id')
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE work_orders 
                    SET description = %s, priority = %s, assigned_technician_id = %s, 
                        customer_id = %s, updated_at = NOW()
                    WHERE id = %s
                """, (description, priority, assigned_technician_id or None, customer_id or None, id))
                conn.commit()
                
            flash('Bon de travail modifié avec succès', 'success')
            return redirect(url_for('work_orders.view_work_order', id=id))
        
        # GET - Affichage du formulaire d'édition
        with conn.cursor() as cursor:
            # Récupération du bon de travail
            cursor.execute("SELECT * FROM work_orders WHERE id = %s", (id,))
            work_order = cursor.fetchone()
            
            if not work_order:
                flash('Bon de travail introuvable', 'error')
                return redirect(url_for('work_orders.list_work_orders'))
            
            # Récupération des techniciens
            cursor.execute("SELECT id, name FROM users WHERE role IN ('technician', 'supervisor') AND is_active = 1")
            technicians = cursor.fetchall()
            
            # Récupération des clients
            cursor.execute("SELECT id, name FROM customers WHERE is_active = 1 ORDER BY name")
            customers = cursor.fetchall()
            
            return render_template('work_orders/edit_simple.html',
                                 work_order=work_order,
                                 technicians=technicians,
                                 customers=customers)
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
        return redirect(url_for('work_orders.list_work_orders'))
    
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
