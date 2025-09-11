"""
ChronoTech AI Copilot - Assistant Intelligent
Module d'analyse et de suggestions automatiques
"""
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Any
from core.database import get_db_connection

logger = logging.getLogger(__name__)

class CopilotAI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.insights_cache = {}
        self.cache_duration = 300  # 5 minutes
        
    def analyze_task_delay(self, task_data: Dict) -> List[Dict]:
        """Analyse les retards et leurs causes potentielles"""
        factors = []
        
        estimated_time = task_data.get('estimated_duration', 0)
        actual_time = task_data.get('actual_duration', 0)
        scheduled_date = task_data.get('scheduled_date')
        completion_date = task_data.get('completion_date')
        
        # Analyser la durée
        if actual_time and estimated_time:
            if actual_time > estimated_time * 1.5:
                factors.append({
                    'type': 'duration_overrun',
                    'severity': 'high',
                    'message': f"Dépassement significatif: {actual_time}min vs {estimated_time}min estimé",
                    'suggestion': "Revoir l'estimation pour des tâches similaires"
                })
            elif actual_time > estimated_time * 1.2:
                factors.append({
                    'type': 'duration_overrun',
                    'severity': 'medium',
                    'message': f"Léger dépassement: {actual_time}min vs {estimated_time}min estimé",
                    'suggestion': "Ajuster les estimations futures"
                })
        
        # Analyser les délais
        if scheduled_date and completion_date:
            delay_hours = (completion_date - scheduled_date).total_seconds() / 3600
            if delay_hours > 24:
                factors.append({
                    'type': 'schedule_delay',
                    'severity': 'high',
                    'message': f"Retard de {int(delay_hours)}h sur la planification",
                    'suggestion': "Vérifier la charge de travail du technicien"
                })
        
        return factors
    
    def detect_workload_anomalies(self, date_from=None, date_to=None) -> List[Dict]:
        """Détecte les anomalies de charge de travail"""
        if not date_from:
            date_from = datetime.now().replace(hour=0, minute=0, second=0)
        if not date_to:
            date_to = date_from + timedelta(days=1)
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Analyser la charge par technicien
        cursor.execute("""
            SELECT 
                u.id, u.name,
                COUNT(wo.id) as task_count,
                SUM(COALESCE(wo.estimated_duration, 60)) as total_minutes,
                AVG(COALESCE(wo.estimated_duration, 60)) as avg_duration
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id
                AND DATE(wo.scheduled_date) BETWEEN %s AND %s
                AND wo.status NOT IN ('completed', 'cancelled')
            WHERE u.role = 'technician'
            GROUP BY u.id, u.name
        """, (date_from.date(), date_to.date()))
        
        technicians = cursor.fetchall()
        anomalies = []
        
        for tech in technicians:
            total_hours = (tech['total_minutes'] or 0) / 60
            
            # Surcharge détectée
            if total_hours > 10:
                anomalies.append({
                    'type': 'overload',
                    'severity': 'critical',
                    'technician_id': tech['id'],
                    'technician_name': tech['name'],
                    'message': f"{tech['name']} a {total_hours:.1f}h de travail planifié",
                    'suggestion': "Redistribuer certaines tâches",
                    'action': 'reassign_tasks'
                })
            elif total_hours > 8:
                anomalies.append({
                    'type': 'high_load',
                    'severity': 'warning',
                    'technician_id': tech['id'],
                    'technician_name': tech['name'],
                    'message': f"{tech['name']} approche la limite avec {total_hours:.1f}h",
                    'suggestion': "Surveiller et éviter d'ajouter des tâches"
                })
            
            # Sous-utilisation
            elif total_hours < 2 and tech['task_count'] > 0:
                anomalies.append({
                    'type': 'underload',
                    'severity': 'info',
                    'technician_id': tech['id'],
                    'technician_name': tech['name'],
                    'message': f"{tech['name']} n'a que {total_hours:.1f}h de travail",
                    'suggestion': "Peut prendre des tâches supplémentaires",
                    'action': 'assign_more_tasks'
                })
        
        conn.close()
        return anomalies
    
    def get_dashboard_insights(self, user_role='admin') -> Dict:
        """Génère les insights pour le dashboard"""
        cache_key = f"insights_{user_role}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        # Vérifier le cache
        if cache_key in self.insights_cache:
            cache_time = self.insights_cache[cache_key]['timestamp']
            if (datetime.now() - cache_time).seconds < self.cache_duration:
                return self.insights_cache[cache_key]['data']
        
        insights = {
            'workload_anomalies': self.detect_workload_anomalies(),
            'recommendations': [],
            'alerts': []
        }
        
        # Générer des recommandations basées sur les anomalies
        for anomaly in insights['workload_anomalies']:
            if anomaly['type'] == 'overload':
                insights['recommendations'].append({
                    'type': 'redistribute',
                    'priority': 'high',
                    'message': f"Redistribuer les tâches de {anomaly['technician_name']}",
                    'technician_id': anomaly['technician_id']
                })
            elif anomaly['type'] == 'underload':
                insights['recommendations'].append({
                    'type': 'assign_more',
                    'priority': 'medium',
                    'message': f"Assigner plus de tâches à {anomaly['technician_name']}",
                    'technician_id': anomaly['technician_id']
                })
        
        # Mettre en cache
        self.insights_cache[cache_key] = {
            'timestamp': datetime.now(),
            'data': insights
        }
        
        return insights
    
    def suggest_reassignment(self, overloaded_tech_id: int) -> List[Dict]:
        """Suggère des réassignations pour un technicien surchargé"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les tâches du technicien surchargé
        cursor.execute("""
            SELECT wo.*, c.name as customer_name
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            WHERE wo.assigned_technician_id = %s
            AND wo.status NOT IN ('completed', 'cancelled')
            AND DATE(wo.scheduled_date) = CURDATE()
            ORDER BY wo.priority ASC, wo.scheduled_date ASC
        """, (overloaded_tech_id,))
        
        tasks_to_reassign = cursor.fetchall()
        
        # Trouver des techniciens disponibles
        cursor.execute("""
            SELECT 
                u.id, u.name,
                SUM(COALESCE(wo.estimated_duration, 60)) as current_load
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id
                AND DATE(wo.scheduled_date) = CURDATE()
                AND wo.status NOT IN ('completed', 'cancelled')
            WHERE u.role = 'technician'
            AND u.id != %s
            GROUP BY u.id, u.name
            HAVING current_load < 360
            ORDER BY current_load ASC
        """, (overloaded_tech_id,))
        
        available_techs = cursor.fetchall()
        
        suggestions = []
        
        for task in tasks_to_reassign[-2:]:  # Les 2 dernières tâches (moindre priorité)
            if available_techs:
                best_tech = available_techs[0]
                suggestions.append({
                    'task_id': task['id'],
                    'task_name': f"#{task['claim_number']} - {task['customer_name']}",
                    'current_tech_id': overloaded_tech_id,
                    'suggested_tech_id': best_tech['id'],
                    'suggested_tech_name': best_tech['name'],
                    'reason': f"Réduire la charge de travail ({best_tech['current_load']}min actuellement)"
                })
        
        conn.close()
        return suggestions
    
    def suggest_best_technician(self, task_data: Dict) -> Dict:
        """Suggère le meilleur technicien pour une tâche"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Récupérer les techniciens disponibles avec leur charge de travail
            cursor.execute("""
                SELECT 
                    u.id, u.name, u.email,
                    COUNT(wo.id) as current_workload,
                    AVG(COALESCE(wo.estimated_duration, 120)) as avg_duration
                FROM users u
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                    AND wo.status IN ('assigned', 'in_progress')
                WHERE u.role = 'technician' AND u.is_active = 1
                GROUP BY u.id, u.name, u.email
                ORDER BY current_workload ASC
            """)
            
            technicians = cursor.fetchall()
            conn.close()
            
            if not technicians:
                return {
                    'suggested_technician_id': None,
                    'suggested_technician_name': None,
                    'reason': 'Aucun technicien disponible'
                }
            
            # Choisir le technicien avec la plus faible charge
            best_tech = technicians[0]
            
            return {
                'suggested_technician_id': best_tech['id'],
                'suggested_technician_name': best_tech['name'],
                'reason': f"Charge de travail optimale ({best_tech['current_workload']} tâches actives)"
            }
            
        except Exception as e:
            logger.error(f"Erreur suggestion meilleur technicien: {e}")
            return {
                'suggested_technician_id': None,
                'suggested_technician_name': None,
                'reason': 'Erreur lors de la suggestion'
            }

# Instance globale
copilot_ai = CopilotAI()
