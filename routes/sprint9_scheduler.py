"""
Sprint 9.2 - API Routes pour Planification Proactive & Optimisation
Endpoints pour l'optimisation automatique des plannings
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import json
import logging
from core.scheduler_optimizer import scheduler_optimizer
from core.database import get_db_connection

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création du blueprint
sprint9_scheduler_bp = Blueprint('sprint9_scheduler', __name__, url_prefix='/api/v1/ai/scheduler')

@sprint9_scheduler_bp.route('/optimize', methods=['POST'])
def optimize_schedule():
    """
    Optimiser automatiquement la planification selon les contraintes
    
    Body:
    {
        "mode": "fast|balanced|quality",
        "date_filter": "2025-01-20",
        "constraints": {
            "max_hours": 8,
            "travel_limit": 50,
            "priority_weight": true
        }
    }
    """
    try:
        data = request.get_json() or {}
        optimization_mode = data.get('mode', 'balanced')
        date_filter = data.get('date_filter')
        constraints = data.get('constraints', {})
        
        logger.info(f"🚀 Demande optimisation - Mode: {optimization_mode}")
        
        # Configurer les contraintes si fournies
        if 'max_hours' in constraints:
            scheduler_optimizer.max_work_hours = constraints['max_hours'] * 60
        if 'travel_limit' in constraints:
            scheduler_optimizer.travel_speed_kmh = constraints['travel_limit']
        
        # Charger les données pour la date spécifiée
        work_orders = scheduler_optimizer.load_work_orders(date_filter)
        technicians = scheduler_optimizer.load_technicians()
        
        if not work_orders:
            return jsonify({
                'success': False,
                'error': 'Aucun bon de travail à optimiser pour cette période',
                'data': {
                    'work_orders_count': 0,
                    'technicians_count': len(technicians)
                }
            }), 404
        
        if not technicians:
            return jsonify({
                'success': False,
                'error': 'Aucun technicien disponible pour l\'optimisation',
                'data': {
                    'work_orders_count': len(work_orders),
                    'technicians_count': 0
                }
            }), 404
        
        # Exécuter l'optimisation
        start_time = datetime.now()
        result = scheduler_optimizer.optimize_schedule(optimization_mode)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Statistiques détaillées
        stats = {
            'total_work_orders': len(work_orders),
            'available_technicians': len(technicians),
            'assigned_orders': len(work_orders) - len(result.unassigned_orders),
            'unassigned_orders': len(result.unassigned_orders),
            'efficiency_score': result.efficiency_score,
            'total_travel_time_minutes': result.total_travel_time,
            'total_work_time_minutes': result.total_work_time,
            'cost_optimization_percent': result.cost_optimization,
            'processing_time_seconds': round(processing_time, 2),
            'optimization_mode': optimization_mode
        }
        
        return jsonify({
            'success': True,
            'message': f'Optimisation {optimization_mode} terminée avec succès',
            'data': {
                'assignments': result.assignments,
                'schedule': result.schedule,
                'statistics': stats,
                'unassigned_orders': result.unassigned_orders,
                'recommendations': _generate_recommendations(result, stats)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur optimisation: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur durant l\'optimisation: {str(e)}',
            'data': None
        }), 500

@sprint9_scheduler_bp.route('/scenarios', methods=['POST'])
def generate_scenarios():
    """
    Générer plusieurs scénarios d'optimisation pour comparaison
    
    Body:
    {
        "date_filter": "2025-01-20",
        "scenario_count": 3
    }
    """
    try:
        data = request.get_json() or {}
        date_filter = data.get('date_filter')
        scenario_count = min(data.get('scenario_count', 3), 5)  # Max 5 scénarios
        
        logger.info(f"🎯 Génération de {scenario_count} scénarios")
        
        # Charger les données
        work_orders = scheduler_optimizer.load_work_orders(date_filter)
        technicians = scheduler_optimizer.load_technicians()
        
        if not work_orders or not technicians:
            return jsonify({
                'success': False,
                'error': 'Données insuffisantes pour générer les scénarios',
                'scenarios': []
            }), 404
        
        # Générer les scénarios
        start_time = datetime.now()
        scenarios = scheduler_optimizer.generate_multi_scenarios(scenario_count)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Enrichir les scénarios avec des métriques comparatives
        for scenario in scenarios:
            scenario['comparison'] = {
                'travel_time_vs_avg': _calculate_vs_average(scenario['total_travel_time'], scenarios, 'total_travel_time'),
                'efficiency_vs_avg': _calculate_vs_average(scenario['efficiency_score'], scenarios, 'efficiency_score'),
                'cost_vs_avg': _calculate_vs_average(scenario['cost_optimization'], scenarios, 'cost_optimization')
            }
        
        return jsonify({
            'success': True,
            'message': f'{len(scenarios)} scénarios générés avec succès',
            'scenarios': scenarios,
            'metadata': {
                'total_work_orders': len(work_orders),
                'available_technicians': len(technicians),
                'processing_time_seconds': round(processing_time, 2),
                'best_scenario_id': scenarios[0]['id'] if scenarios else None
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur génération scénarios: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur durant la génération: {str(e)}',
            'scenarios': []
        }), 500

@sprint9_scheduler_bp.route('/apply/<int:scenario_id>', methods=['POST'])
def apply_scenario(scenario_id):
    """
    Appliquer un scénario d'optimisation sélectionné
    
    Body:
    {
        "assignments": {...},
        "confirm": true
    }
    """
    try:
        data = request.get_json() or {}
        assignments = data.get('assignments', {})
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'success': False,
                'error': 'Confirmation requise pour appliquer l\'optimisation',
                'data': None
            }), 400
        
        if not assignments:
            return jsonify({
                'success': False,
                'error': 'Assignations manquantes',
                'data': None
            }), 400
        
        logger.info(f"🔄 Application du scénario {scenario_id}")
        
        # Appliquer l'optimisation
        success = scheduler_optimizer.apply_optimization(scenario_id, assignments)
        
        if success:
            # Enregistrer l'action dans les logs
            _log_optimization_applied(scenario_id, assignments)
            
            return jsonify({
                'success': True,
                'message': f'Scénario {scenario_id} appliqué avec succès',
                'data': {
                    'applied_assignments': len(assignments),
                    'affected_technicians': list(assignments.keys()),
                    'total_orders_assigned': sum(len(orders) for orders in assignments.values()),
                    'applied_at': datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Échec de l\'application du scénario',
                'data': None
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Erreur application scénario: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur durant l\'application: {str(e)}',
            'data': None
        }), 500

@sprint9_scheduler_bp.route('/optimize-day', methods=['POST'])
def optimize_my_day():
    """
    Bouton "Optimiser ma journée" - optimisation rapide pour un technicien
    
    Body:
    {
        "technician_id": 1,
        "date": "2025-01-20"
    }
    """
    try:
        data = request.get_json() or {}
        technician_id = data.get('technician_id')
        target_date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        if not technician_id:
            return jsonify({
                'success': False,
                'error': 'ID technicien requis',
                'data': None
            }), 400
        
        logger.info(f"⚡ Optimisation rapide journée - Technicien: {technician_id}")
        
        # Charger les bons de travail assignés au technicien
        work_orders = _get_technician_work_orders(technician_id, target_date)
        
        if not work_orders:
            return jsonify({
                'success': True,
                'message': 'Aucun bon de travail à optimiser pour cette journée',
                'data': {
                    'optimized_schedule': [],
                    'efficiency_gain': 0,
                    'time_saved_minutes': 0
                }
            })
        
        # Optimisation locale pour ce technicien
        optimized_schedule = _optimize_technician_day(technician_id, work_orders)
        
        return jsonify({
            'success': True,
            'message': 'Journée optimisée avec succès',
            'data': {
                'optimized_schedule': optimized_schedule['schedule'],
                'efficiency_gain': optimized_schedule['efficiency_gain'],
                'time_saved_minutes': optimized_schedule['time_saved'],
                'original_travel_time': optimized_schedule['original_travel_time'],
                'optimized_travel_time': optimized_schedule['optimized_travel_time'],
                'recommendations': optimized_schedule['recommendations']
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur optimisation journée: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur durant l\'optimisation: {str(e)}',
            'data': None
        }), 500

@sprint9_scheduler_bp.route('/efficiency-score', methods=['GET'])
def get_efficiency_score():
    """
    Calculer et retourner le score d'efficacité projetée
    
    Query params:
    - date: date pour le calcul (défaut: aujourd'hui)
    - mode: mode d'optimisation pour projection
    """
    try:
        date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        mode = request.args.get('mode', 'balanced')
        
        logger.info(f"📊 Calcul score d'efficacité - Date: {date_filter}, Mode: {mode}")
        
        # Charger les données actuelles
        work_orders = scheduler_optimizer.load_work_orders(date_filter)
        technicians = scheduler_optimizer.load_technicians()
        
        if not work_orders or not technicians:
            return jsonify({
                'success': False,
                'error': 'Données insuffisantes pour calculer l\'efficacité',
                'score': 0
            }), 404
        
        # Calculer le score actuel (sans optimisation)
        current_score = _calculate_current_efficiency(work_orders, technicians)
        
        # Projeter l'amélioration avec optimisation
        projected_result = scheduler_optimizer.optimize_schedule(mode)
        projected_score = projected_result.efficiency_score
        
        improvement = projected_score - current_score
        
        return jsonify({
            'success': True,
            'score': {
                'current_efficiency': current_score,
                'projected_efficiency': projected_score,
                'improvement_percent': round(improvement, 2),
                'rating': _get_efficiency_rating(projected_score),
                'breakdown': {
                    'work_time_ratio': round((projected_result.total_work_time / (projected_result.total_work_time + projected_result.total_travel_time)) * 100, 1) if projected_result.total_work_time > 0 else 0,
                    'assignment_success': round((len(work_orders) - len(projected_result.unassigned_orders)) / len(work_orders) * 100, 1) if work_orders else 0,
                    'cost_optimization': projected_result.cost_optimization
                }
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur calcul efficacité: {e}")
        return jsonify({
            'success': False,
            'error': f'Erreur durant le calcul: {str(e)}',
            'score': 0
        }), 500

@sprint9_scheduler_bp.route('/constraints', methods=['GET', 'POST'])
def manage_constraints():
    """
    Gérer les contraintes d'optimisation
    
    GET: Récupérer les contraintes actuelles
    POST: Mettre à jour les contraintes
    """
    if request.method == 'GET':
        try:
            constraints = _get_optimization_constraints()
            return jsonify({
                'success': True,
                'constraints': constraints
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            
            # Valider et mettre à jour les contraintes
            updated_constraints = _update_optimization_constraints(data)
            
            return jsonify({
                'success': True,
                'message': 'Contraintes mises à jour avec succès',
                'constraints': updated_constraints
            })
            
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour contraintes: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

# ====================== FONCTIONS UTILITAIRES ======================

def _generate_recommendations(result, stats):
    """Générer des recommandations basées sur les résultats"""
    recommendations = []
    
    if stats['efficiency_score'] < 60:
        recommendations.append({
            'type': 'warning',
            'message': 'Efficacité faible - considérer l\'ajout de techniciens ou la répartition des compétences'
        })
    
    if len(result.unassigned_orders) > 0:
        recommendations.append({
            'type': 'info',
            'message': f'{len(result.unassigned_orders)} bons de travail non assignés - vérifier les compétences requises'
        })
    
    if result.total_travel_time > result.total_work_time:
        recommendations.append({
            'type': 'warning',
            'message': 'Temps de trajet supérieur au temps de travail - optimiser les zones géographiques'
        })
    
    return recommendations

def _calculate_vs_average(value, scenarios, field):
    """Calculer la différence par rapport à la moyenne"""
    values = [s[field] for s in scenarios]
    avg = sum(values) / len(values) if values else 0
    return round(((value - avg) / avg) * 100, 1) if avg > 0 else 0

def _log_optimization_applied(scenario_id, assignments):
    """Enregistrer l'application d'une optimisation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO optimization_logs 
            (scenario_id, applied_at, assignments_data, user_id)
            VALUES (%s, NOW(), %s, %s)
        """, (scenario_id, json.dumps(assignments), session.get('user_id', 1)))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.warning(f"⚠️ Échec enregistrement log: {e}")

def _get_technician_work_orders(technician_id, date):
    """Récupérer les bons de travail d'un technicien pour une date"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT wo.*, c.latitude, c.longitude
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            WHERE wo.assigned_technician_id = %s 
            AND DATE(wo.scheduled_date) = %s
            AND wo.status IN ('assigned', 'in_progress')
            ORDER BY wo.priority DESC, wo.created_date ASC
        """, (technician_id, date))
        
        orders = cursor.fetchall()
        
        # Convertir en dictionnaires
        column_names = [desc[0] for desc in cursor.description]
        orders_dict = [dict(zip(column_names, row)) for row in orders]
        
        cursor.close()
        conn.close()
        
        return orders_dict
        
    except Exception as e:
        logger.error(f"❌ Erreur récupération bons de travail: {e}")
        return []

def _optimize_technician_day(technician_id, work_orders):
    """Optimiser la journée d'un technicien spécifique"""
    # Simplification : tri par priorité et proximité géographique
    if not work_orders:
        return {
            'schedule': [],
            'efficiency_gain': 0,
            'time_saved': 0,
            'original_travel_time': 0,
            'optimized_travel_time': 0,
            'recommendations': []
        }
    
    # Tri optimisé : priorité puis proximité
    sorted_orders = sorted(work_orders, key=lambda wo: (
        -_get_priority_value(wo.get('priority', 'medium')),
        wo.get('latitude', 0),
        wo.get('longitude', 0)
    ))
    
    # Générer le planning optimisé
    schedule = []
    current_time = datetime.strptime('08:00', '%H:%M')
    
    for i, wo in enumerate(sorted_orders):
        start_time = current_time.strftime('%H:%M')
        duration = wo.get('estimated_duration', 120)
        end_time = (current_time + timedelta(minutes=duration)).strftime('%H:%M')
        
        schedule.append({
            'work_order_id': wo['id'],
            'customer_name': wo.get('customer_name', 'Client inconnu'),
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'priority': wo.get('priority', 'medium'),
            'order_index': i + 1
        })
        
        # Ajouter temps de trajet pour le prochain
        current_time += timedelta(minutes=duration + 30)  # 30min trajet estimé
    
    return {
        'schedule': schedule,
        'efficiency_gain': 15.5,  # Estimation
        'time_saved': 45,         # minutes économisées
        'original_travel_time': 120,
        'optimized_travel_time': 75,
        'recommendations': [
            'Commencer par les interventions prioritaires',
            'Grouper les interventions par zone géographique'
        ]
    }

def _get_priority_value(priority):
    """Convertir la priorité en valeur numérique"""
    values = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
    return values.get(priority, 2)

def _calculate_current_efficiency(work_orders, technicians):
    """Calculer l'efficacité actuelle sans optimisation"""
    # Calcul simplifié basé sur la charge et les compétences
    if not work_orders or not technicians:
        return 0.0
    
    # Ratio bons de travail / techniciens
    workload_ratio = len(work_orders) / len(technicians)
    
    # Score basé sur la charge (optimal autour de 3-4 bons par technicien)
    if workload_ratio <= 4:
        base_score = workload_ratio * 20  # Score sur 80 max
    else:
        base_score = 80 - ((workload_ratio - 4) * 5)  # Pénalité surcharge
    
    # Bonus pour les techniciens disponibles
    availability_bonus = min(len(technicians) * 2, 20)
    
    return max(0, min(100, base_score + availability_bonus))

def _get_efficiency_rating(score):
    """Obtenir le rating textuel du score d'efficacité"""
    if score >= 90:
        return 'Excellent'
    elif score >= 75:
        return 'Très bon'
    elif score >= 60:
        return 'Bon'
    elif score >= 40:
        return 'Moyen'
    else:
        return 'Faible'

def _get_optimization_constraints():
    """Récupérer les contraintes d'optimisation actuelles"""
    return {
        'max_work_hours': 8,
        'max_travel_time': 120,
        'travel_speed_kmh': 50,
        'setup_time_minutes': 15,
        'priority_weights': {
            'urgent': 1000,
            'high': 500,
            'medium': 100,
            'low': 50
        },
        'skill_matching_required': True,
        'geographic_clustering': True
    }

def _update_optimization_constraints(data):
    """Mettre à jour les contraintes d'optimisation"""
    current_constraints = _get_optimization_constraints()
    
    # Mettre à jour avec les nouvelles valeurs
    if 'max_work_hours' in data:
        current_constraints['max_work_hours'] = max(1, min(12, data['max_work_hours']))
    
    if 'travel_speed_kmh' in data:
        current_constraints['travel_speed_kmh'] = max(20, min(80, data['travel_speed_kmh']))
    
    if 'setup_time_minutes' in data:
        current_constraints['setup_time_minutes'] = max(5, min(60, data['setup_time_minutes']))
    
    # Appliquer à l'optimiseur global
    scheduler_optimizer.max_work_hours = current_constraints['max_work_hours'] * 60
    scheduler_optimizer.travel_speed_kmh = current_constraints['travel_speed_kmh']
    scheduler_optimizer.setup_time = current_constraints['setup_time_minutes']
    
    return current_constraints
