"""
Widget Gamification pour le Dashboard
Sprint 5 - Badges et classements
"""

from flask import render_template, current_app, g
from core.database import get_db_connection
import mysql.connector.cursor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def render_gamification_widget(user_id, widget_config=None):
    """Rendu du widget gamification pour le dashboard"""
    try:
        # Configuration par défaut
        config = {
            'show_badges': True,
            'show_leaderboard': True,
            'max_badges': 6,
            'max_leaderboard': 5,
            'leaderboard_type': 'individual_weekly'
        }
        
        if widget_config:
            config.update(widget_config)
        
        # Récupérer les données de l'utilisateur
        user_profile = get_user_gamification_summary(user_id)
        badges = get_user_recent_badges(user_id, config['max_badges']) if config['show_badges'] else []
        leaderboard = get_leaderboard_summary(config['leaderboard_type'], config['max_leaderboard']) if config['show_leaderboard'] else []
        
        return render_template('widgets/gamification_widget.html', 
                             profile=user_profile,
                             badges=badges,
                             leaderboard=leaderboard,
                             config=config)
        
    except Exception as e:
        logger.error(f"Erreur widget gamification: {e}")
        return render_template('widgets/error_widget.html', 
                             title="Gamification",
                             error="Erreur de chargement des données")

def get_user_gamification_summary(user_id):
    """Récupère un résumé du profil gamification de l'utilisateur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)
        
        # Récupérer les scores et badges de l'utilisateur
        cursor.execute("""
            SELECT 
                us.total_points,
                us.weekly_points,
                us.monthly_points,
                COUNT(ub.id) as badges_earned,
                COUNT(DISTINCT bd.id) as total_badges,
                AVG(cf.overall_satisfaction) as avg_satisfaction,
                COUNT(DISTINCT wo.id) as work_orders_completed
            FROM users u
            LEFT JOIN user_scores us ON u.id = us.user_id AND us.period_type = 'total'
            LEFT JOIN user_badges ub ON u.id = ub.user_id
            LEFT JOIN badge_definitions bd ON bd.is_active = TRUE
            LEFT JOIN work_orders wo ON u.id = wo.technician_id AND wo.status = 'completed'
            LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
            WHERE u.id = %s
            GROUP BY u.id, us.total_points, us.weekly_points, us.monthly_points
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            return {
                'total_points': 0,
                'weekly_points': 0,
                'monthly_points': 0,
                'badges_earned': 0,
                'total_badges': 0,
                'avg_satisfaction': 0,
                'work_orders_completed': 0,
                'completion_rate': 0
            }
        
        # Calculer le taux de completion des badges
        completion_rate = 0
        if result['total_badges'] > 0:
            completion_rate = (result['badges_earned'] / result['total_badges']) * 100
        
        return {
            **result,
            'completion_rate': round(completion_rate, 1),
            'avg_satisfaction': round(result.get('avg_satisfaction', 0) or 0, 1)
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération profil gamification: {e}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def get_user_recent_badges(user_id, limit=6):
    """Récupère les badges récents de l'utilisateur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)
        
        cursor.execute("""
            SELECT 
                bd.name,
                bd.description,
                bd.icon,
                bd.color,
                bd.category,
                ub.earned_at,
                CASE WHEN ub.id IS NOT NULL THEN TRUE ELSE FALSE END as earned
            FROM badge_definitions bd
            LEFT JOIN user_badges ub ON bd.id = ub.badge_id AND ub.user_id = %s
            WHERE bd.is_active = TRUE
            ORDER BY ub.earned_at DESC, bd.criteria_value ASC
            LIMIT %s
        """, (user_id, limit))
        
        badges = cursor.fetchall()
        
        # Formater les dates
        for badge in badges:
            if badge['earned_at']:
                badge['earned_at'] = badge['earned_at'].isoformat()
        
        return badges
        
    except Exception as e:
        logger.error(f"Erreur récupération badges récents: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_leaderboard_summary(leaderboard_type='individual_weekly', limit=5):
    """Récupère un résumé du classement"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_class=mysql.connector.cursor.MySQLCursorDict)
        
        # Déterminer la période actuelle
        now = datetime.now()
        if 'weekly' in leaderboard_type:
            period_key = now.strftime('%Y-W%U')
        else:  # monthly
            period_key = now.strftime('%Y-%m')
        
        cursor.execute("""
            SELECT 
                entity_name,
                total_points,
                work_orders_completed,
                avg_satisfaction,
                rank_position
            FROM leaderboards
            WHERE leaderboard_type = %s 
            AND period_key = %s
            ORDER BY rank_position ASC
            LIMIT %s
        """, (leaderboard_type, period_key, limit))
        
        leaderboard = cursor.fetchall()
        
        # Formater les données
        for entry in leaderboard:
            entry['avg_satisfaction'] = round(entry.get('avg_satisfaction', 0) or 0, 1)
        
        return leaderboard
        
    except Exception as e:
        logger.error(f"Erreur récupération classement: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_widget_data(user_id, widget_type='full'):
    """Récupère les données pour différents types de widgets gamification"""
    try:
        if widget_type == 'badges_only':
            return {
                'badges': get_user_recent_badges(user_id, 8),
                'profile': get_user_gamification_summary(user_id)
            }
        elif widget_type == 'leaderboard_only':
            return {
                'leaderboard': get_leaderboard_summary('individual_weekly', 8),
                'profile': get_user_gamification_summary(user_id)
            }
        else:  # full
            return {
                'profile': get_user_gamification_summary(user_id),
                'badges': get_user_recent_badges(user_id, 6),
                'leaderboard': get_leaderboard_summary('individual_weekly', 5)
            }
    except Exception as e:
        logger.error(f"Erreur récupération données widget: {e}")
        return {}

# Configuration des widgets disponibles
def create_badges_renderer():
    def renderer(user_id, config):
        badges_config = dict(config or {})
        badges_config.update({'show_leaderboard': False, 'max_badges': 8})
        return render_gamification_widget(user_id, badges_config)
    return renderer

def create_leaderboard_renderer():
    def renderer(user_id, config):
        leaderboard_config = dict(config or {})
        leaderboard_config.update({'show_badges': False, 'max_leaderboard': 8})
        return render_gamification_widget(user_id, leaderboard_config)
    return renderer

GAMIFICATION_WIDGETS = {
    'gamification_full': {
        'name': 'Gamification Complète',
        'description': 'Badges, points et classement',
        'icon': 'fas fa-trophy',
        'size': 'large',
        'renderer': render_gamification_widget
    },
    'gamification_badges': {
        'name': 'Mes Badges',
        'description': 'Badges obtenus et disponibles',
        'icon': 'fas fa-medal',
        'size': 'medium',
        'renderer': create_badges_renderer()
    },
    'gamification_leaderboard': {
        'name': 'Classement',
        'description': 'Classement de l\'équipe',
        'icon': 'fas fa-list-ol',
        'size': 'medium',
        'renderer': create_leaderboard_renderer()
    }
}

def register_gamification_widgets(widget_registry):
    """Enregistre les widgets de gamification dans le registre"""
    try:
        for widget_id, widget_config in GAMIFICATION_WIDGETS.items():
            widget_registry[widget_id] = widget_config
        logger.info(f"✅ {len(GAMIFICATION_WIDGETS)} widgets gamification enregistrés")
    except Exception as e:
        logger.error(f"Erreur enregistrement widgets gamification: {e}")
