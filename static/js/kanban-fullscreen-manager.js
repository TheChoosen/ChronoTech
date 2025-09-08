/**
 * Kanban Fullscreen Manager - Solution sans conflits
 * Version plein écran du Kanban avec drag-drop optimisé
 */

class KanbanFullscreenManager {
    constructor() {
        this.isFullscreen = false;
        this.originalContent = null;
        this.workOrders = [];
        this.draggedElement = null;
        
        // Configuration des colonnes
        this.columns = {
            'draft': { title: 'Brouillon', color: '#6c757d' },
            'pending': { title: 'En attente', color: '#0d6efd' },
            'assigned': { title: 'Assigné', color: '#fd7e14' },
            'in_progress': { title: 'En cours', color: '#198754' },
            'completed': { title: 'Terminé', color: '#20c997' },
            'cancelled': { title: 'Annulé', color: '#dc3545' }
        };
        
        this.init();
    }
    
    init() {
        console.log('🔧 Initialisation Kanban Fullscreen Manager');
        this.createFullscreenButton();
        this.setupEventListeners();
        this.loadWorkOrders();
    }
    
    createFullscreenButton() {
        // Ajouter le bouton plein écran dans la section Kanban
        const kanbanSection = document.querySelector('#kanban-section');
        if (kanbanSection) {
            const header = kanbanSection.querySelector('.card-header');
            if (header && !header.querySelector('.fullscreen-btn')) {
                const fullscreenBtn = document.createElement('button');
                fullscreenBtn.className = 'btn btn-outline-primary btn-sm fullscreen-btn';
                fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i> Plein écran';
                fullscreenBtn.onclick = () => this.toggleFullscreen();
                
                header.appendChild(fullscreenBtn);
            }
        }
    }
    
    toggleFullscreen() {
        if (this.isFullscreen) {
            this.exitFullscreen();
        } else {
            this.enterFullscreen();
        }
    }
    
    enterFullscreen() {
        console.log('🔄 Passage en mode plein écran');
        
        // Sauvegarder le contenu original
        const kanbanSection = document.querySelector('#kanban-section');
        if (!kanbanSection) return;
        
        this.originalContent = kanbanSection.innerHTML;
        
        // Créer l'interface plein écran
        const fullscreenOverlay = document.createElement('div');
        fullscreenOverlay.id = 'kanban-fullscreen-overlay';
        fullscreenOverlay.className = 'kanban-fullscreen-overlay';
        fullscreenOverlay.innerHTML = this.createFullscreenHTML();
        
        document.body.appendChild(fullscreenOverlay);
        document.body.style.overflow = 'hidden';
        
        this.isFullscreen = true;
        
        // Charger les données et configurer le drag-drop
        setTimeout(() => {
            this.loadWorkOrdersFullscreen();
            this.setupDragDropFullscreen();
        }, 100);
    }
    
    exitFullscreen() {
        console.log('🔄 Sortie du mode plein écran');
        
        const overlay = document.getElementById('kanban-fullscreen-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        document.body.style.overflow = '';
        this.isFullscreen = false;
        
        // Recharger les données du Kanban normal
        if (window.chronochat && window.chronochat.loadKanbanData) {
            window.chronochat.loadKanbanData();
        }
    }
    
    createFullscreenHTML() {
        return `
            <div class="kanban-fullscreen-header">
                <div class="d-flex justify-content-between align-items-center">
                    <h2 class="mb-0">
                        <i class="fas fa-columns"></i> Kanban - Bons de travail
                    </h2>
                    <div class="d-flex gap-2">
                        <button class="btn btn-outline-light btn-sm" onclick="kanbanFullscreen.refreshData()">
                            <i class="fas fa-sync"></i> Actualiser
                        </button>
                        <button class="btn btn-outline-light btn-sm" onclick="kanbanFullscreen.exitFullscreen()">
                            <i class="fas fa-times"></i> Fermer
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="kanban-fullscreen-filters">
                <div class="row">
                    <div class="col-md-3">
                        <select class="form-select form-select-sm" id="filter-technician">
                            <option value="">Tous les techniciens</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <select class="form-select form-select-sm" id="filter-priority">
                            <option value="">Toutes les priorités</option>
                            <option value="urgent">Urgent</option>
                            <option value="high">Élevée</option>
                            <option value="medium">Moyenne</option>
                            <option value="low">Faible</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <input type="text" class="form-control form-control-sm" id="filter-search" 
                               placeholder="Rechercher par client, description...">
                    </div>
                </div>
            </div>
            
            <div class="kanban-fullscreen-board" id="fullscreen-kanban-board">
                ${this.createColumnsHTML()}
            </div>
        `;
    }
    
    createColumnsHTML() {
        return Object.entries(this.columns).map(([status, config]) => `
            <div class="kanban-fullscreen-column" data-status="${status}">
                <div class="column-header" style="border-left: 4px solid ${config.color}">
                    <h5 class="mb-0">${config.title}</h5>
                    <span class="badge bg-secondary" id="fs-count-${status}">0</span>
                </div>
                <div class="column-body kanban-drop-zone" 
                     id="fs-column-${status}"
                     ondrop="kanbanFullscreen.handleDrop(event)"
                     ondragover="kanbanFullscreen.allowDrop(event)">
                </div>
            </div>
        `).join('');
    }
    
    async loadWorkOrders() {
        try {
            const response = await fetch('/api/kanban-data');
            const data = await response.json();
            
            if (data.success && data.kanban_data) {
                this.workOrders = [];
                
                // Collecter tous les bons de travail
                Object.entries(data.kanban_data).forEach(([status, orders]) => {
                    orders.forEach(order => {
                        this.workOrders.push({...order, status});
                    });
                });
                
                console.log(`📊 ${this.workOrders.length} bons de travail chargés`);
            }
        } catch (error) {
            console.error('❌ Erreur lors du chargement des données Kanban:', error);
        }
    }
    
    async loadWorkOrdersFullscreen() {
        await this.loadWorkOrders();
        this.updateFullscreenColumns();
    }
    
    updateFullscreenColumns() {
        if (!this.isFullscreen) return;
        
        // Grouper les bons de travail par statut
        const groupedOrders = {};
        Object.keys(this.columns).forEach(status => {
            groupedOrders[status] = this.workOrders.filter(order => order.status === status);
        });
        
        // Mettre à jour chaque colonne
        Object.entries(groupedOrders).forEach(([status, orders]) => {
            const column = document.getElementById(`fs-column-${status}`);
            const count = document.getElementById(`fs-count-${status}`);
            
            if (column) {
                column.innerHTML = '';
                orders.forEach(order => {
                    const card = this.createFullscreenCard(order);
                    column.appendChild(card);
                });
            }
            
            if (count) {
                count.textContent = orders.length;
            }
        });
    }
    
    createFullscreenCard(workOrder) {
        const card = document.createElement('div');
        card.className = 'kanban-fullscreen-card';
        card.draggable = true;
        card.dataset.cardId = workOrder.id;
        
        const priorityClass = {
            'urgent': 'priority-urgent',
            'high': 'priority-high',
            'medium': 'priority-medium',
            'low': 'priority-low'
        };
        
        card.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-start">
                <h6 class="mb-0">#${workOrder.claim_number}</h6>
                <span class="priority-badge ${priorityClass[workOrder.priority] || ''}">${workOrder.priority}</span>
            </div>
            <div class="card-body">
                <p class="customer-name">${workOrder.customer_name}</p>
                <p class="description">${workOrder.description || 'Aucune description'}</p>
                <div class="card-footer">
                    <small class="technician">${workOrder.technician_name || 'Non assigné'}</small>
                    <small class="date">${this.formatDate(workOrder.created_at)}</small>
                </div>
            </div>
        `;
        
        return card;
    }
    
    setupDragDropFullscreen() {
        if (!this.isFullscreen) return;
        
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('kanban-fullscreen-card')) {
                this.draggedElement = e.target;
                e.target.classList.add('dragging');
                e.dataTransfer.setData('text/plain', e.target.dataset.cardId);
                e.dataTransfer.effectAllowed = 'move';
            }
        });
        
        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('kanban-fullscreen-card')) {
                e.target.classList.remove('dragging');
                this.draggedElement = null;
            }
        });
    }
    
    allowDrop(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        
        // Ajouter effet visuel de survol
        const dropZone = event.currentTarget;
        if (!dropZone.classList.contains('drag-over')) {
            dropZone.classList.add('drag-over');
            setTimeout(() => dropZone.classList.remove('drag-over'), 200);
        }
    }
    
    async handleDrop(event) {
        event.preventDefault();
        
        const cardId = event.dataTransfer.getData('text/plain');
        const dropZone = event.currentTarget;
        const newStatus = dropZone.closest('.kanban-fullscreen-column').dataset.status;
        
        if (!cardId || !newStatus) {
            console.error('❌ Données de drop invalides');
            return;
        }
        
        console.log(`🔄 Déplacement bon de travail ${cardId} vers ${newStatus}`);
        
        try {
            // Mise à jour via API
            const response = await fetch(`/api/work-orders/${cardId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({status: newStatus})
            });
            
            if (response.ok) {
                // Mettre à jour localement
                const workOrder = this.workOrders.find(wo => wo.id == cardId);
                if (workOrder) {
                    workOrder.status = newStatus;
                }
                
                this.updateFullscreenColumns();
                this.showToast('✅ Statut mis à jour avec succès', 'success');
            } else {
                throw new Error('Erreur serveur');
            }
        } catch (error) {
            console.error('❌ Erreur lors de la mise à jour:', error);
            this.showToast('❌ Erreur lors de la mise à jour du statut', 'danger');
        }
    }
    
    async refreshData() {
        console.log('🔄 Actualisation des données Kanban');
        await this.loadWorkOrdersFullscreen();
        this.showToast('🔄 Données actualisées', 'info');
    }
    
    setupEventListeners() {
        // Gestion du raccourci clavier Echap pour fermer
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isFullscreen) {
                this.exitFullscreen();
            }
        });
        
        // Gestion des filtres (délégation d'événements)
        document.addEventListener('change', (e) => {
            if (this.isFullscreen && e.target.matches('#filter-technician, #filter-priority')) {
                this.applyFilters();
            }
        });
        
        document.addEventListener('input', (e) => {
            if (this.isFullscreen && e.target.matches('#filter-search')) {
                this.applyFilters();
            }
        });
    }
    
    applyFilters() {
        // Implémentation des filtres ici si nécessaire
        console.log('🔍 Application des filtres');
    }
    
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
    
    showToast(message, type = 'info') {
        // Système de toast simple
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} kanban-toast`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // Animation d'apparition
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        }, 10);
        
        // Suppression automatique
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }
}

// CSS pour le mode plein écran
const fullscreenCSS = `
.kanban-fullscreen-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    z-index: 9998;
    display: flex;
    flex-direction: column;
}

.kanban-fullscreen-header {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    padding: 1rem 2rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
}

.kanban-fullscreen-filters {
    background: rgba(255, 255, 255, 0.05);
    padding: 1rem 2rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.kanban-fullscreen-board {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    padding: 1rem 2rem;
    overflow-y: auto;
}

.kanban-fullscreen-column {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    height: fit-content;
    min-height: 400px;
}

.kanban-fullscreen-column .column-header {
    padding: 1rem;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px 12px 0 0;
    display: flex;
    justify-content: between;
    align-items: center;
    color: white;
}

.kanban-fullscreen-column .column-body {
    padding: 1rem;
    min-height: 350px;
}

.kanban-fullscreen-card {
    background: white;
    border-radius: 8px;
    margin-bottom: 1rem;
    border: 1px solid #e9ecef;
    cursor: grab;
    transition: all 0.2s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.kanban-fullscreen-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.kanban-fullscreen-card.dragging {
    opacity: 0.5;
    transform: rotate(5deg);
    cursor: grabbing;
}

.kanban-fullscreen-card .card-header {
    padding: 0.75rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e9ecef;
    border-radius: 8px 8px 0 0;
}

.kanban-fullscreen-card .card-body {
    padding: 0.75rem;
}

.kanban-fullscreen-card .customer-name {
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.5rem;
}

.kanban-fullscreen-card .description {
    font-size: 0.875rem;
    color: #6c757d;
    margin-bottom: 0.75rem;
}

.kanban-fullscreen-card .card-footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #6c757d;
}

.priority-badge {
    font-size: 0.7rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
}

.priority-urgent { background: #dc3545; color: white; }
.priority-high { background: #fd7e14; color: white; }
.priority-medium { background: #ffc107; color: #000; }
.priority-low { background: #28a745; color: white; }

.kanban-drop-zone.drag-over {
    background: rgba(255, 255, 255, 0.1);
    border: 2px dashed rgba(255, 255, 255, 0.3);
}

.kanban-toast {
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

@media (max-width: 1200px) {
    .kanban-fullscreen-board {
        grid-template-columns: repeat(3, 1fr);
    }
}

@media (max-width: 768px) {
    .kanban-fullscreen-board {
        grid-template-columns: repeat(2, 1fr);
        padding: 1rem;
    }
    
    .kanban-fullscreen-header,
    .kanban-fullscreen-filters {
        padding: 1rem;
    }
}
`;

// Injecter le CSS
const style = document.createElement('style');
style.textContent = fullscreenCSS;
document.head.appendChild(style);

// Instance globale
let kanbanFullscreen = null;

// Initialisation quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    kanbanFullscreen = new KanbanFullscreenManager();
});

console.log('🎯 Kanban Fullscreen Manager chargé');
