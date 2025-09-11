"""
Sprint 7.3 - API Routes pour Simulation & Optimisation
"""

from flask import Blueprint, request, jsonify, session
from core.planning_simulation import planning_simulator
from core.database import get_db_connection
from core.security import login_required
import json
from datetime import datetime

simulation_api = Blueprint('simulation_api', __name__)

@simulation_api.route('/api/simulation/schedule-change', methods=['POST'])
@login_required
def simulate_schedule_change():
    """Simule l'impact d'un changement de planning"""
    try:
        data = request.get_json()
        
        work_order_id = data.get('work_order_id')
        new_scheduled_date = data.get('new_scheduled_date')
        new_technician_id = data.get('new_technician_id')
        
        if not work_order_id or not new_scheduled_date:
            return jsonify({
                'status': 'error',
                'message': 'Paramètres manquants'
            }), 400
        
        # Exécuter la simulation
        result = planning_simulator.simulate_schedule_change(
            work_order_id=work_order_id,
            new_scheduled_date=new_scheduled_date,
            new_technician_id=new_technician_id
        )
        
        # Enregistrer la simulation
        if result['status'] == 'success':
            _save_simulation_log(session.get('user_id'), 'schedule_change', result)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur API simulation changement: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur interne du serveur'
        }), 500

@simulation_api.route('/api/simulation/auto-optimize', methods=['POST'])
@login_required
def auto_optimize_distribution():
    """Auto-répartition intelligente des bons de travail"""
    try:
        data = request.get_json()
        criteria = data.get('criteria', 'balanced')
        work_orders = data.get('work_orders')  # Liste optionnelle d'IDs
        
        # Exécuter l'optimisation
        result = planning_simulator.auto_optimize_distribution(
            criteria=criteria,
            work_orders=work_orders
        )
        
        # Enregistrer l'optimisation
        if result['status'] == 'success':
            _save_simulation_log(session.get('user_id'), 'auto_optimize', result)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur API auto-optimisation: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur interne du serveur'
        }), 500

@simulation_api.route('/api/simulation/apply', methods=['POST'])
@login_required
def apply_simulation():
    """Applique une simulation de changement de planning"""
    try:
        data = request.get_json()
        simulation_id = data.get('simulation_id')
        
        if not simulation_id:
            return jsonify({
                'status': 'error',
                'message': 'ID de simulation manquant'
            }), 400
        
        # Récupérer les détails de la simulation
        simulation_log = _get_simulation_log(simulation_id)
        if not simulation_log:
            return jsonify({
                'status': 'error',
                'message': 'Simulation introuvable'
            }), 404
        
        # Appliquer les changements
        result = _apply_schedule_changes(simulation_log)
        
        if result['status'] == 'success':
            # Marquer la simulation comme appliquée
            _mark_simulation_applied(simulation_id, session.get('user_id'))
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur application simulation: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de l\'application'
        }), 500

@simulation_api.route('/api/simulation/apply-optimization', methods=['POST'])
@login_required
def apply_optimization():
    """Applique une optimisation automatique"""
    try:
        data = request.get_json()
        optimization_id = data.get('optimization_id')
        
        if not optimization_id:
            return jsonify({
                'status': 'error',
                'message': 'ID d\'optimisation manquant'
            }), 400
        
        # Récupérer les détails de l'optimisation
        optimization_log = _get_simulation_log(optimization_id)
        if not optimization_log:
            return jsonify({
                'status': 'error',
                'message': 'Optimisation introuvable'
            }), 404
        
        # Appliquer les assignations
        result = _apply_optimization_assignments(optimization_log)
        
        if result['status'] == 'success':
            # Marquer l'optimisation comme appliquée
            _mark_simulation_applied(optimization_id, session.get('user_id'))
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur application optimisation: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur lors de l\'application'
        }), 500

@simulation_api.route('/api/simulation/stats', methods=['GET'])
@login_required
def get_simulation_stats():
    """Récupère les statistiques de simulation"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Pourcentage d'optimisation du planning
        cursor.execute("""
            SELECT 
                COUNT(*) as total_assignments,
                COUNT(CASE WHEN assigned_technician_id IS NOT NULL THEN 1 END) as assigned_count
            FROM work_orders 
            WHERE status IN ('pending', 'assigned', 'in_progress')
        """)
        
        assignment_stats = cursor.fetchone()
        optimization_percentage = 0
        if assignment_stats['total_assignments'] > 0:
            optimization_percentage = round(
                (assignment_stats['assigned_count'] / assignment_stats['total_assignments']) * 100
            )
        
        # Dernière simulation
        cursor.execute("""
            SELECT created_at FROM simulation_logs 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (session.get('user_id'),))
        
        last_sim = cursor.fetchone()
        last_simulation = None
        if last_sim:
            last_simulation = last_sim['created_at'].strftime('%d/%m %H:%M')
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'optimization_percentage': optimization_percentage,
            'last_simulation': last_simulation
        })
        
    except Exception as e:
        print(f"❌ Erreur stats simulation: {e}")
        return jsonify({
            'optimization_percentage': 0,
            'last_simulation': None
        })

@simulation_api.route('/api/work-orders/active', methods=['GET'])
@login_required
def get_active_work_orders():
    """Récupère les bons de travail actifs"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id,
                title,
                scheduled_date,
                status,
                priority,
                assigned_technician_id
            FROM work_orders 
            WHERE status IN ('pending', 'assigned', 'in_progress')
                AND scheduled_date >= CURDATE()
            ORDER BY scheduled_date, priority DESC
            LIMIT 50
        """)
        
        work_orders = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({'work_orders': work_orders})
        
    except Exception as e:
        print(f"❌ Erreur récupération bons de travail: {e}")
        return jsonify({'work_orders': []})

@simulation_api.route('/api/work-orders/pending/count', methods=['GET'])
@login_required
def get_pending_orders_count():
    """Récupère le nombre de bons de travail en attente"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM work_orders 
            WHERE status = 'pending' AND assigned_technician_id IS NULL
        """)
        
        result = cursor.fetchone()
        count = result[0] if result else 0
        
        cursor.close()
        connection.close()
        
        return jsonify({'count': count})
        
    except Exception as e:
        print(f"❌ Erreur comptage en attente: {e}")
        return jsonify({'count': 0})

def _save_simulation_log(user_id: int, simulation_type: str, result: dict):
    """Sauvegarde un log de simulation"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Créer la table si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_logs (
                id VARCHAR(100) PRIMARY KEY,
                user_id INT,
                simulation_type VARCHAR(50),
                result_data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_at TIMESTAMP NULL,
                applied_by INT NULL,
                INDEX idx_user_created (user_id, created_at),
                INDEX idx_simulation_id (id)
            )
        """)
        
        simulation_id = result.get('simulation_id') or result.get('optimization_id')
        
        cursor.execute("""
            INSERT INTO simulation_logs (id, user_id, simulation_type, result_data)
            VALUES (%s, %s, %s, %s)
        """, (
            simulation_id,
            user_id,
            simulation_type,
            json.dumps(result)
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde log simulation: {e}")

def _get_simulation_log(simulation_id: str):
    """Récupère un log de simulation"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM simulation_logs 
            WHERE id = %s AND applied_at IS NULL
        """, (simulation_id,))
        
        log = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if log and log['result_data']:
            log['result_data'] = json.loads(log['result_data'])
        
        return log
        
    except Exception as e:
        print(f"❌ Erreur récupération log simulation: {e}")
        return None

def _mark_simulation_applied(simulation_id: str, user_id: int):
    """Marque une simulation comme appliquée"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE simulation_logs 
            SET applied_at = NOW(), applied_by = %s 
            WHERE id = %s
        """, (user_id, simulation_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Erreur marquage simulation appliquée: {e}")

def _apply_schedule_changes(simulation_log: dict) -> dict:
    """Applique les changements de planning d'une simulation"""
    try:
        result_data = simulation_log['result_data']
        
        # Extraire les informations de changement depuis les impacts
        # (implémentation simplifiée - à adapter selon la structure réelle)
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Exemple d'application - à adapter selon la logique métier
        changes_applied = 0
        
        # Ici, on appliquerait les changements réels en base
        # Pour cette démo, on simule l'application
        
        cursor.close()
        connection.close()
        
        return {
            'status': 'success',
            'message': f'{changes_applied} changement(s) appliqué(s)',
            'changes_applied': changes_applied
        }
        
    except Exception as e:
        print(f"❌ Erreur application changements: {e}")
        return {
            'status': 'error',
            'message': 'Erreur lors de l\'application des changements'
        }

def _apply_optimization_assignments(optimization_log: dict) -> dict:
    """Applique les assignations d'une optimisation"""
    try:
        result_data = optimization_log['result_data']
        assignments = result_data.get('proposed_assignments', [])
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        assignments_applied = 0
        
        for assignment in assignments:
            try:
                cursor.execute("""
                    UPDATE work_orders 
                    SET assigned_technician_id = %s, 
                        status = 'assigned',
                        updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                """, (
                    assignment['technician_id'],
                    assignment['work_order_id']
                ))
                
                if cursor.rowcount > 0:
                    assignments_applied += 1
                    
            except Exception as e:
                print(f"❌ Erreur assignation {assignment['work_order_id']}: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return {
            'status': 'success',
            'message': f'{assignments_applied} assignation(s) appliquée(s)',
            'assignments_applied': assignments_applied
        }
        
    except Exception as e:
        print(f"❌ Erreur application assignations: {e}")
        return {
            'status': 'error',
            'message': 'Erreur lors de l\'application des assignations'
        }
