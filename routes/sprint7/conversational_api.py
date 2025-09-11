"""
Routes API Sprint 7 - IA Conversationnelle
Endpoints pour le chatbot IA et les questions conversationnelles
"""

from flask import Blueprint, request, jsonify, session
from core.security import login_required
from core.conversational_ai import conversational_ai
import asyncio
import json

# Blueprint IA conversationnelle
conversational_bp = Blueprint('conversational_ai', __name__)

@conversational_bp.route('/api/v1/ai/conversation', methods=['POST'])
@login_required
def handle_conversation():
    """Endpoint principal pour les questions conversationnelles"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Question requise'
            }), 400
        
        question = data['question']
        context = data.get('context', {})
        user_id = session.get('user_id', 1)  # À adapter selon votre système d'auth
        
        # Traitement asynchrone de la question
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response = loop.run_until_complete(
                conversational_ai.process_question(question, user_id, context)
            )
        finally:
            loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Erreur endpoint conversation: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur interne du serveur'
        }), 500

@conversational_bp.route('/api/v1/ai/conversation/history', methods=['GET'])
@login_required
def get_conversation_history():
    """Récupère l'historique des conversations"""
    try:
        user_id = session.get('user_id', 1)
        limit = request.args.get('limit', 10, type=int)
        
        from core.database import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT question, response, created_at
            FROM ai_conversation_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        history = cursor.fetchall()
        
        # Convertir les timestamps et parser les réponses JSON
        for item in history:
            item['created_at'] = item['created_at'].isoformat()
            try:
                item['response'] = json.loads(item['response'])
            except:
                pass
        
        cursor.close()
        connection.close()
        
        return jsonify(history)
        
    except Exception as e:
        print(f"❌ Erreur récupération historique: {e}")
        return jsonify([])

@conversational_bp.route('/api/v1/ai/suggestions', methods=['GET'])
@login_required
def get_question_suggestions():
    """Fournit des suggestions de questions basées sur le contexte"""
    try:
        context_type = request.args.get('context', 'general')
        
        suggestions = {
            'general': [
                "Quels techniciens sont disponibles maintenant ?",
                "Y a-t-il des tâches urgentes ?",
                "Performance de l'équipe cette semaine",
                "Satisfaction client du mois"
            ],
            'urgent': [
                "Qui peut prendre les urgences ?",
                "Historique des tâches critiques",
                "Comment réduire les urgences ?"
            ],
            'performance': [
                "Top 5 des meilleurs techniciens",
                "Techniciens ayant besoin de formation",
                "Évolution des performances mensuelles"
            ]
        }
        
        return jsonify({
            'suggestions': suggestions.get(context_type, suggestions['general'])
        })
        
    except Exception as e:
        print(f"❌ Erreur suggestions: {e}")
        return jsonify({'suggestions': []})

@conversational_bp.route('/api/v1/ai/feedback', methods=['POST'])
@login_required
def submit_ai_feedback():
    """Permet aux utilisateurs de noter les réponses de l'IA"""
    try:
        data = request.get_json()
        if not data or 'rating' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Rating requis'
            }), 400
        
        user_id = session.get('user_id', 1)
        rating = data['rating']  # 1-5
        question = data.get('question', '')
        response_id = data.get('response_id', None)
        comments = data.get('comments', '')
        
        from core.database import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO ai_feedback 
            (user_id, question, rating, comments, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (user_id, question, rating, comments))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback enregistré'
        })
        
    except Exception as e:
        print(f"❌ Erreur feedback IA: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur sauvegarde feedback'
        }), 500

@conversational_bp.route('/api/v1/ai/stats', methods=['GET'])
@login_required
def get_ai_stats():
    """Statistiques d'utilisation de l'IA conversationnelle"""
    try:
        from core.database import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Statistiques générales
        cursor.execute("""
            SELECT 
                COUNT(*) as total_questions,
                COUNT(DISTINCT user_id) as active_users,
                AVG(CASE WHEN response LIKE '%processing_time%' 
                    THEN JSON_EXTRACT(response, '$.processing_time') 
                    ELSE NULL END) as avg_response_time
            FROM ai_conversation_history
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        
        general_stats = cursor.fetchone()
        
        # Top questions
        cursor.execute("""
            SELECT question, COUNT(*) as frequency
            FROM ai_conversation_history
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY question
            ORDER BY frequency DESC
            LIMIT 5
        """)
        
        top_questions = cursor.fetchall()
        
        # Feedback moyen
        cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(*) as total_feedback
            FROM ai_feedback
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        
        feedback_stats = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'total_questions': general_stats['total_questions'] or 0,
            'active_users': general_stats['active_users'] or 0,
            'avg_response_time': round(general_stats['avg_response_time'] or 0, 2),
            'avg_rating': round(feedback_stats['avg_rating'] or 4.5, 1),
            'total_feedback': feedback_stats['total_feedback'] or 0,
            'top_questions': top_questions
        })
        
    except Exception as e:
        print(f"❌ Erreur stats IA: {e}")
        return jsonify({
            'total_questions': 0,
            'active_users': 0,
            'avg_response_time': 0,
            'avg_rating': 4.5,
            'total_feedback': 0,
            'top_questions': []
        })

# Endpoints pour les données spécifiques utilisées par l'IA

@conversational_bp.route('/api/v1/interventions/heatmap', methods=['GET'])
@login_required
def get_heatmap_data():
    """Données pour la heatmap d'interventions"""
    try:
        period = request.args.get('period', 'week')
        
        # Calculer la date de début selon la période
        from datetime import datetime, timedelta
        if period == 'today':
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = datetime.now() - timedelta(days=7)
        else:  # month
            start_date = datetime.now() - timedelta(days=30)
        
        from core.database import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                wo.id,
                wo.title,
                wo.created_at,
                c.latitude,
                c.longitude,
                c.company_name
            FROM work_orders wo
            LEFT JOIN customers c ON wo.customer_id = c.id
            WHERE wo.created_at >= %s 
                AND c.latitude IS NOT NULL 
                AND c.longitude IS NOT NULL
            ORDER BY wo.created_at DESC
            LIMIT 100
        """, (start_date,))
        
        interventions = cursor.fetchall()
        
        # Calculer les statistiques
        total_interventions = len(interventions)
        
        # Compter les zones actives (approximation par grille)
        zones = set()
        for intervention in interventions:
            if intervention['latitude'] and intervention['longitude']:
                zone_key = f"{int(intervention['latitude'] * 100)}_{int(intervention['longitude'] * 100)}"
                zones.add(zone_key)
        
        active_zones = len(zones)
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'interventions': interventions,
            'stats': {
                'totalInterventions': total_interventions,
                'activeZones': active_zones,
                'period': period
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur données heatmap: {e}")
        return jsonify({
            'interventions': [],
            'stats': {
                'totalInterventions': 0,
                'activeZones': 0,
                'period': period
            }
        })

@conversational_bp.route('/api/v1/admin/stats', methods=['GET'])
@login_required
def get_admin_stats():
    """Statistiques pour le widget Admin Center"""
    try:
        from core.database import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Compter utilisateurs et rôles
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE")
        users_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(DISTINCT role) as count FROM users WHERE is_active = TRUE")
        roles_count = cursor.fetchone()['count']
        
        cursor.close()
        connection.close()
        
        # Uptime simulé (à remplacer par une vraie métrique)
        import random
        uptime = round(95 + random.random() * 4, 1)  # Entre 95% et 99%
        
        return jsonify({
            'users': users_count,
            'roles': roles_count,
            'uptime': uptime
        })
        
    except Exception as e:
        print(f"❌ Erreur stats admin: {e}")
        return jsonify({
            'users': 0,
            'roles': 0,
            'uptime': 99.0
        })

@conversational_bp.route('/api/v1/admin/pending-validations', methods=['GET'])
@login_required
def get_pending_validations():
    """Récupère les validations en attente"""
    try:
        # Simuler quelques validations en attente (à remplacer par vraies données)
        validations = [
            {
                'id': 'rbac_001',
                'type': 'rbac',
                'description': 'Nouveau rôle "Manager Régional" en attente',
                'created_at': '2025-09-08T10:30:00'
            },
            {
                'id': 'audit_001', 
                'type': 'audit',
                'description': 'Export de logs requis pour audit externe',
                'created_at': '2025-09-08T14:15:00'
            }
        ]
        
        return jsonify(validations)
        
    except Exception as e:
        print(f"❌ Erreur validations en attente: {e}")
        return jsonify([])

# Export du blueprint
__all__ = ['conversational_bp']
