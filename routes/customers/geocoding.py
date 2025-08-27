"""
Services de géolocalisation et géocodage pour les clients
"""

import requests
import math
import pymysql
from core.utils import log_error
from .utils import get_db_connection

# Configuration géospatiale
GEOCODING_CONFIG = {
    'provider': 'nominatim',  # nominatim, google, mapbox
    'api_key': None,  # Pour Google Maps ou Mapbox
    'rate_limit': 1,  # Requests per second
    'timeout': 5,     # Timeout en secondes
}


def geocode_address(address_string):
    """Géocode une adresse en coordonnées lat/lng"""
    try:
        if GEOCODING_CONFIG['provider'] == 'nominatim':
            # Service gratuit OpenStreetMap
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address_string,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'ChronoTech/1.0 (contact@chronotech.fr)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=GEOCODING_CONFIG['timeout'])
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        
        elif GEOCODING_CONFIG['provider'] == 'google' and GEOCODING_CONFIG['api_key']:
            # Google Maps Geocoding API (nécessite clé API)
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address_string,
                'key': GEOCODING_CONFIG['api_key']
            }
            
            response = requests.get(url, params=params, timeout=GEOCODING_CONFIG['timeout'])
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['results']:
                    location = data['results'][0]['geometry']['location']
                    return location['lat'], location['lng']
        
        return None
    except Exception as e:
        log_error(f"Erreur géocodage pour '{address_string}': {e}")
        return None


def calculate_distance(lat1, lng1, lat2, lng2):
    """Calcule la distance entre deux points en kilomètres (formule de Haversine)"""
    # Conversion en radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Formule de Haversine
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Rayon de la Terre en kilomètres
    r = 6371
    
    return c * r


def find_addresses_in_radius(center_lat, center_lng, radius_km, customer_id=None):
    """Trouve les adresses dans un rayon donné"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        where_clause = "latitude IS NOT NULL AND longitude IS NOT NULL"
        params = []
        
        if customer_id:
            where_clause += " AND customer_id = %s"
            params.append(customer_id)
        
        # Requête pour récupérer les adresses avec coordonnées
        cursor.execute(f"""
            SELECT id, customer_id, address, city, postal_code, latitude, longitude,
                   (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
                   cos(radians(longitude) - radians(%s)) + sin(radians(%s)) * 
                   sin(radians(latitude)))) AS distance
            FROM customer_addresses 
            WHERE {where_clause}
            HAVING distance <= %s
            ORDER BY distance
        """, [center_lat, center_lng, center_lat] + params + [radius_km])
        
        addresses = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return addresses
        
    except Exception as e:
        log_error(f"Erreur recherche adresses dans rayon: {e}")
        return []


def get_postal_code_suggestions(partial_code, limit=10):
    """Récupère des suggestions de codes postaux basées sur une saisie partielle"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT DISTINCT postal_code, city, COUNT(*) as usage_count
            FROM customer_addresses 
            WHERE postal_code LIKE %s
            GROUP BY postal_code, city
            ORDER BY usage_count DESC, postal_code
            LIMIT %s
        """, [f"{partial_code}%", limit])
        
        suggestions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return suggestions
        
    except Exception as e:
        log_error(f"Erreur suggestions codes postaux: {e}")
        return []


def validate_address_with_geocoding(address, city, postal_code=None):
    """Valide une adresse en tentant de la géocoder"""
    try:
        # Construction de l'adresse complète
        full_address = f"{address}, {city}"
        if postal_code:
            full_address += f" {postal_code}"
        
        # Tentative de géocodage
        coordinates = geocode_address(full_address)
        
        if coordinates:
            return {
                'valid': True,
                'coordinates': {
                    'lat': coordinates[0],
                    'lng': coordinates[1]
                },
                'formatted_address': full_address
            }
        else:
            return {
                'valid': False,
                'error': 'Impossible de géolocaliser cette adresse',
                'coordinates': None
            }
            
    except Exception as e:
        log_error(f"Erreur validation adresse avec géocodage: {e}")
        return {
            'valid': False,
            'error': f'Erreur technique: {e}',
            'coordinates': None
        }


def get_address_suggestions(query, limit=5):
    """Récupère des suggestions d'adresses basées sur une recherche"""
    try:
        if GEOCODING_CONFIG['provider'] == 'nominatim':
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'limit': limit,
                'addressdetails': 1,
                'countrycodes': 'fr'  # Limiter à la France
            }
            headers = {
                'User-Agent': 'ChronoTech/1.0 (contact@chronotech.fr)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=GEOCODING_CONFIG['timeout'])
            if response.status_code == 200:
                data = response.json()
                
                suggestions = []
                for item in data:
                    suggestion = {
                        'display_name': item.get('display_name', ''),
                        'address': item.get('address', {}),
                        'coordinates': {
                            'lat': float(item.get('lat', 0)),
                            'lng': float(item.get('lon', 0))
                        }
                    }
                    suggestions.append(suggestion)
                
                return suggestions
        
        return []
        
    except Exception as e:
        log_error(f"Erreur suggestions adresses: {e}")
        return []
