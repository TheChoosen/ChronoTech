"""
Module de gestion financière des clients
"""

import json
import pymysql
from datetime import datetime, timedelta
from flask import request, jsonify, render_template, flash, redirect, url_for
from core.utils import log_error
from .utils import get_db_connection, require_role, get_current_user, log_customer_activity


def setup_finance_routes(bp):
    """Configure les routes de gestion financière"""
    
    @bp.route('/<int:customer_id>/finances', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_customer_finances(customer_id):
        """Récupère les informations financières d'un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Profil financier de base
            cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
            finance_profile = cursor.fetchone()
            
            # Créer profil par défaut si inexistant
            if not finance_profile:
                cursor.execute("""
                    INSERT INTO customer_finances 
                    (customer_id, credit_limit, payment_terms, risk_level, created_at)
                    VALUES (%s, 0, 30, 'low', NOW())
                """, [customer_id])
                
                cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
                finance_profile = cursor.fetchone()
            
            # Factures en cours
            cursor.execute("""
                SELECT COUNT(*) as open_invoices,
                       COALESCE(SUM(total_amount), 0) as total_outstanding,
                       COALESCE(SUM(CASE WHEN due_date < NOW() THEN total_amount ELSE 0 END), 0) as overdue_amount
                FROM invoices
                WHERE customer_id = %s AND status IN ('open', 'sent')
            """, [customer_id])
            
            ar_summary = cursor.fetchone()
            
            # Historique des paiements récents
            cursor.execute("""
                SELECT * FROM customer_balance_history
                WHERE customer_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """, [customer_id])
            
            payment_history = cursor.fetchall()
            
            # Méthodes de paiement
            cursor.execute("""
                SELECT * FROM customer_payment_methods
                WHERE customer_id = %s AND is_active = 1
                ORDER BY is_default DESC, created_at DESC
            """, [customer_id])
            
            payment_methods = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if request.headers.get('Accept') == 'application/json':
                return jsonify({
                    'success': True,
                    'finance_profile': finance_profile,
                    'ar_summary': ar_summary,
                    'payment_history': payment_history,
                    'payment_methods': payment_methods
                })
            else:
                return render_template(
                    'customers/finances.html',
                    customer_id=customer_id,
                    finance_profile=finance_profile,
                    ar_summary=ar_summary,
                    payment_history=payment_history,
                    payment_methods=payment_methods
                )
                
        except Exception as e:
            log_error(f"Erreur récupération finances client {customer_id}: {e}")
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'success': False, 'message': str(e)}), 500
            else:
                flash('Erreur chargement données financières', 'error')
                return redirect(url_for('customers.view_customer', customer_id=customer_id))

    @bp.route('/<int:customer_id>/finances', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def update_customer_finances(customer_id):
        """Met à jour le profil financier d'un client"""
        try:
            data = request.get_json() if request.is_json else request.form
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
            # Mise à jour du profil financier
            cursor.execute("""
                UPDATE customer_finances SET
                    credit_limit = %s,
                    payment_terms = %s,
                    risk_level = %s,
                    notes = %s,
                    updated_at = NOW()
                WHERE customer_id = %s
            """, [
                data.get('credit_limit', 0),
                data.get('payment_terms', 30),
                data.get('risk_level', 'low'),
                data.get('notes', ''),
                customer_id
            ])
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'finance',
                'Profil financier mis à jour',
                f"Limite crédit: {data.get('credit_limit', 0)}, Risque: {data.get('risk_level', 'low')}",
                None,
                'customer_finances'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Profil financier mis à jour'
            })
            
        except Exception as e:
            log_error(f"Erreur mise à jour finances: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/<int:customer_id>/payment-methods', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_payment_methods(customer_id):
        """Récupère les méthodes de paiement d'un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("""
                SELECT id, payment_type, masked_number, expiry_date, is_default, is_active,
                       provider, created_at, last_used_at
                FROM customer_payment_methods
                WHERE customer_id = %s
                ORDER BY is_default DESC, created_at DESC
            """, [customer_id])
            
            payment_methods = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'payment_methods': payment_methods,
                'count': len(payment_methods)
            })
            
        except Exception as e:
            log_error(f"Erreur récupération méthodes paiement: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/<int:customer_id>/payment-methods', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def add_payment_method(customer_id):
        """Ajoute une nouvelle méthode de paiement"""
        try:
            data = request.get_json()
            
            # Validation des données
            required_fields = ['payment_type', 'masked_number']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'message': f'Champ {field} requis'
                    }), 400
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
            # Si c'est la méthode par défaut, désactiver les autres
            if data.get('is_default', False):
                cursor.execute("""
                    UPDATE customer_payment_methods 
                    SET is_default = 0 
                    WHERE customer_id = %s
                """, [customer_id])
            
            # Ajouter la nouvelle méthode
            cursor.execute("""
                INSERT INTO customer_payment_methods
                (customer_id, payment_type, masked_number, expiry_date, provider, 
                 is_default, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, NOW())
            """, [
                customer_id,
                data['payment_type'],
                data['masked_number'],
                data.get('expiry_date'),
                data.get('provider', ''),
                data.get('is_default', False)
            ])
            
            method_id = cursor.lastrowid
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'payment',
                f"Méthode de paiement ajoutée: {data['payment_type']}",
                f"Numéro masqué: {data['masked_number']}",
                method_id,
                'customer_payment_methods'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Méthode de paiement ajoutée',
                'method_id': method_id
            })
            
        except Exception as e:
            log_error(f"Erreur ajout méthode paiement: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/payment-methods/<int:method_id>', methods=['PATCH'])
    @require_role('admin', 'manager', 'staff')
    def update_payment_method(method_id):
        """Met à jour une méthode de paiement"""
        try:
            data = request.get_json()
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Vérifier que la méthode existe
            cursor.execute("""
                SELECT customer_id FROM customer_payment_methods WHERE id = %s
            """, [method_id])
            
            method = cursor.fetchone()
            if not method:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Méthode non trouvée'}), 404
            
            # Si devient méthode par défaut, désactiver les autres
            if data.get('is_default', False):
                cursor.execute("""
                    UPDATE customer_payment_methods 
                    SET is_default = 0 
                    WHERE customer_id = %s AND id != %s
                """, [method['customer_id'], method_id])
            
            # Mettre à jour la méthode
            update_fields = []
            params = []
            
            for field in ['expiry_date', 'provider', 'is_default', 'is_active']:
                if field in data:
                    update_fields.append(f"{field} = %s")
                    params.append(data[field])
            
            if update_fields:
                params.append(method_id)
                cursor.execute(f"""
                    UPDATE customer_payment_methods 
                    SET {', '.join(update_fields)}, updated_at = NOW()
                    WHERE id = %s
                """, params)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Méthode de paiement mise à jour'
            })
            
        except Exception as e:
            log_error(f"Erreur mise à jour méthode paiement: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/<int:customer_id>/balance-history', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_balance_history(customer_id):
        """Récupère l'historique des soldes d'un client"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Compter le total
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM customer_balance_history 
                WHERE customer_id = %s
            """, [customer_id])
            
            total = cursor.fetchone()['total']
            
            # Récupérer l'historique avec pagination
            offset = (page - 1) * per_page
            cursor.execute("""
                SELECT * FROM customer_balance_history
                WHERE customer_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, [customer_id, per_page, offset])
            
            history = cursor.fetchall()
            
            # Calcul du solde actuel
            cursor.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN event_type IN ('invoice', 'debit') THEN amount
                        ELSE -amount
                    END
                ), 0) as current_balance
                FROM customer_balance_history
                WHERE customer_id = %s
            """, [customer_id])
            
            balance_info = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'history': history,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': -(-total // per_page)  # Division ceiling
                },
                'current_balance': balance_info['current_balance']
            })
            
        except Exception as e:
            log_error(f"Erreur historique soldes: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/<int:customer_id>/balance-history', methods=['POST'])
    @require_role('admin', 'manager', 'staff')
    def add_balance_entry(customer_id):
        """Ajoute une entrée dans l'historique des soldes"""
        try:
            data = request.get_json()
            
            # Validation
            required_fields = ['event_type', 'amount', 'description']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'message': f'Champ {field} requis'
                    }), 400
            
            if data['event_type'] not in ['invoice', 'payment', 'credit', 'debit', 'adjustment']:
                return jsonify({
                    'success': False,
                    'message': 'Type d\'événement invalide'
                }), 400
            
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO customer_balance_history
                (customer_id, event_type, amount, description, reference_id, reference_table, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                customer_id,
                data['event_type'],
                data['amount'],
                data['description'],
                data.get('reference_id'),
                data.get('reference_table'),
                get_current_user().id if get_current_user() else None
            ])
            
            entry_id = cursor.lastrowid
            
            # Log de l'activité
            log_customer_activity(
                customer_id,
                'balance',
                f"Écriture de solde: {data['event_type']}",
                f"Montant: {data['amount']}€ - {data['description']}",
                entry_id,
                'customer_balance_history'
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Écriture ajoutée à l\'historique',
                'entry_id': entry_id
            })
            
        except Exception as e:
            log_error(f"Erreur ajout écriture solde: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @bp.route('/<int:customer_id>/risk-score', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def calculate_risk_score(customer_id):
        """Calcule le score de risque d'un client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Facteurs de risque
            risk_factors = {
                'payment_delays': 0,
                'overdue_amount': 0,
                'payment_frequency': 0,
                'credit_utilization': 0,
                'account_age': 0
            }
            
            # Retards de paiement récents
            cursor.execute("""
                SELECT COUNT(*) as late_payments
                FROM invoices
                WHERE customer_id = %s 
                AND status = 'paid' 
                AND paid_at > due_date
                AND created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            """, [customer_id])
            
            late_payments = cursor.fetchone()['late_payments']
            risk_factors['payment_delays'] = min(late_payments * 10, 50)
            
            # Montant en souffrance
            cursor.execute("""
                SELECT COALESCE(SUM(total_amount), 0) as overdue
                FROM invoices
                WHERE customer_id = %s 
                AND status IN ('open', 'sent')
                AND due_date < NOW()
            """, [customer_id])
            
            overdue = cursor.fetchone()['overdue']
            risk_factors['overdue_amount'] = min((overdue / 1000) * 5, 30)
            
            # Ancienneté du compte (bonus de confiance)
            cursor.execute("""
                SELECT DATEDIFF(NOW(), created_at) as account_days
                FROM customers
                WHERE id = %s
            """, [customer_id])
            
            account_days = cursor.fetchone()['account_days']
            if account_days > 365:
                risk_factors['account_age'] = -10  # Bonus pour ancienneté
            
            # Score total (0-100, 0 = très faible risque, 100 = très haut risque)
            total_score = sum(risk_factors.values())
            total_score = max(0, min(100, total_score))
            
            # Classification
            if total_score <= 20:
                risk_level = 'very_low'
                risk_label = 'Très faible'
            elif total_score <= 40:
                risk_level = 'low'
                risk_label = 'Faible'
            elif total_score <= 60:
                risk_level = 'medium'
                risk_label = 'Moyen'
            elif total_score <= 80:
                risk_level = 'high'
                risk_label = 'Élevé'
            else:
                risk_level = 'very_high'
                risk_label = 'Très élevé'
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'risk_score': {
                    'score': total_score,
                    'level': risk_level,
                    'label': risk_label,
                    'factors': risk_factors,
                    'calculated_at': datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            log_error(f"Erreur calcul score risque: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # =====================================================
    # RÉSUMÉ FINANCIER AVANCÉ
    # =====================================================
    
    @bp.route('/<int:customer_id>/finances/summary', methods=['GET'])
    @require_role('admin', 'manager', 'staff')
    def get_customer_financial_summary(customer_id):
        """Résumé financier complet du client"""
        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
            
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Profil financier de base
            cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
            finance_profile = cursor.fetchone()
            
            # Créer profil par défaut si inexistant
            if not finance_profile:
                cursor.execute("""
                    INSERT INTO customer_finances (customer_id, created_at)
                    VALUES (%s, NOW())
                """, [customer_id])
                conn.commit()
                
                cursor.execute("SELECT * FROM customer_finances WHERE customer_id = %s", [customer_id])
                finance_profile = cursor.fetchone()
            
            # Calcul du solde actuel
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN event_type IN ('invoice', 'debit') THEN amount ELSE -amount END), 0) as current_balance
                FROM customer_balance_history
                WHERE customer_id = %s
            """, [customer_id])
            balance_info = cursor.fetchone()
            
            # Factures en cours (AR)
            cursor.execute("""
                SELECT 
                    COUNT(*) as open_invoices,
                    COALESCE(SUM(total_amount), 0) as total_outstanding,
                    COALESCE(SUM(CASE WHEN due_date < NOW() THEN total_amount ELSE 0 END), 0) as overdue_amount,
                    MIN(due_date) as earliest_due_date
                FROM invoices
                WHERE customer_id = %s AND status IN ('open', 'sent')
            """, [customer_id])
            ar_summary = cursor.fetchone()
            
            # Historique des paiements (6 derniers mois)
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(created_at, '%%Y-%%m') as month,
                    SUM(CASE WHEN event_type = 'payment' THEN amount ELSE 0 END) as payments,
                    SUM(CASE WHEN event_type = 'invoice' THEN amount ELSE 0 END) as invoiced
                FROM customer_balance_history
                WHERE customer_id = %s 
                AND created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(created_at, '%%Y-%%m')
                ORDER BY month DESC
            """, [customer_id])
            payment_history = cursor.fetchall()
            
            # Méthodes de paiement
            cursor.execute("""
                SELECT * FROM customer_payment_methods
                WHERE customer_id = %s AND is_verified = 1
                ORDER BY is_default DESC, created_at DESC
            """, [customer_id])
            payment_methods = cursor.fetchall()
            
            # Calcul score de risque
            risk_factors = {
                'overdue_amount': float(ar_summary['overdue_amount'] or 0),
                'days_overdue': 0,
                'payment_history_score': 85,  # Score par défaut
                'credit_utilization': 0
            }
            
            if ar_summary['earliest_due_date'] and ar_summary['earliest_due_date'] < datetime.now().date():
                risk_factors['days_overdue'] = (datetime.now().date() - ar_summary['earliest_due_date']).days
            
            if finance_profile.get('credit_limit') and finance_profile['credit_limit'] > 0:
                risk_factors['credit_utilization'] = (float(balance_info['current_balance']) / float(finance_profile['credit_limit'])) * 100
            
            # Score de risque simplifié (0-100, plus élevé = plus risqué)
            risk_score = min(100, max(0, 
                (risk_factors['days_overdue'] * 2) + 
                (risk_factors['credit_utilization'] * 0.5) +
                (risk_factors['overdue_amount'] / 1000 * 10)
            ))
            
            cursor.close()
            conn.close()
            
            financial_summary = {
                'finance_profile': finance_profile,
                'current_balance': balance_info['current_balance'],
                'ar_summary': ar_summary,
                'payment_history': payment_history,
                'payment_methods': payment_methods,
                'risk_score': round(risk_score, 1),
                'risk_factors': risk_factors
            }
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': True, 'financial_summary': financial_summary})
            
            return render_template(
                'customers/finances.html',
                customer_id=customer_id,
                **financial_summary
            )
            
        except Exception as e:
            log_error(f"Erreur résumé financier: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'Erreur résumé financier'}), 500
            flash('Erreur chargement résumé financier', 'error')
            return redirect(url_for('customers.view_customer', customer_id=customer_id))
