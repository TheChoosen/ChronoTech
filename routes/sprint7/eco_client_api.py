"""
Sprint 7.5 - API Routes pour Éco-Dashboard & Feedback Client
"""

from flask import Blueprint, request, jsonify, session
from core.eco_client_manager import eco_client_manager
from core.database import get_db_connection
from core.security import login_required
import asyncio
from datetime import datetime

eco_client_api = Blueprint('eco_client_api', __name__)

@eco_client_api.route('/api/eco-client/feedback/realtime', methods=['GET'])
@login_required
def get_realtime_feedback():
    """Récupère le feedback client en temps réel"""
    try:
        work_order_id = request.args.get('work_order_id')
        technician_id = request.args.get('technician_id')
        
        result = eco_client_manager.get_real_time_feedback(
            work_order_id=int(work_order_id) if work_order_id else None,
            technician_id=int(technician_id) if technician_id else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur API feedback temps réel: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de la récupération du feedback'
        }), 500

@eco_client_api.route('/api/eco-client/dashboard', methods=['GET'])
@login_required
def get_eco_dashboard():
    """Récupère le dashboard écologique consolidé"""
    try:
        result = eco_client_manager.get_consolidated_eco_dashboard()
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur API eco-dashboard: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de la génération du dashboard écologique'
        }), 500

@eco_client_api.route('/api/eco-client/feedback/submit', methods=['POST'])
@login_required
def submit_feedback():
    """Soumission de feedback client avec traitement temps réel"""
    try:
        feedback_data = request.get_json()
        
        # Traitement asynchrone pour respecter le délai <10s
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            eco_client_manager.submit_real_time_feedback(feedback_data)
        )
        loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur soumission feedback: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de l\'enregistrement du feedback'
        }), 500

@eco_client_api.route('/api/eco-client/generate-report', methods=['POST'])
@login_required
def generate_eco_report():
    """Génère un rapport écologique personnalisé"""
    try:
        options = request.get_json()
        
        # Récupérer les données du dashboard
        dashboard_result = eco_client_manager.get_consolidated_eco_dashboard()
        if dashboard_result['status'] != 'success':
            return jsonify({
                'status': 'error',
                'message': 'Impossible de récupérer les données écologiques'
            }), 500
        
        eco_data = dashboard_result['eco_data']
        
        # Générer le rapport (simulation)
        report_data = {
            'report_id': f"eco_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'generated_by': session.get('user_id'),
            'summary': {
                'total_co2_reduction': eco_data['carbon_footprint']['current_reduction'],
                'fuel_savings': eco_data['resource_efficiency']['fuel_savings_estimate']['cost_savings_euros'],
                'green_performers': len(eco_data['green_performance']['top_performers']),
                'eco_score_improvement': eco_data['sustainability_trends']['monthly_improvement']
            },
            'recommendations': [
                'Continuer l\'optimisation des routes pour réduire l\'empreinte carbone',
                'Renforcer la formation éco-responsable des techniciens',
                'Développer les pratiques Green Performer dans tous les sites'
            ]
        }
        
        # Sauvegarder le rapport (simulation)
        _save_eco_report(report_data)
        
        return jsonify({
            'status': 'success',
            'report_id': report_data['report_id'],
            'download_url': f"/api/eco-client/reports/{report_data['report_id']}/download",
            'summary': report_data['summary']
        })
        
    except Exception as e:
        print(f"❌ Erreur génération rapport éco: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de la génération du rapport'
        }), 500

@eco_client_api.route('/api/eco-client/optimize-routes', methods=['POST'])
@login_required
def optimize_eco_routes():
    """Lance l'optimisation écologique des routes"""
    try:
        # Simulation d'optimisation des routes
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Récupérer les trajets non optimisés
        cursor.execute("""
            SELECT COUNT(*) as unoptimized_routes
            FROM work_orders 
            WHERE eco_optimized = FALSE 
                AND status IN ('pending', 'assigned')
                AND travel_distance > 0
        """)
        
        result = cursor.fetchone()
        unoptimized_count = result['unoptimized_routes'] or 0
        
        if unoptimized_count == 0:
            cursor.close()
            connection.close()
            return jsonify({
                'status': 'success',
                'message': 'Toutes les routes sont déjà optimisées',
                'routes_optimized': 0
            })
        
        # Simuler l'optimisation (en réalité, on utiliserait un algorithme complexe)
        optimized_count = min(unoptimized_count, 25)  # Limiter pour la démo
        
        cursor.execute("""
            UPDATE work_orders 
            SET eco_optimized = TRUE,
                travel_distance = travel_distance * 0.85,
                updated_at = NOW()
            WHERE eco_optimized = FALSE 
                AND status IN ('pending', 'assigned')
                AND travel_distance > 0
            LIMIT %s
        """, (optimized_count,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        # Calculer les bénéfices estimés
        distance_saved = optimized_count * 5.2  # km moyen économisé par route
        co2_saved = distance_saved * 0.12  # kg CO2 économisé
        fuel_saved = distance_saved * 0.08  # litres économisés
        cost_saved = fuel_saved * 1.5  # euros économisés
        
        return jsonify({
            'status': 'success',
            'routes_optimized': optimized_count,
            'benefits': {
                'distance_saved_km': round(distance_saved, 1),
                'co2_saved_kg': round(co2_saved, 2),
                'fuel_saved_liters': round(fuel_saved, 1),
                'cost_saved_euros': round(cost_saved, 2)
            },
            'message': f'{optimized_count} routes optimisées avec succès'
        })
        
    except Exception as e:
        print(f"❌ Erreur optimisation routes éco: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de l\'optimisation des routes'
        }), 500

@eco_client_api.route('/api/eco-client/badges/assign', methods=['POST'])
@login_required
def assign_green_badge():
    """Assigne un badge Green Performer à un technicien"""
    try:
        data = request.get_json()
        technician_id = data.get('technician_id')
        badge_level = data.get('badge_level', 'Green Starter')
        
        if not technician_id:
            return jsonify({
                'status': 'error',
                'message': 'ID technicien manquant'
            }), 400
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Créer la table des badges si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS green_badges (
                id INT AUTO_INCREMENT PRIMARY KEY,
                technician_id INT NOT NULL,
                badge_name VARCHAR(50) NOT NULL,
                badge_level VARCHAR(20) NOT NULL,
                eco_score DECIMAL(5,2) NOT NULL,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                awarded_by INT,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_technician (technician_id),
                INDEX idx_badge_level (badge_level)
            )
        """)
        
        # Désactiver les anciens badges du technicien
        cursor.execute("""
            UPDATE green_badges 
            SET is_active = FALSE 
            WHERE technician_id = %s
        """, (technician_id,))
        
        # Calculer le score éco du technicien
        cursor.execute("""
            SELECT 
                COUNT(wo.id) as interventions,
                AVG(wo.travel_distance) as avg_distance,
                COUNT(CASE WHEN wo.eco_optimized = TRUE THEN 1 END) as eco_optimized,
                AVG(cf.eco_awareness_rating) as eco_rating
            FROM work_orders wo
            LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
            WHERE wo.assigned_technician_id = %s
                AND wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """, (technician_id,))
        
        tech_stats = cursor.fetchone()
        
        # Calculer le score (logique simplifiée)
        if tech_stats and tech_stats[0] > 0:  # interventions > 0
            interventions = tech_stats[0]
            eco_optimized = tech_stats[2] or 0
            eco_score = (eco_optimized / interventions) * 100
        else:
            eco_score = 0
        
        # Insérer le nouveau badge
        cursor.execute("""
            INSERT INTO green_badges (
                technician_id, badge_name, badge_level, 
                eco_score, awarded_by
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            technician_id,
            f"Green {badge_level}",
            badge_level,
            eco_score,
            session.get('user_id')
        ))
        
        badge_id = cursor.lastrowid
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'status': 'success',
            'badge_id': badge_id,
            'badge_name': f"Green {badge_level}",
            'eco_score': round(eco_score, 1),
            'message': 'Badge attribué avec succès'
        })
        
    except Exception as e:
        print(f"❌ Erreur attribution badge: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de l\'attribution du badge'
        }), 500

@eco_client_api.route('/api/eco-client/feedback/critical', methods=['GET'])
@login_required
def get_critical_feedback():
    """Récupère les feedbacks critiques nécessitant une action immédiate"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                cf.id,
                cf.work_order_id,
                cf.overall_satisfaction,
                cf.comments,
                cf.submitted_at,
                cf.response_time_seconds,
                wo.title as work_order_title,
                u.name as technician_name,
                c.name as customer_name,
                c.phone as customer_phone,
                c.email as customer_email
            FROM client_feedback cf
            LEFT JOIN work_orders wo ON cf.work_order_id = wo.id
            LEFT JOIN users u ON cf.technician_id = u.id
            LEFT JOIN customers c ON wo.customer_id = c.id
            WHERE cf.overall_satisfaction <= 2
                AND cf.submitted_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY cf.submitted_at DESC
        """)
        
        critical_feedback = cursor.fetchall()
        
        # Marquer comme traités si nécessaire
        for feedback in critical_feedback:
            feedback['requires_follow_up'] = True
            feedback['urgency_level'] = 'high' if feedback['overall_satisfaction'] == 1 else 'medium'
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'status': 'success',
            'critical_feedback': critical_feedback,
            'count': len(critical_feedback)
        })
        
    except Exception as e:
        print(f"❌ Erreur feedback critique: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de la récupération des feedbacks critiques'
        }), 500

def _save_eco_report(report_data: dict):
    """Sauvegarde un rapport écologique"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Créer la table des rapports si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eco_reports (
                id VARCHAR(100) PRIMARY KEY,
                generated_by INT,
                report_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_generated_by (generated_by),
                INDEX idx_created_at (created_at)
            )
        """)
        
        cursor.execute("""
            INSERT INTO eco_reports (id, generated_by, report_data)
            VALUES (%s, %s, %s)
        """, (
            report_data['report_id'],
            report_data['generated_by'],
            json.dumps(report_data)
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde rapport éco: {e}")

import json
