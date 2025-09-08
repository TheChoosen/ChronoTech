from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from core.config import get_db_config
import pymysql
from core.utils import log_error, log_info
from core.models import Vehicle, Customer
from core.database import db_manager

bp = Blueprint('vehicles', __name__)


def get_db_connection():
    try:
        cfg = get_db_config()
        return pymysql.connect(**cfg)
    except Exception as e:
        log_error(f"Erreur DB vehicles: {e}")
        return None


@bp.route('/create', methods=['POST'])
def create():
    """Créer un véhicule pour un client (ajax/post)"""
    customer_id = request.form.get('customer_id')
    make = request.form.get('make')
    model = request.form.get('model')
    year = request.form.get('year')
    vin = request.form.get('vin')
    license_plate = request.form.get('license_plate')
    notes = request.form.get('notes')

    if not customer_id:
        # missing customer_id
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'message': 'customer_id manquant'}), 400
        else:
            flash('Client manquant', 'error')
            return redirect(url_for('customers.index'))

    # validate customer exists
    try:
        cid = int(customer_id)
    except Exception:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'message': 'customer_id invalide'}), 400
        else:
            flash('Client invalide', 'error')
            return redirect(url_for('customers.index'))

    try:
        customer_obj = Customer.find_by_id(cid)
    except Exception:
        customer_obj = None

    if not customer_obj:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'message': 'Client introuvable'}), 400
        else:
            flash('Client introuvable', 'error')
            return redirect(url_for('customers.index'))

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO vehicles (customer_id, make, model, year, vin, license_plate, notes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (customer_id, make, model, year or None, vin or None, license_plate or None, notes or None))
            conn.commit()
            vid = cursor.lastrowid
            log_info(f"Véhicule créé id={vid} pour client={customer_id}")
            # If request is AJAX/JSON, return JSON including the created row; otherwise redirect back to customer view
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
            if is_ajax:
                try:
                    # fetch the created vehicle so the client can append it without reloading
                    cursor.execute("SELECT * FROM vehicles WHERE id = %s", (vid,))
                    created = cursor.fetchone()
                except Exception:
                    created = None
                return jsonify({'success': True, 'id': vid, 'vehicle': created})
            else:
                flash('Véhicule créé avec succès', 'success')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))
    except Exception as e:
        log_error(f"Erreur création véhicule: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la création du véhicule'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


@bp.route('/new')
def new():
    """Render a simple vehicle creation form. Uses POST /vehicles/create to submit."""
    customer_id = request.args.get('customer_id')
    customers = []
    try:
        customers = Customer.get_all()
    except Exception:
        customers = []
    return render_template('vehicles/new.html', customer_id=customer_id, customers=customers)


@bp.route('/')
def index():
    """Page d'index interactive pour les véhicules.

    Cette page charge un tableau vide côté client et appelle l'API JSON
    pour récupérer les lignes filtrées/paginées.
    """
    return render_template('vehicles/index.html')


@bp.route('/api')
def api_vehicles():
    """API JSON pour récupérer les véhicules avec filtres et pagination.

    Accessible sous /vehicles/api (blueprint monté sur /vehicles)
    Query params : q, make, model, year, page, per_page, sort_by, sort_dir
    """
    q = (request.args.get('q') or '').strip()
    make = (request.args.get('make') or '').strip()
    model = (request.args.get('model') or '').strip()
    year = (request.args.get('year') or '').strip()
    sort_by = request.args.get('sort_by', 'id')
    sort_dir = request.args.get('sort_dir', 'desc').lower()
    
    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get('per_page', 20))))
    except Exception:
        per_page = 20

    # Validation du tri
    allowed_sort_fields = ['id', 'make', 'model', 'year', 'created_at', 'updated_at']
    if sort_by not in allowed_sort_fields:
        sort_by = 'id'
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'desc'

    # Build dynamic WHERE clause
    where = ["1=1"]
    params = []
    if q:
        where.append("(vin LIKE %s OR license_plate LIKE %s OR notes LIKE %s)")
        qpat = f"%{q}%"
        params.extend([qpat, qpat, qpat])
    if make:
        where.append("make LIKE %s")
        params.append(f"%{make}%")
    if model:
        where.append("model LIKE %s")
        params.append(f"%{model}%")
    if year:
        try:
            y = int(year)
            where.append("year >= %s")
            params.append(y)
        except ValueError:
            pass

    where_clause = " AND ".join(where)
    order_clause = f"ORDER BY {sort_by} {sort_dir.upper()}"

    # total count
    try:
        count_query = f"SELECT COUNT(*) as total FROM vehicles WHERE {where_clause}"
        total_row = db_manager.execute_query(count_query, params, fetch_one=True)
        total = int(total_row.get('total', 0)) if total_row else 0
    except Exception as e:
        log_error(f"Erreur count vehicles API: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

    # pagination
    offset = (page - 1) * per_page
    try:
        data_query = f"SELECT * FROM vehicles WHERE {where_clause} {order_clause} LIMIT %s OFFSET %s"
        data_params = params + [per_page, offset]
        items = db_manager.execute_query(data_query, data_params)
    except Exception as e:
        log_error(f"Erreur fetch vehicles API: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

    # normalize datetimes for JSON
    for row in items:
        for k, v in list(row.items()):
            if hasattr(v, 'isoformat'):
                row[k] = v.isoformat()

    pages = (total + per_page - 1) // per_page if per_page else 1

    return jsonify({
        'page': page,
        'pages': pages,
        'total': total,
        'items': items,
        'sort_by': sort_by,
        'sort_dir': sort_dir
    })


@bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    conn = get_db_connection()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    if not conn:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Erreur de connexion DB'}), 500
        flash('Erreur de connexion DB', 'error')
        return redirect(request.referrer or url_for('customers.index'))
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM vehicles WHERE id = %s", (id,))
            conn.commit()
            if is_ajax:
                return jsonify({'success': True})
            flash('Véhicule supprimé', 'success')
    except Exception as e:
        log_error(f"Erreur suppression véhicule {id}: {e}")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Erreur lors de la suppression'}), 500
        flash('Erreur lors de la suppression', 'error')
    finally:
        conn.close()
    return redirect(request.referrer or url_for('customers.index'))


@bp.route('/customer/<int:customer_id>')
def list_for_customer(customer_id):
    """Lister les véhicules d'un client"""
    conn = get_db_connection()
    vehicles = []
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC", (customer_id,))
                vehicles = cursor.fetchall()
        except Exception as e:
            log_error(f"Erreur list vehicles for customer {customer_id}: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return render_template('vehicles/list.html', vehicles=vehicles, customer_id=customer_id)


@bp.route('/<int:id>')
def view(id):
    """Afficher les détails d'un véhicule"""
    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion DB', 'error')
        return redirect(request.referrer or url_for('vehicles.index'))

    try:
        with conn.cursor() as cursor:
            # Récupérer le véhicule avec les informations du client
            cursor.execute("""
                SELECT v.*, c.name as customer_name, c.email as customer_email, 
                       c.phone as customer_phone, c.address as customer_address
                FROM vehicles v
                LEFT JOIN customers c ON v.customer_id = c.id
                WHERE v.id = %s
            """, (id,))
            
            vehicle = cursor.fetchone()
            
            if not vehicle:
                flash('Véhicule non trouvé', 'error')
                return redirect(url_for('vehicles.index'))
            
            # Récupérer l'historique des interventions pour ce véhicule
            try:
                cursor.execute("""
                    SELECT wo.id, wo.claim_number, wo.description, wo.status, 
                           wo.created_at, wo.completed_at, u.name as technician_name
                    FROM work_orders wo
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    WHERE wo.vehicle_id = %s
                    ORDER BY wo.created_at DESC
                    LIMIT 10
                """, (id,))
                work_orders = cursor.fetchall()
            except Exception as e:
                log_error(f"Erreur récupération work_orders pour véhicule {id}: {e}")
                work_orders = []
            
            return render_template('vehicles/view.html', vehicle=vehicle, work_orders=work_orders)
            
    except Exception as e:
        log_error(f"Erreur affichage véhicule {id}: {e}")
        flash('Erreur lors de l\'affichage du véhicule', 'error')
        return redirect(url_for('vehicles.index'))
    finally:
        try:
            conn.close()
        except Exception:
            pass


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Éditer un véhicule"""
    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion DB', 'error')
        return redirect(request.referrer or url_for('customers.index'))

    try:
        if request.method == 'POST':
            make = request.form.get('make')
            model = request.form.get('model')
            year = request.form.get('year') or None
            vin = request.form.get('vin') or None
            license_plate = request.form.get('license_plate') or None
            notes = request.form.get('notes') or None

            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE vehicles SET make=%s, model=%s, year=%s, vin=%s, license_plate=%s, notes=%s, updated_at=NOW()
                        WHERE id = %s
                    """, (make, model, year, vin, license_plate, notes, id))
                    conn.commit()
                    # prepare updated vehicle for AJAX responses
                    cursor.execute("SELECT * FROM vehicles WHERE id = %s", (id,))
                    updated = cursor.fetchone()
            except Exception as e:
                log_error(f"Erreur update vehicle {id}: {e}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                    return jsonify({'success': False, 'message': 'Erreur lors de la mise à jour'}), 500
                else:
                    flash('Erreur lors de la mise à jour', 'error')
                    return redirect(url_for('vehicles.list_for_customer', customer_id=request.form.get('customer_id') or 0))

            # If AJAX, return updated vehicle JSON; otherwise redirect back
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': True, 'vehicle': updated})
            else:
                flash('Véhicule mis à jour', 'success')
                return redirect(url_for('vehicles.list_for_customer', customer_id=request.form.get('customer_id') or 0))

        # GET - load vehicle
        vehicle = None
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM vehicles WHERE id = %s", (id,))
            vehicle = cursor.fetchone()

        if not vehicle:
            flash('Véhicule non trouvé', 'error')
            return redirect(request.referrer or url_for('customers.index'))

        return render_template('vehicles/edit.html', vehicle=vehicle)
    finally:
        try:
            conn.close()
        except Exception:
            pass
