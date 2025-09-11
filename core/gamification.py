"""
Sprint 5 - Module de Gamification et Engagement
Système de badges, scores et classements pour les techniciens
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
import json
import hashlib
import uuid
from core.database import get_db_connection
from core.config import Config
import logging

logger = logging.getLogger(__name__)

class GamificationEngine:
    """Moteur de gamification pour ChronoTech"""
    
    def __init__(self):
        self.score_weights = {
            'work_order_completed': 10,
            'satisfaction_bonus': 5,  # Par point de satisfaction au-dessus de 4
            'time_bonus': 3,  # Bonus pour complétion rapide
            'quality_bonus': 8,  # Bonus pour travail de qualité
            'teamwork_bonus': 5
        }
    
    def calculate_user_scores(self, user_id: int, period: str = 'weekly') -> Dict:
        """Calcule et met à jour les scores d'un utilisateur"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Appeler la procédure stockée pour calculer les scores
            cursor.callproc('CalculateUserScores', [user_id, period])
            
            # Récupérer le score calculé
            period_key = self._get_period_key(period)
            cursor.execute("""
                SELECT * FROM user_scores 
                WHERE user_id = %s AND score_type = %s AND period_key = %s
            """, (user_id, period, period_key))
            
            score_data = cursor.fetchone()
            conn.commit()
            
            return {
                'success': True,
                'user_id': user_id,
                'period': period,
                'score_data': score_data
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul scores utilisateur {user_id}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def check_and_award_badges(self, user_id: int) -> Dict:
        """Vérifie et attribue les nouveaux badges à un utilisateur"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Appeler la procédure pour vérifier les badges
            cursor.callproc('CheckAndAwardBadges', [user_id])
            
            # Récupérer les badges récemment obtenus (dernière heure)
            cursor.execute("""
                SELECT ub.*, bd.name, bd.description, bd.icon, bd.color, bd.points_awarded
                FROM user_badges ub
                INNER JOIN badge_definitions bd ON ub.badge_id = bd.id
                WHERE ub.user_id = %s 
                AND ub.earned_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                ORDER BY ub.earned_at DESC
            """, (user_id,))
            
            new_badges = cursor.fetchall()
            conn.commit()
            
            return {
                'success': True,
                'user_id': user_id,
                'new_badges': new_badges,
                'badges_count': len(new_badges)
            }
            
        except Exception as e:
            logger.error(f"Erreur vérification badges utilisateur {user_id}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def generate_leaderboard(self, leaderboard_type: str, period_key: str = None) -> Dict:
        """Génère un classement pour une période donnée"""
        try:
            if not period_key:
                period_key = self._get_period_key('weekly' if 'weekly' in leaderboard_type else 'monthly')
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Effacer l'ancien classement
            cursor.execute("""
                DELETE FROM leaderboards 
                WHERE leaderboard_type = %s AND period_key = %s
            """, (leaderboard_type, period_key))
            
            if leaderboard_type.startswith('individual'):
                # Classement individuel
                period_type = 'weekly' if 'weekly' in leaderboard_type else 'monthly'
                
                cursor.execute("""
                    SELECT 
                        u.id as user_id,
                        u.name as user_name,
                        COALESCE(us.points, 0) as total_points,
                        COALESCE(us.work_orders_completed, 0) as work_orders_completed,
                        COALESCE(avg_satisfaction.avg_sat, 0) as avg_satisfaction,
                        COUNT(DISTINCT ub.id) as badges_earned
                    FROM users u
                    LEFT JOIN user_scores us ON u.id = us.user_id 
                        AND us.score_type = %s AND us.period_key = %s
                    LEFT JOIN user_badges ub ON u.id = ub.user_id 
                        AND ub.earned_at >= DATE_SUB(NOW(), INTERVAL %s)
                    LEFT JOIN (
                        SELECT 
                            cf.technician_id,
                            AVG(cf.overall_satisfaction) as avg_sat
                        FROM client_feedback cf
                        WHERE cf.submitted_at >= DATE_SUB(NOW(), INTERVAL %s)
                        GROUP BY cf.technician_id
                    ) avg_satisfaction ON u.id = avg_satisfaction.technician_id
                    WHERE u.is_active = TRUE
                    GROUP BY u.id
                    HAVING total_points > 0
                    ORDER BY total_points DESC, avg_satisfaction DESC
                    LIMIT 50
                """, (
                    period_type, period_key,
                    '7 DAY' if period_type == 'weekly' else '30 DAY',
                    '7 DAY' if period_type == 'weekly' else '30 DAY'
                ))
                
                users_ranking = cursor.fetchall()
                
                # Insérer dans le classement
                for rank, user_data in enumerate(users_ranking, 1):
                    cursor.execute("""
                        INSERT INTO leaderboards 
                        (leaderboard_type, period_key, entity_type, entity_id, entity_name,
                         rank_position, total_points, work_orders_completed, avg_satisfaction, badges_earned)
                        VALUES (%s, %s, 'user', %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        leaderboard_type, period_key, user_data['user_id'], 
                        user_data['user_name'], rank, user_data['total_points'],
                        user_data['work_orders_completed'], user_data['avg_satisfaction'],
                        user_data['badges_earned']
                    ))
            
            conn.commit()
            
            # Récupérer le classement généré
            cursor.execute("""
                SELECT * FROM leaderboards 
                WHERE leaderboard_type = %s AND period_key = %s
                ORDER BY rank_position ASC
            """, (leaderboard_type, period_key))
            
            leaderboard_data = cursor.fetchall()
            
            return {
                'success': True,
                'leaderboard_type': leaderboard_type,
                'period_key': period_key,
                'rankings': leaderboard_data,
                'total_participants': len(leaderboard_data)
            }
            
        except Exception as e:
            logger.error(f"Erreur génération classement {leaderboard_type}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_user_gamification_profile(self, user_id: int) -> Dict:
        """Récupère le profil gamification complet d'un utilisateur"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Statistiques générales
            cursor.execute("SELECT * FROM gamification_stats WHERE user_id = %s", (user_id,))
            stats = cursor.fetchone()
            
            # Badges récents (30 derniers jours)
            cursor.execute("""
                SELECT ub.*, bd.name, bd.description, bd.icon, bd.color, bd.category
                FROM user_badges ub
                INNER JOIN badge_definitions bd ON ub.badge_id = bd.id
                WHERE ub.user_id = %s
                ORDER BY ub.earned_at DESC
                LIMIT 20
            """, (user_id,))
            recent_badges = cursor.fetchall()
            
            # Notifications non lues
            cursor.execute("""
                SELECT * FROM gamification_notifications
                WHERE user_id = %s AND is_read = FALSE
                ORDER BY created_at DESC
                LIMIT 10
            """, (user_id,))
            notifications = cursor.fetchall()
            
            # Position dans les classements
            cursor.execute("""
                SELECT leaderboard_type, rank_position, total_points
                FROM leaderboards
                WHERE entity_type = 'user' AND entity_id = %s
                AND period_key IN (
                    DATE_FORMAT(NOW(), '%%Y-W%%u'),
                    DATE_FORMAT(NOW(), '%%Y-%%m')
                )
            """, (user_id,))
            rankings = cursor.fetchall()
            
            return {
                'success': True,
                'user_id': user_id,
                'stats': stats,
                'recent_badges': recent_badges,
                'notifications': notifications,
                'rankings': {r['leaderboard_type']: r for r in rankings},
                'profile_completion': self._calculate_profile_completion(stats)
            }
            
        except Exception as e:
            logger.error(f"Erreur profil gamification utilisateur {user_id}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _calculate_profile_completion(self, stats: Dict) -> Dict:
        """Calcule le pourcentage de complétion du profil gamification"""
        if not stats:
            return {'percentage': 0, 'next_goals': []}
        
        score = 0
        max_score = 100
        next_goals = []
        
        # Points pour badges (40 points max)
        badge_score = min(40, stats.get('total_badges', 0) * 5)
        score += badge_score
        
        if badge_score < 40:
            next_goals.append(f"Obtenir {(40-badge_score)//5} badges supplémentaires")
        
        # Points pour feedback (30 points max)
        feedback_score = min(30, stats.get('feedback_count', 0) * 3)
        score += feedback_score
        
        if feedback_score < 30:
            next_goals.append(f"Recevoir {(30-feedback_score)//3} feedbacks clients")
        
        # Points pour classement (30 points max)
        rank = stats.get('current_weekly_rank')
        if rank:
            rank_score = max(0, 30 - rank)
            score += rank_score
        else:
            next_goals.append("Apparaître dans le classement hebdomadaire")
        
        return {
            'percentage': min(100, score),
            'next_goals': next_goals[:3]  # Top 3 objectifs
        }
    
    def _get_period_key(self, period: str) -> str:
        """Génère la clé de période selon le type"""
        today = date.today()
        
        if period == 'daily':
            return today.strftime('%Y-%m-%d')
        elif period == 'weekly':
            return today.strftime('%Y-W%U')
        elif period == 'monthly':
            return today.strftime('%Y-%m')
        else:
            return 'total'

class ClientFeedbackManager:
    """Gestionnaire du feedback client post-intervention"""
    
    def __init__(self):
        self.token_expiry_days = 30
    
    def generate_feedback_link(self, work_order_id: int) -> Dict:
        """Génère un lien de feedback sécurisé pour un work order"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Récupérer les informations du work order
            cursor.execute("""
                SELECT wo.*, c.email as customer_email, c.name as customer_name
                FROM work_orders wo
                INNER JOIN customers c ON wo.customer_id = c.id
                WHERE wo.id = %s AND wo.status = 'completed'
            """, (work_order_id,))
            
            work_order = cursor.fetchone()
            if not work_order:
                return {'success': False, 'error': 'Work order non trouvé ou non terminé'}
            
            # Vérifier si un token existe déjà
            cursor.execute("""
                SELECT feedback_token FROM client_feedback
                WHERE work_order_id = %s AND expires_at > NOW()
            """, (work_order_id,))
            
            existing = cursor.fetchone()
            if existing:
                return {
                    'success': True,
                    'feedback_url': f"{Config.BASE_URL}/feedback/{existing['feedback_token']}",
                    'token': existing['feedback_token'],
                    'existing': True
                }
            
            # Générer un nouveau token
            token = self._generate_secure_token(work_order_id)
            expires_at = datetime.now() + timedelta(days=self.token_expiry_days)
            
            # Insérer le token
            cursor.execute("""
                INSERT INTO client_feedback 
                (work_order_id, customer_id, technician_id, feedback_token, token_sent_at, expires_at)
                VALUES (%s, %s, %s, %s, NOW(), %s)
            """, (
                work_order_id,
                work_order['customer_id'],
                work_order['assigned_to'],
                token,
                expires_at
            ))
            
            conn.commit()
            
            return {
                'success': True,
                'feedback_url': f"{Config.BASE_URL}/feedback/{token}",
                'token': token,
                'expires_at': expires_at.isoformat(),
                'work_order': work_order
            }
            
        except Exception as e:
            logger.error(f"Erreur génération lien feedback pour WO {work_order_id}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def submit_feedback(self, token: str, feedback_data: Dict) -> Dict:
        """Traite la soumission d'un feedback client"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Vérifier le token
            cursor.execute("""
                SELECT cf.*, wo.claim_number, u.name as technician_name
                FROM client_feedback cf
                INNER JOIN work_orders wo ON cf.work_order_id = wo.id
                INNER JOIN users u ON cf.technician_id = u.id
                WHERE cf.feedback_token = %s 
                AND cf.expires_at > NOW() 
                AND cf.submitted_at IS NULL
            """, (token,))
            
            feedback_record = cursor.fetchone()
            if not feedback_record:
                return {'success': False, 'error': 'Token invalide ou expiré'}
            
            # Mettre à jour avec les données du feedback
            cursor.execute("""
                UPDATE client_feedback SET
                    overall_satisfaction = %s,
                    quality_work = %s,
                    technician_professionalism = %s,
                    response_time_satisfaction = %s,
                    communication_quality = %s,
                    nps_score = %s,
                    positive_feedback = %s,
                    improvement_feedback = %s,
                    additional_comments = %s,
                    would_recommend = %s,
                    would_use_again = %s,
                    submitted_at = NOW(),
                    ip_address = %s,
                    user_agent = %s
                WHERE feedback_token = %s
            """, (
                feedback_data.get('overall_satisfaction'),
                feedback_data.get('quality_work'),
                feedback_data.get('technician_professionalism'),
                feedback_data.get('response_time_satisfaction'),
                feedback_data.get('communication_quality'),
                feedback_data.get('nps_score'),
                feedback_data.get('positive_feedback'),
                feedback_data.get('improvement_feedback'),
                feedback_data.get('additional_comments'),
                feedback_data.get('would_recommend'),
                feedback_data.get('would_use_again'),
                feedback_data.get('ip_address'),
                feedback_data.get('user_agent'),
                token
            ))
            
            conn.commit()
            
            # Déclencher recalcul des scores et badges pour le technicien
            gamification = GamificationEngine()
            gamification.calculate_user_scores(feedback_record['technician_id'], 'weekly')
            gamification.calculate_user_scores(feedback_record['technician_id'], 'monthly')
            gamification.check_and_award_badges(feedback_record['technician_id'])
            
            return {
                'success': True,
                'message': 'Feedback soumis avec succès',
                'work_order_id': feedback_record['work_order_id'],
                'technician_name': feedback_record['technician_name']
            }
            
        except Exception as e:
            logger.error(f"Erreur soumission feedback {token}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_feedback_stats(self, technician_id: int = None, period_days: int = 30) -> Dict:
        """Récupère les statistiques de feedback"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_clause = "WHERE cf.submitted_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            params = [period_days]
            
            if technician_id:
                where_clause += " AND cf.technician_id = %s"
                params.append(technician_id)
            
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_responses,
                    AVG(cf.overall_satisfaction) as avg_satisfaction,
                    AVG(cf.nps_score) as avg_nps,
                    COUNT(CASE WHEN cf.overall_satisfaction >= 5 THEN 1 END) as excellent_count,
                    COUNT(CASE WHEN cf.overall_satisfaction >= 4 THEN 1 END) as good_count,
                    COUNT(CASE WHEN cf.nps_score >= 9 THEN 1 END) as promoters,
                    COUNT(CASE WHEN cf.nps_score <= 6 THEN 1 END) as detractors,
                    COUNT(CASE WHEN cf.would_recommend = TRUE THEN 1 END) as would_recommend_count
                FROM client_feedback cf
                {where_clause}
            """, params)
            
            stats = cursor.fetchone() or {}
            
            # Calculer le NPS
            total_responses = stats.get('total_responses', 0)
            if total_responses > 0:
                promoters = stats.get('promoters', 0)
                detractors = stats.get('detractors', 0)
                nps = ((promoters - detractors) / total_responses) * 100
            else:
                nps = 0
            
            return {
                'success': True,
                'period_days': period_days,
                'stats': {
                    **stats,
                    'nps_calculated': round(nps, 1),
                    'satisfaction_rate': round((stats.get('good_count', 0) / max(1, total_responses)) * 100, 1),
                    'recommendation_rate': round((stats.get('would_recommend_count', 0) / max(1, total_responses)) * 100, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur stats feedback: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _generate_secure_token(self, work_order_id: int) -> str:
        """Génère un token sécurisé pour le feedback"""
        data = f"{work_order_id}-{uuid.uuid4()}-{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

# Instances globales
gamification_engine = GamificationEngine()
feedback_manager = ClientFeedbackManager()
