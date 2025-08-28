# =====================================================
# EXTENSIONS SPRINT 5-6 - CUSTOMER 360 AVANCÉ
# =====================================================
# À ajouter dans le fichier routes/customers.py existant

# Imports additionnels requis (à ajouter en haut du fichier)
import os
import hashlib
import json
import math
import pymysql
from datetime import datetime, timedelta
from flask import current_app, send_file, make_response
from werkzeug.utils import secure_filename

# =====================================================
# TIMELINE UNIFIÉE AVEC COMMUNICATIONS
# =====================================================

@bp.route('/<int:customer_id>/timeline/export')
def export_customer_timeline(customer_id):
    """Exporte la timeline en différents formats"""
    try:
        format_type = request.args.get('format', 'csv')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer toutes les activités
        cursor.execute("""
            SELECT ca.*, u.name as actor_name
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id
            WHERE ca.customer_id = %s
            ORDER BY ca.created_at DESC
        """, [customer_id])
        activities = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if format_type == 'csv':
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Date', 'Type', 'Titre', 'Description', 'Acteur'])
            
            for activity in activities:
                writer.writerow([
                    activity['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    activity['activity_type'],
                    activity['title'],
                    activity['description'] or '',
                    activity['actor_name'] or 'Système'
                ])
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.csv'
            return response
        
        elif format_type == 'json':
            # Conversion datetime pour JSON
            for activity in activities:
                if isinstance(activity['created_at'], datetime):
                    activity['created_at'] = activity['created_at'].isoformat()
            
            response = make_response(json.dumps(activities, indent=2, ensure_ascii=False))
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.json'
            return response
        
        else:
            return jsonify({'success': False, 'message': 'Format non supporté'}), 400
            
    except Exception as e:
        log_error(f"Erreur export timeline: {e}")
        return jsonify({'success': False, 'message': 'Erreur export timeline'}), 500

# =====================================================
# DOCUMENTS & SIGNATURE ÉLECTRONIQUE
# =====================================================

@bp.route('/<int:customer_id>/documents', methods=['GET'])
def get_customer_documents_complete(customer_id):
    """Liste complète des documents d'un client avec filtres"""
    try:
        document_type = request.args.get('type')
        signed_only = request.args.get('signed') == 'true'
        category = request.args.get('category')
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT cd.*, u.name as created_by_name,
                   CASE 
                       WHEN cd.expires_at IS NOT NULL AND cd.expires_at < NOW() THEN 'expired'
                       WHEN cd.is_signed = 1 THEN 'signed'
                       ELSE 'pending'
                   END as status
            FROM customer_documents cd
            LEFT JOIN users u ON cd.created_by = u.id
            WHERE cd.customer_id = %s
        """
        params = [customer_id]
        
        if document_type:
            query += " AND cd.document_type = %s"
            params.append(document_type)
        
        if signed_only:
            query += " AND cd.is_signed = 1"
        
        if category:
            query += " AND cd.category = %s"
            params.append(category)
        
        query += " ORDER BY cd.created_at DESC"
        
        cursor.execute(query, params)
        documents = cursor.fetchall()
        
        # Statistiques des documents
        cursor.execute("""
            SELECT 
                COUNT(*) as total_documents,
                SUM(CASE WHEN is_signed = 1 THEN 1 ELSE 0 END) as signed_documents,
                SUM(CASE WHEN expires_at IS NOT NULL AND expires_at < NOW() THEN 1 ELSE 0 END) as expired_documents,
                SUM(file_size) as total_size
            FROM customer_documents
            WHERE customer_id = %s
        """, [customer_id])
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True, 
                'documents': documents,
                'stats': stats
            })
            
        return render_template(
            'customers/documents.html', 
            customer_id=customer_id,
            documents=documents,
            stats=stats
        )
    except Exception as e:
        log_error(f"Erreur récupération documents: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur récupération documents'}), 500
        flash('Erreur chargement documents', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

@bp.route('/<int:customer_id>/documents/upload', methods=['POST'])
def upload_customer_document(customer_id):
    """Upload sécurisé de document avec calcul de hash"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
        
        # Validation des paramètres
        document_type = request.form.get('document_type')
        title = request.form.get('title', 'Document sans titre')
        category = request.form.get('category', 'administrative')
        access_level = request.form.get('access_level', 'private')
        
        if not document_type:
            return jsonify({'success': False, 'message': 'Type de document requis'}), 400
        
        # Validation du type de fichier
        allowed_extensions = {'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({'success': False, 'message': f'Type de fichier non autorisé. Types acceptés: {", ".join(allowed_extensions)}'}), 400
        
        # Configuration upload
        upload_base = current_app.config.get('UPLOAD_FOLDER', '/tmp')
        upload_dir = os.path.join(upload_base, 'customers', str(customer_id), 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Nom de fichier sécurisé avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(upload_dir, filename)
        
        # Sauvegarde du fichier
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Calcul hash SHA-256 pour intégrité
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
        
        # Utilisateur courant
        user_id = session.get('user_id')  # Adaptation selon votre système d'auth
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Enregistrement en base
        cursor.execute("""
            INSERT INTO customer_documents
            (customer_id, document_type, category, title, filename, file_path, 
             file_size, mime_type, hash_sha256, access_level, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, document_type, category, title, filename, file_path,
            file_size, file.content_type, file_hash, access_level, user_id
        ])
        document_id = cursor.lastrowid
        
        # Log d'activité
        log_customer_activity(
            customer_id, 
            'document', 
            f"Document ajouté: {title}",
            f"Type: {document_type}, Taille: {file_size} bytes",
            document_id,
            'customer_documents',
            user_id
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document téléversé avec succès',
            'document': {
                'id': document_id,
                'title': title,
                'filename': filename,
                'size': file_size,
                'type': document_type,
                'hash': file_hash
            }
        })
        
    except Exception as e:
        log_error(f"Erreur upload document: {e}")
        return jsonify({'success': False, 'message': 'Erreur upload document'}), 500

# =====================================================
# FINANCES CLIENT AVANCÉES
# =====================================================

@bp.route('/<int:customer_id>/finances/summary', methods=['GET'])
def get_customer_financial_summary(customer_id):
    """Résumé financier complet du client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Profil financier de base
        cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
        finance_profile = cursor.fetchone()
        
        # Créer profil par défaut si inexistant
        if not finance_profile:
            cursor.execute("""
                INSERT INTO customer_finances (customer_id, created_at)
                VALUES (%s, NOW())
            """, [customer_id])
            conn.commit()
            
            cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
            finance_profile = cursor.fetchone()
        
        # Calcul du solde actuel
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN event_type IN ('invoice', 'debit') THEN amount ELSE -amount END), 0) as current_balance
            FROM customer_balance_history
            WHERE customer_id = %s
        """, [customer_id])
        balance_info = cursor.fetchone()
        
        # Factures en cours (AR)
        cursor.execute("""
            SELECT 
                COUNT(*) as open_invoices,
                COALESCE(SUM(total_amount), 0) as total_outstanding,
                COALESCE(SUM(CASE WHEN due_date < NOW() THEN total_amount ELSE 0 END), 0) as overdue_amount,
                MIN(due_date) as earliest_due_date
            FROM invoices
            WHERE customer_id = %s AND status IN ('open', 'sent')
        """, [customer_id])
        ar_summary = cursor.fetchone()
        
        # Historique des paiements (6 derniers mois)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%%Y-%%m') as month,
                SUM(CASE WHEN event_type = 'payment' THEN amount ELSE 0 END) as payments,
                SUM(CASE WHEN event_type = 'invoice' THEN amount ELSE 0 END) as invoiced
            FROM customer_balance_history
            WHERE customer_id = %s 
            AND created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%%Y-%%m')
            ORDER BY month DESC
        """, [customer_id])
        payment_history = cursor.fetchall()
        
        # Méthodes de paiement
        cursor.execute("""
            SELECT * FROM customer_payment_methods
            WHERE customer_id = %s AND is_verified = 1
            ORDER BY is_default DESC, created_at DESC
        """, [customer_id])
        payment_methods = cursor.fetchall()
        
        # Calcul score de risque
        risk_factors = {
            'overdue_amount': float(ar_summary['overdue_amount'] or 0),
            'days_overdue': 0,
            'payment_history_score': 85,  # Score par défaut
            'credit_utilization': 0
        }
        
        if ar_summary['earliest_due_date'] and ar_summary['earliest_due_date'] < datetime.now().date():
            risk_factors['days_overdue'] = (datetime.now().date() - ar_summary['earliest_due_date']).days
        
        if finance_profile['credit_limit'] and finance_profile['credit_limit'] > 0:
            risk_factors['credit_utilization'] = (float(balance_info['current_balance']) / float(finance_profile['credit_limit'])) * 100
        
        # Score de risque simplifié (0-100, plus élevé = plus risqué)
        risk_score = min(100, max(0, 
            (risk_factors['days_overdue'] * 2) + 
            (risk_factors['credit_utilization'] * 0.5) +
            (risk_factors['overdue_amount'] / 1000 * 10)
        ))
        
        cursor.close()
        conn.close()
        
        financial_summary = {
            'finance_profile': finance_profile,
            'current_balance': balance_info['current_balance'],
            'ar_summary': ar_summary,
            'payment_history': payment_history,
            'payment_methods': payment_methods,
            'risk_score': round(risk_score, 1),
            'risk_factors': risk_factors
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'financial_summary': financial_summary})
        
        return render_template(
            'customers/finances.html',
            customer_id=customer_id,
            **financial_summary
        )
        
    except Exception as e:
        log_error(f"Erreur résumé financier: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur résumé financier'}), 500
        flash('Erreur chargement résumé financier', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

# =====================================================
# AUTOMATIONS ET RÈGLES MÉTIER
# =====================================================

@bp.route('/<int:customer_id>/automations/rules', methods=['GET', 'POST'])
def manage_customer_automation_rules(customer_id):
    """Gestion des règles d'automation pour un client"""
    try:
        if request.method == 'GET':
            conn = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Règles disponibles
            cursor.execute("""
                SELECT ar.*, 
                       COUNT(ca.id) as active_instances
                FROM automation_rules ar
                LEFT JOIN customer_automations ca ON ar.id = ca.rule_id 
                    AND ca.customer_id = %s AND ca.status = 'active'
                WHERE ar.is_active = 1 
                AND (ar.applies_to = 'all' OR ar.applies_to = 'customer')
                GROUP BY ar.id
                ORDER BY ar.rule_type, ar.name
            """, [customer_id])
            available_rules = cursor.fetchall()
            
            # Automations actives pour ce client
            cursor.execute("""
                SELECT ca.*, ar.name as rule_name, ar.rule_type, ar.description
                FROM customer_automations ca
                JOIN automation_rules ar ON ca.rule_id = ar.id
                WHERE ca.customer_id = %s
                ORDER BY ca.status, ca.next_execution
            """, [customer_id])
            customer_automations = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'success': True,
                    'available_rules': available_rules,
                    'customer_automations': customer_automations
                })
            
            return render_template(
                'customers/automations.html',
                customer_id=customer_id,
                available_rules=available_rules,
                customer_automations=customer_automations
            )
        
        # POST: Activer une nouvelle automation
        data = request.get_json() if request.is_json else request.form
        rule_id = data.get('rule_id')
        vehicle_id = data.get('vehicle_id')  # Optionnel pour automations véhicule-spécifiques
        custom_data = data.get('custom_data', '{}')
        
        if not rule_id:
            return jsonify({'success': False, 'message': 'ID de règle requis'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Vérifier que la règle existe et est active
        cursor.execute("""
            SELECT * FROM automation_rules 
            WHERE id = %s AND is_active = 1
        """, [rule_id])
        rule = cursor.fetchone()
        
        if not rule:
            return jsonify({'success': False, 'message': 'Règle non trouvée ou inactive'}), 404
        
        # Vérifier si automation déjà active pour ce client/règle
        cursor.execute("""
            SELECT id FROM customer_automations
            WHERE customer_id = %s AND rule_id = %s AND status = 'active'
        """, [customer_id, rule_id])
        existing = cursor.fetchone()
        
        if existing:
            return jsonify({'success': False, 'message': 'Automation déjà active pour cette règle'}), 400
        
        # Calculer prochaine exécution basée sur les conditions de la règle
        next_execution = datetime.now() + timedelta(days=1)  # Par défaut 24h
        
        try:
            conditions = json.loads(rule['conditions']) if isinstance(rule['conditions'], str) else rule['conditions']
            if 'delay_days' in conditions:
                next_execution = datetime.now() + timedelta(days=int(conditions['delay_days']))
        except:
            pass
        
        # Créer l'automation
        cursor.execute("""
            INSERT INTO customer_automations
            (customer_id, rule_id, vehicle_id, next_execution, status, context_data, created_at)
            VALUES (%s, %s, %s, %s, 'active', %s, NOW())
        """, [customer_id, rule_id, vehicle_id, next_execution, custom_data])
        
        automation_id = cursor.lastrowid
        
        # Log d'activité
        log_customer_activity(
            customer_id,
            'system',
            f"Automation activée: {rule['name']}",
            f"Type: {rule['rule_type']}, Prochaine exécution: {next_execution.strftime('%Y-%m-%d %H:%M')}",
            automation_id,
            'customer_automations'
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f"Automation '{rule['name']}' activée",
            'automation_id': automation_id,
            'next_execution': next_execution.isoformat()
        })
        
    except Exception as e:
        log_error(f"Erreur gestion automations: {e}")
        return jsonify({'success': False, 'message': 'Erreur gestion automations'}), 500

# =====================================================
# CLIENT 360 - TABLEAU DE BORD UNIFIÉ
# =====================================================

@bp.route('/<int:customer_id>/dashboard-360', methods=['GET'])
def customer_360_dashboard(customer_id):
    """Tableau de bord Client 360 unifié"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Informations client de base
        cursor.execute("SELECT * FROM customers WHERE id = %s", [customer_id])
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        
        # Timeline récente (10 dernières activités)
        cursor.execute("""
            SELECT ca.*, u.name as actor_name
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id
            WHERE ca.customer_id = %s
            ORDER BY ca.created_at DESC
            LIMIT 10
        """, [customer_id])
        recent_timeline = cursor.fetchall()
        
        # Véhicules et statuts
        cursor.execute("""
            SELECT v.*, 
                   COUNT(wo.id) as total_work_orders,
                   SUM(CASE WHEN wo.status = 'open' THEN 1 ELSE 0 END) as open_work_orders,
                   MAX(wo.scheduled_date) as last_service_date
            FROM vehicles v
            LEFT JOIN work_orders wo ON v.id = wo.vehicle_id
            WHERE v.customer_id = %s
            GROUP BY v.id
            ORDER BY v.created_at DESC
        """, [customer_id])
        vehicles = cursor.fetchall()
        
        # Résumé financier
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status IN ('open', 'sent') THEN 1 END) as open_invoices,
                SUM(CASE WHEN status IN ('open', 'sent') THEN total_amount ELSE 0 END) as outstanding_amount,
                SUM(CASE WHEN status = 'paid' THEN total_amount ELSE 0 END) as paid_amount
            FROM invoices
            WHERE customer_id = %s
        """, [customer_id])
        financial_summary = cursor.fetchone()
        
        # Documents récents
        cursor.execute("""
            SELECT * FROM customer_documents
            WHERE customer_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, [customer_id])
        recent_documents = cursor.fetchall()
        
        # Consentements RGPD actifs
        cursor.execute("""
            SELECT * FROM customer_consents
            WHERE customer_id = %s AND is_active = 1
            ORDER BY updated_at DESC
        """, [customer_id])
        active_consents = cursor.fetchall()
        
        # Automations actives
        cursor.execute("""
            SELECT ca.*, ar.name as rule_name, ar.rule_type
            FROM customer_automations ca
            JOIN automation_rules ar ON ca.rule_id = ar.id
            WHERE ca.customer_id = %s AND ca.status = 'active'
            ORDER BY ca.next_execution ASC
            LIMIT 5
        """, [customer_id])
        active_automations = cursor.fetchall()
        
        # Métriques de communication
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN activity_type = 'communication' THEN 1 ELSE 0 END) as total_communications,
                SUM(CASE WHEN activity_type = 'communication' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) as recent_communications
            FROM customer_activity
            WHERE customer_id = %s
        """, [customer_id])
        communication_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        dashboard_data = {
            'customer': customer,
            'recent_timeline': recent_timeline,
            'vehicles': vehicles,
            'financial_summary': financial_summary,
            'recent_documents': recent_documents,
            'active_consents': active_consents,
            'active_automations': active_automations,
            'communication_stats': communication_stats,
            'summary_cards': {
                'total_vehicles': len(vehicles),
                'open_work_orders': sum(v['open_work_orders'] for v in vehicles),
                'outstanding_amount': financial_summary['outstanding_amount'] or 0,
                'active_automations_count': len(active_automations),
                'documents_count': len(recent_documents),
                'consents_count': len(active_consents)
            }
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'dashboard': dashboard_data})
        
        return render_template(
            'customers/dashboard_360.html',
            customer_id=customer_id,
            **dashboard_data
        )
        
    except Exception as e:
        log_error(f"Erreur dashboard Client 360: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Erreur dashboard Client 360'}), 500
        flash('Erreur chargement dashboard Client 360', 'error')
        return redirect(url_for('customers.view_customer', customer_id=customer_id))

# =====================================================
# FONCTIONS HELPER POUR LES EXTENSIONS
# =====================================================

def log_customer_activity(customer_id, activity_type, title, description=None, related_id=None, related_table=None, actor_id=None):
    """Log une activité dans la timeline client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Métadonnées contextuelles
        metadata = {
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'timestamp': datetime.now().isoformat()
        }
        
        cursor.execute("""
            INSERT INTO customer_activity 
            (customer_id, activity_type, title, description, related_id, related_table, actor_id, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, [
            customer_id, activity_type, title, description, 
            related_id, related_table, actor_id, json.dumps(metadata)
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        log_error(f"Erreur log activité client: {e}")

def get_db_connection():
    """Connexion à la base de données - utilise la fonction existante"""
    from core.config import get_db_config
    config = get_db_config()
    return pymysql.connect(
        host=config['host'],
        user=config['user'], 
        password=config['password'],
        database=config['database'],
        charset='utf8mb4',
        autocommit=False
    )

# =====================================================
# AMÉLIORATION DES FONCTIONS EXISTANTES
# =====================================================

def enhanced_customer_timeline(customer_id, start_date=None, end_date=None, activity_types=None, limit=None):
    """Version améliorée de la timeline avec filtres avancés"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        query = """
            SELECT ca.*, u.name as actor_name, u.email as actor_email
            FROM customer_activity ca
            LEFT JOIN users u ON ca.actor_id = u.id
            WHERE ca.customer_id = %s
        """
        params = [customer_id]
        
        if start_date:
            query += " AND ca.created_at >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND ca.created_at <= %s"
            params.append(end_date)
        
        if activity_types:
            placeholders = ','.join(['%s'] * len(activity_types))
            query += f" AND ca.activity_type IN ({placeholders})"
            params.extend(activity_types)
        
        query += " ORDER BY ca.created_at DESC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cursor.execute(query, params)
        activities = cursor.fetchall()
        
        # Enrichissement des données
        for activity in activities:
            # Parsing des métadonnées
            if activity.get('metadata'):
                try:
                    activity['metadata'] = json.loads(activity['metadata']) if isinstance(activity['metadata'], str) else activity['metadata']
                except:
                    activity['metadata'] = {}
            
            # Ajout d'informations contextuelles
            activity['time_ago'] = format_time_ago(activity['created_at'])
            activity['is_system'] = activity['actor_id'] is None
        
        cursor.close()
        conn.close()
        
        return activities
        
    except Exception as e:
        log_error(f"Erreur timeline améliorée: {e}")
        return []

def format_time_ago(timestamp):
    """Formate un timestamp en format 'il y a X temps'"""
    if not timestamp:
        return "Date inconnue"
    
    now = datetime.now()
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    diff = now - timestamp
    
    if diff.days > 0:
        return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "à l'instant"
