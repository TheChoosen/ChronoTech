"""
Routes API pour le Copilote IA
"""
from flask import Blueprint, request, jsonify, session
from core.ai_copilot import copilot_ai
from core.database import db_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

copilot_bp = Blueprint('copilot', __name__)

@copilot_bp.route('/insights', methods=['GET'])
def get_insights():
    """Récupère les insights du copilote IA"""
    try:
        user_role = session.get('user_role', 'admin')
        insights = copilot_ai.get_dashboard_insights(user_role)
        
        return jsonify({
            'success': True,
            'insights': insights,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des insights: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@copilot_bp.route('/analyze_task', methods=['POST'])
def analyze_task():
    """Analyse une tâche spécifique"""
    try:
        task_id = request.json.get('task_id')
        
        if not task_id:
            return jsonify({
                'success': False,
                'error': 'task_id requis'
            }), 400
        
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT wo.*, c.name as customer_name, u.name as technician_name
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            WHERE wo.id = %s
        """, (task_id,))
        
        task_data = cursor.fetchone()
        conn.close()
        
        if not task_data:
            return jsonify({
                'success': False,
                'error': 'Tâche non trouvée'
            }), 404
        
        analysis = copilot_ai.analyze_task_delay(task_data)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de la tâche: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@copilot_bp.route('/suggest_reassignment', methods=['POST'])
def suggest_reassignment():
    """Suggère des réassignations pour optimiser la charge"""
    try:
        tech_id = request.json.get('technician_id')
        
        if not tech_id:
            return jsonify({
                'success': False,
                'error': 'technician_id requis'
            }), 400
        
        suggestions = copilot_ai.suggest_reassignment(tech_id)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la suggestion de réassignation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@copilot_bp.route('/execute_suggestion', methods=['POST'])
def execute_suggestion():
    """Exécute une suggestion du copilote"""
    try:
        suggestion_type = request.json.get('type')
        task_id = request.json.get('task_id')
        new_tech_id = request.json.get('new_technician_id')
        
        if suggestion_type == 'reassign_task' and task_id and new_tech_id:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Réassigner la tâche
            cursor.execute("""
                UPDATE work_orders 
                SET assigned_technician_id = %s, updated_at = %s
                WHERE id = %s
            """, (new_tech_id, datetime.now(), task_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Tâche réassignée avec succès'
            })
        
        return jsonify({
            'success': False,
            'error': 'Type de suggestion non pris en charge'
        }), 400
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la suggestion: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
