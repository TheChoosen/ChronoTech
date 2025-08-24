/**
 * Customer 360 - JavaScript centralisé
 * Gestion unifiée de tous les aspects du Customer 360
 */

class Customer360Manager {
    constructor(customerId) {
        this.customerId = customerId;
        this.loadedSections = new Set();
        this.cache = new Map();
        this.eventHandlers = new Map();
        
        this.init();
    }
    
    init() {
        this.setupTabNavigation();
        this.setupKeyboardShortcuts();
        this.setupAutoSave();
        this.setupRealTimeUpdates();
        
        console.log(`Customer 360 Manager initialized for customer ${this.customerId}`);
    }
    
    // ===== NAVIGATION ET LAZY LOADING =====
    
    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
        
        tabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', (e) => {
                const sectionName = button.getAttribute('data-section');
                this.loadSectionIfNeeded(sectionName);
                this.updateUrl(sectionName);
                this.trackSectionView(sectionName);
            });
        });
        
        // Gérer le bouton retour du navigateur
        window.addEventListener('popstate', (e) => {
            const params = new URLSearchParams(window.location.search);
            const tab = params.get('tab') || 'profile';
            this.activateTab(tab);
        });
    }
    
    async loadSectionIfNeeded(sectionName) {
        if (this.loadedSections.has(sectionName)) {
            return;
        }
        
        const placeholder = document.getElementById(`${sectionName}-placeholder`);
        if (!placeholder) {
            return;
        }
        
        try {
            // Vérifier le cache d'abord
            let html = this.cache.get(`section_${sectionName}`);
            
            if (!html) {
                const response = await fetch(`/api/customers/${this.customerId}/sections/${sectionName}`);
                html = await response.text();
                
                // Mettre en cache pour 5 minutes
                this.cache.set(`section_${sectionName}`, html);
                setTimeout(() => {
                    this.cache.delete(`section_${sectionName}`);
                }, 5 * 60 * 1000);
            }
            
            // Remplacer le placeholder
            const tabPane = document.getElementById(sectionName);
            tabPane.innerHTML = html;
            
            // Marquer comme chargée
            this.loadedSections.add(sectionName);
            
            // Initialiser les scripts spécifiques à la section
            this.initializeSectionScripts(sectionName);
            
            // Déclencher l'événement
            this.emit('sectionLoaded', { section: sectionName });
            
        } catch (error) {
            console.error(`Erreur lors du chargement de la section ${sectionName}:`, error);
            this.showSectionError(sectionName, placeholder);
        }
    }
    
    initializeSectionScripts(sectionName) {
        switch(sectionName) {
            case 'finances':
                this.initializeCharts();
                break;
            case 'analytics':
                this.initializeAnalyticsCharts();
                break;
            case 'documents':
                this.initializeDragAndDrop();
                break;
            case 'activity':
                this.initializeInfiniteScroll();
                break;
        }
    }
    
    showSectionError(sectionName, placeholder) {
        placeholder.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                <h5 class="text-danger">Erreur de chargement</h5>
                <p class="text-muted">Impossible de charger cette section.</p>
                <button class="clay-button" onclick="customer360.loadSectionIfNeeded('${sectionName}')">
                    <i class="fas fa-sync me-2"></i>Réessayer
                </button>
            </div>
        `;
    }
    
    // ===== GESTION DES DONNÉES =====
    
    async fetchSectionData(sectionName, params = {}) {
        const cacheKey = `${sectionName}_${JSON.stringify(params)}`;
        
        // Vérifier le cache
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        try {
            const response = await fetch(`/api/customers/${this.customerId}/${sectionName}?${new URLSearchParams(params)}`);
            const data = await response.json();
            
            // Mettre en cache
            this.cache.set(cacheKey, data);
            setTimeout(() => {
                this.cache.delete(cacheKey);
            }, 2 * 60 * 1000); // 2 minutes
            
            return data;
        } catch (error) {
            console.error(`Erreur lors de la récupération des données ${sectionName}:`, error);
            throw error;
        }
    }
    
    async updateSectionData(sectionName, data) {
        try {
            const response = await fetch(`/api/customers/${this.customerId}/${sectionName}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Invalider le cache
                this.invalidateCache(sectionName);
                
                // Déclencher l'événement de mise à jour
                this.emit('dataUpdated', { section: sectionName, data: result.data });
                
                this.showToast('Données mises à jour avec succès', 'success');
            } else {
                throw new Error(result.message || 'Erreur lors de la mise à jour');
            }
            
            return result;
        } catch (error) {
            console.error(`Erreur lors de la mise à jour ${sectionName}:`, error);
            this.showToast('Erreur lors de la mise à jour', 'error');
            throw error;
        }
    }
    
    // ===== RACCOURCIS CLAVIER =====
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + chiffre pour changer d'onglet
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '6') {
                e.preventDefault();
                const sections = ['profile', 'activity', 'finances', 'documents', 'analytics', 'consents'];
                const index = parseInt(e.key) - 1;
                if (sections[index]) {
                    this.activateTab(sections[index]);
                }
            }
            
            // Ctrl/Cmd + S pour sauvegarder
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.saveCurrentSection();
            }
            
            // Ctrl/Cmd + E pour éditer
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                this.editCustomer();
            }
            
            // Escape pour fermer les modals
            if (e.key === 'Escape') {
                this.closeActiveModal();
            }
        });
    }
    
    // ===== AUTO-SAUVEGARDE =====
    
    setupAutoSave() {
        // Sauvegarder automatiquement toutes les 30 secondes
        setInterval(() => {
            this.autoSave();
        }, 30000);
        
        // Sauvegarder avant de quitter la page
        window.addEventListener('beforeunload', () => {
            this.autoSave();
        });
    }
    
    autoSave() {
        // Sauvegarder les données en cours de modification
        const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-section');
        if (activeTab && this.hasUnsavedChanges(activeTab)) {
            this.saveSection(activeTab, true); // silent save
        }
    }
    
    hasUnsavedChanges(sectionName) {
        // Vérifier s'il y a des modifications non sauvegardées
        const forms = document.querySelectorAll(`#${sectionName} form`);
        return Array.from(forms).some(form => form.classList.contains('modified'));
    }
    
    // ===== MISES À JOUR EN TEMPS RÉEL =====
    
    setupRealTimeUpdates() {
        // WebSocket ou polling pour les mises à jour en temps réel
        if (window.WebSocket) {
            this.initWebSocket();
        } else {
            this.initPolling();
        }
    }
    
    initWebSocket() {
        const ws = new WebSocket(`ws://${window.location.host}/ws/customers/${this.customerId}`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleRealTimeUpdate(data);
        };
        
        ws.onclose = () => {
            console.log('WebSocket connexion fermée, basculement vers le polling');
            this.initPolling();
        };
        
        this.ws = ws;
    }
    
    initPolling() {
        // Polling toutes les 60 secondes
        setInterval(() => {
            this.checkForUpdates();
        }, 60000);
    }
    
    async checkForUpdates() {
        try {
            const response = await fetch(`/api/customers/${this.customerId}/updates?since=${this.lastUpdateTime}`);
            const updates = await response.json();
            
            if (updates.length > 0) {
                updates.forEach(update => this.handleRealTimeUpdate(update));
                this.lastUpdateTime = new Date().toISOString();
            }
        } catch (error) {
            console.error('Erreur lors de la vérification des mises à jour:', error);
        }
    }
    
    handleRealTimeUpdate(data) {
        switch(data.type) {
            case 'customer_updated':
                this.refreshSection('profile');
                break;
            case 'new_activity':
                this.refreshSection('activity');
                break;
            case 'payment_received':
                this.refreshSection('finances');
                break;
            case 'document_uploaded':
                this.refreshSection('documents');
                break;
        }
        
        // Afficher une notification
        this.showToast(data.message, 'info');
    }
    
    // ===== GRAPHIQUES ET VISUALISATIONS =====
    
    initializeCharts() {
        // Initialiser Chart.js avec le thème claymorphism
        Chart.defaults.color = 'var(--text-color)';
        Chart.defaults.borderColor = 'var(--border-color)';
        Chart.defaults.backgroundColor = 'var(--bg-light)';
    }
    
    initializeAnalyticsCharts() {
        // Configuration spécifique pour les graphiques analytics
        this.initializeCharts();
        
        // Lazy loading des données de graphiques
        setTimeout(() => {
            this.loadAnalyticsData();
        }, 500);
    }
    
    async loadAnalyticsData() {
        try {
            const data = await this.fetchSectionData('analytics');
            this.updateAnalyticsCharts(data);
        } catch (error) {
            console.error('Erreur lors du chargement des analytics:', error);
        }
    }
    
    // ===== GLISSER-DÉPOSER =====
    
    initializeDragAndDrop() {
        const dropZone = document.getElementById('dropZone');
        if (!dropZone) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
        });
        
        dropZone.addEventListener('dragenter', this.highlight.bind(this));
        dropZone.addEventListener('dragover', this.highlight.bind(this));
        dropZone.addEventListener('dragleave', this.unhighlight.bind(this));
        dropZone.addEventListener('drop', this.handleDrop.bind(this));
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    highlight(e) {
        e.target.classList.add('drag-highlight');
    }
    
    unhighlight(e) {
        e.target.classList.remove('drag-highlight');
    }
    
    async handleDrop(e) {
        const files = e.dataTransfer.files;
        await this.uploadFiles(files);
    }
    
    // ===== DÉFILEMENT INFINI =====
    
    initializeInfiniteScroll() {
        const container = document.querySelector('#activity .timeline');
        if (!container) return;
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadMoreActivity();
                }
            });
        });
        
        const sentinel = document.createElement('div');
        sentinel.className = 'scroll-sentinel';
        container.appendChild(sentinel);
        observer.observe(sentinel);
    }
    
    // ===== UTILITAIRES =====
    
    activateTab(sectionName) {
        const tabButton = document.querySelector(`[data-section="${sectionName}"]`);
        if (tabButton) {
            const bsTab = new bootstrap.Tab(tabButton);
            bsTab.show();
        }
    }
    
    updateUrl(sectionName) {
        const url = new URL(window.location);
        url.searchParams.set('tab', sectionName);
        window.history.pushState({}, '', url);
    }
    
    trackSectionView(sectionName) {
        // Analytics/tracking
        if (window.gtag) {
            gtag('event', 'section_view', {
                customer_id: this.customerId,
                section: sectionName
            });
        }
    }
    
    invalidateCache(pattern = null) {
        if (pattern) {
            for (const key of this.cache.keys()) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
    }
    
    async refreshSection(sectionName) {
        this.invalidateCache(sectionName);
        this.loadedSections.delete(sectionName);
        await this.loadSectionIfNeeded(sectionName);
    }
    
    // ===== GESTION DES ÉVÉNEMENTS =====
    
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }
    
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Erreur dans le gestionnaire d'événement ${event}:`, error);
                }
            });
        }
    }
    
    // ===== NOTIFICATIONS =====
    
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.getElementById('globalToast');
        if (!toast) return;
        
        const title = document.getElementById('toastTitle');
        const body = document.getElementById('toastBody');
        
        const config = {
            'success': { title: 'Succès', class: 'text-success', icon: 'fas fa-check-circle' },
            'error': { title: 'Erreur', class: 'text-danger', icon: 'fas fa-exclamation-circle' },
            'warning': { title: 'Attention', class: 'text-warning', icon: 'fas fa-exclamation-triangle' },
            'info': { title: 'Information', class: 'text-info', icon: 'fas fa-info-circle' }
        };
        
        const typeConfig = config[type] || config['info'];
        
        title.textContent = typeConfig.title;
        title.className = `me-auto ${typeConfig.class}`;
        body.innerHTML = `<i class="${typeConfig.icon} me-2"></i>${message}`;
        
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();
    }
    
    // ===== ACTIONS RAPIDES =====
    
    async saveCurrentSection() {
        const activeTab = document.querySelector('.nav-link.active')?.getAttribute('data-section');
        if (activeTab) {
            await this.saveSection(activeTab);
        }
    }
    
    async saveSection(sectionName, silent = false) {
        const forms = document.querySelectorAll(`#${sectionName} form`);
        
        for (const form of forms) {
            if (form.classList.contains('modified')) {
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                try {
                    await this.updateSectionData(sectionName, data);
                    form.classList.remove('modified');
                    
                    if (!silent) {
                        this.showToast('Section sauvegardée', 'success');
                    }
                } catch (error) {
                    if (!silent) {
                        this.showToast('Erreur lors de la sauvegarde', 'error');
                    }
                }
            }
        }
    }
    
    editCustomer() {
        window.location.href = `/customers/${this.customerId}/edit`;
    }
    
    closeActiveModal() {
        const activeModal = document.querySelector('.modal.show');
        if (activeModal) {
            const bsModal = bootstrap.Modal.getInstance(activeModal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }
    
    // ===== DESTRUCTION =====
    
    destroy() {
        if (this.ws) {
            this.ws.close();
        }
        
        this.cache.clear();
        this.eventHandlers.clear();
        
        console.log('Customer 360 Manager destroyed');
    }
}

// Utilitaires globaux
const Customer360Utils = {
    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount || 0);
    },
    
    formatDate(dateString, format = 'short') {
        if (!dateString) return '-';
        
        const date = new Date(dateString);
        
        switch (format) {
            case 'short':
                return date.toLocaleDateString('fr-FR');
            case 'long':
                return date.toLocaleDateString('fr-FR', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            case 'time':
                return date.toLocaleTimeString('fr-FR');
            case 'datetime':
                return date.toLocaleString('fr-FR');
            case 'relative':
                return this.formatRelativeTime(dateString);
            default:
                return date.toLocaleDateString('fr-FR');
        }
    },
    
    formatRelativeTime(dateString) {
        if (!dateString) return '-';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'À l\'instant';
        if (diffInSeconds < 3600) return `Il y a ${Math.floor(diffInSeconds / 60)} min`;
        if (diffInSeconds < 86400) return `Il y a ${Math.floor(diffInSeconds / 3600)}h`;
        if (diffInSeconds < 2592000) return `Il y a ${Math.floor(diffInSeconds / 86400)} jours`;
        
        return this.formatDate(dateString);
    },
    
    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return Math.round((bytes / Math.pow(1024, i)) * 100) / 100 + ' ' + sizes[i];
    },
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Initialisation globale
let customer360;

document.addEventListener('DOMContentLoaded', function() {
    // Récupérer l'ID client depuis l'élément de données
    const customerIdElement = document.querySelector('[data-customer-id]');
    if (customerIdElement) {
        const customerId = customerIdElement.getAttribute('data-customer-id');
        customer360 = new Customer360Manager(customerId);
        
        // Rendre les utilitaires accessibles globalement
        window.customer360 = customer360;
        window.Customer360Utils = Customer360Utils;
    }
});

// Nettoyage avant de quitter la page
window.addEventListener('beforeunload', function() {
    if (customer360) {
        customer360.destroy();
    }
});
