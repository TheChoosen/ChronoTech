"""
Sprint 4 - Module d'analyse prédictive et proactive
Maintenance prévisionnelle, heatmap des interventions, eco-scoring
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import json
import uuid
from core.database import get_db_connection
from core.config import Config
import logging

logger = logging.getLogger(__name__)

class PredictiveMaintenanceEngine:
    """Moteur de prédiction de maintenance pour les véhicules"""
    
    def __init__(self):
        self.confidence_threshold = 70.0
        self.urgency_rules = {
            'critical': {'days_ahead': 7, 'confidence_min': 90},
            'high': {'days_ahead': 14, 'confidence_min': 80},
            'medium': {'days_ahead': 30, 'confidence_min': 70},
            'low': {'days_ahead': 60, 'confidence_min': 60}
        }
    
    def analyze_vehicle_health(self, vehicle_id: int) -> Dict:
        """Analyse l'état d'un véhicule et génère des prédictions"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Récupérer les données du véhicule
            cursor.execute("""
                SELECT v.*, 
                       COUNT(wo.id) as total_interventions,
                       AVG(DATEDIFF(wo.completed_at, wo.created_at)) as avg_resolution_days,
                       SUM(wo.total_cost) as total_maintenance_cost,
                       MAX(wo.completed_at) as last_intervention
                FROM vehicles v
                LEFT JOIN work_orders wo ON v.id = wo.vehicle_id 
                WHERE v.id = %s AND wo.status = 'completed'
                GROUP BY v.id
            """, (vehicle_id,))
            
            vehicle_data = cursor.fetchone()
            if not vehicle_data:
                return {'error': 'Vehicle not found'}
            
            # Calculer les prédictions basées sur l'historique
            predictions = self._calculate_predictions(vehicle_data, cursor)
            
            # Sauvegarder les nouvelles prédictions
            for prediction in predictions:
                self._save_prediction(prediction, cursor)
            
            conn.commit()
            return {
                'vehicle_id': vehicle_id,
                'predictions': predictions,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse véhicule {vehicle_id}: {e}")
            return {'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _calculate_predictions(self, vehicle_data: Dict, cursor) -> List[Dict]:
        """Calcule les prédictions basées sur l'historique"""
        predictions = []
        
        # Règles de prédiction basées sur l'âge et l'usage
        vehicle_age = datetime.now().year - (vehicle_data.get('year') or 2020)
        total_interventions = vehicle_data.get('total_interventions') or 0
        
        # Prédiction maintenance générale
        if vehicle_age > 5 or total_interventions > 10:
            next_maintenance = date.today() + timedelta(days=30)
            confidence = min(95.0, 60 + (vehicle_age * 5) + (total_interventions * 2))
            
            predictions.append({
                'vehicle_id': vehicle_data['id'],
                'prediction_type': 'maintenance',
                'predicted_date': next_maintenance,
                'confidence_score': confidence,
                'urgency_level': self._determine_urgency(30, confidence),
                'maintenance_category': 'Maintenance préventive',
                'description': f'Maintenance recommandée pour véhicule de {vehicle_age} ans avec {total_interventions} interventions',
                'predicted_cost': 450.00 + (vehicle_age * 50),
                'data_sources': json.dumps({
                    'vehicle_age': vehicle_age,
                    'total_interventions': total_interventions,
                    'last_intervention': str(vehicle_data.get('last_intervention', 'N/A'))
                }),
                'algorithm_used': 'rule_based_v1'
            })
        
        # Prédiction inspection technique
        if vehicle_age > 4:
            inspection_date = date.today() + timedelta(days=60)
            predictions.append({
                'vehicle_id': vehicle_data['id'],
                'prediction_type': 'inspection',
                'predicted_date': inspection_date,
                'confidence_score': 85.0,
                'urgency_level': 'medium',
                'maintenance_category': 'Contrôle technique',
                'description': f'Contrôle technique requis pour véhicule {vehicle_data.get("make", "")} {vehicle_data.get("model", "")}',
                'predicted_cost': 120.00,
                'data_sources': json.dumps({'vehicle_age': vehicle_age}),
                'algorithm_used': 'regulatory_compliance'
            })
        
        return predictions
    
    def _determine_urgency(self, days_ahead: int, confidence: float) -> str:
        """Détermine le niveau d'urgence basé sur les jours et la confiance"""
        for urgency, rules in self.urgency_rules.items():
            if days_ahead <= rules['days_ahead'] and confidence >= rules['confidence_min']:
                return urgency
        return 'low'
    
    def _save_prediction(self, prediction: Dict, cursor):
        """Sauvegarde une prédiction en base"""
        try:
            cursor.execute("""
                INSERT INTO vehicle_maintenance_predictions 
                (vehicle_id, prediction_type, predicted_date, confidence_score, urgency_level,
                 predicted_cost, maintenance_category, description, data_sources, algorithm_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                confidence_score = VALUES(confidence_score),
                predicted_cost = VALUES(predicted_cost),
                updated_at = CURRENT_TIMESTAMP
            """, (
                prediction['vehicle_id'],
                prediction['prediction_type'],
                prediction['predicted_date'],
                prediction['confidence_score'],
                prediction['urgency_level'],
                prediction['predicted_cost'],
                prediction['maintenance_category'],
                prediction['description'],
                prediction['data_sources'],
                prediction['algorithm_used']
            ))
        except Exception as e:
            logger.error(f"Erreur sauvegarde prédiction: {e}")

class InterventionHeatmapManager:
    """Gestionnaire de heatmap des interventions géographiques"""
    
    def __init__(self):
        self.default_radius = 5.0  # km
        self.colors = ['#00ff00', '#ffff00', '#ff8000', '#ff0000', '#800080']
    
    def generate_heatmap_data(self, date_filter: Optional[str] = None) -> Dict:
        """Génère les données pour la heatmap Google Maps"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Récupérer toutes les interventions avec coordonnées
            date_condition = ""
            params = []
            
            if date_filter:
                if date_filter == 'last_30_days':
                    date_condition = "AND wo.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
                elif date_filter == 'last_90_days':
                    date_condition = "AND wo.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)"
            
            cursor.execute(f"""
                SELECT 
                    wo.latitude,
                    wo.longitude,
                    COUNT(*) as intervention_count,
                    AVG(wo.total_cost) as avg_cost,
                    AVG(TIMESTAMPDIFF(HOUR, wo.created_at, wo.completed_at)) as avg_duration_hours,
                    wo.status,
                    c.name as customer_name
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                WHERE wo.latitude IS NOT NULL 
                AND wo.longitude IS NOT NULL
                {date_condition}
                GROUP BY wo.latitude, wo.longitude
                ORDER BY intervention_count DESC
            """, params)
            
            interventions = cursor.fetchall()
            
            # Créer des zones automatiquement
            zones = self._create_dynamic_zones(interventions, cursor)
            
            # Générer les données pour Google Maps
            heatmap_points = []
            for intervention in interventions:
                intensity = min(intervention['intervention_count'] / 10.0, 1.0)
                heatmap_points.append({
                    'lat': float(intervention['latitude']),
                    'lng': float(intervention['longitude']),
                    'weight': intensity,
                    'count': intervention['intervention_count'],
                    'avg_cost': float(intervention.get('avg_cost') or 0),
                    'customer': intervention.get('customer_name', 'N/A')
                })
            
            return {
                'heatmap_points': heatmap_points,
                'zones': zones,
                'total_interventions': len(interventions),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur génération heatmap: {e}")
            return {'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _create_dynamic_zones(self, interventions: List[Dict], cursor) -> List[Dict]:
        """Crée des zones d'intervention dynamiques"""
        zones = []
        processed_coords = set()
        
        for intervention in interventions:
            lat, lng = intervention['latitude'], intervention['longitude']
            coord_key = f"{lat}_{lng}"
            
            if coord_key in processed_coords:
                continue
            
            # Chercher les interventions proches (dans un rayon de 2km)
            nearby_interventions = [
                i for i in interventions 
                if self._calculate_distance(lat, lng, i['latitude'], i['longitude']) <= 2.0
            ]
            
            if len(nearby_interventions) >= 3:  # Zone dense
                total_count = sum(i['intervention_count'] for i in nearby_interventions)
                avg_cost = sum(i.get('avg_cost') or 0 for i in nearby_interventions) / len(nearby_interventions)
                
                # Déterminer la couleur selon l'intensité
                color_index = min(int(total_count / 5), len(self.colors) - 1)
                
                zone = {
                    'zone_name': f'Zone {len(zones) + 1}',
                    'center_latitude': lat,
                    'center_longitude': lng,
                    'radius_km': 2.0,
                    'color_hex': self.colors[color_index],
                    'intervention_count': total_count,
                    'avg_cost': avg_cost,
                    'nearby_count': len(nearby_interventions)
                }
                
                zones.append(zone)
                
                # Marquer les coordonnées comme traitées
                for ni in nearby_interventions:
                    processed_coords.add(f"{ni['latitude']}_{ni['longitude']}")
        
        return zones
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcule la distance entre deux points (approximation simple)"""
        # Formule approximative pour de petites distances
        dlat = abs(lat1 - lat2)
        dlon = abs(lon1 - lon2)
        return ((dlat ** 2 + dlon ** 2) ** 0.5) * 111  # Conversion approximative en km

class EcoScoringSystem:
    """Système de calcul d'eco-score pour les work orders"""
    
    def __init__(self):
        self.base_score = 50
        self.scoring_weights = {
            'carbon_footprint': -20,  # Négatif car plus c'est élevé, moins c'est bon
            'energy_consumption': -15,
            'travel_distance': -10,
            'recycled_materials': 15,
            'eco_friendly_materials': 20,
            'waste_reduction': 25
        }
    
    def calculate_eco_score(self, work_order_id: int) -> Dict:
        """Calcule l'eco-score d'un work order"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Récupérer les données du work order
            cursor.execute("""
                SELECT wo.*, 
                       c.latitude as customer_lat, c.longitude as customer_lng,
                       u.latitude as tech_lat, u.longitude as tech_lng
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                LEFT JOIN users u ON wo.assigned_to = u.id
                WHERE wo.id = %s
            """, (work_order_id,))
            
            work_order = cursor.fetchone()
            if not work_order:
                return {'error': 'Work order not found'}
            
            # Calculer les métriques environnementales
            eco_metrics = self._calculate_eco_metrics(work_order)
            
            # Calculer le score final
            eco_score = self._calculate_final_score(eco_metrics)
            
            # Sauvegarder en base
            self._save_eco_score(work_order_id, eco_score, eco_metrics, cursor)
            
            conn.commit()
            
            return {
                'work_order_id': work_order_id,
                'eco_score': eco_score['score'],
                'metrics': eco_metrics,
                'grade': eco_score['grade'],
                'suggestions': eco_score['suggestions']
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul eco-score {work_order_id}: {e}")
            return {'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _calculate_eco_metrics(self, work_order: Dict) -> Dict:
        """Calcule les métriques environnementales"""
        metrics = {
            'carbon_footprint_kg': 0.0,
            'energy_consumption_kwh': 0.0,
            'waste_generated_kg': 0.0,
            'recycled_materials_kg': 0.0,
            'travel_distance_km': 0.0,
            'eco_friendly_materials_used': False
        }
        
        # Calculer la distance de déplacement
        if all([work_order.get('customer_lat'), work_order.get('customer_lng'), 
                work_order.get('tech_lat'), work_order.get('tech_lng')]):
            distance = self._calculate_distance(
                work_order['customer_lat'], work_order['customer_lng'],
                work_order['tech_lat'], work_order['tech_lng']
            )
            metrics['travel_distance_km'] = distance
            metrics['carbon_footprint_kg'] = distance * 0.2  # 0.2kg CO2/km approximation
        
        # Estimer la consommation d'énergie basée sur la durée
        if work_order.get('completed_at') and work_order.get('created_at'):
            duration_hours = (work_order['completed_at'] - work_order['created_at']).total_seconds() / 3600
            metrics['energy_consumption_kwh'] = duration_hours * 2.5  # Estimation
        
        # Analyser la description pour détecter les matériaux éco
        description = (work_order.get('description') or '').lower()
        eco_keywords = ['recyclé', 'écologique', 'bio', 'durable', 'renouvelable']
        if any(keyword in description for keyword in eco_keywords):
            metrics['eco_friendly_materials_used'] = True
            metrics['recycled_materials_kg'] = 5.0  # Estimation
        
        return metrics
    
    def _calculate_final_score(self, metrics: Dict) -> Dict:
        """Calcule le score final et détermine la note"""
        score = self.base_score
        
        # Appliquer les pénalités/bonus
        score += min(metrics['carbon_footprint_kg'] * self.scoring_weights['carbon_footprint'], 0)
        score += min(metrics['energy_consumption_kwh'] * self.scoring_weights['energy_consumption'], 0)
        score += min(metrics['travel_distance_km'] * self.scoring_weights['travel_distance'], 0)
        
        # Appliquer les bonus
        score += metrics['recycled_materials_kg'] * self.scoring_weights['recycled_materials']
        if metrics['eco_friendly_materials_used']:
            score += self.scoring_weights['eco_friendly_materials']
        
        # Normaliser entre 0 et 100
        score = max(0, min(100, int(score)))
        
        # Déterminer la note
        if score >= 80:
            grade = 'A'
            suggestions = ['Excellente performance environnementale !']
        elif score >= 60:
            grade = 'B'
            suggestions = ['Bonne performance, quelques améliorations possibles']
        elif score >= 40:
            grade = 'C'
            suggestions = ['Performance moyenne, optimisations recommandées']
        else:
            grade = 'D'
            suggestions = ['Performance faible, actions correctives nécessaires']
        
        return {
            'score': score,
            'grade': grade,
            'suggestions': suggestions
        }
    
    def _save_eco_score(self, work_order_id: int, eco_score: Dict, metrics: Dict, cursor):
        """Sauvegarde l'eco-score en base"""
        try:
            green_practices = json.dumps({
                'eco_materials': metrics['eco_friendly_materials_used'],
                'recycling': metrics['recycled_materials_kg'] > 0,
                'grade': eco_score['grade']
            })
            
            cursor.execute("""
                INSERT INTO work_order_eco_scores 
                (work_order_id, eco_score, carbon_footprint_kg, energy_consumption_kwh,
                 waste_generated_kg, recycled_materials_kg, travel_distance_km,
                 eco_friendly_materials_used, green_practices_applied)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                eco_score = VALUES(eco_score),
                carbon_footprint_kg = VALUES(carbon_footprint_kg),
                energy_consumption_kwh = VALUES(energy_consumption_kwh),
                travel_distance_km = VALUES(travel_distance_km),
                updated_at = CURRENT_TIMESTAMP
            """, (
                work_order_id,
                eco_score['score'],
                metrics['carbon_footprint_kg'],
                metrics['energy_consumption_kwh'],
                metrics['waste_generated_kg'],
                metrics['recycled_materials_kg'],
                metrics['travel_distance_km'],
                metrics['eco_friendly_materials_used'],
                green_practices
            ))
        except Exception as e:
            logger.error(f"Erreur sauvegarde eco-score: {e}")
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcule la distance entre deux points"""
        dlat = abs(lat1 - lat2)
        dlon = abs(lon1 - lon2)
        return ((dlat ** 2 + dlon ** 2) ** 0.5) * 111

# Instances globales
predictive_engine = PredictiveMaintenanceEngine()
heatmap_manager = InterventionHeatmapManager()
eco_scoring = EcoScoringSystem()
