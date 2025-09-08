"""
ChronoTech - Système d'Annotations Visuelles Sprint 3
Outil d'annotation sur photos et pièces jointes avec canvas
"""

from flask import Blueprint, render_template, request, jsonify, session
from core.database import get_db_connection
from core.security import token_required
import base64
import json
import os
from datetime import datetime
import uuid
import logging

visual_annotations_bp = Blueprint('visual_annotations', __name__, url_prefix='/api/annotations')
logger = logging.getLogger(__name__)

@visual_annotations_bp.route('/workorder/<int:work_order_id>/photos')
@token_required
def get_photos_for_annotation(work_order_id):
    """Récupérer les photos disponibles pour annotation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                id,
                filename,
                file_path,
                file_type,
                uploaded_at,
                uploaded_by
            FROM work_order_attachments 
            WHERE work_order_id = %s 
            AND file_type LIKE 'image%'
            ORDER BY uploaded_at DESC
        """, (work_order_id,))
        
        photos = cursor.fetchall() or []
        
        # Ajouter les annotations existantes pour chaque photo
        for photo in photos:
            cursor.execute("""
                SELECT 
                    id,
                    annotation_type,
                    coordinates,
                    text_content,
                    color,
                    created_by,
                    created_at
                FROM visual_annotations 
                WHERE attachment_id = %s
                ORDER BY created_at ASC
            """, (photo['id'],))
            
            photo['annotations'] = cursor.fetchall() or []
            
            # Compter les annotations
            photo['annotation_count'] = len(photo['annotations'])
        
        return jsonify({
            'success': True,
            'photos': photos
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération photos: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@visual_annotations_bp.route('/save', methods=['POST'])
@token_required
def save_annotation():
    """Sauvegarder une annotation visuelle"""
    try:
        data = request.get_json()
        
        required_fields = ['attachment_id', 'work_order_id', 'annotation_type', 'coordinates']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Champs requis manquants'}), 400
        
        user_id = session.get('user_id')
        user_name = session.get('user_name', 'Utilisateur')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Générer un ID unique pour l'annotation
        annotation_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO visual_annotations (
                id, work_order_id, attachment_id, annotation_type,
                coordinates, text_content, color, stroke_width,
                created_by, created_by_name, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            annotation_id,
            data['work_order_id'],
            data['attachment_id'],
            data['annotation_type'],
            json.dumps(data['coordinates']),
            data.get('text_content', ''),
            data.get('color', '#ff0000'),
            data.get('stroke_width', 3),
            user_id,
            user_name,
            datetime.now()
        ))
        
        conn.commit()
        
        # Logger l'activité
        logger.info(f"Annotation sauvegardée: {annotation_id} par {user_name}")
        
        return jsonify({
            'success': True,
            'annotation_id': annotation_id,
            'message': 'Annotation sauvegardée'
        })
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde annotation: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@visual_annotations_bp.route('/delete/<annotation_id>', methods=['DELETE'])
@token_required
def delete_annotation(annotation_id):
    """Supprimer une annotation"""
    try:
        user_id = session.get('user_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Vérifier que l'utilisateur peut supprimer cette annotation
        cursor.execute("""
            SELECT created_by FROM visual_annotations 
            WHERE id = %s
        """, (annotation_id,))
        
        annotation = cursor.fetchone()
        if not annotation:
            return jsonify({'error': 'Annotation non trouvée'}), 404
        
        # Seul le créateur ou un admin peut supprimer
        user_role = session.get('role')
        if annotation['created_by'] != user_id and user_role != 'admin':
            return jsonify({'error': 'Non autorisé'}), 403
        
        cursor.execute("DELETE FROM visual_annotations WHERE id = %s", (annotation_id,))
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Annotation supprimée'
        })
        
    except Exception as e:
        logger.error(f"Erreur suppression annotation: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@visual_annotations_bp.route('/workorder/<int:work_order_id>/summary')
@token_required
def get_annotations_summary(work_order_id):
    """Résumé des annotations pour un bon de travail"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                va.annotation_type,
                COUNT(*) as count,
                MAX(va.created_at) as last_annotation
            FROM visual_annotations va
            WHERE va.work_order_id = %s
            GROUP BY va.annotation_type
        """, (work_order_id,))
        
        summary = cursor.fetchall() or []
        
        # Total annotations
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM visual_annotations 
            WHERE work_order_id = %s
        """, (work_order_id,))
        
        total_result = cursor.fetchone()
        total_annotations = total_result['total'] if total_result else 0
        
        return jsonify({
            'success': True,
            'total_annotations': total_annotations,
            'by_type': summary
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération résumé annotations: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Utilitaires pour la gestion des annotations

def get_annotation_types():
    """Types d'annotations disponibles"""
    return {
        'arrow': 'Flèche',
        'circle': 'Cercle', 
        'rectangle': 'Rectangle',
        'text': 'Texte',
        'freehand': 'Dessin libre',
        'highlight': 'Surlignage',
        'problem': 'Problème identifié',
        'solution': 'Solution proposée'
    }

class AnnotationCanvasManager:
    """Gestionnaire pour les opérations canvas côté serveur"""
    
    @staticmethod
    def validate_coordinates(coordinates):
        """Valider le format des coordonnées"""
        required_fields = ['x', 'y']
        
        if isinstance(coordinates, list):
            # Pour les dessins libres (liste de points)
            return all(
                isinstance(point, dict) and 
                all(field in point for field in required_fields)
                for point in coordinates
            )
        elif isinstance(coordinates, dict):
            # Pour les formes simples
            return all(field in coordinates for field in required_fields)
        
        return False
    
    @staticmethod
    def calculate_bounding_box(coordinates):
        """Calculer la boîte englobante d'une annotation"""
        if isinstance(coordinates, list):
            if not coordinates:
                return None
                
            x_coords = [point['x'] for point in coordinates]
            y_coords = [point['y'] for point in coordinates]
            
            return {
                'min_x': min(x_coords),
                'max_x': max(x_coords),
                'min_y': min(y_coords),
                'max_y': max(y_coords)
            }
        elif isinstance(coordinates, dict):
            return {
                'min_x': coordinates.get('x', 0),
                'max_x': coordinates.get('x', 0) + coordinates.get('width', 0),
                'min_y': coordinates.get('y', 0),
                'max_y': coordinates.get('y', 0) + coordinates.get('height', 0)
            }
        
        return None
