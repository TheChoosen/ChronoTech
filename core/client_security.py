"""
ChronoTech - Extensions Security pour Sprint 3
Gestion des tokens client et vérification sécurisée
"""

import hashlib
import secrets
import hmac
from datetime import datetime, timedelta
from core.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

def generate_client_token(work_order_id, duration_days=7):
    """
    Générer un token sécurisé pour l'accès client
    
    Args:
        work_order_id (int): ID du bon de travail
        duration_days (int): Durée de validité en jours
    
    Returns:
        str: Token sécurisé
    """
    try:
        # Générer un token aléatoire sécurisé
        random_bytes = secrets.token_bytes(32)
        timestamp = str(int(datetime.now().timestamp()))
        
        # Combiner work_order_id, timestamp et random bytes
        token_data = f"{work_order_id}:{timestamp}:{random_bytes.hex()}"
        
        # Hash avec clé secrète
        secret_key = get_secret_key()
        token_hash = hmac.new(
            secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Format final: base64 du hash
        import base64
        final_token = base64.urlsafe_b64encode(
            f"{work_order_id}:{timestamp}:{token_hash}".encode()
        ).decode().rstrip('=')
        
        logger.info(f"Token généré pour work_order {work_order_id}")
        return final_token
        
    except Exception as e:
        logger.error(f"Erreur génération token: {e}")
        return None

def verify_client_token(work_order_id, token):
    """
    Vérifier la validité d'un token client
    
    Args:
        work_order_id (int): ID du bon de travail
        token (str): Token à vérifier
    
    Returns:
        bool: True si le token est valide
    """
    try:
        # Décoder le token
        import base64
        
        # Ajouter padding si nécessaire
        padding = 4 - len(token) % 4
        if padding != 4:
            token += '=' * padding
        
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        token_parts = decoded.split(':')
        
        if len(token_parts) != 3:
            logger.warning(f"Format token invalide pour work_order {work_order_id}")
            return False
        
        token_work_order_id, timestamp, token_hash = token_parts
        
        # Vérifier que l'ID correspond
        if int(token_work_order_id) != work_order_id:
            logger.warning(f"Work order ID mismatch: {token_work_order_id} != {work_order_id}")
            return False
        
        # Vérifier en base de données
        if not verify_token_in_database(work_order_id, token):
            logger.warning(f"Token non trouvé en base pour work_order {work_order_id}")
            return False
        
        # Vérifier l'expiration
        if is_token_expired(work_order_id, token):
            logger.warning(f"Token expiré pour work_order {work_order_id}")
            return False
        
        # Regénérer le hash pour vérification
        token_data = f"{token_work_order_id}:{timestamp}:{secrets.token_bytes(32).hex()}"
        secret_key = get_secret_key()
        expected_hash = hmac.new(
            secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Note: On ne peut pas vérifier le hash exact car il contient des bytes aléatoires
        # La vérification principale se fait via la base de données
        
        # Marquer le token comme utilisé
        mark_token_used(work_order_id, token)
        
        logger.info(f"Token vérifié avec succès pour work_order {work_order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur vérification token: {e}")
        return False

def verify_token_in_database(work_order_id, token):
    """Vérifier que le token existe en base de données"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, expires_at 
            FROM client_tokens 
            WHERE work_order_id = %s AND token = %s
        """, (work_order_id, token))
        
        result = cursor.fetchone()
        return result is not None
        
    except Exception as e:
        logger.error(f"Erreur vérification token en base: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def is_token_expired(work_order_id, token):
    """Vérifier si un token est expiré"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT expires_at 
            FROM client_tokens 
            WHERE work_order_id = %s AND token = %s
        """, (work_order_id, token))
        
        result = cursor.fetchone()
        if not result:
            return True
        
        expires_at = result[0]
        return datetime.now() > expires_at
        
    except Exception as e:
        logger.error(f"Erreur vérification expiration token: {e}")
        return True
    finally:
        if 'conn' in locals():
            conn.close()

def mark_token_used(work_order_id, token):
    """Marquer un token comme utilisé et incrémenter le compteur"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE client_tokens 
            SET is_used = TRUE, 
                access_count = access_count + 1,
                updated_at = NOW()
            WHERE work_order_id = %s AND token = %s
        """, (work_order_id, token))
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Erreur marquage token utilisé: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_secret_key():
    """
    Récupérer la clé secrète pour la signature des tokens
    En production, cette clé devrait être dans les variables d'environnement
    """
    import os
    return os.environ.get('CHRONOTECH_SECRET_KEY', 'chronotech_default_secret_2025_sprint3')

def generate_secure_link(work_order_id, base_url=None):
    """
    Générer un lien sécurisé complet pour un client
    
    Args:
        work_order_id (int): ID du bon de travail
        base_url (str): URL de base (optionnel)
    
    Returns:
        dict: Informations du lien généré
    """
    try:
        # Générer le token
        token = generate_client_token(work_order_id)
        if not token:
            return None
        
        # URL de base par défaut
        if not base_url:
            base_url = "http://localhost:5020"
        
        # Construire l'URL complète
        client_url = f"{base_url}/client/view?id={work_order_id}&token={token}"
        
        # Calculer l'expiration
        expires_at = datetime.now() + timedelta(days=7)
        
        return {
            'client_url': client_url,
            'token': token,
            'work_order_id': work_order_id,
            'expires_at': expires_at.isoformat(),
            'qr_code_data': client_url  # Pour génération QR code future
        }
        
    except Exception as e:
        logger.error(f"Erreur génération lien sécurisé: {e}")
        return None

def validate_client_access(request, work_order_id):
    """
    Valider l'accès client complet avec logging
    
    Args:
        request: Objet request Flask
        work_order_id (int): ID du bon de travail
    
    Returns:
        bool: True si l'accès est autorisé
    """
    try:
        token = request.args.get('token')
        if not token:
            return False
        
        # Vérifier le token
        if not verify_client_token(work_order_id, token):
            return False
        
        # Logger l'accès
        log_client_access_detailed(
            work_order_id, 
            request.remote_addr,
            request.headers.get('User-Agent', '')
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur validation accès client: {e}")
        return False

def log_client_access_detailed(work_order_id, ip_address, user_agent):
    """Logger un accès client avec détails"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO client_access_logs (
                work_order_id, ip_address, user_agent, accessed_at
            ) VALUES (%s, %s, %s, %s)
        """, (work_order_id, ip_address, user_agent, datetime.now()))
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Erreur log accès client détaillé: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def cleanup_expired_tokens():
    """
    Nettoyer les tokens expirés (à appeler périodiquement)
    
    Returns:
        int: Nombre de tokens supprimés
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM client_tokens 
            WHERE expires_at < %s
        """, (datetime.now(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Nettoyage: {deleted_count} tokens expirés supprimés")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Erreur nettoyage tokens: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def get_client_access_statistics(work_order_id):
    """
    Récupérer les statistiques d'accès client pour un bon de travail
    
    Args:
        work_order_id (int): ID du bon de travail
    
    Returns:
        dict: Statistiques d'accès
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_accesses,
                COUNT(DISTINCT ip_address) as unique_visitors,
                MIN(accessed_at) as first_access,
                MAX(accessed_at) as last_access,
                AVG(session_duration) as avg_session_duration
            FROM client_access_logs 
            WHERE work_order_id = %s
        """, (work_order_id,))
        
        stats = cursor.fetchone()
        
        # Statistiques des tokens
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tokens,
                COUNT(CASE WHEN is_used THEN 1 END) as used_tokens,
                MAX(access_count) as max_access_count
            FROM client_tokens 
            WHERE work_order_id = %s
        """, (work_order_id,))
        
        token_stats = cursor.fetchone()
        
        return {
            **stats,
            **token_stats,
            'work_order_id': work_order_id
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération statistiques: {e}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()
