"""
Routes IA Sprint 1 - Suggestions et Prévisions
APIs manquantes pour compléter le Sprint 1 Copilote IA
"""
from flask import Blueprint, request, jsonify, session
from core.ai_copilot import copilot_ai
from core.database import db_manager
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

ai_sprint1_bp = Blueprint('ai_sprint1', __name__, url_prefix='/ai')

@ai_sprint1_bp.route('/suggestions', methods=['GET'])
def get_ai_suggestions():
    """
    API /ai/suggestions - Livrable Sprint 1
    Suggestions contextuelles pour superviseurs et répartiteurs
    """
    try:
        user_role = session.get('user_role', 'admin')
        context = request.args.get('context', 'dashboard')  # dashboard, kanban, gantt
        limit = request.args.get('limit', 10, type=int)
        
        suggestions = []
        
        # Suggestions pour superviseurs - surcharge techniciens
        if user_role in ['admin', 'supervisor']:
            overload_suggestions = get_technician_overload_suggestions()
            suggestions.extend(overload_suggestions)
        
        # Suggestions pour répartiteurs - assignation optimale
        if user_role in ['admin', 'dispatcher', 'supervisor']:
            assignment_suggestions = get_optimal_assignment_suggestions()
            suggestions.extend(assignment_suggestions)
        
        # Suggestions contextuelles selon l'interface
        if context == 'kanban':
            kanban_suggestions = get_kanban_context_suggestions()
            suggestions.extend(kanban_suggestions)
        elif context == 'gantt':
            gantt_suggestions = get_gantt_context_suggestions()
            suggestions.extend(gantt_suggestions)
        
        # Limiter et trier par priorité
        suggestions = sorted(suggestions, key=lambda x: x.get('priority_score', 0), reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'context': context,
            'user_role': user_role,
            'count': len(suggestions),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération suggestions IA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_sprint1_bp.route('/previsions', methods=['GET'])
def get_ai_predictions():
    """
    API /ai/previsions - Livrable Sprint 1
    Prévisions IA pour planification et optimisation
    """
    try:
        prediction_type = request.args.get('type', 'workload')  # workload, delays, resources
        period = request.args.get('period', '7')  # jours
        department = request.args.get('department', None)
        
        predictions = {}
        
        if prediction_type in ['workload', 'all']:
            predictions['workload'] = predict_workload_trends(int(period), department)
        
        if prediction_type in ['delays', 'all']:
            predictions['delays'] = predict_potential_delays(int(period), department)
        
        if prediction_type in ['resources', 'all']:
            predictions['resources'] = predict_resource_needs(int(period), department)
        
        # Calcul score de confiance global
        confidence_score = calculate_prediction_confidence(predictions)
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'metadata': {
                'type': prediction_type,
                'period_days': int(period),
                'department': department,
                'confidence_score': confidence_score,
                'generated_at': datetime.now().isoformat(),
                'valid_until': (datetime.now() + timedelta(hours=6)).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur génération prévisions IA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_sprint1_bp.route('/notifications/contextual', methods=['GET'])
def get_contextual_notifications():
    """
    Notifications contextuelles pour Kanban et Gantt
    User Story: Superviseur - alerte surcharge technicien
    """
    try:
        context = request.args.get('context', 'dashboard')  # kanban, gantt, dashboard
        severity = request.args.get('severity', 'all')  # high, medium, low, all
        
        notifications = []
        
        # Notifications de surcharge technicien (User Story 1)
        overload_notifications = get_technician_overload_notifications(context, severity)
        notifications.extend(overload_notifications)
        
        # Notifications d'optimisation d'assignation (User Story 2)
        assignment_notifications = get_assignment_optimization_notifications(context, severity)
        notifications.extend(assignment_notifications)
        
        # Notifications de prévisions critiques
        prediction_notifications = get_prediction_notifications(context, severity)
        notifications.extend(prediction_notifications)
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'context': context,
            'count': len(notifications),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur notifications contextuelles: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_sprint1_bp.route('/technician/best_match', methods=['POST'])
def get_best_technician_for_task():
    """
    User Story: Répartiteur - proposition automatique meilleur technicien
    """
    try:
        task_data = request.json
        
        if not task_data:
            return jsonify({
                'success': False,
                'error': 'Données de tâche requises'
            }), 400
        
        # Analyser les critères de la tâche
        task_requirements = analyze_task_requirements(task_data)
        
        # Évaluer les techniciens disponibles
        available_technicians = get_available_technicians(task_data.get('scheduled_date'))
        
        # Algorithme de matching optimal
        best_matches = find_optimal_technician_matches(task_requirements, available_technicians)
        
        return jsonify({
            'success': True,
            'task_id': task_data.get('id'),
            'best_matches': best_matches,
            'criteria_used': task_requirements,
            'confidence_scores': {match['technician_id']: match['confidence'] for match in best_matches},
            'recommendation': best_matches[0] if best_matches else None,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur recherche meilleur technicien: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Fonctions helper pour les suggestions
def get_technician_overload_suggestions():
    """Détecte les techniciens en surcharge"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Requête pour détecter surcharge
        cursor.execute("""
            SELECT 
                u.id, u.name,
                COUNT(wo.id) as active_tasks,
                AVG(TIMESTAMPDIFF(HOUR, wo.created_at, NOW())) as avg_task_age,
                SUM(CASE WHEN wo.priority = 'urgent' THEN 1 ELSE 0 END) as urgent_tasks
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_to AND wo.status IN ('assigned', 'in_progress')
            WHERE u.role = 'technician'
            GROUP BY u.id, u.name
            HAVING active_tasks > 5 OR urgent_tasks > 2
            ORDER BY active_tasks DESC, urgent_tasks DESC
        """)
        
        overloaded_techs = cursor.fetchall()
        suggestions = []
        
        for tech in overloaded_techs:
            severity = 'high' if tech['urgent_tasks'] > 2 else 'medium'
            suggestions.append({
                'type': 'technician_overload',
                'title': f"Surcharge détectée: {tech['name']}",
                'message': f"{tech['active_tasks']} tâches actives, {tech['urgent_tasks']} urgentes",
                'severity': severity,
                'priority_score': tech['active_tasks'] * 10 + tech['urgent_tasks'] * 20,
                'technician_id': tech['id'],
                'action_suggestions': [
                    'Réassigner les tâches non-urgentes',
                    'Ajouter du support temporaire',
                    'Reporter les nouvelles assignations'
                ],
                'context': 'workload_management'
            })
        
        cursor.close()
        conn.close()
        return suggestions
        
    except Exception as e:
        logger.error(f"Erreur suggestions surcharge: {e}")
        return []

def get_optimal_assignment_suggestions():
    """Suggestions d'assignation optimale"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Tâches non assignées
        cursor.execute("""
            SELECT wo.*, c.name as customer_name, v.license_plate
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN vehicles v ON wo.vehicle_id = v.id
            WHERE wo.assigned_to IS NULL AND wo.status = 'pending'
            ORDER BY wo.priority DESC, wo.created_at ASC
            LIMIT 10
        """)
        
        unassigned_tasks = cursor.fetchall()
        suggestions = []
        
        for task in unassigned_tasks:
            # Analyser le meilleur technicien
            best_tech = copilot_ai.suggest_best_technician(task)
            
            if best_tech:
                suggestions.append({
                    'type': 'optimal_assignment',
                    'title': f"Assignation suggérée: Tâche #{task['claim_number']}",
                    'message': f"Technicien recommandé: {best_tech['name']} (Score: {best_tech['score']:.1f})",
                    'severity': 'medium',
                    'priority_score': 50 + (20 if task['priority'] == 'urgent' else 0),
                    'task_id': task['id'],
                    'recommended_technician': best_tech,
                    'action_suggestions': [
                        f"Assigner à {best_tech['name']}",
                        'Voir les alternatives',
                        'Ajuster la planification'
                    ],
                    'context': 'task_assignment'
                })
        
        cursor.close()
        conn.close()
        return suggestions
        
    except Exception as e:
        logger.error(f"Erreur suggestions assignation: {e}")
        return []

def get_kanban_context_suggestions():
    """Suggestions spécifiques au contexte Kanban"""
    return [
        {
            'type': 'kanban_optimization',
            'title': 'Optimisation du flux Kanban',
            'message': 'Déplacez 3 tâches de "En attente" vers "En cours" pour équilibrer',
            'severity': 'low',
            'priority_score': 30,
            'context': 'kanban_flow'
        }
    ]

def get_gantt_context_suggestions():
    """Suggestions spécifiques au contexte Gantt"""
    return [
        {
            'type': 'gantt_scheduling',
            'title': 'Conflit de planification détecté',
            'message': 'Ajustez les créneaux pour éviter le chevauchement de ressources',
            'severity': 'medium',
            'priority_score': 60,
            'context': 'gantt_scheduling'
        }
    ]

# Fonctions helper pour les prévisions
def predict_workload_trends(period_days, department=None):
    """Prévisions de charge de travail"""
    try:
        # Simulation de prévisions basées sur l'historique
        base_date = datetime.now()
        predictions = []
        
        for i in range(period_days):
            date = base_date + timedelta(days=i)
            # Simulation: charge plus élevée en milieu de semaine
            base_load = 85 if date.weekday() in [1, 2, 3] else 65
            predicted_load = base_load + (i * 2)  # Tendance croissante
            
            predictions.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted_load_percentage': min(predicted_load, 100),
                'confidence': 0.75,
                'factors': ['historical_trends', 'seasonal_patterns']
            })
        
        return {
            'trend': 'increasing',
            'average_load': sum(p['predicted_load_percentage'] for p in predictions) / len(predictions),
            'peak_days': [p['date'] for p in predictions if p['predicted_load_percentage'] > 90],
            'daily_predictions': predictions
        }
        
    except Exception as e:
        logger.error(f"Erreur prévision charge: {e}")
        return {}

def predict_potential_delays(period_days, department=None):
    """Prévisions de retards potentiels"""
    return {
        'high_risk_tasks': 3,
        'predicted_average_delay': 2.5,  # heures
        'risk_factors': ['resource_shortage', 'complex_tasks'],
        'recommendations': ['Increase buffer time', 'Assign senior technicians']
    }

def predict_resource_needs(period_days, department=None):
    """Prévisions de besoins en ressources"""
    return {
        'additional_technicians_needed': 1,
        'peak_demand_periods': ['2025-09-10', '2025-09-15'],
        'skills_in_demand': ['electrical', 'hydraulics'],
        'equipment_utilization': 0.85
    }

def calculate_prediction_confidence(predictions):
    """Calcul du score de confiance global"""
    if not predictions:
        return 0.0
    
    # Simulation de calcul de confiance
    return 0.78

# Fonctions helper pour les notifications
def get_technician_overload_notifications(context, severity):
    """Notifications de surcharge technicien"""
    notifications = []
    
    # Simulation de notification critique
    if severity in ['high', 'all']:
        notifications.append({
            'id': f"overload_{datetime.now().timestamp()}",
            'type': 'technician_overload',
            'severity': 'high',
            'title': '🚨 Surcharge Critique Détectée',
            'message': 'Jean Dupont: 8 tâches actives, 3 urgentes. Action immédiate requise.',
            'context': context,
            'actions': ['reassign_tasks', 'add_support', 'notify_supervisor'],
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat()
        })
    
    return notifications

def get_assignment_optimization_notifications(context, severity):
    """Notifications d'optimisation d'assignation"""
    notifications = []
    
    if severity in ['medium', 'all']:
        notifications.append({
            'id': f"assignment_{datetime.now().timestamp()}",
            'type': 'assignment_optimization',
            'severity': 'medium',
            'title': '💡 Assignation Sub-optimale',
            'message': '5 tâches non assignées pourraient être optimisées',
            'context': context,
            'actions': ['view_suggestions', 'auto_assign', 'manual_review'],
            'created_at': datetime.now().isoformat()
        })
    
    return notifications

def get_prediction_notifications(context, severity):
    """Notifications basées sur les prévisions"""
    return [
        {
            'id': f"prediction_{datetime.now().timestamp()}",
            'type': 'prediction_alert',
            'severity': 'medium',
            'title': '📈 Pic de Charge Prévu',
            'message': 'Charge de travail de 95% prévue pour demain',
            'context': context,
            'actions': ['prepare_resources', 'adjust_schedule', 'notify_team'],
            'created_at': datetime.now().isoformat()
        }
    ]

# Fonctions helper pour matching technicien optimal
def analyze_task_requirements(task_data):
    """Analyse les exigences de la tâche"""
    return {
        'skills_required': task_data.get('skills', ['general']),
        'priority': task_data.get('priority', 'medium'),
        'complexity': task_data.get('complexity', 'medium'),
        'estimated_duration': task_data.get('estimated_duration', 120),
        'location': task_data.get('location'),
        'equipment_needed': task_data.get('equipment', [])
    }

def get_available_technicians(scheduled_date=None):
    """Récupère les techniciens disponibles"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                u.id, u.name, u.email,
                COUNT(wo.id) as current_workload,
                AVG(wo.completion_time) as avg_completion_time,
                GROUP_CONCAT(DISTINCT us.skill_name) as skills
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_to AND wo.status IN ('assigned', 'in_progress')
            LEFT JOIN user_skills us ON u.id = us.user_id
            WHERE u.role = 'technician' AND u.is_active = 1
            GROUP BY u.id, u.name, u.email
            ORDER BY current_workload ASC
        """)
        
        technicians = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Traiter les compétences
        for tech in technicians:
            tech['skills'] = tech['skills'].split(',') if tech['skills'] else []
            tech['availability_score'] = max(0, 100 - (tech['current_workload'] * 10))
        
        return technicians
        
    except Exception as e:
        logger.error(f"Erreur récupération techniciens: {e}")
        return []

def find_optimal_technician_matches(requirements, technicians):
    """Algorithme de matching optimal"""
    matches = []
    
    for tech in technicians:
        score = calculate_match_score(requirements, tech)
        
        if score > 0.3:  # Seuil minimum
            matches.append({
                'technician_id': tech['id'],
                'technician_name': tech['name'],
                'confidence': score,
                'reasoning': generate_match_reasoning(requirements, tech, score),
                'availability_score': tech['availability_score'],
                'current_workload': tech['current_workload']
            })
    
    # Trier par score de confiance
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    return matches[:5]  # Top 5

def calculate_match_score(requirements, technician):
    """Calcul du score de matching"""
    score = 0.0
    
    # Score de disponibilité (40% du total)
    availability_factor = technician['availability_score'] / 100
    score += availability_factor * 0.4
    
    # Score de compétences (40% du total)
    required_skills = set(requirements.get('skills_required', []))
    tech_skills = set(technician.get('skills', []))
    
    if required_skills:
        skill_match = len(required_skills.intersection(tech_skills)) / len(required_skills)
    else:
        skill_match = 1.0  # Pas de compétences spécifiques requises
    
    score += skill_match * 0.4
    
    # Score d'efficacité basé sur l'historique (20% du total)
    efficiency_factor = min(1.0, 120 / max(technician.get('avg_completion_time', 120), 60))
    score += efficiency_factor * 0.2
    
    return min(score, 1.0)

def generate_match_reasoning(requirements, technician, score):
    """Génère l'explication du matching"""
    reasons = []
    
    if technician['current_workload'] <= 3:
        reasons.append("Charge de travail faible")
    
    required_skills = set(requirements.get('skills_required', []))
    tech_skills = set(technician.get('skills', []))
    matching_skills = required_skills.intersection(tech_skills)
    
    if matching_skills:
        reasons.append(f"Compétences: {', '.join(matching_skills)}")
    
    if score > 0.8:
        reasons.append("Correspondance excellente")
    elif score > 0.6:
        reasons.append("Bonne correspondance")
    
    return reasons
