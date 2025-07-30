from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'une-autre-super-cle-secrete'

# --- Direct Configuration ---
MYSQL_HOST = '192.168.50.101'
MYSQL_PORT = 3306
MYSQL_USER = 'gsicloud'
MYSQL_PASSWORD = 'TCOChoosenOne204$'
MYSQL_DB = 'gsi'

# Fonction utilitaire pour obtenir une connexion MySQL
def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            session['user_email'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid login'
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
            conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        if session['user_role'] == 'technician':
            cur.execute("""
                SELECT i.id, i.customer_name, i.customer_address, i.status, i.technician_id, 
                       i.start_time, i.end_time, u.name as technician_name 
                FROM interventions i 
                LEFT JOIN users u ON i.technician_id = u.id 
                WHERE i.technician_id = %s 
                ORDER BY i.start_time DESC
            """, (session['user_id'],))
        else:
            cur.execute("""
                SELECT i.id, i.customer_name, i.customer_address, i.status, i.technician_id,
                       i.start_time, i.end_time, u.name as technician_name 
                FROM interventions i 
                LEFT JOIN users u ON i.technician_id = u.id 
                ORDER BY i.start_time DESC
            """)
        interventions = cur.fetchall()
        # Récupérer la liste des techniciens pour le modal de création
        cur.execute("SELECT id, name FROM users WHERE role = 'technician'")
        technicians = cur.fetchall()
    conn.close()
    return render_template('dashboard.html', interventions=interventions, technicians=technicians)

@app.route('/intervention/new', methods=['POST'])
def create_intervention():
    if 'user_id' not in session or session.get('user_role') == 'technician':
        return redirect(url_for('login'))
    customer_name = request.form['customer_name']
    customer_address = request.form['customer_address']
    technician_id = request.form['technician_id']
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO interventions (customer_name, customer_address, technician_id, status) VALUES (%s, %s, %s, 'pending')",
            (customer_name, customer_address, technician_id)
        )
        conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/intervention/<int:id>')
def intervention(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT i.*, u.name as technician_name FROM interventions i LEFT JOIN users u ON i.technician_id = u.id WHERE i.id = %s", (id,))
        intervention_data = cur.fetchone()
        if not intervention_data:
            conn.close()
            return "Intervention not found", 404
        if session['user_role'] == 'technician' and intervention_data['technician_id'] != session['user_id']:
            conn.close()
            return "Access denied", 403
        cur.execute("SELECT s.*, p.DESCR as product_name FROM intervention_steps s LEFT JOIN bdm.inprix p ON s.product_id = p.CODEAP WHERE s.intervention_id = %s ORDER BY s.timestamp ASC", (id,))
        steps = cur.fetchall()
        cur.execute("SELECT CODEAP, DESCR FROM bdm.inprix WHERE ACTIF = 'O'")
        products = cur.fetchall()
        # Récupérer la liste des techniciens pour le modal d'édition
        cur.execute("SELECT id, name FROM users WHERE role = 'technician'")
        technicians = cur.fetchall()
    conn.close()
    return render_template('intervention.html', intervention=intervention_data, steps=steps, products=products, technicians=technicians)

@app.route('/intervention/<int:id>/add_step', methods=['POST'])
def add_step(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    description = request.form['description']
    product_id = request.form.get('product_id')
    conn = get_db_connection()
    with conn.cursor() as cur:
        if product_id:
            cur.execute("INSERT INTO intervention_steps (intervention_id, description, timestamp, product_id) VALUES (%s, %s, NOW(), %s)", (id, description, product_id))
        else:
            cur.execute("INSERT INTO intervention_steps (intervention_id, description, timestamp) VALUES (%s, %s, NOW())", (id, description))
        conn.commit()
    conn.close()
    return redirect(url_for('intervention', id=id))

@app.route('/intervention/<int:id>/step/<int:step_id>/edit', methods=['POST'])
def edit_step(id, step_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM intervention_steps WHERE id = %s AND intervention_id = %s", (step_id, id))
        step = cur.fetchone()
        if not step:
            conn.close()
            return "Étape introuvable", 404
        if request.method == 'POST':
            description = request.form['description']
            cur.execute("UPDATE intervention_steps SET description=%s WHERE id=%s", (description, step_id))
            conn.commit()
            conn.close()
            return redirect(url_for('intervention', id=id))
    conn.close()
    return redirect(url_for('intervention', id=id))

@app.route('/intervention/<int:id>/delete_step/<int:step_id>', methods=['POST'])
def delete_step(id, step_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM intervention_steps WHERE id = %s AND intervention_id = %s", (step_id, id))
        conn.commit()
    conn.close()
    return redirect(url_for('intervention', id=id))

@app.route('/intervention/<int:id>/start', methods=['POST'])
def start_intervention(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE interventions SET status = 'in_progress', start_time = NOW() WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('intervention', id=id))

@app.route('/intervention/<int:id>/stop', methods=['POST'])
def stop_intervention(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE interventions SET status = 'completed', end_time = NOW() WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('intervention', id=id))

@app.route('/intervention/<int:id>/edit', methods=['GET', 'POST'])
def edit_intervention(id):
    if 'user_id' not in session or session.get('user_role') == 'technician':
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM interventions WHERE id = %s", (id,))
        intervention = cur.fetchone()
        if not intervention:
            conn.close()
            return "Intervention not found", 404
        if request.method == 'POST':
            customer_name = request.form['customer_name']
            customer_address = request.form['customer_address']
            technician_id = request.form['technician_id']
            cur.execute(
                "UPDATE interventions SET customer_name=%s, customer_address=%s, technician_id=%s WHERE id=%s",
                (customer_name, customer_address, technician_id, id)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('intervention', id=id))
    conn.close()
    # Rediriger vers la page intervention au lieu de rendre un template séparé
    return redirect(url_for('intervention', id=id))

@app.route('/intervention/<int:id>/delete', methods=['POST'])
def delete_intervention(id):
    if 'user_id' not in session or session.get('user_role') == 'technician':
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM intervention_steps WHERE intervention_id = %s", (id,))
        cur.execute("DELETE FROM interventions WHERE id = %s", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile', methods=['POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    conn = get_db_connection()
    with conn.cursor() as cur:
        if password:
            hashed_password = generate_password_hash(password)
            cur.execute("UPDATE users SET name=%s, email=%s, password=%s, role=%s WHERE id=%s", (name, email, hashed_password, role, session['user_id']))
        else:
            cur.execute("UPDATE users SET name=%s, email=%s, role=%s WHERE id=%s", (name, email, role, session['user_id']))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
    conn.close()
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['user_role'] = user['role']
    return redirect(url_for('dashboard'))

@app.route('/technicians')
def technicians():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE role = 'technician'")
        techs = cur.fetchall()
    conn.close()
    return render_template('technicians_management.html', technicians=techs)

@app.route('/technician/new', methods=['GET', 'POST'])
def new_technician():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'technician')", (name, email, hashed_password))
            conn.commit()
        conn.close()
        return redirect(url_for('technicians'))
    # Rediriger vers la page technicians au lieu de rendre un template séparé
    return redirect(url_for('technicians'))

@app.route('/technician/<int:id>/edit', methods=['GET', 'POST'])
def edit_technician(id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s AND role = 'technician'", (id,))
        tech = cur.fetchone()
        if not tech:
            conn.close()
            return "Technicien introuvable", 404
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            if password:
                hashed_password = generate_password_hash(password)
                cur.execute("UPDATE users SET name=%s, email=%s, password=%s WHERE id=%s", (name, email, hashed_password, id))
            else:
                cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, id))
            conn.commit()
            conn.close()
            return redirect(url_for('technicians'))
    conn.close()
    # Rediriger vers la page technicians au lieu de rendre un template séparé
    return redirect(url_for('technicians'))

@app.route('/technician/<int:id>/delete', methods=['POST'])
def delete_technician(id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Récupérer le nom du technicien pour le message
            cur.execute("SELECT name FROM users WHERE id = %s AND role = 'technician'", (id,))
            technician = cur.fetchone()
            
            if not technician:
                flash('Technicien introuvable', 'error')
                conn.close()
                return redirect(url_for('technicians'))
            
            # Vérifier s'il y a des interventions associées
            cur.execute("SELECT COUNT(*) as count FROM interventions WHERE technician_id = %s", (id,))
            result = cur.fetchone()
            
            if result['count'] > 0:
                # Il y a des interventions associées, on ne peut pas supprimer
                flash(f'Impossible de supprimer {technician["name"]} car il a {result["count"]} intervention(s) associée(s). Veuillez d\'abord réassigner ou supprimer ces interventions.', 'error')
                conn.close()
                return redirect(url_for('technicians'))
            
            # Aucune intervention associée, on peut supprimer
            cur.execute("DELETE FROM users WHERE id = %s AND role = 'technician'", (id,))
            conn.commit()
            flash(f'Technicien {technician["name"]} supprimé avec succès', 'success')
            
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
        conn.close()
        return redirect(url_for('technicians'))
    
    conn.close()
    return redirect(url_for('technicians'))

@app.route('/technician/<int:id>/reassign', methods=['POST'])
def reassign_technician_interventions(id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    
    new_technician_id = request.form.get('new_technician_id')
    if not new_technician_id:
        flash('Veuillez sélectionner un technicien de remplacement', 'error')
        return redirect(url_for('technicians'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Vérifier que le nouveau technicien existe
            cur.execute("SELECT name FROM users WHERE id = %s AND role = 'technician'", (new_technician_id,))
            new_tech = cur.fetchone()
            
            if not new_tech:
                flash('Technicien de remplacement introuvable', 'error')
                conn.close()
                return redirect(url_for('technicians'))
            
            # Obtenir les informations de l'ancien technicien
            cur.execute("SELECT name FROM users WHERE id = %s AND role = 'technician'", (id,))
            old_tech = cur.fetchone()
            
            if not old_tech:
                flash('Technicien à supprimer introuvable', 'error')
                conn.close()
                return redirect(url_for('technicians'))
            
            # Compter les interventions à réassigner
            cur.execute("SELECT COUNT(*) as count FROM interventions WHERE technician_id = %s", (id,))
            intervention_count = cur.fetchone()['count']
            
            if intervention_count == 0:
                flash('Aucune intervention à réassigner', 'info')
                conn.close()
                return redirect(url_for('technicians'))
            
            # Réassigner les interventions
            cur.execute("UPDATE interventions SET technician_id = %s WHERE technician_id = %s", 
                       (new_technician_id, id))
            
            # Supprimer l'ancien technicien
            cur.execute("DELETE FROM users WHERE id = %s AND role = 'technician'", (id,))
            
            conn.commit()
            flash(f'{intervention_count} intervention(s) réassignée(s) de {old_tech["name"]} vers {new_tech["name"]}. Technicien supprimé avec succès.', 'success')
            
    except Exception as e:
        conn.rollback()
        flash(f'Erreur lors de la réassignation: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('technicians'))

# ===== WORK ORDERS ROUTES =====

@app.route('/work_orders')
def work_orders():
    """Page principale de gestion des travaux demandés"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Récupérer tous les travaux avec les informations des techniciens
            cur.execute("""
                SELECT wo.*, u_tech.name as technician_name, u_creator.name as creator_name,
                       COUNT(wop.id) as products_count
                FROM work_orders wo
                LEFT JOIN users u_tech ON wo.assigned_technician_id = u_tech.id
                LEFT JOIN users u_creator ON wo.created_by_user_id = u_creator.id
                LEFT JOIN work_order_products wop ON wo.id = wop.work_order_id
                GROUP BY wo.id
                ORDER BY wo.created_at DESC
            """)
            work_orders = cur.fetchall()
            
            # Récupérer la liste des techniciens pour l'assignation
            cur.execute("SELECT id, name FROM users WHERE role = 'technician' ORDER BY name")
            technicians = cur.fetchall()
            
    except Exception as e:
        flash(f'Erreur lors du chargement des travaux: {str(e)}', 'error')
        work_orders = []
        technicians = []
    finally:
        conn.close()
    
    return render_template('work_orders.html', work_orders=work_orders, technicians=technicians)

@app.route('/work_orders/new', methods=['GET', 'POST'])
def create_work_order():
    """Créer un nouveau travail demandé"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            claim_number = request.form.get('claim_number', '').strip()
            customer_name = request.form.get('customer_name', '').strip()
            customer_address = request.form.get('customer_address', '').strip()
            customer_phone = request.form.get('customer_phone', '').strip()
            customer_email = request.form.get('customer_email', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', 'medium')
            assigned_technician_id = request.form.get('assigned_technician_id')
            estimated_duration = request.form.get('estimated_duration')
            estimated_cost = request.form.get('estimated_cost')
            scheduled_date = request.form.get('scheduled_date')
            notes = request.form.get('notes', '').strip()
            
            # Validations
            if not claim_number:
                flash('Le numéro de réclamation est obligatoire', 'error')
                return redirect(url_for('create_work_order'))
            
            if not customer_name:
                flash('Le nom du client est obligatoire', 'error')
                return redirect(url_for('create_work_order'))
            
            if not description:
                flash('La description est obligatoire', 'error')
                return redirect(url_for('create_work_order'))
            
            # Traitement des valeurs optionnelles
            if assigned_technician_id == '':
                assigned_technician_id = None
            if estimated_duration == '':
                estimated_duration = None
            if estimated_cost == '':
                estimated_cost = None
            if scheduled_date == '':
                scheduled_date = None
            if customer_phone == '':
                customer_phone = None
            if customer_email == '':
                customer_email = None
            if notes == '':
                notes = None
            
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    # Vérifier l'unicité du numéro de réclamation
                    cur.execute("SELECT id FROM work_orders WHERE claim_number = %s", (claim_number,))
                    if cur.fetchone():
                        flash('Ce numéro de réclamation existe déjà', 'error')
                        return redirect(url_for('create_work_order'))
                    
                    # Insérer le nouveau travail
                    cur.execute("""
                        INSERT INTO work_orders 
                        (claim_number, customer_name, customer_address, customer_phone, customer_email,
                         description, priority, assigned_technician_id, created_by_user_id, 
                         estimated_duration, estimated_cost, scheduled_date, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (claim_number, customer_name, customer_address, customer_phone, customer_email,
                          description, priority, assigned_technician_id, session['user_id'],
                          estimated_duration, estimated_cost, scheduled_date, notes))
                    
                    work_order_id = cur.lastrowid
                    
                    # Ajouter l'historique de statut
                    cur.execute("""
                        INSERT INTO work_order_status_history 
                        (work_order_id, new_status, changed_by_user_id, change_reason)
                        VALUES (%s, %s, %s, %s)
                    """, (work_order_id, 'draft', session['user_id'], 'Création du travail'))
                    
                    conn.commit()
                    flash('Travail créé avec succès', 'success')
                    return redirect(url_for('work_orders'))
                    
            except pymysql.IntegrityError:
                flash('Erreur: ce numéro de réclamation existe déjà', 'error')
                return redirect(url_for('create_work_order'))
            except Exception as e:
                flash(f'Erreur lors de la création: {str(e)}', 'error')
                return redirect(url_for('create_work_order'))
            finally:
                conn.close()
                
        except Exception as e:
            flash(f'Erreur lors du traitement des données: {str(e)}', 'error')
            return redirect(url_for('create_work_order'))
    
    # GET: afficher le formulaire
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM users WHERE role = 'technician' ORDER BY name")
            technicians = cur.fetchall()
    except Exception as e:
        flash(f'Erreur lors du chargement: {str(e)}', 'error')
        technicians = []
    finally:
        conn.close()
    
    return render_template('work_order_form.html', technicians=technicians, action='create')

@app.route('/work_orders/<int:id>/edit', methods=['GET', 'POST'])
def edit_work_order(id):
    """Modifier un travail demandé existant"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            claim_number = request.form.get('claim_number', '').strip()
            customer_name = request.form.get('customer_name', '').strip()
            customer_address = request.form.get('customer_address', '').strip()
            customer_phone = request.form.get('customer_phone', '').strip()
            customer_email = request.form.get('customer_email', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', 'medium')
            status = request.form.get('status', 'draft')
            assigned_technician_id = request.form.get('assigned_technician_id')
            estimated_duration = request.form.get('estimated_duration')
            estimated_cost = request.form.get('estimated_cost')
            scheduled_date = request.form.get('scheduled_date')
            notes = request.form.get('notes', '').strip()
            
            # Validations
            if not claim_number:
                flash('Le numéro de réclamation est obligatoire', 'error')
                return redirect(url_for('edit_work_order', id=id))
            
            if not customer_name:
                flash('Le nom du client est obligatoire', 'error')
                return redirect(url_for('edit_work_order', id=id))
            
            if not description:
                flash('La description est obligatoire', 'error')
                return redirect(url_for('edit_work_order', id=id))
            
            # Traitement des valeurs optionnelles
            if assigned_technician_id == '':
                assigned_technician_id = None
            if estimated_duration == '':
                estimated_duration = None
            if estimated_cost == '':
                estimated_cost = None
            if scheduled_date == '':
                scheduled_date = None
            if customer_phone == '':
                customer_phone = None
            if customer_email == '':
                customer_email = None
            if notes == '':
                notes = None
            
            try:
                with conn.cursor() as cur:
                    # Récupérer l'ancien statut pour l'historique
                    cur.execute("SELECT status FROM work_orders WHERE id = %s", (id,))
                    old_record = cur.fetchone()
                    if not old_record:
                        flash('Travail non trouvé', 'error')
                        return redirect(url_for('work_orders'))
                    
                    old_status = old_record['status']
                    
                    # Vérifier l'unicité du numéro de réclamation (sauf pour ce record)
                    cur.execute("SELECT id FROM work_orders WHERE claim_number = %s AND id != %s", (claim_number, id))
                    if cur.fetchone():
                        flash('Ce numéro de réclamation existe déjà', 'error')
                        return redirect(url_for('edit_work_order', id=id))
                    
                    # Mettre à jour le travail
                    cur.execute("""
                        UPDATE work_orders SET 
                        claim_number = %s, customer_name = %s, customer_address = %s, 
                        customer_phone = %s, customer_email = %s, description = %s, 
                        priority = %s, status = %s, assigned_technician_id = %s,
                        estimated_duration = %s, estimated_cost = %s, scheduled_date = %s, notes = %s
                        WHERE id = %s
                    """, (claim_number, customer_name, customer_address, customer_phone, customer_email,
                          description, priority, status, assigned_technician_id, estimated_duration, 
                          estimated_cost, scheduled_date, notes, id))
                    
                    # Ajouter l'historique si le statut a changé
                    if old_status != status:
                        cur.execute("""
                            INSERT INTO work_order_status_history 
                            (work_order_id, old_status, new_status, changed_by_user_id, change_reason)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (id, old_status, status, session['user_id'], 'Modification du travail'))
                    
                    conn.commit()
                    flash('Travail modifié avec succès', 'success')
                    return redirect(url_for('work_orders'))
                    
            except pymysql.IntegrityError:
                flash('Erreur: ce numéro de réclamation existe déjà', 'error')
                return redirect(url_for('edit_work_order', id=id))
            except Exception as e:
                flash(f'Erreur lors de la modification: {str(e)}', 'error')
                return redirect(url_for('edit_work_order', id=id))
                
        except Exception as e:
            flash(f'Erreur lors du traitement des données: {str(e)}', 'error')
            return redirect(url_for('edit_work_order', id=id))
        finally:
            conn.close()
    
    # GET: afficher le formulaire avec les données existantes
    try:
        with conn.cursor() as cur:
            # Récupérer le travail
            cur.execute("SELECT * FROM work_orders WHERE id = %s", (id,))
            work_order = cur.fetchone()
            if not work_order:
                flash('Travail non trouvé', 'error')
                return redirect(url_for('work_orders'))
            
            # Récupérer la liste des techniciens
            cur.execute("SELECT id, name FROM users WHERE role = 'technician' ORDER BY name")
            technicians = cur.fetchall()
            
    except Exception as e:
        flash(f'Erreur lors du chargement: {str(e)}', 'error')
        return redirect(url_for('work_orders'))
    finally:
        conn.close()
    
    return render_template('work_order_form.html', work_order=work_order, technicians=technicians, action='edit')

@app.route('/work_orders/<int:id>/delete', methods=['POST'])
def delete_work_order(id):
    """Supprimer un travail demandé"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Vérifier si le travail a des produits associés
            cur.execute("SELECT COUNT(*) as count FROM work_order_products WHERE work_order_id = %s", (id,))
            products_count = cur.fetchone()['count']
            
            if products_count > 0:
                flash('Impossible de supprimer ce travail car il a des produits associés', 'error')
                return redirect(url_for('work_orders'))
            
            # Supprimer le travail (l'historique sera supprimé automatiquement via CASCADE)
            cur.execute("DELETE FROM work_orders WHERE id = %s", (id,))
            
            if cur.rowcount > 0:
                conn.commit()
                flash('Travail supprimé avec succès', 'success')
            else:
                flash('Travail non trouvé', 'error')
                
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('work_orders'))

@app.route('/work_orders/<int:id>/products')
def work_order_products(id):
    """Gérer les produits d'un travail demandé"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Récupérer le travail
            cur.execute("SELECT * FROM work_orders WHERE id = %s", (id,))
            work_order = cur.fetchone()
            if not work_order:
                flash('Travail non trouvé', 'error')
                return redirect(url_for('work_orders'))
            
            # Récupérer les produits du travail
            cur.execute("""
                SELECT * FROM work_order_products 
                WHERE work_order_id = %s 
                ORDER BY created_at
            """, (id,))
            products = cur.fetchall()
            
    except Exception as e:
        flash(f'Erreur lors du chargement: {str(e)}', 'error')
        return redirect(url_for('work_orders'))
    finally:
        conn.close()
    
    return render_template('work_order_products.html', work_order=work_order, products=products)

@app.route('/work_orders/<int:work_order_id>/products/add', methods=['POST'])
def add_work_order_product(work_order_id):
    """Ajouter un produit à un travail demandé"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        product_name = request.form.get('product_name', '').strip()
        product_reference = request.form.get('product_reference', '').strip()
        quantity = request.form.get('quantity')
        unit_price = request.form.get('unit_price')
        total_price = request.form.get('total_price')
        notes = request.form.get('notes', '').strip()
        
        # Validations
        if not product_name:
            flash('Le nom du produit est obligatoire', 'error')
            return redirect(url_for('work_order_products', id=work_order_id))
        
        if not quantity or float(quantity) <= 0:
            flash('La quantité doit être supérieure à 0', 'error')
            return redirect(url_for('work_order_products', id=work_order_id))
        
        # Traitement des valeurs optionnelles
        if product_reference == '':
            product_reference = None
        if unit_price == '':
            unit_price = None
        if total_price == '':
            total_price = None
        if notes == '':
            notes = None
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Vérifier que le travail existe
                cur.execute("SELECT id FROM work_orders WHERE id = %s", (work_order_id,))
                if not cur.fetchone():
                    flash('Travail non trouvé', 'error')
                    return redirect(url_for('work_orders'))
                
                # Insérer le produit
                cur.execute("""
                    INSERT INTO work_order_products 
                    (work_order_id, product_name, product_reference, quantity, 
                     unit_price, total_price, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (work_order_id, product_name, product_reference, quantity,
                      unit_price, total_price, notes))
                
                conn.commit()
                flash('Produit ajouté avec succès', 'success')
                
        except Exception as e:
            flash(f'Erreur lors de l\'ajout: {str(e)}', 'error')
        finally:
            conn.close()
            
    except Exception as e:
        flash(f'Erreur lors du traitement des données: {str(e)}', 'error')
    
    return redirect(url_for('work_order_products', id=work_order_id))

@app.route('/work_orders/<int:work_order_id>/products/<int:product_id>/edit', methods=['POST'])
def edit_work_order_product(work_order_id, product_id):
    """Modifier un produit d'un travail demandé"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        product_name = request.form.get('product_name', '').strip()
        product_reference = request.form.get('product_reference', '').strip()
        quantity = request.form.get('quantity')
        unit_price = request.form.get('unit_price')
        total_price = request.form.get('total_price')
        notes = request.form.get('notes', '').strip()
        
        # Validations
        if not product_name:
            flash('Le nom du produit est obligatoire', 'error')
            return redirect(url_for('work_order_products', id=work_order_id))
        
        if not quantity or float(quantity) <= 0:
            flash('La quantité doit être supérieure à 0', 'error')
            return redirect(url_for('work_order_products', id=work_order_id))
        
        # Traitement des valeurs optionnelles
        if product_reference == '':
            product_reference = None
        if unit_price == '':
            unit_price = None
        if total_price == '':
            total_price = None
        if notes == '':
            notes = None
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Vérifier que le produit et le travail existent
                cur.execute("""
                    SELECT wop.id FROM work_order_products wop
                    JOIN work_orders wo ON wop.work_order_id = wo.id
                    WHERE wop.id = %s AND wo.id = %s
                """, (product_id, work_order_id))
                
                if not cur.fetchone():
                    flash('Produit non trouvé', 'error')
                    return redirect(url_for('work_order_products', id=work_order_id))
                
                # Mettre à jour le produit
                cur.execute("""
                    UPDATE work_order_products SET 
                    product_name = %s, product_reference = %s, quantity = %s,
                    unit_price = %s, total_price = %s, notes = %s
                    WHERE id = %s
                """, (product_name, product_reference, quantity, unit_price, 
                      total_price, notes, product_id))
                
                conn.commit()
                flash('Produit modifié avec succès', 'success')
                
        except Exception as e:
            flash(f'Erreur lors de la modification: {str(e)}', 'error')
        finally:
            conn.close()
            
    except Exception as e:
        flash(f'Erreur lors du traitement des données: {str(e)}', 'error')
    
    return redirect(url_for('work_order_products', id=work_order_id))

@app.route('/work_orders/<int:work_order_id>/products/<int:product_id>/delete', methods=['POST'])
def delete_work_order_product(work_order_id, product_id):
    """Supprimer un produit d'un travail demandé"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Vérifier que le produit et le travail existent
            cur.execute("""
                SELECT wop.id FROM work_order_products wop
                JOIN work_orders wo ON wop.work_order_id = wo.id
                WHERE wop.id = %s AND wo.id = %s
            """, (product_id, work_order_id))
            
            if not cur.fetchone():
                flash('Produit non trouvé', 'error')
                return redirect(url_for('work_order_products', id=work_order_id))
            
            # Supprimer le produit
            cur.execute("DELETE FROM work_order_products WHERE id = %s", (product_id,))
            
            if cur.rowcount > 0:
                conn.commit()
                flash('Produit supprimé avec succès', 'success')
            else:
                flash('Produit non trouvé', 'error')
                
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('work_order_products', id=work_order_id))

@app.route('/api/work_orders/search')
def search_work_orders():
    """API pour la recherche de travaux demandés"""
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}, 403
    
    query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    technician_filter = request.args.get('technician', '')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT wo.*, u_tech.name as technician_name, u_creator.name as creator_name,
                       COUNT(wop.id) as products_count
                FROM work_orders wo
                LEFT JOIN users u_tech ON wo.assigned_technician_id = u_tech.id
                LEFT JOIN users u_creator ON wo.created_by_user_id = u_creator.id
                LEFT JOIN work_order_products wop ON wo.id = wop.work_order_id
                WHERE 1=1
            """
            params = []
            
            if query:
                sql += " AND (wo.claim_number LIKE %s OR wo.customer_name LIKE %s OR wo.description LIKE %s)"
                like_query = f"%{query}%"
                params.extend([like_query, like_query, like_query])
            
            if status_filter:
                sql += " AND wo.status = %s"
                params.append(status_filter)
            
            if priority_filter:
                sql += " AND wo.priority = %s"
                params.append(priority_filter)
            
            if technician_filter:
                sql += " AND wo.assigned_technician_id = %s"
                params.append(technician_filter)
            
            sql += " GROUP BY wo.id ORDER BY wo.created_at DESC LIMIT 100"
            
            cur.execute(sql, params)
            work_orders = cur.fetchall()
            
            return {'work_orders': work_orders}
            
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        conn.close()

@app.route('/api/technician/<int:id>/interventions/count')
def get_technician_interventions_count(id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return {'error': 'Unauthorized'}, 403
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM interventions WHERE technician_id = %s", (id,))
            result = cur.fetchone()
            return {'count': result['count']}
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        conn.close()

@app.route('/api/work_orders/<int:work_order_id>/products/<int:product_id>')
def get_work_order_product(work_order_id, product_id):
    """API pour récupérer les détails d'un produit"""
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}, 403
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT wop.* FROM work_order_products wop
                JOIN work_orders wo ON wop.work_order_id = wo.id
                WHERE wop.id = %s AND wo.id = %s
            """, (product_id, work_order_id))
            
            product = cur.fetchone()
            if not product:
                return {'error': 'Product not found'}, 404
            
            return product
            
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5050)
