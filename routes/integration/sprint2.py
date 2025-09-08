"""
Intégration Sprint 2 - Registration des nouveaux blueprints
Routes API sécurisées pour Work Orders Tasks et Interventions
"""
from routes.work_orders.api_tasks import api_tasks_bp
from routes.interventions.api_interventions import api_interventions_bp

def register_sprint2_blueprints(app):
    """
    Enregistrer tous les blueprints du Sprint 2
    
    Args:
        app: Instance Flask de l'application
    """
    
    # Enregistrement des blueprints avec préfixes API
    app.register_blueprint(api_tasks_bp, url_prefix='/api/v1')
    app.register_blueprint(api_interventions_bp, url_prefix='/api/v1')
    
    # Log de confirmation
    app.logger.info("Sprint 2 blueprints registered successfully")
    app.logger.info("API Routes available:")
    app.logger.info("- Work Orders Tasks: /api/v1/work_orders/<id>/tasks/*")
    app.logger.info("- Interventions: /api/v1/interventions/*")
    
    return app
