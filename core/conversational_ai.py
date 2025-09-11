"""
Sprint 7.2 - IA Conversationnelle
Copilote IA Chatbot pour superviseurs et managers
Permet de poser des questions directes et recevoir des réponses exploitables
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re
from core.database import get_db_connection

class ConversationalAI:
    """Moteur d'IA conversationnelle pour ChronoTech"""
    
    def __init__(self):
        self.context_memory = {}
        self.user_sessions = {}
        self.response_cache = {}
        
        # Patterns de questions supportés
        self.question_patterns = {
            'availability': [
                r'quels?\s+techniciens?\s+(?:sont\s+)?disponibles?\s*(?:cet?\s+)?(?:après-midi|demain|aujourd\'hui)?',
                r'qui\s+(?:est\s+)?libre\s*(?:cet?\s+)?(?:après-midi|demain|aujourd\'hui)?',
                r'disponibilité\s+(?:des\s+)?techniciens?'
            ],
            'workload': [
                r'combien\s+(?:de\s+)?(?:tâches?|interventions?|bons?)\s+(?:pour\s+)?(.+)',
                r'charge\s+(?:de\s+travail\s+)?(?:de\s+)?(.+)',
                r'planning\s+(?:de\s+)?(.+)'
            ],
            'performance': [
                r'performance\s+(?:de\s+)?(.+)',
                r'statistiques?\s+(?:de\s+)?(.+)',
                r'résultats?\s+(?:de\s+)?(.+)'
            ],
            'urgent': [
                r'(?:quelles?\s+)?(?:tâches?|interventions?)\s+urgentes?',
                r'priorités?\s+(?:du\s+jour|aujourd\'hui)',
                r'problèmes?\s+critiques?'
            ],
            'customer': [
                r'(?:satisfaction\s+)?client\s+(.+)',
                r'feedback\s+(?:du\s+)?client\s+(.+)',
                r'avis\s+client\s+(.+)'
            ],
            'eco_score': [
                r'éco-score\s+(?:de\s+)?(.+)',
                r'impact\s+environnemental\s+(?:de\s+)?(.+)',
                r'durabilité\s+(?:de\s+)?(.+)'
            ]
        }
        
        # Réponses templates
        self.response_templates = {
            'no_data': "Je n'ai pas trouvé de données pour cette demande.",
            'error': "Désolé, une erreur s'est produite lors du traitement de votre demande.",
            'clarification': "Pouvez-vous préciser votre demande ?",
            'processing': "Je traite votre demande..."
        }
    
    async def process_question(self, question: str, user_id: int, context: Dict = None) -> Dict[str, Any]:
        """Traite une question et retourne une réponse structurée"""
        try:
            # Nettoyer et normaliser la question
            cleaned_question = self._clean_question(question)
            
            # Identifier le type de question
            question_type, extracted_params = self._classify_question(cleaned_question)
            
            # Générer la réponse
            response = await self._generate_response(question_type, extracted_params, user_id, context)
            
            # Sauvegarder dans l'historique
            self._save_to_history(user_id, question, response)
            
            return {
                'status': 'success',
                'response': response,
                'question_type': question_type,
                'processing_time': response.get('processing_time', 0),
                'suggestions': self._get_follow_up_suggestions(question_type)
            }
            
        except Exception as e:
            print(f"❌ Erreur traitement question IA: {e}")
            return {
                'status': 'error',
                'response': {
                    'text': self.response_templates['error'],
                    'data': None,
                    'charts': []
                },
                'processing_time': 0
            }
    
    def _clean_question(self, question: str) -> str:
        """Nettoie et normalise la question"""
        # Minuscules
        question = question.lower().strip()
        
        # Supprimer la ponctuation excessive
        question = re.sub(r'[?!]{2,}', '?', question)
        
        # Normaliser les espaces
        question = re.sub(r'\s+', ' ', question)
        
        return question
    
    def _classify_question(self, question: str) -> tuple:
        """Classifie le type de question et extrait les paramètres"""
        for question_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, question)
                if match:
                    params = match.groups() if match.groups() else []
                    return question_type, params
        
        return 'unknown', []
    
    async def _generate_response(self, question_type: str, params: List[str], user_id: int, context: Dict) -> Dict[str, Any]:
        """Génère une réponse basée sur le type de question"""
        start_time = datetime.now()
        
        try:
            if question_type == 'availability':
                response = await self._handle_availability_question(params, context)
            elif question_type == 'workload':
                response = await self._handle_workload_question(params, context)
            elif question_type == 'performance':
                response = await self._handle_performance_question(params, context)
            elif question_type == 'urgent':
                response = await self._handle_urgent_question(params, context)
            elif question_type == 'customer':
                response = await self._handle_customer_question(params, context)
            elif question_type == 'eco_score':
                response = await self._handle_eco_score_question(params, context)
            else:
                response = await self._handle_unknown_question(params, context)
            
            # Calculer le temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            response['processing_time'] = round(processing_time, 2)
            
            return response
            
        except Exception as e:
            print(f"❌ Erreur génération réponse: {e}")
            return {
                'text': self.response_templates['error'],
                'data': None,
                'charts': [],
                'processing_time': 0
            }
    
    async def _handle_availability_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions sur la disponibilité des techniciens"""
        try:
            # Déterminer la période
            period = self._extract_time_period(params)
            
            # Requête base de données
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
            SELECT 
                u.id,
                u.name,
                u.department,
                COUNT(wo.id) as current_tasks,
                CASE 
                    WHEN COUNT(wo.id) = 0 THEN 'Disponible'
                    WHEN COUNT(wo.id) <= 2 THEN 'Peu occupé'
                    WHEN COUNT(wo.id) <= 4 THEN 'Occupé'
                    ELSE 'Surchargé'
                END as availability_status
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                AND wo.status IN ('assigned', 'in_progress')
            WHERE u.role = 'technician' AND u.is_active = TRUE
            GROUP BY u.id, u.name, u.department
            ORDER BY current_tasks ASC, u.name ASC
            """
            
            cursor.execute(query)
            technicians = cursor.fetchall()
            
            # Filtrer par disponibilité
            available_technicians = [t for t in technicians if t['availability_status'] in ['Disponible', 'Peu occupé']]
            
            # Générer la réponse
            if available_technicians:
                response_text = f"Voici les {len(available_technicians)} techniciens disponibles {period}:\n\n"
                
                for tech in available_technicians[:5]:  # Limiter à 5
                    response_text += f"• **{tech['name']}** ({tech['department']}) - {tech['availability_status']}"
                    if tech['current_tasks'] > 0:
                        response_text += f" ({tech['current_tasks']} tâche{'s' if tech['current_tasks'] > 1 else ''})"
                    response_text += "\n"
                
                if len(available_technicians) > 5:
                    response_text += f"\n... et {len(available_technicians) - 5} autres techniciens disponibles."
            else:
                response_text = f"Aucun technicien n'est actuellement disponible {period}. Tous les techniciens sont occupés."
            
            cursor.close()
            connection.close()
            
            return {
                'text': response_text,
                'data': {
                    'available_count': len(available_technicians),
                    'total_count': len(technicians),
                    'technicians': available_technicians
                },
                'charts': [
                    {
                        'type': 'doughnut',
                        'title': 'Disponibilité des techniciens',
                        'data': self._generate_availability_chart_data(technicians)
                    }
                ]
            }
            
        except Exception as e:
            print(f"❌ Erreur requête disponibilité: {e}")
            return {
                'text': self.response_templates['no_data'],
                'data': None,
                'charts': []
            }
    
    async def _handle_workload_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions sur la charge de travail"""
        try:
            technician_name = params[0] if params else None
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if technician_name:
                # Recherche par nom de technicien
                query = """
                SELECT 
                    u.name,
                    COUNT(wo.id) as total_tasks,
                    COUNT(CASE WHEN wo.status = 'assigned' THEN 1 END) as assigned_tasks,
                    COUNT(CASE WHEN wo.status = 'in_progress' THEN 1 END) as in_progress_tasks,
                    COUNT(CASE WHEN wo.priority = 'urgent' THEN 1 END) as urgent_tasks
                FROM users u
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id
                WHERE u.name LIKE %s AND u.role = 'technician' AND u.is_active = TRUE
                GROUP BY u.id, u.name
                """
                cursor.execute(query, (f"%{technician_name}%",))
                result = cursor.fetchone()
                
                if result:
                    response_text = f"Charge de travail de **{result['name']}** :\n\n"
                    response_text += f"• Total des tâches actives : {result['total_tasks']}\n"
                    response_text += f"• Tâches assignées : {result['assigned_tasks']}\n"
                    response_text += f"• Tâches en cours : {result['in_progress_tasks']}\n"
                    response_text += f"• Tâches urgentes : {result['urgent_tasks']}\n"
                    
                    # Évaluation de la charge
                    if result['total_tasks'] == 0:
                        response_text += "\n✅ **Statut : Disponible**"
                    elif result['total_tasks'] <= 2:
                        response_text += "\n🟡 **Statut : Peu occupé**"
                    elif result['total_tasks'] <= 4:
                        response_text += "\n🟠 **Statut : Occupé**"
                    else:
                        response_text += "\n🔴 **Statut : Surchargé**"
                else:
                    response_text = f"Aucun technicien trouvé avec le nom '{technician_name}'."
            else:
                # Vue d'ensemble de tous les techniciens
                query = """
                SELECT 
                    COUNT(DISTINCT u.id) as total_technicians,
                    COUNT(wo.id) as total_active_tasks,
                    AVG(task_count.tasks_per_tech) as avg_tasks_per_tech
                FROM users u
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                    AND wo.status IN ('assigned', 'in_progress')
                LEFT JOIN (
                    SELECT assigned_technician_id, COUNT(*) as tasks_per_tech
                    FROM work_orders 
                    WHERE status IN ('assigned', 'in_progress')
                    GROUP BY assigned_technician_id
                ) task_count ON u.id = task_count.assigned_technician_id
                WHERE u.role = 'technician' AND u.is_active = TRUE
                """
                cursor.execute(query)
                stats = cursor.fetchone()
                
                response_text = "**Vue d'ensemble de la charge de travail :**\n\n"
                response_text += f"• Nombre de techniciens actifs : {stats['total_technicians']}\n"
                response_text += f"• Total des tâches actives : {stats['total_active_tasks']}\n"
                response_text += f"• Moyenne par technicien : {round(stats['avg_tasks_per_tech'] or 0, 1)} tâches\n"
            
            cursor.close()
            connection.close()
            
            return {
                'text': response_text,
                'data': result if technician_name else stats,
                'charts': []
            }
            
        except Exception as e:
            print(f"❌ Erreur requête charge travail: {e}")
            return {
                'text': self.response_templates['no_data'],
                'data': None,
                'charts': []
            }
    
    async def _handle_urgent_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions sur les tâches urgentes"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
            SELECT 
                wo.id,
                wo.title,
                wo.priority,
                wo.status,
                wo.created_at,
                c.company_name as customer_name,
                u.name as technician_name
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            LEFT JOIN users u ON wo.assigned_technician_id = u.id
            WHERE wo.priority = 'urgent' AND wo.status IN ('pending', 'assigned', 'in_progress')
            ORDER BY wo.created_at ASC
            LIMIT 10
            """
            
            cursor.execute(query)
            urgent_tasks = cursor.fetchall()
            
            if urgent_tasks:
                response_text = f"**{len(urgent_tasks)} tâche{'s' if len(urgent_tasks) > 1 else ''} urgente{'s' if len(urgent_tasks) > 1 else ''} en cours :**\n\n"
                
                for task in urgent_tasks:
                    response_text += f"🚨 **{task['title']}**\n"
                    response_text += f"   Client : {task['customer_name'] or 'Non assigné'}\n"
                    response_text += f"   Technicien : {task['technician_name'] or 'Non assigné'}\n"
                    response_text += f"   Statut : {task['status']}\n"
                    response_text += f"   Créée : {task['created_at'].strftime('%d/%m/%Y %H:%M')}\n\n"
            else:
                response_text = "✅ **Aucune tâche urgente en cours.** Toutes les priorités sont sous contrôle."
            
            cursor.close()
            connection.close()
            
            return {
                'text': response_text,
                'data': {
                    'urgent_count': len(urgent_tasks),
                    'tasks': urgent_tasks
                },
                'charts': []
            }
            
        except Exception as e:
            print(f"❌ Erreur requête tâches urgentes: {e}")
            return {
                'text': self.response_templates['no_data'],
                'data': None,
                'charts': []
            }
    
    async def _handle_performance_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions sur les performances"""
        try:
            technician_name = params[0] if params else None
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if technician_name:
                # Performance d'un technicien spécifique
                query = """
                SELECT 
                    u.name,
                    COUNT(wo.id) as completed_tasks,
                    AVG(TIMESTAMPDIFF(HOUR, wo.created_at, wo.completed_at)) as avg_completion_time,
                    AVG(cf.overall_satisfaction) as avg_customer_satisfaction,
                    COUNT(CASE WHEN wo.completed_at <= wo.scheduled_date THEN 1 END) as on_time_completions
                FROM users u
                LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                    AND wo.status = 'completed'
                    AND wo.completed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
                WHERE u.name LIKE %s AND u.role = 'technician' AND u.is_active = TRUE
                GROUP BY u.id, u.name
                """
                cursor.execute(query, (f"%{technician_name}%",))
                result = cursor.fetchone()
                
                if result:
                    on_time_rate = (result['on_time_completions'] / result['completed_tasks'] * 100) if result['completed_tasks'] > 0 else 0
                    
                    response_text = f"**Performance de {result['name']} (30 derniers jours) :**\n\n"
                    response_text += f"• Tâches complétées : {result['completed_tasks']}\n"
                    response_text += f"• Temps moyen de traitement : {round(result['avg_completion_time'] or 0, 1)}h\n"
                    response_text += f"• Satisfaction client : {round(result['avg_customer_satisfaction'] or 0, 1)}/10\n"
                    response_text += f"• Taux de respect des délais : {round(on_time_rate, 1)}%\n"
                    
                    # Évaluation globale
                    if result['avg_customer_satisfaction'] and result['avg_customer_satisfaction'] >= 8 and on_time_rate >= 80:
                        response_text += "\n⭐ **Évaluation : Excellent**"
                    elif result['avg_customer_satisfaction'] and result['avg_customer_satisfaction'] >= 6 and on_time_rate >= 60:
                        response_text += "\n👍 **Évaluation : Bon**"
                    else:
                        response_text += "\n⚠️ **Évaluation : À améliorer**"
                else:
                    response_text = f"Aucun technicien trouvé avec le nom '{technician_name}' ou aucune donnée disponible."
            else:
                response_text = "Veuillez préciser le nom du technicien pour consulter ses performances."
            
            cursor.close()
            connection.close()
            
            return {
                'text': response_text,
                'data': result if technician_name else None,
                'charts': []
            }
            
        except Exception as e:
            print(f"❌ Erreur requête performance: {e}")
            return {
                'text': self.response_templates['no_data'],
                'data': None,
                'charts': []
            }
    
    async def _handle_customer_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions sur les clients"""
        # Implémentation similaire pour les questions clients
        return {
            'text': "Fonctionnalité client en cours de développement...",
            'data': None,
            'charts': []
        }
    
    async def _handle_eco_score_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions sur l'éco-score"""
        # Implémentation similaire pour l'éco-score
        return {
            'text': "Fonctionnalité éco-score en cours de développement...",
            'data': None,
            'charts': []
        }
    
    async def _handle_unknown_question(self, params: List[str], context: Dict) -> Dict[str, Any]:
        """Gère les questions non reconnues"""
        return {
            'text': "Je ne comprends pas cette question. Voici ce que je peux vous aider :\n\n" +
                   "• Disponibilité des techniciens\n" +
                   "• Charge de travail\n" +
                   "• Tâches urgentes\n" +
                   "• Performances\n" +
                   "• Satisfaction client\n" +
                   "• Éco-score\n\n" +
                   "Exemple : \"Quels techniciens sont disponibles cet après-midi ?\"",
            'data': None,
            'charts': []
        }
    
    def _extract_time_period(self, params: List[str]) -> str:
        """Extrait la période temporelle de la question"""
        text = ' '.join(params).lower() if params else ''
        
        if 'aujourd\'hui' in text or 'ce matin' in text or 'cet après-midi' in text:
            return "aujourd'hui"
        elif 'demain' in text:
            return "demain"
        elif 'cette semaine' in text:
            return "cette semaine"
        else:
            return "actuellement"
    
    def _generate_availability_chart_data(self, technicians: List[Dict]) -> Dict:
        """Génère les données pour le graphique de disponibilité"""
        status_counts = {}
        for tech in technicians:
            status = tech['availability_status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'labels': list(status_counts.keys()),
            'datasets': [{
                'data': list(status_counts.values()),
                'backgroundColor': ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
            }]
        }
    
    def _get_follow_up_suggestions(self, question_type: str) -> List[str]:
        """Génère des suggestions de questions de suivi"""
        suggestions = {
            'availability': [
                "Qui est le plus expérimenté parmi les disponibles ?",
                "Charge de travail de [nom du technicien] ?",
                "Planning de demain ?"
            ],
            'workload': [
                "Performances de ce technicien ?",
                "Tâches urgentes assignées ?",
                "Quels techniciens sont disponibles ?"
            ],
            'urgent': [
                "Techniciens disponibles pour l'urgent ?",
                "Historique des tâches urgentes ?",
                "Comment réduire les urgences ?"
            ]
        }
        
        return suggestions.get(question_type, [
            "Quels techniciens sont disponibles ?",
            "Y a-t-il des tâches urgentes ?",
            "Performance de l'équipe ?"
        ])
    
    def _save_to_history(self, user_id: int, question: str, response: Dict):
        """Sauvegarde la conversation dans l'historique"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO ai_conversation_history 
                (user_id, question, response, created_at)
                VALUES (%s, %s, %s, %s)
            """, (user_id, question, json.dumps(response), datetime.now()))
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde historique IA: {e}")

# Instance globale
conversational_ai = ConversationalAI()
