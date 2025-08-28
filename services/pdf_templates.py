"""
Template PDF pour les rapports d'intervention - WeasyPrint
"""

def generate_intervention_weasyprint_pdf(pdf_generator, intervention_data, notes_data, media_data):
    """Générer PDF d'intervention avec WeasyPrint"""
    import os
    from datetime import datetime
    
    # Template HTML pour intervention
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport d'Intervention #{intervention_data['id']}</title>
    </head>
    <body>
        <div class="header">
            <h1>CHRONOTECH</h1>
            <h2>RAPPORT D'INTERVENTION #{intervention_data['id']}</h2>
            <div class="date">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</div>
        </div>
        
        <div class="section">
            <h3>INFORMATIONS GÉNÉRALES</h3>
            <table class="info-table">
                <tr><td class="label">Bon de travail:</td><td>#{intervention_data['claim_number']} - {intervention_data['wo_title']}</td></tr>
                <tr><td class="label">Tâche:</td><td>{intervention_data['task_title']}</td></tr>
                <tr><td class="label">Priorité:</td><td class="priority-{intervention_data['priority']}">{intervention_data['priority'].upper()}</td></tr>
                <tr><td class="label">Technicien:</td><td>{intervention_data['technician_name'] or 'Non assigné'}</td></tr>
                <tr><td class="label">Client:</td><td>{intervention_data['customer_name']}</td></tr>
                <tr><td class="label">Téléphone:</td><td>{intervention_data['customer_phone'] or '-'}</td></tr>
            </table>
        </div>
    """
    
    # Informations véhicule si disponibles
    if intervention_data['make'] and intervention_data['model']:
        html_content += f"""
        <div class="section">
            <h3>VÉHICULE</h3>
            <table class="info-table">
                <tr><td class="label">Véhicule:</td><td>{intervention_data['make']} {intervention_data['model']} ({intervention_data['year'] or 'N/A'})</td></tr>
                <tr><td class="label">Plaque:</td><td>{intervention_data['license_plate'] or '-'}</td></tr>
            </table>
        </div>
        """
    
    # Description de la tâche
    if intervention_data['task_description']:
        html_content += f"""
        <div class="section">
            <h3>DESCRIPTION DE LA TÂCHE</h3>
            <div class="task-description">
                {intervention_data['task_description']}
            </div>
        </div>
        """
    
    # Détails temporels
    duration_text = ""
    if intervention_data['duration_minutes']:
        hours = intervention_data['duration_minutes'] // 60
        minutes = intervention_data['duration_minutes'] % 60
        duration_text = f"{hours}h{minutes:02d}"
    
    html_content += f"""
    <div class="section">
        <h3>TEMPS D'INTERVENTION</h3>
        <table class="info-table">
            <tr><td class="label">Début:</td><td>{intervention_data['started_at'].strftime('%d/%m/%Y %H:%M') if intervention_data['started_at'] else 'Non démarré'}</td></tr>
            <tr><td class="label">Fin:</td><td>{intervention_data['ended_at'].strftime('%d/%m/%Y %H:%M') if intervention_data['ended_at'] else 'En cours'}</td></tr>
            <tr><td class="label">Durée:</td><td>{duration_text or 'N/A'}</td></tr>
            <tr><td class="label">Statut:</td><td class="status-{intervention_data['result_status'] or 'pending'}">{intervention_data['result_status'] or 'En cours'}</td></tr>
        </table>
    </div>
    """
    
    # Notes d'intervention
    if notes_data:
        html_content += """
        <div class="section">
            <h3>NOTES D'INTERVENTION</h3>
        """
        
        for note in notes_data:
            html_content += f"""
            <div class="note-item">
                <div class="note-header">
                    <strong>{note['author_name']}</strong> - {note['created_at'].strftime('%d/%m/%Y %H:%M')}
                </div>
                <div class="note-content">
                    {note['note_text']}
                </div>
            </div>
            """
        
        html_content += "</div>"
    
    # Médias (photos)
    if media_data:
        html_content += """
        <div class="section">
            <h3>PHOTOS ET DOCUMENTS</h3>
            <div class="media-grid">
        """
        
        for media in media_data:
            media_type = "📷" if media['media_type'] == 'photo' else "📄"
            html_content += f"""
            <div class="media-item">
                <div class="media-icon">{media_type}</div>
                <div class="media-info">
                    <div class="media-filename">{media['filename']}</div>
                    <div class="media-meta">{media['created_at'].strftime('%d/%m/%Y %H:%M')}</div>
                </div>
            </div>
            """
        
        html_content += """
            </div>
        </div>
        """
    
    # Signature et conclusion
    html_content += f"""
    <div class="section">
        <h3>RÉSUMÉ</h3>
        <div class="summary-box">
            <p><strong>Intervention:</strong> {intervention_data['task_title']}</p>
            <p><strong>Résultat:</strong> {intervention_data['result_status'] or 'En cours'}</p>
            <p><strong>Durée totale:</strong> {duration_text or 'N/A'}</p>
            <p><strong>Notes:</strong> {len(notes_data)} note(s) ajoutée(s)</p>
            <p><strong>Médias:</strong> {len(media_data)} fichier(s) joint(s)</p>
        </div>
    </div>
    
    <div class="footer">
        <div class="signature-area">
            <div class="signature-box">
                <div class="signature-line"></div>
                <div class="signature-label">Signature Technicien</div>
                <div class="signature-name">{intervention_data['technician_name'] or 'N/A'}</div>
            </div>
            <div class="signature-box">
                <div class="signature-line"></div>
                <div class="signature-label">Signature Client</div>
                <div class="signature-name">{intervention_data['customer_name']}</div>
            </div>
        </div>
        
        <div class="footer-info">
            <p><strong>ChronoTech</strong> - Rapport d'intervention technique</p>
            <p>Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            <p>Intervention #{intervention_data['id']} - Bon de travail #{intervention_data['claim_number']}</p>
        </div>
    </div>
    </body>
    </html>
    """
    
    # CSS spécifique pour les interventions
    css_content = pdf_generator._get_pdf_css() + """
    .task-description {
        background: #f8f9fa;
        padding: 15px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
        line-height: 1.6;
    }
    
    .note-item {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        margin-bottom: 15px;
        overflow: hidden;
    }
    
    .note-header {
        background: #f5f5f5;
        padding: 8px 12px;
        font-size: 11px;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .note-content {
        padding: 12px;
        line-height: 1.5;
    }
    
    .media-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
        margin-top: 15px;
    }
    
    .media-item {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        text-align: center;
        background: #fafafa;
    }
    
    .media-icon {
        font-size: 24px;
        margin-bottom: 8px;
    }
    
    .media-filename {
        font-size: 11px;
        font-weight: bold;
        margin-bottom: 4px;
        word-break: break-all;
    }
    
    .media-meta {
        font-size: 9px;
        color: #666;
    }
    
    .summary-box {
        background: #e3f2fd;
        border: 1px solid #90caf9;
        border-radius: 5px;
        padding: 15px;
        margin: 15px 0;
    }
    
    .summary-box p {
        margin: 5px 0;
        font-size: 12px;
    }
    
    .signature-name {
        font-size: 10px;
        color: #666;
        margin-top: 3px;
    }
    
    /* Status colors */
    .status-completed { background: #e8f5e8; color: #2e7d32; padding: 3px 8px; border-radius: 3px; }
    .status-in_progress { background: #fff9c4; color: #f57f17; padding: 3px 8px; border-radius: 3px; }
    .status-pending { background: #fce4ec; color: #ad1457; padding: 3px 8px; border-radius: 3px; }
    .status-cancelled { background: #ffebee; color: #c62828; padding: 3px 8px; border-radius: 3px; }
    """
    
    # Générer le PDF
    filename = f"intervention_report_{intervention_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(pdf_generator.output_path, filename)
    
    from weasyprint import HTML, CSS
    
    html = HTML(string=html_content, base_url=pdf_generator.static_path)
    css = CSS(string=css_content, font_config=pdf_generator.font_config)
    
    html.write_pdf(pdf_path, stylesheets=[css], font_config=pdf_generator.font_config)
    
    return pdf_path

def generate_intervention_reportlab_pdf(pdf_generator, intervention_data, notes_data, media_data):
    """Générer PDF d'intervention avec ReportLab"""
    import os
    from datetime import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    filename = f"intervention_report_{intervention_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(pdf_generator.output_path, filename)
    
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
        spaceAfter=30,
        textColor=colors.HexColor('#667eea')
    )
    
    story.append(Paragraph("CHRONOTECH", title_style))
    story.append(Paragraph(f"RAPPORT D'INTERVENTION #{intervention_data['id']}", title_style))
    story.append(Spacer(1, 20))
    
    # Informations générales
    info_data = [
        ['Bon de travail:', f"#{intervention_data['claim_number']} - {intervention_data['wo_title']}"],
        ['Tâche:', intervention_data['task_title']],
        ['Priorité:', intervention_data['priority'].upper()],
        ['Technicien:', intervention_data['technician_name'] or 'Non assigné'],
        ['Client:', intervention_data['customer_name']],
        ['Téléphone:', intervention_data['customer_phone'] or '-']
    ]
    
    if intervention_data['make'] and intervention_data['model']:
        info_data.extend([
            ['Véhicule:', f"{intervention_data['make']} {intervention_data['model']} ({intervention_data['year'] or 'N/A'})"],
            ['Plaque:', intervention_data['license_plate'] or '-']
        ])
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    story.append(Paragraph("INFORMATIONS GÉNÉRALES", styles['Heading2']))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Temps d'intervention
    duration_text = ""
    if intervention_data['duration_minutes']:
        hours = intervention_data['duration_minutes'] // 60
        minutes = intervention_data['duration_minutes'] % 60
        duration_text = f"{hours}h{minutes:02d}"
    
    time_data = [
        ['Début:', intervention_data['started_at'].strftime('%d/%m/%Y %H:%M') if intervention_data['started_at'] else 'Non démarré'],
        ['Fin:', intervention_data['ended_at'].strftime('%d/%m/%Y %H:%M') if intervention_data['ended_at'] else 'En cours'],
        ['Durée:', duration_text or 'N/A'],
        ['Statut:', intervention_data['result_status'] or 'En cours']
    ]
    
    time_table = Table(time_data, colWidths=[2*inch, 4*inch])
    time_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    
    story.append(Paragraph("TEMPS D'INTERVENTION", styles['Heading2']))
    story.append(time_table)
    story.append(Spacer(1, 20))
    
    # Description de la tâche
    if intervention_data['task_description']:
        story.append(Paragraph("DESCRIPTION DE LA TÂCHE", styles['Heading2']))
        story.append(Paragraph(intervention_data['task_description'], styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Notes
    if notes_data:
        story.append(Paragraph("NOTES D'INTERVENTION", styles['Heading2']))
        for note in notes_data:
            note_header = f"<b>{note['author_name']}</b> - {note['created_at'].strftime('%d/%m/%Y %H:%M')}"
            story.append(Paragraph(note_header, styles['Normal']))
            story.append(Paragraph(note['note_text'], styles['Normal']))
            story.append(Spacer(1, 10))
    
    # Résumé
    story.append(Paragraph("RÉSUMÉ", styles['Heading2']))
    summary_text = f"""
    <b>Intervention:</b> {intervention_data['task_title']}<br/>
    <b>Résultat:</b> {intervention_data['result_status'] or 'En cours'}<br/>
    <b>Durée totale:</b> {duration_text or 'N/A'}<br/>
    <b>Notes:</b> {len(notes_data)} note(s) ajoutée(s)<br/>
    <b>Médias:</b> {len(media_data)} fichier(s) joint(s)
    """
    story.append(Paragraph(summary_text, styles['Normal']))
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_path

# Intégrer les méthodes dans la classe PDFGeneratorService
def extend_pdf_generator():
    """Étendre le PDFGeneratorService avec les méthodes d'intervention"""
    from services.pdf_generator import PDFGeneratorService
    
    PDFGeneratorService._generate_intervention_weasyprint_pdf = generate_intervention_weasyprint_pdf
    PDFGeneratorService._generate_intervention_reportlab_pdf = generate_intervention_reportlab_pdf
