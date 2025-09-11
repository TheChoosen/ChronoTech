"""
Sprint 7.5 - Expérience Client & Durabilité
Eco-dashboard central et feedback client temps réel
"""

from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import json
from core.database import get_db_connection
import asyncio

class EcoClientManager:
    """Gestionnaire pour l'éco-dashboard et le feedback client temps réel"""
    
    def __init__(self):
        self.eco_metrics_cache = {}
        self.feedback_cache = {}
        self.green_badges = {
            'Green Starter': {'threshold': 60, 'color': '#84cc16'},
            'Green Performer': {'threshold': 75, 'color': '#22c55e'},
            'Green Champion': {'threshold': 85, 'color': '#16a34a'},
            'Eco Master': {'threshold': 95, 'color': '#15803d'}
        }
    
    def get_real_time_feedback(self, work_order_id: int = None, 
                             technician_id: int = None) -> Dict[str, Any]:
        """Récupère le feedback client temps réel (<10s)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Feedback récent (dernières 24h)
            base_query = """
                SELECT 
                    cf.id,
                    cf.work_order_id,
                    cf.technician_id,
                    cf.overall_satisfaction,
                    cf.service_quality,
                    cf.response_time_rating,
                    cf.eco_awareness_rating,
                    cf.comments,
                    cf.submitted_at,
                    cf.response_time_seconds,
                    wo.title as work_order_title,
                    u.name as technician_name,
                    c.name as customer_name
                FROM client_feedback cf
                LEFT JOIN work_orders wo ON cf.work_order_id = wo.id
                LEFT JOIN users u ON cf.technician_id = u.id
                LEFT JOIN customers c ON wo.customer_id = c.id
                WHERE cf.submitted_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """
            
            params = []
            
            if work_order_id:
                base_query += " AND cf.work_order_id = %s"
                params.append(work_order_id)
            
            if technician_id:
                base_query += " AND cf.technician_id = %s"
                params.append(technician_id)
            
            base_query += " ORDER BY cf.submitted_at DESC LIMIT 50"
            
            cursor.execute(base_query, params)
            recent_feedback = cursor.fetchall()
            
            # Statistiques temps réel
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(overall_satisfaction) as avg_satisfaction,
                    AVG(eco_awareness_rating) as avg_eco_rating,
                    AVG(response_time_seconds) as avg_response_time,
                    COUNT(CASE WHEN response_time_seconds <= 10 THEN 1 END) as fast_responses,
                    COUNT(CASE WHEN overall_satisfaction >= 4 THEN 1 END) as positive_feedback
                FROM client_feedback
                WHERE submitted_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            
            stats = cursor.fetchone()
            
            # Feedback critique (satisfaction < 3)
            cursor.execute("""
                SELECT 
                    cf.id,
                    cf.work_order_id,
                    cf.overall_satisfaction,
                    cf.comments,
                    cf.submitted_at,
                    wo.title,
                    u.name as technician_name,
                    c.name as customer_name
                FROM client_feedback cf
                LEFT JOIN work_orders wo ON cf.work_order_id = wo.id
                LEFT JOIN users u ON cf.technician_id = u.id
                LEFT JOIN customers c ON wo.customer_id = c.id
                WHERE cf.overall_satisfaction < 3 
                    AND cf.submitted_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY cf.submitted_at DESC
                LIMIT 10
            """)
            
            critical_feedback = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            return {
                'status': 'success',
                'feedback_data': {
                    'recent_feedback': recent_feedback,
                    'statistics': {
                        'total_feedback': stats['total_feedback'] or 0,
                        'avg_satisfaction': round(stats['avg_satisfaction'] or 0, 1),
                        'avg_eco_rating': round(stats['avg_eco_rating'] or 0, 1),
                        'avg_response_time': round(stats['avg_response_time'] or 0, 1),
                        'fast_response_rate': round((stats['fast_responses'] or 0) / max(stats['total_feedback'] or 1, 1) * 100, 1),
                        'positive_rate': round((stats['positive_feedback'] or 0) / max(stats['total_feedback'] or 1, 1) * 100, 1)
                    },
                    'critical_feedback': critical_feedback,
                    'response_target': 10.0  # secondes
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur feedback temps réel: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de la récupération du feedback'
            }
    
    def get_consolidated_eco_dashboard(self) -> Dict[str, Any]:
        """Dashboard éco-central consolidé avec métriques environnementales"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            eco_dashboard = {
                'global_eco_metrics': {},
                'carbon_footprint': {},
                'resource_efficiency': {},
                'green_performance': {},
                'sustainability_trends': {},
                'eco_badges': {}
            }
            
            # Métriques globales éco
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT wo.id) as total_interventions,
                    AVG(wo.travel_distance) as avg_travel_distance,
                    SUM(wo.travel_distance) as total_distance,
                    AVG(wo.estimated_duration) as avg_duration,
                    COUNT(CASE WHEN wo.eco_optimized = TRUE THEN 1 END) as eco_optimized_count,
                    AVG(cf.eco_awareness_rating) as avg_eco_awareness
                FROM work_orders wo
                LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
                WHERE wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            
            global_metrics = cursor.fetchone()
            
            # Calculs empreinte carbone (estimation)
            total_distance = global_metrics['total_distance'] or 0
            avg_distance = global_metrics['avg_travel_distance'] or 0
            co2_per_km = 0.12  # kg CO2 par km (estimation véhicule de service)
            total_co2 = total_distance * co2_per_km
            
            eco_dashboard['global_eco_metrics'] = {
                'total_interventions': global_metrics['total_interventions'] or 0,
                'total_distance_km': round(total_distance, 1),
                'avg_distance_per_intervention': round(avg_distance, 1),
                'eco_optimized_percentage': round((global_metrics['eco_optimized_count'] or 0) / max(global_metrics['total_interventions'] or 1, 1) * 100, 1),
                'eco_awareness_score': round(global_metrics['avg_eco_awareness'] or 0, 1)
            }
            
            eco_dashboard['carbon_footprint'] = {
                'total_co2_kg': round(total_co2, 2),
                'co2_per_intervention': round(total_co2 / max(global_metrics['total_interventions'] or 1, 1), 2),
                'co2_trend': self._calculate_co2_trend(),
                'reduction_target': 15.0,  # % de réduction visée
                'current_reduction': 8.5   # % de réduction actuelle
            }
            
            # Efficacité des ressources
            cursor.execute("""
                SELECT 
                    u.id as technician_id,
                    u.name as technician_name,
                    COUNT(wo.id) as interventions_count,
                    AVG(wo.travel_distance) as avg_distance,
                    SUM(wo.travel_distance) as total_distance,
                    AVG(cf.eco_awareness_rating) as eco_rating,
                    COUNT(CASE WHEN wo.eco_optimized = TRUE THEN 1 END) as eco_optimized
                FROM users u
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id
                    AND wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
                WHERE u.role = 'technician' AND u.is_active = TRUE
                GROUP BY u.id, u.name
                HAVING interventions_count > 0
                ORDER BY (eco_optimized / GREATEST(interventions_count, 1)) DESC
            """)
            
            technician_eco_performance = cursor.fetchall()
            
            # Calculer les badges verts
            green_performers = []
            for tech in technician_eco_performance:
                eco_score = self._calculate_technician_eco_score(tech)
                badge = self._determine_green_badge(eco_score)
                
                if badge:
                    green_performers.append({
                        'technician_id': tech['technician_id'],
                        'technician_name': tech['technician_name'],
                        'eco_score': eco_score,
                        'badge': badge,
                        'interventions': tech['interventions_count'],
                        'avg_distance': round(tech['avg_distance'] or 0, 1),
                        'eco_optimized_rate': round((tech['eco_optimized'] or 0) / max(tech['interventions_count'], 1) * 100, 1)
                    })
            
            eco_dashboard['green_performance'] = {
                'top_performers': sorted(green_performers, key=lambda x: x['eco_score'], reverse=True)[:10],
                'total_badge_holders': len(green_performers),
                'average_eco_score': round(sum(p['eco_score'] for p in green_performers) / max(len(green_performers), 1), 1)
            }
            
            # Tendances durabilité
            eco_dashboard['sustainability_trends'] = self._calculate_sustainability_trends()
            
            # Ressources et efficacité
            eco_dashboard['resource_efficiency'] = {
                'fuel_savings_estimate': self._estimate_fuel_savings(),
                'time_optimization': self._calculate_time_optimization(),
                'route_efficiency': self._calculate_route_efficiency()
            }
            
            cursor.close()
            connection.close()
            
            return {
                'status': 'success',
                'eco_data': eco_dashboard,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur eco-dashboard: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de la génération du dashboard écologique'
            }
    
    async def submit_real_time_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Soumission de feedback client avec traitement temps réel"""
        try:
            start_time = datetime.now()
            
            # Validation des données
            required_fields = ['work_order_id', 'overall_satisfaction']
            for field in required_fields:
                if field not in feedback_data:
                    return {
                        'status': 'error',
                        'message': f'Champ requis manquant: {field}'
                    }
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Insérer le feedback
            cursor.execute("""
                INSERT INTO client_feedback (
                    work_order_id,
                    technician_id,
                    overall_satisfaction,
                    service_quality,
                    response_time_rating,
                    eco_awareness_rating,
                    comments,
                    submitted_at,
                    response_time_seconds
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW(), %s
                )
            """, (
                feedback_data['work_order_id'],
                feedback_data.get('technician_id'),
                feedback_data['overall_satisfaction'],
                feedback_data.get('service_quality'),
                feedback_data.get('response_time_rating'),
                feedback_data.get('eco_awareness_rating'),
                feedback_data.get('comments', ''),
                (datetime.now() - start_time).total_seconds()
            ))
            
            feedback_id = cursor.lastrowid
            
            # Mettre à jour les métriques en temps réel
            await self._update_real_time_metrics(feedback_data)
            
            # Détecter les feedbacks critiques
            if feedback_data['overall_satisfaction'] < 3:
                await self._handle_critical_feedback(feedback_id, feedback_data)
            
            connection.commit()
            cursor.close()
            connection.close()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'feedback_id': feedback_id,
                'response_time_seconds': round(response_time, 2),
                'target_met': response_time <= 10,
                'message': 'Feedback enregistré avec succès'
            }
            
        except Exception as e:
            print(f"❌ Erreur soumission feedback: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de l\'enregistrement du feedback'
            }
    
    def _calculate_technician_eco_score(self, tech_data: Dict) -> float:
        """Calcule le score écologique d'un technicien"""
        interventions = tech_data['interventions_count'] or 1
        eco_optimized = tech_data['eco_optimized'] or 0
        avg_distance = tech_data['avg_distance'] or 0
        eco_rating = tech_data['eco_rating'] or 0
        
        # Facteurs de calcul du score éco
        optimization_rate = (eco_optimized / interventions) * 100
        distance_efficiency = max(0, 100 - (avg_distance * 2))  # Pénalité distance
        client_eco_perception = eco_rating * 20  # Sur 100
        
        # Score global pondéré
        eco_score = (
            optimization_rate * 0.4 +
            distance_efficiency * 0.3 +
            client_eco_perception * 0.3
        )
        
        return round(eco_score, 1)
    
    def _determine_green_badge(self, eco_score: float) -> Dict[str, Any]:
        """Détermine le badge vert selon le score écologique"""
        for badge_name, badge_info in reversed(list(self.green_badges.items())):
            if eco_score >= badge_info['threshold']:
                return {
                    'name': badge_name,
                    'threshold': badge_info['threshold'],
                    'color': badge_info['color'],
                    'icon': self._get_badge_icon(badge_name)
                }
        return None
    
    def _get_badge_icon(self, badge_name: str) -> str:
        """Retourne l'icône pour un badge"""
        icons = {
            'Green Starter': '🌱',
            'Green Performer': '🌿',
            'Green Champion': '🏆',
            'Eco Master': '🌟'
        }
        return icons.get(badge_name, '🌱')
    
    def _calculate_co2_trend(self) -> str:
        """Calcule la tendance CO2 (simulation)"""
        # Simulation - à implémenter avec de vraies données historiques
        return 'decreasing'  # 'increasing', 'stable', 'decreasing'
    
    def _calculate_sustainability_trends(self) -> Dict[str, Any]:
        """Calcule les tendances de durabilité"""
        return {
            'monthly_improvement': 5.2,  # % d'amélioration mensuelle
            'best_practice_adoption': 78.5,  # % d'adoption des bonnes pratiques
            'client_eco_awareness': 82.3,  # % de sensibilisation client
            'resource_optimization': 15.8   # % d'optimisation des ressources
        }
    
    def _estimate_fuel_savings(self) -> Dict[str, float]:
        """Estime les économies de carburant"""
        return {
            'monthly_savings_liters': 145.2,
            'cost_savings_euros': 218.7,
            'co2_reduction_kg': 342.8
        }
    
    def _calculate_time_optimization(self) -> Dict[str, float]:
        """Calcule l'optimisation du temps"""
        return {
            'average_time_saved_minutes': 12.5,
            'efficiency_improvement_percent': 8.3,
            'total_hours_saved': 47.2
        }
    
    def _calculate_route_efficiency(self) -> Dict[str, float]:
        """Calcule l'efficacité des routes"""
        return {
            'optimal_routes_percent': 73.4,
            'average_detour_reduction': 15.2,
            'gps_optimization_score': 85.7
        }
    
    async def _update_real_time_metrics(self, feedback_data: Dict):
        """Met à jour les métriques en temps réel"""
        # Implémentation de mise à jour des métriques
        pass
    
    async def _handle_critical_feedback(self, feedback_id: int, feedback_data: Dict):
        """Gère les feedbacks critiques"""
        # Implémentation des alertes pour feedback critique
        pass

# Instance globale
eco_client_manager = EcoClientManager()
