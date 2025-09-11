"""
Routes Interventions - Sprint 2
Gestion des interventions avec validation IA et upload médias
"""

from .routes import bp
from .kanban_api import kanban_bp

__all__ = ['bp', 'kanban_bp']
