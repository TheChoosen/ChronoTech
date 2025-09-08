"""
Routes IA pour les interventions - Sprint 2 Production
Endpoints pour l'analyse IA, suggestions et résumés
"""
import os
import pymysql
import logging
import json
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
from services.ai_guards import ai_guards

logger = logging.getLogger(__name__)

# Blueprint pour les routes IA
ai_bp = Blueprint('ai', __name__)

def get_db_connection():
    """Connexion à la base de données"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DB', 'chronotech'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def require_auth(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@ai_bp.route('/api/openai/audio', methods=['POST'])
@require_auth
def process_audio():
    """
    Traitement audio pour transcription et analyse
    Endpoint référencé par _details_scripts.html
    """
    try:
        # Vérifier qu'un fichier audio est présent
        if 'audio' not in request.files:
            return jsonify({
                'success': False, 
                'message': 'Aucun fichier audio fourni'
            }), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                'success': False, 
                'message': 'Fichier audio vide'
            }), 400
        
        # Pour l'instant, simulation de transcription
        # En production, intégrer avec OpenAI Whisper ou service similaire
        mock_transcription = {
            'success': True,
            'transcription': 'Simulation de transcription audio - Vérification des freins effectuée, plaquettes à 70%, disques en bon état.',
            'confidence': 0.85,
            'duration': 15.3,
            'language': 'fr'
        }
        
        return jsonify(mock_transcription)
        
    except Exception as e:
        logger.error(f"Erreur traitement audio: {e}")
        return jsonify({
            'success': False, 
            'message': 'Erreur lors du traitement audio'
        }), 500

@ai_bp.route('/interventions/ai/generate_summary/<int:work_order_id>', methods=['POST'])
@require_auth
def generate_summary(work_order_id):
    """
    Génération de résumé IA pour une intervention
    Endpoint référencé par _details_scripts.html
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Récupérer les données de l'intervention
            cursor.execute("""
                SELECT 
                    wo.*,
                    GROUP_CONCAT(DISTINCT in_.note SEPARATOR '\n') as all_notes,
                    COUNT(DISTINCT im.id) as media_count,
                    GROUP_CONCAT(DISTINCT wot.title SEPARATOR ', ') as tasks
                FROM work_orders wo
                LEFT JOIN work_order_tasks wot ON wo.id = wot.work_order_id
                LEFT JOIN interventions i ON wot.id = i.task_id
                LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                LEFT JOIN intervention_media im ON i.id = im.intervention_id
                WHERE wo.id = %s
                GROUP BY wo.id
            """, (work_order_id,))
            
            intervention_data = cursor.fetchone()
            
            if not intervention_data:
                return jsonify({
                    'success': False,
                    'message': 'Intervention non trouvée'
                }), 404
            
            # Génération du résumé (simulation IA)
            summary = {
                'success': True,
                'summary': {
                    'title': f"Résumé intervention {intervention_data['claim_number']}",
                    'description': f"Intervention sur véhicule pour {intervention_data.get('customer_name', 'Client')}",
                    'tasks_completed': intervention_data['tasks'] or 'Aucune tâche définie',
                    'notes_summary': intervention_data['all_notes'][:200] + '...' if intervention_data['all_notes'] and len(intervention_data['all_notes']) > 200 else intervention_data['all_notes'] or 'Aucune note',
                    'media_attached': intervention_data['media_count'] or 0,
                    'status': intervention_data['status'],
                    'generated_at': datetime.now().isoformat()
                },
                'recommendations': [
                    'Planifier un suivi dans 3 mois',
                    'Vérifier l\'usure des pièces remplacées',
                    'Documenter les prochaines maintenances préventives'
                ]
            }
            
            return jsonify(summary)
            
    except Exception as e:
        logger.error(f"Erreur génération résumé WO {work_order_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la génération du résumé'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@ai_bp.route('/interventions/ai/suggestions/<int:work_order_id>', methods=['GET'])
@require_auth
def get_suggestions(work_order_id):
    """
    Récupération des suggestions IA pour une intervention
    Endpoint référencé par _details_scripts.html
    """
    try:
        suggestion_type = request.args.get('type', 'diagnostic')
        
        # Utiliser le service AI Guards pour les suggestions
        if suggestion_type == 'parts':
            # Récupérer d'abord une tâche de ce WO
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM work_order_tasks 
                        WHERE work_order_id = %s 
                        LIMIT 1
                    """, (work_order_id,))
                    
                    task = cursor.fetchone()
                    if task:
                        parts_suggestions = ai_guards.suggest_parts_for_task(task['id'])
                    else:
                        parts_suggestions = []
            finally:
                conn.close()
            
            return jsonify({
                'success': True,
                'type': 'parts',
                'suggestions': parts_suggestions
            })
        
        elif suggestion_type == 'diagnostic':
            # Suggestions de diagnostic génériques
            diagnostic_suggestions = [
                {
                    'category': 'Freinage',
                    'items': [
                        'Vérifier l\'épaisseur des plaquettes',
                        'Contrôler l\'état des disques',
                        'Tester la pression du liquide de frein'
                    ]
                },
                {
                    'category': 'Moteur',
                    'items': [
                        'Contrôler le niveau d\'huile',
                        'Vérifier les bougies d\'allumage',
                        'Inspecter les courroies'
                    ]
                },
                {
                    'category': 'Électrique',
                    'items': [
                        'Tester la batterie',
                        'Vérifier l\'alternateur',
                        'Contrôler les fusibles'
                    ]
                }
            ]
            
            return jsonify({
                'success': True,
                'type': 'diagnostic',
                'suggestions': diagnostic_suggestions
            })
        
        else:
            return jsonify({
                'success': False,
                'message': f'Type de suggestion non supporté: {suggestion_type}'
            }), 400
            
    except Exception as e:
        logger.error(f"Erreur suggestions IA WO {work_order_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la récupération des suggestions'
        }), 500

@ai_bp.route('/api/ai/chat', methods=['POST'])
@require_auth
def ai_chat():
    """
    Chat IA pour assistance technique
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Message requis'
            }), 400
        
        # Simulation de réponse IA
        # En production, intégrer avec OpenAI GPT ou service similaire
        ai_response = {
            'success': True,
            'response': f"Réponse IA simulée pour: '{message}'. En production, ceci serait traité par un modèle de langage avancé.",
            'confidence': 0.9,
            'sources': ['Manuel technique', 'Base de connaissances'],
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(ai_response)
        
    except Exception as e:
        logger.error(f"Erreur chat IA: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors du traitement de la demande'
        }), 500
