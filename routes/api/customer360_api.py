"""
API Customer 360 - Vue complète client
Agrège toutes les données liées à un client
"""
from flask import Blueprint, jsonify, request, session
from core.database import db_manager
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

customer360_api = Blueprint('customer360_api', __name__)

@customer360_api.route('/customer/<int:customer_id>/overview', methods=['GET'])
def get_customer_overview(customer_id):
    """Récupère la vue 360° complète d'un client"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Informations client de base
        cursor.execute("""
            SELECT c.*, geo.latitude, geo.longitude
            FROM customers c
            LEFT JOIN geo_coordinates geo ON c.id = geo.customer_id
            WHERE c.id = %s
        """, (customer_id,))
        
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({
                'success': False,
                'error': 'Client non trouvé'
            }), 404
        
        # Interventions (tous les bons de travail)
        cursor.execute("""
            SELECT 
                wo.*,
                u.name as technician_name,
                u.phone as technician_phone,
                (SELECT COUNT(*) FROM intervention_notes WHERE work_order_id = wo.id) as notes_count,
                (SELECT COUNT(*) FROM intervention_media WHERE work_order_id = wo.id) as media_count
            FROM work_orders wo
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            WHERE wo.customer_id = %s
            ORDER BY wo.created_at DESC
            LIMIT 50
        """, (customer_id,))
        
        interventions = cursor.fetchall()
        
        # Statistiques des interventions
        cursor.execute("""
            SELECT 
                COUNT(*) as total_interventions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_interventions,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as active_interventions,
                AVG(CASE WHEN actual_duration IS NOT NULL THEN actual_duration END) as avg_duration,
                SUM(CASE WHEN total_amount IS NOT NULL THEN total_amount ELSE 0 END) as total_revenue
            FROM work_orders
            WHERE customer_id = %s
        """, (customer_id,))
        
        intervention_stats = cursor.fetchone()
        
        # Véhicules (si la table existe)
        vehicles = []
        try:
            cursor.execute("""
                SELECT v.*, 
                    (SELECT COUNT(*) FROM work_orders WHERE vehicle_id = v.id) as intervention_count
                FROM vehicles v
                WHERE v.customer_id = %s
                ORDER BY v.created_at DESC
            """, (customer_id,))
            vehicles = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Table vehicles non disponible: {e}")
        
        # Factures (si la table existe)
        invoices = []
        try:
            cursor.execute("""
                SELECT i.*,
                    CASE 
                        WHEN payment_date IS NOT NULL THEN 'paid'
                        WHEN due_date < CURDATE() THEN 'overdue'
                        ELSE 'pending'
                    END as payment_status
                FROM invoices i
                WHERE i.customer_id = %s
                ORDER BY i.created_at DESC
                LIMIT 20
            """, (customer_id,))
            invoices = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Table invoices non disponible: {e}")
        
        # Équipements du client
        equipment = []
        try:
            cursor.execute("""
                SELECT e.*,
                    CASE 
                        WHEN next_maintenance_due <= CURDATE() THEN 'due'
                        WHEN next_maintenance_due <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 'soon'
                        ELSE 'ok'
                    END as maintenance_status
                FROM equipment e
                WHERE e.customer_id = %s
                ORDER BY e.next_maintenance_due ASC
            """, (customer_id,))
            equipment = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Table equipment non disponible: {e}")
        
        # Communications récentes (notes, messages)
        cursor.execute("""
            SELECT 
                'note' as type,
                in_notes.id,
                in_notes.note_text as content,
                in_notes.created_at,
                u.name as author_name,
                wo.claim_number as context_ref
            FROM intervention_notes in_notes
            JOIN work_orders wo ON in_notes.work_order_id = wo.id
            LEFT JOIN users u ON in_notes.created_by = u.id
            WHERE wo.customer_id = %s
            
            UNION ALL
            
            SELECT 
                'chat' as type,
                cm.id,
                cm.message as content,
                cm.created_at,
                u.name as author_name,
                CONCAT('Bon #', wo.claim_number) as context_ref
            FROM chat_messages cm
            JOIN work_orders wo ON cm.context_id = wo.id
            LEFT JOIN users u ON cm.user_id = u.id
            WHERE cm.context_type = 'work_order' 
            AND wo.customer_id = %s
            
            ORDER BY created_at DESC
            LIMIT 10
        """, (customer_id, customer_id))
        
        communications = cursor.fetchall()
        
        # Métriques de satisfaction (calculées)
        satisfaction_metrics = {
            'completion_rate': 0,
            'avg_rating': 0,
            'on_time_rate': 0,
            'response_time_avg': 0
        }
        
        if intervention_stats['total_interventions'] > 0:
            satisfaction_metrics['completion_rate'] = round(
                (intervention_stats['completed_interventions'] / intervention_stats['total_interventions']) * 100, 1
            )
        
        # Calcul du taux de ponctualité
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN completion_date <= scheduled_date THEN 1 END) as on_time
            FROM work_orders
            WHERE customer_id = %s 
            AND status = 'completed'
            AND completion_date IS NOT NULL
            AND scheduled_date IS NOT NULL
        """, (customer_id,))
        
        punctuality = cursor.fetchone()
        if punctuality['total'] > 0:
            satisfaction_metrics['on_time_rate'] = round(
                (punctuality['on_time'] / punctuality['total']) * 100, 1
            )
        
        conn.close()
        
        return jsonify({
            'success': True,
            'customer': customer,
            'interventions': interventions,
            'intervention_stats': intervention_stats,
            'vehicles': vehicles,
            'invoices': invoices,
            'equipment': equipment,
            'communications': communications,
            'satisfaction_metrics': satisfaction_metrics,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la vue 360° client: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer360_api.route('/customers/search', methods=['GET'])
def search_customers():
    """Recherche de clients pour la sélection"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))
        
        if len(query) < 2:
            return jsonify({
                'success': True,
                'customers': []
            })
        
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Recherche par nom, email ou téléphone
        cursor.execute("""
            SELECT 
                c.id, c.name, c.email, c.phone, c.city, c.customer_type,
                COUNT(wo.id) as intervention_count,
                MAX(wo.created_at) as last_intervention_date
            FROM customers c
            LEFT JOIN work_orders wo ON c.id = wo.customer_id
            WHERE c.name LIKE %s 
            OR c.email LIKE %s 
            OR c.phone LIKE %s
            GROUP BY c.id, c.name, c.email, c.phone, c.city, c.customer_type
            ORDER BY c.name ASC
            LIMIT %s
        """, (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        
        customers = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'customers': customers
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de clients: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@customer360_api.route('/customer/<int:customer_id>/timeline', methods=['GET'])
def get_customer_timeline(customer_id):
    """Timeline chronologique des événements client"""
    try:
        days_back = int(request.args.get('days', 90))
        date_from = datetime.now() - timedelta(days=days_back)
        
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Événements de la timeline
        cursor.execute("""
            SELECT 
                'work_order_created' as event_type,
                wo.id as event_id,
                wo.claim_number as title,
                wo.problem_description as description,
                wo.created_at as event_date,
                wo.priority,
                'primary' as badge_color,
                u.name as actor
            FROM work_orders wo
            LEFT JOIN users u ON wo.created_by = u.id
            WHERE wo.customer_id = %s AND wo.created_at >= %s
            
            UNION ALL
            
            SELECT 
                'work_order_completed' as event_type,
                wo.id as event_id,
                CONCAT('Intervention terminée: ', wo.claim_number) as title,
                wo.resolution_description as description,
                wo.completion_date as event_date,
                wo.priority,
                'success' as badge_color,
                u.name as actor
            FROM work_orders wo
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            WHERE wo.customer_id = %s 
            AND wo.completion_date >= %s
            AND wo.status = 'completed'
            
            UNION ALL
            
            SELECT 
                'invoice_created' as event_type,
                i.id as event_id,
                CONCAT('Facture #', i.invoice_number) as title,
                CONCAT('Montant: ', i.total_amount, '€') as description,
                i.created_at as event_date,
                'medium' as priority,
                'info' as badge_color,
                'Système' as actor
            FROM invoices i
            WHERE i.customer_id = %s AND i.created_at >= %s
            
            ORDER BY event_date DESC
            LIMIT 50
        """, (customer_id, date_from, customer_id, date_from, customer_id, date_from))
        
        timeline_events = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'timeline': timeline_events,
            'period_days': days_back
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la timeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
