"""
Routes pour la gestion des widgets personnalisables
"""
from flask import Blueprint, request, jsonify, session, render_template
from core.database import db_manager
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

widgets_bp = Blueprint('dashboard_widgets', __name__)

@widgets_bp.route('/widgets', methods=['GET'])
def get_user_widgets():
    """Récupère la configuration des widgets de l'utilisateur"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Non authentifié'}), 401
        
        conn = db_manager.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Récupérer la configuration existante
        cursor.execute("""
            SELECT layout_config, updated_at
            FROM user_dashboard_config
            WHERE user_id = %s
        """, (user_id,))
        
        config = cursor.fetchone()
        conn.close()
        
        if config:
            return jsonify({
                'success': True,
                'layout': json.loads(config['layout_config']),
                'last_updated': config['updated_at'].isoformat()
            })
        else:
            # Configuration par défaut
            default_layout = {
                'widgets': [
                    {'id': 'copilot', 'x': 0, 'y': 0, 'w': 12, 'h': 4, 'enabled': True},
                    {'id': 'work_orders_kanban', 'x': 0, 'y': 4, 'w': 8, 'h': 6, 'enabled': True},
                    {'id': 'technicians_kanban', 'x': 8, 'y': 4, 'w': 4, 'h': 6, 'enabled': True},
                    {'id': 'gantt_chart', 'x': 0, 'y': 10, 'w': 12, 'h': 5, 'enabled': True},
                    {'id': 'customer360', 'x': 0, 'y': 15, 'w': 6, 'h': 4, 'enabled': False},
                    {'id': 'kpi_technicians', 'x': 6, 'y': 15, 'w': 6, 'h': 4, 'enabled': False}
                ]
            }
            
            return jsonify({
                'success': True,
                'layout': default_layout,
                'is_default': True
            })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des widgets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@widgets_bp.route('/widgets/save', methods=['POST'])
def save_user_widgets():
    """Sauvegarde la configuration des widgets"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Non authentifié'}), 401
        
        layout = request.json.get('layout')
        if not layout:
            return jsonify({'success': False, 'error': 'Layout requis'}), 400
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Upsert de la configuration
        cursor.execute("""
            INSERT INTO user_dashboard_config (user_id, layout_config, updated_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                layout_config = VALUES(layout_config),
                updated_at = VALUES(updated_at)
        """, (user_id, json.dumps(layout), datetime.now()))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Configuration sauvegardée'})
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des widgets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@widgets_bp.route('/widgets/available', methods=['GET'])
def get_available_widgets():
    """Récupère la liste des widgets disponibles"""
    try:
        user_role = session.get('user_role', 'technician')
        
        # Définir les widgets disponibles selon le rôle
        all_widgets = {
            'copilot': {
                'id': 'copilot',
                'name': 'Copilote IA',
                'description': 'Assistant intelligent avec analyses et recommandations',
                'icon': 'fa-robot',
                'color': 'primary',
                'roles': ['admin', 'supervisor', 'dispatcher'],
                'default_size': {'w': 12, 'h': 4}
            },
            'work_orders_kanban': {
                'id': 'work_orders_kanban',
                'name': 'Kanban Bons de Travail',
                'description': 'Vue Kanban des bons de travail',
                'icon': 'fa-tasks',
                'color': 'primary',
                'roles': ['admin', 'supervisor', 'dispatcher', 'technician'],
                'default_size': {'w': 8, 'h': 6}
            },
            'technicians_kanban': {
                'id': 'technicians_kanban',
                'name': 'Kanban Techniciens',
                'description': 'Vue Kanban des techniciens et leur statut',
                'icon': 'fa-users-gear',
                'color': 'success',
                'roles': ['admin', 'supervisor', 'dispatcher'],
                'default_size': {'w': 4, 'h': 6}
            },
            'gantt_chart': {
                'id': 'gantt_chart',
                'name': 'Diagramme de Gantt',
                'description': 'Planning des interventions',
                'icon': 'fa-chart-gantt',
                'color': 'info',
                'roles': ['admin', 'supervisor', 'dispatcher'],
                'default_size': {'w': 12, 'h': 5}
            },
            'customer360': {
                'id': 'customer360',
                'name': 'Vue 360° Client',
                'description': 'Fiche complète client avec historique',
                'icon': 'fa-user-circle',
                'color': 'warning',
                'roles': ['admin', 'supervisor', 'dispatcher'],
                'default_size': {'w': 6, 'h': 4}
            },
            'kpi_technicians': {
                'id': 'kpi_technicians',
                'name': 'KPI Techniciens',
                'description': 'Indicateurs de performance en temps réel',
                'icon': 'fa-chart-line',
                'color': 'success',
                'roles': ['admin', 'supervisor'],
                'default_size': {'w': 6, 'h': 4}
            },
            'predictive_alerts': {
                'id': 'predictive_alerts',
                'name': 'Alertes Prédictives',
                'description': 'Détection automatique des surcharges',
                'icon': 'fa-bell',
                'color': 'warning',
                'roles': ['admin', 'supervisor'],
                'default_size': {'w': 6, 'h': 4}
            },
            'interventions_map': {
                'id': 'interventions_map',
                'name': 'Carte des Interventions',
                'description': 'Heatmap géographique des interventions',
                'icon': 'fa-map-marker-alt',
                'color': 'danger',
                'roles': ['admin', 'supervisor', 'dispatcher'],
                'default_size': {'w': 12, 'h': 6}
            },
            'stats_cards': {
                'id': 'stats_cards',
                'name': 'Cartes de Statistiques',
                'description': 'KPIs principaux en un coup d\'œil',
                'icon': 'fa-chart-bar',
                'color': 'info',
                'roles': ['admin', 'supervisor', 'dispatcher', 'technician'],
                'default_size': {'w': 12, 'h': 2}
            }
        }
        
        # Filtrer selon le rôle
        available_widgets = {
            widget_id: widget_config
            for widget_id, widget_config in all_widgets.items()
            if user_role in widget_config['roles']
        }
        
        return jsonify({
            'success': True,
            'widgets': available_widgets,
            'user_role': user_role
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des widgets disponibles: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@widgets_bp.route('/widgets/reset', methods=['POST'])
def reset_user_widgets():
    """Remet à zéro la configuration des widgets"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Non authentifié'}), 401
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Supprimer la configuration existante
        cursor.execute("""
            DELETE FROM user_dashboard_config WHERE user_id = %s
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Configuration réinitialisée'})
        
    except Exception as e:
        logger.error(f"Erreur lors de la réinitialisation des widgets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
