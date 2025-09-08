"""
Utilitaire de pagination pour ChronoTech
"""
import math

class Pagination:
    """Classe de pagination simple pour les listes de données"""
    
    def __init__(self, page, per_page, total, items):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items
        self.pages = math.ceil(total / per_page) if per_page > 0 else 0
        
    @property
    def has_prev(self):
        """Indique s'il y a une page précédente"""
        return self.page > 1
    
    @property
    def prev_num(self):
        """Numéro de la page précédente"""
        return self.page - 1 if self.has_prev else None
    
    @property
    def has_next(self):
        """Indique s'il y a une page suivante"""
        return self.page < self.pages
    
    @property
    def next_num(self):
        """Numéro de la page suivante"""
        return self.page + 1 if self.has_next else None
    
    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        """Générateur pour les numéros de pages à afficher"""
        last = self.pages
        for num in range(1, last + 1):
            if num <= left_edge or \
               (self.page - left_current - 1 < num < self.page + right_current) or \
               num > last - right_edge:
                yield num

def paginate_query(cursor, base_query, params, page, per_page, count_query=None):
    """
    Pagine une requête SQL
    
    Args:
        cursor: Curseur de base de données
        base_query: Requête SQL de base
        params: Paramètres de la requête
        page: Numéro de page (commence à 1)
        per_page: Nombre d'éléments par page
        count_query: Requête de comptage (optionnelle, calculée automatiquement si None)
    
    Returns:
        Pagination: Objet de pagination avec les résultats
    """
    # Validation des paramètres
    page = max(1, int(page))
    per_page = max(1, min(100, int(per_page)))  # Limite max de 100 par page
    
    # Comptage total
    if count_query:
        cursor.execute(count_query, params)
    else:
        # Extraction automatique de la requête de comptage
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
        cursor.execute(count_query, params)
    
    total = cursor.fetchone()['total']
    
    # Calcul de l'offset
    offset = (page - 1) * per_page
    
    # Requête paginée
    paginated_query = f"{base_query} LIMIT %s OFFSET %s"
    cursor.execute(paginated_query, params + [per_page, offset])
    items = cursor.fetchall()
    
    return Pagination(page, per_page, total, items)
