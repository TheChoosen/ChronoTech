/**
 * Vue Kanban des Interventions - ChronoTech
 * Gestion du drag & drop et interactions en temps réel
 */

class InterventionKanban {
    constructor() {
        this.data = null;
        this.sortableInstances = [];
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = true;
        this.currentInterventionId = null;
        this.technicians = [];
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadTechnicians();
        await this.loadKanbanData();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Filtres
        document.getElementById('technician-filter').addEventListener('change', () => this.loadKanbanData());
        document.getElementById('priority-filter').addEventListener('change', () => this.loadKanbanData());
        document.getElementById('date-filter').addEventListener('change', () => this.loadKanbanData());
        
        // Actions
        document.getElementById('refresh-btn').addEventListener('click', () => this.loadKanbanData());
        document.getElementById('auto-refresh-toggle').addEventListener('click', () => this.toggleAutoRefresh());
        
        // Modal assignation
        const technicianSelect = document.getElementById('technician-select');
        const confirmBtn = document.getElementById('confirm-assign');
        
        if (technicianSelect) {
            technicianSelect.addEventListener('change', (e) => {
                const techId = e.target.value;
                
                if (techId) {
                    confirmBtn.disabled = false;
                    this.showTechnicianWorkload(techId);
                } else {
                    confirmBtn.disabled = true;
                    document.getElementById('technician-workload').style.display = 'none';
                }
            });
        }
        
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmAssignment());
        }
    }
    
    async loadTechnicians() {
        try {
            const response = await fetch('/api/kanban/technicians');
            const result = await response.json();
            
            if (result.success) {
                this.technicians = result.technicians;
                this.populateTechnicianFilters();
            }
        } catch (error) {
            console.error('Erreur chargement techniciens:', error);
        }
    }
    
    populateTechnicianFilters() {
        const filterSelect = document.getElementById('technician-filter');
        const assignSelect = document.getElementById('technician-select');
        
        if (!filterSelect || !assignSelect) return;
        
        // Nettoyer les options existantes (sauf la première)
        filterSelect.innerHTML = '<option value="">Tous les techniciens</option>';
        assignSelect.innerHTML = '<option value="">Sélectionner un technicien...</option>';
        
        this.technicians.forEach(tech => {
            // Filtre
            const filterOption = document.createElement('option');
            filterOption.value = tech.id;
            filterOption.textContent = `${tech.name} (${tech.active_interventions} actives)`;
            filterSelect.appendChild(filterOption);
            
            // Assignation
            const assignOption = document.createElement('option');
            assignOption.value = tech.id;
            assignOption.textContent = tech.name;
            assignOption.dataset.workload = tech.active_interventions;
            assignOption.dataset.avgDuration = tech.avg_duration || 120;
            assignSelect.appendChild(assignOption);
        });
    }
    
    async loadKanbanData() {
        this.showLoader(true);
        
        try {
            const params = new URLSearchParams();
            
            // Ajouter les filtres
            const technicianFilter = document.getElementById('technician-filter').value;
            const priorityFilter = document.getElementById('priority-filter').value;
            const dateFilter = document.getElementById('date-filter').value;
            
            if (technicianFilter) params.append('technician_id', technicianFilter);
            if (priorityFilter) params.append('priority', priorityFilter);
            if (dateFilter) params.append('date', dateFilter);
            
            const response = await fetch(`/api/kanban/interventions?${params.toString()}`);
            const result = await response.json();
            
            if (result.success) {
                this.data = result;
                this.renderKanbanBoard();
                this.updateStats(result.stats);
                this.showNotification('Données mises à jour', 'success');
            } else {
                throw new Error(result.error || 'Erreur de chargement');
            }
            
        } catch (error) {
            console.error('Erreur chargement Kanban:', error);
            this.showNotification('Erreur de chargement des données', 'error');
        } finally {
            this.showLoader(false);
        }
    }
    
    renderKanbanBoard() {
        const board = document.getElementById('kanban-board');
        if (!board) return;
        
        board.innerHTML = '';
        
        // Nettoyer les instances Sortable existantes
        this.sortableInstances.forEach(instance => instance.destroy());
        this.sortableInstances = [];
        
        Object.entries(this.data.columns).forEach(([status, column]) => {
            const columnElement = this.createColumn(status, column);
            board.appendChild(columnElement);
            
            // Initialiser Sortable pour cette colonne si disponible
            if (typeof Sortable !== 'undefined') {
                const sortable = new Sortable(columnElement.querySelector('.kanban-column-body'), {
                    group: 'kanban',
                    animation: 150,
                    ghostClass: 'drag-ghost',
                    chosenClass: 'dragging',
                    dragClass: 'drag-item',
                    onStart: (evt) => {
                        evt.item.classList.add('dragging');
                    },
                    onEnd: (evt) => {
                        evt.item.classList.remove('dragging');
                        
                        // Si l'élément a changé de colonne
                        if (evt.from !== evt.to) {
                            const interventionId = evt.item.dataset.interventionId;
                            const newStatus = evt.to.closest('.kanban-column').dataset.status;
                            this.updateInterventionStatus(interventionId, newStatus);
                        }
                    }
                });
                
                this.sortableInstances.push(sortable);
            }
        });
    }
    
    createColumn(status, column) {
        const columnDiv = document.createElement('div');
        columnDiv.className = `kanban-column status-${status}`;
        columnDiv.dataset.status = status;
        
        columnDiv.innerHTML = `
            <div class="kanban-column-header">
                <div class="kanban-column-title">${column.title}</div>
                <div class="kanban-column-count">${column.items.length}</div>
            </div>
            <div class="kanban-column-body">
                ${column.items.length === 0 ? 
                    '<div class="kanban-empty">Aucune intervention</div>' : 
                    column.items.map(item => this.createCard(item)).join('')
                }
            </div>
        `;
        
        return columnDiv;
    }
    
    createCard(intervention) {
        const isOverdue = intervention.is_overdue ? 'overdue' : '';
        const vehicleInfo = intervention.vehicle_info ? 
            `<div class="kanban-card-vehicle">🚗 ${intervention.vehicle_info} - ${intervention.license_plate || 'N/A'}</div>` : '';
        
        const technicianInfo = intervention.technician_name ?
            `<div class="kanban-card-technician">
                <i class="fas fa-user"></i> ${intervention.technician_name}
            </div>` : '';
        
        const scheduledDate = intervention.scheduled_date ? 
            new Date(intervention.scheduled_date).toLocaleString('fr-FR', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) : 'Non planifié';
        
        return `
            <div class="kanban-card priority-${intervention.priority || 'low'}" 
                 data-intervention-id="${intervention.id}"
                 onclick="kanban.openInterventionDetails(${intervention.id})">
                
                <div class="kanban-card-actions">
                    <button class="kanban-card-action" title="Assigner" 
                            onclick="event.stopPropagation(); kanban.openAssignModal(${intervention.id})">
                        <i class="fas fa-user-plus"></i>
                    </button>
                    <button class="kanban-card-action" title="Détails" 
                            onclick="event.stopPropagation(); kanban.openInterventionDetails(${intervention.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
                
                <div class="kanban-card-header">
                    <a href="/work_orders/${intervention.id}/details" class="kanban-card-number" 
                       onclick="event.stopPropagation()">
                        #${intervention.claim_number || intervention.id}
                    </a>
                    <span class="kanban-card-priority priority-${intervention.priority || 'low'}">
                        ${this.getPriorityLabel(intervention.priority)}
                    </span>
                </div>
                
                <div class="kanban-card-title">${intervention.description || 'Description manquante'}</div>
                
                <div class="kanban-card-customer">
                    <i class="fas fa-building"></i> ${intervention.customer_name || 'Client inconnu'}
                </div>
                
                ${technicianInfo}
                ${vehicleInfo}
                
                <div class="kanban-card-footer">
                    <div class="kanban-card-date ${isOverdue}">
                        <i class="fas fa-calendar-alt"></i>
                        ${scheduledDate}
                    </div>
                    <div class="kanban-card-indicators">
                        <div class="kanban-indicator ${intervention.notes_count > 0 ? 'has-content' : ''}">
                            <i class="fas fa-sticky-note"></i>
                            ${intervention.notes_count || 0}
                        </div>
                        <div class="kanban-indicator ${intervention.media_count > 0 ? 'has-content' : ''}">
                            <i class="fas fa-paperclip"></i>
                            ${intervention.media_count || 0}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    getPriorityLabel(priority) {
        const labels = {
            urgent: 'URGENT',
            high: 'ÉLEVÉE',
            medium: 'MOYENNE',
            low: 'FAIBLE'
        };
        return labels[priority] || 'FAIBLE';
    }
    
    async updateInterventionStatus(interventionId, newStatus) {
        try {
            const response = await fetch(`/api/kanban/interventions/${interventionId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: newStatus })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`Statut mis à jour: ${this.getStatusLabel(newStatus)}`, 'success');
                // Recharger pour mettre à jour les compteurs
                setTimeout(() => this.loadKanbanData(), 1000);
            } else {
                throw new Error(result.error || 'Erreur de mise à jour');
            }
            
        } catch (error) {
            console.error('Erreur mise à jour statut:', error);
            this.showNotification('Erreur lors de la mise à jour', 'error');
            // Recharger pour annuler le déplacement
            this.loadKanbanData();
        }
    }
    
    getStatusLabel(status) {
        const labels = {
            pending: 'En attente',
            assigned: 'Assigné',
            in_progress: 'En cours',
            waiting_parts: 'Attente pièces',
            completed: 'Terminé',
            cancelled: 'Annulé'
        };
        return labels[status] || status;
    }
    
    openAssignModal(interventionId) {
        this.currentInterventionId = interventionId;
        const technicianSelect = document.getElementById('technician-select');
        const confirmBtn = document.getElementById('confirm-assign');
        const workloadDiv = document.getElementById('technician-workload');
        
        if (technicianSelect) technicianSelect.value = '';
        if (confirmBtn) confirmBtn.disabled = true;
        if (workloadDiv) workloadDiv.style.display = 'none';
        
        if (typeof $ !== 'undefined') {
            $('#assignModal').modal('show');
        }
    }
    
    showTechnicianWorkload(technicianId) {
        const option = document.querySelector(`#technician-select option[value="${technicianId}"]`);
        const workloadInfo = document.getElementById('workload-info');
        const workloadDiv = document.getElementById('technician-workload');
        
        if (option && workloadInfo && workloadDiv) {
            const workload = option.dataset.workload || 0;
            const avgDuration = Math.round(option.dataset.avgDuration || 120);
            
            workloadInfo.textContent = 
                `${workload} interventions actives (durée moyenne: ${avgDuration}min)`;
            workloadDiv.style.display = 'block';
        }
    }
    
    async confirmAssignment() {
        const technicianId = document.getElementById('technician-select').value;
        
        if (!technicianId || !this.currentInterventionId) return;
        
        try {
            const response = await fetch(`/api/kanban/interventions/${this.currentInterventionId}/assign`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ technician_id: technicianId })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`Intervention assignée à ${result.technician_name}`, 'success');
                if (typeof $ !== 'undefined') {
                    $('#assignModal').modal('hide');
                }
                this.loadKanbanData();
            } else {
                throw new Error(result.error || 'Erreur d\'assignation');
            }
            
        } catch (error) {
            console.error('Erreur assignation:', error);
            this.showNotification('Erreur lors de l\'assignation', 'error');
        }
    }
    
    openInterventionDetails(interventionId) {
        // Ouvrir dans un nouvel onglet
        window.open(`/work_orders/${interventionId}/details`, '_blank');
    }
    
    updateStats(stats) {
        const totalCount = document.querySelector('#total-count span');
        const urgentCount = document.querySelector('#urgent-count span');
        const overdueCount = document.querySelector('#overdue-count span');
        const progressCount = document.querySelector('#progress-count span');
        
        if (totalCount) totalCount.textContent = stats.total || 0;
        if (urgentCount) urgentCount.textContent = stats.urgent || 0;
        if (overdueCount) overdueCount.textContent = stats.overdue || 0;
        if (progressCount) progressCount.textContent = stats.in_progress || 0;
    }
    
    startAutoRefresh() {
        if (this.autoRefreshEnabled) {
            this.autoRefreshInterval = setInterval(() => {
                this.loadKanbanData();
            }, 30000); // 30 secondes
        }
    }
    
    toggleAutoRefresh() {
        const btn = document.getElementById('auto-refresh-toggle');
        if (!btn) return;
        
        this.autoRefreshEnabled = !this.autoRefreshEnabled;
        
        if (this.autoRefreshEnabled) {
            btn.innerHTML = '<i class="fas fa-pause"></i> Auto-refresh';
            btn.classList.remove('btn-outline-secondary');
            btn.classList.add('btn-outline-success');
            this.startAutoRefresh();
        } else {
            btn.innerHTML = '<i class="fas fa-play"></i> Auto-refresh';
            btn.classList.remove('btn-outline-success');
            btn.classList.add('btn-outline-secondary');
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.autoRefreshInterval = null;
            }
        }
    }
    
    showLoader(show) {
        const loader = document.getElementById('loader');
        if (loader) {
            loader.style.display = show ? 'flex' : 'none';
        }
    }
    
    showNotification(message, type = 'info') {
        // Créer ou réutiliser l'élément de notification
        let notification = document.querySelector('.update-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.className = 'update-notification';
            document.body.appendChild(notification);
        }
        
        // Définir la couleur selon le type
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#007bff'
        };
        
        notification.style.background = colors[type] || colors.info;
        notification.textContent = message;
        notification.classList.add('show');
        
        // Masquer après 3 secondes
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }
}

// Initialiser la vue Kanban quand le DOM est prêt
let kanban;
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier si nous sommes sur la page Kanban
    if (document.getElementById('kanban-board')) {
        kanban = new InterventionKanban();
    }
});

// Nettoyage au déchargement de la page
window.addEventListener('beforeunload', () => {
    if (kanban && kanban.autoRefreshInterval) {
        clearInterval(kanban.autoRefreshInterval);
    }
});
