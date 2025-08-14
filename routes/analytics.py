"""
Module d'analytics et tableaux de bord - ChronoTech
"""


from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import pymysql
from pymysql.cursors import DictCursor
from config import get_db_config
from utils import log_info, log_error, log_warning
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
                'completed_orders': 0
            }
            return render_template('analytics/dashboard.html', stats=stats, metrics=metrics)

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
        trend_data = {'labels': [], 'values': []}
        try:
            cursor = conn.cursor()

            # ...existing code for metrics...

            # Valeurs par défaut pour les métriques non encore calculées
            metrics.setdefault('work_orders_change', 0)
            metrics.setdefault('time_change', 0)
            metrics.setdefault('avg_resolution_time', 0)
            metrics.setdefault('total_revenue', 0)
            metrics.setdefault('revenue_change', 0)
            metrics.setdefault('completed_orders', 0)
            metrics.setdefault('completion_rate', 0)

            # Taux de complétion
            cursor.execute("SELECT COUNT(*) AS total FROM work_orders")
            total_orders = cursor.fetchone()['total'] or 0
            cursor.execute("SELECT COUNT(*) AS completed FROM work_orders WHERE status = 'completed'")
            completed_orders = cursor.fetchone()['completed'] or 0
            metrics['completed_orders'] = completed_orders
            metrics['completion_rate'] = round((completed_orders / total_orders) * 100, 1) if total_orders else 0

            # TODO: Calculate real time_metrics and trend_data if needed

            cursor.close()
            conn.close()
        except Exception as e:
            log_error(f"Erreur lors de la génération du tableau de bord: {e}")
            # If an error occurs, metrics/time_metrics/trend_data are already initialized with safe defaults
        # Ensure all required keys are present before rendering
        for k, v in {
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
        }.items():
            metrics.setdefault(k, v)
        return render_template('analytics/dashboard.html', stats=stats, metrics=metrics, time_metrics=time_metrics, trend_data=trend_data)

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
            'total_revenue': 0
        }
        return render_template('analytics/dashboard.html', stats=stats, metrics=metrics)

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
