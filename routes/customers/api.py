"""
API REST pour les opérations clients avancées
"""

import json
import hashlib
import pymysql
from datetime import datetime
from flask import request, jsonify, session
from core.utils import log_error
from .utils import get_db_connection, require_role, get_current_user, log_customer_activity


def setup_api_routes(bp):
    """Configure les routes API REST"""
    
    # =====================================================
    # API VÉHICULES
    # =====================================================
    
    @bp.route('/api/customers/<int:customer_id>/vehicles', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_customer_vehicles(customer_id):
        """Récupérer tous les véhicules d'un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("""
                SELECT * FROM vehicles 
                WHERE customer_id = %s 
                ORDER BY created_at DESC
            """, [customer_id])
            
            vehicles = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'vehicles': vehicles,
                'count': len(vehicles)
            })
            
        except Exception as e:
            log_error(f"Erreur récupération véhicules client {customer_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/customers/<int:customer_id>/vehicles', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def create_customer_vehicle(customer_id):
        """Créer un nouveau véhicule pour un client"""
        try:
            data = request.get_json()
            
            # Validation des données requises
            required_fields = ['make', 'model', 'year']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False, 
                        'message': f'Champ {field} requis'
                    }), 400
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO vehicles 
                (customer_id, make, model, year, vin, license_plate, color, notes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                customer_id,
                data['make'],
                data['model'],
                data['year'],
                data.get('vin'),
                data.get('license_plate'),
                data.get('color'),
                data.get('notes')
            ])
            
            vehicle_id = cursor.lastrowid
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'vehicle',
                f"Véhicule ajouté: {data['make']} {data['model']}",
                f"Année: {data['year']}, Immatriculation: {data.get('license_plate', 'N/A')}",
                vehicle_id,
                'vehicles'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Véhicule créé avec succès',
                'vehicle_id': vehicle_id
            })
            
        except Exception as e:
            log_error(f"Erreur création véhicule: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # =====================================================
    # API ACTIONS CUSTOMER 360
    # =====================================================
    
    @bp.route('/api/customers/<int:customer_id>/send-email', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def send_customer_email_api(customer_id):
        """Envoyer un email à un client"""
        try:
            data = request.get_json()
            subject = data.get('subject', '')
            message = data.get('message', '')
            email_type = data.get('type', 'general')
            
            if not subject or not message:
                return jsonify({
                    'success': False,
                    'message': 'Sujet et message requis'
                }), 400
            
            # Récupérer les informations du client
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("""
                SELECT email, name FROM customers WHERE id = %s
            """, [customer_id])
            
            customer = cursor.fetchone()
            
            if not customer or not customer['email']:
                cursor.close()
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Client ou email non trouvé'
                }), 404
            
            # TODO: Intégrer avec service email (SMTP, SendGrid, etc.)
            # Pour l'instant, simulation d'envoi
            email_sent = True  # Remplacer par vraie logique d'envoi
            
            if email_sent:
                # Log de l'activité
                log_customer_activity(
                    customer_id,
                    'communication',
                    f"Email envoyé: {subject}",
                    f"Type: {email_type}, Destinataire: {customer['email']}",
                    None,
                    'emails'
                )
                
                # Enregistrer l'email en base
                cursor.execute("""
                    INSERT INTO customer_emails 
                    (customer_id, subject, message, email_type, sent_at, sent_by)
                    VALUES (%s, %s, %s, %s, NOW(), %s)
                """, [
                    customer_id, subject, message, email_type,
                    session.get('user_id')
                ])
                
                conn.commit()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': email_sent,
                'message': 'Email envoyé avec succès' if email_sent else 'Erreur envoi email'
            })
            
        except Exception as e:
            log_error(f"Erreur envoi email: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/customers/<int:customer_id>/export', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def export_customer_data_api(customer_id):
        """Exporter les données d'un client"""
        try:
            export_format = request.args.get('format', 'json')
            include_history = request.args.get('history', 'true').lower() == 'true'
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Données de base du client
            cursor.execute("SELECT * FROM customers WHERE id = %s", [customer_id])
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            export_data = {
                'customer': customer,
                'exported_at': datetime.now().isoformat(),
                'exported_by': session.get('user_id')
            }
            
            if include_history:
                # Véhicules
                cursor.execute("SELECT * FROM vehicles WHERE customer_id = %s", [customer_id])
                export_data['vehicles'] = cursor.fetchall()
                
                # Contacts
                cursor.execute("SELECT * FROM customer_contacts WHERE customer_id = %s", [customer_id])
                export_data['contacts'] = cursor.fetchall()
                
                # Bons de travail
                cursor.execute("""
                    SELECT * FROM work_orders 
                    WHERE customer_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 50
                """, [customer_id])
                export_data['work_orders'] = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'export',
                f"Données exportées en {export_format.upper()}",
                f"Historique inclus: {'Oui' if include_history else 'Non'}",
                None,
                'exports'
            )
            
            if export_format == 'json':
                return jsonify({
                    'success': True,
                    'data': export_data
                })
            else:
                # TODO: Implémenter export CSV/PDF
                return jsonify({
                    'success': False,
                    'message': f'Format {export_format} non supporté actuellement'
                }), 400
                
        except Exception as e:
            log_error(f"Erreur export données client: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/customers/<int:customer_id>/duplicate', methods=['POST'])
    @require_role('admin', 'manager')
    def duplicate_customer_api(customer_id):
        """Dupliquer un client existant"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Récupérer le client original
            cursor.execute("SELECT * FROM customers WHERE id = %s", [customer_id])
            original = cursor.fetchone()
            
            if not original:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Créer la copie avec suffixe
            new_name = f"{original['name']} (Copie)"
            new_email = f"copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original['email']}"
            
            cursor.execute("""
                INSERT INTO customers 
                (name, email, phone, mobile, company, address, city, postal_code, notes, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                new_name,
                new_email,
                original['phone'],
                original.get('mobile'),
                original.get('company'),
                original.get('address'),
                original.get('city'),
                original.get('postal_code'),
                f"Copie de {original['name']} - {original.get('notes', '')}"
            ])
            
            new_customer_id = cursor.lastrowid
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'duplicate',
                f"Client dupliqué vers ID {new_customer_id}",
                f"Nouveau nom: {new_name}",
                new_customer_id,
                'customers'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Client dupliqué avec succès',
                'new_customer_id': new_customer_id,
                'new_name': new_name
            })
            
        except Exception as e:
            log_error(f"Erreur duplication client: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/customers/duplicates/detect', methods=['GET'])
    @require_role('admin', 'manager')
    def detect_customer_duplicates_api():
        """Détecter les doublons de clients"""
        try:
            similarity_threshold = request.args.get('threshold', 0.8, type=float)
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Utiliser SOUNDEX pour détecter les noms similaires
            cursor.execute("""
                SELECT c1.id as id1, c1.name as name1, c1.email as email1,
                       c2.id as id2, c2.name as name2, c2.email as email2,
                       SOUNDEX(c1.name) as soundex1, SOUNDEX(c2.name) as soundex2
                FROM customers c1
                JOIN customers c2 ON c1.id < c2.id 
                WHERE (
                    SOUNDEX(c1.name) = SOUNDEX(c2.name) OR
                    c1.email = c2.email OR
                    (c1.phone = c2.phone AND c1.phone IS NOT NULL)
                )
                ORDER BY c1.name, c2.name
                LIMIT 100
            """)
            
            potential_duplicates = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'duplicates': potential_duplicates,
                'count': len(potential_duplicates),
                'threshold_used': similarity_threshold
            })
            
        except Exception as e:
            log_error(f"Erreur détection doublons: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/customers/merge', methods=['POST'])
    @require_role('admin', 'manager')
    def merge_customers_api():
        """Fusionner deux clients"""
        try:
            data = request.get_json()
            primary_id = data.get('primary_id')
            secondary_id = data.get('secondary_id')
            
            if not primary_id or not secondary_id:
                return jsonify({
                    'success': False,
                    'message': 'IDs des clients requis'
                }), 400
            
            if primary_id == secondary_id:
                return jsonify({
                    'success': False,
                    'message': 'Impossible de fusionner un client avec lui-même'
                }), 400
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Vérifier que les deux clients existent
            cursor.execute("SELECT name FROM customers WHERE id IN (%s, %s)", [primary_id, secondary_id])
            clients = cursor.fetchall()
            
            if len(clients) != 2:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Un ou plusieurs clients non trouvés'}), 404
            
            # Transférer les données du client secondaire vers le principal
            tables_to_merge = [
                'work_orders',
                'vehicles', 
                'customer_contacts',
                'customer_addresses',
                'invoices'
            ]
            
            for table in tables_to_merge:
                cursor.execute(f"""
                    UPDATE {table} 
                    SET customer_id = %s 
                    WHERE customer_id = %s
                """, [primary_id, secondary_id])
            
            # Supprimer le client secondaire
            cursor.execute("DELETE FROM customers WHERE id = %s", [secondary_id])
            
            # Log de l'activité
            log_customer_activity(
                primary_id,
                'merge',
                f"Fusion avec client ID {secondary_id}",
                f"Données transférées depuis {clients[1]['name']}",
                secondary_id,
                'customers'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Clients fusionnés avec succès. Client principal: ID {primary_id}'
            })
            
        except Exception as e:
            log_error(f"Erreur fusion clients: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # =====================================================
    # API GÉOLOCALISATION
    # =====================================================
    
    @bp.route('/api/geocode-address', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def geocode_address_api():
        """API de géocodage d'adresse"""
        try:
            from .geocoding import geocode_address
            
            data = request.get_json()
            address = data.get('address', '')
            
            if not address:
                return jsonify({'success': False, 'message': 'Adresse requise'}), 400
            
            # TODO: Intégrer avec API géocodage réelle (Google Maps, OpenStreetMap, etc.)
            # Pour l'instant, simulation
            coordinates = geocode_address(address)
            
            if coordinates:
                return jsonify({
                    'success': True,
                    'coordinates': {
                        'latitude': coordinates[0],
                        'longitude': coordinates[1]
                    },
                    'address': address
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Impossible de géocoder cette adresse'
                })
                
        except Exception as e:
            log_error(f"Erreur géocodage: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/postal-lookup', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def postal_lookup_api():
        """API de recherche de codes postaux"""
        try:
            from .geocoding import get_postal_code_suggestions
            
            partial_code = request.args.get('q', '')
            limit = min(request.args.get('limit', 10, type=int), 20)
            
            if len(partial_code) < 2:
                return jsonify({'suggestions': []})
            
            # TODO: Intégrer avec API codes postaux réelle
            # Pour l'instant, suggestions simulées
            suggestions = get_postal_code_suggestions(partial_code, limit)
            
            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'query': partial_code
            })
            
        except Exception as e:
            log_error(f"Erreur recherche codes postaux: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # =====================================================
    # SEGMENTS RFM ET ANALYTICS
    # =====================================================
    
    @bp.route('/rfm-segments')
    @require_role('admin', 'manager', 'staff')
    def get_rfm_segments():
        """Affiche la page des segments RFM"""
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.index'))
            
            cursor = conn.cursor()
            
            # Récupérer les segments RFM
            cursor.execute("""
                SELECT 
                    segment,
                    COUNT(*) as customer_count,
                    AVG(CAST(recency AS FLOAT)) as avg_recency,
                    AVG(CAST(frequency AS FLOAT)) as avg_frequency,
                    AVG(CAST(monetary AS FLOAT)) as avg_monetary
                FROM customer_rfm 
                GROUP BY segment
                ORDER BY segment
            """)
            
            segments = cursor.fetchall()
            
            # Récupérer les clients par segment
            cursor.execute("""
                SELECT 
                    cr.*,
                    c.name,
                    c.company,
                    c.email
                FROM customer_rfm cr
                JOIN customers c ON cr.customer_id = c.id
                ORDER BY cr.segment, cr.rfm_score DESC
            """)
            
            customers_rfm = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'success': True,
                    'segments': segments,
                    'customers_rfm': customers_rfm
                })
            
            from flask import render_template
            return render_template('customers/rfm_segments.html', 
                                 segments=segments, 
                                 customers_rfm=customers_rfm)
            
        except Exception as e:
            log_error(f"Erreur segments RFM: {e}")
            from flask import flash
            flash('Erreur lors de la récupération des segments RFM', 'error')
            return redirect(url_for('customers.index'))

    # =====================================================
    # TIMELINE ET EXPORT AVANCÉ
    # =====================================================
    
    @bp.route('/<int:customer_id>/timeline/export')
    @require_role('admin', 'manager', 'staff')
    def export_customer_timeline(customer_id):
        """Exporte la timeline en différents formats"""
        try:
            format_type = request.args.get('format', 'csv')
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
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
                from flask import make_response
                
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Date', 'Type', 'Titre', 'Description', 'Acteur'])
                
                for activity in activities:
                    writer.writerow([
                        activity[4].strftime('%Y-%m-%d %H:%M:%S') if activity[4] else '',  # created_at
                        activity[2],  # activity_type
                        activity[3],  # title
                        activity[5] or '',  # description
                        activity[-1] or 'Système'  # actor_name
                    ])
                
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.csv'
                return response
            
            elif format_type == 'json':
                from flask import make_response
                
                # Conversion pour JSON
                activities_json = []
                for activity in activities:
                    activities_json.append({
                        'created_at': activity[4].isoformat() if activity[4] else None,
                        'activity_type': activity[2],
                        'title': activity[3],
                        'description': activity[5],
                        'actor_name': activity[-1] or 'Système'
                    })
                
                response = make_response(json.dumps(activities_json, indent=2, ensure_ascii=False))
                response.headers['Content-Type'] = 'application/json'
                response.headers['Content-Disposition'] = f'attachment; filename=timeline_client_{customer_id}.json'
                return response
            
            else:
                return jsonify({'success': False, 'message': 'Format non supporté'}), 400
                
        except Exception as e:
            log_error(f"Erreur export timeline: {e}")
            return jsonify({'success': False, 'message': 'Erreur export timeline'}), 500

    # =====================================================
    # DASHBOARD 360 UNIFIÉ
    # =====================================================
    
    @bp.route('/<int:customer_id>/dashboard-360', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def customer_360_dashboard(customer_id):
        """Tableau de bord Client 360 unifié"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
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
            
            cursor.close()
            conn.close()
            
            dashboard_data = {
                'customer': customer,
                'recent_timeline': recent_timeline,
                'vehicles': vehicles,
                'financial_summary': financial_summary,
                'summary_cards': {
                    'total_vehicles': len(vehicles) if vehicles else 0,
                    'open_work_orders': sum(v[5] for v in vehicles if len(v) > 5) if vehicles else 0,
                    'outstanding_amount': financial_summary[1] if financial_summary and len(financial_summary) > 1 else 0,
                }
            }
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': True, 'dashboard': dashboard_data})
            
            from flask import render_template
            return render_template(
                'customers/dashboard_360.html',
                customer_id=customer_id,
                **dashboard_data
            )
            
        except Exception as e:
            log_error(f"Erreur dashboard Client 360: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'Erreur dashboard Client 360'}), 500
            from flask import flash
            flash('Erreur chargement dashboard Client 360', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))

    # =====================================================
    # DOUBLONS ET FUSION DE CLIENTS
    # =====================================================
    
    @bp.route('/duplicates')
    @bp.route('/list-duplicates')  # Alias pour compatibilité
    @require_role('admin', 'manager', 'staff')
    def list_customer_duplicates():
        """Liste les doublons potentiels de clients"""
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.index'))
            
            cursor = conn.cursor()
            
            # Recherche de doublons basés sur email, téléphone ou nom/prénom similaires
            cursor.execute("""
                SELECT c1.id as id1, c1.name as name1, c1.email as email1, c1.phone as phone1,
                       c2.id as id2, c2.name as name2, c2.email as email2, c2.phone as phone2,
                       'email' as duplicate_type
                FROM customers c1
                JOIN customers c2 ON c1.email = c2.email 
                WHERE c1.id < c2.id AND c1.email IS NOT NULL AND c1.email != ''
                
                UNION ALL
                
                SELECT c1.id as id1, c1.name as name1, c1.email as email1, c1.phone as phone1,
                       c2.id as id2, c2.name as name2, c2.email as email2, c2.phone as phone2,
                       'phone' as duplicate_type
                FROM customers c1
                JOIN customers c2 ON c1.phone = c2.phone 
                WHERE c1.id < c2.id AND c1.phone IS NOT NULL AND c1.phone != ''
                
                ORDER BY duplicate_type, id1
            """)
            
            duplicates = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'success': True,
                    'duplicates': duplicates,
                    'count': len(duplicates)
                })
            
            from flask import render_template
            return render_template('customers/duplicates.html', duplicates=duplicates)
            
        except Exception as e:
            log_error(f"Erreur détection doublons: {e}")
            from flask import flash
            flash('Erreur lors de la détection des doublons', 'error')
            return redirect(url_for('customers.index'))

    # =====================================================
    # TOURNÉES DE LIVRAISON
    # =====================================================
    
    @bp.route('/delivery-routes')
    @require_role('admin', 'manager', 'staff')
    def delivery_routes():
        """Page de gestion des tournées de livraison"""
        try:
            conn = get_db_connection()
            if not conn:
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.index'))
            
            cursor = conn.cursor()
            
            # Récupérer les clients avec adresses pour optimisation des tournées
            cursor.execute("""
                SELECT c.id, c.name, c.address, c.city, c.postal_code,
                       COUNT(wo.id) as pending_work_orders
                FROM customers c
                LEFT JOIN work_orders wo ON c.id = wo.customer_id AND wo.status = 'scheduled'
                WHERE c.address IS NOT NULL AND c.address != ''
                GROUP BY c.id
                HAVING pending_work_orders > 0 OR c.id IS NOT NULL
                ORDER BY pending_work_orders DESC, c.city, c.name
            """)
            
            customers_routes = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'success': True,
                    'customers_routes': customers_routes,
                    'count': len(customers_routes)
                })
            
            from flask import render_template
            return render_template('customers/delivery_routes.html', 
                                 customers_routes=customers_routes)
            
        except Exception as e:
            log_error(f"Erreur tournées livraison: {e}")
            from flask import flash
            flash('Erreur chargement tournées', 'error')
            return redirect(url_for('customers.index'))
    
    # =====================================================
    # TIMELINE CLIENT
    # =====================================================
    
    @bp.route('/<int:customer_id>/timeline')
    @require_role('admin', 'manager', 'staff')
    def customer_timeline(customer_id):
        """Afficher la timeline d'un client"""
        try:
            conn = get_db_connection()
            if not conn:
                from flask import flash
                flash('Erreur de connexion à la base de données', 'error')
                return redirect(url_for('customers.index'))
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Récupérer les informations du client
            cursor.execute("SELECT * FROM customers WHERE id = %s", [customer_id])
            customer = cursor.fetchone()
            
            if not customer:
                from flask import flash
                flash('Client non trouvé', 'error')
                return redirect(url_for('customers.index'))
            
            # Récupérer la timeline du client
            cursor.execute("""
                SELECT 
                    activity_type, description, activity_date, 
                    user_id, metadata
                FROM customer_activities 
                WHERE customer_id = %s 
                ORDER BY activity_date DESC
                LIMIT 100
            """, [customer_id])
            
            activities = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    'success': True,
                    'customer': customer,
                    'activities': activities,
                    'count': len(activities)
                })
            
            from flask import render_template
            return render_template('customers/timeline.html', 
                                 customer=customer,
                                 activities=activities)
            
        except Exception as e:
            log_error(f"Erreur timeline client {customer_id}: {e}")
            from flask import flash
            flash('Erreur chargement timeline', 'error')
            return redirect(url_for('customers.index'))

    @bp.route('/api/customers/<int:customer_id>/toggle-status', methods=['POST'])
    @require_role('admin', 'manager')
    def toggle_customer_status_api(customer_id):
        """Activer/désactiver un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Récupérer le statut actuel
            cursor.execute("SELECT is_active, name FROM customers WHERE id = %s", [customer_id])
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Inverser le statut
            new_status = not customer['is_active']
            
            cursor.execute("""
                UPDATE customers 
                SET is_active = %s, updated_at = NOW() 
                WHERE id = %s
            """, [new_status, customer_id])
            
            # Log de l'activité
            action = 'activate' if new_status else 'deactivate'
            status_text = 'activé' if new_status else 'désactivé'
            
            log_customer_activity(
                customer_id,
                action,
                f"Client {status_text}",
                f"Statut changé: {'Actif' if new_status else 'Inactif'}",
                None,
                'customers'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Client {status_text} avec succès',
                'new_status': new_status,
                'status_text': 'Actif' if new_status else 'Inactif'
            })
            
        except Exception as e:
            log_error(f"Erreur toggle status client {customer_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # =====================================================
    # API ACTIVITIES POUR ONGLET ACTIVITY
    # =====================================================
    
    @bp.route('/api/customers/<int:customer_id>/activities', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_customer_activities(customer_id):
        """Récupérer les activités d'un client pour l'onglet Activity"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Vérifier que le client existe
            cursor.execute("SELECT id, name FROM customers WHERE id = %s", [customer_id])
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Paramètres de pagination
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            activity_type = request.args.get('type', None)
            
            # Construction de la requête avec filtres
            base_query = """
                SELECT ca.*, u.name as actor_name
                FROM customer_activity ca
                LEFT JOIN users u ON ca.actor_id = u.id
                WHERE ca.customer_id = %s
            """
            
            params = [customer_id]
            
            if activity_type:
                base_query += " AND ca.activity_type = %s"
                params.append(activity_type)
            
            base_query += " ORDER BY ca.created_at DESC"
            
            # Pagination
            offset = (page - 1) * per_page
            query = base_query + f" LIMIT {per_page} OFFSET {offset}"
            
            cursor.execute(query, params)
            activities = cursor.fetchall()
            
            # Compter le total pour la pagination
            count_query = "SELECT COUNT(*) as total FROM customer_activity ca WHERE ca.customer_id = %s"
            count_params = [customer_id]
            
            if activity_type:
                count_query += " AND ca.activity_type = %s"
                count_params.append(activity_type)
            
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()['total']
            
            # Types d'activités disponibles
            cursor.execute("""
                SELECT DISTINCT activity_type, COUNT(*) as count
                FROM customer_activity 
                WHERE customer_id = %s 
                GROUP BY activity_type
                ORDER BY count DESC
            """, [customer_id])
            activity_types = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'activities': activities,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                },
                'activity_types': activity_types,
                'customer': customer
            })
            
        except Exception as e:
            log_error(f"Erreur récupération activités client {customer_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/customers/<int:customer_id>/activity', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def add_customer_activity(customer_id):
        """Ajouter une activité client manuelle"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'message': 'Données manquantes'}), 400
            
            activity_type = data.get('activity_type')
            title = data.get('title')
            description = data.get('description', '')
            
            if not activity_type or not title:
                return jsonify({'success': False, 'message': 'Type et titre requis'}), 400
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
            # Vérifier que le client existe
            cursor.execute("SELECT id FROM customers WHERE id = %s", [customer_id])
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Ajouter l'activité
            current_user = get_current_user()
            actor_id = current_user.id if current_user else None
            
            log_customer_activity(
                customer_id,
                activity_type,
                title,
                description,
                None,
                'manual_entry',
                actor_id
            )
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Activité ajoutée avec succès'
            })
            
        except Exception as e:
            log_error(f"Erreur ajout activité client {customer_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # =====================================================
    # API DOCUMENTS POUR ONGLET DOCUMENTS
    # =====================================================
    
    @bp.route('/api/customers/<int:customer_id>/documents', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_customer_documents(customer_id):
        """Récupérer les documents d'un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Vérifier que le client existe
            cursor.execute("SELECT id, name FROM customers WHERE id = %s", [customer_id])
            customer = cursor.fetchone()
            
            if not customer:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Récupérer les documents
            cursor.execute("""
                SELECT 
                    id, filename, original_filename, file_size, mime_type,
                    category, description, is_private, created_at,
                    uploaded_by
                FROM customer_documents 
                WHERE customer_id = %s 
                ORDER BY created_at DESC
            """, [customer_id])
            
            documents = cursor.fetchall()
            
            # Statistiques
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    SUM(file_size) as total_size,
                    COUNT(CASE WHEN category = 'contract' THEN 1 END) as contracts,
                    COUNT(CASE WHEN category = 'invoice' THEN 1 END) as invoices,
                    COUNT(CASE WHEN category = 'technical' THEN 1 END) as technical,
                    COUNT(CASE WHEN category = 'other' THEN 1 END) as other
                FROM customer_documents 
                WHERE customer_id = %s
            """, [customer_id])
            
            stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'documents': documents,
                'stats': stats,
                'customer': customer
            })
            
        except Exception as e:
            log_error(f"Erreur récupération documents client {customer_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/customers/<int:customer_id>/documents', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def upload_customer_document(customer_id):
        """Upload d'un document client"""
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'Nom de fichier vide'}), 400
            
            # Paramètres du formulaire
            category = request.form.get('category', 'other')
            description = request.form.get('description', '')
            is_private = request.form.get('is_private', 'false').lower() == 'true'
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
            # Vérifier que le client existe
            cursor.execute("SELECT id FROM customers WHERE id = %s", [customer_id])
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
            
            # Générer un nom de fichier sécurisé
            from werkzeug.utils import secure_filename
            import uuid
            import os
            
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1]
            filename = f"{uuid.uuid4()}{file_extension}"
            
            # Créer le répertoire s'il n'existe pas
            upload_dir = f"/home/amenard/Chronotech/ChronoTech/uploads/customers/{customer_id}"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Sauvegarder le fichier
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Informations sur le fichier
            file_size = os.path.getsize(file_path)
            mime_type = file.content_type or 'application/octet-stream'
            
            # Enregistrer en base
            current_user = get_current_user()
            uploaded_by = current_user.id if current_user else None
            
            cursor.execute("""
                INSERT INTO customer_documents 
                (customer_id, filename, original_filename, file_path, file_size, 
                 mime_type, category, description, is_private, uploaded_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                customer_id, filename, original_filename, file_path, file_size,
                mime_type, category, description, is_private, uploaded_by
            ])
            
            document_id = cursor.lastrowid
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'document_upload',
                f"Document téléchargé: {original_filename}",
                f"Catégorie: {category}, Taille: {file_size} bytes",
                document_id,
                'documents'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Document téléchargé avec succès',
                'document_id': document_id,
                'filename': original_filename
            })
            
        except Exception as e:
            log_error(f"Erreur upload document client {customer_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/api/customers/<int:customer_id>/documents/<int:document_id>', methods=['DELETE'])
    @require_role('admin', 'manager')
    def delete_customer_document(customer_id, document_id):
        """Supprimer un document client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Récupérer les informations du document
            cursor.execute("""
                SELECT filename, original_filename, file_path
                FROM customer_documents 
                WHERE id = %s AND customer_id = %s
            """, [document_id, customer_id])
            
            document = cursor.fetchone()
            
            if not document:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Document non trouvé'}), 404
            
            # Supprimer le fichier physique
            import os
            if os.path.exists(document['file_path']):
                os.remove(document['file_path'])
            
            # Supprimer de la base
            cursor.execute("""
                DELETE FROM customer_documents 
                WHERE id = %s AND customer_id = %s
            """, [document_id, customer_id])
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'document_delete',
                f"Document supprimé: {document['original_filename']}",
                f"ID: {document_id}",
                document_id,
                'documents'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Document supprimé avec succès'
            })
            
        except Exception as e:
            log_error(f"Erreur suppression document {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
