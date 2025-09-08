"""
Module de gestion des factures ChronoTech
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, session
from functools import wraps
import pymysql
from core.database import db_manager, log_activity
import logging

logger = logging.getLogger(__name__)

# Créer le blueprint pour les factures
bp = Blueprint('invoices', __name__, url_prefix='/invoices')

def login_required(f):
    """Décorateur pour s'assurer que l'utilisateur est connecté"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('auth_login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/new')
@login_required
def new_invoice():
    """Créer une nouvelle facture"""
    try:
        customer_id = request.args.get('customer_id')
        
        if not customer_id:
            flash('ID client requis pour créer une facture', 'error')
            return redirect(url_for('customers.index'))
        
        # Vérifier que le client existe
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM customers WHERE id = %s", (customer_id,))
            customer = cursor.fetchone()
            
            if not customer:
                flash('Client non trouvé', 'error')
                return redirect(url_for('customers.index'))
        
        connection.close()
        
        return render_template('invoices/new.html', customer=customer)
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de facture: {e}")
        flash('Erreur lors de la création de la facture', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/create', methods=['POST'])
@login_required
def create_invoice():
    """Créer une nouvelle facture via POST"""
    try:
        customer_id = request.form.get('customer_id')
        description = request.form.get('description', '')
        amount = request.form.get('amount', 0)
        due_date = request.form.get('due_date')
        
        if not customer_id or not amount:
            flash('ID client et montant requis', 'error')
            return redirect(request.referrer or url_for('customers.index'))
        
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            # Insérer la nouvelle facture
            cursor.execute("""
                INSERT INTO invoices (customer_id, description, total_amount, due_date, status, created_at)
                VALUES (%s, %s, %s, %s, 'open', NOW())
            """, (customer_id, description, float(amount), due_date))
            
            invoice_id = cursor.lastrowid
            
            # Logger l'activité
            log_activity(
                user_id=session.get('user_id'),
                action='create',
                target_type='invoice',
                target_id=invoice_id,
                details=f"Facture créée pour le client {customer_id}"
            )
            
        connection.commit()
        connection.close()
        
        flash('Facture créée avec succès', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer_id, tab='finances'))
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de facture: {e}")
        flash('Erreur lors de la création de la facture', 'error')
        return redirect(request.referrer or url_for('customers.index'))

@bp.route('/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """Voir une facture"""
    try:
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT i.*, c.name as customer_name, c.email as customer_email
                FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                WHERE i.id = %s
            """, (invoice_id,))
            
            invoice = cursor.fetchone()
            
            if not invoice:
                flash('Facture non trouvée', 'error')
                return redirect(url_for('customers.index'))
        
        connection.close()
        
        return render_template('invoices/view.html', invoice=invoice)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage de la facture: {e}")
        flash('Erreur lors de l\'affichage de la facture', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/<int:invoice_id>/edit')
@login_required
def edit_invoice(invoice_id):
    """Éditer une facture"""
    try:
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT i.*, c.name as customer_name
                FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                WHERE i.id = %s
            """, (invoice_id,))
            
            invoice = cursor.fetchone()
            
            if not invoice:
                flash('Facture non trouvée', 'error')
                return redirect(url_for('customers.index'))
        
        connection.close()
        
        return render_template('invoices/edit.html', invoice=invoice)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'édition de la facture: {e}")
        flash('Erreur lors de l\'édition de la facture', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/<int:invoice_id>/update', methods=['POST'])
@login_required
def update_invoice(invoice_id):
    """Mettre à jour une facture"""
    try:
        description = request.form.get('description', '')
        amount = request.form.get('amount', 0)
        due_date = request.form.get('due_date')
        status = request.form.get('status', 'open')
        
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE invoices 
                SET description = %s, total_amount = %s, due_date = %s, status = %s, updated_at = NOW()
                WHERE id = %s
            """, (description, float(amount), due_date, status, invoice_id))
            
            # Logger l'activité
            log_activity(
                user_id=session.get('user_id'),
                action='update',
                target_type='invoice',
                target_id=invoice_id,
                details=f"Facture {invoice_id} mise à jour"
            )
            
        connection.commit()
        connection.close()
        
        flash('Facture mise à jour avec succès', 'success')
        return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la facture: {e}")
        flash('Erreur lors de la mise à jour de la facture', 'error')
        return redirect(url_for('invoices.edit_invoice', invoice_id=invoice_id))

@bp.route('/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete_invoice(invoice_id):
    """Supprimer une facture"""
    try:
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            # Récupérer les infos de la facture avant suppression
            cursor.execute("SELECT customer_id FROM invoices WHERE id = %s", (invoice_id,))
            invoice = cursor.fetchone()
            
            if not invoice:
                flash('Facture non trouvée', 'error')
                return redirect(url_for('customers.index'))
            
            customer_id = invoice['customer_id']
            
            # Supprimer la facture
            cursor.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
            
            # Logger l'activité
            log_activity(
                user_id=session.get('user_id'),
                action='delete',
                target_type='invoice',
                target_id=invoice_id,
                details=f"Facture {invoice_id} supprimée"
            )
            
        connection.commit()
        connection.close()
        
        flash('Facture supprimée avec succès', 'success')
        return redirect(url_for('customers.view', id=customer_id, tab='finances'))
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la facture: {e}")
        flash('Erreur lors de la suppression de la facture', 'error')
        return redirect(url_for('customers.index'))

@bp.route('/api/customer/<int:customer_id>')
@login_required
def api_customer_invoices(customer_id):
    """API pour récupérer les factures d'un client"""
    try:
        connection = db_manager.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, description, total_amount, due_date, status, created_at
                FROM invoices
                WHERE customer_id = %s
                ORDER BY created_at DESC
            """, (customer_id,))
            
            invoices = cursor.fetchall()
            
            # Convertir les dates en format ISO
            for invoice in invoices:
                if invoice['created_at']:
                    invoice['created_at'] = invoice['created_at'].isoformat()
                if invoice['due_date']:
                    invoice['due_date'] = invoice['due_date'].isoformat()
                invoice['total_amount'] = float(invoice['total_amount'])
        
        connection.close()
        
        return jsonify({
            'success': True,
            'invoices': invoices
        })
        
    except Exception as e:
        logger.error(f"Erreur API factures client: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
