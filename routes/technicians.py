"""
Module de gestion des techniciens - ChronoTech
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from forms import TechnicianForm
import pymysql
from config import get_db_config
from utils import log_info, log_error, log_warning
import traceback

# Création du blueprint
bp = Blueprint('technicians', __name__)

def get_db_connection():
    """Obtient une connexion à la base de données"""
    try:
        return pymysql.connect(**get_db_config())
    except Exception as e:
        log_error(f"Erreur de connexion à la base de données: {e}")
        return None

@bp.route('/')
def index():
    """Page principale des techniciens"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {
                'total_technicians': 0,
                'active_technicians': 0,
                'supervisors': 0,
                'managers': 0
            }
            class DummyPagination:
                total = 0
                prev_num = None
                next_num = None
                pages = 1
            pagination = DummyPagination()
            return render_template('technicians/index.html', technicians=[], stats=stats, pagination=pagination)

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, email, role, created_at, is_active
            FROM users 
            WHERE role IN ('technician', 'supervisor', 'manager') AND is_active = TRUE
            ORDER BY role ASC, name ASC
        """)

        technicians = cursor.fetchall()
        cursor.close()
        conn.close()

        # Calcul des stats
        stats = {
            'total_technicians': len([t for t in technicians if t['role'] == 'technician']),
            'active_technicians': len([t for t in technicians if t['role'] == 'technician' and t.get('is_active', True)]),
            'supervisors': len([t for t in technicians if t['role'] == 'supervisor']),
            'managers': len([t for t in technicians if t['role'] == 'manager'])
        }

        log_info(f"Récupération de {len(technicians)} techniciens")
        class DummyPagination:
            total = len(technicians)
            prev_num = None
            next_num = None
            pages = 1
        pagination = DummyPagination()
        return render_template('technicians/index.html', technicians=technicians, stats=stats, pagination=pagination)

    except Exception as e:
        log_error(f"Erreur lors de la récupération des techniciens: {e}")
        flash('Erreur lors du chargement des techniciens', 'error')
        stats = {
            'total_technicians': 0,
            'active_technicians': 0,
            'supervisors': 0,
            'managers': 0
        }
        class DummyPagination:
            total = 0
            prev_num = None
            next_num = None
            pages = 1
        pagination = DummyPagination()
        return render_template('technicians/index.html', technicians=[], stats=stats, pagination=pagination)

@bp.route('/add', methods=['GET', 'POST'])
def add_technician():
    """Ajouter un nouveau technicien"""
    form = TechnicianForm()
    if form.validate_on_submit():
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return render_template('technicians/add.html', form=form)
            cursor = conn.cursor()
            default_password = 'ChronoTech2025!'
            cursor.execute("""
                INSERT INTO users (name, email, password, role, phone, specialty, status, notes)
                VALUES (%(name)s, %(email)s, %(password)s, %(role)s, %(phone)s, %(specialty)s, %(status)s, %(notes)s)
            """, {
                'name': form.name.data,
                'email': form.email.data,
                'password': default_password,  # En production, utiliser un hash
                'role': 'technician',
                'phone': form.phone.data,
                'specialty': form.specialty.data,
                'status': form.status.data,
                'notes': form.notes.data
            })
            conn.commit()
            user_id = cursor.lastrowid
            cursor.close()
            conn.close()
            log_info(f"Nouveau technicien créé: {form.name.data} (ID: {user_id})")
            flash('Technicien ajouté avec succès', 'success')
            return redirect(url_for('technicians.index'))
        except pymysql.IntegrityError as e:
            log_error(f"Erreur d'intégrité lors de l'ajout du technicien: {e}")
            flash('Un utilisateur avec cet email existe déjà', 'error')
        except Exception as e:
            log_error(f"Erreur lors de l'ajout du technicien: {e}")
            flash('Erreur lors de l\'ajout du technicien', 'error')
    return render_template('technicians/add.html', form=form)

@bp.route('/<int:technician_id>')
def view_technician(technician_id):
    """Voir les détails d'un technicien"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('technicians.index'))
        
        cursor = conn.cursor(dictionary=True)
        
        # Récupérer les informations du technicien
        cursor.execute("""
            SELECT * FROM users 
            WHERE id = %s AND role IN ('technician', 'supervisor', 'manager', 'admin') AND is_active = TRUE
        """, (technician_id,))
        
        technician = cursor.fetchone()
        if not technician:
            flash('Technicien non trouvé', 'error')
            return redirect(url_for('technicians.index'))
        
        # Récupérer les bons de travail assignés
        cursor.execute("""
            SELECT id, claim_number, customer_name, description, status, priority, created_at, scheduled_date
            FROM work_orders 
            WHERE assigned_technician_id = %s 
            ORDER BY 
                CASE status 
                    WHEN 'in_progress' THEN 1
                    WHEN 'assigned' THEN 2
                    WHEN 'pending' THEN 3
                    ELSE 4
                END,
                priority = 'urgent' DESC,
                priority = 'high' DESC,
                priority = 'medium' DESC,
                scheduled_date ASC
        """, (technician_id,))
        
        work_orders = cursor.fetchall()
        
        # Statistiques du technicien
        cursor.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_orders,
                SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned_orders
            FROM work_orders 
            WHERE assigned_technician_id = %s
        """, (technician_id,))
        
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template('technicians/view.html', 
                             technician=technician, 
                             work_orders=work_orders, 
                             stats=stats)
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération du technicien {technician_id}: {e}")
        flash('Erreur lors du chargement du technicien', 'error')
        return redirect(url_for('technicians.index'))

@bp.route('/<int:technician_id>/edit', methods=['GET', 'POST'])
def edit_technician(technician_id):
    """Modifier un technicien"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            conn = get_db_connection()
            if not conn:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})
                else:
                    flash('Erreur de connexion à la base de données', 'error')
                    return redirect(url_for('technicians.view_technician', technician_id=technician_id))
            
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET name = %(name)s, email = %(email)s, role = %(role)s, updated_at = NOW()
                WHERE id = %(id)s AND is_active = TRUE
            """, {
                'name': data.get('name'),
                'email': data.get('email'),
                'role': data.get('role'),
                'id': technician_id
            })
            
            conn.commit()
            cursor.close()
            conn.close()
            
            log_info(f"Technicien modifié: {data.get('name')} (ID: {technician_id})")
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Technicien modifié avec succès'})
            else:
                flash('Technicien modifié avec succès', 'success')
                return redirect(url_for('technicians.view_technician', technician_id=technician_id))
                
        except Exception as e:
            log_error(f"Erreur lors de la modification du technicien {technician_id}: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la modification du technicien'})
            else:
                flash('Erreur lors de la modification du technicien', 'error')
                return redirect(url_for('technicians.view_technician', technician_id=technician_id))
    
    # GET request - afficher le formulaire de modification
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('technicians.index'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s AND is_active = TRUE", (technician_id,))
        technician = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not technician:
            flash('Technicien non trouvé', 'error')
            return redirect(url_for('technicians.index'))
        
        return render_template('technicians/edit.html', technician=technician)
        
    except Exception as e:
        log_error(f"Erreur lors du chargement du formulaire d'édition pour le technicien {technician_id}: {e}")
        flash('Erreur lors du chargement du formulaire', 'error')
        return redirect(url_for('technicians.index'))

@bp.route('/<int:technician_id>/workload')
def technician_workload(technician_id):
    """Afficher la charge de travail d'un technicien"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erreur de connexion à la base de données'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Récupérer les bons de travail avec durées estimées
        cursor.execute("""
            SELECT 
                w.id,
                w.claim_number,
                w.description,
                w.priority,
                w.status,
                w.estimated_duration,
                w.scheduled_date,
                c.name as customer_name
            FROM work_orders w
            LEFT JOIN customers c ON w.customer_id = c.id
            WHERE w.assigned_technician_id = %s 
            AND w.status IN ('assigned', 'in_progress')
            ORDER BY w.scheduled_date ASC, w.priority = 'urgent' DESC, w.priority = 'high' DESC
        """, (technician_id,))
        
        workload = cursor.fetchall()
        
        # Calculer la charge totale
        total_hours = sum(order.get('estimated_duration', 0) for order in workload) / 60  # Convertir en heures
        
        cursor.close()
        conn.close()
        
        if request.is_json:
            return jsonify({
                'workload': workload,
                'total_hours': round(total_hours, 2),
                'total_orders': len(workload)
            })
        else:
            return render_template('technicians/workload.html', 
                                 technician_id=technician_id,
                                 workload=workload,
                                 total_hours=round(total_hours, 2))
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération de la charge de travail pour le technicien {technician_id}: {e}")
        if request.is_json:
            return jsonify({'error': 'Erreur lors de la récupération de la charge de travail'}), 500
        else:
            flash('Erreur lors du chargement de la charge de travail', 'error')
            return redirect(url_for('technicians.view_technician', technician_id=technician_id))

@bp.route('/api/available')
def api_available_technicians():
    """API pour obtenir les techniciens disponibles"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erreur de connexion à la base de données'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.id,
                u.name,
                u.role,
                COUNT(w.id) as active_orders,
                COALESCE(SUM(w.estimated_duration), 0) as total_workload_minutes
            FROM users u
            LEFT JOIN work_orders w ON u.id = w.assigned_technician_id 
                AND w.status IN ('assigned', 'in_progress')
            WHERE u.role IN ('technician', 'supervisor') 
            AND u.is_active = TRUE
            GROUP BY u.id, u.name, u.role
            ORDER BY total_workload_minutes ASC, u.name ASC
        """, )
        
        technicians = cursor.fetchall()
        
        # Ajouter des informations calculées
        for tech in technicians:
            tech['workload_hours'] = round(tech['total_workload_minutes'] / 60, 1)
            tech['availability_status'] = 'disponible' if tech['active_orders'] < 3 else 'occupé'
        
        cursor.close()
        conn.close()
        
        return jsonify({'technicians': technicians})
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération des techniciens disponibles: {e}")
        return jsonify({'error': 'Erreur lors de la récupération des techniciens'}), 500
