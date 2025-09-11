"""
Routes API Sprint 4 - Analyse prédictive et proactive
Endpoints pour maintenance prévisionnelle, heatmap et eco-scoring
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
from core.predictive_analytics import predictive_engine, heatmap_manager, eco_scoring
from core.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

# Blueprint pour les API d'analyse prédictive
predictive_bp = Blueprint('predictive', __name__, url_prefix='/api/predictive')

@predictive_bp.route('/dashboard')
@login_required
def predictive_dashboard():
    """Page principale du dashboard prédictif"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Statistiques générales
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT vmp.vehicle_id) as vehicles_monitored,
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN urgency_level = 'critical' THEN 1 END) as critical_alerts,
                COUNT(CASE WHEN urgency_level = 'high' THEN 1 END) as high_alerts,
                AVG(confidence_score) as avg_confidence
            FROM vehicle_maintenance_predictions vmp
            WHERE is_dismissed = FALSE
        """)
        
        stats = cursor.fetchone() or {}
        
        return render_template('predictive/dashboard.html', 
                             title="Dashboard Prédictif",
                             stats=stats)
        
    except Exception as e:
        logger.error(f"Erreur dashboard prédictif: {e}")
        return render_template('error.html', error=str(e)), 500
    finally:
        if 'conn' in locals():
            conn.close()

@predictive_bp.route('/maintenance/analyze/<int:vehicle_id>')
@login_required
def analyze_vehicle(vehicle_id):
    """Analyse prédictive d'un véhicule spécifique"""
    try:
        result = predictive_engine.analyze_vehicle_health(vehicle_id)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Erreur analyse véhicule {vehicle_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@predictive_bp.route('/maintenance/predictions')
@login_required
def get_maintenance_predictions():
    """Récupère toutes les prédictions de maintenance actives"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Filtres optionnels
        urgency_filter = request.args.get('urgency')
        vehicle_filter = request.args.get('vehicle_id')
        
        conditions = ["vmp.is_dismissed = FALSE"]
        params = []
        
        if urgency_filter:
            conditions.append("vmp.urgency_level = %s")
            params.append(urgency_filter)
        
        if vehicle_filter:
            conditions.append("vmp.vehicle_id = %s")
            params.append(int(vehicle_filter))
        
        where_clause = " AND ".join(conditions)
        
        cursor.execute(f"""
            SELECT 
                vmp.*,
                v.license_plate,
                v.make,
                v.model,
                v.year,
                DATEDIFF(vmp.predicted_date, CURDATE()) as days_until_prediction
            FROM vehicle_maintenance_predictions vmp
            INNER JOIN vehicles v ON vmp.vehicle_id = v.id
            WHERE {where_clause}
            ORDER BY 
                FIELD(vmp.urgency_level, 'critical', 'high', 'medium', 'low'),
                vmp.predicted_date ASC
        """, params)
        
        predictions = cursor.fetchall()
        
        # Convertir les dates en string pour JSON
        for prediction in predictions:
            if prediction.get('predicted_date'):
                prediction['predicted_date'] = prediction['predicted_date'].isoformat()
            if prediction.get('created_at'):
                prediction['created_at'] = prediction['created_at'].isoformat()
            if prediction.get('dismissed_at'):
                prediction['dismissed_at'] = prediction['dismissed_at'].isoformat()
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'total': len(predictions)
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération prédictions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@predictive_bp.route('/maintenance/dismiss/<int:prediction_id>')
@login_required
def dismiss_prediction(prediction_id):
    """Rejette une prédiction"""
    try:
        reason = request.json.get('reason', 'Dismissed by user')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE vehicle_maintenance_predictions 
            SET is_dismissed = TRUE,
                dismissed_by = %s,
                dismissed_at = NOW(),
                dismissed_reason = %s
            WHERE id = %s
        """, (current_user.id, reason, prediction_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Prédiction non trouvée'}), 404
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Prédiction rejetée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur rejet prédiction {prediction_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@predictive_bp.route('/heatmap')
@login_required
def get_heatmap_data():
    """Récupère les données de heatmap des interventions"""
    try:
        date_filter = request.args.get('period', 'all')
        
        heatmap_data = heatmap_manager.generate_heatmap_data(date_filter)
        
        if 'error' in heatmap_data:
            return jsonify({'success': False, 'error': heatmap_data['error']}), 400
        
        return jsonify({
            'success': True,
            'data': heatmap_data
        })
        
    except Exception as e:
        logger.error(f"Erreur données heatmap: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@predictive_bp.route('/heatmap/page')
@login_required
def heatmap_page():
    """Page de visualisation de la heatmap"""
    return render_template('predictive/heatmap.html', 
                         title="Heatmap des Interventions")

@predictive_bp.route('/eco-score/calculate/<int:work_order_id>')
@login_required
def calculate_eco_score(work_order_id):
    """Calcule l'eco-score d'un work order"""
    try:
        result = eco_scoring.calculate_eco_score(work_order_id)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Erreur calcul eco-score {work_order_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@predictive_bp.route('/eco-score/stats')
@login_required
def get_eco_score_stats():
    """Récupère les statistiques d'eco-scoring"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Statistiques générales
        cursor.execute("""
            SELECT 
                COUNT(*) as total_scored,
                AVG(eco_score) as avg_score,
                COUNT(CASE WHEN eco_score >= 80 THEN 1 END) as grade_a_count,
                COUNT(CASE WHEN eco_score >= 60 AND eco_score < 80 THEN 1 END) as grade_b_count,
                COUNT(CASE WHEN eco_score >= 40 AND eco_score < 60 THEN 1 END) as grade_c_count,
                COUNT(CASE WHEN eco_score < 40 THEN 1 END) as grade_d_count,
                SUM(carbon_footprint_kg) as total_carbon,
                SUM(recycled_materials_kg) as total_recycled,
                AVG(travel_distance_km) as avg_distance
            FROM work_order_eco_scores
            WHERE calculated_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        
        stats = cursor.fetchone() or {}
        
        # Évolution mensuelle
        cursor.execute("""
            SELECT 
                DATE_FORMAT(calculated_at, '%Y-%m') as month,
                AVG(eco_score) as avg_score,
                COUNT(*) as count
            FROM work_order_eco_scores
            WHERE calculated_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(calculated_at, '%Y-%m')
            ORDER BY month
        """)
        
        monthly_evolution = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'monthly_evolution': monthly_evolution
        })
        
    except Exception as e:
        logger.error(f"Erreur stats eco-score: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@predictive_bp.route('/alerts')
@login_required
def get_predictive_alerts():
    """Récupère les alertes prédictives actives"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        severity_filter = request.args.get('severity')
        alert_type_filter = request.args.get('type')
        
        conditions = ["is_active = TRUE"]
        params = []
        
        if severity_filter:
            conditions.append("severity = %s")
            params.append(severity_filter)
        
        if alert_type_filter:
            conditions.append("alert_type = %s")
            params.append(alert_type_filter)
        
        where_clause = " AND ".join(conditions)
        
        cursor.execute(f"""
            SELECT 
                pa.*,
                u1.name as acknowledged_by_name,
                u2.name as resolved_by_name
            FROM predictive_alerts pa
            LEFT JOIN users u1 ON pa.acknowledged_by = u1.id
            LEFT JOIN users u2 ON pa.resolved_by = u2.id
            WHERE {where_clause}
            ORDER BY 
                FIELD(severity, 'critical', 'error', 'warning', 'info'),
                created_at DESC
        """, params)
        
        alerts = cursor.fetchall()
        
        # Convertir les dates pour JSON
        for alert in alerts:
            for date_field in ['created_at', 'acknowledged_at', 'resolved_at']:
                if alert.get(date_field):
                    alert[date_field] = alert[date_field].isoformat()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'total': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération alertes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@predictive_bp.route('/alerts/acknowledge/<int:alert_id>')
@login_required
def acknowledge_alert(alert_id):
    """Acquitte une alerte prédictive"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE predictive_alerts 
            SET acknowledged_at = NOW(),
                acknowledged_by = %s
            WHERE id = %s AND acknowledged_at IS NULL
        """, (current_user.id, alert_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Alerte non trouvée ou déjà acquittée'}), 404
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Alerte acquittée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur acquittement alerte {alert_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@predictive_bp.route('/batch/analyze-all-vehicles')
@login_required
def batch_analyze_vehicles():
    """Lance une analyse prédictive sur tous les véhicules"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer tous les véhicules actifs
        cursor.execute("SELECT id FROM vehicles WHERE is_active = TRUE")
        vehicle_ids = [row[0] for row in cursor.fetchall()]
        
        results = []
        success_count = 0
        error_count = 0
        
        for vehicle_id in vehicle_ids:
            try:
                result = predictive_engine.analyze_vehicle_health(vehicle_id)
                if 'error' not in result:
                    success_count += 1
                    results.append({
                        'vehicle_id': vehicle_id,
                        'status': 'success',
                        'predictions_count': len(result.get('predictions', []))
                    })
                else:
                    error_count += 1
                    results.append({
                        'vehicle_id': vehicle_id,
                        'status': 'error',
                        'error': result['error']
                    })
            except Exception as e:
                error_count += 1
                results.append({
                    'vehicle_id': vehicle_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_vehicles': len(vehicle_ids),
                'success_count': success_count,
                'error_count': error_count
            },
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Erreur analyse batch véhicules: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Routes pour les templates additionnels
@predictive_bp.route('/maintenance')
@login_required
def maintenance_page():
    """Page de maintenance prédictive"""
    return render_template('predictive/maintenance.html', 
                         title="Maintenance Prédictive")

@predictive_bp.route('/eco-scoring')
@login_required
def eco_scoring_page():
    """Page d'eco-scoring"""
    return render_template('predictive/eco_scoring.html', 
                         title="Eco-Scoring")
