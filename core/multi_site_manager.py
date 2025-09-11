"""
Sprint 7.4 - Multi-sites & Consolidation
Vue comparative et consolidation des ateliers multiples
"""

from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import statistics
from core.database import get_db_connection

class MultiSiteManager:
    """Gestionnaire pour la vue multi-sites et consolidation"""
    
    def __init__(self):
        self.comparison_cache = {}
        self.site_metrics_cache = {}
    
    def get_comparative_dashboard(self, site_ids: List[int] = None, 
                                date_range: int = 30) -> Dict[str, Any]:
        """Vue comparative des sites/ateliers"""
        try:
            # Si aucun site spécifié, récupérer tous les sites actifs
            if not site_ids:
                site_ids = self._get_active_site_ids()
            
            comparative_data = {
                'sites_overview': [],
                'comparative_metrics': {},
                'performance_ranking': [],
                'trends_analysis': {},
                'recommendations': []
            }
            
            # Récupérer les données de chaque site
            for site_id in site_ids:
                site_data = self._get_site_comprehensive_data(site_id, date_range)
                comparative_data['sites_overview'].append(site_data)
            
            # Calculer les métriques comparatives
            comparative_data['comparative_metrics'] = self._calculate_comparative_metrics(
                comparative_data['sites_overview']
            )
            
            # Classement de performance
            comparative_data['performance_ranking'] = self._calculate_performance_ranking(
                comparative_data['sites_overview']
            )
            
            # Analyse des tendances
            comparative_data['trends_analysis'] = self._analyze_cross_site_trends(
                comparative_data['sites_overview'], date_range
            )
            
            # Recommandations d'optimisation
            comparative_data['recommendations'] = self._generate_multi_site_recommendations(
                comparative_data
            )
            
            return {
                'status': 'success',
                'data': comparative_data,
                'generated_at': datetime.now().isoformat(),
                'sites_count': len(site_ids),
                'date_range_days': date_range
            }
            
        except Exception as e:
            print(f"❌ Erreur dashboard comparatif: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de la génération du dashboard comparatif'
            }
    
    def get_consolidated_view(self, grouping: str = 'department') -> Dict[str, Any]:
        """Vue consolidée avec groupement personnalisable"""
        try:
            consolidation_data = {
                'groups': [],
                'global_metrics': {},
                'cross_group_analysis': {},
                'efficiency_opportunities': []
            }
            
            # Grouper les données selon le critère
            if grouping == 'department':
                groups = self._group_by_department()
            elif grouping == 'region':
                groups = self._group_by_region()
            elif grouping == 'team_size':
                groups = self._group_by_team_size()
            else:
                groups = self._group_by_performance()
            
            # Analyser chaque groupe
            for group in groups:
                group_analysis = self._analyze_group(group, grouping)
                consolidation_data['groups'].append(group_analysis)
            
            # Métriques globales
            consolidation_data['global_metrics'] = self._calculate_global_metrics(groups)
            
            # Analyse croisée
            consolidation_data['cross_group_analysis'] = self._perform_cross_group_analysis(
                consolidation_data['groups']
            )
            
            # Opportunités d'efficacité
            consolidation_data['efficiency_opportunities'] = self._identify_efficiency_opportunities(
                consolidation_data['groups']
            )
            
            return {
                'status': 'success',
                'data': consolidation_data,
                'grouping_criteria': grouping,
                'groups_count': len(groups),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erreur vue consolidée: {e}")
            return {
                'status': 'error',
                'message': 'Erreur lors de la consolidation'
            }
    
    def get_real_time_filters(self) -> Dict[str, Any]:
        """Filtres temps réel pour la vue multi-sites"""
        try:
            filters = {
                'sites': self._get_available_sites(),
                'departments': self._get_available_departments(),
                'regions': self._get_available_regions(),
                'time_periods': [
                    {'value': 7, 'label': '7 derniers jours'},
                    {'value': 30, 'label': '30 derniers jours'},
                    {'value': 90, 'label': '3 derniers mois'},
                    {'value': 365, 'label': '12 derniers mois'}
                ],
                'performance_metrics': [
                    {'value': 'efficiency', 'label': 'Efficacité'},
                    {'value': 'productivity', 'label': 'Productivité'},
                    {'value': 'quality', 'label': 'Qualité'},
                    {'value': 'satisfaction', 'label': 'Satisfaction client'},
                    {'value': 'eco_score', 'label': 'Score écologique'}
                ],
                'grouping_options': [
                    {'value': 'department', 'label': 'Par département'},
                    {'value': 'region', 'label': 'Par région'},
                    {'value': 'team_size', 'label': 'Par taille d\'équipe'},
                    {'value': 'performance', 'label': 'Par performance'}
                ]
            }
            
            return {
                'status': 'success',
                'filters': filters
            }
            
        except Exception as e:
            print(f"❌ Erreur filtres temps réel: {e}")
            return {
                'status': 'error',
                'filters': {}
            }
    
    def _get_active_site_ids(self) -> List[int]:
        """Récupère les IDs des sites actifs"""
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT DISTINCT site_id 
            FROM users 
            WHERE site_id IS NOT NULL AND is_active = TRUE
            ORDER BY site_id
        """)
        
        site_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        return site_ids
    
    def _get_site_comprehensive_data(self, site_id: int, date_range: int) -> Dict[str, Any]:
        """Récupère les données complètes d'un site"""
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Informations de base du site
        cursor.execute("""
            SELECT 
                s.id,
                s.name,
                s.location,
                s.department,
                s.region,
                COUNT(DISTINCT u.id) as team_size,
                COUNT(DISTINCT wo.id) as total_work_orders,
                AVG(cf.overall_satisfaction) as avg_satisfaction
            FROM sites s
            LEFT JOIN users u ON s.id = u.site_id AND u.is_active = TRUE
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                AND wo.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            LEFT JOIN client_feedback cf ON u.id = cf.technician_id
                AND cf.submitted_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            WHERE s.id = %s
            GROUP BY s.id, s.name, s.location, s.department, s.region
        """, (date_range, date_range, site_id))
        
        site_info = cursor.fetchone()
        
        if not site_info:
            cursor.close()
            connection.close()
            return {}
        
        # Métriques de performance
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN wo.status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN wo.status = 'pending' THEN 1 END) as pending_orders,
                COUNT(CASE WHEN wo.status = 'in_progress' THEN 1 END) as in_progress_orders,
                AVG(CASE WHEN wo.status = 'completed' THEN 
                    TIMESTAMPDIFF(HOUR, wo.created_at, wo.completed_at) END) as avg_completion_time,
                AVG(CASE WHEN cf.overall_satisfaction IS NOT NULL THEN cf.overall_satisfaction END) as satisfaction_score,
                COUNT(DISTINCT CASE WHEN wo.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN wo.id END) as week_activity
            FROM users u
            LEFT JOIN work_orders wo ON u.id = wo.assigned_technician_id 
                AND wo.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            LEFT JOIN client_feedback cf ON wo.id = cf.work_order_id
                AND cf.submitted_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            WHERE u.site_id = %s AND u.is_active = TRUE
        """, (date_range, date_range, site_id))
        
        performance_metrics = cursor.fetchone()
        
        # Calculs des KPIs
        efficiency_rate = 0
        if performance_metrics['completed_orders'] and site_info['total_work_orders']:
            efficiency_rate = (performance_metrics['completed_orders'] / site_info['total_work_orders']) * 100
        
        productivity_score = 0
        if site_info['team_size'] and site_info['total_work_orders']:
            productivity_score = site_info['total_work_orders'] / site_info['team_size']
        
        cursor.close()
        connection.close()
        
        return {
            'site_id': site_id,
            'site_name': site_info['name'],
            'location': site_info['location'],
            'department': site_info['department'],
            'region': site_info['region'],
            'team_size': site_info['team_size'] or 0,
            'total_work_orders': site_info['total_work_orders'] or 0,
            'completed_orders': performance_metrics['completed_orders'] or 0,
            'pending_orders': performance_metrics['pending_orders'] or 0,
            'in_progress_orders': performance_metrics['in_progress_orders'] or 0,
            'efficiency_rate': round(efficiency_rate, 1),
            'productivity_score': round(productivity_score, 1),
            'satisfaction_score': round(performance_metrics['satisfaction_score'] or 0, 1),
            'avg_completion_time': round(performance_metrics['avg_completion_time'] or 0, 1),
            'week_activity': performance_metrics['week_activity'] or 0,
            'performance_grade': self._calculate_performance_grade(efficiency_rate, productivity_score, performance_metrics['satisfaction_score'] or 0)
        }
    
    def _calculate_comparative_metrics(self, sites_data: List[Dict]) -> Dict[str, Any]:
        """Calcule les métriques comparatives entre sites"""
        if not sites_data:
            return {}
        
        metrics = {
            'efficiency_comparison': {},
            'productivity_comparison': {},
            'satisfaction_comparison': {},
            'team_size_analysis': {},
            'workload_distribution': {}
        }
        
        # Efficacité
        efficiency_rates = [site['efficiency_rate'] for site in sites_data if site['efficiency_rate']]
        if efficiency_rates:
            metrics['efficiency_comparison'] = {
                'average': round(statistics.mean(efficiency_rates), 1),
                'best': max(efficiency_rates),
                'worst': min(efficiency_rates),
                'std_deviation': round(statistics.stdev(efficiency_rates) if len(efficiency_rates) > 1 else 0, 1)
            }
        
        # Productivité
        productivity_scores = [site['productivity_score'] for site in sites_data if site['productivity_score']]
        if productivity_scores:
            metrics['productivity_comparison'] = {
                'average': round(statistics.mean(productivity_scores), 1),
                'best': max(productivity_scores),
                'worst': min(productivity_scores),
                'std_deviation': round(statistics.stdev(productivity_scores) if len(productivity_scores) > 1 else 0, 1)
            }
        
        # Satisfaction
        satisfaction_scores = [site['satisfaction_score'] for site in sites_data if site['satisfaction_score']]
        if satisfaction_scores:
            metrics['satisfaction_comparison'] = {
                'average': round(statistics.mean(satisfaction_scores), 1),
                'best': max(satisfaction_scores),
                'worst': min(satisfaction_scores),
                'std_deviation': round(statistics.stdev(satisfaction_scores) if len(satisfaction_scores) > 1 else 0, 1)
            }
        
        # Analyse taille d'équipe
        team_sizes = [site['team_size'] for site in sites_data if site['team_size']]
        if team_sizes:
            metrics['team_size_analysis'] = {
                'average': round(statistics.mean(team_sizes), 1),
                'largest': max(team_sizes),
                'smallest': min(team_sizes),
                'total_employees': sum(team_sizes)
            }
        
        # Distribution charge de travail
        total_orders = sum(site['total_work_orders'] for site in sites_data)
        if total_orders > 0:
            metrics['workload_distribution'] = {
                'total_orders': total_orders,
                'average_per_site': round(total_orders / len(sites_data), 1),
                'most_loaded_site': max(sites_data, key=lambda x: x['total_work_orders'])['site_name'],
                'least_loaded_site': min(sites_data, key=lambda x: x['total_work_orders'])['site_name']
            }
        
        return metrics
    
    def _calculate_performance_ranking(self, sites_data: List[Dict]) -> List[Dict]:
        """Calcule le classement de performance des sites"""
        # Calculer un score global pour chaque site
        for site in sites_data:
            performance_score = (
                site['efficiency_rate'] * 0.4 +
                min(site['productivity_score'] * 10, 100) * 0.3 +  # Normaliser la productivité
                site['satisfaction_score'] * 20 * 0.3  # Normaliser la satisfaction (sur 5 -> sur 100)
            )
            site['overall_performance_score'] = round(performance_score, 1)
        
        # Trier par score décroissant
        ranked_sites = sorted(sites_data, key=lambda x: x['overall_performance_score'], reverse=True)
        
        # Ajouter le rang
        for i, site in enumerate(ranked_sites, 1):
            site['rank'] = i
            if i == 1:
                site['rank_badge'] = '🥇'
            elif i == 2:
                site['rank_badge'] = '🥈'
            elif i == 3:
                site['rank_badge'] = '🥉'
            else:
                site['rank_badge'] = f"#{i}"
        
        return ranked_sites
    
    def _analyze_cross_site_trends(self, sites_data: List[Dict], date_range: int) -> Dict[str, Any]:
        """Analyse les tendances croisées entre sites"""
        trends = {
            'performance_trends': {},
            'workload_trends': {},
            'satisfaction_trends': {},
            'efficiency_patterns': {}
        }
        
        # Analyser les patterns par département
        departments = {}
        for site in sites_data:
            dept = site.get('department', 'Unknown')
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(site)
        
        # Tendances par département
        dept_analysis = {}
        for dept, dept_sites in departments.items():
            if len(dept_sites) > 1:
                avg_efficiency = statistics.mean([s['efficiency_rate'] for s in dept_sites if s['efficiency_rate']])
                avg_satisfaction = statistics.mean([s['satisfaction_score'] for s in dept_sites if s['satisfaction_score']])
                
                dept_analysis[dept] = {
                    'sites_count': len(dept_sites),
                    'avg_efficiency': round(avg_efficiency, 1),
                    'avg_satisfaction': round(avg_satisfaction, 1),
                    'consistency': 'high' if statistics.stdev([s['efficiency_rate'] for s in dept_sites if s['efficiency_rate']]) < 10 else 'low'
                }
        
        trends['performance_trends'] = dept_analysis
        
        return trends
    
    def _generate_multi_site_recommendations(self, comparative_data: Dict) -> List[Dict]:
        """Génère des recommandations multi-sites"""
        recommendations = []
        
        sites = comparative_data['sites_overview']
        metrics = comparative_data['comparative_metrics']
        
        # Recommandation sur l'efficacité
        if 'efficiency_comparison' in metrics:
            efficiency_gap = metrics['efficiency_comparison']['best'] - metrics['efficiency_comparison']['worst']
            if efficiency_gap > 20:
                recommendations.append({
                    'type': 'improvement',
                    'category': 'Efficacité',
                    'title': 'Écart d\'efficacité important détecté',
                    'description': f"Écart de {efficiency_gap:.1f}% entre le meilleur et le moins bon site. Analyser les bonnes pratiques.",
                    'priority': 'high',
                    'impact': 'high'
                })
        
        # Recommandation sur la charge de travail
        if 'workload_distribution' in metrics:
            total_orders = metrics['workload_distribution']['total_orders']
            sites_count = len(sites)
            if sites_count > 0:
                avg_per_site = total_orders / sites_count
                overloaded_sites = [s for s in sites if s['total_work_orders'] > avg_per_site * 1.5]
                underloaded_sites = [s for s in sites if s['total_work_orders'] < avg_per_site * 0.5]
                
                if overloaded_sites and underloaded_sites:
                    recommendations.append({
                        'type': 'optimization',
                        'category': 'Répartition',
                        'title': 'Déséquilibre de charge détecté',
                        'description': f"{len(overloaded_sites)} site(s) surchargé(s) et {len(underloaded_sites)} sous-chargé(s). Redistribution possible.",
                        'priority': 'medium',
                        'impact': 'medium'
                    })
        
        # Recommandation sur la satisfaction
        low_satisfaction_sites = [s for s in sites if s['satisfaction_score'] < 3.0]
        if low_satisfaction_sites:
            recommendations.append({
                'type': 'quality',
                'category': 'Satisfaction',
                'title': 'Sites avec faible satisfaction',
                'description': f"{len(low_satisfaction_sites)} site(s) avec satisfaction < 3.0. Action corrective nécessaire.",
                'priority': 'high',
                'impact': 'high'
            })
        
        return recommendations
    
    def _calculate_performance_grade(self, efficiency: float, productivity: float, satisfaction: float) -> str:
        """Calcule la note de performance d'un site"""
        score = (efficiency * 0.4 + min(productivity * 10, 100) * 0.3 + satisfaction * 20 * 0.3)
        
        if score >= 85:
            return 'A+'
        elif score >= 75:
            return 'A'
        elif score >= 65:
            return 'B+'
        elif score >= 55:
            return 'B'
        elif score >= 45:
            return 'C+'
        elif score >= 35:
            return 'C'
        else:
            return 'D'
    
    def _get_available_sites(self) -> List[Dict]:
        """Récupère la liste des sites disponibles"""
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT DISTINCT s.id, s.name, s.location, s.department, s.region
            FROM sites s
            INNER JOIN users u ON s.id = u.site_id
            WHERE u.is_active = TRUE
            ORDER BY s.name
        """)
        
        sites = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return sites
    
    def _get_available_departments(self) -> List[str]:
        """Récupère la liste des départements"""
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT DISTINCT department 
            FROM sites 
            WHERE department IS NOT NULL AND department != ''
            ORDER BY department
        """)
        
        departments = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        return departments
    
    def _get_available_regions(self) -> List[str]:
        """Récupère la liste des régions"""
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT DISTINCT region 
            FROM sites 
            WHERE region IS NOT NULL AND region != ''
            ORDER BY region
        """)
        
        regions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        
        return regions
    
    def _group_by_department(self) -> List[Dict]:
        """Groupe les sites par département"""
        # Implémentation simplifiée
        return []
    
    def _group_by_region(self) -> List[Dict]:
        """Groupe les sites par région"""
        # Implémentation simplifiée
        return []
    
    def _group_by_team_size(self) -> List[Dict]:
        """Groupe les sites par taille d'équipe"""
        # Implémentation simplifiée
        return []
    
    def _group_by_performance(self) -> List[Dict]:
        """Groupe les sites par niveau de performance"""
        # Implémentation simplifiée
        return []
    
    def _analyze_group(self, group: Dict, grouping: str) -> Dict:
        """Analyse un groupe de sites"""
        # Implémentation simplifiée
        return {}
    
    def _calculate_global_metrics(self, groups: List[Dict]) -> Dict:
        """Calcule les métriques globales"""
        # Implémentation simplifiée
        return {}
    
    def _perform_cross_group_analysis(self, groups: List[Dict]) -> Dict:
        """Effectue une analyse croisée entre groupes"""
        # Implémentation simplifiée
        return {}
    
    def _identify_efficiency_opportunities(self, groups: List[Dict]) -> List[Dict]:
        """Identifie les opportunités d'efficacité"""
        # Implémentation simplifiée
        return []

# Instance globale
multi_site_manager = MultiSiteManager()
