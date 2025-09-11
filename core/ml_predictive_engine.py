"""
Sprint 9.1 - Maintenance Prédictive 2.0
Moteur ML supervisé avec données télématiques IoT et auto-génération préventive
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from core.database import get_db_connection
import asyncio
import logging

logger = logging.getLogger(__name__)

class MLPredictiveEngine:
    """Moteur ML avancé pour maintenance prédictive 2.0"""
    
    def __init__(self):
        self.maintenance_model = None
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'mileage', 'engine_hours', 'usage_intensity', 'last_maintenance_days',
            'avg_daily_usage', 'temperature_avg', 'vibration_level', 
            'oil_pressure', 'brake_wear_level', 'tire_wear_level'
        ]
        self.models_loaded = False
        self.prediction_cache = {}
        
    def load_or_train_models(self) -> bool:
        """Charge les modèles ou les entraîne si nécessaire"""
        try:
            # Tentative de chargement des modèles existants
            try:
                self.maintenance_model = joblib.load('ai/models/maintenance_predictor.pkl')
                self.anomaly_detector = joblib.load('ai/models/anomaly_detector.pkl')
                self.scaler = joblib.load('ai/models/feature_scaler.pkl')
                self.models_loaded = True
                logger.info("✅ Modèles ML maintenance chargés avec succès")
                return True
            except FileNotFoundError:
                logger.info("🔄 Modèles introuvables, entraînement en cours...")
                return self._train_new_models()
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement modèles ML: {e}")
            return False
    
    def _train_new_models(self) -> bool:
        """Entraîne de nouveaux modèles ML"""
        try:
            # Récupérer les données d'entraînement
            training_data = self._get_training_data()
            if training_data.empty:
                logger.warning("⚠️ Pas de données d'entraînement, utilisation modèle par défaut")
                return self._create_default_models()
            
            # Préparer les features et targets
            X = training_data[self.feature_columns].fillna(0)
            y_maintenance = training_data['days_to_next_maintenance']
            
            # Normalisation des features
            X_scaled = self.scaler.fit_transform(X)
            
            # Division train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_maintenance, test_size=0.2, random_state=42
            )
            
            # Entraînement modèle de maintenance
            self.maintenance_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.maintenance_model.fit(X_train, y_train)
            
            # Validation
            y_pred = self.maintenance_model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            logger.info(f"✅ Modèle maintenance entraîné - MAE: {mae:.2f} jours, R²: {r2:.3f}")
            
            # Entraînement détecteur d'anomalies
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            self.anomaly_detector.fit(X_scaled)
            
            # Sauvegarde des modèles
            self._save_models()
            self.models_loaded = True
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur entraînement modèles: {e}")
            return self._create_default_models()
    
    def _get_training_data(self) -> pd.DataFrame:
        """Récupère les données d'entraînement depuis la base"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Requête pour récupérer l'historique de maintenance avec télématique
            cursor.execute("""
                SELECT 
                    v.id as vehicle_id,
                    v.mileage,
                    COALESCE(v.mileage / 1000, 100) as engine_hours,
                    COALESCE(wom.completed_date, DATE_SUB(NOW(), INTERVAL 90 DAY)) as last_maintenance_date,
                    COALESCE(DATEDIFF(wom.scheduled_date, NOW()), 30) as days_to_next_maintenance,
                    
                    -- Données télématiques (simulées si pas disponibles)
                    COALESCE(vt.usage_intensity, RAND() * 10) as usage_intensity,
                    COALESCE(vt.avg_daily_usage, v.mileage / GREATEST(DATEDIFF(NOW(), v.created_at), 1)) as avg_daily_usage,
                    COALESCE(vt.temperature_avg, 20 + RAND() * 30) as temperature_avg,
                    COALESCE(vt.vibration_level, RAND() * 5) as vibration_level,
                    COALESCE(vt.oil_pressure, 30 + RAND() * 20) as oil_pressure,
                    COALESCE(vt.brake_wear_level, RAND() * 100) as brake_wear_level,
                    COALESCE(vt.tire_wear_level, RAND() * 100) as tire_wear_level,
                    
                    COALESCE(DATEDIFF(NOW(), wom.completed_date), 90) as last_maintenance_days
                    
                FROM vehicles v
                LEFT JOIN vehicle_telemetry vt ON v.id = vt.vehicle_id 
                    AND vt.recorded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                LEFT JOIN work_orders wom ON v.id = wom.vehicle_id 
                    AND wom.type IN ('maintenance', 'preventive')
                    AND wom.status = 'completed'
                WHERE v.id IS NOT NULL 
                ORDER BY v.id, wom.completed_date DESC, vt.recorded_at DESC
            """)
            
            data = cursor.fetchall()
            cursor.close()
            connection.close()
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Agrégation par véhicule (prendre les données les plus récentes)
            df_agg = df.groupby('vehicle_id').agg({
                'mileage': 'last',
                'engine_hours': 'last', 
                'usage_intensity': 'mean',
                'avg_daily_usage': 'mean',
                'temperature_avg': 'mean',
                'vibration_level': 'mean',
                'oil_pressure': 'mean',
                'brake_wear_level': 'last',
                'tire_wear_level': 'last',
                'last_maintenance_days': 'last',
                'days_to_next_maintenance': 'last'
            }).reset_index()
            
            # Filtrer les valeurs aberrantes
            df_clean = df_agg[
                (df_agg['days_to_next_maintenance'] > 0) &
                (df_agg['days_to_next_maintenance'] < 365) &
                (df_agg['mileage'] > 0)
            ]
            
            logger.info(f"📊 Données d'entraînement: {len(df_clean)} véhicules")
            return df_clean
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération données training: {e}")
            return pd.DataFrame()
    
    def _create_default_models(self) -> bool:
        """Crée des modèles par défaut si pas de données"""
        try:
            # Modèle par défaut basé sur des règles heuristiques
            self.maintenance_model = None  # Utiliser règles heuristiques
            self.anomaly_detector = None
            self.models_loaded = True
            logger.info("⚠️ Modèles par défaut créés (règles heuristiques)")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur création modèles par défaut: {e}")
            return False
    
    def predict_maintenance_needs(self, vehicle_id: int) -> Dict[str, Any]:
        """Prédit les besoins de maintenance d'un véhicule"""
        try:
            if not self.models_loaded:
                self.load_or_train_models()
            
            # Récupérer les données du véhicule
            vehicle_data = self._get_vehicle_current_data(vehicle_id)
            if not vehicle_data:
                return {'error': 'Données véhicule introuvables'}
            
            # Prédiction avec ML si modèle disponible
            if self.maintenance_model is not None:
                prediction = self._ml_prediction(vehicle_data)
            else:
                prediction = self._heuristic_prediction(vehicle_data)
            
            # Classification du risque
            risk_level = self._classify_risk_level(prediction['days_to_maintenance'])
            
            # Génération recommandations
            recommendations = self._generate_recommendations(vehicle_data, prediction, risk_level)
            
            result = {
                'vehicle_id': vehicle_id,
                'prediction': prediction,
                'risk_level': risk_level,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat(),
                'model_type': 'ml' if self.maintenance_model else 'heuristic'
            }
            
            # Cache la prédiction
            self.prediction_cache[vehicle_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur prédiction maintenance véhicule {vehicle_id}: {e}")
            return {'error': str(e)}
    
    def _get_vehicle_current_data(self, vehicle_id: int) -> Optional[Dict]:
        """Récupère les données actuelles d'un véhicule"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT 
                    v.*,
                    COALESCE(DATEDIFF(NOW(), wom.completed_date), 90) as last_maintenance_days,
                    COALESCE(DATEDIFF(wom.scheduled_date, NOW()), 30) as scheduled_maintenance_days,
                    COALESCE(v.mileage / 1000, 100) as engine_hours,
                    
                    -- Données télématiques récentes
                    vt.usage_intensity,
                    vt.avg_daily_usage,
                    vt.temperature_avg,
                    vt.vibration_level,
                    vt.oil_pressure,
                    vt.brake_wear_level,
                    vt.tire_wear_level,
                    vt.recorded_at as telemetry_date
                    
                FROM vehicles v
                LEFT JOIN vehicle_telemetry vt ON v.id = vt.vehicle_id
                    AND vt.recorded_at = (
                        SELECT MAX(recorded_at) 
                        FROM vehicle_telemetry 
                        WHERE vehicle_id = v.id
                    )
                LEFT JOIN (
                    SELECT vehicle_id, 
                           MAX(completed_date) as last_maintenance_date,
                           DATE_ADD(MAX(completed_date), INTERVAL 3 MONTH) as next_maintenance_date
                    FROM work_orders 
                    WHERE type IN ('maintenance', 'preventive') AND status = 'completed'
                    GROUP BY vehicle_id
                ) wom ON v.id = wom.vehicle_id
                WHERE v.id = %s AND v.id IS NOT NULL
            """, (vehicle_id,))
            
            data = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if not data:
                return None
                
            # Compléter avec des valeurs par défaut si télématique manquante
            if not data['usage_intensity']:
                data.update({
                    'usage_intensity': 5.0,  # Moyenne
                    'avg_daily_usage': (data['mileage'] or 0) / max(365, 1),
                    'temperature_avg': 25.0,
                    'vibration_level': 2.0,
                    'oil_pressure': 40.0,
                    'brake_wear_level': 50.0,
                    'tire_wear_level': 60.0
                })
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération données véhicule {vehicle_id}: {e}")
            return None
    
    def _ml_prediction(self, vehicle_data: Dict) -> Dict[str, Any]:
        """Prédiction avec modèle ML"""
        try:
            # Préparer les features
            features = []
            for col in self.feature_columns:
                value = vehicle_data.get(col, 0)
                features.append(float(value) if value is not None else 0.0)
            
            features_array = np.array([features])
            features_scaled = self.scaler.transform(features_array)
            
            # Prédiction maintenance
            days_to_maintenance = self.maintenance_model.predict(features_scaled)[0]
            
            # Détection d'anomalies
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
            is_anomaly = self.anomaly_detector.predict(features_scaled)[0] == -1
            
            # Calcul de confiance
            confidence = min(100, max(0, (anomaly_score + 0.5) * 100))
            
            return {
                'days_to_maintenance': max(0, int(days_to_maintenance)),
                'confidence_score': round(confidence, 1),
                'anomaly_detected': bool(is_anomaly),
                'anomaly_score': round(float(anomaly_score), 3),
                'predicted_date': (datetime.now() + timedelta(days=int(days_to_maintenance))).date().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur prédiction ML: {e}")
            return self._heuristic_prediction(vehicle_data)
    
    def _heuristic_prediction(self, vehicle_data: Dict) -> Dict[str, Any]:
        """Prédiction avec règles heuristiques"""
        try:
            mileage = vehicle_data.get('mileage', 0) or 0
            last_maintenance_days = vehicle_data.get('last_maintenance_days', 0) or 0
            scheduled_days = vehicle_data.get('scheduled_maintenance_days', 30)
            
            # Règles heuristiques
            mileage_factor = min(2.0, mileage / 50000)  # Plus de kilométrage = maintenance plus fréquente
            usage_factor = vehicle_data.get('usage_intensity', 5) / 10  # Intensité d'usage
            age_factor = last_maintenance_days / 365  # Ancienneté dernière maintenance
            
            # Calcul des jours ajustés
            base_days = scheduled_days if scheduled_days > 0 else 90
            adjustment_factor = 1 - (mileage_factor * 0.3 + usage_factor * 0.2 + age_factor * 0.1)
            adjusted_days = int(base_days * max(0.1, adjustment_factor))
            
            # Détection d'anomalies simple
            brake_wear = vehicle_data.get('brake_wear_level', 50)
            tire_wear = vehicle_data.get('tire_wear_level', 50)
            oil_pressure = vehicle_data.get('oil_pressure', 40)
            
            anomaly_detected = (
                brake_wear > 80 or 
                tire_wear > 85 or 
                oil_pressure < 25 or
                last_maintenance_days > 365
            )
            
            confidence = 75.0 if not anomaly_detected else 60.0
            
            return {
                'days_to_maintenance': max(1, adjusted_days),
                'confidence_score': confidence,
                'anomaly_detected': anomaly_detected,
                'anomaly_score': -0.2 if anomaly_detected else 0.1,
                'predicted_date': (datetime.now() + timedelta(days=adjusted_days)).date().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur prédiction heuristique: {e}")
            return {
                'days_to_maintenance': 30,
                'confidence_score': 50.0,
                'anomaly_detected': False,
                'anomaly_score': 0.0,
                'predicted_date': (datetime.now() + timedelta(days=30)).date().isoformat()
            }
    
    def _classify_risk_level(self, days_to_maintenance: int) -> Dict[str, Any]:
        """Classifie le niveau de risque"""
        if days_to_maintenance <= 7:
            return {
                'level': 'critical',
                'label': 'Critique',
                'color': '#ef4444',
                'priority': 1,
                'action_required': 'Maintenance immédiate requise'
            }
        elif days_to_maintenance <= 14:
            return {
                'level': 'high',
                'label': 'Élevé', 
                'color': '#f59e0b',
                'priority': 2,
                'action_required': 'Planifier maintenance sous 2 semaines'
            }
        elif days_to_maintenance <= 30:
            return {
                'level': 'medium',
                'label': 'Moyen',
                'color': '#3b82f6',
                'priority': 3,
                'action_required': 'Maintenance à prévoir'
            }
        else:
            return {
                'level': 'low',
                'label': 'Faible',
                'color': '#10b981',
                'priority': 4,
                'action_required': 'Surveillance continue'
            }
    
    def _generate_recommendations(self, vehicle_data: Dict, prediction: Dict, risk_level: Dict) -> List[Dict]:
        """Génère des recommandations personnalisées"""
        recommendations = []
        
        # Recommandations basées sur le risque
        if risk_level['level'] == 'critical':
            recommendations.append({
                'type': 'urgent',
                'title': 'Maintenance critique requise',
                'description': f"Intervention nécessaire dans les {prediction['days_to_maintenance']} jours",
                'action': 'create_work_order_preventive',
                'priority': 1
            })
        
        # Recommandations basées sur les anomalies
        if prediction['anomaly_detected']:
            recommendations.append({
                'type': 'anomaly',
                'title': 'Anomalie détectée',
                'description': 'Comportement inhabituel nécessitant inspection',
                'action': 'schedule_inspection',
                'priority': 2
            })
        
        # Recommandations basées sur les données télématiques
        brake_wear = vehicle_data.get('brake_wear_level', 0)
        if brake_wear > 75:
            recommendations.append({
                'type': 'component',
                'title': 'Freins à surveiller',
                'description': f'Usure freins à {brake_wear}%',
                'action': 'check_brakes',
                'priority': 2
            })
        
        tire_wear = vehicle_data.get('tire_wear_level', 0)
        if tire_wear > 80:
            recommendations.append({
                'type': 'component',
                'title': 'Pneus à remplacer',
                'description': f'Usure pneus à {tire_wear}%',
                'action': 'replace_tires',
                'priority': 2
            })
        
        oil_pressure = vehicle_data.get('oil_pressure', 40)
        if oil_pressure < 30:
            recommendations.append({
                'type': 'component',
                'title': 'Pression huile faible',
                'description': f'Pression huile: {oil_pressure} PSI',
                'action': 'check_oil_system',
                'priority': 1
            })
        
        return recommendations
    
    def generate_preventive_work_order(self, vehicle_id: int, prediction_data: Dict) -> Dict[str, Any]:
        """Génère automatiquement un bon de travail préventif"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Récupérer infos véhicule
            cursor.execute("""
                SELECT v.*, c.name as customer_name 
                FROM vehicles v
                LEFT JOIN customers c ON v.customer_id = c.id
                WHERE v.id = %s
            """, (vehicle_id,))
            
            vehicle = cursor.fetchone()
            if not vehicle:
                return {'error': 'Véhicule introuvable'}
            
            # Créer le bon de travail préventif
            risk_level = prediction_data.get('risk_level', {})
            recommendations = prediction_data.get('recommendations', [])
            
            work_order_data = {
                'title': f"Maintenance préventive - {vehicle['make']} {vehicle['model']}",
                'description': self._generate_work_order_description(prediction_data, recommendations),
                'customer_id': vehicle['customer_id'],
                'vehicle_id': vehicle_id,
                'priority': risk_level.get('priority', 3),
                'status': 'pending',
                'type': 'preventive_maintenance',
                'scheduled_date': prediction_data['prediction']['predicted_date'],
                'estimated_duration': self._estimate_duration(recommendations),
                'auto_generated': True,
                'ml_prediction_id': prediction_data.get('prediction_id'),
                'created_by_ai': True
            }
            
            # Insérer le bon de travail
            cursor.execute("""
                INSERT INTO work_orders (
                    title, description, customer_id, vehicle_id, priority, 
                    status, type, scheduled_date, estimated_duration,
                    auto_generated, created_at, ml_prediction_data
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s
                )
            """, (
                work_order_data['title'],
                work_order_data['description'],
                work_order_data['customer_id'],
                work_order_data['vehicle_id'],
                work_order_data['priority'],
                work_order_data['status'],
                work_order_data['type'],
                work_order_data['scheduled_date'],
                work_order_data['estimated_duration'],
                work_order_data['auto_generated'],
                json.dumps(prediction_data)
            ))
            
            work_order_id = cursor.lastrowid
            
            # Ajouter les tâches spécifiques
            self._add_preventive_tasks(cursor, work_order_id, recommendations)
            
            connection.commit()
            cursor.close()
            connection.close()
            
            logger.info(f"✅ Bon préventif auto-généré: {work_order_id} pour véhicule {vehicle_id}")
            
            return {
                'work_order_id': work_order_id,
                'status': 'created',
                'message': 'Bon de travail préventif généré automatiquement',
                'vehicle_info': f"{vehicle['make']} {vehicle['model']}",
                'customer': vehicle['customer_name'],
                'scheduled_date': work_order_data['scheduled_date'],
                'priority': work_order_data['priority']
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur génération bon préventif: {e}")
            return {'error': str(e)}
    
    def _generate_work_order_description(self, prediction_data: Dict, recommendations: List[Dict]) -> str:
        """Génère la description du bon de travail"""
        description = "🤖 BON DE TRAVAIL PRÉVENTIF AUTO-GÉNÉRÉ\n\n"
        
        prediction = prediction_data.get('prediction', {})
        risk_level = prediction_data.get('risk_level', {})
        
        description += f"📊 ANALYSE PRÉDICTIVE:\n"
        description += f"• Maintenance prévue dans: {prediction.get('days_to_maintenance', 'N/A')} jours\n"
        description += f"• Niveau de risque: {risk_level.get('label', 'Inconnu')}\n"
        description += f"• Score de confiance: {prediction.get('confidence_score', 0)}%\n"
        
        if prediction.get('anomaly_detected'):
            description += f"⚠️ ANOMALIE DÉTECTÉE (score: {prediction.get('anomaly_score', 0)})\n"
        
        description += f"\n🔧 RECOMMANDATIONS:\n"
        for rec in recommendations:
            description += f"• {rec.get('title', '')}: {rec.get('description', '')}\n"
        
        description += f"\n📅 Généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        description += f"\n🎯 Modèle utilisé: {prediction_data.get('model_type', 'ML')}"
        
        return description
    
    def _estimate_duration(self, recommendations: List[Dict]) -> int:
        """Estime la durée nécessaire en minutes"""
        base_duration = 120  # 2h de base
        
        duration_map = {
            'check_brakes': 30,
            'replace_tires': 60,
            'check_oil_system': 45,
            'schedule_inspection': 90,
            'create_work_order_preventive': 0
        }
        
        total_duration = base_duration
        for rec in recommendations:
            action = rec.get('action', '')
            total_duration += duration_map.get(action, 30)
        
        return min(total_duration, 480)  # Max 8h
    
    def _add_preventive_tasks(self, cursor, work_order_id: int, recommendations: List[Dict]):
        """Ajoute les tâches préventives spécifiques"""
        base_tasks = [
            {'name': 'Contrôle général', 'estimated_time': 60},
            {'name': 'Vérification niveaux', 'estimated_time': 30},
            {'name': 'Test fonctionnalités', 'estimated_time': 45}
        ]
        
        # Ajouter tâches basées sur recommandations
        for rec in recommendations:
            if rec.get('action') == 'check_brakes':
                base_tasks.append({'name': 'Contrôle système de freinage', 'estimated_time': 30})
            elif rec.get('action') == 'replace_tires':
                base_tasks.append({'name': 'Remplacement pneumatiques', 'estimated_time': 60})
            elif rec.get('action') == 'check_oil_system':
                base_tasks.append({'name': 'Vérification circuit huile', 'estimated_time': 45})
        
        # Insérer les tâches
        for task in base_tasks:
            cursor.execute("""
                INSERT INTO work_order_tasks (
                    work_order_id, task_name, estimated_time, status, created_at
                ) VALUES (%s, %s, %s, 'pending', NOW())
            """, (work_order_id, task['name'], task['estimated_time']))
    
    def _save_models(self):
        """Sauvegarde les modèles entraînés"""
        try:
            import os
            os.makedirs('ai/models', exist_ok=True)
            
            if self.maintenance_model:
                joblib.dump(self.maintenance_model, 'ai/models/maintenance_predictor.pkl')
            if self.anomaly_detector:
                joblib.dump(self.anomaly_detector, 'ai/models/anomaly_detector.pkl')
            joblib.dump(self.scaler, 'ai/models/feature_scaler.pkl')
            
            logger.info("✅ Modèles ML sauvegardés")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde modèles: {e}")
    
    def get_fleet_predictions(self, limit: int = 50) -> List[Dict]:
        """Récupère les prédictions pour toute la flotte"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT id, make, model, license_plate, mileage
                FROM vehicles 
                WHERE id IS NOT NULL 
                ORDER BY created_at ASC
                LIMIT %s
            """, (limit,))
            
            vehicles = cursor.fetchall()
            cursor.close()
            connection.close()
            
            predictions = []
            for vehicle in vehicles[:10]:  # Limiter pour éviter surcharge
                prediction = self.predict_maintenance_needs(vehicle['id'])
                if 'error' not in prediction:
                    prediction['vehicle_info'] = {
                        'make': vehicle['make'],
                        'model': vehicle['model'],
                        'license_plate': vehicle['license_plate'],
                        'mileage': vehicle['mileage']
                    }
                    predictions.append(prediction)
            
            # Trier par urgence
            predictions.sort(key=lambda x: x['prediction']['days_to_maintenance'])
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Erreur prédictions flotte: {e}")
            return []

# Instance globale
ml_predictive_engine = MLPredictiveEngine()
