#!/usr/bin/env python3
"""
Script de diagnostic pour la pagination des clients
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.customers.utils import MiniPagination

def test_pagination():
    """Test la classe MiniPagination"""
    print("🔍 Test de la classe MiniPagination")
    print("=" * 50)
    
    # Test avec 100 clients total, page 1, 20 par page
    pagination = MiniPagination(page=1, per_page=20, total=100)
    
    print(f"Page actuelle: {pagination.page}")
    print(f"Par page: {pagination.per_page}")
    print(f"Total: {pagination.total}")
    print(f"Nombre de pages: {pagination.pages}")
    print(f"Offset: {pagination.offset}")
    print(f"A page précédente: {pagination.has_prev}")
    print(f"A page suivante: {pagination.has_next}")
    print(f"Page précédente: {pagination.prev_num}")
    print(f"Page suivante: {pagination.next_num}")
    
    print("\n📄 Pages générées par iter_pages():")
    pages = list(pagination.iter_pages())
    print(f"Pages: {pages}")
    
    # Test avec page 3
    print("\n" + "=" * 50)
    print("Test avec page 3")
    pagination2 = MiniPagination(page=3, per_page=20, total=100)
    pages2 = list(pagination2.iter_pages())
    print(f"Page 3 - Pages: {pages2}")
    
    # Test condition pour affichage pagination
    print("\n" + "=" * 50)
    print("Test conditions d'affichage:")
    print(f"pagination.pages > 1: {pagination.pages > 1}")
    print(f"pagination and pagination.pages > 1: {pagination and pagination.pages > 1}")

if __name__ == "__main__":
    test_pagination()
