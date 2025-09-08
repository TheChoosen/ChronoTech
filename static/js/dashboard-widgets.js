/**
 * ChronoTech Dashboard Widgets - Système de widgets personnalisables
 * Utilise GridStack.js pour le drag & drop
 */

class DashboardWidgets {
    constructor() {
        this.grid = null;
        this.availableWidgets = {};
        this.currentLayout = null;
        this.isCustomizing = false;
        this.init();
    }

    async init() {
        // Charger les widgets disponibles
        await this.loadAvailableWidgets();
        
        // Charger la configuration utilisateur
        await this.loadUserLayout();
        
        // Initialiser GridStack si on est en mode personnalisation
        if (document.getElementById('dashboard-customize')) {
            this.initCustomizationMode();
        } else {
            this.initDisplayMode();
        }
    }

    async loadAvailableWidgets() {
        try {
            const response = await fetch('/dashboard/api/widgets/available');
            const data = await response.json();
            
            if (data.success) {
                this.availableWidgets = data.widgets;
                console.log('Widgets disponibles chargés:', Object.keys(this.availableWidgets));
            } else {
                console.error('Erreur lors du chargement des widgets disponibles:', data.error);
            }
        } catch (error) {
            console.error('Erreur lors du chargement des widgets disponibles:', error);
        }
    }

    async loadUserLayout() {
        try {
            const response = await fetch('/dashboard/api/widgets');
            const data = await response.json();
            
            if (data.success) {
                this.currentLayout = data.layout;
                console.log('Layout utilisateur chargé:', this.currentLayout);
                
                if (data.is_default) {
                    console.log('Configuration par défaut appliquée');
                }
            } else {
                console.error('Erreur lors du chargement du layout:', data.error);
            }
        } catch (error) {
            console.error('Erreur lors du chargement du layout:', error);
        }
    }

    async saveUserLayout() {
        if (!this.currentLayout) return;

        try {
            const response = await fetch('/dashboard/api/widgets/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    layout: this.currentLayout
                })
            });

            const data = await response.json();

            if (data.success) {
                showToast('Configuration du tableau de bord sauvegardée', 'success');
            } else {
                showToast('Erreur lors de la sauvegarde: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Erreur lors de la sauvegarde:', error);
            showToast('Erreur lors de la sauvegarde', 'error');
        }
    }

    initDisplayMode() {
        console.log('Initialisation du mode affichage');
        
        if (!this.currentLayout || !this.currentLayout.widgets) {
            console.warn('Aucun layout disponible');
            return;
        }

        // Appliquer le layout aux widgets existants
        this.applyLayoutToExistingWidgets();
    }

    applyLayoutToExistingWidgets() {
        this.currentLayout.widgets.forEach(widgetConfig => {
            const widgetElement = document.getElementById(`${widgetConfig.id}-widget`);
            
            if (widgetElement) {
                // Appliquer la visibilité
                if (widgetConfig.enabled) {
                    widgetElement.style.display = 'block';
                    
                    // Appliquer les classes de taille Bootstrap si nécessaire
                    this.applyBootstrapSizing(widgetElement, widgetConfig);
                } else {
                    widgetElement.style.display = 'none';
                }
            }
        });
    }

    applyBootstrapSizing(element, config) {
        // Conversion approximative GridStack vers Bootstrap
        const parentRow = element.closest('.row');
        if (parentRow) {
            // Supprimer les classes de colonne existantes
            element.className = element.className.replace(/col-\w*-?\d*/g, '');
            
            // Appliquer nouvelle taille basée sur la largeur GridStack
            let colClass;
            if (config.w <= 3) colClass = 'col-lg-3';
            else if (config.w <= 6) colClass = 'col-lg-6';
            else if (config.w <= 9) colClass = 'col-lg-9';
            else colClass = 'col-lg-12';
            
            element.classList.add(colClass);
        }
    }

    initCustomizationMode() {
        console.log('Initialisation du mode personnalisation');
        
        // Initialiser GridStack
        this.grid = GridStack.init({
            cellHeight: 60,
            acceptWidgets: true,
            removable: '.trash',
            margin: 10,
            float: true,
            disableOneColumnMode: true,
            column: 12,
            row: 20
        });

        // Charger les widgets dans la grille
        this.loadWidgetsInGrid();

        // Écouteurs d'événements
        this.bindCustomizationEvents();

        // Créer la zone de widgets disponibles
        this.createWidgetsPalette();
    }

    loadWidgetsInGrid() {
        if (!this.currentLayout || !this.currentLayout.widgets) return;

        this.currentLayout.widgets.forEach(widgetConfig => {
            if (widgetConfig.enabled) {
                this.addWidgetToGrid(widgetConfig);
            }
        });
    }

    addWidgetToGrid(widgetConfig) {
        const widgetInfo = this.availableWidgets[widgetConfig.id];
        if (!widgetInfo) return;

        const widgetElement = this.createWidgetElement(widgetConfig, widgetInfo);
        
        this.grid.addWidget(widgetElement, {
            x: widgetConfig.x,
            y: widgetConfig.y,
            w: widgetConfig.w,
            h: widgetConfig.h,
            id: widgetConfig.id
        });
    }

    createWidgetElement(config, info) {
        const widgetDiv = document.createElement('div');
        widgetDiv.className = 'grid-stack-item';
        widgetDiv.setAttribute('gs-id', config.id);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'grid-stack-item-content clay-card';
        
        contentDiv.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">
                    <i class="fa-solid ${info.icon} me-2 text-${info.color}"></i>
                    ${info.name}
                </h6>
                <div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="dashboardWidgets.configureWidget('${config.id}')">
                        <i class="fa-solid fa-cog"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="dashboardWidgets.removeWidget('${config.id}')">
                        <i class="fa-solid fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="card-body">
                <p class="text-muted mb-0">${info.description}</p>
                <div class="widget-preview mt-2">
                    <div class="bg-light rounded p-2 text-center">
                        <i class="fa-solid ${info.icon} fa-2x text-${info.color} mb-2"></i>
                        <small class="d-block text-muted">Aperçu du widget</small>
                    </div>
                </div>
            </div>
        `;
        
        widgetDiv.appendChild(contentDiv);
        return widgetDiv;
    }

    createWidgetsPalette() {
        const paletteContainer = document.getElementById('widgets-palette');
        if (!paletteContainer) return;

        // Créer les widgets disponibles
        Object.entries(this.availableWidgets).forEach(([widgetId, widgetInfo]) => {
            const isActive = this.currentLayout.widgets.some(w => w.id === widgetId && w.enabled);
            
            if (!isActive) {
                const widgetCard = this.createPaletteWidget(widgetId, widgetInfo);
                paletteContainer.appendChild(widgetCard);
            }
        });
    }

    createPaletteWidget(widgetId, widgetInfo) {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'col-md-6 col-lg-4 mb-3';
        
        cardDiv.innerHTML = `
            <div class="card h-100 widget-palette-item" data-widget-id="${widgetId}">
                <div class="card-body text-center">
                    <i class="fa-solid ${widgetInfo.icon} fa-2x text-${widgetInfo.color} mb-3"></i>
                    <h6>${widgetInfo.name}</h6>
                    <p class="text-muted small">${widgetInfo.description}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="dashboardWidgets.addWidget('${widgetId}')">
                        <i class="fa-solid fa-plus me-1"></i>Ajouter
                    </button>
                </div>
            </div>
        `;
        
        return cardDiv;
    }

    bindCustomizationEvents() {
        // Sauvegarder lors des changements
        this.grid.on('change', (event, items) => {
            this.updateLayoutFromGrid();
        });

        // Sauvegarder automatiquement
        this.autoSaveInterval = setInterval(() => {
            this.saveUserLayout();
        }, 10000); // Toutes les 10 secondes
    }

    updateLayoutFromGrid() {
        if (!this.grid) return;

        const gridItems = this.grid.getGridItems();
        
        // Mettre à jour la configuration
        this.currentLayout.widgets = this.currentLayout.widgets.map(widget => {
            const gridItem = gridItems.find(item => item.getAttribute('gs-id') === widget.id);
            
            if (gridItem) {
                const node = gridItem.gridstackNode;
                return {
                    ...widget,
                    x: node.x,
                    y: node.y,
                    w: node.w,
                    h: node.h,
                    enabled: true
                };
            }
            
            return widget;
        });
    }

    addWidget(widgetId) {
        const widgetInfo = this.availableWidgets[widgetId];
        if (!widgetInfo) return;

        // Créer la configuration du widget
        const widgetConfig = {
            id: widgetId,
            x: 0,
            y: 0,
            w: widgetInfo.default_size.w,
            h: widgetInfo.default_size.h,
            enabled: true
        };

        // Ajouter à la grille
        this.addWidgetToGrid(widgetConfig);

        // Mettre à jour le layout
        this.currentLayout.widgets.push(widgetConfig);

        // Supprimer de la palette
        const paletteItem = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (paletteItem) {
            paletteItem.closest('.col-md-6').remove();
        }

        showToast(`Widget "${widgetInfo.name}" ajouté`, 'success');
    }

    removeWidget(widgetId) {
        // Supprimer de la grille
        const gridItem = document.querySelector(`[gs-id="${widgetId}"]`);
        if (gridItem) {
            this.grid.removeWidget(gridItem);
        }

        // Mettre à jour le layout
        this.currentLayout.widgets = this.currentLayout.widgets.map(widget => {
            if (widget.id === widgetId) {
                return { ...widget, enabled: false };
            }
            return widget;
        });

        // Remettre dans la palette
        const widgetInfo = this.availableWidgets[widgetId];
        if (widgetInfo) {
            const paletteContainer = document.getElementById('widgets-palette');
            const widgetCard = this.createPaletteWidget(widgetId, widgetInfo);
            paletteContainer.appendChild(widgetCard);
        }

        showToast(`Widget "${widgetInfo.name}" supprimé`, 'info');
    }

    configureWidget(widgetId) {
        showToast(`Configuration du widget ${widgetId} - À implémenter`, 'info');
    }

    async resetLayout() {
        if (!confirm('Êtes-vous sûr de vouloir remettre à zéro votre tableau de bord ?')) {
            return;
        }

        try {
            const response = await fetch('/dashboard/api/widgets/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                showToast('Configuration réinitialisée', 'success');
                
                // Recharger la page après un court délai
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showToast('Erreur lors de la réinitialisation: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Erreur lors de la réinitialisation:', error);
            showToast('Erreur lors de la réinitialisation', 'error');
        }
    }

    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        if (this.grid) {
            this.grid.destroy();
        }
    }
}

// Instance globale
let dashboardWidgets;

// Initialiser quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    dashboardWidgets = new DashboardWidgets();
});

// Nettoyer à la fermeture
window.addEventListener('beforeunload', function() {
    if (dashboardWidgets) {
        dashboardWidgets.destroy();
    }
});
