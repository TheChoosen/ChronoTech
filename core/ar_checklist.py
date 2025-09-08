"""
ChronoTech Sprint 2 - Prototype AR (Réalité Augmentée)
Interface AR pour checklist interventions sur tablette
"""
import json
import logging
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

class ARChecklistOverlay:
    """Gestionnaire de l'overlay AR pour les checklists d'intervention"""
    
    def __init__(self):
        self.current_checklist = None
        self.ar_markers = {}
        self.overlay_templates = self._load_overlay_templates()
        self.camera_active = False
        self.detection_confidence = 0.7
        
        # Configuration AR
        self.ar_config = {
            'marker_detection': True,
            'text_overlay': True,
            'progress_bar': True,
            'voice_feedback': True,
            'auto_validation': False
        }
        
    def _load_overlay_templates(self) -> Dict:
        """Charger les templates d'overlay AR"""
        return {
            'vehicle_inspection': {
                'title': 'Inspection Véhicule',
                'zones': [
                    {
                        'name': 'Moteur',
                        'position': (50, 100),
                        'checklist': [
                            'Niveau d\'huile',
                            'Liquide de refroidissement',
                            'Courroies',
                            'Batterie'
                        ],
                        'marker_id': 'engine_zone'
                    },
                    {
                        'name': 'Freinage',
                        'position': (300, 200),
                        'checklist': [
                            'Plaquettes avant',
                            'Plaquettes arrière',
                            'Liquide de frein',
                            'Test pédale'
                        ],
                        'marker_id': 'brake_zone'
                    },
                    {
                        'name': 'Éclairage',
                        'position': (200, 300),
                        'checklist': [
                            'Phares avant',
                            'Feux arrière',
                            'Clignotants',
                            'Feux de détresse'
                        ],
                        'marker_id': 'lights_zone'
                    }
                ]
            },
            'equipment_maintenance': {
                'title': 'Maintenance Équipement',
                'zones': [
                    {
                        'name': 'Panneau Électrique',
                        'position': (100, 150),
                        'checklist': [
                            'Vérification fusibles',
                            'Test disjoncteurs',
                            'Mesure tension',
                            'Inspection câblage'
                        ],
                        'marker_id': 'electrical_panel'
                    },
                    {
                        'name': 'Système Hydraulique',
                        'position': (400, 180),
                        'checklist': [
                            'Pression système',
                            'Niveau fluide',
                            'État des joints',
                            'Test pompe'
                        ],
                        'marker_id': 'hydraulic_system'
                    }
                ]
            }
        }
    
    def start_ar_session(self, work_order_id: int, checklist_type: str) -> Dict:
        """Démarrer une session AR pour une checklist"""
        try:
            if checklist_type not in self.overlay_templates:
                return {
                    'success': False,
                    'message': f'Type de checklist {checklist_type} non supporté'
                }
            
            self.current_checklist = {
                'work_order_id': work_order_id,
                'type': checklist_type,
                'template': self.overlay_templates[checklist_type],
                'progress': {},
                'started_at': datetime.now().isoformat(),
                'completed_items': 0,
                'total_items': self._count_checklist_items(checklist_type)
            }
            
            # Initialiser le progress pour chaque zone
            for zone in self.current_checklist['template']['zones']:
                zone_name = zone['name']
                self.current_checklist['progress'][zone_name] = {
                    'completed': [],
                    'total': len(zone['checklist']),
                    'status': 'pending'
                }
            
            self.camera_active = True
            
            return {
                'success': True,
                'message': 'Session AR démarrée',
                'checklist_id': f"ar_{work_order_id}_{checklist_type}",
                'template': self.current_checklist['template'],
                'total_items': self.current_checklist['total_items']
            }
            
        except Exception as e:
            logger.error(f"Erreur démarrage session AR: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_camera_frame(self, frame_data: str) -> Dict:
        """Traiter une frame de la caméra pour l'overlay AR"""
        try:
            if not self.current_checklist:
                return {
                    'success': False,
                    'message': 'Aucune session AR active'
                }
            
            # Décoder l'image base64
            frame = self._decode_frame(frame_data)
            if frame is None:
                return {
                    'success': False,
                    'message': 'Erreur décodage frame'
                }
            
            # Détecter les marqueurs AR (simulation)
            detected_markers = self._detect_ar_markers(frame)
            
            # Générer l'overlay
            overlay_frame = self._generate_overlay(frame, detected_markers)
            
            # Encoder le résultat
            encoded_frame = self._encode_frame(overlay_frame)
            
            return {
                'success': True,
                'frame': encoded_frame,
                'detected_markers': detected_markers,
                'overlay_info': self._get_overlay_info()
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement frame AR: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _decode_frame(self, frame_data: str) -> Optional[np.ndarray]:
        """Décoder une frame base64 en image OpenCV"""
        try:
            # Supprimer le préfixe data:image si présent
            if frame_data.startswith('data:image'):
                frame_data = frame_data.split(',')[1]
            
            # Décoder base64
            image_data = base64.b64decode(frame_data)
            
            # Convertir en array numpy
            nparr = np.frombuffer(image_data, np.uint8)
            
            # Décoder l'image
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return frame
            
        except Exception as e:
            logger.error(f"Erreur décodage frame: {e}")
            return None
    
    def _encode_frame(self, frame: np.ndarray) -> str:
        """Encoder une frame OpenCV en base64"""
        try:
            # Encoder en JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Convertir en base64
            encoded = base64.b64encode(buffer).decode('utf-8')
            
            return f"data:image/jpeg;base64,{encoded}"
            
        except Exception as e:
            logger.error(f"Erreur encodage frame: {e}")
            return ""
    
    def _detect_ar_markers(self, frame: np.ndarray) -> List[Dict]:
        """Détecter les marqueurs AR dans la frame (simulation)"""
        # Simulation de détection de marqueurs
        # En production, utiliser ArUco, AprilTag ou détection d'objets
        
        height, width = frame.shape[:2]
        detected_markers = []
        
        # Simuler la détection de différentes zones
        if self.current_checklist:
            template = self.current_checklist['template']
            
            for i, zone in enumerate(template['zones']):
                # Simulation : détecter les marqueurs selon des critères basiques
                marker_detected = self._simulate_marker_detection(frame, zone['marker_id'])
                
                if marker_detected:
                    # Position simulée du marqueur
                    x = int(width * 0.2 + (i * 0.3 * width))
                    y = int(height * 0.3 + (i * 0.2 * height))
                    
                    detected_markers.append({
                        'marker_id': zone['marker_id'],
                        'zone_name': zone['name'],
                        'position': (x, y),
                        'confidence': 0.85,
                        'checklist_items': zone['checklist']
                    })
        
        return detected_markers
    
    def _simulate_marker_detection(self, frame: np.ndarray, marker_id: str) -> bool:
        """Simuler la détection d'un marqueur spécifique"""
        # Simulation basée sur des caractéristiques de l'image
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Détection de contours comme proxy pour objets
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Si suffisamment de contours, considérer qu'on a détecté quelque chose
        significant_contours = [c for c in contours if cv2.contourArea(c) > 1000]
        
        # Simulation : marqueurs détectés si assez de contours significatifs
        return len(significant_contours) > 2
    
    def _generate_overlay(self, frame: np.ndarray, detected_markers: List[Dict]) -> np.ndarray:
        """Générer l'overlay AR sur la frame"""
        overlay_frame = frame.copy()
        
        if not self.current_checklist:
            return overlay_frame
        
        # Titre principal
        title = self.current_checklist['template']['title']
        cv2.putText(overlay_frame, title, (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
        
        # Barre de progression globale
        progress_percent = self._calculate_global_progress()
        self._draw_progress_bar(overlay_frame, 20, 60, 300, 20, progress_percent)
        
        # Overlay pour chaque marqueur détecté
        for marker in detected_markers:
            self._draw_zone_overlay(overlay_frame, marker)
        
        # Instructions vocales (texte)
        instructions = self._get_current_instructions()
        if instructions:
            self._draw_instructions_box(overlay_frame, instructions)
        
        return overlay_frame
    
    def _draw_progress_bar(self, frame: np.ndarray, x: int, y: int, width: int, height: int, percent: float):
        """Dessiner une barre de progression"""
        # Fond de la barre
        cv2.rectangle(frame, (x, y), (x + width, y + height), (64, 64, 64), -1)
        
        # Progression
        progress_width = int(width * percent / 100)
        if progress_width > 0:
            color = (0, 255, 0) if percent == 100 else (0, 165, 255)  # Vert si complet, orange sinon
            cv2.rectangle(frame, (x, y), (x + progress_width, y + height), color, -1)
        
        # Texte du pourcentage
        text = f"{percent:.1f}%"
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        text_x = x + (width - text_size[0]) // 2
        text_y = y + height - 5
        cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def _draw_zone_overlay(self, frame: np.ndarray, marker: Dict):
        """Dessiner l'overlay pour une zone détectée"""
        x, y = marker['position']
        zone_name = marker['zone_name']
        checklist_items = marker['checklist_items']
        
        # Cadre de la zone
        cv2.rectangle(frame, (x - 10, y - 30), (x + 250, y + len(checklist_items) * 25 + 10), 
                     (0, 0, 0, 128), -1)  # Fond semi-transparent
        
        # Nom de la zone
        cv2.putText(frame, zone_name, (x, y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Items de la checklist
        zone_progress = self.current_checklist['progress'].get(zone_name, {})
        completed_items = zone_progress.get('completed', [])
        
        for i, item in enumerate(checklist_items):
            item_y = y + (i * 25) + 15
            
            # Checkbox
            checkbox_color = (0, 255, 0) if item in completed_items else (128, 128, 128)
            cv2.rectangle(frame, (x, item_y - 10), (x + 15, item_y + 5), checkbox_color, -1)
            
            if item in completed_items:
                # Checkmark
                cv2.line(frame, (x + 3, item_y - 2), (x + 7, item_y + 2), (255, 255, 255), 2)
                cv2.line(frame, (x + 7, item_y + 2), (x + 12, item_y - 7), (255, 255, 255), 2)
            
            # Texte de l'item
            text_color = (200, 200, 200) if item in completed_items else (255, 255, 255)
            cv2.putText(frame, item, (x + 25, item_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
    
    def _draw_instructions_box(self, frame: np.ndarray, instructions: str):
        """Dessiner la boîte d'instructions"""
        height, width = frame.shape[:2]
        
        # Position en bas de l'écran
        box_height = 80
        box_y = height - box_height - 20
        
        # Fond de la boîte
        cv2.rectangle(frame, (20, box_y), (width - 20, height - 20), (0, 0, 0, 180), -1)
        
        # Texte des instructions
        lines = instructions.split('\n')
        for i, line in enumerate(lines):
            text_y = box_y + 25 + (i * 20)
            cv2.putText(frame, line, (30, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    def complete_checklist_item(self, zone_name: str, item_name: str) -> Dict:
        """Marquer un item de checklist comme complété"""
        try:
            if not self.current_checklist:
                return {
                    'success': False,
                    'message': 'Aucune session AR active'
                }
            
            zone_progress = self.current_checklist['progress'].get(zone_name)
            if not zone_progress:
                return {
                    'success': False,
                    'message': f'Zone {zone_name} non trouvée'
                }
            
            # Ajouter l'item aux complétés s'il n'y est pas déjà
            if item_name not in zone_progress['completed']:
                zone_progress['completed'].append(item_name)
                self.current_checklist['completed_items'] += 1
                
                # Vérifier si la zone est complète
                if len(zone_progress['completed']) == zone_progress['total']:
                    zone_progress['status'] = 'completed'
                else:
                    zone_progress['status'] = 'in_progress'
                
                # Log de l'action
                logger.info(f"✅ Item complété: {zone_name} - {item_name}")
                
                return {
                    'success': True,
                    'message': f'Item {item_name} complété',
                    'zone_progress': zone_progress,
                    'global_progress': self._calculate_global_progress()
                }
            else:
                return {
                    'success': False,
                    'message': 'Item déjà complété'
                }
                
        except Exception as e:
            logger.error(f"Erreur completion item: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_global_progress(self) -> float:
        """Calculer le pourcentage de progression global"""
        if not self.current_checklist:
            return 0.0
        
        total_items = self.current_checklist['total_items']
        completed_items = self.current_checklist['completed_items']
        
        if total_items == 0:
            return 100.0
        
        return (completed_items / total_items) * 100
    
    def _count_checklist_items(self, checklist_type: str) -> int:
        """Compter le nombre total d'items dans une checklist"""
        template = self.overlay_templates.get(checklist_type, {})
        total = 0
        
        for zone in template.get('zones', []):
            total += len(zone.get('checklist', []))
        
        return total
    
    def _get_overlay_info(self) -> Dict:
        """Récupérer les informations d'overlay actuelles"""
        if not self.current_checklist:
            return {}
        
        return {
            'checklist_type': self.current_checklist['type'],
            'global_progress': self._calculate_global_progress(),
            'zone_progress': self.current_checklist['progress'],
            'total_items': self.current_checklist['total_items'],
            'completed_items': self.current_checklist['completed_items']
        }
    
    def _get_current_instructions(self) -> Optional[str]:
        """Récupérer les instructions actuelles à afficher"""
        if not self.current_checklist:
            return None
        
        # Instructions basées sur la progression
        global_progress = self._calculate_global_progress()
        
        if global_progress == 0:
            return "Pointez la caméra vers les zones à inspecter\nDites 'complété' pour valider un item"
        elif global_progress < 50:
            return "Continuez l'inspection des zones\nUtilisez les commandes vocales pour naviguer"
        elif global_progress < 100:
            return "Presque terminé !\nVérifiez les derniers items"
        else:
            return "Inspection terminée !\nDites 'finaliser' pour clôturer"
    
    def finalize_ar_session(self) -> Dict:
        """Finaliser la session AR et générer le rapport"""
        try:
            if not self.current_checklist:
                return {
                    'success': False,
                    'message': 'Aucune session AR active'
                }
            
            # Générer le rapport final
            report = {
                'work_order_id': self.current_checklist['work_order_id'],
                'checklist_type': self.current_checklist['type'],
                'started_at': self.current_checklist['started_at'],
                'completed_at': datetime.now().isoformat(),
                'global_progress': self._calculate_global_progress(),
                'zone_details': self.current_checklist['progress'],
                'total_items': self.current_checklist['total_items'],
                'completed_items': self.current_checklist['completed_items'],
                'completion_rate': self._calculate_global_progress()
            }
            
            # Réinitialiser la session
            self.current_checklist = None
            self.camera_active = False
            
            return {
                'success': True,
                'message': 'Session AR finalisée',
                'report': report
            }
            
        except Exception as e:
            logger.error(f"Erreur finalisation session AR: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_ar_session_status(self) -> Dict:
        """Récupérer le statut de la session AR actuelle"""
        if not self.current_checklist:
            return {
                'active': False,
                'message': 'Aucune session AR active'
            }
        
        return {
            'active': True,
            'work_order_id': self.current_checklist['work_order_id'],
            'checklist_type': self.current_checklist['type'],
            'global_progress': self._calculate_global_progress(),
            'camera_active': self.camera_active,
            'started_at': self.current_checklist['started_at'],
            'zone_progress': self.current_checklist['progress']
        }
    
    def update_ar_config(self, config_updates: Dict) -> Dict:
        """Mettre à jour la configuration AR"""
        try:
            self.ar_config.update(config_updates)
            
            return {
                'success': True,
                'message': 'Configuration AR mise à jour',
                'config': self.ar_config
            }
            
        except Exception as e:
            logger.error(f"Erreur mise à jour config AR: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Instance globale du système AR
ar_overlay = ARChecklistOverlay()

# Fonction utilitaire pour les templates personnalisés
def add_custom_ar_template(template_name: str, template_config: Dict) -> bool:
    """Ajouter un template AR personnalisé"""
    try:
        ar_overlay.overlay_templates[template_name] = template_config
        logger.info(f"📱 Template AR '{template_name}' ajouté")
        return True
    except Exception as e:
        logger.error(f"Erreur ajout template AR: {e}")
        return False
