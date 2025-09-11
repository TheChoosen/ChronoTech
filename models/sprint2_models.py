from core.database import get_db_connection
"""
Modèles Sprint 2 - Work Orders Tasks et Interventions
Extension des modèles existants selon le PRD Interventions & Bons de travail
"""
import os
import pymysql
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Connexion centralisée importée de core.database,
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DB', 'chronotech'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

@dataclass
class WorkOrderTask:
    """Modèle pour les tâches de bon de travail"""
    id: Optional[int] = None
    work_order_id: int = None
    title: str = ""
    description: str = ""
    task_source: str = "requested"  # requested, suggested, preventive
    created_by: str = "operator"    # operator, ai, system
    status: str = "pending"         # pending, assigned, in_progress, done, cancelled
    priority: str = "medium"        # low, medium, high, urgent
    technician_id: Optional[int] = None
    estimated_minutes: Optional[int] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Champs calculés/jointures
    technician_name: Optional[str] = None
    work_order_title: Optional[str] = None
    customer_name: Optional[str] = None
    intervention_id: Optional[int] = None
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> 'WorkOrderTask':
        """Créer une nouvelle tâche en base"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO work_order_tasks 
                    (work_order_id, title, description, task_source, created_by, 
                     priority, technician_id, estimated_minutes, scheduled_start, scheduled_end)
                    VALUES (%(work_order_id)s, %(title)s, %(description)s, %(task_source)s, 
                           %(created_by)s, %(priority)s, %(technician_id)s, %(estimated_minutes)s,
                           %(scheduled_start)s, %(scheduled_end)s)
                """, data)
                
                task_id = cursor.lastrowid
                conn.commit()
                
                # Retourner l'objet créé
                return cls.get_by_id(task_id)
        finally:
            conn.close()
    
    @classmethod
    def get_by_id(cls, task_id: int) -> Optional['WorkOrderTask']:
        """Récupérer une tâche par son ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        wot.*,
                        u.name as technician_name,
                        wo.description as work_order_title,
                        c.name as customer_name,
                        i.id as intervention_id
                    FROM work_order_tasks wot
                    LEFT JOIN users u ON wot.technician_id = u.id
                    LEFT JOIN work_orders wo ON wot.work_order_id = wo.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    WHERE wot.id = %s
                """, (task_id,))
                
                data = cursor.fetchone()
                if data:
                    return cls(**data)
                return None
        finally:
            conn.close()
    
    @classmethod
    def get_by_work_order(cls, work_order_id: int, status: Optional[str] = None) -> List['WorkOrderTask']:
        """Récupérer toutes les tâches d'un work order"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                where_clause = "WHERE wot.work_order_id = %s"
                params = [work_order_id]
                
                if status:
                    where_clause += " AND wot.status = %s"
                    params.append(status)
                
                cursor.execute(f"""
                    SELECT 
                        wot.*,
                        u.name as technician_name,
                        wo.description as work_order_title,
                        c.name as customer_name,
                        i.id as intervention_id
                    FROM work_order_tasks wot
                    LEFT JOIN users u ON wot.technician_id = u.id
                    LEFT JOIN work_orders wo ON wot.work_order_id = wo.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    {where_clause}
                    ORDER BY wot.priority DESC, wot.created_at ASC
                """, params)
                
                return [cls(**row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def update_status(self, new_status: str, user_id: int = None) -> bool:
        """Mettre à jour le statut de la tâche"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                update_data = {
                    'status': new_status,
                    'task_id': self.id
                }
                
                # Gestion des timestamps automatiques
                if new_status == 'in_progress' and not self.started_at:
                    update_data['started_at'] = datetime.now()
                elif new_status in ['done', 'cancelled'] and not self.completed_at:
                    update_data['completed_at'] = datetime.now()
                
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET status = %(status)s,
                        started_at = COALESCE(%(started_at)s, started_at),
                        completed_at = COALESCE(%(completed_at)s, completed_at),
                        updated_at = NOW()
                    WHERE id = %(task_id)s
                """, {
                    **update_data,
                    'started_at': update_data.get('started_at'),
                    'completed_at': update_data.get('completed_at')
                })
                
                conn.commit()
                self.status = new_status
                return True
        except Exception as e:
            logger.error(f"Erreur mise à jour statut tâche {self.id}: {e}")
            return False
        finally:
            conn.close()
    
    def assign_to_technician(self, technician_id: int) -> bool:
        """Assigner la tâche à un technicien"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET technician_id = %s, status = 'assigned', updated_at = NOW()
                    WHERE id = %s
                """, (technician_id, self.id))
                
                conn.commit()
                self.technician_id = technician_id
                self.status = 'assigned'
                return True
        except Exception as e:
            logger.error(f"Erreur assignation tâche {self.id}: {e}")
            return False
        finally:
            conn.close()

@dataclass
class Intervention:
    """Modèle pour les interventions (1-1 avec WorkOrderTask)"""
    id: Optional[int] = None
    work_order_id: int = None
    task_id: int = None
    technician_id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result_status: str = "ok"  # ok, rework, cancelled
    summary: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Champs calculés/jointures
    task_title: Optional[str] = None
    work_order_title: Optional[str] = None
    customer_name: Optional[str] = None
    technician_name: Optional[str] = None
    notes_count: int = 0
    media_count: int = 0
    duration_minutes: Optional[int] = None
    
    @classmethod
    def create_for_task(cls, task_id: int, technician_id: int = None) -> 'Intervention':
        """Créer une intervention pour une tâche donnée"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupérer les infos de la tâche
                cursor.execute("""
                    SELECT work_order_id FROM work_order_tasks WHERE id = %s
                """, (task_id,))
                
                task_data = cursor.fetchone()
                if not task_data:
                    raise ValueError(f"Task {task_id} not found")
                
                # Créer l'intervention
                cursor.execute("""
                    INSERT INTO interventions 
                    (work_order_id, task_id, technician_id, started_at)
                    VALUES (%s, %s, %s, NOW())
                """, (task_data['work_order_id'], task_id, technician_id))
                
                intervention_id = cursor.lastrowid
                
                # Mettre à jour le statut de la tâche
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET status = 'in_progress', started_at = NOW()
                    WHERE id = %s
                """, (task_id,))
                
                conn.commit()
                return cls.get_by_id(intervention_id)
        finally:
            conn.close()
    
    @classmethod
    def get_by_id(cls, intervention_id: int) -> Optional['Intervention']:
        """Récupérer une intervention par son ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        i.*,
                        wot.title as task_title,
                        wo.description as work_order_title,
                        c.name as customer_name,
                        u.name as technician_name,
                        COUNT(DISTINCT in_.id) as notes_count,
                        COUNT(DISTINCT im.id) as media_count,
                        TIMESTAMPDIFF(MINUTE, i.started_at, COALESCE(i.ended_at, NOW())) as duration_minutes
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    JOIN work_orders wo ON i.work_order_id = wo.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN users u ON i.technician_id = u.id
                    LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                    LEFT JOIN intervention_media im ON i.id = im.intervention_id
                    WHERE i.id = %s
                    GROUP BY i.id
                """, (intervention_id,))
                
                data = cursor.fetchone()
                if data:
                    return cls(**data)
                return None
        finally:
            conn.close()
    
    @classmethod
    def get_by_technician(cls, technician_id: int, active_only: bool = False) -> List['Intervention']:
        """Récupérer les interventions d'un technicien"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                where_clause = "WHERE i.technician_id = %s"
                params = [technician_id]
                
                if active_only:
                    where_clause += " AND i.ended_at IS NULL"
                
                cursor.execute(f"""
                    SELECT 
                        i.*,
                        wot.title as task_title,
                        wo.description as work_order_title,
                        c.name as customer_name,
                        u.name as technician_name,
                        COUNT(DISTINCT in_.id) as notes_count,
                        COUNT(DISTINCT im.id) as media_count,
                        TIMESTAMPDIFF(MINUTE, i.started_at, COALESCE(i.ended_at, NOW())) as duration_minutes
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    JOIN work_orders wo ON i.work_order_id = wo.id
                    LEFT JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN users u ON i.technician_id = u.id
                    LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                    LEFT JOIN intervention_media im ON i.id = im.intervention_id
                    {where_clause}
                    GROUP BY i.id
                    ORDER BY i.started_at DESC
                """, params)
                
                return [cls(**row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def add_note(self, content: str, author_id: int) -> bool:
        """Ajouter une note à l'intervention"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO intervention_notes 
                    (intervention_id, author_user_id, note)
                    VALUES (%s, %s, %s)
                """, (self.id, author_id, content))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Erreur ajout note intervention {self.id}: {e}")
            return False
        finally:
            conn.close()
    
    def end_intervention(self, result_status: str = "ok", summary: str = "") -> bool:
        """Terminer l'intervention"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE interventions 
                    SET ended_at = NOW(), result_status = %s, summary = %s
                    WHERE id = %s
                """, (result_status, summary, self.id))
                
                # Mettre à jour le statut de la tâche
                cursor.execute("""
                    UPDATE work_order_tasks 
                    SET status = 'done', completed_at = NOW()
                    WHERE id = %s
                """, (self.task_id,))
                
                conn.commit()
                self.ended_at = datetime.now()
                self.result_status = result_status
                self.summary = summary
                return True
        except Exception as e:
            logger.error(f"Erreur fin intervention {self.id}: {e}")
            return False
        finally:
            conn.close()
    
    def get_notes(self) -> List[Dict[str, Any]]:
        """Récupérer toutes les notes de l'intervention"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT in_.*, u.name as author_name
                    FROM intervention_notes in_
                    JOIN users u ON in_.author_user_id = u.id
                    WHERE in_.intervention_id = %s
                    ORDER BY in_.created_at DESC
                """, (self.id,))
                
                return cursor.fetchall()
        finally:
            conn.close()
    
    def get_media(self) -> List[Dict[str, Any]]:
        """Récupérer tous les médias de l'intervention"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM intervention_media
                    WHERE intervention_id = %s
                    ORDER BY created_at DESC
                """, (self.id,))
                
                return cursor.fetchall()
        finally:
            conn.close()

class WorkOrderTaskManager:
    """Gestionnaire pour les opérations complexes sur les tâches"""
    
    @staticmethod
    def get_dashboard_data(technician_id: int = None) -> Dict[str, Any]:
        """Récupérer les données du tableau de bord"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Filtre par technicien si spécifié
                where_tech = ""
                params = []
                if technician_id:
                    where_tech = "AND (wot.technician_id = %s OR wo.assigned_technician_id = %s)"
                    params = [technician_id, technician_id]
                
                # Statistiques des tâches
                cursor.execute(f"""
                    SELECT 
                        wot.status,
                        COUNT(*) as count,
                        AVG(TIMESTAMPDIFF(MINUTE, wot.started_at, wot.completed_at)) as avg_duration_minutes
                    FROM work_order_tasks wot
                    JOIN work_orders wo ON wot.work_order_id = wo.id
                    WHERE 1=1 {where_tech}
                    GROUP BY wot.status
                """, params)
                
                task_stats = {row['status']: row for row in cursor.fetchall()}
                
                # Tâches urgentes
                cursor.execute(f"""
                    SELECT COUNT(*) as urgent_tasks
                    FROM work_order_tasks wot
                    JOIN work_orders wo ON wot.work_order_id = wo.id
                    WHERE wot.priority = 'urgent' 
                      AND wot.status NOT IN ('done', 'cancelled')
                      {where_tech}
                """, params)
                
                urgent_data = cursor.fetchone()
                
                # Interventions actives
                cursor.execute(f"""
                    SELECT COUNT(*) as active_interventions
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    JOIN work_orders wo ON wot.work_order_id = wo.id
                    WHERE i.ended_at IS NULL
                      {where_tech}
                """, params)
                
                active_interventions = cursor.fetchone()
                
                return {
                    'task_stats': task_stats,
                    'urgent_tasks': urgent_data['urgent_tasks'],
                    'active_interventions': active_interventions['active_interventions']
                }
        finally:
            conn.close()
    
    @staticmethod
    def get_technician_workload(technician_id: int) -> Dict[str, Any]:
        """Récupérer la charge de travail d'un technicien"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN wot.status = 'assigned' THEN 1 END) as assigned_tasks,
                        COUNT(CASE WHEN wot.status = 'in_progress' THEN 1 END) as active_tasks,
                        SUM(CASE WHEN wot.status = 'assigned' THEN wot.estimated_minutes ELSE 0 END) as estimated_workload_minutes,
                        COUNT(CASE WHEN i.ended_at IS NULL THEN 1 END) as active_interventions
                    FROM work_order_tasks wot
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    WHERE wot.technician_id = %s
                """, (technician_id,))
                
                return cursor.fetchone()
        finally:
            conn.close()
