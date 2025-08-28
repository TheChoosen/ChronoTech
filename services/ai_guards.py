"""
Services IA et Guards pour la validation des Work Orders et Interventions
Sprint 2 - Guards IA pour validation clôture
"""
import logging
from typing import Tuple, Dict, List, Optional, Any
from datetime import datetime, timedelta
import pymysql
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Résultat d'une validation avec détails"""
    is_valid: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    severity: str = 'error'  # error, warning, info

class AIGuardsService:
    """Service de validation IA pour les Work Orders et Interventions"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'chronotech'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
    
    def get_db_connection(self):
        """Connexion à la base de données"""
        return pymysql.connect(**self.db_config)
    
    def can_close_work_order(self, wo_id: int) -> ValidationResult:
        """
        Validation IA pour fermeture d'un Bon de travail
        Vérifie toutes les conditions métier obligatoires
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupération WO avec ses tâches
                cursor.execute("""
                    SELECT wo.*, 
                           COUNT(DISTINCT wot.id) as tasks_count,
                           COUNT(DISTINCT CASE WHEN wot.status = 'done' THEN wot.id END) as completed_tasks,
                           COUNT(DISTINCT CASE WHEN wot.status IN ('pending', 'assigned') THEN wot.id END) as pending_tasks,
                           COUNT(DISTINCT i.id) as interventions_count
                    FROM work_orders wo
                    LEFT JOIN work_order_tasks wot ON wo.id = wot.work_order_id
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    WHERE wo.id = %s
                    GROUP BY wo.id
                """, (wo_id,))
                
                wo_data = cursor.fetchone()
                if not wo_data:
                    return ValidationResult(False, f"Bon de travail {wo_id} non trouvé")
                
                # 1. Vérifier qu'il y a au moins une tâche complétée
                if wo_data['completed_tasks'] == 0:
                    return ValidationResult(
                        False, 
                        "Aucune tâche complétée - Impossible de fermer le bon de travail",
                        {"completed_tasks": wo_data['completed_tasks'], "total_tasks": wo_data['tasks_count']}
                    )
                
                # 2. Vérifier les heures technicien
                hours_check = self._check_technician_hours(wo_id, cursor)
                if not hours_check.is_valid:
                    return hours_check
                
                # 3. Vérifier les pièces utilisées
                parts_check = self._check_parts_usage(wo_id, cursor)
                if not parts_check.is_valid:
                    return parts_check
                
                # 4. Vérifier les notes d'intervention obligatoires
                notes_check = self._check_intervention_notes(wo_id, cursor)
                if not notes_check.is_valid:
                    return notes_check
                
                # 5. Vérifications métier spécifiques
                business_check = self._check_business_rules(wo_id, cursor)
                if not business_check.is_valid:
                    return business_check
                
                # 6. Vérifications qualité (optionnelles mais recommandées)
                quality_check = self._check_quality_requirements(wo_id, cursor)
                if quality_check.severity == 'warning':
                    logger.warning(f"WO {wo_id}: {quality_check.message}")
                
                return ValidationResult(
                    True, 
                    "Bon de travail prêt pour fermeture",
                    {
                        "completed_tasks": wo_data['completed_tasks'],
                        "total_tasks": wo_data['tasks_count'],
                        "interventions": wo_data['interventions_count']
                    }
                )
                
        except Exception as e:
            logger.error(f"Erreur validation clôture WO {wo_id}: {e}")
            return ValidationResult(False, f"Erreur technique lors de la validation: {str(e)}")
        finally:
            conn.close()
    
    def _check_technician_hours(self, wo_id: int, cursor) -> ValidationResult:
        """Vérifier que les heures technicien sont renseignées"""
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT i.id) as interventions_count,
                SUM(CASE WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                    THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at) ELSE 0 END) as total_minutes,
                COUNT(CASE WHEN i.started_at IS NULL OR i.ended_at IS NULL THEN 1 END) as incomplete_interventions
            FROM work_order_tasks wot
            JOIN interventions i ON wot.id = i.task_id
            WHERE wot.work_order_id = %s
        """, (wo_id,))
        
        hours_data = cursor.fetchone()
        
        if hours_data['interventions_count'] == 0:
            return ValidationResult(False, "Aucune intervention enregistrée")
        
        if hours_data['incomplete_interventions'] > 0:
            return ValidationResult(
                False, 
                f"{hours_data['incomplete_interventions']} intervention(s) sans heures complètes",
                {"incomplete_interventions": hours_data['incomplete_interventions']}
            )
        
        if hours_data['total_minutes'] < 15:  # Minimum 15 minutes
            return ValidationResult(
                False, 
                f"Durée totale insuffisante: {hours_data['total_minutes']} minutes (minimum 15)",
                {"total_minutes": hours_data['total_minutes']}
            )
        
        return ValidationResult(True, f"Heures validées: {hours_data['total_minutes']} minutes")
    
    def _check_parts_usage(self, wo_id: int, cursor) -> ValidationResult:
        """Vérifier que les pièces utilisées sont documentées"""
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT wop.id) as parts_count,
                SUM(wop.quantity) as total_quantity,
                COUNT(CASE WHEN wop.unit_price IS NULL OR wop.unit_price = 0 THEN 1 END) as parts_no_price
            FROM work_order_products wop
            WHERE wop.work_order_id = %s
        """, (wo_id,))
        
        parts_data = cursor.fetchone()
        
        # Vérifier s'il y a confirmation explicite "aucune pièce"
        cursor.execute("""
            SELECT COUNT(*) as no_parts_confirmed
            FROM work_order_notes won
            WHERE won.work_order_id = %s 
            AND (won.note LIKE '%aucune pièce%' OR won.note LIKE '%no parts%' OR won.note LIKE '%sans pièce%')
        """, (wo_id,))
        
        no_parts_data = cursor.fetchone()
        
        if parts_data['parts_count'] == 0 and no_parts_data['no_parts_confirmed'] == 0:
            return ValidationResult(
                False, 
                "Pièces utilisées non renseignées. Ajoutez les pièces ou confirmez 'aucune pièce utilisée'",
                {"parts_count": 0, "confirmed_no_parts": False}
            )
        
        if parts_data['parts_no_price'] > 0:
            return ValidationResult(
                False, 
                f"{parts_data['parts_no_price']} pièce(s) sans prix - Correction requise",
                {"parts_no_price": parts_data['parts_no_price']}
            )
        
        return ValidationResult(
            True, 
            f"Pièces validées: {parts_data['parts_count']} références" if parts_data['parts_count'] > 0 else "Aucune pièce confirmée"
        )
    
    def _check_intervention_notes(self, wo_id: int, cursor) -> ValidationResult:
        """Vérifier les notes d'intervention obligatoires"""
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT in_.id) as notes_count,
                COUNT(DISTINCT i.id) as interventions_count,
                COUNT(CASE WHEN CHAR_LENGTH(in_.note) < 10 THEN 1 END) as short_notes
            FROM work_order_tasks wot
            JOIN interventions i ON wot.id = i.task_id
            LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
            WHERE wot.work_order_id = %s
        """, (wo_id,))
        
        notes_data = cursor.fetchone()
        
        if notes_data['interventions_count'] == 0:
            return ValidationResult(False, "Aucune intervention trouvée")
        
        if notes_data['notes_count'] == 0:
            return ValidationResult(
                False, 
                "Aucune note d'intervention - Documentation obligatoire",
                {"notes_count": 0, "interventions_count": notes_data['interventions_count']}
            )
        
        if notes_data['short_notes'] > 0:
            return ValidationResult(
                False, 
                f"{notes_data['short_notes']} note(s) trop courte(s) - Minimum 10 caractères",
                {"short_notes": notes_data['short_notes']},
                "warning"
            )
        
        return ValidationResult(True, f"Notes validées: {notes_data['notes_count']} entrée(s)")
    
    def _check_business_rules(self, wo_id: int, cursor) -> ValidationResult:
        """Vérifications métier spécifiques"""
        # Vérifier les tâches critiques
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN wot.priority = 'urgent' AND wot.status != 'done' THEN 1 END) as urgent_pending,
                COUNT(CASE WHEN wot.task_source = 'requested' AND wot.status != 'done' THEN 1 END) as requested_pending
            FROM work_order_tasks wot
            WHERE wot.work_order_id = %s
        """, (wo_id,))
        
        business_data = cursor.fetchone()
        
        if business_data['urgent_pending'] > 0:
            return ValidationResult(
                False, 
                f"{business_data['urgent_pending']} tâche(s) urgente(s) non terminée(s)",
                {"urgent_pending": business_data['urgent_pending']}
            )
        
        if business_data['requested_pending'] > 0:
            return ValidationResult(
                False, 
                f"{business_data['requested_pending']} tâche(s) demandée(s) par le client non terminée(s)",
                {"requested_pending": business_data['requested_pending']},
                "warning"
            )
        
        return ValidationResult(True, "Règles métier respectées")
    
    def _check_quality_requirements(self, wo_id: int, cursor) -> ValidationResult:
        """Vérifications qualité optionnelles"""
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT im.id) as media_count,
                COUNT(CASE WHEN im.is_before_work = 1 THEN 1 END) as before_photos,
                COUNT(CASE WHEN im.is_after_work = 1 THEN 1 END) as after_photos
            FROM work_order_tasks wot
            JOIN interventions i ON wot.id = i.task_id
            LEFT JOIN intervention_media im ON i.id = im.intervention_id
            WHERE wot.work_order_id = %s
        """, (wo_id,))
        
        quality_data = cursor.fetchone()
        
        warnings = []
        if quality_data['before_photos'] == 0:
            warnings.append("Aucune photo avant intervention")
        if quality_data['after_photos'] == 0:
            warnings.append("Aucune photo après intervention")
        
        if warnings:
            return ValidationResult(
                True, 
                f"Recommandations qualité: {', '.join(warnings)}",
                quality_data,
                "warning"
            )
        
        return ValidationResult(True, "Exigences qualité respectées", quality_data)
    
    def can_start_intervention(self, wo_id: int, task_id: int, technician_id: int) -> ValidationResult:
        """Validation pour démarrage d'intervention"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Vérifier cohérence WO/Task
                cursor.execute("""
                    SELECT wot.*, wo.status as wo_status
                    FROM work_order_tasks wot
                    JOIN work_orders wo ON wot.work_order_id = wo.id
                    WHERE wot.id = %s AND wot.work_order_id = %s
                """, (task_id, wo_id))
                
                task = cursor.fetchone()
                if not task:
                    return ValidationResult(False, f"Tâche {task_id} n'appartient pas au WO {wo_id}")
                
                # Vérifier statut WO
                if task['wo_status'] in ['completed', 'closed', 'cancelled']:
                    return ValidationResult(False, f"Impossible de démarrer - WO en statut {task['wo_status']}")
                
                # Vérifier statut tâche
                if task['status'] in ['done', 'cancelled']:
                    return ValidationResult(False, f"Tâche déjà en statut {task['status']}")
                
                # Vérifier assignation
                if task['technician_id'] and task['technician_id'] != technician_id:
                    return ValidationResult(False, f"Tâche assignée à un autre technicien (ID: {task['technician_id']})")
                
                # Vérifier intervention existante
                cursor.execute("SELECT id FROM interventions WHERE task_id = %s", (task_id,))
                existing = cursor.fetchone()
                if existing:
                    return ValidationResult(False, f"Intervention déjà existante (ID: {existing['id']})")
                
                return ValidationResult(True, "Intervention peut être démarrée")
                
        except Exception as e:
            logger.error(f"Erreur validation démarrage intervention: {e}")
            return ValidationResult(False, f"Erreur technique: {str(e)}")
        finally:
            conn.close()
    
    def suggest_parts_for_task(self, task_id: int) -> List[Dict[str, Any]]:
        """Suggestions IA de pièces pour une tâche donnée"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Récupérer la tâche et son contexte
                cursor.execute("""
                    SELECT wot.*, wo.vehicle_id, wo.customer_id
                    FROM work_order_tasks wot
                    JOIN work_orders wo ON wot.work_order_id = wo.id
                    WHERE wot.id = %s
                """, (task_id,))
                
                task = cursor.fetchone()
                if not task:
                    return []
                
                # Rechercher des tâches similaires
                cursor.execute("""
                    SELECT DISTINCT wop.product_name, wop.part_number, 
                           COUNT(*) as usage_count,
                           AVG(wop.quantity) as avg_quantity,
                           AVG(wop.unit_price) as avg_price
                    FROM work_order_tasks wot_similar
                    JOIN work_orders wo_similar ON wot_similar.work_order_id = wo_similar.id
                    JOIN work_order_products wop ON wo_similar.id = wop.work_order_id
                    WHERE wot_similar.title LIKE %s
                    OR wot_similar.description LIKE %s
                    GROUP BY wop.product_name, wop.part_number
                    HAVING usage_count >= 2
                    ORDER BY usage_count DESC, avg_price ASC
                    LIMIT 10
                """, (f"%{task['title']}%", f"%{task['description']}%"))
                
                suggestions = cursor.fetchall()
                
                return [
                    {
                        'product_name': s['product_name'],
                        'part_number': s['part_number'],
                        'suggested_quantity': int(s['avg_quantity']),
                        'estimated_price': float(s['avg_price']) if s['avg_price'] else 0,
                        'confidence': min(s['usage_count'] * 0.1, 1.0),
                        'reason': f"Utilisé {s['usage_count']} fois pour des tâches similaires"
                    }
                    for s in suggestions
                ]
                
        except Exception as e:
            logger.error(f"Erreur suggestions pièces: {e}")
            return []
        finally:
            conn.close()
    
    def get_intervention_recommendations(self, task_id: int) -> Dict[str, Any]:
        """Recommandations IA pour une intervention"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Analyser tâches similaires réussies
                cursor.execute("""
                    SELECT 
                        AVG(TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)) as avg_duration,
                        COUNT(CASE WHEN i.result_status = 'rework' THEN 1 END) as rework_count,
                        COUNT(*) as total_similar,
                        GROUP_CONCAT(DISTINCT in_.note SEPARATOR '\n---\n') as sample_notes
                    FROM work_order_tasks wot
                    JOIN work_order_tasks wot_similar ON (
                        wot_similar.title LIKE CONCAT('%', SUBSTRING(wot.title, 1, 10), '%')
                        OR wot_similar.task_source = wot.task_source
                    )
                    JOIN interventions i ON wot_similar.id = i.task_id
                    LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                    WHERE wot.id = %s AND i.result_status = 'ok'
                    GROUP BY wot.id
                """, (task_id,))
                
                analysis = cursor.fetchone()
                
                recommendations = {
                    'estimated_duration_minutes': int(analysis['avg_duration']) if analysis and analysis['avg_duration'] else 60,
                    'rework_risk': 'high' if analysis and (analysis['rework_count'] / analysis['total_similar']) > 0.2 else 'low',
                    'similar_cases': analysis['total_similar'] if analysis else 0,
                    'suggested_notes': [
                        "Vérifier l'état initial avant intervention",
                        "Documenter les étapes avec photos",
                        "Tester le fonctionnement après réparation"
                    ],
                    'parts_suggestions': self.suggest_parts_for_task(task_id)
                }
                
                return recommendations
                
        except Exception as e:
            logger.error(f"Erreur recommandations intervention: {e}")
            return {'estimated_duration_minutes': 60, 'rework_risk': 'unknown', 'similar_cases': 0}
        finally:
            conn.close()


# Instance globale du service
ai_guards = AIGuardsService()
