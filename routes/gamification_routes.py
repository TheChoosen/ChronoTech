"""
Routes API Sprint 5 - Gamification et engagement
Endpoints pour badges, classements et feedback client
"""

from flask import Blueprint, jsonify, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
from core.gamification import GamificationEngine, ClientFeedbackManager

# Initialiser les instances
gamification_engine = GamificationEngine()
feedback_manager = ClientFeedbackManager()
from core.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

# Blueprint pour la gamification
gamification_bp = Blueprint('gamification', __name__, url_prefix='/api/gamification')

@gamification_bp.route('/dashboard')
@login_required
def gamification_dashboard():
    """Page principale du dashboard gamification"""
    try:
        # Récupérer le profil de l'utilisateur connecté
        profile = gamification_engine.get_user_gamification_profile(current_user.id)
        
        # Récupérer le classement hebdomadaire
        leaderboard = gamification_engine.generate_leaderboard('individual_weekly')
        
        return render_template('gamification/dashboard.html', 
                             title="Gamification Dashboard",
                             profile=profile.get('data', {}),
                             leaderboard=leaderboard.get('rankings', []))
        
    except Exception as e:
        logger.error(f"Erreur dashboard gamification: {e}")
        return render_template('error.html', error=str(e)), 500

@gamification_bp.route('/profile/<int:user_id>')
@login_required
def get_user_profile(user_id):
    """Récupère le profil gamification d'un utilisateur"""
    try:
        # Vérifier que l'utilisateur peut accéder à ce profil
        if user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
        
        profile = gamification_engine.get_user_gamification_profile(user_id)
        
        if not profile['success']:
            return jsonify({'success': False, 'error': profile['error']}), 400
        
        return jsonify({
            'success': True,
            'data': profile
        })
        
    except Exception as e:
        logger.error(f"Erreur profil utilisateur {user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gamification_bp.route('/badges/available')
@login_required
def get_available_badges():
    """Récupère tous les badges disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT bd.*, 
                   CASE WHEN ub.id IS NOT NULL THEN TRUE ELSE FALSE END as earned,
                   ub.earned_at
            FROM badge_definitions bd
            LEFT JOIN user_badges ub ON bd.id = ub.badge_id AND ub.user_id = %s
            WHERE bd.is_active = TRUE
            ORDER BY bd.category, bd.criteria_value ASC
        """, (current_user.id,))
        
        badges = cursor.fetchall()
        
        # Grouper par catégorie
        badges_by_category = {}
        for badge in badges:
            category = badge['category']
            if category not in badges_by_category:
                badges_by_category[category] = []
            
            badges_by_category[category].append({
                **badge,
                'earned_at': badge['earned_at'].isoformat() if badge['earned_at'] else None
            })
        
        return jsonify({
            'success': True,
            'badges_by_category': badges_by_category,
            'total_badges': len(badges),
            'earned_count': sum(1 for b in badges if b['earned'])
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération badges: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@gamification_bp.route('/leaderboard/<leaderboard_type>')
@login_required
def get_leaderboard(leaderboard_type):
    """Récupère un classement spécifique"""
    try:
        period_key = request.args.get('period')
        
        # Valider le type de classement
        valid_types = [
            'individual_weekly', 'individual_monthly',
            'team_weekly', 'team_monthly',
            'department_weekly', 'department_monthly'
        ]
        
        if leaderboard_type not in valid_types:
            return jsonify({'success': False, 'error': 'Type de classement invalide'}), 400
        
        # Générer le classement
        leaderboard = gamification_engine.generate_leaderboard(leaderboard_type, period_key)
        
        if not leaderboard['success']:
            return jsonify({'success': False, 'error': leaderboard['error']}), 400
        
        # Ajouter la position de l'utilisateur actuel si applicable
        user_position = None
        if leaderboard_type.startswith('individual'):
            for i, entry in enumerate(leaderboard['rankings']):
                if entry['entity_id'] == current_user.id:
                    user_position = i + 1
                    break
        
        return jsonify({
            'success': True,
            'leaderboard_type': leaderboard_type,
            'period_key': leaderboard['period_key'],
            'rankings': leaderboard['rankings'],
            'total_participants': leaderboard['total_participants'],
            'user_position': user_position
        })
        
    except Exception as e:
        logger.error(f"Erreur classement {leaderboard_type}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gamification_bp.route('/scores/recalculate')
@login_required
def recalculate_scores():
    """Recalcule les scores de l'utilisateur actuel"""
    try:
        periods = ['weekly', 'monthly', 'total']
        results = {}
        
        for period in periods:
            result = gamification_engine.calculate_user_scores(current_user.id, period)
            results[period] = result
        
        # Vérifier les nouveaux badges
        badges_result = gamification_engine.check_and_award_badges(current_user.id)
        
        return jsonify({
            'success': True,
            'scores': results,
            'badges_check': badges_result,
            'message': 'Scores recalculés avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur recalcul scores utilisateur {current_user.id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@gamification_bp.route('/notifications')
@login_required
def get_notifications():
    """Récupère les notifications de gamification de l'utilisateur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        limit = int(request.args.get('limit', 20))
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        where_clause = "WHERE user_id = %s"
        params = [current_user.id]
        
        if unread_only:
            where_clause += " AND is_read = FALSE"
        
        cursor.execute(f"""
            SELECT * FROM gamification_notifications
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """, params + [limit])
        
        notifications = cursor.fetchall()
        
        # Convertir les dates pour JSON
        for notification in notifications:
            notification['created_at'] = notification['created_at'].isoformat()
            if notification['read_at']:
                notification['read_at'] = notification['read_at'].isoformat()
            if notification['data']:
                notification['data'] = json.loads(notification['data'])
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'total': len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Erreur notifications utilisateur {current_user.id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@gamification_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marque une notification comme lue"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE gamification_notifications 
            SET is_read = TRUE, read_at = NOW()
            WHERE id = %s AND user_id = %s AND is_read = FALSE
        """, (notification_id, current_user.id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Notification non trouvée'}), 404
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marquée comme lue'
        })
        
    except Exception as e:
        logger.error(f"Erreur marquage notification {notification_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@gamification_bp.route('/stats/overview')
@login_required
def get_stats_overview():
    """Récupère un aperçu des statistiques de gamification"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Statistiques générales du système
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT ub.user_id) as active_users,
                COUNT(DISTINCT ub.id) as total_badges_earned,
                COUNT(DISTINCT bd.id) as total_badges_available,
                AVG(cf.overall_satisfaction) as avg_satisfaction,
                COUNT(DISTINCT cf.id) as total_feedback
            FROM badge_definitions bd
            LEFT JOIN user_badges ub ON bd.id = ub.badge_id
            LEFT JOIN client_feedback cf ON cf.submitted_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            WHERE bd.is_active = TRUE
        """)
        
        system_stats = cursor.fetchone() or {}
        
        # Top performers cette semaine
        cursor.execute("""
            SELECT 
                l.entity_name,
                l.total_points,
                l.work_orders_completed,
                l.avg_satisfaction
            FROM leaderboards l
            WHERE l.leaderboard_type = 'individual_weekly'
            AND l.period_key = DATE_FORMAT(NOW(), '%Y-W%u')
            ORDER BY l.rank_position ASC
            LIMIT 5
        """)
        
        top_performers = cursor.fetchall()
        
        # Badges les plus récents
        cursor.execute("""
            SELECT 
                ub.earned_at,
                u.name as user_name,
                bd.name as badge_name,
                bd.icon,
                bd.color
            FROM user_badges ub
            INNER JOIN users u ON ub.user_id = u.id
            INNER JOIN badge_definitions bd ON ub.badge_id = bd.id
            WHERE ub.earned_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY ub.earned_at DESC
            LIMIT 10
        """)
        
        recent_badges = cursor.fetchall()
        
        # Convertir les dates
        for badge in recent_badges:
            badge['earned_at'] = badge['earned_at'].isoformat()
        
        return jsonify({
            'success': True,
            'system_stats': system_stats,
            'top_performers': top_performers,
            'recent_badges': recent_badges
        })
        
    except Exception as e:
        logger.error(f"Erreur aperçu statistiques: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Routes pour le feedback client (publiques)
feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')

@feedback_bp.route('/<token>')
def feedback_form(token):
    """Affiche le formulaire de feedback client"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Vérifier le token
        cursor.execute("""
            SELECT cf.*, wo.claim_number, wo.description as work_description,
                   c.name as customer_name, u.name as technician_name,
                   u.photo as technician_photo
            FROM client_feedback cf
            INNER JOIN work_orders wo ON cf.work_order_id = wo.id
            INNER JOIN customers c ON cf.customer_id = c.id
            INNER JOIN users u ON cf.technician_id = u.id
            WHERE cf.feedback_token = %s AND cf.expires_at > NOW()
        """, (token,))
        
        feedback_data = cursor.fetchone()
        
        if not feedback_data:
            return render_template('feedback/expired.html', 
                                 title="Lien expiré"), 410
        
        # Vérifier si déjà soumis
        if feedback_data['submitted_at']:
            return render_template('feedback/already_submitted.html',
                                 title="Feedback déjà soumis",
                                 feedback=feedback_data)
        
        return render_template('feedback/form.html',
                             title="Évaluation de l'intervention",
                             feedback=feedback_data,
                             token=token)
        
    except Exception as e:
        logger.error(f"Erreur formulaire feedback {token}: {e}")
        return render_template('error.html', error=str(e)), 500
    finally:
        if 'conn' in locals():
            conn.close()

@feedback_bp.route('/<token>/submit', methods=['POST'])
def submit_feedback(token):
    """Traite la soumission du feedback client"""
    try:
        # Récupérer les données du formulaire
        feedback_data = {
            'overall_satisfaction': int(request.form.get('overall_satisfaction', 0)),
            'quality_work': int(request.form.get('quality_work', 0)),
            'technician_professionalism': int(request.form.get('technician_professionalism', 0)),
            'response_time_satisfaction': int(request.form.get('response_time_satisfaction', 0)),
            'communication_quality': int(request.form.get('communication_quality', 0)),
            'nps_score': int(request.form.get('nps_score', 0)),
            'positive_feedback': request.form.get('positive_feedback', '').strip(),
            'improvement_feedback': request.form.get('improvement_feedback', '').strip(),
            'additional_comments': request.form.get('additional_comments', '').strip(),
            'would_recommend': request.form.get('would_recommend') == 'on',
            'would_use_again': request.form.get('would_use_again') == 'on',
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        }
        
        # Valider les données requises
        required_fields = ['overall_satisfaction', 'quality_work', 'technician_professionalism', 
                          'response_time_satisfaction', 'communication_quality', 'nps_score']
        
        for field in required_fields:
            if not feedback_data[field] or feedback_data[field] == 0:
                return render_template('feedback/form.html',
                                     error=f"Le champ {field} est requis",
                                     token=token), 400
        
        # Soumettre le feedback
        result = feedback_manager.submit_feedback(token, feedback_data)
        
        if not result['success']:
            return render_template('feedback/form.html',
                                 error=result['error'],
                                 token=token), 400
        
        return render_template('feedback/success.html',
                             title="Merci pour votre feedback",
                             result=result)
        
    except Exception as e:
        logger.error(f"Erreur soumission feedback {token}: {e}")
        return render_template('feedback/form.html',
                             error="Erreur lors de la soumission",
                             token=token), 500

@feedback_bp.route('/stats')
@login_required
def feedback_stats():
    """Statistiques de feedback (pour admins/superviseurs)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        period_days = int(request.args.get('days', 30))
        technician_id = request.args.get('technician_id')
        
        if technician_id:
            technician_id = int(technician_id)
        
        stats = feedback_manager.get_feedback_stats(technician_id, period_days)
        
        if not stats['success']:
            return jsonify({'success': False, 'error': stats['error']}), 400
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Erreur stats feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Routes pour la page de classement
@gamification_bp.route('/leaderboard/page')
@login_required
def leaderboard_page():
    """Page de visualisation des classements"""
    return render_template('gamification/leaderboard.html', 
                         title="Classements")
