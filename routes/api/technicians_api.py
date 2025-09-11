# ChronoTech - API Routes pour KPI Techniciens
# Endpoint pour les données des widgets dashboard

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import mysql.connector
import mysql.connector

def get_db_connection():
    """Connexion à la base de données MySQL"""
    return mysql.connector.connect(
        host='192.168.50.101',
        user='gsicloud',
        password='TCOChoosenOne204$',
        database='bdm',
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci',
        autocommit=True
    )

# Blueprint pour les API techniciens
technicians_api = Blueprint('technicians_api', __name__, url_prefix='/api/technicians')

@technicians_api.route('/kpi', methods=['GET'])
def get_technicians_kpi():
    """Retourne les KPI des techniciens pour le widget dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Compter les techniciens actifs (connectés dans les 2 dernières heures)
        cursor.execute("""
            SELECT COUNT(*) as active_count
            FROM technicians t
            LEFT JOIN user_sessions us ON t.user_id = us.user_id
            WHERE t.status = 'active' 
            AND (us.last_activity IS NULL OR us.last_activity >= %s)
        """, (datetime.now() - timedelta(hours=2),))
        
        active_technicians = cursor.fetchone()['active_count']
        
        # Compter les interventions actives
        cursor.execute("""
            SELECT COUNT(*) as active_interventions
            FROM work_orders wo
            WHERE wo.status IN ('assigned', 'in_progress')
            AND wo.assigned_technician_id IS NOT NULL
        """)
        
        active_interventions = cursor.fetchone()['active_interventions']
        
        # Calculer la performance moyenne (basée sur les interventions terminées aujourd'hui)
        today = datetime.now().date()
        cursor.execute("""
            SELECT 
                AVG(TIMESTAMPDIFF(MINUTE, wo.started_at, wo.completed_at)) as avg_duration,
                COUNT(*) as completed_today,
                AVG(CASE 
                    WHEN wo.estimated_duration > 0 AND wo.completed_at IS NOT NULL 
                    THEN (wo.estimated_duration / TIMESTAMPDIFF(MINUTE, wo.started_at, wo.completed_at)) * 100
                    ELSE 100 
                END) as efficiency_rate
            FROM work_orders wo
            WHERE DATE(wo.completed_at) = %s
            AND wo.status = 'completed'
            AND wo.started_at IS NOT NULL
        """, (today,))
        
        performance_data = cursor.fetchone()
        avg_duration = performance_data['avg_duration'] or 0
        efficiency_rate = min(100, performance_data['efficiency_rate'] or 75)  # Cap à 100%
        
        # Formater le temps moyen
        if avg_duration > 0:
            hours = int(avg_duration // 60)
            minutes = int(avg_duration % 60)
            avg_time = f"{hours}h{minutes:02d}" if hours > 0 else f"{minutes}min"
        else:
            avg_time = "N/A"
        
        # Top performers (techniciens avec le plus d'interventions terminées aujourd'hui)
        cursor.execute("""
            SELECT 
                t.id,
                t.name,
                t.firstname,
                COUNT(wo.id) as completed_today,
                AVG(TIMESTAMPDIFF(MINUTE, wo.started_at, wo.completed_at)) as avg_time
            FROM technicians t
            JOIN work_orders wo ON t.id = wo.assigned_technician_id
            WHERE DATE(wo.completed_at) = %s
            AND wo.status = 'completed'
            AND wo.started_at IS NOT NULL
            GROUP BY t.id, t.name, t.firstname
            ORDER BY completed_today DESC, avg_time ASC
            LIMIT 5
        """, (today,))
        
        top_performers_raw = cursor.fetchall()
        top_performers = []
        
        for performer in top_performers_raw:
            name = f"{performer['firstname'] or ''} {performer['name'] or ''}".strip()
            initials = ''.join([n[0].upper() for n in name.split() if n])[:2] or '??'
            
            top_performers.append({
                'id': performer['id'],
                'name': name or 'Technicien Inconnu',
                'initials': initials,
                'completed_today': performer['completed_today'],
                'avg_time': performer['avg_time']
            })
        
        # Calculer le score de performance global
        if efficiency_rate >= 90:
            performance = min(100, efficiency_rate)
        elif efficiency_rate >= 70:
            performance = efficiency_rate
        else:
            performance = max(50, efficiency_rate)  # Minimum 50%
        
        result = {
            'active_technicians': active_technicians,
            'active_interventions': active_interventions,
            'average_performance': round(performance, 1),
            'average_time': avg_time,
            'efficiency_rate': round(efficiency_rate, 1),
            'top_performers': top_performers,
            'last_updated': datetime.now().isoformat()
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(result)
        
    except mysql.connector.Error as e:
        print(f"❌ Erreur base de données KPI techniciens: {e}")
        return jsonify({
            'error': 'Erreur base de données',
            'active_technicians': 0,
            'active_interventions': 0,
            'average_performance': 0,
            'average_time': 'N/A',
            'efficiency_rate': 0,
            'top_performers': [],
            'last_updated': datetime.now().isoformat()
        }), 500
        
    except Exception as e:
        print(f"❌ Erreur inattendue KPI techniciens: {e}")
        return jsonify({
            'error': 'Erreur serveur',
            'active_technicians': 0,
            'active_interventions': 0,
            'average_performance': 0,
            'average_time': 'N/A',
            'efficiency_rate': 0,
            'top_performers': [],
            'last_updated': datetime.now().isoformat()
        }), 500

@technicians_api.route('/status', methods=['GET'])
def get_technicians_status():
    """Retourne le statut de tous les techniciens"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                t.id,
                t.name,
                t.firstname,
                t.status,
                t.specialization,
                COUNT(wo.id) as active_work_orders,
                us.last_activity
            FROM technicians t
            LEFT JOIN work_orders wo ON t.id = wo.assigned_technician_id 
                AND wo.status IN ('assigned', 'in_progress')
            LEFT JOIN user_sessions us ON t.user_id = us.user_id
            GROUP BY t.id, t.name, t.firstname, t.status, t.specialization, us.last_activity
            ORDER BY t.name, t.firstname
        """)
        
        technicians = cursor.fetchall()
        
        # Formater les données
        formatted_technicians = []
        for tech in technicians:
            # Déterminer le statut réel basé sur l'activité
            last_activity = tech['last_activity']
            is_online = last_activity and (datetime.now() - last_activity) < timedelta(hours=2)
            
            status = tech['status']
            if not is_online and status == 'active':
                status = 'offline'
            
            formatted_technicians.append({
                'id': tech['id'],
                'name': f"{tech['firstname'] or ''} {tech['name'] or ''}".strip(),
                'status': status,
                'specialization': tech['specialization'],
                'active_work_orders': tech['active_work_orders'],
                'is_online': is_online,
                'last_activity': last_activity.isoformat() if last_activity else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'technicians': formatted_technicians,
            'total_count': len(formatted_technicians),
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Erreur récupération statut techniciens: {e}")
        return jsonify({
            'error': 'Erreur serveur',
            'technicians': [],
            'total_count': 0,
            'last_updated': datetime.now().isoformat()
        }), 500

def register_technicians_api(app):
    """Enregistre le blueprint des APIs techniciens"""
    app.register_blueprint(technicians_api)
    print("✅ APIs techniciens enregistrées")
