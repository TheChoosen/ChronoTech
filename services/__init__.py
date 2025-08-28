"""
Services ChronoTech - Sprint 2
Modules de services pour l'application
"""

# Import des services principaux
from .ai_guards import AIGuardsService, ValidationResult

# Instance globale du service AI Guards
ai_guards = AIGuardsService()

# Export des services
__all__ = ['ai_guards', 'ValidationResult', 'AIGuardsService']
