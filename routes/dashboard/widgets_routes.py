"""
Dashboard Widgets Routes
Routes pour la personnalisation des widgets
"""
from flask import Blueprint, render_template, session
from core.security import login_required

widgets_routes_bp = Blueprint('widgets_routes', __name__)

@widgets_routes_bp.route('/dashboard/widgets/customize')
@login_required
def customize_widgets():
    """Page de personnalisation des widgets"""
    return render_template('dashboard/customize_widgets.html')

@widgets_routes_bp.route('/dashboard/widgets/preview/<widget_id>')
@login_required
def preview_widget(widget_id):
    """Prévisualisation d'un widget"""
    return render_template(f'dashboard/components/{widget_id}_widget.html')
