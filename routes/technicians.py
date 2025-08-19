"""
Module de gestion des techniciens - ChronoTech
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from core.forms import TechnicianForm
import pymysql
from core.config import get_db_config
from core.utils import log_info, log_error, log_warning
import os
import json
from werkzeug.utils import secure_filename

# Création du blueprint
bp = Blueprint('technicians', __name__)


def _debug(msg):
    try:
        # simple stdout print for quick debugging in dev environment
        print(f"[DEBUG technicians] {msg}")
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
    """Page principale des techniciens"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {
                'total_technicians': 0,
                'active_technicians': 0,
                'supervisors': 0,
                'managers': 0,
            }

            class DummyPagination:
                total = 0
                prev_num = None
                next_num = None
                pages = 1

            pagination = DummyPagination()
            return render_template('technicians/index.html', technicians=[], stats=stats, pagination=pagination)

        # Lire les filtres depuis la querystring
        status_filter = request.args.get('status', '').strip()
        specialization_filter = request.args.get('specialization', '').strip()
        zone_filter = request.args.get('zone', '').strip()
        search_filter = request.args.get('search', '').strip()
        availability_filter = request.args.get('availability', '').strip()
        sort = request.args.get('sort', 'name')

        # Construire dynamiquement la clause WHERE selon les filtres
        where_clauses = ["role IN ('technician', 'supervisor', 'manager')"]
        params = []

        # status filter: empty => Tous statuts -> ne pas filtrer par is_active
        if status_filter:
            # map UI values to DB column 'status' or to is_active if needed
            if status_filter == 'active':
                where_clauses.append('is_active = TRUE')
            elif status_filter == 'inactive':
                where_clauses.append('is_active = FALSE')
            else:
                # support status values stored in 'status' column
                where_clauses.append('status = %s')
                params.append(status_filter)

        # specialization (optional column 'specialization' or 'specialty')
        if specialization_filter:
            where_clauses.append("(specialization = %s OR specialty = %s)")
            params.extend([specialization_filter, specialization_filter])

        if zone_filter:
            where_clauses.append('zone = %s')
            params.append(zone_filter)

        if search_filter:
            where_clauses.append("(name LIKE %s OR email LIKE %s OR specialty LIKE %s)")
            pattern = f"%{search_filter}%"
            params.extend([pattern, pattern, pattern])

        # order by
        sort_map = {
            'name': 'name ASC',
            'workload': 'name ASC',  # workload requires extra calculation - fallback to name
            'rating': 'name ASC',
            'last_activity': 'updated_at DESC',
        }
        order_clause = sort_map.get(sort, 'name ASC')

        # Use SELECT * to avoid errors if optional columns (specialization, specialty, zone) are absent
        sql = f"SELECT * FROM users WHERE {' AND '.join(where_clauses)} ORDER BY {order_clause}"
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql, tuple(params) if params else None)
        technicians = cursor.fetchall()
        cursor.close()
        conn.close()

        # Ensure optional keys exist so templates can safely access them
        for t in technicians:
            # experience_years used in several templates
            if 'experience_years' not in t or t.get('experience_years') is None:
                t['experience_years'] = 0

            # Normalize schedule_json: it may be stored as JSON text, bytes, dict, or null
            raw_sched = t.get('schedule_json')
            if raw_sched is None:
                t['schedule_json'] = {}
            else:
                if isinstance(raw_sched, str):
                    try:
                        t['schedule_json'] = json.loads(raw_sched)
                    except Exception:
                        t['schedule_json'] = {}
                elif isinstance(raw_sched, (bytes, bytearray)):
                    try:
                        t['schedule_json'] = json.loads(raw_sched.decode())
                    except Exception:
                        t['schedule_json'] = {}
                elif isinstance(raw_sched, dict):
                    # already a dict
                    pass
                else:
                    t['schedule_json'] = {}

        # Wrap rows to provide attribute-style access with safe defaults for templates
        class RowWrapper:
            def __init__(self, data):
                self._d = data

            def __getattr__(self, name):
                # Return explicit defaults for known optional fields
                if name == 'experience_years':
                    return self._d.get('experience_years', 0)
                if name == 'schedule_json':
                    return self._d.get('schedule_json', {})
                # fall back to the underlying dict keys
                if name in self._d:
                    return self._d[name]
                return None

            def get(self, key, default=None):
                return self._d.get(key, default)

            def to_dict(self):
                return self._d

        wrapped_technicians = [RowWrapper(t) for t in technicians]

        # Calcul des stats
        stats = {
            'total_technicians': len([t for t in technicians if t.get('role') == 'technician']),
            'active_technicians': len([t for t in technicians if t.get('role') == 'technician' and t.get('is_active', True)]),
            'supervisors': len([t for t in technicians if t.get('role') == 'supervisor']),
            'managers': len([t for t in technicians if t.get('role') == 'manager']),
        }

        log_info(f"Récupération de {len(technicians)} techniciens | filtres: status='{status_filter}' specialization='{specialization_filter}' zone='{zone_filter}' search='{search_filter}' availability='{availability_filter}' sort='{sort}'")

        class DummyPagination:
            total = len(technicians)
            prev_num = None
            next_num = None
            pages = 1

        pagination = DummyPagination()
        return render_template('technicians/index.html', technicians=wrapped_technicians, stats=stats, pagination=pagination)

    except Exception as e:
        log_error(f"Erreur lors de la récupération des techniciens: {e}")
        flash('Erreur lors du chargement des techniciens', 'error')
        stats = {
            'total_technicians': 0,
            'active_technicians': 0,
            'supervisors': 0,
            'managers': 0,
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
            cursor.execute(
                """
                INSERT INTO users (name, email, password, role, phone, specialty, status, notes, is_active)
                VALUES (%(name)s, %(email)s, %(password)s, %(role)s, %(phone)s, %(specialty)s, %(status)s, %(notes)s, %(is_active)s)
                """,
                {
                    'name': form.name.data,
                    'email': form.email.data,
                    'password': default_password,  # En production, utiliser un hash
                    'role': 'technician',
                    'phone': form.phone.data,
                    'specialty': form.specialty.data,
                    'status': form.status.data,
                    'notes': form.notes.data,
                    'is_active': 1,
                },
            )

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

    # Default lists used by the add template
    specializations = ['Électrique', 'Mécanique', 'Climatisation', 'Plomberie', 'Informatique']
    certification_levels = ['', 'Niveau 1', 'Niveau 2', 'Niveau 3']
    zones = ['Nord', 'Sud', 'Est', 'Ouest', 'Centre']
    technical_skills = []

    return render_template('technicians/add.html', form=form, specializations=specializations, certification_levels=certification_levels, zones=zones, technical_skills=technical_skills)


@bp.route('/<int:technician_id>')
def view_technician(technician_id):
    """Voir les détails d'un technicien"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('technicians.index'))

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Récupérer les informations du technicien
        cursor.execute(
            """
            SELECT * FROM users
            WHERE id = %s AND role IN ('technician', 'supervisor', 'manager', 'admin')
            """,
            (technician_id,),
        )

        technician = cursor.fetchone()
        # Defensive parse: ensure schedule_json is a dict to avoid template .items() errors
        if technician:
            raw = technician.get('schedule_json')
            if raw is None:
                technician['schedule_json'] = {}
            else:
                if isinstance(raw, str):
                    try:
                        technician['schedule_json'] = json.loads(raw)
                    except Exception:
                        technician['schedule_json'] = {}
                elif isinstance(raw, (bytes, bytearray)):
                    try:
                        technician['schedule_json'] = json.loads(raw.decode())
                    except Exception:
                        technician['schedule_json'] = {}
                elif isinstance(raw, dict):
                    pass
                else:
                    technician['schedule_json'] = {}
        if not technician:
            cursor.close()
            conn.close()
            flash('Technicien non trouvé', 'error')
            return redirect(url_for('technicians.index'))

        # Récupérer les bons de travail assignés
        cursor.execute(
            """
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
            """,
            (technician_id,),
        )

        work_orders = cursor.fetchall()

        # Statistiques du technicien
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_orders,
                SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned_orders
            FROM work_orders
            WHERE assigned_technician_id = %s
            """,
            (technician_id,),
        )

        stats = cursor.fetchone()

        # Calculer la charge actuelle (en pourcentage) basée sur estimated_duration
        try:
            cursor.execute(
                "SELECT COALESCE(SUM(estimated_duration),0) as total_minutes FROM work_orders WHERE assigned_technician_id = %s AND status IN ('assigned','in_progress')",
                (technician_id,),
            )
            srow = cursor.fetchone()
            total_minutes = int(srow.get('total_minutes', 0) or 0)
        except Exception:
            total_minutes = 0

        # défauts : max_weekly_hours et current_workload
        max_weekly_hours = technician.get('max_weekly_hours') or technician.get('max_hours', 40) or 40
        try:
            workload_pct = 0
            if max_weekly_hours and total_minutes:
                workload_hours = total_minutes / 60.0
                workload_pct = round((workload_hours / float(max_weekly_hours)) * 100)
        except Exception:
            workload_pct = 0

        # Assurez des clefs présentes pour le template
        if not isinstance(stats, dict):
            stats = stats or {}
        stats['current_workload'] = workload_pct
        technician['current_workload'] = workload_pct
        technician['max_weekly_hours'] = max_weekly_hours

        cursor.close()
        conn.close()

        return render_template(
            'technicians/view.html', technician=technician, work_orders=work_orders, stats=stats
        )

    except Exception as e:
        log_error(f"Erreur lors de la récupération du technicien {technician_id}: {e}")
        flash('Erreur lors du chargement du technicien', 'error')
        return redirect(url_for('technicians.index'))


@bp.route('/<int:technician_id>/edit', methods=['GET', 'POST'])
def edit_technician(technician_id):
    """Modifier un technicien"""
    if request.method == 'POST':
        try:
            _debug(f"POST /technicians/{technician_id}/edit - entering POST handler")
            # Prefer WTForms validation when possible (handles CSRF)
            form = TechnicianForm()

            # Determine source data: form if validated, otherwise fallback to raw form data
            use_form = False
            if form.validate_on_submit():
                use_form = True

            # Build schedule JSON from checkbox inputs
            days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
            # Accept both 'work_days' and 'work_days[]' names (templates differ)
            if request.form:
                work_days = request.form.getlist('work_days') or request.form.getlist('work_days[]') or []
            else:
                work_days = []
            schedule = {}
            for day in days:
                enabled = day in work_days
                start = request.form.get(f"{day}_start", '08:00')
                end = request.form.get(f"{day}_end", '17:00')
                schedule[day] = {'enabled': enabled, 'start': start, 'end': end}
            _debug(f"Built schedule: {json.dumps(schedule)}")

            # Photo handling
            photo_filename = None
            remove_photo = request.form.get('remove_photo') == 'true' or request.form.get('remove_photo') == 'on'
            if 'photo' in request.files and request.files['photo'] and request.files['photo'].filename:
                f = request.files['photo']
                # Save into project's static/uploads/photos directory
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                photos_dir = os.path.join(root_dir, 'static', 'uploads', 'photos')
                os.makedirs(photos_dir, exist_ok=True)
                filename = secure_filename(f.filename)
                save_path = os.path.join(photos_dir, filename)
                f.save(save_path)
                photo_filename = filename
                _debug(f"Saved uploaded photo to {save_path}")

            conn = get_db_connection()
            if not conn:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'})
                else:
                    flash('Erreur de connexion à la base de données', 'error')
                    return redirect(url_for('technicians.view_technician', technician_id=technician_id))

            cursor = conn.cursor()

            # Check if schedule_json column exists
            dbname = get_db_config().get('database')
            try:
                cursor.execute(
                    """
                    SELECT COUNT(*) as cnt
                    FROM information_schema.COLUMNS
                    WHERE table_schema = %s AND table_name = 'users' AND column_name = 'schedule_json'
                    """,
                    (dbname,),
                )
                col_info = cursor.fetchone()
                # support both tuple-based and dict-based cursors
                if isinstance(col_info, dict):
                    # 'cnt' should be present, fallback to first value
                    has_schedule_col = bool(col_info.get('cnt') or next(iter(col_info.values()), None))
                else:
                    has_schedule_col = bool(col_info and col_info[0])
            except Exception:
                has_schedule_col = False
            _debug(f"has_schedule_col={has_schedule_col}")

            # Choose values from WTForm when validated, otherwise fallback to request.form
            def gv(name, default=None):
                if use_form and hasattr(form, name):
                    val = getattr(form, name).data
                    return val if val is not None else default
                return request.form.get(name, default)

            params = {
                'name': gv('name'),
                'email': gv('email'),
                # Ensure role is never NULL
                'role': (gv('role') or 'technician'),
                'phone': gv('phone'),
                'employee_id': gv('employee_id'),
                'hire_date': gv('hire_date'),
                'birth_date': gv('birth_date'),
                'emergency_contact': gv('emergency_contact'),
                'address': gv('address'),
                'specialization': gv('specialization') or gv('specialty'),
                'certification_level': gv('certification_level'),
                'experience_years': gv('experience_years') or 0,
                'hourly_rate': gv('hourly_rate'),
                'zone': gv('zone'),
                'max_weekly_hours': gv('max_weekly_hours') or gv('max_hours') or 40,
                'vehicle_assigned': gv('vehicle_assigned'),
                'tools_assigned': gv('tools_assigned'),
                'notes': gv('notes'),
                'active': 1 if (gv('active') in [True, 'y', 'on', 'true', '1', 1]) else 0,
                'on_call': 1 if (gv('on_call') in [True, 'y', 'on', 'true', '1', 1]) else 0,
                'schedule_json': None,
                'photo': None,
                'id': technician_id,
            }

            # Defensive coercions: ensure no None values where NOT NULL is expected
            if not params.get('role'):
                params['role'] = 'technician'
            if params.get('active') is None:
                params['active'] = 1
            if params.get('on_call') is None:
                params['on_call'] = 0

            # Attach schedule JSON if possible (use module-level json to avoid shadowing)
            try:
                params['schedule_json'] = json.dumps(schedule)
            except Exception:
                params['schedule_json'] = None

            # Photo assignment/removal
            if photo_filename:
                params['photo'] = photo_filename
            elif remove_photo:
                params['photo'] = ''

            # Dynamically build UPDATE statement based on existing columns to avoid unknown column errors
            cursor.execute(
                """
                SELECT column_name FROM information_schema.COLUMNS
                WHERE table_schema = %s AND table_name = 'users'
                """,
                (dbname,),
            )
            existing_cols = set()
            for row in cursor.fetchall():
                col = None
                if isinstance(row, dict):
                    # prefer the explicit key, but tolerate other key names/ordering
                    col = row.get('column_name') or row.get('COLUMN_NAME') or next(iter(row.values()), None)
                else:
                    try:
                        col = row[0]
                    except Exception:
                        col = None

                if col:
                    existing_cols.add(col)

            _debug(f"Existing columns in users: {sorted(list(existing_cols))}")

            # If required optional columns are missing, do NOT attempt DDL at runtime in production.
            # Instead, log a warning so operators can run the appropriate migration.
            if 'schedule_json' not in existing_cols:
                log_warning("Colonne 'schedule_json' manquante dans la table users - exécutez la migration pour l'ajouter (Documents/migrations/2025-08-18_convert_schedule_json_to_json.sql)")
            if 'on_call' not in existing_cols:
                log_warning("Colonne 'on_call' manquante dans la table users - exécutez la migration pour l'ajouter (see Documents/migrations)")

            # Map param keys to candidate DB column names (use first existing candidate)
            col_candidates = {
                'name': ['name'],
                'email': ['email'],
                'role': ['role'],
                'phone': ['phone'],
                'employee_id': ['employee_id'],
                'hire_date': ['hire_date'],
                'birth_date': ['birth_date'],
                'emergency_contact': ['emergency_contact'],
                'address': ['address'],
                # support both 'specialization' and legacy 'specialty'
                'specialization': ['specialization', 'specialty'],
                'certification_level': ['certification_level'],
                'experience_years': ['experience_years'],
                'hourly_rate': ['hourly_rate'],
                'zone': ['zone'],
                'max_weekly_hours': ['max_weekly_hours', 'max_hours'],
                'vehicle_assigned': ['vehicle_assigned'],
                'tools_assigned': ['tools_assigned'],
                'notes': ['notes'],
                'is_active': ['is_active'],
                'on_call': ['on_call'],
                'schedule_json': ['schedule_json'],
                'photo': ['photo'],
            }

            updates = []
            exec_params = {'id': technician_id}
            for pkey, candidates in col_candidates.items():
                # choose the first candidate column that exists in DB
                chosen_col = None
                for c in candidates:
                    if c in existing_cols:
                        chosen_col = c
                        break

                if not chosen_col:
                    continue

                updates.append(f"{chosen_col}=%({pkey})s")

                # Resolve the value from params, with fallbacks for mismatched keys
                val = params.get(pkey)

                # common mismatch: application uses 'active' while DB column is 'is_active'
                if val is None and pkey == 'is_active':
                    val = params.get('active')

                # ensure numeric defaults where appropriate
                if val is None and pkey == 'experience_years':
                    val = 0
                if val is None and pkey in ('max_weekly_hours', 'hourly_rate'):
                    # sensible default values to avoid NOT NULL errors
                    val = params.get(pkey) or params.get('max_hours') or 0

                # schedule_json and photo may be explicitly set to '' to remove them
                if pkey == 'schedule_json' and val is None:
                    val = params.get('schedule_json')
                if pkey == 'photo' and val is None:
                    val = params.get('photo')

                exec_params[pkey] = val

            _debug(f"SQL updates: {updates}")
            _debug(f"Exec params: {exec_params}")

            # Ensure critical flags are present to avoid NOT NULL integrity errors
            if 'is_active' in existing_cols:
                # If the exec_params doesn't have is_active, try to map from params['active'] or default to 1
                ia = exec_params.get('is_active', None)
                if ia is None:
                    ia = params.get('active', 1)
                try:
                    ia = int(ia)
                except Exception:
                    ia = 1
                exec_params['is_active'] = ia

            # Always set updated_at
            set_clause = ", ".join(updates) if updates else ''
            if set_clause:
                # Allow updates even when the user is currently inactive
                sql = f"UPDATE users SET {set_clause}, updated_at=NOW() WHERE id=%(id)s"
            else:
                sql = "UPDATE users SET updated_at=NOW() WHERE id=%(id)s"

            cursor.execute(sql, exec_params)
            _debug(f"Executed SQL: {sql}")
            _debug(f"With params: {exec_params}")

            # TODO: handle technical_skills association table if present
            # skills = request.form.getlist('technical_skills')

            conn.commit()
            cursor.close()
            conn.close()

            log_info(f"Technicien modifié: {params.get('name')} (ID: {technician_id})")

            if request.is_json:
                return jsonify({'success': True, 'message': 'Technicien modifié avec succès'})
            else:
                flash('Technicien modifié avec succès', 'success')
                return redirect(url_for('technicians.view_technician', technician_id=technician_id))

        except Exception as e:
            # Log full traceback and attempt to include the SQL statement and execution params
            try:
                import traceback

                tb = traceback.format_exc()
                sql_text = locals().get('sql', None)
                exec_params = locals().get('exec_params', None)
                detail = (
                    f"Erreur lors de la modification du technicien {technician_id}: {e}; "
                    f"SQL={sql_text}; params={exec_params}; traceback={tb}"
                )
                log_error(detail)
            except Exception as log_exc:
                # Fallback to simpler logging if something goes wrong while logging
                log_error(f"Erreur lors du logging de l'exception pour le technicien {technician_id}: {log_exc}")
                log_error(f"Erreur originale: {e}")

            # Return a helpful JSON message for API callers; for form submissions keep UX the same
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la modification du technicien', 'error': str(e)})
            else:
                flash('Erreur lors de la modification du technicien', 'error')
                return redirect(url_for('technicians.view_technician', technician_id=technician_id))

    # GET request - afficher le formulaire de modification
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('technicians.index'))

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Allow opening the edit form even if the user is marked inactive
        cursor.execute("SELECT * FROM users WHERE id = %s", (technician_id,))
        technician = cursor.fetchone()

        # Defensive parsing: ensure schedule_json is a dict for templates
        if technician:
            raw = technician.get('schedule_json')
            _debug(f"GET /technicians/{technician_id}/edit - raw schedule_json from DB: {raw}")
            if raw is None:
                technician['schedule_json'] = {}
            else:
                if isinstance(raw, str):
                    try:
                        technician['schedule_json'] = json.loads(raw)
                        _debug(f"Parsed schedule_json (str) -> dict: {technician['schedule_json']}")
                    except Exception:
                        technician['schedule_json'] = {}
                elif isinstance(raw, (bytes, bytearray)):
                    try:
                        technician['schedule_json'] = json.loads(raw.decode())
                        _debug(f"Parsed schedule_json (bytes) -> dict: {technician['schedule_json']}")
                    except Exception:
                        technician['schedule_json'] = {}
                elif isinstance(raw, dict):
                    _debug(f"schedule_json already dict: {raw}")
                    pass
                else:
                    technician['schedule_json'] = {}

        # Normalize and expose commonly used keys for templates so inputs render correctly
        if technician:
            # provide a consistent 'specialization' key (templates use technician.specialization)
            technician['specialization'] = technician.get('specialization') or technician.get('specialty') or ''

            # Ensure text fields exist
            technician['certification_level'] = technician.get('certification_level') or ''
            technician['zone'] = technician.get('zone') or ''
            technician['vehicle_assigned'] = technician.get('vehicle_assigned') or ''
            technician['tools_assigned'] = technician.get('tools_assigned') or ''
            technician['notes'] = technician.get('notes') or ''

            # Numeric defaults
            technician['experience_years'] = technician.get('experience_years') or 0
            technician['max_weekly_hours'] = technician.get('max_weekly_hours') or technician.get('max_hours') or 40
            # hourly_rate stored as numeric/decimal - present as string in templates
            hr = technician.get('hourly_rate')
            technician['hourly_rate'] = str(hr) if hr is not None else '0.00'

            # Boolean flags: templates check technician.active and technician.on_call
            technician['active'] = bool(technician.get('is_active')) if technician.get('is_active') is not None else False
            technician['on_call'] = bool(technician.get('on_call')) if technician.get('on_call') is not None else False

        cursor.close()
        conn.close()

        if not technician:
            flash('Technicien non trouvé', 'error')
            return redirect(url_for('technicians.index'))

        # Fournir un objet form aux templates (WTForms) — le template utilise
        # souvent form.* mais préremplit les valeurs depuis `technician`.
        try:
            form = TechnicianForm()
            # Diagnostic: lister quelques attributs et vérifier la présence de birth_date
            try:
                attrs = [a for a in dir(form) if not a.startswith('_')]
                has_birth = hasattr(form, 'birth_date')
                log_info(f"TechnicianForm instantiated; birth_date present={has_birth}; sample_attrs={attrs[:40]}")
            except Exception:
                log_info("TechnicianForm instantiated but failed to introspect attributes")

            # Prefill WTForm with values from the technician row so required fields are shown and preserved
            try:
                form_data = {
                    'name': technician.get('name'),
                    'email': technician.get('email'),
                    'phone': technician.get('phone'),
                    'employee_id': technician.get('employee_id'),
                    'hire_date': technician.get('hire_date'),
                    'birth_date': technician.get('birth_date'),
                    'emergency_contact': technician.get('emergency_contact'),
                    'address': technician.get('address'),
                    # map DB 'specialty' -> form 'specialization' when appropriate
                    'specialization': technician.get('specialization') or technician.get('specialty'),
                    'certification_level': technician.get('certification_level'),
                    'experience_years': technician.get('experience_years'),
                    'hourly_rate': technician.get('hourly_rate'),
                    'zone': technician.get('zone'),
                    'max_weekly_hours': technician.get('max_weekly_hours') or technician.get('max_hours'),
                    'vehicle_assigned': technician.get('vehicle_assigned'),
                    'tools_assigned': technician.get('tools_assigned'),
                    'notes': technician.get('notes'),
                    'certifications': technician.get('certifications'),
                    'status': technician.get('status'),
                    # boolean fields: convert 0/1 to True/False
                    'active': bool(technician.get('is_active')) if technician.get('is_active') is not None else False,
                    'on_call': bool(technician.get('on_call')) if technician.get('on_call') is not None else False,
                }

                # WTForms will accept date strings or date objects; process will coerce as appropriate
                form.process(data=form_data)
            except Exception as e:
                log_error(f"Erreur lors du préremplissage du form pour le technicien {technician_id}: {e}")
        except Exception as e:
            # En cas d'erreur d'import/instanciation, fallback à None
            log_error(f"Erreur d'instanciation TechnicianForm: {e}")
            form = None

        # Provide selection lists for the edit template (could be loaded from DB/settings)
        specializations = ['Électrique', 'Mécanique', 'Climatisation', 'Plomberie', 'Informatique']
        certification_levels = ['', 'Niveau 1', 'Niveau 2', 'Niveau 3']
        zones = ['Nord', 'Sud', 'Est', 'Ouest', 'Centre']
        technical_skills = []

        return render_template('technicians/edit.html', technician=technician, form=form, specializations=specializations, certification_levels=certification_levels, zones=zones, technical_skills=technical_skills)

    except Exception as e:
        try:
            import traceback

            tb = traceback.format_exc()
            log_error(f"Erreur lors du chargement du formulaire d'édition pour le technicien {technician_id}: {e}; traceback={tb}")
        except Exception:
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

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Récupérer les bons de travail avec durées estimées
        cursor.execute(
            """
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
            """,
            (technician_id,),
        )

        workload = cursor.fetchall()

        # Calculer la charge totale
        total_hours = sum(order.get('estimated_duration', 0) for order in workload) / 60  # Convertir en heures

        cursor.close()
        conn.close()

        if request.is_json:
            return jsonify({'workload': workload, 'total_hours': round(total_hours, 2), 'total_orders': len(workload)})
        else:
            return render_template('technicians/workload.html', technician_id=technician_id, workload=workload, total_hours=round(total_hours, 2))

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

        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
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
            """
        )

        technicians = cursor.fetchall()

        # Ajouter des informations calculées
        for tech in technicians:
            tech['workload_hours'] = round(tech.get('total_workload_minutes', 0) / 60, 1)
            tech['availability_status'] = 'disponible' if tech.get('active_orders', 0) < 3 else 'occupé'

        cursor.close()
        conn.close()

        return jsonify({'technicians': technicians})

    except Exception as e:
        log_error(f"Erreur lors de la récupération des techniciens disponibles: {e}")
        return jsonify({'error': 'Erreur lors de la récupération des techniciens'}), 500


@bp.route('/schedule')
@bp.route('/<int:technician_id>/schedule')
def schedule(technician_id=None):
    """Afficher le planning d'un technicien (read-only).

    Supporte les deux formes de lien utilisées dans les templates :
    - url_for('technicians.schedule') avec paramètre query ?technician_id=...
    - url_for('technicians.schedule', technician_id=...)
    """
    try:
        # récupérer l'id soit depuis le chemin, soit depuis la querystring
        if technician_id is None:
            technician_id = request.args.get('technician_id', type=int)

        if not technician_id:
            flash('Technicien non spécifié', 'error')
            return redirect(url_for('technicians.index'))

        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            return redirect(url_for('technicians.index'))

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Récupérer d'abord les informations de base du technicien (sans dépendre de colonnes optionnelles)
        cursor.execute(
            "SELECT id, name FROM users WHERE id = %s",
            (technician_id,),
        )
        technician = cursor.fetchone()

        if not technician:
            cursor.close()
            conn.close()
            flash('Technicien non trouvé', 'error')
            return redirect(url_for('technicians.index'))

        # Vérifier si la colonne schedule_json existe avant d'essayer de la lire
        dbname = get_db_config().get('database')
        try:
            cursor.execute(
                """
                SELECT COUNT(*) as cnt
                FROM information_schema.COLUMNS
                WHERE table_schema = %s AND table_name = 'users' AND column_name = 'schedule_json'
                """,
                (dbname,),
            )
            col_info = cursor.fetchone()
            has_schedule_col = bool(col_info and col_info.get('cnt'))
        except Exception:
            has_schedule_col = False

        schedule = {}
        if has_schedule_col:
            try:
                cursor.execute("SELECT schedule_json FROM users WHERE id = %s", (technician_id,))
                row = cursor.fetchone()
                raw = row.get('schedule_json') if row else None
                if raw:
                    if isinstance(raw, str):
                        try:
                            schedule = json.loads(raw)
                        except Exception:
                            schedule = {}
                    else:
                        schedule = raw
            except Exception as e:
                log_error(f"Erreur lors de la lecture de schedule_json pour {technician_id}: {e}")
                schedule = {}

        cursor.close()
        conn.close()

        technician['schedule_json'] = schedule or {}

        return render_template('technicians/schedule.html', technician=technician)

    except Exception as e:
        log_error(f"Erreur lors de la récupération du planning du technicien {technician_id}: {e}")
        flash('Erreur lors du chargement du planning', 'error')
        return redirect(url_for('technicians.index'))
