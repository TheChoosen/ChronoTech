# Extension complète du module customers avec toutes les fonctionnalités Sprint 5-6

import os
import hashlib
import json
import math
import pymysql
from datetime import datetime, timedelta
from flask import current_app, send_file, Blueprint
from werkzeug.utils import secure_filename

# =====================================================
# TIMELINE UNIFIÉE AVEC COMMUNICATIONS
# =====================================================
bp = Blueprint('customers', __name__)

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
        user_id = None
        try:
            from flask_login import current_user
            if hasattr(current_user, 'id'):
                user_id = current_user.id
        except ImportError:
            pass
        
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

@bp.route('/documents/<int:document_id>/signature', methods=['POST'])
def sign_customer_document(document_id):
    """Signature électronique d'un document avec audit"""
    try:
        data = request.get_json() if request.is_json else request.form
        signature_data = data.get('signature_data')  # Base64 de la signature
        signature_provider = data.get('provider', 'internal')
        signer_name = data.get('signer_name')
        signer_email = data.get('signer_email')
        
        if not signature_data:
            return jsonify({'success': False, 'message': 'Données de signature requises'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Vérifier que le document existe
        cursor.execute("SELECT * FROM customer_documents WHERE id = %s", [document_id])
        document = cursor.fetchone()
        
        if not document:
            return jsonify({'success': False, 'message': 'Document non trouvé'}), 404
        
        if document['is_signed']:
            return jsonify({'success': False, 'message': 'Document déjà signé'}), 400
        
        # Préparer les données de signature
        signature_metadata = {
            'signature_data': signature_data,
            'signer_name': signer_name,
            'signer_email': signer_email,
            'signature_timestamp': datetime.now().isoformat(),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'provider': signature_provider
        }
        
        # Mise à jour du document
        cursor.execute("""
            UPDATE customer_documents SET
            is_signed = TRUE,
            signed_at = NOW(),
            signature_provider = %s,
            signature_data = %s
            WHERE id = %s
        """, [signature_provider, json.dumps(signature_metadata), document_id])
        
        # Log d'activité
        log_customer_activity(
            document['customer_id'], 
            'document', 
            f"Document signé: {document['title']}",
            f"Signé par: {signer_name} via {signature_provider}",
            document_id,
            'customer_documents'
        )
        
        # Log d'accès aux documents pour audit
        cursor.execute("""
            INSERT INTO customer_document_access_log
            (document_id, user_id, access_type, ip_address, user_agent, accessed_at)
            VALUES (%s, %s, 'sign', %s, %s, NOW())
        """, [
            document_id, None, request.remote_addr, 
            request.headers.get('User-Agent', '')
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Document signé avec succès',
            'signed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        log_error(f"Erreur signature document: {e}")
        return jsonify({'success': False, 'message': 'Erreur signature document'}), 500

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
# SEGMENTATION ET PERSONNALISATION
# =====================================================

@bp.route('/<int:customer_id>/segments', methods=['GET', 'POST'])
def manage_customer_segments(customer_id):
    """Gestion des segments et tags client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        if request.method == 'GET':
            # Segments actuels du client
            cursor.execute("""
                SELECT cs.*, 
                       csm.added_at,
                       CASE WHEN csm.expires_at IS NULL OR csm.expires_at > NOW() THEN 1 ELSE 0 END as is_active
                FROM customer_segments cs
                JOIN customer_segment_memberships csm ON cs.id = csm.segment_id
                WHERE csm.customer_id = %s
                ORDER BY cs.segment_type, cs.name
            """, [customer_id])
            current_segments = cursor.fetchall()
            
            # Segments disponibles
            cursor.execute("""
                SELECT cs.*,
                       COUNT(csm.customer_id) as member_count
                FROM customer_segments cs
                LEFT JOIN customer_segment_memberships csm ON cs.id = csm.segment_id
                    AND (csm.expires_at IS NULL OR csm.expires_at > NOW())
                WHERE cs.is_active = 1
                GROUP BY cs.id
                ORDER BY cs.segment_type, cs.name
            """, [])
            available_segments = cursor.fetchall()
            
            # Tags personnalisés du client
            cursor.execute("""
                SELECT tag, added_at, added_by, u.name as added_by_name
                FROM customer_tags ct
                LEFT JOIN users u ON ct.added_by = u.id
                WHERE ct.customer_id = %s
                ORDER BY ct.added_at DESC
            """, [customer_id])
            customer_tags = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'success': True,
                    'current_segments': current_segments,
                    'available_segments': available_segments,
                    'customer_tags': customer_tags
                })
            
            return render_template(
                'customers/segments.html',
                customer_id=customer_id,
                current_segments=current_segments,
                available_segments=available_segments,
                customer_tags=customer_tags
            )
        
        # POST: Ajouter segment ou tag
        data = request.get_json() if request.is_json else request.form
        action = data.get('action')  # 'add_segment', 'remove_segment', 'add_tag', 'remove_tag'
        
        user_id = None
        try:
            from flask_login import current_user
            if hasattr(current_user, 'id'):
                user_id = current_user.id
        except ImportError:
            pass
        
        if action == 'add_segment':
            segment_id = data.get('segment_id')
            expires_at = data.get('expires_at')  # Optionnel
            
            # Vérifier si déjà membre
            cursor.execute("""
                SELECT id FROM customer_segment_memberships
                WHERE customer_id = %s AND segment_id = %s
                AND (expires_at IS NULL OR expires_at > NOW())
            """, [customer_id, segment_id])
            
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Client déjà dans ce segment'}), 400
            
            # Ajouter au segment
            cursor.execute("""
                INSERT INTO customer_segment_memberships
                (customer_id, segment_id, added_at, expires_at)
                VALUES (%s, %s, NOW(), %s)
            """, [customer_id, segment_id, expires_at])
            
            # Log activité
            cursor.execute("SELECT name FROM customer_segments WHERE id = %s", [segment_id])
            segment_name = cursor.fetchone()['name']
            
            log_customer_activity(
                customer_id,
                'system',
                f"Ajouté au segment: {segment_name}",
                f"Expires: {expires_at or 'Jamais'}",
                segment_id,
                'customer_segments',
                user_id
            )
            
            message = f"Client ajouté au segment '{segment_name}'"
        
        elif action == 'add_tag':
            tag = data.get('tag', '').strip()
            
            if not tag:
                return jsonify({'success': False, 'message': 'Tag requis'}), 400
            
            # Vérifier si tag existe déjà
            cursor.execute("""
                SELECT tag FROM customer_tags
                WHERE customer_id = %s AND tag = %s
            """, [customer_id, tag])
            
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Tag déjà existant'}), 400
            
            # Ajouter le tag
            cursor.execute("""
                INSERT INTO customer_tags
                (customer_id, tag, added_by, added_at)
                VALUES (%s, %s, %s, NOW())
            """, [customer_id, tag, user_id])
            
            log_customer_activity(
                customer_id,
                'system',
                f"Tag ajouté: {tag}",
                f"Ajouté par: {user_id or 'Système'}",
                None,
                'customer_tags',
                user_id
            )
            
            message = f"Tag '{tag}' ajouté"
        
        else:
            return jsonify({'success': False, 'message': 'Action non reconnue'}), 400
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        log_error(f"Erreur gestion segments: {e}")
        return jsonify({'success': False, 'message': 'Erreur gestion segments'}), 500

# =====================================================
# DÉTECTION DE DOUBLONS ET FUSION
# =====================================================

@bp.route('/duplicates/detection', methods=['GET'])
def detect_customer_duplicates():
    """Détection intelligente des doublons clients"""
    try:
        threshold = float(request.args.get('threshold', 0.7))  # Seuil de similarité
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Récupérer tous les clients actifs
        cursor.execute("""
            SELECT id, name, email, phone, company, 
                   CONCAT(COALESCE(address, ''), ' ', COALESCE(city, ''), ' ', COALESCE(postal_code, '')) as full_address
            FROM customers 
            WHERE status != 'deleted'
            ORDER BY created_at DESC
        """)
        customers = cursor.fetchall()
        
        potential_duplicates = []
        
        # Algorithme de détection de doublons
        for i, customer1 in enumerate(customers):
            for j, customer2 in enumerate(customers[i+1:], i+1):
                similarity_score = 0
                reasons = []
                
                # Comparaison email exact
                if customer1['email'] and customer2['email'] and customer1['email'].lower() == customer2['email'].lower():
                    similarity_score += 0.4
                    reasons.append('Email identique')
                
                # Comparaison téléphone (normalisé)
                if customer1['phone'] and customer2['phone']:
                    phone1_clean = ''.join(filter(str.isdigit, customer1['phone']))
                    phone2_clean = ''.join(filter(str.isdigit, customer2['phone']))
                    if len(phone1_clean) >= 10 and len(phone2_clean) >= 10:
                        if phone1_clean[-10:] == phone2_clean[-10:]:  # Comparer les 10 derniers chiffres
                            similarity_score += 0.3
                            reasons.append('Téléphone identique')
                
                # Comparaison nom (Levenshtein simplifié)
                if customer1['name'] and customer2['name']:
                    name1 = customer1['name'].lower().strip()
                    name2 = customer2['name'].lower().strip()
                    if name1 == name2:
                        similarity_score += 0.3
                        reasons.append('Nom identique')
                    elif len(name1) > 3 and len(name2) > 3:
                        # Similarité approximative
                        common_words = set(name1.split()) & set(name2.split())
                        if len(common_words) >= 2:
                            similarity_score += 0.2
                            reasons.append('Noms similaires')
                
                # Comparaison entreprise
                if customer1['company'] and customer2['company']:
                    if customer1['company'].lower().strip() == customer2['company'].lower().strip():
                        similarity_score += 0.2
                        reasons.append('Entreprise identique')
                
                # Si score dépasse le seuil, c'est un doublon potentiel
                if similarity_score >= threshold:
                    potential_duplicates.append({
                        'customer1': customer1,
                        'customer2': customer2,
                        'similarity_score': round(similarity_score, 2),
                        'reasons': reasons,
                        'confidence': 'high' if similarity_score >= 0.8 else 'medium' if similarity_score >= 0.6 else 'low'
                    })
        
        # Trier par score de similarité décroissant
        potential_duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        cursor.close()
        conn.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                'success': True,
                'potential_duplicates': potential_duplicates,
                'total_found': len(potential_duplicates),
                'threshold_used': threshold
            })
        
        return render_template(
            'customers/duplicates.html',
            potential_duplicates=potential_duplicates,
            total_found=len(potential_duplicates),
            threshold_used=threshold
        )
        
    except Exception as e:
        log_error(f"Erreur détection doublons: {e}")
        return jsonify({'success': False, 'message': 'Erreur détection doublons'}), 500

@bp.route('/merge', methods=['POST'])
def merge_customers():
    """Fusion contrôlée de deux clients avec audit complet"""
    try:
        data = request.get_json() if request.is_json else request.form
        primary_id = int(data.get('primary_id'))  # Client à conserver
        duplicate_id = int(data.get('duplicate_id'))  # Client à fusionner
        merge_strategy = data.get('merge_strategy', 'keep_primary')  # 'keep_primary', 'merge_data'
        
        if primary_id == duplicate_id:
            return jsonify({'success': False, 'message': 'Impossible de fusionner un client avec lui-même'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # Vérifier que les deux clients existent
        cursor.execute("SELECT * FROM customers WHERE id IN (%s, %s)", [primary_id, duplicate_id])
        customers = cursor.fetchall()
        
        if len(customers) != 2:
            return jsonify({'success': False, 'message': 'Un ou plusieurs clients introuvables'}), 404
        
        primary_customer = next(c for c in customers if c['id'] == primary_id)
        duplicate_customer = next(c for c in customers if c['id'] == duplicate_id)
        
        # Début transaction
        cursor.execute("START TRANSACTION")
        
        try:
            # Tables à migrer (ordre important pour les contraintes FK)
            migration_tables = [
                'customer_contacts',
                'customer_addresses', 
                'customer_documents',
                'customer_consents',
                'customer_consent_history',
                'customer_activity',
                'customer_finances',
                'customer_payment_methods',
                'customer_balance_history',
                'customer_automations',
                'customer_programs',
                'customer_loyalty_transactions',
                'customer_segment_memberships',
                'customer_tags',
                'vehicles',  # Important: véhicules liés
                'work_orders'  # Via vehicles
            ]
            
            migration_summary = {
                'migrated_records': {},
                'conflicts_resolved': {},
                'errors': []
            }
            
            # Migration des enregistrements liés
            for table in migration_tables:
                try:
                    # Vérifier si la table existe
                    cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    if not cursor.fetchone():
                        continue
                    
                    # Vérifier la structure de la table
                    cursor.execute(f"SHOW COLUMNS FROM {table}")
                    columns = [col[0] for col in cursor.fetchall()]
                    
                    if 'customer_id' in columns:
                        # Migration directe via customer_id
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE customer_id = %s", [duplicate_id])
                        count_to_migrate = cursor.fetchone()['count']
                        
                        if count_to_migrate > 0:
                            cursor.execute(f"UPDATE {table} SET customer_id = %s WHERE customer_id = %s", [primary_id, duplicate_id])
                            migration_summary['migrated_records'][table] = count_to_migrate
                    
                    elif table == 'work_orders':
                        # Migration via vehicles
                        cursor.execute("""
                            UPDATE work_orders wo
                            JOIN vehicles v ON wo.vehicle_id = v.id
                            SET wo.customer_id = %s  -- Si la colonne existe
                            WHERE v.customer_id = %s
                        """, [primary_id, duplicate_id])
                        # Note: Ceci ne fonctionne que si work_orders a une colonne customer_id
                
                except Exception as table_error:
                    migration_summary['errors'].append(f"Erreur migration {table}: {str(table_error)}")
                    continue
            
            # Fusion des données client si demandée
            if merge_strategy == 'merge_data':
                # Fusion intelligente des champs
                merge_fields = {}
                
                # Prendre les valeurs non-nulles du duplicate si primary est null
                for field in ['phone', 'email', 'address', 'city', 'postal_code', 'company']:
                    if field in primary_customer and field in duplicate_customer:
                        if not primary_customer[field] and duplicate_customer[field]:
                            merge_fields[field] = duplicate_customer[field]
                
                if merge_fields:
                    # Construire requête UPDATE dynamique
                    set_clauses = [f"{field} = %s" for field in merge_fields.keys()]
                    values = list(merge_fields.values()) + [primary_id]
                    
                    cursor.execute(f"""
                        UPDATE customers 
                        SET {', '.join(set_clauses)}, updated_at = NOW()
                        WHERE id = %s
                    """, values)
                    
                    migration_summary['conflicts_resolved']['merged_fields'] = list(merge_fields.keys())
            
            # Marquer le client dupliqué comme fusionné (soft delete)
            cursor.execute("""
                UPDATE customers 
                SET status = 'merged', 
                    merged_into = %s,
                    updated_at = NOW(),
                    name = CONCAT(name, ' [FUSIONNÉ]')
                WHERE id = %s
            """, [primary_id, duplicate_id])
            
            # Log de l'activité de fusion
            log_customer_activity(
                primary_id,
                'system',
                f"Fusion client: {duplicate_customer['name']} (ID: {duplicate_id})",
                f"Stratégie: {merge_strategy}, Tables migrées: {len(migration_summary['migrated_records'])}",
                duplicate_id,
                'customers'
            )
            
            # Log d'audit complet
            audit_data = {
                'action': 'customer_merge',
                'primary_customer_id': primary_id,
                'duplicate_customer_id': duplicate_id,
                'merge_strategy': merge_strategy,
                'migration_summary': migration_summary,
                'timestamp': datetime.now().isoformat(),
                'ip_address': request.remote_addr
            }
            
            cursor.execute("""
                INSERT INTO customer_audit_log
                (customer_id, action_type, action_data, ip_address, created_at)
                VALUES (%s, 'merge', %s, %s, NOW())
            """, [primary_id, json.dumps(audit_data), request.remote_addr])
            
            # Commit de la transaction
            cursor.execute("COMMIT")
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f"Fusion réussie: {duplicate_customer['name']} fusionné dans {primary_customer['name']}",
                'primary_customer_id': primary_id,
                'migration_summary': migration_summary
            })
            
        except Exception as merge_error:
            cursor.execute("ROLLBACK")
            raise merge_error
            
    except Exception as e:
        log_error(f"Erreur fusion clients: {e}")
        return jsonify({'success': False, 'message': f'Erreur fusion clients: {str(e)}'}), 500

# =====================================================
# IMPORT DES MODULES REQUIS
# =====================================================

try:
    from flask import make_response
    import pymysql.cursors
except ImportError as e:
    log_error(f"Import manquant pour extensions clients: {e}")
