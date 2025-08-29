/**
 * PDF Viewer Component - Sprint 3
 * Gestionnaire de visualisation et d'impression PDF
 */

class PDFViewer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            showToolbar: true,
            allowDownload: true,
            allowPrint: true,
            scale: 1.0,
            maxScale: 3.0,
            minScale: 0.5,
            ...options
        };
        
        this.currentDocument = null;
        this.currentPage = 1;
        this.totalPages = 0;
        this.scale = this.options.scale;
        
        this.init();
    }
    
    init() {
        this.createViewer();
        this.setupEventListeners();
    }
    
    createViewer() {
        this.container.className = 'pdf-viewer';
        this.container.innerHTML = `
            ${this.options.showToolbar ? this.createToolbar() : ''}
            <div class="pdf-viewport">
                <div class="pdf-content">
                    <div class="pdf-placeholder">
                        <div class="placeholder-icon">📄</div>
                        <div class="placeholder-text">Aucun document chargé</div>
                    </div>
                </div>
            </div>
            <div class="pdf-loading" style="display: none;">
                <div class="loading-spinner"></div>
                <div class="loading-text">Chargement du document...</div>
            </div>
        `;
    }
    
    createToolbar() {
        return `
            <div class="pdf-toolbar">
                <div class="toolbar-group">
                    <button class="toolbar-btn" data-action="prev-page" title="Page précédente" disabled>
                        <span class="icon">⬅️</span>
                    </button>
                    <div class="page-info">
                        <span class="current-page">0</span>
                        <span class="page-separator">/</span>
                        <span class="total-pages">0</span>
                    </div>
                    <button class="toolbar-btn" data-action="next-page" title="Page suivante" disabled>
                        <span class="icon">➡️</span>
                    </button>
                </div>
                
                <div class="toolbar-group">
                    <button class="toolbar-btn" data-action="zoom-out" title="Zoom arrière">
                        <span class="icon">🔍-</span>
                    </button>
                    <div class="zoom-info">
                        <span class="zoom-level">${Math.round(this.scale * 100)}%</span>
                    </div>
                    <button class="toolbar-btn" data-action="zoom-in" title="Zoom avant">
                        <span class="icon">🔍+</span>
                    </button>
                    <button class="toolbar-btn" data-action="fit-width" title="Ajuster à la largeur">
                        <span class="icon">📏</span>
                    </button>
                </div>
                
                <div class="toolbar-group">
                    ${this.options.allowDownload ? `
                        <button class="toolbar-btn" data-action="download" title="Télécharger">
                            <span class="icon">💾</span>
                        </button>
                    ` : ''}
                    ${this.options.allowPrint ? `
                        <button class="toolbar-btn" data-action="print" title="Imprimer">
                            <span class="icon">🖨️</span>
                        </button>
                    ` : ''}
                    <button class="toolbar-btn" data-action="fullscreen" title="Plein écran">
                        <span class="icon">⛶</span>
                    </button>
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        // Boutons de la toolbar
        this.container.addEventListener('click', this.handleToolbarClick.bind(this));
        
        // Raccourcis clavier
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        
        // Zoom avec molette
        this.container.addEventListener('wheel', this.handleWheel.bind(this));
        
        // Responsive
        window.addEventListener('resize', this.handleResize.bind(this));
        
        // Touch pour mobile
        this.setupTouchEvents();
    }
    
    setupTouchEvents() {
        let startDistance = 0;
        let startScale = 1;
        
        this.container.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                startDistance = this.getTouchDistance(e.touches);
                startScale = this.scale;
            }
        });
        
        this.container.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                const currentDistance = this.getTouchDistance(e.touches);
                const ratio = currentDistance / startDistance;
                const newScale = startScale * ratio;
                
                this.setZoom(newScale);
            }
        });
    }
    
    getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    // ===== ÉVÉNEMENTS =====
    
    handleToolbarClick(e) {
        const action = e.target.closest('[data-action]')?.dataset.action;
        if (!action) return;
        
        switch (action) {
            case 'prev-page':
                this.previousPage();
                break;
            case 'next-page':
                this.nextPage();
                break;
            case 'zoom-in':
                this.zoomIn();
                break;
            case 'zoom-out':
                this.zoomOut();
                break;
            case 'fit-width':
                this.fitToWidth();
                break;
            case 'download':
                this.download();
                break;
            case 'print':
                this.print();
                break;
            case 'fullscreen':
                this.toggleFullscreen();
                break;
        }
    }
    
    handleKeyDown(e) {
        if (!this.currentDocument) return;
        
        switch (e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                this.previousPage();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.nextPage();
                break;
            case '+':
            case '=':
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.zoomIn();
                }
                break;
            case '-':
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.zoomOut();
                }
                break;
            case 'p':
                if (e.ctrlKey && this.options.allowPrint) {
                    e.preventDefault();
                    this.print();
                }
                break;
            case 'f':
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.toggleFullscreen();
                }
                break;
        }
    }
    
    handleWheel(e) {
        if (e.ctrlKey) {
            e.preventDefault();
            
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            const newScale = Math.max(this.options.minScale, 
                            Math.min(this.options.maxScale, this.scale + delta));
            
            this.setZoom(newScale);
        }
    }
    
    handleResize() {
        // Redimensionner le viewport
        if (this.currentDocument) {
            this.renderCurrentPage();
        }
    }
    
    // ===== CHARGEMENT DOCUMENTS =====
    
    async loadDocument(url) {
        this.showLoading();
        
        try {
            // Simuler le chargement d'un PDF
            await this.fetchDocument(url);
            
            this.currentDocument = url;
            this.currentPage = 1;
            this.totalPages = await this.getDocumentPageCount(url);
            
            this.hideLoading();
            this.updateUI();
            this.renderCurrentPage();
            
        } catch (error) {
            this.hideLoading();
            this.showError('Erreur lors du chargement du document: ' + error.message);
        }
    }
    
    async fetchDocument(url) {
        // Simuler une requête HTTP
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (url.includes('error')) {
                    reject(new Error('Document introuvable'));
                } else {
                    resolve();
                }
            }, 1000);
        });
    }
    
    async getDocumentPageCount(url) {
        // En réalité, ça serait récupéré via une API ou PDF.js
        return Math.floor(Math.random() * 10) + 1;
    }
    
    // ===== RENDU =====
    
    renderCurrentPage() {
        if (!this.currentDocument) return;
        
        const content = this.container.querySelector('.pdf-content');
        content.innerHTML = this.createPageHTML();
        
        // Appliquer le zoom
        const page = content.querySelector('.pdf-page');
        if (page) {
            page.style.transform = `scale(${this.scale})`;
        }
    }
    
    createPageHTML() {
        // Simuler le rendu d'une page PDF
        return `
            <div class="pdf-page" data-page="${this.currentPage}">
                <div class="page-content">
                    <div class="page-header">
                        <h1>Document PDF - Page ${this.currentPage}</h1>
                        <div class="document-info">
                            ${this.currentDocument}
                        </div>
                    </div>
                    <div class="page-body">
                        <p>Contenu de la page ${this.currentPage} du document PDF.</p>
                        <p>Cette vue serait remplacée par le vrai rendu PDF avec PDF.js.</p>
                        <div class="sample-table">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Élément</th>
                                        <th>Description</th>
                                        <th>Statut</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>Tâche ${this.currentPage}-1</td>
                                        <td>Description de la tâche</td>
                                        <td>Terminé</td>
                                    </tr>
                                    <tr>
                                        <td>Tâche ${this.currentPage}-2</td>
                                        <td>Autre description</td>
                                        <td>En cours</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // ===== NAVIGATION =====
    
    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.renderCurrentPage();
            this.updateUI();
        }
    }
    
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderCurrentPage();
            this.updateUI();
        }
    }
    
    goToPage(pageNumber) {
        if (pageNumber >= 1 && pageNumber <= this.totalPages) {
            this.currentPage = pageNumber;
            this.renderCurrentPage();
            this.updateUI();
        }
    }
    
    // ===== ZOOM =====
    
    zoomIn() {
        const newScale = Math.min(this.options.maxScale, this.scale + 0.25);
        this.setZoom(newScale);
    }
    
    zoomOut() {
        const newScale = Math.max(this.options.minScale, this.scale - 0.25);
        this.setZoom(newScale);
    }
    
    setZoom(scale) {
        this.scale = Math.max(this.options.minScale, 
                            Math.min(this.options.maxScale, scale));
        
        const page = this.container.querySelector('.pdf-page');
        if (page) {
            page.style.transform = `scale(${this.scale})`;
            page.style.transformOrigin = 'top left';
        }
        
        this.updateZoomInfo();
    }
    
    fitToWidth() {
        const viewport = this.container.querySelector('.pdf-viewport');
        const page = this.container.querySelector('.pdf-page');
        
        if (viewport && page) {
            const viewportWidth = viewport.clientWidth - 40; // padding
            const pageWidth = page.scrollWidth;
            const scale = viewportWidth / pageWidth;
            
            this.setZoom(scale);
        }
    }
    
    // ===== ACTIONS =====
    
    download() {
        if (!this.currentDocument) return;
        
        // Créer un lien de téléchargement
        const link = document.createElement('a');
        link.href = this.currentDocument;
        link.download = this.getDocumentName();
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showToast('Téléchargement démarré', 'success');
    }
    
    print() {
        if (!this.currentDocument) return;
        
        // Ouvrir la vue d'impression
        const printWindow = window.open(this.currentDocument, '_blank');
        if (printWindow) {
            printWindow.onload = () => {
                printWindow.print();
            };
        } else {
            this.showToast('Impossible d\'ouvrir la vue d\'impression', 'error');
        }
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.container.requestFullscreen().catch(() => {
                this.showToast('Plein écran non supporté', 'error');
            });
        } else {
            document.exitFullscreen();
        }
    }
    
    // ===== INTERFACE =====
    
    updateUI() {
        // Mettre à jour les informations de page
        const currentPageEl = this.container.querySelector('.current-page');
        const totalPagesEl = this.container.querySelector('.total-pages');
        
        if (currentPageEl) currentPageEl.textContent = this.currentPage;
        if (totalPagesEl) totalPagesEl.textContent = this.totalPages;
        
        // Mettre à jour les boutons de navigation
        const prevBtn = this.container.querySelector('[data-action="prev-page"]');
        const nextBtn = this.container.querySelector('[data-action="next-page"]');
        
        if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
        if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;
        
        this.updateZoomInfo();
    }
    
    updateZoomInfo() {
        const zoomEl = this.container.querySelector('.zoom-level');
        if (zoomEl) {
            zoomEl.textContent = `${Math.round(this.scale * 100)}%`;
        }
    }
    
    showLoading() {
        const loading = this.container.querySelector('.pdf-loading');
        if (loading) loading.style.display = 'flex';
    }
    
    hideLoading() {
        const loading = this.container.querySelector('.pdf-loading');
        if (loading) loading.style.display = 'none';
    }
    
    showError(message) {
        const content = this.container.querySelector('.pdf-content');
        content.innerHTML = `
            <div class="pdf-error">
                <div class="error-icon">⚠️</div>
                <div class="error-message">${message}</div>
                <button class="retry-btn" onclick="location.reload()">Réessayer</button>
            </div>
        `;
    }
    
    showToast(message, type = 'info') {
        // Créer un toast temporaire
        const toast = document.createElement('div');
        toast.className = `pdf-toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(toast);
        
        // Animation d'entrée
        setTimeout(() => toast.classList.add('toast-show'), 100);
        
        // Auto-suppression
        setTimeout(() => {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // ===== UTILITAIRES =====
    
    getDocumentName() {
        if (!this.currentDocument) return 'document.pdf';
        
        const url = new URL(this.currentDocument);
        const pathname = url.pathname;
        const filename = pathname.split('/').pop();
        
        return filename || 'document.pdf';
    }
    
    // ===== API PUBLIQUE =====
    
    getCurrentPage() {
        return this.currentPage;
    }
    
    getTotalPages() {
        return this.totalPages;
    }
    
    getCurrentScale() {
        return this.scale;
    }
    
    isDocumentLoaded() {
        return !!this.currentDocument;
    }
    
    destroy() {
        this.currentDocument = null;
        this.container.innerHTML = '';
        document.removeEventListener('keydown', this.handleKeyDown.bind(this));
        window.removeEventListener('resize', this.handleResize.bind(this));
    }
}

// Export pour utilisation
window.PDFViewer = PDFViewer;

// Styles CSS en ligne pour un démarrage rapide
if (!document.querySelector('#pdf-viewer-styles')) {
    const styles = document.createElement('style');
    styles.id = 'pdf-viewer-styles';
    styles.textContent = `
        .pdf-viewer {
            display: flex;
            flex-direction: column;
            height: 100%;
            background: #f0f0f0;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .pdf-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #fff;
            border-bottom: 1px solid #ddd;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .toolbar-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .toolbar-btn {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 6px 10px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s ease;
        }
        
        .toolbar-btn:hover:not(:disabled) {
            background: #e9ecef;
            border-color: #adb5bd;
        }
        
        .toolbar-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .page-info, .zoom-info {
            padding: 6px 12px;
            background: #e9ecef;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .pdf-viewport {
            flex: 1;
            overflow: auto;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        
        .pdf-content {
            max-width: 100%;
        }
        
        .pdf-page {
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin: 0 auto;
            min-height: 400px;
            transition: transform 0.2s ease;
        }
        
        .pdf-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 300px;
            color: #6c757d;
        }
        
        .placeholder-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        .pdf-loading {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.9);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .pdf-error {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 300px;
            color: #dc3545;
        }
        
        .error-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        .retry-btn {
            margin-top: 16px;
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .pdf-toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 16px;
            border-radius: 4px;
            color: white;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            z-index: 1000;
        }
        
        .pdf-toast.toast-show {
            transform: translateX(0);
        }
        
        .toast-success { background: #28a745; }
        .toast-error { background: #dc3545; }
        .toast-info { background: #17a2b8; }
        
        @media (max-width: 768px) {
            .pdf-toolbar {
                padding: 6px 8px;
            }
            
            .toolbar-group {
                gap: 4px;
            }
            
            .toolbar-btn {
                padding: 8px;
                font-size: 16px;
            }
            
            .pdf-viewport {
                padding: 10px;
            }
        }
    `;
    document.head.appendChild(styles);
}
