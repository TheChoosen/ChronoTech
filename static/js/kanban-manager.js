/**
 * ChronoChat Kanban - Fonctionnalité Complète avec WebSocket
 * Gestion temps réel des bons de travail
 */

class ChronoChatKanban {
    constructor() {
        this.workOrders = [];
        this.filteredWorkOrders = [];
        this.technicians = [];
        this.socket = null;
        this.currentUser = null;
        this.draggedElement = null;
        
        // Colonnes du Kanban
        this.columns = {
            'draft': 'Brouillon',
            'pending': 'En attente',
            'assigned': 'Assigné',
            'in_progress': 'En cours',
            'completed': 'Terminé',
            'cancelled': 'Annulé'
        };
        
        // Couleurs de priorité
        this.priorityColors = {
            'urgent': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#28a745'
        };
        
        this.init();
    }
    
    async init() {
        console.log('🎯 Initialisation Kanban ChronoChat...');
        
        // Récupérer les informations utilisateur
        this.currentUser = await this.getCurrentUser();
        
        // Initialiser WebSocket
        this.initWebSocket();
        
        // Charger les données initiales
        await this.loadInitialData();
        
        // Créer l'interface
        this.createKanbanInterface();
        
        // Initialiser les événements
        this.initEventListeners();
        
        console.log('✅ Kanban initialisé avec succès');
    }
    
    async getCurrentUser() {
        try {
            const response = await fetch('http://localhost:5002/api/current-user');
            return await response.json();
        } catch (error) {
            console.error('Erreur récupération utilisateur:', error);
            return { id: 1, name: 'Admin System', role: 'admin' };
        }
    }
    
    initWebSocket() {
        // Connexion WebSocket pour les mises à jour temps réel
        const wsUrl = `ws://localhost:5001/socket.io/?user_id=${this.currentUser.id}&username=${this.currentUser.name}`;
        
        this.socket = io('http://localhost:5001', {
            query: {
                user_id: this.currentUser.id,
                username: this.currentUser.name
            },
            autoConnect: false
        });
        
        // Événements WebSocket
        this.socket.on('connect', () => {
            console.log('🔗 WebSocket Kanban connecté');
        });
        
        this.socket.on('work_order_updated', (data) => {
            this.handleWorkOrderUpdate(data);
        });
        
        this.socket.on('disconnect', () => {
            console.log('🔌 WebSocket Kanban déconnecté');
        });
        
        // Connexion automatique après l'initialisation
        setTimeout(() => {
            this.socket.connect();
        }, 1000);
    }
    
    async loadInitialData() {
        try {
            // Charger les bons de travail
            const workOrdersResponse = await fetch('http://localhost:5002/api/work-orders');
            const workOrdersData = await workOrdersResponse.json();
            this.workOrders = workOrdersData.work_orders || [];
            
            // Charger les techniciens
            const techniciansResponse = await fetch('http://localhost:5002/api/technicians');
            const techniciansData = await techniciansResponse.json();
            this.technicians = techniciansData.technicians || [];
            
            // Appliquer les filtres initiaux
            this.applyFilters();
            
        } catch (error) {
            console.error('Erreur chargement données:', error);
            this.showNotification('Erreur de chargement des données', 'error');
        }
    }
    
    createKanbanInterface() {
        const kanbanContainer = document.getElementById('kanban-container');
        if (!kanbanContainer) {
            console.error('Container Kanban non trouvé');
            return;
        }
        
        kanbanContainer.innerHTML = `
            <div class="kanban-header">
                <h3>📋 Tableau Kanban - Bons de Travail</h3>
                <div class="kanban-controls">
                    ${this.createFilterControls()}
                    <button class="btn btn-primary" onclick="kanbanManager.refreshData()">
                        🔄 Actualiser
                    </button>
                </div>
            </div>
            <div class="kanban-filters">
                ${this.createAdvancedFilters()}
            </div>
            <div class="kanban-board">
                ${this.createKanbanColumns()}
            </div>
            <div class="kanban-stats">
                ${this.createStatsPanel()}
            </div>
        `;
        
        // Rendre les colonnes droppables
        this.initDragAndDrop();
    }
    
    createFilterControls() {
        return `
            <div class="filter-controls">
                <select id="priority-filter" class="form-select">
                    <option value="">Toutes priorités</option>
                    <option value="urgent">🔴 Urgent</option>
                    <option value="high">🟠 Élevée</option>
                    <option value="medium">🟡 Moyenne</option>
                    <option value="low">🟢 Faible</option>
                </select>
                
                <select id="technician-filter" class="form-select">
                    <option value="">Tous techniciens</option>
                    ${this.technicians.map(tech => 
                        `<option value="${tech.id}">${tech.name}</option>`
                    ).join('')}
                </select>
                
                <input type="date" id="date-from-filter" class="form-control" placeholder="Date début">
                <input type="date" id="date-to-filter" class="form-control" placeholder="Date fin">
                
                <input type="text" id="search-filter" class="form-control" placeholder="🔍 Rechercher...">
            </div>
        `;
    }
    
    createAdvancedFilters() {
        return `
            <div class="advanced-filters">
                <div class="filter-row">
                    <label>Status:</label>
                    <div class="status-filters">
                        ${Object.entries(this.columns).map(([status, label]) => `
                            <label class="filter-checkbox">
                                <input type="checkbox" value="${status}" checked data-filter="status">
                                <span class="status-badge status-${status}">${label}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    createKanbanColumns() {
        return Object.entries(this.columns).map(([status, label]) => `
            <div class="kanban-column" data-status="${status}">
                <div class="column-header">
                    <h4>${label}</h4>
                    <span class="count-badge">${this.getWorkOrdersByStatus(status).length}</span>
                </div>
                <div class="column-content" data-status="${status}">
                    ${this.createWorkOrderCards(status)}
                </div>
            </div>
        `).join('');
    }
    
    createWorkOrderCards(status) {
        const workOrders = this.getWorkOrdersByStatus(status);
        
        return workOrders.map(wo => `
            <div class="work-order-card" 
                 data-id="${wo.id}" 
                 data-status="${wo.status}"
                 draggable="true">
                <div class="card-header">
                    <span class="claim-number">${wo.claim_number}</span>
                    <span class="priority priority-${wo.priority}" 
                          style="background-color: ${this.priorityColors[wo.priority]}">
                        ${wo.priority.toUpperCase()}
                    </span>
                </div>
                <div class="card-body">
                    <h5>${wo.customer_name}</h5>
                    <p class="description">${this.truncateText(wo.description, 80)}</p>
                    ${wo.assigned_technician_name ? 
                        `<div class="technician">👨‍🔧 ${wo.assigned_technician_name}</div>` : 
                        '<div class="no-technician">⚠️ Non assigné</div>'
                    }
                    ${wo.scheduled_date ? 
                        `<div class="scheduled-date">📅 ${this.formatDate(wo.scheduled_date)}</div>` : 
                        ''
                    }
                </div>
                <div class="card-actions">
                    <button class="btn-icon" onclick="kanbanManager.editWorkOrder(${wo.id})" title="Modifier">
                        ✏️
                    </button>
                    <button class="btn-icon" onclick="kanbanManager.assignTechnician(${wo.id})" title="Assigner">
                        👨‍🔧
                    </button>
                    <button class="btn-icon" onclick="kanbanManager.viewDetails(${wo.id})" title="Détails">
                        👁️
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    createStatsPanel() {
        const stats = this.calculateStats();
        
        return `
            <div class="stats-panel">
                <h4>📊 Statistiques</h4>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-number">${stats.total}</span>
                        <span class="stat-label">Total</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">${stats.urgent}</span>
                        <span class="stat-label">Urgent</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">${stats.inProgress}</span>
                        <span class="stat-label">En cours</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number">${stats.completed}</span>
                        <span class="stat-label">Terminés</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    initEventListeners() {
        // Filtres
        document.getElementById('priority-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('technician-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('date-from-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('date-to-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('search-filter')?.addEventListener('input', () => this.applyFilters());
        
        // Filtres de statut
        document.querySelectorAll('[data-filter="status"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.applyFilters());
        });
    }
    
    initDragAndDrop() {
        // Cartes draggables
        document.querySelectorAll('.work-order-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                this.draggedElement = card;
                card.classList.add('dragging');
            });
            
            card.addEventListener('dragend', (e) => {
                card.classList.remove('dragging');
                this.draggedElement = null;
            });
        });
        
        // Zones droppables
        document.querySelectorAll('.column-content').forEach(column => {
            column.addEventListener('dragover', (e) => {
                e.preventDefault();
                column.classList.add('drag-over');
            });
            
            column.addEventListener('dragleave', (e) => {
                column.classList.remove('drag-over');
            });
            
            column.addEventListener('drop', (e) => {
                e.preventDefault();
                column.classList.remove('drag-over');
                
                if (this.draggedElement) {
                    const workOrderId = parseInt(this.draggedElement.dataset.id);
                    const newStatus = column.dataset.status;
                    const oldStatus = this.draggedElement.dataset.status;
                    
                    if (newStatus !== oldStatus) {
                        this.updateWorkOrderStatus(workOrderId, newStatus);
                    }
                }
            });
        });
    }
    
    async updateWorkOrderStatus(workOrderId, newStatus) {
        try {
            const response = await fetch(`http://localhost:5002/api/work-orders/${workOrderId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: newStatus })
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Mettre à jour localement
                const workOrder = this.workOrders.find(wo => wo.id === workOrderId);
                if (workOrder) {
                    workOrder.status = newStatus;
                    workOrder.updated_at = result.timestamp;
                }
                
                // Notifier via WebSocket
                if (this.socket && this.socket.connected) {
                    this.socket.emit('work_order_status_changed', {
                        work_order_id: workOrderId,
                        old_status: result.old_status,
                        new_status: newStatus,
                        changed_by: this.currentUser.name
                    });
                }
                
                // Actualiser l'affichage
                this.refreshKanbanBoard();
                
                this.showNotification(`Statut mis à jour: ${result.old_status} → ${newStatus}`, 'success');
                
            } else {
                throw new Error('Erreur mise à jour statut');
            }
            
        } catch (error) {
            console.error('Erreur mise à jour statut:', error);
            this.showNotification('Erreur lors de la mise à jour', 'error');
            
            // Recharger pour annuler le changement visuel
            await this.loadInitialData();
            this.refreshKanbanBoard();
        }
    }
    
    async assignTechnician(workOrderId) {
        const workOrder = this.workOrders.find(wo => wo.id === workOrderId);
        if (!workOrder) return;
        
        // Créer le modal de sélection
        const modal = this.createTechnicianSelectionModal(workOrder);
        document.body.appendChild(modal);
        
        // Afficher le modal
        modal.style.display = 'flex';
    }
    
    createTechnicianSelectionModal(workOrder) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>👨‍🔧 Assigner un technicien</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <p><strong>Bon de travail:</strong> ${workOrder.claim_number}</p>
                    <p><strong>Client:</strong> ${workOrder.customer_name}</p>
                    <p><strong>Actuel:</strong> ${workOrder.assigned_technician_name || 'Non assigné'}</p>
                    
                    <div class="form-group">
                        <label>Sélectionner un technicien:</label>
                        <select id="technician-select" class="form-select">
                            <option value="">-- Non assigné --</option>
                            ${this.technicians.map(tech => `
                                <option value="${tech.id}" 
                                        ${tech.id === workOrder.assigned_technician_id ? 'selected' : ''}>
                                    ${tech.name} (${tech.role})
                                </option>
                            `).join('')}
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">
                        Annuler
                    </button>
                    <button class="btn btn-primary" onclick="kanbanManager.confirmTechnicianAssignment(${workOrder.id})">
                        Assigner
                    </button>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    async confirmTechnicianAssignment(workOrderId) {
        const modal = document.querySelector('.modal-overlay');
        const technicianSelect = modal.querySelector('#technician-select');
        const technicianId = technicianSelect.value || null;
        
        try {
            const response = await fetch(`http://localhost:5002/api/work-orders/${workOrderId}/assign`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ technician_id: technicianId })
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Mettre à jour localement
                const workOrder = this.workOrders.find(wo => wo.id === workOrderId);
                if (workOrder) {
                    workOrder.assigned_technician_id = technicianId;
                    workOrder.assigned_technician_name = result.technician_name;
                }
                
                // Actualiser l'affichage
                this.refreshKanbanBoard();
                
                modal.remove();
                this.showNotification(
                    technicianId ? 
                    `Assigné à ${result.technician_name}` : 
                    'Assignment retiré', 
                    'success'
                );
                
            } else {
                throw new Error('Erreur assignment');
            }
            
        } catch (error) {
            console.error('Erreur assignment:', error);
            this.showNotification('Erreur lors de l\'assignment', 'error');
        }
    }
    
    applyFilters() {
        const priorityFilter = document.getElementById('priority-filter')?.value;
        const technicianFilter = document.getElementById('technician-filter')?.value;
        const dateFromFilter = document.getElementById('date-from-filter')?.value;
        const dateToFilter = document.getElementById('date-to-filter')?.value;
        const searchFilter = document.getElementById('search-filter')?.value.toLowerCase();
        
        // Récupérer les statuts sélectionnés
        const selectedStatuses = Array.from(document.querySelectorAll('[data-filter="status"]:checked'))
            .map(cb => cb.value);
        
        this.filteredWorkOrders = this.workOrders.filter(wo => {
            // Filtre de statut
            if (selectedStatuses.length > 0 && !selectedStatuses.includes(wo.status)) {
                return false;
            }
            
            // Filtre de priorité
            if (priorityFilter && wo.priority !== priorityFilter) {
                return false;
            }
            
            // Filtre de technicien
            if (technicianFilter && wo.assigned_technician_id != technicianFilter) {
                return false;
            }
            
            // Filtre de date
            if (dateFromFilter && wo.scheduled_date) {
                const scheduleDate = new Date(wo.scheduled_date).toISOString().split('T')[0];
                if (scheduleDate < dateFromFilter) return false;
            }
            
            if (dateToFilter && wo.scheduled_date) {
                const scheduleDate = new Date(wo.scheduled_date).toISOString().split('T')[0];
                if (scheduleDate > dateToFilter) return false;
            }
            
            // Filtre de recherche
            if (searchFilter) {
                const searchText = `${wo.customer_name} ${wo.description} ${wo.claim_number}`.toLowerCase();
                if (!searchText.includes(searchFilter)) return false;
            }
            
            return true;
        });
        
        this.refreshKanbanBoard();
    }
    
    refreshKanbanBoard() {
        // Mettre à jour les colonnes
        Object.keys(this.columns).forEach(status => {
            const column = document.querySelector(`.column-content[data-status="${status}"]`);
            const countBadge = document.querySelector(`.kanban-column[data-status="${status}"] .count-badge`);
            
            if (column) {
                column.innerHTML = this.createWorkOrderCards(status);
            }
            
            if (countBadge) {
                countBadge.textContent = this.getWorkOrdersByStatus(status).length;
            }
        });
        
        // Mettre à jour les statistiques
        const statsPanel = document.querySelector('.stats-panel');
        if (statsPanel) {
            statsPanel.innerHTML = this.createStatsPanel().match(/<div class="stats-panel">([\s\S]*)<\/div>/)[1];
        }
        
        // Réinitialiser le drag & drop
        this.initDragAndDrop();
    }
    
    async refreshData() {
        this.showNotification('🔄 Actualisation en cours...', 'info');
        await this.loadInitialData();
        this.refreshKanbanBoard();
        this.showNotification('✅ Données actualisées', 'success');
    }
    
    // Méthodes utilitaires
    getWorkOrdersByStatus(status) {
        return this.filteredWorkOrders.filter(wo => wo.status === status);
    }
    
    calculateStats() {
        return {
            total: this.filteredWorkOrders.length,
            urgent: this.filteredWorkOrders.filter(wo => wo.priority === 'urgent').length,
            inProgress: this.filteredWorkOrders.filter(wo => wo.status === 'in_progress').length,
            completed: this.filteredWorkOrders.filter(wo => wo.status === 'completed').length
        };
    }
    
    truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }
    
    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    handleWorkOrderUpdate(data) {
        // Traiter les mises à jour WebSocket
        const workOrder = this.workOrders.find(wo => wo.id === data.work_order_id);
        if (workOrder) {
            Object.assign(workOrder, data.updates);
            this.applyFilters();
            this.refreshKanbanBoard();
        }
    }
    
    showNotification(message, type = 'info') {
        // Créer et afficher une notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Supprimer après 3 secondes
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    editWorkOrder(workOrderId) {
        // Placeholder pour l'édition
        console.log('Edit work order:', workOrderId);
        this.showNotification('Fonction d\'édition à implémenter', 'info');
    }
    
    viewDetails(workOrderId) {
        // Placeholder pour les détails
        console.log('View details:', workOrderId);
        this.showNotification('Fonction de détails à implémenter', 'info');
    }
}

// Initialisation globale
let kanbanManager = null;

// Démarrage automatique
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('kanban-container')) {
        kanbanManager = new ChronoChatKanban();
    }
});

// Export pour utilisation externe
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChronoChatKanban;
}
