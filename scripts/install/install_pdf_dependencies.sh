#!/bin/bash

# Script d'installation des dépendances PDF - Sprint 3
# Ce script installe WeasyPrint et ReportLab pour la génération de PDF

echo "🚀 Installation des dépendances PDF pour ChronoTech Sprint 3"
echo "============================================================="

# Vérifier si nous sommes dans le bon répertoire
if [ ! -f "requirements.txt" ]; then
    echo "❌ Erreur: requirements.txt non trouvé. Assurez-vous d'être dans le répertoire ChronoTech."
    exit 1
fi

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Vérifier Python
if ! command_exists python3; then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

echo "✅ Python 3 détecté: $(python3 --version)"

# Vérifier pip
if ! command_exists pip3; then
    echo "❌ pip3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

echo "✅ pip3 détecté: $(pip3 --version)"

# Installer les dépendances système pour WeasyPrint (Ubuntu/Debian)
echo ""
echo "📦 Installation des dépendances système pour WeasyPrint..."

# Détecter la distribution
if command_exists apt-get; then
    echo "🔍 Détection d'un système basé sur Debian/Ubuntu"
    
    # Mettre à jour les packages
    echo "📥 Mise à jour des packages système..."
    sudo apt-get update
    
    # Installer les dépendances WeasyPrint
    echo "📦 Installation des dépendances WeasyPrint..."
    sudo apt-get install -y \
        python3-dev \
        python3-pip \
        python3-cffi \
        python3-brotli \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-liberation \
        fonts-dejavu-core \
        fontconfig
    
    echo "✅ Dépendances système installées"

elif command_exists yum; then
    echo "🔍 Détection d'un système basé sur RedHat/CentOS"
    
    # Installer les dépendances WeasyPrint pour CentOS/RHEL
    sudo yum install -y \
        python3-devel \
        python3-pip \
        python3-cffi \
        cairo-devel \
        pango-devel \
        gdk-pixbuf2-devel \
        libffi-devel \
        shared-mime-info \
        liberation-fonts \
        dejavu-fonts \
        fontconfig
    
    echo "✅ Dépendances système installées"

elif command_exists pacman; then
    echo "🔍 Détection d'un système Arch Linux"
    
    # Installer les dépendances WeasyPrint pour Arch
    sudo pacman -S --noconfirm \
        python-pip \
        python-cffi \
        cairo \
        pango \
        gdk-pixbuf2 \
        libffi \
        shared-mime-info \
        ttf-liberation \
        ttf-dejavu \
        fontconfig
    
    echo "✅ Dépendances système installées"

else
    echo "⚠️  Distribution non reconnue. Vous devrez installer manuellement les dépendances WeasyPrint."
    echo "    Consultez: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation"
fi

# Créer un environnement virtuel si il n'existe pas
if [ ! -d "venv" ]; then
    echo ""
    echo "🐍 Création de l'environnement virtuel Python..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "🔌 Activation de l'environnement virtuel..."
source venv/bin/activate

# Mettre à jour pip
echo "⬆️  Mise à jour de pip..."
pip install --upgrade pip setuptools wheel

# Installer les dépendances Python
echo ""
echo "📚 Installation des dépendances Python..."

# Installer ReportLab d'abord (plus simple)
echo "📄 Installation de ReportLab..."
pip install reportlab>=4.0.0

if [ $? -eq 0 ]; then
    echo "✅ ReportLab installé avec succès"
else
    echo "❌ Erreur lors de l'installation de ReportLab"
    exit 1
fi

# Tenter d'installer WeasyPrint
echo "🎨 Installation de WeasyPrint..."
pip install weasyprint>=60.0

if [ $? -eq 0 ]; then
    echo "✅ WeasyPrint installé avec succès"
    WEASYPRINT_OK=true
else
    echo "⚠️  Échec de l'installation de WeasyPrint (ReportLab sera utilisé comme fallback)"
    WEASYPRINT_OK=false
fi

# Installer les autres dépendances
echo "📦 Installation des autres dépendances..."
pip install flask-login>=0.6.2

# Test des installations
echo ""
echo "🧪 Test des installations..."

# Test ReportLab
python3 -c "
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate
    print('✅ ReportLab: OK')
except ImportError as e:
    print(f'❌ ReportLab: ERREUR - {e}')
"

# Test WeasyPrint si installé
if [ "$WEASYPRINT_OK" = true ]; then
    python3 -c "
try:
    from weasyprint import HTML, CSS
    print('✅ WeasyPrint: OK')
except ImportError as e:
    print(f'❌ WeasyPrint: ERREUR - {e}')
"
fi

# Test Flask-Login
python3 -c "
try:
    from flask_login import login_required
    print('✅ Flask-Login: OK')
except ImportError as e:
    print(f'❌ Flask-Login: ERREUR - {e}')
"

# Créer les dossiers nécessaires
echo ""
echo "📁 Création des dossiers PDF..."

mkdir -p static/generated_pdfs
mkdir -p templates/pdf
mkdir -p services

echo "✅ Dossiers créés:"
echo "   - static/generated_pdfs/ (pour les PDFs générés)"
echo "   - templates/pdf/ (pour les templates PDF)"
echo "   - services/ (pour les services PDF)"

# Permissions
chmod 755 static/generated_pdfs
chmod 755 templates/pdf
chmod 755 services

# Créer un fichier de test
echo ""
echo "🧪 Création d'un test PDF..."

cat > test_pdf_generation.py << 'EOF'
#!/usr/bin/env python3
"""
Test de génération PDF - Sprint 3
"""
import os
import sys
from datetime import datetime

def test_reportlab():
    """Test ReportLab"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        # Créer un PDF de test
        filename = f"test_reportlab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join('static', 'generated_pdfs', filename)
        
        doc = SimpleDocDocument(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("Test ReportLab - ChronoTech Sprint 3", styles['Title']))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        
        doc.build(story)
        
        print(f"✅ ReportLab: PDF généré avec succès ({filename})")
        return True
        
    except Exception as e:
        print(f"❌ ReportLab: Erreur - {e}")
        return False

def test_weasyprint():
    """Test WeasyPrint"""
    try:
        from weasyprint import HTML
        
        # HTML de test
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Test WeasyPrint</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                h1 {{ color: #667eea; }}
            </style>
        </head>
        <body>
            <h1>Test WeasyPrint - ChronoTech Sprint 3</h1>
            <p>Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p>WeasyPrint fonctionne correctement !</p>
        </body>
        </html>
        """
        
        # Créer un PDF de test
        filename = f"test_weasyprint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join('static', 'generated_pdfs', filename)
        
        html = HTML(string=html_content)
        html.write_pdf(filepath)
        
        print(f"✅ WeasyPrint: PDF généré avec succès ({filename})")
        return True
        
    except Exception as e:
        print(f"❌ WeasyPrint: Erreur - {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test des librairies PDF...")
    print("=" * 40)
    
    reportlab_ok = test_reportlab()
    weasyprint_ok = test_weasyprint()
    
    print("\n📊 Résumé:")
    print(f"ReportLab: {'✅ OK' if reportlab_ok else '❌ ERREUR'}")
    print(f"WeasyPrint: {'✅ OK' if weasyprint_ok else '❌ ERREUR'}")
    
    if reportlab_ok or weasyprint_ok:
        print("\n🎉 Au moins une librairie PDF fonctionne. Le service PDF sera opérationnel !")
        sys.exit(0)
    else:
        print("\n💥 Aucune librairie PDF ne fonctionne. Vérifiez l'installation.")
        sys.exit(1)
EOF

# Rendre le test exécutable
chmod +x test_pdf_generation.py

# Exécuter le test
echo "▶️  Exécution du test..."
python3 test_pdf_generation.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation terminée avec succès !"
    echo ""
    echo "📋 Résumé:"
    echo "✅ Services PDF installés et testés"
    echo "✅ Dossiers créés"
    echo "✅ Environnement virtuel configuré"
    echo ""
    echo "🚀 Prochaines étapes:"
    echo "1. Ajoutez les blueprints PDF à votre app.py:"
    echo "   from routes.pdf import pdf_bp"
    echo "   app.register_blueprint(pdf_bp)"
    echo ""
    echo "2. Incluez les boutons PDF dans vos templates:"
    echo "   {% include 'components/pdf_buttons.html' %}"
    echo ""
    echo "3. Démarrez votre application ChronoTech !"
    echo ""
    echo "📁 Fichiers PDF générés dans: static/generated_pdfs/"
    
else
    echo ""
    echo "💥 Installation incomplète - voir les erreurs ci-dessus"
    echo ""
    echo "🔧 Solutions possibles:"
    echo "1. Vérifiez les dépendances système"
    echo "2. Installez manuellement: pip install reportlab weasyprint"
    echo "3. Consultez la documentation WeasyPrint"
    
    exit 1
fi
