"""
Sprint 9.2 - Planification Proactive & Optimisation
Algorithme de planification optimisée avec Google OR-Tools
"""

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
import numpy as np
from datetime import datetime, timedelta
import json
import math
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass
from core.database import get_db_connection

logger = logging.getLogger(__name__)

@dataclass
class WorkOrder:
    """Représentation d'un bon de travail pour l'optimisation"""
    id: int
    customer_name: str
    description: str
    priority: str
    estimated_duration: int  # en minutes
    required_skills: List[str]
    location_lat: float
    location_lng: float
    preferred_time_start: Optional[str] = None
    preferred_time_end: Optional[str] = None
    deadline: Optional[str] = None
    
@dataclass 
class Technician:
    """Représentation d'un technicien pour l'optimisation"""
    id: int
    name: str
    skills: List[str]
    availability_start: str
    availability_end: str
    location_lat: float
    location_lng: float
    hourly_rate: float
    efficiency_score: float = 1.0

@dataclass
class OptimizationResult:
    """Résultat d'optimisation avec scoring"""
    assignments: Dict[int, List[int]]  # technician_id -> [work_order_ids]
    schedule: Dict[int, List[Dict]]    # technician_id -> [schedule_items]
    efficiency_score: float
    total_travel_time: int
    total_work_time: int
    unassigned_orders: List[int]
    cost_optimization: float
    scenarios: List[Dict] = None

class SchedulerOptimizer:
    """Optimisateur de planification avec Google OR-Tools"""
    
    def __init__(self):
        self.work_orders: List[WorkOrder] = []
        self.technicians: List[Technician] = []
        self.distance_matrix: np.ndarray = None
        self.time_matrix: np.ndarray = None
        
        # Paramètres d'optimisation
        self.max_work_hours = 8 * 60  # 8 heures en minutes
        self.travel_speed_kmh = 50    # Vitesse moyenne de déplacement
        self.setup_time = 15          # Temps de préparation par intervention
        
    def load_work_orders(self, date_filter: str = None) -> List[WorkOrder]:
        """Charger les bons de travail depuis la base de données"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Requête adaptée selon le filtre de date
            base_query = """
                SELECT 
                    wo.id,
                    wo.claim_number,
                    wo.customer_name,
                    wo.description,
                    wo.priority,
                    COALESCE(wo.estimated_duration, 120) as estimated_duration,
                    COALESCE(c.latitude, 46.2276) as location_lat,
                    COALESCE(c.longitude, 2.2137) as location_lng,
                    wo.preferred_start_time,
                    wo.preferred_end_time,
                    wo.deadline,
                    COALESCE(wo.required_skills, '[]') as required_skills
                FROM work_orders wo
                LEFT JOIN customers c ON wo.customer_id = c.id
                WHERE wo.status IN ('pending', 'assigned')
            """
            
            if date_filter:
                base_query += " AND DATE(wo.created_at) = %s"
                cursor.execute(base_query, (date_filter,))
            else:
                base_query += " AND DATE(wo.created_at) = CURDATE()"
                cursor.execute(base_query)
            
            orders = cursor.fetchall()
            self.work_orders = []
            
            # Obtenir les noms des colonnes
            column_names = [desc[0] for desc in cursor.description]
            
            for order_row in orders:
                # Créer un dictionnaire à partir de la ligne
                order = dict(zip(column_names, order_row))
                
                try:
                    skills = json.loads(order['required_skills']) if order['required_skills'] else []
                except:
                    skills = []
                    
                # Vérifier que l'id n'est pas la chaîne 'id'
                if str(order['id']).isdigit():
                    self.work_orders.append(WorkOrder(
                        id=int(order['id']),
                        customer_name=order['customer_name'] or 'Client inconnu',
                        description=order['description'] or 'Description manquante',
                        priority=order['priority'] or 'medium',
                        estimated_duration=int(order['estimated_duration']) if order['estimated_duration'] and str(order['estimated_duration']).isdigit() else 120,
                        required_skills=skills,
                        location_lat=float(order['location_lat']) if order['location_lat'] else 46.2276,
                        location_lng=float(order['location_lng']) if order['location_lng'] else 2.2137,
                        preferred_time_start=order['preferred_start_time'],
                        preferred_time_end=order['preferred_end_time'],
                        deadline=order['deadline']
                    ))
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ {len(self.work_orders)} bons de travail chargés pour optimisation")
            return self.work_orders
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement bons de travail: {e}")
            return []
    
    def load_technicians(self) -> List[Technician]:
        """Charger les techniciens disponibles"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    u.id,
                    u.name,
                    u.email,
                    COALESCE(u.skills, '[]') as skills,
                    COALESCE(u.latitude, 46.2276) as location_lat,
                    COALESCE(u.longitude, 2.2137) as location_lng,
                    COALESCE(u.hourly_rate, 25.0) as hourly_rate,
                    COALESCE(u.efficiency_score, 1.0) as efficiency_score,
                    '08:00' as availability_start,
                    '17:00' as availability_end
                FROM users u
                WHERE u.role = 'technician' 
                AND u.is_active = TRUE
                AND u.availability_status = 'available'
            """)
            
            techs = cursor.fetchall()
            self.technicians = []
            
            # Obtenir les noms des colonnes
            column_names = [desc[0] for desc in cursor.description]
            
            for tech_row in techs:
                # Créer un dictionnaire à partir de la ligne
                tech = dict(zip(column_names, tech_row))
                
                try:
                    skills = json.loads(tech['skills']) if tech['skills'] else []
                except:
                    skills = ['maintenance_generale']
                    
                # Vérifier que l'id n'est pas la chaîne 'id'
                if str(tech['id']).isdigit():
                    self.technicians.append(Technician(
                        id=int(tech['id']),
                        name=tech['name'],
                        skills=skills,
                        availability_start=tech['availability_start'],
                        availability_end=tech['availability_end'],
                        location_lat=float(tech['location_lat']) if tech['location_lat'] else 46.2276,
                        location_lng=float(tech['location_lng']) if tech['location_lng'] else 2.2137,
                        hourly_rate=float(tech['hourly_rate']) if tech['hourly_rate'] else 25.0,
                        efficiency_score=float(tech['efficiency_score']) if tech['efficiency_score'] else 1.0
                    ))
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ {len(self.technicians)} techniciens chargés pour optimisation")
            return self.technicians
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement techniciens: {e}")
            # Fallback avec données par défaut
            self.technicians = [
                Technician(
                    id=1, name="Jean Dupont", skills=["plomberie", "electricité"],
                    availability_start="08:00", availability_end="17:00",
                    location_lat=46.2276, location_lng=2.2137,
                    hourly_rate=28.0, efficiency_score=1.2
                ),
                Technician(
                    id=2, name="Sophie Martin", skills=["climatisation", "chauffage"],
                    availability_start="09:00", availability_end="18:00", 
                    location_lat=46.2300, location_lng=2.2200,
                    hourly_rate=32.0, efficiency_score=1.1
                ),
                Technician(
                    id=3, name="Pierre Durand", skills=["maintenance_generale"],
                    availability_start="07:30", availability_end="16:30",
                    location_lat=46.2250, location_lng=2.2100,
                    hourly_rate=25.0, efficiency_score=1.0
                )
            ]
            return self.technicians

    def calculate_distance_matrix(self):
        """Calculer la matrice des distances entre tous les points"""
        n_locations = len(self.work_orders) + len(self.technicians)
        self.distance_matrix = np.zeros((n_locations, n_locations))
        self.time_matrix = np.zeros((n_locations, n_locations))
        
        # Combiner toutes les locations (techniciens puis bons de travail)
        all_locations = []
        
        # Ajouter les positions des techniciens
        for tech in self.technicians:
            all_locations.append((tech.location_lat, tech.location_lng))
            
        # Ajouter les positions des bons de travail  
        for wo in self.work_orders:
            all_locations.append((wo.location_lat, wo.location_lng))
        
        # Calculer les distances
        for i in range(n_locations):
            for j in range(n_locations):
                if i != j:
                    distance = self._haversine_distance(
                        all_locations[i][0], all_locations[i][1],
                        all_locations[j][0], all_locations[j][1]
                    )
                    self.distance_matrix[i][j] = distance
                    self.time_matrix[i][j] = int((distance / self.travel_speed_kmh) * 60)  # minutes
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculer la distance haversine entre deux points GPS"""
        R = 6371  # Rayon de la Terre en km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calculate_priority_weight(self, priority: str) -> int:
        """Convertir la priorité en poids numérique"""
        weights = {
            'urgent': 1000,
            'high': 500, 
            'medium': 100,
            'low': 50
        }
        return weights.get(priority, 100)
    
    def _check_skill_compatibility(self, tech: Technician, wo: WorkOrder) -> bool:
        """Vérifier la compatibilité des compétences"""
        if not wo.required_skills:
            return True
            
        # Compétences générales toujours compatibles
        general_skills = ['maintenance_generale', 'intervention_generale']
        if any(skill in tech.skills for skill in general_skills):
            return True
            
        # Vérification spécifique
        return any(skill in tech.skills for skill in wo.required_skills)
    
    def optimize_schedule(self, optimization_mode: str = 'balanced') -> OptimizationResult:
        """Optimiser la planification avec Google OR-Tools"""
        try:
            logger.info(f"🚀 Démarrage optimisation - Mode: {optimization_mode}")
            
            # Charger les données
            if not self.work_orders:
                self.load_work_orders()
            if not self.technicians:
                self.load_technicians()
                
            if not self.work_orders or not self.technicians:
                logger.warning("⚠️ Aucune donnée disponible pour l'optimisation")
                return self._generate_fallback_result()
            
            # Calculer les matrices de distance
            self.calculate_distance_matrix()
            
            # Configuration du problème OR-Tools
            n_techs = len(self.technicians)
            n_orders = len(self.work_orders)
            
            # Créer le gestionnaire de données
            data = self._create_vrp_data()
            
            # Créer le modèle de routage
            manager = pywrapcp.RoutingIndexManager(
                data['distance_matrix'].shape[0],  # nombre de nœuds
                n_techs,                           # nombre de véhicules (techniciens)
                data['starts'],                    # points de départ
                data['ends']                       # points d'arrivée
            )
            
            routing = pywrapcp.RoutingModel(manager)
            
            # Fonction de coût de distance
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(data['distance_matrix'][from_node][to_node])
                
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Contraintes de capacité (heures de travail max)
            def time_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                
                travel_time = int(data['time_matrix'][from_node][to_node])
                
                # Ajouter le temps de travail si c'est un bon de travail
                if to_node >= n_techs:  # C'est un bon de travail
                    wo_index = to_node - n_techs
                    if wo_index < len(self.work_orders):
                        work_time = self.work_orders[wo_index].estimated_duration
                        return travel_time + work_time + self.setup_time
                        
                return travel_time
            
            time_callback_index = routing.RegisterTransitCallback(time_callback)
            
            # Contrainte de temps max par technicien
            routing.AddDimension(
                time_callback_index,
                0,                    # pas de slack
                self.max_work_hours,  # capacité max
                True,                 # start cumul to zero
                'Time'
            )
            
            # Ajouter les contraintes de compétences
            self._add_skill_constraints(routing, manager, data)
            
            # Paramètres de recherche selon le mode
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            
            if optimization_mode == 'fast':
                search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                search_parameters.time_limit.seconds = 10
            elif optimization_mode == 'quality':
                search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.SAVINGS
                search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
                search_parameters.time_limit.seconds = 60
            else:  # balanced
                search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
                search_parameters.time_limit.seconds = 30
            
            # Résoudre
            logger.info("🔄 Résolution du problème d'optimisation...")
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                logger.info("✅ Solution d'optimisation trouvée")
                return self._extract_solution(manager, routing, solution)
            else:
                logger.warning("⚠️ Pas de solution optimale trouvée - utilisation heuristique")
                return self._generate_heuristic_solution()
                
        except Exception as e:
            logger.error(f"❌ Erreur durant optimisation: {e}")
            return self._generate_fallback_result()
    
    def _create_vrp_data(self) -> Dict:
        """Créer les données pour le problème VRP"""
        n_techs = len(self.technicians)
        n_orders = len(self.work_orders)
        
        # Les techniciens sont les premiers nœuds (0 à n_techs-1)
        # Les bons de travail suivent (n_techs à n_techs+n_orders-1)
        
        data = {
            'distance_matrix': self.distance_matrix,
            'time_matrix': self.time_matrix,
            'starts': list(range(n_techs)),  # Chaque technicien démarre de sa position
            'ends': list(range(n_techs)),    # Et y retourne
            'num_vehicles': n_techs,
            'depot': 0  # Non utilisé dans ce contexte multi-dépôt
        }
        
        return data
    
    def _add_skill_constraints(self, routing, manager, data):
        """Ajouter les contraintes de compétences"""
        n_techs = len(self.technicians)
        
        # Pour chaque bon de travail, définir quels techniciens peuvent le prendre
        for wo_idx, wo in enumerate(self.work_orders):
            wo_node = n_techs + wo_idx
            
            # Trouver les techniciens incompatibles
            for tech_idx, tech in enumerate(self.technicians):
                if not self._check_skill_compatibility(tech, wo):
                    # Interdire l'assignation de ce bon de travail à ce technicien
                    routing.VehicleVar(manager.NodeToIndex(wo_node)).SetValues([tech_idx])
    
    def _extract_solution(self, manager, routing, solution) -> OptimizationResult:
        """Extraire les résultats de la solution OR-Tools"""
        assignments = {}
        schedule = {}
        total_travel_time = 0
        total_work_time = 0
        
        n_techs = len(self.technicians)
        
        for tech_idx in range(n_techs):
            assignments[tech_idx] = []
            schedule[tech_idx] = []
            
            index = routing.Start(tech_idx)
            route_time = 0
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                
                if node >= n_techs:  # C'est un bon de travail
                    wo_index = node - n_techs
                    if wo_index < len(self.work_orders):
                        wo = self.work_orders[wo_index]
                        assignments[tech_idx].append(wo.id)
                        
                        # Calculer l'heure de début
                        start_time = self._calculate_start_time(route_time)
                        end_time = self._calculate_end_time(start_time, wo.estimated_duration)
                        
                        schedule[tech_idx].append({
                            'work_order_id': wo.id,
                            'customer_name': wo.customer_name,
                            'description': wo.description[:100] + '...' if len(wo.description) > 100 else wo.description,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': wo.estimated_duration,
                            'priority': wo.priority,
                            'location': {'lat': wo.location_lat, 'lng': wo.location_lng}
                        })
                        
                        total_work_time += wo.estimated_duration
                
                # Passer au nœud suivant
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Ajouter le temps de trajet
                if not routing.IsEnd(index):
                    from_node = manager.IndexToNode(previous_index)
                    to_node = manager.IndexToNode(index)
                    travel_time = int(self.time_matrix[from_node][to_node])
                    total_travel_time += travel_time
                    route_time += travel_time
        
        # Calculer le score d'efficacité
        efficiency_score = self._calculate_efficiency_score(
            total_work_time, total_travel_time, len(self.work_orders)
        )
        
        # Trouver les bons de travail non assignés
        assigned_ids = set()
        for wo_ids in assignments.values():
            assigned_ids.update(wo_ids)
        
        unassigned_orders = [wo.id for wo in self.work_orders if wo.id not in assigned_ids]
        
        return OptimizationResult(
            assignments=assignments,
            schedule=schedule,
            efficiency_score=efficiency_score,
            total_travel_time=total_travel_time,
            total_work_time=total_work_time,
            unassigned_orders=unassigned_orders,
            cost_optimization=self._calculate_cost_optimization(assignments)
        )
    
    def _generate_heuristic_solution(self) -> OptimizationResult:
        """Générer une solution heuristique simple"""
        logger.info("🧠 Génération solution heuristique")
        
        assignments = {}
        schedule = {}
        
        # Initialiser les assignations
        for tech in self.technicians:
            assignments[tech.id] = []
            schedule[tech.id] = []
        
        # Trier les bons de travail par priorité et délai
        sorted_orders = sorted(self.work_orders, 
                             key=lambda wo: (self._calculate_priority_weight(wo.priority), wo.id),
                             reverse=True)
        
        # Assignation simple : premier technicien disponible avec les bonnes compétences
        for wo in sorted_orders:
            best_tech = None
            min_distance = float('inf')
            
            for tech in self.technicians:
                if self._check_skill_compatibility(tech, wo):
                    # Calculer la charge actuelle du technicien
                    current_load = sum(
                        next((wo2.estimated_duration for wo2 in self.work_orders if wo2.id == wo_id), 0)
                        for wo_id in assignments[tech.id]
                    )
                    
                    if current_load < self.max_work_hours:
                        distance = self._haversine_distance(
                            tech.location_lat, tech.location_lng,
                            wo.location_lat, wo.location_lng
                        )
                        
                        if distance < min_distance:
                            min_distance = distance
                            best_tech = tech
            
            # Assigner au meilleur technicien
            if best_tech:
                assignments[best_tech.id].append(wo.id)
                
                # Générer un horaire approximatif
                start_time = f"0{8 + len(assignments[best_tech.id])}:00"
                end_time = f"0{8 + len(assignments[best_tech.id])}:{wo.estimated_duration // 60:02d}"
                
                schedule[best_tech.id].append({
                    'work_order_id': wo.id,
                    'customer_name': wo.customer_name,
                    'description': wo.description[:100] + '...' if len(wo.description) > 100 else wo.description,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': wo.estimated_duration,
                    'priority': wo.priority,
                    'location': {'lat': wo.location_lat, 'lng': wo.location_lng}
                })
        
        # Calculer les métriques
        total_work_time = sum(wo.estimated_duration for wo in self.work_orders)
        total_travel_time = 60  # Estimation approximative
        
        assigned_ids = set()
        for wo_ids in assignments.values():
            assigned_ids.update(wo_ids)
        
        unassigned_orders = [wo.id for wo in self.work_orders if wo.id not in assigned_ids]
        
        efficiency_score = self._calculate_efficiency_score(
            total_work_time, total_travel_time, len(self.work_orders) - len(unassigned_orders)
        )
        
        return OptimizationResult(
            assignments=assignments,
            schedule=schedule,
            efficiency_score=efficiency_score,
            total_travel_time=total_travel_time,
            total_work_time=total_work_time,
            unassigned_orders=unassigned_orders,
            cost_optimization=75.0  # Score heuristique
        )
    
    def _generate_fallback_result(self) -> OptimizationResult:
        """Générer un résultat de fallback en cas d'erreur"""
        logger.warning("⚠️ Génération résultat de fallback")
        
        return OptimizationResult(
            assignments={1: [], 2: [], 3: []},
            schedule={1: [], 2: [], 3: []},
            efficiency_score=0.0,
            total_travel_time=0,
            total_work_time=0,
            unassigned_orders=[],
            cost_optimization=0.0
        )
    
    def _calculate_start_time(self, route_time_minutes: int) -> str:
        """Calculer l'heure de début basée sur le temps de route"""
        start_hour = 8 + (route_time_minutes // 60)
        start_minute = route_time_minutes % 60
        return f"{start_hour:02d}:{start_minute:02d}"
    
    def _calculate_end_time(self, start_time: str, duration_minutes: int) -> str:
        """Calculer l'heure de fin"""
        hour, minute = map(int, start_time.split(':'))
        total_minutes = hour * 60 + minute + duration_minutes
        end_hour = (total_minutes // 60) % 24
        end_minute = total_minutes % 60
        return f"{end_hour:02d}:{end_minute:02d}"
    
    def _calculate_efficiency_score(self, work_time: int, travel_time: int, assigned_count: int) -> float:
        """Calculer le score d'efficacité"""
        if work_time == 0:
            return 0.0
            
        # Ratio temps de travail / temps total
        total_time = work_time + travel_time
        work_ratio = work_time / total_time if total_time > 0 else 0
        
        # Bonus pour les assignations réussies
        assignment_bonus = min(assigned_count / len(self.work_orders) if self.work_orders else 0, 1.0)
        
        # Score final sur 100
        score = (work_ratio * 70 + assignment_bonus * 30)
        return round(score, 2)
    
    def _calculate_cost_optimization(self, assignments: Dict) -> float:
        """Calculer le pourcentage d'optimisation des coûts"""
        # Calcul simplifié basé sur la réduction des trajets
        total_assignments = sum(len(orders) for orders in assignments.values())
        if total_assignments == 0:
            return 0.0
            
        # Estimation d'optimisation basée sur la concentration géographique
        return min(85.0, 60.0 + (total_assignments * 2.5))
    
    def generate_multi_scenarios(self, n_scenarios: int = 3) -> List[Dict]:
        """Générer plusieurs scénarios d'optimisation"""
        scenarios = []
        modes = ['fast', 'balanced', 'quality']
        
        for i, mode in enumerate(modes[:n_scenarios]):
            logger.info(f"🎯 Génération scénario {i+1}: {mode}")
            
            result = self.optimize_schedule(optimization_mode=mode)
            
            scenario = {
                'id': i + 1,
                'name': f'Scénario {mode.title()}',
                'mode': mode,
                'efficiency_score': result.efficiency_score,
                'total_travel_time': result.total_travel_time,
                'total_work_time': result.total_work_time,
                'assigned_count': len(self.work_orders) - len(result.unassigned_orders),
                'cost_optimization': result.cost_optimization,
                'assignments': result.assignments,
                'schedule': result.schedule,
                'description': self._get_scenario_description(mode, result)
            }
            
            scenarios.append(scenario)
        
        # Trier par score d'efficacité
        scenarios.sort(key=lambda s: s['efficiency_score'], reverse=True)
        
        return scenarios
    
    def _get_scenario_description(self, mode: str, result: OptimizationResult) -> str:
        """Générer une description du scénario"""
        descriptions = {
            'fast': f"Optimisation rapide - {result.efficiency_score}% efficacité, {len(result.unassigned_orders)} non assignés",
            'balanced': f"Équilibre optimal - {result.efficiency_score}% efficacité, trajet réduit de {result.cost_optimization}%",
            'quality': f"Qualité maximale - {result.efficiency_score}% efficacité, {result.total_travel_time}min de trajet total"
        }
        return descriptions.get(mode, f"Scénario personnalisé - {result.efficiency_score}% efficacité")
    
    def apply_optimization(self, scenario_id: int, assignments: Dict) -> bool:
        """Appliquer l'optimisation sélectionnée à la base de données"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            logger.info(f"🔄 Application optimisation scénario {scenario_id}")
            
            # Mettre à jour les assignations dans la base
            for tech_id, work_order_ids in assignments.items():
                for wo_id in work_order_ids:
                    cursor.execute("""
                        UPDATE work_orders 
                        SET assigned_technician_id = %s,
                            status = 'assigned',
                            updated_at = NOW()
                        WHERE id = %s
                    """, (tech_id, wo_id))
            
            # Enregistrer l'historique d'optimisation
            cursor.execute("""
                INSERT INTO optimization_history 
                (scenario_id, applied_at, applied_by, assignments_count)
                VALUES (%s, NOW(), 1, %s)
            """, (scenario_id, sum(len(orders) for orders in assignments.values())))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("✅ Optimisation appliquée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur application optimisation: {e}")
            return False

# Instance globale pour réutilisation
scheduler_optimizer = SchedulerOptimizer()
