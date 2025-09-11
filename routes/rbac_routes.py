"""
Sprint 6 - Routes RBAC pour la gestion des permissions
Interface web pour administrer les permissions et les rôles
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from core.rbac_advanced import permission_manager, security_logger, audit_logger
from core.database import get_db_connection
from core.utils import log_info, log_error
import json
from datetime import datetime, timedelta

# Blueprint pour l'administration RBAC
rbac_bp = Blueprint('rbac', __name__, url_prefix='/admin/rbac')

def require_rbac_admin(f):
    """Décorateur pour limiter l'accès aux administrateurs RBAC"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_login'))
        
        user_id = session['user_id']
        if not permission_manager.user_has_permission(user_id, 'users.manage_permissions'):
            flash('Accès refusé - Permissions administrateur requises', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# INTERFACE PRINCIPALE DE GESTION DES PERMISSIONS
# ============================================================================

@rbac_bp.route('/')
@require_rbac_admin
def dashboard():
    """Dashboard principal RBAC"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Statistiques générales
                cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_active = TRUE")
                total_users = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM user_roles")
                total_roles = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM system_permissions")
                total_permissions = cursor.fetchone()['total']
                
                # Événements de sécurité récents
                cursor.execute("""
                    SELECT COUNT(*) as count, severity
                    FROM security_events 
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY severity
                """)
                security_stats = {row['severity']: row['count'] for row in cursor.fetchall()}
                
                # Utilisateurs par rôle
                cursor.execute("""
                    SELECT role, COUNT(*) as count
                    FROM users 
                    WHERE is_active = TRUE
                    GROUP BY role
                """)
                users_by_role = cursor.fetchall()
                
                return render_template('admin/rbac/dashboard.html',
                                     total_users=total_users,
                                     total_roles=total_roles,
                                     total_permissions=total_permissions,
                                     security_stats=security_stats,
                                     users_by_role=users_by_role)
                
    except Exception as e:
        log_error(f"Erreur dashboard RBAC: {e}")
        flash('Erreur lors du chargement du dashboard', 'error')
        return redirect(url_for('dashboard'))

# ============================================================================
# GESTION DES UTILISATEURS ET PERMISSIONS
# ============================================================================

@rbac_bp.route('/users')
@require_rbac_admin
def list_users():
    """Liste des utilisateurs avec leurs permissions"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Compter le total
                cursor.execute("SELECT COUNT(*) as total FROM users WHERE is_active = TRUE")
                total = cursor.fetchone()['total']
                
                # Récupérer les utilisateurs
                cursor.execute("""
                    SELECT u.*, ur.display_name as role_display_name
                    FROM users u
                    LEFT JOIN user_roles ur ON u.role = ur.name
                    WHERE u.is_active = TRUE
                    ORDER BY u.name ASC
                    LIMIT %s OFFSET %s
                """, (per_page, offset))
                
                users = cursor.fetchall()
                pages = (total + per_page - 1) // per_page
                
                return render_template('admin/rbac/users.html',
                                     users=users,
                                     page=page,
                                     pages=pages,
                                     total=total)
                
    except Exception as e:
        log_error(f"Erreur liste utilisateurs RBAC: {e}")
        flash('Erreur lors du chargement des utilisateurs', 'error')
        return redirect(url_for('rbac.dashboard'))

@rbac_bp.route('/users/<int:user_id>/permissions')
@require_rbac_admin
def user_permissions(user_id):
    """Détails des permissions d'un utilisateur"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Récupérer l'utilisateur
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    flash('Utilisateur introuvable', 'error')
                    return redirect(url_for('rbac.list_users'))
                
                # Récupérer les permissions détaillées
                permissions = permission_manager.get_user_role_permissions(user_id)
                
                # Récupérer toutes les permissions système pour le formulaire
                cursor.execute("""
                    SELECT * FROM system_permissions 
                    ORDER BY resource, action
                """)
                all_permissions = cursor.fetchall()
                
                # Organiser par ressource
                permissions_by_resource = {}
                for perm in all_permissions:
                    resource = perm['resource']
                    if resource not in permissions_by_resource:
                        permissions_by_resource[resource] = []
                    permissions_by_resource[resource].append(perm)
                
                return render_template('admin/rbac/user_permissions.html',
                                     user=user,
                                     permissions=permissions,
                                     all_permissions=permissions_by_resource)
                
    except Exception as e:
        log_error(f"Erreur permissions utilisateur {user_id}: {e}")
        flash('Erreur lors du chargement des permissions', 'error')
        return redirect(url_for('rbac.list_users'))

@rbac_bp.route('/users/<int:user_id>/permissions', methods=['POST'])
@require_rbac_admin
def update_user_permissions(user_id):
    """Met à jour les permissions d'un utilisateur"""
    try:
        data = request.get_json()
        permission_name = data.get('permission')
        action = data.get('action')  # 'grant' ou 'revoke'
        reason = data.get('reason', '')
        expires_days = data.get('expires_days')
        
        if not permission_name or action not in ['grant', 'revoke']:
            return jsonify({'error': 'Données invalides'}), 400
        
        granted_by = session['user_id']
        expires_at = None
        
        if expires_days and action == 'grant':
            expires_at = datetime.now() + timedelta(days=int(expires_days))
        
        if action == 'grant':
            success = permission_manager.grant_permission(
                user_id, permission_name, granted_by, expires_at, reason
            )
        else:
            success = permission_manager.revoke_permission(
                user_id, permission_name, granted_by, reason
            )
        
        if success:
            # Logger l'action
            audit_logger.log_action(
                granted_by, f'permission_{action}', 'user_permissions', 
                str(user_id),
                new_values={
                    'permission': permission_name,
                    'action': action,
                    'reason': reason,
                    'expires_at': expires_at.isoformat() if expires_at else None
                }
            )
            
            return jsonify({'success': True, 'message': f'Permission {action}ed avec succès'})
        else:
            return jsonify({'error': 'Erreur lors de la mise à jour'}), 500
            
    except Exception as e:
        log_error(f"Erreur mise à jour permissions utilisateur {user_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ============================================================================
# GESTION DES RÔLES
# ============================================================================

@rbac_bp.route('/roles')
@require_rbac_admin
def list_roles():
    """Liste des rôles avec leurs permissions"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT ur.*, COUNT(u.id) as user_count
                    FROM user_roles ur
                    LEFT JOIN users u ON ur.name = u.role AND u.is_active = TRUE
                    GROUP BY ur.id
                    ORDER BY ur.name ASC
                """)
                
                roles = cursor.fetchall()
                
                return render_template('admin/rbac/roles.html', roles=roles)
                
    except Exception as e:
        log_error(f"Erreur liste rôles RBAC: {e}")
        flash('Erreur lors du chargement des rôles', 'error')
        return redirect(url_for('rbac.dashboard'))

@rbac_bp.route('/roles/<int:role_id>/permissions')
@require_rbac_admin
def role_permissions(role_id):
    """Détails des permissions d'un rôle"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Récupérer le rôle
                cursor.execute("SELECT * FROM user_roles WHERE id = %s", (role_id,))
                role = cursor.fetchone()
                
                if not role:
                    flash('Rôle introuvable', 'error')
                    return redirect(url_for('rbac.list_roles'))
                
                # Récupérer les permissions du rôle
                cursor.execute("""
                    SELECT sp.*, rp.granted_at
                    FROM role_permissions rp
                    JOIN system_permissions sp ON rp.permission_id = sp.id
                    WHERE rp.role_id = %s
                    ORDER BY sp.resource, sp.action
                """, (role_id,))
                
                role_permissions = cursor.fetchall()
                
                # Récupérer toutes les permissions pour le formulaire
                cursor.execute("""
                    SELECT * FROM system_permissions 
                    ORDER BY resource, action
                """)
                all_permissions = cursor.fetchall()
                
                # Organiser par ressource
                permissions_by_resource = {}
                assigned_permission_ids = {p['id'] for p in role_permissions}
                
                for perm in all_permissions:
                    resource = perm['resource']
                    if resource not in permissions_by_resource:
                        permissions_by_resource[resource] = []
                    
                    perm['is_assigned'] = perm['id'] in assigned_permission_ids
                    permissions_by_resource[resource].append(perm)
                
                return render_template('admin/rbac/role_permissions.html',
                                     role=role,
                                     role_permissions=role_permissions,
                                     all_permissions=permissions_by_resource)
                
    except Exception as e:
        log_error(f"Erreur permissions rôle {role_id}: {e}")
        flash('Erreur lors du chargement des permissions', 'error')
        return redirect(url_for('rbac.list_roles'))

# ============================================================================
# LOGS D'AUDIT ET SÉCURITÉ
# ============================================================================

@rbac_bp.route('/audit')
@require_rbac_admin
def audit_logs():
    """Interface pour consulter les logs d'audit"""
    try:
        page = request.args.get('page', 1, type=int)
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        
        # Filtres pour la requête
        filters = {}
        if user_id:
            filters['user_id'] = user_id
        if action:
            filters['action'] = action
        if resource_type:
            filters['resource_type'] = resource_type
        
        filters['limit'] = 50
        
        logs = audit_logger.get_audit_logs(**filters)
        
        # Récupérer les utilisateurs pour le filtre
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT u.id, u.name, u.email
                    FROM users u
                    JOIN audit_logs al ON u.id = al.user_id
                    ORDER BY u.name
                """)
                users_with_logs = cursor.fetchall()
        
        return render_template('admin/rbac/audit_logs.html',
                             logs=logs,
                             users_with_logs=users_with_logs,
                             filters=request.args)
        
    except Exception as e:
        log_error(f"Erreur logs audit RBAC: {e}")
        flash('Erreur lors du chargement des logs', 'error')
        return redirect(url_for('rbac.dashboard'))

@rbac_bp.route('/security-events')
@require_rbac_admin
def security_events():
    """Interface pour consulter les événements de sécurité"""
    try:
        severity = request.args.get('severity')
        limit = request.args.get('limit', 100, type=int)
        
        events = security_logger.get_security_events(limit, severity)
        
        return render_template('admin/rbac/security_events.html',
                             events=events,
                             current_severity=severity)
        
    except Exception as e:
        log_error(f"Erreur événements sécurité RBAC: {e}")
        flash('Erreur lors du chargement des événements', 'error')
        return redirect(url_for('rbac.dashboard'))

# ============================================================================
# EXPORT DES DONNÉES
# ============================================================================

@rbac_bp.route('/export/audit')
@require_rbac_admin
def export_audit():
    """Exporte les logs d'audit"""
    try:
        format_type = request.args.get('format', 'json')
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        
        # Filtres
        filters = {'limit': 10000}  # Limite élevée pour export
        if user_id:
            filters['user_id'] = user_id
        if action:
            filters['action'] = action
        if resource_type:
            filters['resource_type'] = resource_type
        
        exported_data = audit_logger.export_audit_logs(format_type, **filters)
        
        # Logger l'export
        audit_logger.log_action(
            session['user_id'], 'export', 'audit_logs',
            new_values={'format': format_type, 'filters': filters}
        )
        
        from flask import Response
        
        if format_type == 'csv':
            response = Response(
                exported_data,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
        else:
            response = Response(
                exported_data,
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                }
            )
        
        return response
        
    except Exception as e:
        log_error(f"Erreur export audit: {e}")
        flash('Erreur lors de l\'export', 'error')
        return redirect(url_for('rbac.audit_logs'))

# ============================================================================
# API ENDPOINTS POUR LES INTERFACES AJAX
# ============================================================================

@rbac_bp.route('/api/user/<int:user_id>/effective-permissions')
@require_rbac_admin
def api_user_effective_permissions(user_id):
    """API pour récupérer les permissions effectives d'un utilisateur"""
    try:
        permissions = permission_manager.get_user_permissions(user_id)
        return jsonify({'permissions': permissions})
    except Exception as e:
        log_error(f"Erreur API permissions utilisateur {user_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@rbac_bp.route('/api/permissions/search')
@require_rbac_admin  
def api_search_permissions():
    """API pour rechercher des permissions"""
    try:
        query = request.args.get('q', '')
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM system_permissions 
                    WHERE name LIKE %s OR description LIKE %s
                    ORDER BY resource, action
                    LIMIT 20
                """, (f"%{query}%", f"%{query}%"))
                
                permissions = cursor.fetchall()
                return jsonify({'permissions': permissions})
                
    except Exception as e:
        log_error(f"Erreur recherche permissions: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
