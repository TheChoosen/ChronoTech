"""
Routes PDF - Sprint 3
Endpoints pour générer et télécharger les PDFs
"""
from flask import Blueprint, request, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
import os
import logging
from datetime import datetime
from werkzeug.utils import secure_filename

# Import du service PDF
try:
    from services.pdf_generator import pdf_generator
    PDF_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Service PDF non disponible: {e}")
    PDF_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Blueprint PDF
pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

@pdf_bp.route('/work-order/<int:work_order_id>')
@login_required
def generate_work_order_pdf(work_order_id):
    """
    Générer et télécharger le PDF d'un bon de travail
    
    Args:
        work_order_id: ID du bon de travail
        
    Query params:
        include_interventions: inclure les détails des interventions (default: true)
        download: télécharger directement (default: true)
    """
    if not PDF_SERVICE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Service PDF non disponible. Installez WeasyPrint ou ReportLab.'
        }), 503
    
    try:
        # Paramètres
        include_interventions = request.args.get('include_interventions', 'true').lower() == 'true'
        download = request.args.get('download', 'true').lower() == 'true'
        
        # Vérifier les permissions (ajustez selon votre logique)
        if not _can_access_work_order(work_order_id, current_user):
            abort(403)
        
        # Générer le PDF
        result = pdf_generator.generate_work_order_pdf(
            work_order_id=work_order_id,
            include_interventions=include_interventions
        )
        
        if not result['success']:
            return jsonify(result), 400
        
        # Télécharger ou retourner les infos
        if download:
            return send_file(
                result['pdf_path'],
                as_attachment=True,
                download_name=result['filename'],
                mimetype='application/pdf'
            )
        else:
            # Retourner les métadonnées pour AJAX
            return jsonify({
                'success': True,
                'download_url': f"/pdf/download/{result['filename']}",
                'filename': result['filename'],
                'size_bytes': result['size_bytes'],
                'generated_at': result['generated_at']
            })
    
    except Exception as e:
        logger.error(f"Erreur génération PDF Work Order {work_order_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la génération du PDF'
        }), 500

@pdf_bp.route('/intervention/<int:intervention_id>')
@login_required
def generate_intervention_pdf(intervention_id):
    """
    Générer et télécharger le rapport PDF d'une intervention
    
    Args:
        intervention_id: ID de l'intervention
    """
    if not PDF_SERVICE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Service PDF non disponible'
        }), 503
    
    try:
        # Vérifier les permissions
        if not _can_access_intervention(intervention_id, current_user):
            abort(403)
        
        # Générer le PDF
        result = pdf_generator.generate_intervention_report_pdf(intervention_id)
        
        if not result['success']:
            return jsonify(result), 400
        
        # Télécharger
        return send_file(
            result['pdf_path'],
            as_attachment=True,
            download_name=result['filename'],
            mimetype='application/pdf'
        )
    
    except Exception as e:
        logger.error(f"Erreur génération PDF Intervention {intervention_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la génération du PDF'
        }), 500

@pdf_bp.route('/download/<filename>')
@login_required
def download_generated_pdf(filename):
    """
    Télécharger un PDF généré précédemment
    
    Args:
        filename: Nom du fichier PDF
    """
    try:
        # Sécuriser le nom de fichier
        safe_filename = secure_filename(filename)
        
        # Vérifier que c'est bien un PDF
        if not safe_filename.endswith('.pdf'):
            abort(400)
        
        # Chemin du fichier
        pdf_path = os.path.join(
            os.getcwd(), 'static', 'generated_pdfs', safe_filename
        )
        
        # Vérifier que le fichier existe
        if not os.path.exists(pdf_path):
            abort(404)
        
        # Vérifier que l'utilisateur peut télécharger ce fichier
        # (basé sur le nom du fichier qui contient l'ID)
        if not _can_download_pdf(safe_filename, current_user):
            abort(403)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        logger.error(f"Erreur téléchargement PDF {filename}: {e}")
        abort(500)

@pdf_bp.route('/batch/work-orders', methods=['POST'])
@login_required
def generate_batch_work_order_pdfs():
    """
    Générer plusieurs PDFs de work orders en lot
    
    Body JSON:
        {
            "work_order_ids": [1, 2, 3],
            "include_interventions": true,
            "zip_download": true
        }
    """
    if not PDF_SERVICE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Service PDF non disponible'
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'work_order_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'work_order_ids requis'
            }), 400
        
        work_order_ids = data['work_order_ids']
        include_interventions = data.get('include_interventions', True)
        zip_download = data.get('zip_download', True)
        
        # Vérifier les permissions pour tous les work orders
        for wo_id in work_order_ids:
            if not _can_access_work_order(wo_id, current_user):
                return jsonify({
                    'success': False,
                    'error': f'Accès refusé pour le work order {wo_id}'
                }), 403
        
        # Générer les PDFs
        results = []
        generated_files = []
        
        for wo_id in work_order_ids:
            result = pdf_generator.generate_work_order_pdf(
                work_order_id=wo_id,
                include_interventions=include_interventions
            )
            
            results.append({
                'work_order_id': wo_id,
                'success': result['success'],
                'filename': result.get('filename'),
                'error': result.get('error')
            })
            
            if result['success']:
                generated_files.append(result['pdf_path'])
        
        # Si zip demandé, créer une archive
        if zip_download and generated_files:
            zip_path = _create_pdf_zip(generated_files)
            
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f"work_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mimetype='application/zip'
            )
        else:
            return jsonify({
                'success': True,
                'results': results,
                'total_generated': len(generated_files)
            })
    
    except Exception as e:
        logger.error(f"Erreur génération batch PDFs: {e}")
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la génération des PDFs'
        }), 500

@pdf_bp.route('/status')
@login_required
def pdf_service_status():
    """Vérifier le statut du service PDF"""
    return jsonify({
        'available': PDF_SERVICE_AVAILABLE,
        'weasyprint_available': PDF_SERVICE_AVAILABLE and hasattr(pdf_generator, 'WEASYPRINT_AVAILABLE') and pdf_generator.WEASYPRINT_AVAILABLE,
        'reportlab_available': PDF_SERVICE_AVAILABLE and hasattr(pdf_generator, 'REPORTLAB_AVAILABLE') and pdf_generator.REPORTLAB_AVAILABLE,
        'output_directory': os.path.join(os.getcwd(), 'static', 'generated_pdfs') if PDF_SERVICE_AVAILABLE else None
    })

@pdf_bp.route('/templates/test')
@login_required
def test_pdf_template():
    """
    Tester la génération PDF avec des données de test
    (Uniquement pour les administrateurs)
    """
    if not current_user.is_admin:
        abort(403)
    
    if not PDF_SERVICE_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Service PDF non disponible'
        }), 503
    
    try:
        # Données de test
        test_wo_data = {
            'id': 999,
            'claim_number': 'TEST-001',
            'customer_name': 'Client Test',
            'customer_email': 'test@example.com',
            'customer_phone': '555-0123',
            'customer_address': '123 Rue Test',
            'customer_city': 'Testville',
            'customer_postal_code': '12345',
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'license_plate': 'TEST-123',
            'vin': '1HGBH41JXMN109186',
            'mileage': 45000,
            'fuel_type': 'Essence'
        }
        
        test_tasks_data = [
            {
                'id': 1,
                'title': 'Vidange moteur',
                'description': 'Changement huile et filtre',
                'priority': 'high',
                'status': 'pending',
                'technician_name': 'Jean Dupont'
            },
            {
                'id': 2,
                'title': 'Vérification freins',
                'description': 'Contrôle plaquettes et disques',
                'priority': 'medium',
                'status': 'assigned',
                'technician_name': 'Marie Martin'
            }
        ]
        
        test_interventions_data = []
        
        # Générer le PDF test
        if hasattr(pdf_generator, '_generate_weasyprint_pdf'):
            pdf_path = pdf_generator._generate_weasyprint_pdf(
                test_wo_data, test_tasks_data, test_interventions_data
            )
        elif hasattr(pdf_generator, '_generate_reportlab_pdf'):
            pdf_path = pdf_generator._generate_reportlab_pdf(
                test_wo_data, test_tasks_data, test_interventions_data
            )
        else:
            raise RuntimeError("Aucune méthode de génération PDF disponible")
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name='test_work_order.pdf',
            mimetype='application/pdf'
        )
    
    except Exception as e:
        logger.error(f"Erreur test PDF: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _can_access_work_order(work_order_id: int, user) -> bool:
    """
    Vérifier si l'utilisateur peut accéder au work order
    
    Args:
        work_order_id: ID du work order
        user: Utilisateur actuel
        
    Returns:
        True si l'accès est autorisé
    """
    # Logique de permissions (à adapter selon votre modèle)
    if hasattr(user, 'is_admin') and user.is_admin:
        return True
    
    if hasattr(user, 'is_supervisor') and user.is_supervisor:
        return True
    
    # Pour les techniciens, vérifier l'assignation
    # Ici vous devriez vérifier dans la base de données
    # si le technicien est assigné à ce work order
    
    return True  # Par défaut, autoriser (à modifier selon vos besoins)

def _can_access_intervention(intervention_id: int, user) -> bool:
    """
    Vérifier si l'utilisateur peut accéder à l'intervention
    
    Args:
        intervention_id: ID de l'intervention
        user: Utilisateur actuel
        
    Returns:
        True si l'accès est autorisé
    """
    # Logique similaire à _can_access_work_order
    if hasattr(user, 'is_admin') and user.is_admin:
        return True
    
    if hasattr(user, 'is_supervisor') and user.is_supervisor:
        return True
    
    return True  # Par défaut, autoriser

def _can_download_pdf(filename: str, user) -> bool:
    """
    Vérifier si l'utilisateur peut télécharger ce PDF
    
    Args:
        filename: Nom du fichier PDF
        user: Utilisateur actuel
        
    Returns:
        True si le téléchargement est autorisé
    """
    # Extraire l'ID du work order du nom de fichier
    # Format: work_order_123_20241201_143045.pdf
    
    if hasattr(user, 'is_admin') and user.is_admin:
        return True
    
    # Pour plus de sécurité, vous pourriez maintenir
    # une table des PDFs générés avec les permissions
    
    return True  # Par défaut, autoriser

def _create_pdf_zip(pdf_files: list) -> str:
    """
    Créer une archive ZIP des PDFs générés
    
    Args:
        pdf_files: Liste des chemins vers les PDFs
        
    Returns:
        Chemin vers le fichier ZIP
    """
    import zipfile
    
    zip_filename = f"work_orders_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(os.getcwd(), 'static', 'generated_pdfs', zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for pdf_path in pdf_files:
            if os.path.exists(pdf_path):
                # Ajouter le fichier avec juste le nom (pas le chemin complet)
                zipf.write(pdf_path, os.path.basename(pdf_path))
    
    return zip_path
