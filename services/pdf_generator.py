"""
Service de génération PDF - Sprint 3
Génération de rapports professionnels pour work orders et interventions
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from io import BytesIO
import pymysql

# Import des librairies PDF
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFGeneratorService:
    """Service de génération PDF pour ChronoTech"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'chronotech'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        # Configuration des chemins
        self.templates_path = os.path.join(os.getcwd(), 'templates', 'pdf')
        self.static_path = os.path.join(os.getcwd(), 'static')
        self.output_path = os.path.join(os.getcwd(), 'static', 'generated_pdfs')
        
        # Créer les dossiers nécessaires
        os.makedirs(self.templates_path, exist_ok=True)
        os.makedirs(self.output_path, exist_ok=True)
        
        # Configuration des polices
        self.font_config = FontConfiguration() if WEASYPRINT_AVAILABLE else None
    
    def get_db_connection(self):
        """Connexion à la base de données"""
        return pymysql.connect(**self.db_config)
    
    def generate_work_order_pdf(self, work_order_id: int, include_interventions: bool = True) -> Dict[str, Any]:
        """
        Générer un PDF complet du bon de travail
        
        Args:
            work_order_id: ID du bon de travail
            include_interventions: Inclure les détails des interventions
            
        Returns:
            Dict avec le chemin du fichier et les métadonnées
        """
        try:
            # Récupérer les données du work order
            wo_data = self._get_work_order_data(work_order_id)
            if not wo_data:
                raise ValueError(f"Work Order {work_order_id} non trouvé")
            
            # Récupérer les tâches
            tasks_data = self._get_work_order_tasks(work_order_id)
            
            # Récupérer les interventions si demandé
            interventions_data = []
            if include_interventions:
                interventions_data = self._get_work_order_interventions(work_order_id)
            
            # Générer le PDF selon la méthode disponible
            if WEASYPRINT_AVAILABLE:
                pdf_path = self._generate_weasyprint_pdf(wo_data, tasks_data, interventions_data)
            elif REPORTLAB_AVAILABLE:
                pdf_path = self._generate_reportlab_pdf(wo_data, tasks_data, interventions_data)
            else:
                raise RuntimeError("Aucune librairie PDF disponible (WeasyPrint ou ReportLab)")
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'filename': os.path.basename(pdf_path),
                'work_order_id': work_order_id,
                'generated_at': datetime.now().isoformat(),
                'size_bytes': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
            }
            
        except Exception as e:
            logger.error(f"Erreur génération PDF Work Order {work_order_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'work_order_id': work_order_id
            }
    
    def generate_intervention_report_pdf(self, intervention_id: int) -> Dict[str, Any]:
        """
        Générer un rapport PDF d'intervention pour le technicien
        
        Args:
            intervention_id: ID de l'intervention
            
        Returns:
            Dict avec le chemin du fichier et les métadonnées
        """
        try:
            # Récupérer les données de l'intervention
            intervention_data = self._get_intervention_data(intervention_id)
            if not intervention_data:
                raise ValueError(f"Intervention {intervention_id} non trouvée")
            
            # Récupérer les notes et médias
            notes_data = self._get_intervention_notes(intervention_id)
            media_data = self._get_intervention_media(intervention_id)
            
            # Générer le rapport
            if WEASYPRINT_AVAILABLE:
                pdf_path = self._generate_intervention_weasyprint_pdf(intervention_data, notes_data, media_data)
            elif REPORTLAB_AVAILABLE:
                pdf_path = self._generate_intervention_reportlab_pdf(intervention_data, notes_data, media_data)
            else:
                raise RuntimeError("Aucune librairie PDF disponible")
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'filename': os.path.basename(pdf_path),
                'intervention_id': intervention_id,
                'generated_at': datetime.now().isoformat(),
                'size_bytes': os.path.getsize(pdf_path)
            }
            
        except Exception as e:
            logger.error(f"Erreur génération PDF Intervention {intervention_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'intervention_id': intervention_id
            }
    
    def _get_work_order_data(self, work_order_id: int) -> Optional[Dict[str, Any]]:
        """Récupérer les données complètes d'un work order"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        wo.*,
                        c.name as customer_name,
                        c.email as customer_email,
                        c.phone as customer_phone,
                        c.address as customer_address,
                        c.city as customer_city,
                        c.postal_code as customer_postal_code,
                        v.make, v.model, v.year, v.license_plate, v.vin,
                        v.mileage, v.fuel_type,
                        u.name as technician_name,
                        u.email as technician_email,
                        COUNT(DISTINCT wot.id) as tasks_count,
                        COUNT(DISTINCT i.id) as interventions_count
                    FROM work_orders wo
                    JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                    LEFT JOIN users u ON wo.assigned_technician_id = u.id
                    LEFT JOIN work_order_tasks wot ON wo.id = wot.work_order_id
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    WHERE wo.id = %s
                    GROUP BY wo.id
                """, (work_order_id,))
                
                return cursor.fetchone()
        finally:
            conn.close()
    
    def _get_work_order_tasks(self, work_order_id: int) -> List[Dict[str, Any]]:
        """Récupérer les tâches d'un work order"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        wot.*,
                        u.name as technician_name,
                        i.id as intervention_id,
                        i.started_at,
                        i.ended_at,
                        i.result_status,
                        CASE 
                            WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                            THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                            ELSE NULL 
                        END as duration_minutes
                    FROM work_order_tasks wot
                    LEFT JOIN users u ON wot.technician_id = u.id
                    LEFT JOIN interventions i ON wot.id = i.task_id
                    WHERE wot.work_order_id = %s
                    ORDER BY wot.created_at ASC
                """, (work_order_id,))
                
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _get_work_order_interventions(self, work_order_id: int) -> List[Dict[str, Any]]:
        """Récupérer les interventions complètes d'un work order"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        i.*,
                        wot.title as task_title,
                        wot.description as task_description,
                        u.name as technician_name,
                        COUNT(DISTINCT in_.id) as notes_count,
                        COUNT(DISTINCT im.id) as media_count
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    LEFT JOIN users u ON i.technician_id = u.id
                    LEFT JOIN intervention_notes in_ ON i.id = in_.intervention_id
                    LEFT JOIN intervention_media im ON i.id = im.intervention_id
                    WHERE i.work_order_id = %s
                    GROUP BY i.id
                    ORDER BY i.started_at ASC
                """, (work_order_id,))
                
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _get_intervention_data(self, intervention_id: int) -> Optional[Dict[str, Any]]:
        """Récupérer les données complètes d'une intervention"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        i.*,
                        wot.title as task_title,
                        wot.description as task_description,
                        wot.priority,
                        wo.claim_number,
                        wo.description as wo_title,
                        c.name as customer_name,
                        c.email as customer_email,
                        c.phone as customer_phone,
                        v.make, v.model, v.year, v.license_plate,
                        u.name as technician_name,
                        u.email as technician_email,
                        CASE 
                            WHEN i.started_at IS NOT NULL AND i.ended_at IS NOT NULL 
                            THEN TIMESTAMPDIFF(MINUTE, i.started_at, i.ended_at)
                            ELSE NULL 
                        END as duration_minutes
                    FROM interventions i
                    JOIN work_order_tasks wot ON i.task_id = wot.id
                    JOIN work_orders wo ON i.work_order_id = wo.id
                    JOIN customers c ON wo.customer_id = c.id
                    LEFT JOIN vehicles v ON wo.vehicle_id = v.id
                    LEFT JOIN users u ON i.technician_id = u.id
                    WHERE i.id = %s
                """, (intervention_id,))
                
                return cursor.fetchone()
        finally:
            conn.close()
    
    def _get_intervention_notes(self, intervention_id: int) -> List[Dict[str, Any]]:
        """Récupérer les notes d'une intervention"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT in_.*, u.name as author_name
                    FROM intervention_notes in_
                    JOIN users u ON in_.author_user_id = u.id
                    WHERE in_.intervention_id = %s
                    ORDER BY in_.created_at ASC
                """, (intervention_id,))
                
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _get_intervention_media(self, intervention_id: int) -> List[Dict[str, Any]]:
        """Récupérer les médias d'une intervention"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM intervention_media
                    WHERE intervention_id = %s
                    ORDER BY created_at ASC
                """, (intervention_id,))
                
                return cursor.fetchall()
        finally:
            conn.close()
    
    def _generate_weasyprint_pdf(self, wo_data: Dict, tasks_data: List, interventions_data: List) -> str:
        """Générer PDF avec WeasyPrint (HTML/CSS)"""
        # Créer le template HTML
        html_content = self._create_work_order_html(wo_data, tasks_data, interventions_data)
        
        # CSS pour styling professionnel
        css_content = self._get_pdf_css()
        
        # Générer le PDF
        filename = f"work_order_{wo_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(self.output_path, filename)
        
        html = HTML(string=html_content, base_url=self.static_path)
        css = CSS(string=css_content, font_config=self.font_config)
        
        html.write_pdf(pdf_path, stylesheets=[css], font_config=self.font_config)
        
        return pdf_path
    
    def _generate_reportlab_pdf(self, wo_data: Dict, tasks_data: List, interventions_data: List) -> str:
        """Générer PDF avec ReportLab (programmation directe)"""
        filename = f"work_order_{wo_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(self.output_path, filename)
        
        # Créer le document
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # En-tête
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        story.append(Paragraph(f"BON DE TRAVAIL #{wo_data['claim_number']}", title_style))
        story.append(Spacer(1, 20))
        
        # Informations client
        client_data = [
            ['Client:', wo_data['customer_name']],
            ['Téléphone:', wo_data['customer_phone'] or '-'],
            ['Email:', wo_data['customer_email'] or '-'],
            ['Adresse:', f"{wo_data['customer_address'] or ''} {wo_data['customer_city'] or ''} {wo_data['customer_postal_code'] or ''}".strip() or '-']
        ]
        
        if wo_data['make'] and wo_data['model']:
            client_data.extend([
                ['Véhicule:', f"{wo_data['make']} {wo_data['model']} ({wo_data['year'] or 'N/A'})"],
                ['Plaque:', wo_data['license_plate'] or '-'],
                ['Kilométrage:', f"{wo_data['mileage']} km" if wo_data['mileage'] else '-']
            ])
        
        client_table = Table(client_data, colWidths=[2*inch, 4*inch])
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        
        story.append(client_table)
        story.append(Spacer(1, 20))
        
        # Tâches
        if tasks_data:
            story.append(Paragraph("TÂCHES À EFFECTUER", styles['Heading2']))
            story.append(Spacer(1, 10))
            
            task_data = [['#', 'Description', 'Priorité', 'Statut', 'Technicien']]
            for i, task in enumerate(tasks_data, 1):
                task_data.append([
                    str(i),
                    task['title'],
                    task['priority'].upper(),
                    task['status'].replace('_', ' ').title(),
                    task['technician_name'] or 'Non assigné'
                ])
            
            task_table = Table(task_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1*inch, 1.5*inch])
            task_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            
            story.append(task_table)
        
        # Construire le PDF
        doc.build(story)
        
        return pdf_path
    
    def _create_work_order_html(self, wo_data: Dict, tasks_data: List, interventions_data: List) -> str:
        """Créer le template HTML pour le work order"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Bon de Travail #{wo_data['claim_number']}</title>
        </head>
        <body>
            <div class="header">
                <h1>CHRONOTECH</h1>
                <h2>BON DE TRAVAIL #{wo_data['claim_number']}</h2>
                <div class="date">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</div>
            </div>
            
            <div class="section">
                <h3>INFORMATIONS CLIENT</h3>
                <table class="info-table">
                    <tr><td class="label">Client:</td><td>{wo_data['customer_name']}</td></tr>
                    <tr><td class="label">Téléphone:</td><td>{wo_data['customer_phone'] or '-'}</td></tr>
                    <tr><td class="label">Email:</td><td>{wo_data['customer_email'] or '-'}</td></tr>
                    <tr><td class="label">Adresse:</td><td>{(wo_data['customer_address'] or '') + ' ' + (wo_data['customer_city'] or '') + ' ' + (wo_data['customer_postal_code'] or '')}</td></tr>
                </table>
            </div>
        """
        
        if wo_data['make'] and wo_data['model']:
            html += f"""
            <div class="section">
                <h3>INFORMATIONS VÉHICULE</h3>
                <table class="info-table">
                    <tr><td class="label">Véhicule:</td><td>{wo_data['make']} {wo_data['model']} ({wo_data['year'] or 'N/A'})</td></tr>
                    <tr><td class="label">Plaque:</td><td>{wo_data['license_plate'] or '-'}</td></tr>
                    <tr><td class="label">VIN:</td><td>{wo_data['vin'] or '-'}</td></tr>
                    <tr><td class="label">Kilométrage:</td><td>{wo_data['mileage'] or '-'} km</td></tr>
                    <tr><td class="label">Carburant:</td><td>{wo_data['fuel_type'] or '-'}</td></tr>
                </table>
            </div>
            """
        
        if tasks_data:
            html += """
            <div class="section">
                <h3>TÂCHES À EFFECTUER</h3>
                <table class="tasks-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Description</th>
                            <th>Priorité</th>
                            <th>Statut</th>
                            <th>Technicien</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for i, task in enumerate(tasks_data, 1):
                priority_class = f"priority-{task['priority']}"
                status_class = f"status-{task['status']}"
                
                html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{task['title']}</td>
                            <td class="{priority_class}">{task['priority'].upper()}</td>
                            <td class="{status_class}">{task['status'].replace('_', ' ').title()}</td>
                            <td>{task['technician_name'] or 'Non assigné'}</td>
                        </tr>
                """
                
                if task['description']:
                    html += f"""
                        <tr class="task-description">
                            <td></td>
                            <td colspan="4"><em>{task['description']}</em></td>
                        </tr>
                    """
            
            html += """
                    </tbody>
                </table>
            </div>
            """
        
        if interventions_data:
            html += """
            <div class="section">
                <h3>INTERVENTIONS RÉALISÉES</h3>
            """
            
            for intervention in interventions_data:
                duration = ""
                if intervention['started_at'] and intervention['ended_at']:
                    duration_min = (intervention['ended_at'] - intervention['started_at']).total_seconds() / 60
                    duration = f" - Durée: {int(duration_min // 60)}h{int(duration_min % 60):02d}"
                
                html += f"""
                <div class="intervention">
                    <h4>{intervention['task_title']}</h4>
                    <div class="intervention-meta">
                        <strong>Technicien:</strong> {intervention['technician_name'] or 'N/A'}<br>
                        <strong>Début:</strong> {intervention['started_at'].strftime('%d/%m/%Y %H:%M') if intervention['started_at'] else 'N/A'}<br>
                        <strong>Fin:</strong> {intervention['ended_at'].strftime('%d/%m/%Y %H:%M') if intervention['ended_at'] else 'En cours'}{duration}<br>
                        <strong>Résultat:</strong> {intervention['result_status'] or 'En cours'}
                    </div>
                    
                    <div class="intervention-stats">
                        <span class="stat">📝 {intervention['notes_count']} note(s)</span>
                        <span class="stat">📷 {intervention['media_count']} média(s)</span>
                    </div>
                </div>
                """
            
            html += "</div>"
        
        html += """
            <div class="footer">
                <div class="signature-area">
                    <div class="signature-box">
                        <div class="signature-line"></div>
                        <div class="signature-label">Signature Technicien</div>
                    </div>
                    <div class="signature-box">
                        <div class="signature-line"></div>
                        <div class="signature-label">Signature Client</div>
                    </div>
                </div>
                
                <div class="footer-info">
                    <p><strong>ChronoTech</strong> - Service d'intervention technique</p>
                    <p>Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _get_pdf_css(self) -> str:
        """CSS professionnel pour les PDFs"""
        return """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: "Page " counter(page) " sur " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }
        
        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #667eea;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 24px;
            margin: 0;
            font-weight: bold;
        }
        
        .header h2 {
            color: #333;
            font-size: 18px;
            margin: 10px 0;
        }
        
        .date {
            color: #666;
            font-size: 10px;
        }
        
        .section {
            margin-bottom: 25px;
            page-break-inside: avoid;
        }
        
        .section h3 {
            background: #667eea;
            color: white;
            padding: 8px 12px;
            margin: 0 0 15px 0;
            font-size: 14px;
            text-transform: uppercase;
        }
        
        .info-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .info-table td {
            padding: 8px;
            border: 1px solid #ddd;
        }
        
        .info-table .label {
            background: #f8f9fa;
            font-weight: bold;
            width: 25%;
        }
        
        .tasks-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        
        .tasks-table th {
            background: #667eea;
            color: white;
            padding: 8px;
            text-align: left;
            font-weight: bold;
        }
        
        .tasks-table td {
            padding: 6px 8px;
            border: 1px solid #ddd;
            vertical-align: top;
        }
        
        .tasks-table .task-description td {
            font-style: italic;
            color: #666;
            font-size: 10px;
        }
        
        .priority-urgent { background: #ffe6e6; color: #c62828; font-weight: bold; }
        .priority-high { background: #fff3e0; color: #ef6c00; font-weight: bold; }
        .priority-medium { background: #e3f2fd; color: #1976d2; }
        .priority-low { background: #f3e5f5; color: #7b1fa2; }
        
        .status-done { background: #e8f5e8; color: #2e7d32; }
        .status-in_progress { background: #fff9c4; color: #f57f17; }
        .status-assigned { background: #e1f5fe; color: #0277bd; }
        .status-pending { background: #fce4ec; color: #ad1457; }
        
        .intervention {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }
        
        .intervention h4 {
            color: #667eea;
            margin: 0 0 10px 0;
            font-size: 14px;
        }
        
        .intervention-meta {
            font-size: 11px;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        
        .intervention-stats {
            display: flex;
            gap: 15px;
        }
        
        .intervention-stats .stat {
            font-size: 10px;
            color: #666;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }
        
        .signature-area {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        
        .signature-box {
            width: 40%;
            text-align: center;
        }
        
        .signature-line {
            border-bottom: 1px solid #333;
            height: 40px;
            margin-bottom: 5px;
        }
        
        .signature-label {
            font-size: 10px;
            color: #666;
        }
        
        .footer-info {
            text-align: center;
            font-size: 10px;
            color: #666;
        }
        
        .footer-info p {
            margin: 5px 0;
        }
        """
    
    def _generate_intervention_weasyprint_pdf(self, intervention_data: Dict, notes_data: List, media_data: List) -> str:
        """Générer PDF d'intervention avec WeasyPrint"""
        from services.pdf_templates import generate_intervention_weasyprint_pdf
        return generate_intervention_weasyprint_pdf(self, intervention_data, notes_data, media_data)
    
    def _generate_intervention_reportlab_pdf(self, intervention_data: Dict, notes_data: List, media_data: List) -> str:
        """Générer PDF d'intervention avec ReportLab"""
        from services.pdf_templates import generate_intervention_reportlab_pdf
        return generate_intervention_reportlab_pdf(self, intervention_data, notes_data, media_data)

# Instance globale du service
pdf_generator = PDFGeneratorService()
