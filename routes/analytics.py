"""
Module d'analytics et tableaux de bord - ChronoTech
"""


from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import pymysql
from pymysql.cursors import DictCursor
from core.config import get_db_config
from core.utils import log_info, log_error, log_warning
from datetime import datetime, timedelta
import json

# Création du blueprint
bp = Blueprint('analytics', __name__)

def get_db_connection():
    """Obtient une connexion à la base de données"""
    try:
        cfg = get_db_config()
        cfg.setdefault('cursorclass', DictCursor)
        return pymysql.connect(**cfg)
    except Exception as e:
        log_error(f"Erreur de connexion à la base de données: {e}")
        return None

@bp.route('/')
def dashboard():
    try:
        conn = get_db_connection()
        if not conn:
            flash('Erreur de connexion à la base de données', 'error')
            stats = {}
            metrics = {
                'total_work_orders': 0,
                'work_orders_change': 0,
                'orders_by_status': {},
                'orders_by_priority': {},
                'active_technicians': 0,
                'active_customers': 0,
                'orders_this_week': 0,
                'completed_this_week': 0,
                'completion_rate': 0,
                'time_change': 0,
                'avg_resolution_time': 0,
                'completed_orders': 0,
                'total_revenue': 0,
                'revenue_change': 0
            }
            time_metrics = {'under_4h': 0, 'under_8h': 0, 'under_24h': 0, 'over_24h': 0}
            trend_data = {
                'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
                'data': [0, 0, 0, 0, 0, 0, 0]
            }
            status_chart = {
                'labels': ['En attente', 'En cours', 'Terminé', 'Annulé'],
                'data': [0, 0, 0, 0],
                'colors': ['#ffc107', '#007bff', '#28a745', '#dc3545']
            }
            priority_chart = {
                'labels': ['Basse', 'Moyenne', 'Haute', 'Urgente'],
                'data': [0, 0, 0, 0],
                'colors': ['#6c757d', '#007bff', '#fd7e14', '#dc3545']
            }
            technician_chart = {
                'labels': ['Disponible', 'Occupé', 'En pause'],
                'data': [0, 0, 0],
                'colors': ['#28a745', '#ffc107', '#6c757d']
            }
            zones = []
            status_breakdown = []
            intervention_types = {
                'labels': ['Maintenance', 'Réparation', 'Installation', 'Diagnostic'],
                'data': [0, 0, 0, 0],
                'colors': ['#17a2b8', '#28a745', '#ffc107', '#dc3545']
            }
            return render_template('analytics/dashboard.html', 
                                   stats=stats, 
                                   metrics=metrics, 
                                   time_metrics=time_metrics, 
                                   trend_data=trend_data, 
                                   status_chart=status_chart, 
                                   priority_chart=priority_chart, 
                                   technician_chart=technician_chart,
                                   zones=zones,
                                   status_breakdown=status_breakdown,intervention_types=intervention_types)

        # Always provide a default time_metrics dict
        default_time_metrics = {
            'under_4h': 0,
            'under_8h': 0,
            'under_24h': 0,
            'over_24h': 0
        }
        stats = {}
        metrics = {}
        time_metrics = {'under_4h': 0, 'under_8h': 0, 'under_24h': 0, 'over_24h': 0}
        trend_data = {
            'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'data': [0, 0, 0, 0, 0, 0, 0]
        }
        status_chart = {
            'labels': ['En attente', 'En cours', 'Terminé', 'Annulé'],
            'data': [0, 0, 0, 0],
            'colors': ['#ffc107', '#007bff', '#28a745', '#dc3545']
        }
        priority_chart = {
            'labels': ['Basse', 'Moyenne', 'Haute', 'Urgente'],
            'data': [0, 0, 0, 0],
            'colors': ['#6c757d', '#007bff', '#fd7e14', '#dc3545']
        }
        technician_chart = {
            'labels': ['Disponible', 'Occupé', 'En pause'],
            'data': [0, 0, 0],
            'colors': ['#28a745', '#ffc107', '#6c757d']
        }
        zones = []  # Liste des zones pour le tableau
        status_breakdown = []  # Répartition des statuts
        intervention_types = {
            'labels': ['Maintenance', 'Réparation', 'Installation', 'Diagnostic'],
            'data': [0, 0, 0, 0],
            'colors': ['#17a2b8', '#28a745', '#ffc107', '#dc3545']
        }
        try:
            cursor = conn.cursor()

            # Populate the simple stats used by the dashboard template
            # 1) Active orders (work orders currently in progress)
            cursor.execute("SELECT COUNT(*) AS active_orders FROM work_orders WHERE status = 'in_progress'")
            row = cursor.fetchone() or {}
            stats['active_orders'] = int(row.get('active_orders') or 0)

            # 2) Completed today (prefer completion_date but also accept updated_at)
            cursor.execute(
                """
                SELECT COUNT(*) AS completed_today
                FROM work_orders
                WHERE status = 'completed'
                AND (
                    (completion_date IS NOT NULL AND DATE(completion_date) = CURDATE())
                    OR DATE(updated_at) = CURDATE()
                )
                """
            )
            row = cursor.fetchone() or {}
            stats['completed_today'] = int(row.get('completed_today') or 0)

            # 3) Urgent orders (not yet completed or cancelled)
            cursor.execute("SELECT COUNT(*) AS urgent_orders FROM work_orders WHERE priority = 'urgent' AND status NOT IN ('completed','cancelled')")
            row = cursor.fetchone() or {}
            stats['urgent_orders'] = int(row.get('urgent_orders') or 0)

            # 4) Active technicians (users with role technician and is_active)
            cursor.execute("SELECT COUNT(*) AS active_technicians FROM users WHERE role = 'technician' AND is_active = 1")
            row = cursor.fetchone() or {}
            stats['active_technicians'] = int(row.get('active_technicians') or 0)

            # Also compute a few summary metrics used elsewhere (completion rate, totals)
            cursor.execute("SELECT COUNT(*) AS total FROM work_orders")
            total_orders = int((cursor.fetchone() or {}).get('total') or 0)
            cursor.execute("SELECT COUNT(*) AS completed FROM work_orders WHERE status = 'completed'")
            completed_orders = int((cursor.fetchone() or {}).get('completed') or 0)

            metrics.setdefault('work_orders_change', 0)
            metrics.setdefault('time_change', 0)
            metrics.setdefault('avg_resolution_time', 0)
            metrics.setdefault('total_revenue', 0)
            metrics.setdefault('revenue_change', 0)
            metrics['completed_orders'] = completed_orders
            metrics['completion_rate'] = round((completed_orders / total_orders) * 100, 1) if total_orders else 0

            cursor.close()
            conn.close()
        except Exception as e:
            log_error(f"Erreur lors de la génération du tableau de bord: {e}")
            # If an error occurs, metrics/time_metrics/trend_data are already initialized with safe defaults
        # Ensure all required keys are present before rendering
        required_metrics = {
            'total_work_orders': 0,
            'orders_by_status': {},
            'orders_by_priority': {},
            'active_technicians': 0,
            'active_customers': 0,
            'orders_this_week': 0,
            'completed_this_week': 0,
            'work_orders_change': 0,
            'time_change': 0,
            'avg_resolution_time': 0,
            'total_revenue': 0,
            'revenue_change': 0,
            'completed_orders': 0,
            'completion_rate': 0
        }
        for k, v in required_metrics.items():
            if k not in metrics:
                metrics[k] = v
        
        return render_template('analytics/dashboard.html', 
                               stats=stats, 
                               metrics=metrics, 
                               time_metrics=time_metrics, 
                               trend_data=trend_data, 
                               status_chart=status_chart, 
                               priority_chart=priority_chart, 
                               technician_chart=technician_chart,
                               zones=zones,
                               status_breakdown=status_breakdown,intervention_types=intervention_types)

    except Exception as e:
        log_error(f"Erreur lors de la génération du tableau de bord: {e}")
        flash('Erreur lors du chargement du tableau de bord', 'error')
        stats = {}
        metrics = {
            'total_work_orders': 0,
            'work_orders_change': 0,
            'orders_by_status': {},
            'orders_by_priority': {},
            'active_technicians': 0,
            'active_customers': 0,
            'orders_this_week': 0,
            'completed_this_week': 0,
            'completion_rate': 0,
            'time_change': 0,
            'avg_resolution_time': 0,
            'completed_orders': 0,
            'total_revenue': 0,
            'revenue_change': 0
        }
        time_metrics = {'under_4h': 0, 'under_8h': 0, 'under_24h': 0, 'over_24h': 0}
        trend_data = {
            'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
            'data': [0, 0, 0, 0, 0, 0, 0]
        }
        status_chart = {
            'labels': ['En attente', 'En cours', 'Terminé', 'Annulé'],
            'data': [0, 0, 0, 0],
            'colors': ['#ffc107', '#007bff', '#28a745', '#dc3545']
        }
        priority_chart = {
            'labels': ['Basse', 'Moyenne', 'Haute', 'Urgente'],
            'data': [0, 0, 0, 0],
            'colors': ['#6c757d', '#007bff', '#fd7e14', '#dc3545']
        }
        technician_chart = {
            'labels': ['Disponible', 'Occupé', 'En pause'],
            'data': [0, 0, 0],
            'colors': ['#28a745', '#ffc107', '#6c757d']
        }
        zones = []
        status_breakdown = []
        intervention_types = {
            'labels': ['Maintenance', 'Réparation', 'Installation', 'Diagnostic'],
            'data': [0, 0, 0, 0],
            'colors': ['#17a2b8', '#28a745', '#ffc107', '#dc3545']
        }
        return render_template('analytics/dashboard.html', 
                               stats=stats, 
                               metrics=metrics, 
                               time_metrics=time_metrics, 
                               trend_data=trend_data, 
                               status_chart=status_chart, 
                               priority_chart=priority_chart, 
                               technician_chart=technician_chart,
                               zones=zones,
                               status_breakdown=status_breakdown,intervention_types=intervention_types)

@bp.route('/api/stats/summary')
def stats_summary():
    """API pour statistiques résumées"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Erreur de connexion à la base de données'}), 500
        
        cursor = conn.cursor()

        summary = {}
        cursor.execute("""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) AS this_week,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN priority = 'urgent' THEN 1 ELSE 0 END) AS urgent,
                AVG(estimated_duration) AS avg_duration
            FROM work_orders
        """)
        stats = cursor.fetchone()
        summary.update(stats)
        summary['avg_duration_hours'] = round((stats['avg_duration'] or 0) / 60, 1)

        cursor.close()
        conn.close()
        return jsonify(summary)
        
    except Exception as e:
        log_error(f"Erreur lors de la récupération du résumé des statistiques: {e}")
        return jsonify({'error': 'Erreur lors de la récupération des statistiques'}), 500
