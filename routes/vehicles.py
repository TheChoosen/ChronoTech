from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from core.config import get_db_config
import pymysql
from core.utils import log_error, log_info

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
        return jsonify({'success': False, 'message': 'customer_id manquant'}), 400

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
    return render_template('customers/vehicles_new.html', customer_id=customer_id)


@bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    conn = get_db_connection()
    if not conn:
        flash('Erreur de connexion DB', 'error')
        return redirect(request.referrer or url_for('customers.index'))
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM vehicles WHERE id = %s", (id,))
            conn.commit()
            flash('Véhicule supprimé', 'success')
    except Exception as e:
        log_error(f"Erreur suppression véhicule {id}: {e}")
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

    return render_template('customers/vehicles_list.html', vehicles=vehicles, customer_id=customer_id)


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

        return render_template('customers/vehicles_edit.html', vehicle=vehicle)
    finally:
        try:
            conn.close()
        except Exception:
            pass
