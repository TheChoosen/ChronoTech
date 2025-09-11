/**
 * Dashboard Kanban Modals JavaScript
 * Gestion des modals Kanban pour techniciens et bons de travail
 */

class DashboardKanban {
    constructor() {
        this.techniciansData = [];
        this.workOrdersData = [];
        this.autoRefreshInterval = null;
        this.refreshRate = 30000; // 30 secondes
        this.init();
    }

    init() {
        this.initEventListeners();
        this.initDragAndDrop();
        this.startAutoRefresh();
    }

    initEventListeners() {
        // Techniciens Kanban
        const techModal = document.getElementById('techniciansKanbanModal');
        if (techModal) {
            techModal.addEventListener('shown.bs.modal', () => {
                this.loadTechniciansData();
            });

            // Filtres et actions
            document.getElementById('technicianSearchFilter')?.addEventListener('input', (e) => {
                this.filterTechnicians(e.target.value);
            });

            document.getElementById('refreshTechniciansKanban')?.addEventListener('click', () => {
                this.loadTechniciansData(true);
            });

            document.getElementById('exportTechniciansData')?.addEventListener('click', () => {
                this.exportTechniciansData();
            });
        }

        // Work Orders Kanban
        const workOrderModal = document.getElementById('workOrdersKanbanModal');
        if (workOrderModal) {
            workOrderModal.addEventListener('shown.bs.modal', () => {
                this.loadWorkOrdersData();
            });

            // Filtres et actions
            document.getElementById('workOrderSearchFilter')?.addEventListener('input', (e) => {
                this.filterWorkOrders(e.target.value);
            });

            document.getElementById('priorityFilter')?.addEventListener('change', (e) => {
                this.filterWorkOrdersByPriority(e.target.value);
            });

            document.getElementById('refreshWorkOrdersKanban')?.addEventListener('click', () => {
                this.loadWorkOrdersData(true);
            });

            document.getElementById('exportWorkOrdersData')?.addEventListener('click', () => {
                this.exportWorkOrdersData();
            });
        }
    }

    initDragAndDrop() {
        // Initialisation du drag & drop avec SortableJS si disponible
        if (typeof Sortable !== 'undefined') {
            this.initTechniciansDragDrop();
            this.initWorkOrdersDragDrop();
        }
    }

    initTechniciansDragDrop() {
        const columns = ['availableTechnicians', 'busyTechnicians', 'pauseTechnicians', 'offlineTechnicians'];
        
        columns.forEach(columnId => {
            const element = document.getElementById(columnId);
            if (element) {
                new Sortable(element, {
                    group: 'technicians',
                    animation: 150,
                    ghostClass: 'dragging',
                    onEnd: (evt) => {
                        this.handleTechnicianMove(evt);
                    }
                });
            }
        });
    }

    initWorkOrdersDragDrop() {
        const columns = ['pendingWorkOrders', 'assignedWorkOrders', 'inProgressWorkOrders', 'reviewWorkOrders', 'completedWorkOrders'];
        
        columns.forEach(columnId => {
            const element = document.getElementById(columnId);
            if (element) {
                new Sortable(element, {
                    group: 'workorders',
                    animation: 150,
                    ghostClass: 'dragging',
                    onEnd: (evt) => {
                        this.handleWorkOrderMove(evt);
                    }
                });
            }
        });
    }

    async loadTechniciansData(showLoader = false) {
        if (showLoader) {
            this.showTechniciansLoader();
        }

        try {
            const response = await fetch('/api/dashboard/technicians');
            if (response.ok) {
                this.techniciansData = await response.json();
                this.renderTechnicians();
                this.updateTechniciansStats();
                this.updateLastUpdateTime('lastUpdateTime');
            } else {
                console.error('Erreur lors du chargement des techniciens:', response.statusText);
                this.showTechniciansError();
            }
        } catch (error) {
            console.error('Erreur réseau:', error);
            this.showTechniciansError();
        }
    }

    async loadWorkOrdersData(showLoader = false) {
        if (showLoader) {
            this.showWorkOrdersLoader();
        }

        try {
            const response = await fetch('/api/dashboard/work-orders');
            if (response.ok) {
                this.workOrdersData = await response.json();
                this.renderWorkOrders();
                this.updateWorkOrdersStats();
                this.updateLastUpdateTime('lastWorkOrderUpdateTime');
            } else {
                console.error('Erreur lors du chargement des bons de travail:', response.statusText);
                this.showWorkOrdersError();
            }
        } catch (error) {
            console.error('Erreur réseau:', error);
            this.showWorkOrdersError();
        }
    }

    renderTechnicians() {
        const columns = {
            available: document.getElementById('availableTechnicians'),
            busy: document.getElementById('busyTechnicians'),
            pause: document.getElementById('pauseTechnicians'),
            offline: document.getElementById('offlineTechnicians')
        };

        // Vider les colonnes
        Object.values(columns).forEach(column => {
            if (column) column.innerHTML = '';
        });

        this.techniciansData.forEach(technician => {
            const card = this.createTechnicianCard(technician);
            const targetColumn = columns[technician.status];
            if (targetColumn) {
                targetColumn.appendChild(card);
            }
        });

        // Afficher message si vide
        Object.entries(columns).forEach(([status, column]) => {
            if (column && column.children.length === 0) {
                column.appendChild(this.createEmptyState('technician', status));
            }
        });
    }

    renderWorkOrders() {
        const columns = {
            pending: document.getElementById('pendingWorkOrders'),
            assigned: document.getElementById('assignedWorkOrders'),
            in_progress: document.getElementById('inProgressWorkOrders'),
            review: document.getElementById('reviewWorkOrders'),
            completed: document.getElementById('completedWorkOrders')
        };

        // Vider les colonnes
        Object.values(columns).forEach(column => {
            if (column) column.innerHTML = '';
        });

        this.workOrdersData.forEach(workOrder => {
            const card = this.createWorkOrderCard(workOrder);
            const targetColumn = columns[workOrder.status];
            if (targetColumn) {
                targetColumn.appendChild(card);
            }
        });

        // Afficher message si vide
        Object.entries(columns).forEach(([status, column]) => {
            if (column && column.children.length === 0) {
                column.appendChild(this.createEmptyState('workorder', status));
            }
        });
    }

    createTechnicianCard(technician) {
        const card = document.createElement('div');
        card.className = 'technician-card card-enter';
        card.dataset.technicianId = technician.id;
        
        const initials = technician.name.split(' ').map(n => n[0]).join('').toUpperCase();
        
        card.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="technician-avatar me-3">
                    ${technician.avatar ? `<img src="${technician.avatar}" alt="${technician.name}" class="w-100 h-100 rounded-circle">` : initials}
                </div>
                <div class="technician-info flex-grow-1">
                    <h6 class="mb-1">${technician.name}</h6>
                    <small class="text-muted">${technician.specialization || 'Technicien'}</small>
                    <div class="d-flex justify-content-between align-items-center mt-2">
                        <small class="text-muted">
                            <i class="fas fa-tasks me-1"></i>
                            ${technician.active_tasks || 0} tâches
                        </small>
                        <span class="badge bg-${this.getStatusColor(technician.status)} technician-badge">
                            ${this.getStatusLabel(technician.status)}
                        </span>
                    </div>
                </div>
            </div>
            <div class="card-actions">
                <button class="btn btn-sm btn-outline-primary card-action-btn" onclick="dashboardKanban.viewTechnicianDetails(${technician.id})" title="Voir détails">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-success card-action-btn" onclick="dashboardKanban.assignTaskToTechnician(${technician.id})" title="Assigner tâche">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
        `;

        card.addEventListener('click', () => {
            this.viewTechnicianDetails(technician.id);
        });

        return card;
    }

    createWorkOrderCard(workOrder) {
        const card = document.createElement('div');
        card.className = 'work-order-card card-enter';
        card.dataset.workOrderId = workOrder.id;
        
        const priorityClass = `priority-${workOrder.priority}`;
        const statusClass = `status-${workOrder.status}`;
        
        card.innerHTML = `
            <div class="status-indicator ${statusClass}"></div>
            <div class="card-details" style="margin-left: 8px;">
                <div class="card-title">${workOrder.title}</div>
                <div class="text-muted small mb-2">${workOrder.customer_name}</div>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        <i class="fas fa-calendar me-1"></i>
                        ${this.formatDate(workOrder.created_at)}
                    </small>
                    <span class="badge ${priorityClass} priority-badge">
                        ${this.getPriorityLabel(workOrder.priority)}
                    </span>
                </div>
                ${workOrder.assigned_technician ? `
                    <div class="mt-2">
                        <span class="technician-badge">
                            <i class="fas fa-user me-1"></i>
                            ${workOrder.assigned_technician}
                        </span>
                    </div>
                ` : ''}
                <div class="card-meta">
                    <i class="fas fa-clock me-1"></i>
                    Estimé: ${workOrder.estimated_duration || 'N/A'}h
                </div>
            </div>
            <div class="card-actions">
                <button class="btn btn-sm btn-outline-primary card-action-btn" onclick="dashboardKanban.viewWorkOrderDetails(${workOrder.id})" title="Voir détails">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-warning card-action-btn" onclick="dashboardKanban.editWorkOrder(${workOrder.id})" title="Modifier">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        `;

        card.addEventListener('click', () => {
            this.viewWorkOrderDetails(workOrder.id);
        });

        return card;
    }

    createEmptyState(type, status) {
        const div = document.createElement('div');
        div.className = 'p-3 text-center text-muted empty-state';
        
        const messages = {
            technician: {
                available: { icon: 'user-check', text: 'Aucun technicien disponible' },
                busy: { icon: 'tools', text: 'Aucun technicien en mission' },
                pause: { icon: 'coffee', text: 'Aucun technicien en pause' },
                offline: { icon: 'user-slash', text: 'Aucun technicien hors ligne' }
            },
            workorder: {
                pending: { icon: 'hourglass-start', text: 'Aucune intervention en attente' },
                assigned: { icon: 'user-check', text: 'Aucune intervention assignée' },
                in_progress: { icon: 'tools', text: 'Aucune intervention en cours' },
                review: { icon: 'search', text: 'Aucune intervention en révision' },
                completed: { icon: 'trophy', text: 'Aucune intervention terminée' }
            }
        };

        const message = messages[type]?.[status] || { icon: 'info-circle', text: 'Aucun élément' };
        
        div.innerHTML = `
            <i class="fas fa-${message.icon} fa-2x mb-2"></i>
            <p class="mb-0 small">${message.text}</p>
        `;

        return div;
    }

    updateTechniciansStats() {
        const stats = {
            available: 0,
            busy: 0,
            offline: 0,
            totalTasks: 0
        };

        this.techniciansData.forEach(technician => {
            stats[technician.status]++;
            stats.totalTasks += technician.active_tasks || 0;
        });

        document.getElementById('availableTechCount').textContent = stats.available;
        document.getElementById('busyTechCount').textContent = stats.busy;
        document.getElementById('offlineTechCount').textContent = stats.offline;
        document.getElementById('totalTasksCount').textContent = stats.totalTasks;

        // Mettre à jour les compteurs dans les headers
        document.getElementById('availableCount').textContent = stats.available;
        document.getElementById('busyCount').textContent = stats.busy;
        document.getElementById('pauseCount').textContent = this.techniciansData.filter(t => t.status === 'pause').length;
        document.getElementById('offlineCount').textContent = stats.offline;
    }

    updateWorkOrdersStats() {
        const stats = {
            pending: 0,
            assigned: 0,
            in_progress: 0,
            review: 0,
            completed: 0,
            urgent: 0
        };

        this.workOrdersData.forEach(workOrder => {
            stats[workOrder.status]++;
            if (workOrder.priority === 'urgent') stats.urgent++;
        });

        // Mettre à jour les statistiques générales
        Object.keys(stats).forEach(key => {
            const element = document.getElementById(`${key}WorkOrdersCount`);
            if (element) element.textContent = stats[key];
        });

        // Mettre à jour les compteurs dans les headers
        Object.keys(stats).forEach(key => {
            if (key !== 'urgent') {
                const element = document.getElementById(`${key}Count`);
                if (element) element.textContent = stats[key];
            }
        });
    }

    updateLastUpdateTime(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = new Date().toLocaleTimeString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    // Utilitaires
    getStatusColor(status) {
        const colors = {
            available: 'success',
            busy: 'warning',
            pause: 'info',
            offline: 'danger'
        };
        return colors[status] || 'secondary';
    }

    getStatusLabel(status) {
        const labels = {
            available: 'Disponible',
            busy: 'Occupé',
            pause: 'En pause',
            offline: 'Hors ligne'
        };
        return labels[status] || status;
    }

    getPriorityLabel(priority) {
        const labels = {
            low: 'Faible',
            normal: 'Normale',
            high: 'Élevée',
            urgent: 'Urgente'
        };
        return labels[priority] || priority;
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit'
        });
    }

    // Filtres
    filterTechnicians(searchTerm) {
        const cards = document.querySelectorAll('.technician-card');
        cards.forEach(card => {
            const name = card.querySelector('.technician-info h6').textContent.toLowerCase();
            const visible = name.includes(searchTerm.toLowerCase());
            card.style.display = visible ? 'block' : 'none';
        });
    }

    filterWorkOrders(searchTerm) {
        const cards = document.querySelectorAll('.work-order-card');
        cards.forEach(card => {
            const title = card.querySelector('.card-title').textContent.toLowerCase();
            const customer = card.querySelector('.text-muted.small').textContent.toLowerCase();
            const visible = title.includes(searchTerm.toLowerCase()) || customer.includes(searchTerm.toLowerCase());
            card.style.display = visible ? 'block' : 'none';
        });
    }

    filterWorkOrdersByPriority(priority) {
        const cards = document.querySelectorAll('.work-order-card');
        cards.forEach(card => {
            if (!priority) {
                card.style.display = 'block';
            } else {
                const priorityBadge = card.querySelector('.priority-badge');
                const cardPriority = priorityBadge ? priorityBadge.className.match(/priority-(\w+)/)?.[1] : null;
                card.style.display = cardPriority === priority ? 'block' : 'none';
            }
        });
    }

    // Actions
    async handleTechnicianMove(evt) {
        const technicianId = evt.item.dataset.technicianId;
        const newStatus = evt.to.id.replace('Technicians', '').toLowerCase();
        
        try {
            const response = await fetch(`/api/technicians/${technicianId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la mise à jour du statut');
            }

            this.showToast('Statut du technicien mis à jour avec succès', 'success');
            this.loadTechniciansData();
        } catch (error) {
            console.error('Erreur:', error);
            this.showToast('Erreur lors de la mise à jour du statut', 'error');
            // Recharger pour annuler le changement visuel
            this.loadTechniciansData();
        }
    }

    async handleWorkOrderMove(evt) {
        const workOrderId = evt.item.dataset.workOrderId;
        const newStatus = evt.to.id.replace('WorkOrders', '').toLowerCase();
        
        try {
            const response = await fetch(`/api/work-orders/${workOrderId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la mise à jour du statut');
            }

            this.showToast('Statut de l\'intervention mis à jour avec succès', 'success');
            this.loadWorkOrdersData();
        } catch (error) {
            console.error('Erreur:', error);
            this.showToast('Erreur lors de la mise à jour du statut', 'error');
            // Recharger pour annuler le changement visuel
            this.loadWorkOrdersData();
        }
    }

    // Actions sur les cartes
    viewTechnicianDetails(technicianId) {
        // Ouvrir modal de détails du technicien
        console.log('Voir détails technicien:', technicianId);
    }

    assignTaskToTechnician(technicianId) {
        // Ouvrir modal d'assignation de tâche
        console.log('Assigner tâche au technicien:', technicianId);
    }

    viewWorkOrderDetails(workOrderId) {
        // Ouvrir modal de détails du bon de travail
        console.log('Voir détails bon de travail:', workOrderId);
    }

    editWorkOrder(workOrderId) {
        // Ouvrir modal d'édition du bon de travail
        console.log('Modifier bon de travail:', workOrderId);
    }

    // Export
    exportTechniciansData() {
        const csvContent = this.convertTechniciansToCSV();
        this.downloadCSV(csvContent, 'techniciens-kanban.csv');
    }

    exportWorkOrdersData() {
        const csvContent = this.convertWorkOrdersToCSV();
        this.downloadCSV(csvContent, 'interventions-kanban.csv');
    }

    convertTechniciansToCSV() {
        const headers = ['Nom', 'Statut', 'Spécialisation', 'Tâches actives'];
        const rows = this.techniciansData.map(tech => [
            tech.name,
            this.getStatusLabel(tech.status),
            tech.specialization || '',
            tech.active_tasks || 0
        ]);
        
        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }

    convertWorkOrdersToCSV() {
        const headers = ['Titre', 'Client', 'Statut', 'Priorité', 'Technicien', 'Date création'];
        const rows = this.workOrdersData.map(wo => [
            wo.title,
            wo.customer_name,
            wo.status,
            this.getPriorityLabel(wo.priority),
            wo.assigned_technician || '',
            this.formatDate(wo.created_at)
        ]);
        
        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }

    downloadCSV(content, filename) {
        const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Auto-actualisation
    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            // Actualiser seulement si les modals sont ouvertes
            if (document.getElementById('techniciansKanbanModal')?.classList.contains('show')) {
                this.loadTechniciansData();
            }
            if (document.getElementById('workOrdersKanbanModal')?.classList.contains('show')) {
                this.loadWorkOrdersData();
            }
        }, this.refreshRate);
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }

    // États de chargement et d'erreur
    showTechniciansLoader() {
        const columns = ['availableTechnicians', 'busyTechnicians', 'pauseTechnicians', 'offlineTechnicians'];
        columns.forEach(columnId => {
            const column = document.getElementById(columnId);
            if (column) {
                column.innerHTML = this.getLoadingHTML();
            }
        });
    }

    showWorkOrdersLoader() {
        const columns = ['pendingWorkOrders', 'assignedWorkOrders', 'inProgressWorkOrders', 'reviewWorkOrders', 'completedWorkOrders'];
        columns.forEach(columnId => {
            const column = document.getElementById(columnId);
            if (column) {
                column.innerHTML = this.getLoadingHTML();
            }
        });
    }

    getLoadingHTML() {
        return `
            <div class="loading-card loading-skeleton"></div>
            <div class="loading-card loading-skeleton"></div>
            <div class="loading-card loading-skeleton"></div>
        `;
    }

    showTechniciansError() {
        const columns = ['availableTechnicians', 'busyTechnicians', 'pauseTechnicians', 'offlineTechnicians'];
        columns.forEach(columnId => {
            const column = document.getElementById(columnId);
            if (column) {
                column.innerHTML = `
                    <div class="p-3 text-center text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <p class="mb-0 small">Erreur de chargement</p>
                    </div>
                `;
            }
        });
    }

    showWorkOrdersError() {
        const columns = ['pendingWorkOrders', 'assignedWorkOrders', 'inProgressWorkOrders', 'reviewWorkOrders', 'completedWorkOrders'];
        columns.forEach(columnId => {
            const column = document.getElementById(columnId);
            if (column) {
                column.innerHTML = `
                    <div class="p-3 text-center text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <p class="mb-0 small">Erreur de chargement</p>
                    </div>
                `;
            }
        });
    }

    showToast(message, type = 'info') {
        // Utiliser le système de toast existant ou créer un simple alert
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
}

// Initialisation globale
let dashboardKanban;

document.addEventListener('DOMContentLoaded', function() {
    dashboardKanban = new DashboardKanban();
});

// Mock data pour les tests (à supprimer en production)
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    // Mock endpoints pour les tests
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        if (url.includes('/api/dashboard/technicians')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([
                    { id: 1, name: 'Jean Dupont', status: 'available', specialization: 'Électricien', active_tasks: 2 },
                    { id: 2, name: 'Marie Martin', status: 'busy', specialization: 'Plombier', active_tasks: 1 },
                    { id: 3, name: 'Pierre Durant', status: 'pause', specialization: 'Chauffagiste', active_tasks: 0 },
                    { id: 4, name: 'Sophie Blanc', status: 'offline', specialization: 'Électricien', active_tasks: 0 }
                ])
            });
        }
        
        if (url.includes('/api/dashboard/work-orders')) {
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([
                    { id: 1, title: 'Réparation chauffage', customer_name: 'Client A', status: 'pending', priority: 'urgent', created_at: '2025-09-09T10:00:00' },
                    { id: 2, title: 'Installation électrique', customer_name: 'Client B', status: 'assigned', priority: 'high', assigned_technician: 'Jean Dupont', created_at: '2025-09-09T09:00:00' },
                    { id: 3, title: 'Maintenance climatisation', customer_name: 'Client C', status: 'in_progress', priority: 'normal', assigned_technician: 'Marie Martin', created_at: '2025-09-08T14:00:00' },
                    { id: 4, title: 'Inspection sécurité', customer_name: 'Client D', status: 'review', priority: 'low', assigned_technician: 'Pierre Durant', created_at: '2025-09-08T11:00:00' },
                    { id: 5, title: 'Réparation plomberie', customer_name: 'Client E', status: 'completed', priority: 'normal', assigned_technician: 'Sophie Blanc', created_at: '2025-09-07T16:00:00' }
                ])
            });
        }
        
        return originalFetch.apply(this, arguments);
    };
}
