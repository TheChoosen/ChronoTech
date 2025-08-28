"""
Modèles de données pour ChronoTech
Classes pour représenter les entités de l'application
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from .database import db_manager
import logging

logger = logging.getLogger(__name__)

class BaseModel:
    """Classe de base pour tous les modèles"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        """Convertir l'objet en dictionnaire"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """Créer un objet à partir d'un dictionnaire"""
        return cls(**data)

class User(BaseModel):
    """Modèle pour les utilisateurs"""
    
    def __init__(self, id=None, name=None, email=None, password=None, role=None, 
                 created_at=None, updated_at=None, is_active=True, **kwargs):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
        self.role = role
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_active = is_active
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_id(cls, user_id):
        """Trouver un utilisateur par ID"""
        try:
            query = "SELECT * FROM users WHERE id = %s AND is_active = TRUE"
            result = db_manager.execute_query(query, (user_id,), fetch_one=True)
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de l'utilisateur {user_id}: {e}")
            return None
    
    @classmethod
    def find_by_email(cls, email):
        """Trouver un utilisateur par email"""
        try:
            query = "SELECT * FROM users WHERE email = %s AND is_active = TRUE"
            result = db_manager.execute_query(query, (email,), fetch_one=True)
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de l'utilisateur {email}: {e}")
            return None
    
    @classmethod
    def get_all(cls, role=None):
        """Récupérer tous les utilisateurs"""
        try:
            if role:
                query = "SELECT * FROM users WHERE role = %s AND is_active = TRUE ORDER BY name"
                result = db_manager.execute_query(query, (role,))
            else:
                query = "SELECT * FROM users WHERE is_active = TRUE ORDER BY name"
                result = db_manager.execute_query(query)
            
            return [cls.from_dict(user) for user in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs: {e}")
            return []
    
    def save(self):
        """Sauvegarder l'utilisateur"""
        try:
            if self.id:
                # Mise à jour
                query = """
                    UPDATE users 
                    SET name = %s, email = %s, role = %s, updated_at = NOW()
                    WHERE id = %s
                """
                params = (self.name, self.email, self.role, self.id)
                db_manager.execute_query(query, params)
            else:
                # Création
                query = """
                    INSERT INTO users (name, email, password, role, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """
                params = (self.name, self.email, self.password, self.role)
                db_manager.execute_query(query, params)
                
                # Récupérer l'ID généré
                self.id = db_manager.get_connection().insert_id()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'utilisateur: {e}")
            return False
    
    def delete(self):
        """Supprimer l'utilisateur (soft delete)"""
        try:
            query = "UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s"
            db_manager.execute_query(query, (self.id,))
            self.is_active = False
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'utilisateur: {e}")
            return False

class Customer(BaseModel):
    """Modèle pour les clients"""
    
    def __init__(self, id=None, name=None, company=None, email=None, phone=None, 
                 address=None, vehicle_info=None, created_at=None, updated_at=None, 
                 is_active=True, **kwargs):
        self.id = id
        self.name = name
        self.company = company
        self.email = email
        self.phone = phone
        self.address = address
        self.vehicle_info = vehicle_info
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_active = is_active
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_id(cls, customer_id):
        """Trouver un client par ID"""
        try:
            query = "SELECT * FROM customers WHERE id = %s AND is_active = TRUE"
            result = db_manager.execute_query(query, (customer_id,), fetch_one=True)
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du client {customer_id}: {e}")
            return None
    
    @classmethod
    def get_all(cls):
        """Récupérer tous les clients"""
        try:
            query = "SELECT * FROM customers WHERE is_active = TRUE ORDER BY name"
            result = db_manager.execute_query(query)
            return [cls.from_dict(customer) for customer in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des clients: {e}")
            return []
    
    @classmethod
    def search(cls, search_term):
        """Rechercher des clients"""
        try:
            query = """
                SELECT * FROM customers 
                WHERE is_active = TRUE 
                AND (name LIKE %s OR company LIKE %s OR email LIKE %s)
                ORDER BY name
            """
            search_pattern = f"%{search_term}%"
            result = db_manager.execute_query(query, (search_pattern, search_pattern, search_pattern))
            return [cls.from_dict(customer) for customer in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de clients: {e}")
            return []
    
    def save(self):
        """Sauvegarder le client"""
        try:
            if self.id:
                # Mise à jour
                query = """
                    UPDATE customers 
                    SET name = %s, company = %s, email = %s, phone = %s, 
                        address = %s, vehicle_info = %s, updated_at = NOW()
                    WHERE id = %s
                """
                params = (self.name, self.company, self.email, self.phone, 
                         self.address, self.vehicle_info, self.id)
                db_manager.execute_query(query, params)
            else:
                # Création
                query = """
                    INSERT INTO customers (name, company, email, phone, address, vehicle_info, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                params = (self.name, self.company, self.email, self.phone, 
                         self.address, self.vehicle_info)
                db_manager.execute_query(query, params)
                
                # Récupérer l'ID généré
                self.id = db_manager.get_connection().insert_id()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du client: {e}")
            return False


class Vehicle(BaseModel):
    """Modèle pour les véhicules liés aux clients"""
    def __init__(self, id=None, customer_id=None, make=None, model=None, year=None, vin=None, license_plate=None, notes=None, created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.customer_id = customer_id
        self.make = make
        self.model = model
        self.year = year
        self.vin = vin
        self.license_plate = license_plate
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
        super().__init__(**kwargs)

    @classmethod
    def find_by_customer(cls, customer_id):
        try:
            query = "SELECT * FROM vehicles WHERE customer_id = %s ORDER BY created_at DESC"
            result = db_manager.execute_query(query, (customer_id,))
            return [cls.from_dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des véhicules pour le client {customer_id}: {e}")
            return []

    @classmethod
    def find_by_id(cls, vehicle_id):
        try:
            query = "SELECT * FROM vehicles WHERE id = %s"
            result = db_manager.execute_query(query, (vehicle_id,), fetch_one=True)
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du véhicule {vehicle_id}: {e}")
            return None

class WorkOrder(BaseModel):
    """Modèle pour les bons de travail"""
    
    def __init__(self, id=None, claim_number=None, customer_name=None, customer_address=None,
                 customer_phone=None, description=None, priority='medium', status='pending',
                 assigned_technician_id=None, created_by_user_id=None, customer_id=None,
                 estimated_duration=None, scheduled_date=None, created_at=None, 
                 updated_at=None, **kwargs):
        self.id = id
        self.claim_number = claim_number
        self.customer_name = customer_name
        self.customer_address = customer_address
        self.customer_phone = customer_phone
        self.description = description
        self.priority = priority
        self.status = status
        self.assigned_technician_id = assigned_technician_id
        self.created_by_user_id = created_by_user_id
        self.customer_id = customer_id
        self.estimated_duration = estimated_duration
        self.scheduled_date = scheduled_date
        self.created_at = created_at
        self.updated_at = updated_at
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_id(cls, work_order_id):
        """Trouver un bon de travail par ID"""
        try:
            query = "SELECT * FROM work_orders WHERE id = %s"
            result = db_manager.execute_query(query, (work_order_id,), fetch_one=True)
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du bon de travail {work_order_id}: {e}")
            return None
    
    @classmethod
    def get_all(cls, status=None, technician_id=None, customer_id=None):
        """Récupérer tous les bons de travail avec filtres optionnels"""
        try:
            base_query = "SELECT * FROM work_orders WHERE 1=1"
            params = []
            
            if status:
                base_query += " AND status = %s"
                params.append(status)
            
            if technician_id:
                base_query += " AND assigned_technician_id = %s"
                params.append(technician_id)
            
            if customer_id:
                base_query += " AND customer_id = %s"
                params.append(customer_id)
            
            base_query += " ORDER BY created_at DESC"
            
            result = db_manager.execute_query(base_query, params if params else None)
            return [cls.from_dict(wo) for wo in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des bons de travail: {e}")
            return []
    
    @classmethod
    def search(cls, search_term):
        """Rechercher des bons de travail"""
        try:
            query = """
                SELECT * FROM work_orders 
                WHERE claim_number LIKE %s 
                   OR customer_name LIKE %s 
                   OR description LIKE %s
                ORDER BY created_at DESC
            """
            search_pattern = f"%{search_term}%"
            result = db_manager.execute_query(query, (search_pattern, search_pattern, search_pattern))
            return [cls.from_dict(wo) for wo in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de bons de travail: {e}")
            return []
    
    def save(self):
        """Sauvegarder le bon de travail"""
        try:
            if self.id:
                # Mise à jour
                query = """
                    UPDATE work_orders 
                    SET claim_number = %s, customer_name = %s, customer_address = %s,
                        customer_phone = %s, description = %s, priority = %s, status = %s,
                        assigned_technician_id = %s, customer_id = %s, estimated_duration = %s,
                        scheduled_date = %s, updated_at = NOW()
                    WHERE id = %s
                """
                params = (self.claim_number, self.customer_name, self.customer_address,
                         self.customer_phone, self.description, self.priority, self.status,
                         self.assigned_technician_id, self.customer_id, self.estimated_duration,
                         self.scheduled_date, self.id)
                db_manager.execute_query(query, params)
            else:
                # Création
                query = """
                    INSERT INTO work_orders (claim_number, customer_name, customer_address,
                                           customer_phone, description, priority, status,
                                           assigned_technician_id, created_by_user_id, customer_id,
                                           estimated_duration, scheduled_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                params = (self.claim_number, self.customer_name, self.customer_address,
                         self.customer_phone, self.description, self.priority, self.status,
                         self.assigned_technician_id, self.created_by_user_id, self.customer_id,
                         self.estimated_duration, self.scheduled_date)
                db_manager.execute_query(query, params)
                
                # Récupérer l'ID généré
                self.id = db_manager.get_connection().insert_id()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du bon de travail: {e}")
            return False
    
    def get_assigned_technician(self):
        """Récupérer le technicien assigné"""
        if self.assigned_technician_id:
            return User.find_by_id(self.assigned_technician_id)
        return None
    
    def get_customer(self):
        """Récupérer le client associé"""
        if self.customer_id:
            return Customer.find_by_id(self.customer_id)
        return None
    
    def get_lines(self):
        """Récupérer les lignes du bon de travail"""
        return WorkOrderLine.find_by_work_order_id(self.id)
    
    def get_interventions(self):
        """Récupérer les interventions associées"""
        return InterventionNote.find_by_work_order_id(self.id)

class WorkOrderLine(BaseModel):
    """Modèle pour les lignes de bon de travail"""
    
    def __init__(self, id=None, work_order_id=None, product_description=None, 
                 quantity=None, unit_price=None, total_price=None, **kwargs):
        self.id = id
        self.work_order_id = work_order_id
        self.product_description = product_description
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_work_order_id(cls, work_order_id):
        """Trouver les lignes d'un bon de travail"""
        try:
            query = "SELECT * FROM work_order_lines WHERE work_order_id = %s ORDER BY id"
            result = db_manager.execute_query(query, (work_order_id,))
            return [cls.from_dict(line) for line in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des lignes du bon de travail {work_order_id}: {e}")
            return []
    
    def save(self):
        """Sauvegarder la ligne de bon de travail"""
        try:
            if self.id:
                # Mise à jour
                query = """
                    UPDATE work_order_lines 
                    SET product_description = %s, quantity = %s, unit_price = %s, total_price = %s
                    WHERE id = %s
                """
                params = (self.product_description, self.quantity, self.unit_price, 
                         self.total_price, self.id)
                db_manager.execute_query(query, params)
            else:
                # Création
                query = """
                    INSERT INTO work_order_lines (work_order_id, product_description, quantity, unit_price, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                """
                params = (self.work_order_id, self.product_description, self.quantity, 
                         self.unit_price, self.total_price)
                db_manager.execute_query(query, params)
                
                # Récupérer l'ID généré
                self.id = db_manager.get_connection().insert_id()
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la ligne de bon de travail: {e}")
            return False

class InterventionNote(BaseModel):
    """Modèle pour les notes d'intervention"""
    
    def __init__(self, id=None, work_order_id=None, user_id=None, note_text=None,
                 note_type='private', created_at=None, **kwargs):
        self.id = id
        self.work_order_id = work_order_id
        self.user_id = user_id
        self.note_text = note_text
        self.note_type = note_type
        self.created_at = created_at
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_work_order_id(cls, work_order_id):
        """Trouver les notes d'un bon de travail"""
        try:
            query = """
                SELECT in.*, u.name as user_name 
                FROM intervention_notes in
                LEFT JOIN users u ON in.user_id = u.id
                WHERE in.work_order_id = %s 
                ORDER BY in.created_at DESC
            """
            result = db_manager.execute_query(query, (work_order_id,))
            return [cls.from_dict(note) for note in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des notes d'intervention {work_order_id}: {e}")
            return []
    
    def save(self):
        """Sauvegarder la note d'intervention"""
        try:
            query = """
                INSERT INTO intervention_notes (work_order_id, user_id, note_text, note_type, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            params = (self.work_order_id, self.user_id, self.note_text, self.note_type)
            db_manager.execute_query(query, params)
            
            # Récupérer l'ID généré
            self.id = db_manager.get_connection().insert_id()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la note d'intervention: {e}")
            return False

class InterventionMedia(BaseModel):
    """Modèle pour les médias d'intervention"""
    
    def __init__(self, id=None, work_order_id=None, user_id=None, file_name=None,
                 file_path=None, file_type=None, file_size=None, description=None,
                 created_at=None, **kwargs):
        self.id = id
        self.work_order_id = work_order_id
        self.user_id = user_id
        self.file_name = file_name
        self.file_path = file_path
        self.file_type = file_type
        self.file_size = file_size
        self.description = description
        self.created_at = created_at
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_work_order_id(cls, work_order_id):
        """Trouver les médias d'un bon de travail"""
        try:
            query = """
                SELECT im.*, u.name as user_name 
                FROM intervention_media im
                LEFT JOIN users u ON im.user_id = u.id
                WHERE im.work_order_id = %s 
                ORDER BY im.created_at DESC
            """
            result = db_manager.execute_query(query, (work_order_id,))
            return [cls.from_dict(media) for media in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des médias d'intervention {work_order_id}: {e}")
            return []
    
    def save(self):
        """Sauvegarder le média d'intervention"""
        try:
            query = """
                INSERT INTO intervention_media (work_order_id, user_id, file_name, file_path, 
                                              file_type, file_size, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = (self.work_order_id, self.user_id, self.file_name, self.file_path,
                     self.file_type, self.file_size, self.description)
            db_manager.execute_query(query, params)
            
            # Récupérer l'ID généré
            self.id = db_manager.get_connection().insert_id()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du média d'intervention: {e}")
            return False

class Notification(BaseModel):
    """Modèle pour les notifications"""
    
    def __init__(self, id=None, user_id=None, title=None, message=None, type='info',
                 is_read=False, related_id=None, related_type=None, created_at=None, **kwargs):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.message = message
        self.type = type
        self.is_read = is_read
        self.related_id = related_id
        self.related_type = related_type
        self.created_at = created_at
        super().__init__(**kwargs)
    
    @classmethod
    def find_by_user_id(cls, user_id, unread_only=False):
        """Trouver les notifications d'un utilisateur"""
        try:
            query = "SELECT * FROM notifications WHERE user_id = %s"
            params = [user_id]
            
            if unread_only:
                query += " AND is_read = FALSE"
            
            query += " ORDER BY created_at DESC"
            
            result = db_manager.execute_query(query, params)
            return [cls.from_dict(notification) for notification in result] if result else []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche des notifications de l'utilisateur {user_id}: {e}")
            return []
    
    def save(self):
        """Sauvegarder la notification"""
        try:
            query = """
                INSERT INTO notifications (user_id, title, message, type, related_id, related_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            params = (self.user_id, self.title, self.message, self.type, 
                     self.related_id, self.related_type)
            db_manager.execute_query(query, params)
            
            # Récupérer l'ID généré
            self.id = db_manager.get_connection().insert_id()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la notification: {e}")
            return False
    
    def mark_as_read(self):
        """Marquer la notification comme lue"""
        try:
            query = "UPDATE notifications SET is_read = TRUE WHERE id = %s"
            db_manager.execute_query(query, (self.id,))
            self.is_read = True
            return True
        except Exception as e:
            logger.error(f"Erreur lors du marquage de la notification comme lue: {e}")
            return False

# Fonctions helper pour les requêtes communes
def get_dashboard_stats(user_id=None, user_role=None):
    """Récupérer les statistiques pour le tableau de bord"""
    try:
        stats = {}
        
        # Statistiques générales des bons de travail
        if user_role == 'technician' and user_id:
            # Statistiques pour le technicien
            stats['my_work_orders'] = len(WorkOrder.get_all(technician_id=user_id))
            stats['my_pending'] = len(WorkOrder.get_all(status='pending', technician_id=user_id))
            stats['my_in_progress'] = len(WorkOrder.get_all(status='in_progress', technician_id=user_id))
        else:
            # Statistiques globales
            stats['total_work_orders'] = len(WorkOrder.get_all())
            stats['pending_work_orders'] = len(WorkOrder.get_all(status='pending'))
            stats['in_progress_work_orders'] = len(WorkOrder.get_all(status='in_progress'))
            stats['completed_work_orders'] = len(WorkOrder.get_all(status='completed'))
        
        # Statistiques des utilisateurs (seulement pour admin/manager)
        if user_role in ['admin', 'manager']:
            stats['total_users'] = len(User.get_all())
            stats['technicians'] = len(User.get_all(role='technician'))
        
        # Statistiques des clients
        stats['total_customers'] = len(Customer.get_all())
        
        # Notifications non lues
        if user_id:
            stats['unread_notifications'] = len(Notification.find_by_user_id(user_id, unread_only=True))
        
        return stats
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques du tableau de bord: {e}")
        return {}

def get_recent_activities(user_id=None, limit=10):
    """Récupérer les activités récentes"""
    try:
        # Pour l'instant, on retourne les bons de travail récents
        # Plus tard, on pourra ajouter une table d'activités
        recent_work_orders = WorkOrder.get_all()[:limit]
        
        activities = []
        for wo in recent_work_orders:
            activities.append({
                'type': 'work_order',
                'title': f"Bon de travail {wo.claim_number}",
                'description': wo.description[:50] + "..." if len(wo.description) > 50 else wo.description,
                'status': wo.status,
                'created_at': wo.created_at,
                'url': f"/work_orders/{wo.id}"
            })
        
        return activities
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des activités récentes: {e}")
        return []

# =====================================================
# NOUVEAUX MODÈLES SPRINT 1 - ANTI-ORPHAN ARCHITECTURE
# =====================================================

class WorkOrderTask(BaseModel):
    """
    Modèle pour les tâches de bon de travail - SPRINT 1
    Empêche par design les tâches orphelines
    """
    
    def __init__(self, id=None, work_order_id=None, title=None, description=None,
                 task_source=None, created_by='operator', status='pending', 
                 priority='medium', technician_id=None, estimated_minutes=None,
                 scheduled_start=None, scheduled_end=None, started_at=None, 
                 completed_at=None, created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.work_order_id = work_order_id  # OBLIGATOIRE - Pas d'orphelines!
        self.title = title
        self.description = description
        self.task_source = task_source  # 'requested', 'suggested', 'preventive'
        self.created_by = created_by  # 'operator', 'ai', 'system'
        self.status = status  # 'pending', 'assigned', 'in_progress', 'done', 'cancelled'
        self.priority = priority  # 'low', 'medium', 'high', 'urgent'
        self.technician_id = technician_id
        self.estimated_minutes = estimated_minutes
        self.scheduled_start = scheduled_start
        self.scheduled_end = scheduled_end
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at
        self.updated_at = updated_at
        super().__init__(**kwargs)
    
    @classmethod
    def create(cls, work_order_id, title, task_source, **kwargs):
        """
        Créer une nouvelle tâche (SPRINT 1 - sécurisée)
        work_order_id est OBLIGATOIRE
        """
        if not work_order_id:
            raise ValueError("work_order_id is required - no orphan tasks allowed")
        
        if task_source not in ['requested', 'suggested', 'preventive']:
            raise ValueError("task_source must be one of: requested, suggested, preventive")
        
        try:
            query = """
                INSERT INTO work_order_tasks 
                (work_order_id, title, description, task_source, created_by, priority)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            db_manager.execute_query(query, (
                work_order_id, title, kwargs.get('description', ''),
                task_source, kwargs.get('created_by', 'operator'),
                kwargs.get('priority', 'medium')
            ))
            
            # Récupérer la tâche créée
            return cls.get_by_id(db_manager.get_last_insert_id())
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche: {e}")
            raise
    
    @classmethod
    def get_by_work_order(cls, work_order_id):
        """Récupérer toutes les tâches d'un bon de travail"""
        try:
            query = """
                SELECT * FROM work_order_tasks 
                WHERE work_order_id = %s 
                ORDER BY created_at ASC
            """
            
            results = db_manager.execute_query(query, (work_order_id,))
            return [cls(**result) for result in results]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tâches: {e}")
            return []
    
    @classmethod
    def get_by_id(cls, task_id):
        """Récupérer une tâche par son ID"""
        try:
            query = "SELECT * FROM work_order_tasks WHERE id = %s"
            results = db_manager.execute_query(query, (task_id,))
            
            if results:
                return cls(**results[0])
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la tâche {task_id}: {e}")
            return None
    
    def update_status(self, new_status, technician_id=None):
        """Mettre à jour le statut d'une tâche"""
        try:
            update_fields = []
            params = []
            
            # Statut
            update_fields.append("status = %s")
            params.append(new_status)
            
            # Horodatage automatique selon le statut
            if new_status == 'in_progress' and not self.started_at:
                update_fields.append("started_at = NOW()")
            elif new_status == 'done' and not self.completed_at:
                update_fields.append("completed_at = NOW()")
            
            # Technicien
            if technician_id:
                update_fields.append("technician_id = %s")
                params.append(technician_id)
            
            update_fields.append("updated_at = NOW()")
            params.append(self.id)
            
            query = f"""
                UPDATE work_order_tasks 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            db_manager.execute_query(query, params)
            self.status = new_status
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut de la tâche {self.id}: {e}")
            return False

class Intervention(BaseModel):
    """
    Modèle pour les interventions - SPRINT 1
    Relation 1-1 stricte avec WorkOrderTask
    """
    
    def __init__(self, id=None, work_order_id=None, task_id=None, technician_id=None,
                 started_at=None, ended_at=None, result_status='ok', summary=None,
                 created_at=None, **kwargs):
        self.id = id
        self.work_order_id = work_order_id  # OBLIGATOIRE
        self.task_id = task_id  # OBLIGATOIRE et UNIQUE
        self.technician_id = technician_id
        self.started_at = started_at
        self.ended_at = ended_at
        self.result_status = result_status  # 'ok', 'rework', 'cancelled'
        self.summary = summary
        self.created_at = created_at
        super().__init__(**kwargs)
    
    @classmethod
    def create_from_task(cls, task_id, technician_id=None, **kwargs):
        """
        Créer une intervention à partir d'une tâche (SPRINT 1 - sécurisée)
        Vérifie la relation 1-1
        """
        try:
            # Vérifier que la tâche existe et récupérer son work_order_id
            task = WorkOrderTask.get_by_id(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # Vérifier qu'il n'y a pas déjà une intervention pour cette tâche
            existing_query = "SELECT COUNT(*) as count FROM interventions WHERE task_id = %s"
            existing_results = db_manager.execute_query(existing_query, (task_id,))
            
            if existing_results[0]['count'] > 0:
                raise ValueError(f"Task {task_id} already has an intervention (1-1 relationship)")
            
            # Créer l'intervention
            query = """
                INSERT INTO interventions 
                (work_order_id, task_id, technician_id, summary)
                VALUES (%s, %s, %s, %s)
            """
            
            db_manager.execute_query(query, (
                task.work_order_id, task_id, technician_id, 
                kwargs.get('summary', 'Intervention started')
            ))
            
            # Mettre à jour le statut de la tâche
            task.update_status('in_progress', technician_id)
            
            return cls.get_by_id(db_manager.get_last_insert_id())
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'intervention: {e}")
            raise
    
    @classmethod
    def get_by_id(cls, intervention_id):
        """Récupérer une intervention par son ID"""
        try:
            query = "SELECT * FROM interventions WHERE id = %s"
            results = db_manager.execute_query(query, (intervention_id,))
            
            if results:
                return cls(**results[0])
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'intervention {intervention_id}: {e}")
            return None
    
    @classmethod
    def get_by_work_order(cls, work_order_id):
        """Récupérer toutes les interventions d'un bon de travail"""
        try:
            query = """
                SELECT i.*, wot.title as task_title
                FROM interventions i
                JOIN work_order_tasks wot ON i.task_id = wot.id
                WHERE i.work_order_id = %s 
                ORDER BY i.created_at ASC
            """
            
            results = db_manager.execute_query(query, (work_order_id,))
            return [cls(**result) for result in results]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des interventions: {e}")
            return []

if __name__ == "__main__":
    # Tests des modèles
    print("Test des modèles ChronoTech Sprint 1")
    
    # Test de création d'un utilisateur
    user = User(name="Test User", email="test@chronotech.fr", role="technician")
    print(f"Utilisateur créé: {user.to_dict()}")
    
    # Test de récupération des bons de travail
    work_orders = WorkOrder.get_all()
    print(f"Nombre de bons de travail: {len(work_orders)}")
    
    # Test des statistiques du tableau de bord
    stats = get_dashboard_stats()
    print(f"Statistiques: {stats}")
    
    # Test SPRINT 1 - WorkOrderTask
    if work_orders:
        try:
            # Créer une tâche test
            task = WorkOrderTask.create(
                work_order_id=work_orders[0].id,
                title="Tâche test modèle",
                task_source="requested",
                description="Test du modèle WorkOrderTask"
            )
            print(f"Tâche créée: {task.to_dict()}")
            
            # Créer une intervention
            intervention = Intervention.create_from_task(
                task_id=task.id,
                summary="Test intervention modèle"
            )
            print(f"Intervention créée: {intervention.to_dict()}")
            
        except Exception as e:
            print(f"Erreur test Sprint 1: {e}")
