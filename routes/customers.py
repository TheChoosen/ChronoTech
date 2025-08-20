"""Module de gestion des clients - ChronoTech"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from core.forms import CustomerForm
import pymysql
from core.config import get_db_config
from core.utils import log_info, log_error, log_warning
import traceback

# Création du blueprint
bp = Blueprint('customers', __name__)


class MiniPagination:
    """Lightweight pagination object to mimic Flask-SQLAlchemy / Werkzeug pagination used in templates."""
    def __init__(self, total=0, page=1, per_page=20):
        try:
            self.total = int(total or 0)
        except Exception:
            self.total = 0
        self.page = int(page or 1)
        self.per_page = int(per_page or 20)
        self.pages = max(1, (self.total + self.per_page - 1) // self.per_page)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
        # Simplified iterator that yields all pages; templates handle ellipses if needed
        for p in range(1, self.pages + 1):
            yield p



def _debug(msg):
    try:
        print(f"[DEBUG customers] {msg}")
    except Exception:
        pass


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
            pagination = MiniPagination(total=0, page=1, per_page=20)
            return render_template('customers/index.html', customers=[], stats=stats, pagination=pagination)

        # Build dynamic filters from query params
        args = request.args or {}
        search = (args.get('search') or '').strip()
        customer_type = args.get('customer_type') or ''
        zone = args.get('zone') or ''
        status = args.get('status') or ''
        sort = args.get('sort') or 'name'

        # Detect existing columns to avoid referencing missing schema fields
        try:
            col_cur = conn.cursor()
            col_cur.execute("SHOW COLUMNS FROM customers")
            existing_cols = {r[0] for r in col_cur.fetchall()}
            col_cur.close()
        except Exception:
            existing_cols = set()

        where_clauses = []
        params = []

        if search:
            like = f"%{search}%"
            where_clauses.append("(name LIKE %s OR company LIKE %s OR email LIKE %s OR phone LIKE %s)")
            params.extend([like, like, like, like])

        if customer_type and 'customer_type' in existing_cols:
            where_clauses.append('customer_type = %s')
            params.append(customer_type)

        if zone and 'zone' in existing_cols:
            where_clauses.append('zone = %s')
            params.append(zone)

        if status and 'status' in existing_cols:
            where_clauses.append('status = %s')
            params.append(status)

        # If there's an is_active column and the caller did not filter by status,
        # default to only showing active customers for backward-compatibility.
        if 'is_active' in existing_cols and not status:
            where_clauses.insert(0, 'is_active = TRUE')

        # Map allowed sorts to SQL order clauses
        sort_map = {
            'name': 'name ASC',
            'name_desc': 'name DESC',
            'created_date': 'created_at DESC',
            'last_order': 'created_at DESC'
        }
        order_by = sort_map.get(sort, 'name ASC')

        # Build select list, include optional columns only if present
        select_cols = ['id', 'name', 'company', 'email', 'phone', 'address', 'created_at', 'is_active']
        for opt in ('status', 'customer_type', 'zone'):
            if opt in existing_cols:
                select_cols.append(opt)

        where_sql = ' AND '.join(where_clauses)

        # Log the built query and params for debugging
        try:
            log_info(f"Customers SQL WHERE: {where_sql} params={params}")
        except Exception:
            pass

        # First get total count matching filters (accurate stats & pagination)
        count_sql = f"SELECT COUNT(*) AS cnt FROM customers WHERE {where_sql}"
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_matching = int(row['cnt']) if row and 'cnt' in row else 0
        except Exception as e:
            log_error(f"Erreur count customers: {e}")
            total_matching = 0

        # Now fetch the actual rows (could add LIMIT/OFFSET for pagination later)
        sql = f"SELECT {', '.join(select_cols)} FROM customers WHERE {where_sql} ORDER BY {order_by}"
        try:
            cursor.execute(sql, params)
            customers = cursor.fetchall()
        except Exception as e:
            log_error(f"Erreur select customers: {e}")
            customers = []
        finally:
            cursor.close()
        # Compute vehicles count for listed customers
        try:
            if customers:
                cust_ids = [c['id'] for c in customers]
                # build placeholders for IN clause
                placeholders = ','.join(['%s'] * len(cust_ids))
                cur2 = conn.cursor(pymysql.cursors.DictCursor)
                cur2.execute(f"SELECT customer_id, COUNT(*) AS cnt FROM vehicles WHERE customer_id IN ({placeholders}) GROUP BY customer_id", cust_ids)
                rows = cur2.fetchall()
                counts = {r['customer_id']: r['cnt'] for r in rows}
                for c in customers:
                    c['vehicles_count'] = counts.get(c['id'], 0)
                cur2.close()
            else:
                # no customers -> nothing to do
                pass
        except Exception as e:
            log_error(f"Erreur comptage véhicules: {e}")
        finally:
            conn.close()

        log_info(f"Récupération de {len(customers)} clients")
        # Statistiques basiques (à adapter selon tes besoins)
        stats = {
            'total_customers': total_matching,
            'active_customers': len([c for c in customers if c.get('is_active', True)]),
            'total_work_orders': 0,  # À calculer si besoin
            'total_revenue': 0      # À calculer si besoin
        }
        pagination = MiniPagination(total=total_matching, page=1, per_page=20)
        # If AJAX request, return only the rendered list fragment as JSON for client-side replacement
        try:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        except Exception:
            is_ajax = False

        if is_ajax:
            try:
                fragment = render_template('customers/_list.html', customers=customers, stats=stats, pagination=pagination)
                stats_fragment = render_template('customers/_stats.html', stats=stats)
                return jsonify({'success': True, 'html': fragment, 'stats_html': stats_fragment, 'total': pagination.total})
            except Exception as e:
                log_error(f"Erreur rendu fragment clients pour AJAX: {e}")
                return jsonify({'success': False, 'error': 'render_error'}), 500

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
        pagination = MiniPagination(total=0, page=1, per_page=20)
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
                INSERT INTO customers (name, company, email, phone, address, siret, status, postal_code, city, country, billing_address, payment_terms, notes, tax_number, preferred_contact_method, zone, created_at, updated_at, is_active)
                VALUES (%(name)s, %(company)s, %(email)s, %(phone)s, %(address)s, %(siret)s, %(status)s, %(postal_code)s, %(city)s, %(country)s, %(billing_address)s, %(payment_terms)s, %(notes)s, %(tax_number)s, %(preferred_contact_method)s, %(zone)s, NOW(), NOW(), TRUE)
            """, {
                'name': form.name.data,
                'company': form.company.data,
                'email': form.email.data,
                'phone': form.phone.data,
                'address': form.address.data,
                'siret': getattr(form, 'siret', None) and form.siret.data or None,
                'status': getattr(form, 'status', None) and form.status.data or None,
                'postal_code': getattr(form, 'postal_code', None) and form.postal_code.data or None,
                'city': getattr(form, 'city', None) and form.city.data or None,
                'country': getattr(form, 'country', None) and form.country.data or None,
                'billing_address': getattr(form, 'billing_address', None) and form.billing_address.data or None,
                'payment_terms': getattr(form, 'payment_terms', None) and form.payment_terms.data or None,
                'notes': getattr(form, 'notes', None) and form.notes.data or None,
                'tax_number': getattr(form, 'tax_number', None) and form.tax_number.data or None,
                'preferred_contact_method': getattr(form, 'preferred_contact_method', None) and form.preferred_contact_method.data or None,
                'zone': getattr(form, 'zone', None) and form.zone.data or None
            })

            customer_id = cursor.lastrowid
            conn.commit()
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

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Récupérer les informations du client
        cursor.execute("""
            SELECT * FROM customers WHERE id = %s
        """, (customer_id,))

        customer = cursor.fetchone()
        if not customer:
            cursor.close()
            conn.close()
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

        # Minimal stats and auxiliary data expected by the template
        stats = {
            'total_work_orders': len(work_orders),
            'completed_work_orders': len([w for w in work_orders if w.get('status') == 'completed']),
            'total_spent': 0,
            # Avoid calling custom filters in contexts where they may not be registered
            'last_order_date': None
        }

        # Provide commonly-used lists/objects to avoid template errors when data is missing
        recent_work_orders = work_orders[:5]
        recent_activities = []
        customer_contacts = []
        monthly_orders_data = []
        priority_distribution = []

        # Load vehicles for this customer
        vehicles = []
        try:
            conn2 = get_db_connection()
            if conn2:
                cur2 = conn2.cursor(pymysql.cursors.DictCursor)
                cur2.execute("SELECT id, make, model, year, vin, license_plate, notes FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC", (customer_id,))
                vehicles = cur2.fetchall()
                cur2.close()
                conn2.close()
        except Exception:
            vehicles = []

        return render_template('customers/view.html', customer=customer, work_orders=work_orders,
                               stats=stats, recent_work_orders=recent_work_orders,
                               recent_activities=recent_activities, customer_contacts=customer_contacts,
                               monthly_orders_data=monthly_orders_data, priority_distribution=priority_distribution,
                               vehicles=vehicles)

    except Exception as e:
        log_error(f"Erreur lors de la récupération du client {customer_id}: {e}")
        flash('Erreur lors du chargement du client', 'error')
        return redirect(url_for('customers.index'))


@bp.route('/<int:customer_id>/contacts/create', methods=['POST'])
def create_contact(customer_id):
    """Create a contact for a customer. AJAX-aware (returns JSON) or fallback to redirect."""
    name = request.form.get('name')
    role = request.form.get('role')
    email = request.form.get('email')
    phone = request.form.get('phone')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO contacts (customer_id, name, role, email, phone, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (customer_id, name, role, email, phone))
            conn.commit()
            cid = cursor.lastrowid
            # fetch created
            try:
                cursor.execute("SELECT id, name, role, email, phone FROM contacts WHERE id = %s", (cid,))
                created = cursor.fetchone()
            except Exception:
                created = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'id': cid, 'contact': created})
        flash('Contact ajouté', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))
    except Exception as e:
        log_error(f"Erreur création contact: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur création contact'}), 500
        flash('Erreur création contact', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


@bp.route('/contacts/<int:contact_id>/update', methods=['POST'])
def update_contact(contact_id):
    """Update a contact. Expects form data and customer_id in form for redirect fallback."""
    name = request.form.get('name')
    role = request.form.get('role')
    email = request.form.get('email')
    phone = request.form.get('phone')
    customer_id = request.form.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))

        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE contacts SET name=%s, role=%s, email=%s, phone=%s, updated_at=NOW()
                WHERE id = %s
            """, (name, role, email, phone, contact_id))
            conn.commit()
            try:
                cursor.execute("SELECT id, name, role, email, phone FROM contacts WHERE id = %s", (contact_id,))
                updated = cursor.fetchone()
            except Exception:
                updated = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'contact': updated})
        flash('Contact modifié', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur update contact: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur mise à jour'}), 500
        flash('Erreur mise à jour contact', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


@bp.route('/contacts/<int:contact_id>/delete', methods=['POST'])
def delete_contact(contact_id):
    """Delete a contact. Expects customer_id in form for redirect fallback."""
    customer_id = request.form.get('customer_id') or request.args.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
            conn.commit()
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True})
        flash('Contact supprimé', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur suppression contact: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur suppression'}), 500
        flash('Erreur suppression contact', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


@bp.route('/<int:customer_id>/addresses/create', methods=['POST'])
def create_address(customer_id):
    """Create a delivery address for a customer. AJAX-aware."""
    label = request.form.get('label')
    street = request.form.get('street')
    postal_code = request.form.get('postal_code')
    city = request.form.get('city')
    country = request.form.get('country')
    phone = request.form.get('phone')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO addresses (customer_id, label, street, postal_code, city, country, phone, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (customer_id, label, street, postal_code, city, country, phone))
            conn.commit()
            aid = cursor.lastrowid
            try:
                cursor.execute("SELECT id, label, street, postal_code, city, country, phone FROM addresses WHERE id = %s", (aid,))
                created = cursor.fetchone()
            except Exception:
                created = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'id': aid, 'address': created})
        flash('Adresse ajoutée', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))
    except Exception as e:
        log_error(f"Erreur création adresse: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur création adresse'}), 500
        flash('Erreur création adresse', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))


@bp.route('/addresses/<int:address_id>/update', methods=['POST'])
def update_address(address_id):
    label = request.form.get('label')
    street = request.form.get('street')
    postal_code = request.form.get('postal_code')
    city = request.form.get('city')
    country = request.form.get('country')
    phone = request.form.get('phone')
    customer_id = request.form.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE addresses SET label=%s, street=%s, postal_code=%s, city=%s, country=%s, phone=%s, updated_at=NOW()
                WHERE id = %s
            """, (label, street, postal_code, city, country, phone, address_id))
            conn.commit()
            try:
                cursor.execute("SELECT id, label, street, postal_code, city, country, phone FROM addresses WHERE id = %s", (address_id,))
                updated = cursor.fetchone()
            except Exception:
                updated = None
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'address': updated})
        flash('Adresse modifiée', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur update adresse: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur mise à jour'}), 500
        flash('Erreur mise à jour adresse', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


@bp.route('/addresses/<int:address_id>/delete', methods=['POST'])
def delete_address(address_id):
    customer_id = request.form.get('customer_id') or request.args.get('customer_id')
    try:
        conn = get_db_connection()
        if not conn:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'DB connection error'}), 500
            flash('Erreur de connexion DB', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM addresses WHERE id = %s", (address_id,))
            conn.commit()
        conn.close()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True})
        flash('Adresse supprimée', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))
    except Exception as e:
        log_error(f"Erreur suppression adresse: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur suppression'}), 500
        flash('Erreur suppression adresse', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id or 0))


# Backwards-compatible alias: some templates call `customers.view` with param `id`
@bp.route('/<int:id>/view')
def view(id):
    return redirect(url_for('customers.view_customer', customer_id=id))


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
                WHERE id = %(id)s
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

            # Decide next action: normal view or create work order
            create_order_flag = False
            try:
                # data may be a dict (JSON) or ImmutableMultiDict (form)
                create_order_flag = str(data.get('save_and_add_order', '')).strip() in ['1', 'true', 'True']
            except Exception:
                create_order_flag = False

            next_url = url_for('customers.view_customer', customer_id=customer_id)
            if create_order_flag:
                next_url = url_for('work_orders.create_work_order', customer_id=customer_id)

            if request.is_json:
                return jsonify({'success': True, 'message': 'Client modifié avec succès', 'next': next_url})
            else:
                flash('Client modifié avec succès', 'success')
                return redirect(next_url)

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

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
        customer = cursor.fetchone()
        _debug(f"Fetched customer for edit GET: {customer}")
        cursor.close()
        conn.close()

        if not customer:
            flash('Client non trouvé', 'error')
            return redirect(url_for('customers.index'))

        # Instantiate a form prefilled with customer data for the template
        try:
            form = CustomerForm(data=customer)
        except Exception:
            form = CustomerForm()

        return render_template('customers/edit.html', customer=customer, form=form)

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

        # Determine if this was an AJAX request (X-Requested-With) or JSON
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': True, 'message': 'Client supprimé avec succès', 'id': customer_id})
        else:
            flash('Client supprimé avec succès', 'success')
            return redirect(url_for('customers.index'))

    except Exception as e:
        log_error(f"Erreur lors de la suppression du client {customer_id}: {e}")
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'message': 'Erreur lors de la suppression du client'}), 500
        else:
            flash('Erreur lors de la suppression du client', 'error')
            return redirect(url_for('customers.index'))


# Backwards-compatible aliases used by templates
@bp.route('/<int:id>/actions/delete', methods=['POST'], endpoint='delete')
def delete_alias(id):
    return delete_customer(id)


@bp.route('/<int:id>/export', methods=['GET'], endpoint='export_data')
def export_alias(id):
    # Minimal stub: redirect to view for now
    return redirect(url_for('customers.view_customer', customer_id=id))


def _register_dummy_endpoints(state):
    """When the blueprint is registered on the app, create minimal dummy endpoints
    used by templates to avoid url_for errors in environments where other blueprints
    (like 'quotes') may not be registered during tests or limited contexts."""
    app = state.app
    try:
        # Provide a minimal quotes.add endpoint
        if 'quotes.add' not in app.view_functions:
            app.add_url_rule('/quotes/add', endpoint='quotes.add', view_func=lambda: redirect(url_for('customers.index')))
        # Provide minimal appointment and parts endpoints used by templates
        if 'appointments.create' not in app.view_functions:
            app.add_url_rule('/appointments/create', endpoint='appointments.create', view_func=lambda customer_id=None: redirect(url_for('work_orders.create_work_order', customer_id=customer_id or '')))
        if 'parts.create_order' not in app.view_functions:
            app.add_url_rule('/parts/create', endpoint='parts.create_order', view_func=lambda customer_id=None: redirect(url_for('work_orders.create_work_order', customer_id=customer_id or '')))
    except Exception:
        pass


bp.record(_register_dummy_endpoints)


@bp.route('/alt')
def index_alt():
    """Alternative UI for customers list (compact table + quick actions)."""
    try:
        # params
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        q = request.args.get('search', '').strip()

        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {'total_customers': 0, 'active_customers': 0, 'total_work_orders': 0, 'total_revenue': 0}
            class DummyPagination:
                total = 0
                prev_num = None
                next_num = None
                pages = 1
            pagination = DummyPagination()
            return render_template('customers/index_alt.html', customers=[], stats=stats, pagination=pagination)

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        where_clauses = ["is_active = TRUE"]
        params = []
        if q:
            where_clauses.append("(name LIKE %s OR company LIKE %s OR email LIKE %s OR phone LIKE %s)")
            like_q = f"%{q}%"
            params.extend([like_q, like_q, like_q, like_q])

        where_sql = " AND ".join(where_clauses)

        # total count for pagination
        cursor.execute(f"SELECT COUNT(*) as total FROM customers WHERE {where_sql}", params)
        total = cursor.fetchone().get('total', 0)

        # paging
        offset = (page - 1) * per_page
        params_page = params[:]  # copy
        params_page.extend([per_page, offset])

        cursor.execute(f"SELECT id, name, company, email, phone, city, created_at, is_active FROM customers WHERE {where_sql} ORDER BY name ASC LIMIT %s OFFSET %s", params_page)
        customers = cursor.fetchall()

        # vehicles counts for the page
        try:
            if customers:
                cust_ids = [c['id'] for c in customers]
                placeholders = ','.join(['%s'] * len(cust_ids))
                cur2 = conn.cursor(pymysql.cursors.DictCursor)
                cur2.execute(f"SELECT customer_id, COUNT(*) AS cnt FROM vehicles WHERE customer_id IN ({placeholders}) GROUP BY customer_id", cust_ids)
                rows = cur2.fetchall()
                counts = {r['customer_id']: r['cnt'] for r in rows}
                for c in customers:
                    c['vehicles_count'] = counts.get(c['id'], 0)
                cur2.close()
        except Exception:
            for c in customers:
                c['vehicles_count'] = 0

        # basic stats
        stats = {
            'total_customers': total,
            'active_customers': total,
            'total_work_orders': 0,
            'total_revenue': 0
        }

        # simple Pagination object
        class Pagination:
            def __init__(self, page, per_page, total):
                self.page = page
                self.per_page = per_page
                self.total = total

            @property
            def pages(self):
                return max(1, (self.total + self.per_page - 1) // self.per_page)

            @property
            def has_prev(self):
                return self.page > 1

            @property
            def has_next(self):
                return self.page < self.pages

            @property
            def prev_num(self):
                return self.page - 1 if self.has_prev else None

            @property
            def next_num(self):
                return self.page + 1 if self.has_next else None

            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or (num >= self.page - left_current and num <= self.page + right_current) or num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num

        pagination = Pagination(page, per_page, total)

        cursor.close()
        conn.close()

        return render_template('customers/index_alt.html', customers=customers, stats=stats, pagination=pagination)

    except Exception as e:
        log_error(f"Erreur index_alt: {e}")
        flash('Erreur lors du chargement de la page', 'error')
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

        cursor = conn.cursor(pymysql.cursors.DictCursor)
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

