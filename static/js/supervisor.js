/**
 * JavaScript Dashboard Superviseur avec Kanban - Sprint 3
 * Gestion drag & drop et interface temps réel
 */

class SupervisorDashboard {
    constructor() {
        this.websocket = null;
        this.currentView = 'kanban';
        this.filters = {
            technician: 'all',
            priority: 'all',
            status: 'all',
            date: 'today'
        };
        this.draggedTask = null;
        this.refreshInterval = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupWebSocket();
        this.setupFilters();
        this.startAutoRefresh();
        this.loadDashboardData();
    }
    
    setupEventListeners() {
        // Changement de vue
        document.addEventListener('click', (e) => {
            if (e.target.closest('.view-btn')) {
                this.switchView(e.target.dataset.view);
            }
        });
        
        // Actions sur les tâches
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-assign')) {
                this.handleAssignTask(e);
            } else if (e.target.closest('.btn-priority')) {
                this.handleChangePriority(e);
            } else if (e.target.closest('.btn-details')) {
                this.handleTaskDetails(e);
            }
        });
        
        // Gestion des modales
        document.addEventListener('click', (e) => {
            if (e.target.closest('.close-modal')) {
                this.closeModal(e.target.closest('.modal'));
            }
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });
        
        // Actions d'en-tête
        document.addEventListener('click', (e) => {
            if (e.target.closest('#refresh-dashboard')) {
                this.refreshDashboard();
            } else if (e.target.closest('#export-data')) {
                this.exportDashboardData();
            }
        });
        
        // Raccourcis clavier
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshDashboard();
                        break;
                    case 'k':
                        e.preventDefault();
                        this.switchView('kanban');
                        break;
                    case 'g':
                        e.preventDefault();
                        this.switchView('gantt');
                        break;
                }
            }
        });
        
        // Redimensionnement fenêtre
        window.addEventListener('resize', () => {
            this.adjustLayout();
        });
    }
    
    // ===== DRAG & DROP KANBAN =====
    
    setupDragAndDrop() {
        this.setupDraggableItems();
        this.setupDropZones();
    }
    
    setupDraggableItems() {
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('task-card')) {
                this.draggedTask = e.target;
                e.target.classList.add('dragging');
                
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/html', e.target.outerHTML);
                e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
            }
        });
        
        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('task-card')) {
                e.target.classList.remove('dragging');
                this.clearDropPlaceholders();
                this.draggedTask = null;
            }
        });
    }
    
    setupDropZones() {
        document.addEventListener('dragover', (e) => {
            const dropZone = e.target.closest('.column-body');
            if (dropZone && this.draggedTask) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                
                this.showDropPlaceholder(dropZone, e.clientY);
            }
        });
        
        document.addEventListener('dragleave', (e) => {
            const dropZone = e.target.closest('.column-body');
            if (dropZone) {
                this.hideDropPlaceholder(dropZone);
            }
        });
        
        document.addEventListener('drop', (e) => {
            const dropZone = e.target.closest('.column-body');
            if (dropZone && this.draggedTask) {
                e.preventDefault();
                
                const taskId = this.draggedTask.dataset.taskId;
                const newStatus = dropZone.closest('.kanban-column').dataset.status;
                const oldStatus = this.draggedTask.closest('.kanban-column').dataset.status;
                
                if (newStatus !== oldStatus) {
                    this.moveTask(taskId, newStatus, dropZone);
                }
                
                this.clearDropPlaceholders();
            }
        });
    }
    
    showDropPlaceholder(dropZone, clientY) {
        this.clearDropPlaceholders();
        
        const placeholder = document.createElement('div');
        placeholder.className = 'drop-placeholder show';
        placeholder.innerHTML = 'Déposer la tâche ici';
        
        // Trouver la position d'insertion
        const tasks = Array.from(dropZone.querySelectorAll('.task-card:not(.dragging)'));
        let insertBefore = null;
        
        for (let task of tasks) {
            const rect = task.getBoundingClientRect();
            if (clientY < rect.top + rect.height / 2) {
                insertBefore = task;
                break;
            }
        }
        
        if (insertBefore) {
            dropZone.insertBefore(placeholder, insertBefore);
        } else {
            dropZone.appendChild(placeholder);
        }
    }
    
    hideDropPlaceholder(dropZone) {
        const placeholder = dropZone.querySelector('.drop-placeholder');
        if (placeholder) {
            placeholder.classList.remove('show');
            setTimeout(() => {
                if (placeholder.parentNode) {
                    placeholder.parentNode.removeChild(placeholder);
                }
            }, 200);
        }
    }
    
    clearDropPlaceholders() {
        document.querySelectorAll('.drop-placeholder').forEach(placeholder => {
            placeholder.classList.remove('show');
            setTimeout(() => {
                if (placeholder.parentNode) {
                    placeholder.parentNode.removeChild(placeholder);
                }
            }, 200);
        });
    }
    
    async moveTask(taskId, newStatus, dropZone) {
        try {
            // Animation optimiste
            const taskCard = this.draggedTask.cloneNode(true);
            taskCard.classList.remove('dragging');
            
            const placeholder = dropZone.querySelector('.drop-placeholder');
            if (placeholder) {
                dropZone.replaceChild(taskCard, placeholder);
            } else {
                dropZone.appendChild(taskCard);
            }
            
            // Supprimer l'ancienne carte
            this.draggedTask.style.opacity = '0.5';
            
            // Appel API
            const response = await this.apiRequest('PUT', `/supervisor/tasks/${taskId}/status`, {
                status: newStatus
            });
            
            if (response.success) {
                // Succès: supprimer l'ancienne carte
                this.draggedTask.remove();
                
                // Mettre à jour les compteurs
                this.updateColumnCounts();
                
                // Notification
                this.showNotification(`Tâche déplacée vers ${this.getStatusLabel(newStatus)}`, 'success');
                
                // Log pour audit
                this.logTaskMove(taskId, newStatus, response.technician_name);
            } else {
                throw new Error(response.message || 'Erreur lors du déplacement');
            }
        } catch (error) {
            // Erreur: annuler le déplacement
            taskCard.remove();
            this.draggedTask.style.opacity = '1';
            
            this.showNotification('Erreur: ' + error.message, 'error');
        }
    }
    
    // ===== GESTION DES TÂCHES =====
    
    async handleAssignTask(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        
        this.openAssignModal(taskId);
    }
    
    async handleChangePriority(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        const currentPriority = taskCard.dataset.priority;
        
        this.openPriorityModal(taskId, currentPriority);
    }
    
    async handleTaskDetails(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        
        this.openTaskDetailsModal(taskId);
    }
    
    async assignTask(taskId, technicianId) {
        try {
            const response = await this.apiRequest('PUT', `/supervisor/tasks/${taskId}/assign`, {
                technician_id: technicianId
            });
            
            if (response.success) {
                // Mettre à jour la carte
                const taskCard = document.querySelector(`[data-task-id=\"${taskId}\"]`);
                if (taskCard) {
                    this.updateTaskCard(taskCard, response.task);
                }
                
                this.showNotification('Tâche assignée avec succès', 'success');
                this.closeModals();
            } else {
                throw new Error(response.message || 'Erreur lors de l\'assignation');
            }
        } catch (error) {
            this.showNotification('Erreur: ' + error.message, 'error');
        }
    }
    
    async updateTaskPriority(taskId, priority) {
        try {
            const response = await this.apiRequest('PUT', `/supervisor/tasks/${taskId}/priority`, {
                priority: priority
            });
            
            if (response.success) {
                const taskCard = document.querySelector(`[data-task-id=\"${taskId}\"]`);
                if (taskCard) {
                    this.updateTaskCard(taskCard, response.task);
                }
                
                this.showNotification('Priorité mise à jour', 'success');
                this.closeModals();
            } else {
                throw new Error(response.message || 'Erreur lors de la mise à jour');
            }
        } catch (error) {
            this.showNotification('Erreur: ' + error.message, 'error');
        }
    }
    
    // ===== FILTRES =====
    
    setupFilters() {
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('filter-select')) {
                const filterType = e.target.dataset.filter;
                const filterValue = e.target.value;
                
                this.filters[filterType] = filterValue;
                this.applyFilters();
            }
        });
    }
    
    applyFilters() {
        const taskCards = document.querySelectorAll('.task-card');
        
        taskCards.forEach(card => {
            let visible = true;
            
            // Filtre technicien
            if (this.filters.technician !== 'all') {
                const technicianId = card.dataset.technicianId;
                if (technicianId !== this.filters.technician) {
                    visible = false;
                }
            }
            
            // Filtre priorité
            if (this.filters.priority !== 'all') {
                const priority = card.dataset.priority;
                if (priority !== this.filters.priority) {
                    visible = false;
                }
            }
            
            // Filtre statut
            if (this.filters.status !== 'all') {
                const column = card.closest('.kanban-column');
                const status = column ? column.dataset.status : null;
                if (status !== this.filters.status) {
                    visible = false;
                }
            }
            
            // Appliquer la visibilité
            card.style.display = visible ? 'block' : 'none';
        });
        
        // Mettre à jour les compteurs
        this.updateColumnCounts();
    }
    
    // ===== MÉTRIQUES ET DONNÉES =====
    
    async loadDashboardData() {
        try {
            this.showLoadingOverlay();
            
            const response = await this.apiRequest('GET', '/supervisor/dashboard-data');
            
            if (response.success) {
                this.updateMetrics(response.metrics);
                this.updateKanbanBoard(response.tasks);
                this.updateTechnicianList(response.technicians);
            } else {
                throw new Error(response.message || 'Erreur lors du chargement');
            }
        } catch (error) {
            this.showNotification('Erreur: ' + error.message, 'error');
        } finally {
            this.hideLoadingOverlay();
        }
    }
    
    updateMetrics(metrics) {
        Object.keys(metrics).forEach(key => {
            const metricCard = document.querySelector(`[data-metric=\"${key}\"]`);
            if (metricCard) {
                const valueElement = metricCard.querySelector('.metric-value');
                const changeElement = metricCard.querySelector('.metric-change');
                
                if (valueElement) {
                    valueElement.textContent = metrics[key].value;
                }
                
                if (changeElement && metrics[key].change !== undefined) {
                    const change = metrics[key].change;
                    changeElement.textContent = `${change > 0 ? '+' : ''}${change}%`;
                    changeElement.className = `metric-change ${change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral'}`;
                }
            }
        });
    }
    
    updateKanbanBoard(tasks) {
        // Vider les colonnes
        document.querySelectorAll('.column-body').forEach(column => {
            column.innerHTML = '';
        });
        
        // Ajouter les tâches
        tasks.forEach(task => {
            const taskCard = this.createTaskCard(task);
            const column = document.querySelector(`[data-status=\"${task.status}\"] .column-body`);
            if (column) {
                column.appendChild(taskCard);
            }
        });
        
        // Mettre à jour les compteurs
        this.updateColumnCounts();
        
        // Réappliquer les filtres
        this.applyFilters();
    }
    
    createTaskCard(task) {
        const card = document.createElement('div');
        card.className = 'task-card';
        card.draggable = true;
        card.dataset.taskId = task.id;
        card.dataset.priority = task.priority;
        card.dataset.technicianId = task.technician_id || '';
        
        card.innerHTML = `
            <div class="task-header">
                <span class="task-id">#${task.id}</span>
                <span class="task-priority ${task.priority}">${task.priority.toUpperCase()}</span>
            </div>
            <div class="task-title">${task.title}</div>
            <div class="task-customer">${task.customer_name || 'Client non défini'}</div>
            <div class="task-meta">
                <div class="task-technician">
                    <div class="technician-avatar">${this.getInitials(task.technician_name)}</div>
                    <span>${task.technician_name || 'Non assigné'}</span>
                </div>
                <div class="task-time">${this.formatTaskTime(task)}</div>
            </div>
            <div class="quick-actions">
                <button class="action-btn btn-assign" title="Assigner">
                    👤
                </button>
                <button class="action-btn btn-priority" title="Priorité">
                    ⚡
                </button>
                <button class="action-btn btn-details" title="Détails">
                    👁️
                </button>
            </div>
        `;
        
        return card;
    }
    
    updateColumnCounts() {
        document.querySelectorAll('.kanban-column').forEach(column => {
            const visibleTasks = column.querySelectorAll('.task-card:not([style*=\"display: none\"])');
            const countElement = column.querySelector('.column-count');
            if (countElement) {
                countElement.textContent = visibleTasks.length;
            }
        });
    }
    
    // ===== WEBSOCKET TEMPS RÉEL =====
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/supervisor`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connecté');
                this.showNotification('Connexion temps réel établie', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket fermé');
                this.showNotification('Connexion temps réel fermée', 'warning');
                
                // Tentative de reconnexion
                setTimeout(() => {
                    this.setupWebSocket();
                }, 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('Erreur WebSocket:', error);
            };
        } catch (error) {
            console.log('WebSocket non supporté, utilisation du polling');
            this.startPolling();
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'task_updated':
                this.handleTaskUpdate(data.task);
                break;
            case 'task_assigned':
                this.handleTaskAssignment(data.task, data.technician);
                break;
            case 'task_started':
            case 'task_completed':
                this.handleTaskStatusChange(data.task);
                break;
            case 'metrics_updated':
                this.updateMetrics(data.metrics);
                break;
            default:
                console.log('Message WebSocket non géré:', data);
        }
    }
    
    handleTaskUpdate(task) {
        const taskCard = document.querySelector(`[data-task-id=\"${task.id}\"]`);
        if (taskCard) {
            this.updateTaskCard(taskCard, task);
        }
        
        this.showNotification(`Tâche #${task.id} mise à jour`, 'info');
    }
    
    handleTaskAssignment(task, technician) {
        const taskCard = document.querySelector(`[data-task-id=\"${task.id}\"]`);
        if (taskCard) {
            this.updateTaskCard(taskCard, task);
        }
        
        this.showNotification(`Tâche #${task.id} assignée à ${technician.name}`, 'success');
    }
    
    handleTaskStatusChange(task) {
        this.moveTaskToColumn(task.id, task.status);
        this.showNotification(`Tâche #${task.id} - ${this.getStatusLabel(task.status)}`, 'info');
    }
    
    // ===== MODALES =====
    
    openAssignModal(taskId) {
        // Implémenter l'ouverture de la modal d'assignation
        console.log('Ouvrir modal assignation pour tâche:', taskId);
    }
    
    openPriorityModal(taskId, currentPriority) {
        // Implémenter l'ouverture de la modal de priorité
        console.log('Ouvrir modal priorité pour tâche:', taskId, currentPriority);
    }
    
    openTaskDetailsModal(taskId) {
        // Implémenter l'ouverture de la modal de détails
        console.log('Ouvrir modal détails pour tâche:', taskId);
    }
    
    closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }
    
    // ===== UTILITAIRES =====
    
    async apiRequest(method, url, data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification-toast ${type}`;
        
        notification.innerHTML = `
            <div class="toast-header">
                <span class="toast-title">${this.getNotificationTitle(type)}</span>
                <span class="toast-time">${new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="toast-message">${message}</div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }
    
    getNotificationTitle(type) {
        const titles = {
            success: 'Succès',
            error: 'Erreur',
            warning: 'Attention',
            info: 'Information'
        };
        return titles[type] || 'Notification';
    }
    
    getStatusLabel(status) {
        const labels = {
            pending: 'En attente',
            assigned: 'Assigné',
            'in-progress': 'En cours',
            done: 'Terminé',
            cancelled: 'Annulé'
        };
        return labels[status] || status;
    }
    
    getInitials(name) {
        if (!name) return '?';
        return name.split(' ').map(word => word[0]).join('').substr(0, 2).toUpperCase();
    }
    
    formatTaskTime(task) {
        if (task.estimated_minutes) {
            const hours = Math.floor(task.estimated_minutes / 60);
            const minutes = task.estimated_minutes % 60;
            return hours > 0 ? `${hours}h${minutes}m` : `${minutes}m`;
        }
        return '';
    }
    
    updateTaskCard(card, taskData) {
        // Mettre à jour les données de la carte
        card.dataset.priority = taskData.priority;
        card.dataset.technicianId = taskData.technician_id || '';
        
        // Mettre à jour le contenu
        const title = card.querySelector('.task-title');
        if (title) title.textContent = taskData.title;
        
        const priority = card.querySelector('.task-priority');
        if (priority) {
            priority.textContent = taskData.priority.toUpperCase();
            priority.className = `task-priority ${taskData.priority}`;
        }
        
        const technician = card.querySelector('.task-technician span');
        if (technician) technician.textContent = taskData.technician_name || 'Non assigné';
        
        const avatar = card.querySelector('.technician-avatar');
        if (avatar) avatar.textContent = this.getInitials(taskData.technician_name);
    }
    
    moveTaskToColumn(taskId, newStatus) {
        const taskCard = document.querySelector(`[data-task-id=\"${taskId}\"]`);
        const newColumn = document.querySelector(`[data-status=\"${newStatus}\"] .column-body`);
        
        if (taskCard && newColumn) {
            newColumn.appendChild(taskCard);
            this.updateColumnCounts();
        }
    }
    
    showLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="loading-spinner"></div>';
        document.querySelector('.supervisor-dashboard').appendChild(overlay);
    }
    
    hideLoadingOverlay() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    switchView(view) {
        this.currentView = view;
        
        // Mettre à jour les boutons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        
        // Charger la vue appropriée
        switch (view) {
            case 'kanban':
                this.loadKanbanView();
                break;
            case 'gantt':
                this.loadGanttView();
                break;
            case 'calendar':
                this.loadCalendarView();
                break;
        }
    }
    
    loadKanbanView() {
        // Vue Kanban déjà chargée
        console.log('Vue Kanban active');
    }
    
    loadGanttView() {
        // Implémenter la vue Gantt
        console.log('Chargement vue Gantt');
    }
    
    loadCalendarView() {
        // Implémenter la vue Calendrier
        console.log('Chargement vue Calendrier');
    }
    
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.loadDashboardData();
            }
        }, 30000); // Refresh toutes les 30 secondes
    }
    
    async refreshDashboard() {
        await this.loadDashboardData();
        this.showNotification('Dashboard actualisé', 'success');
    }
    
    adjustLayout() {
        // Ajuster la mise en page en fonction de la taille de l'écran
        const isMobile = window.innerWidth < 768;
        
        if (isMobile) {
            // Ajustements pour mobile
            document.querySelector('.kanban-board').style.gridTemplateColumns = '1fr';
        } else {
            // Ajustements pour desktop
            document.querySelector('.kanban-board').style.gridTemplateColumns = 'repeat(auto-fit, minmax(300px, 1fr))';
        }
    }
    
    logTaskMove(taskId, newStatus, technicianName) {
        console.log(`[AUDIT] Tâche ${taskId} déplacée vers ${newStatus} par ${technicianName}`);
        
        // Optionnel: envoyer au serveur pour audit
        this.apiRequest('POST', '/supervisor/audit/task-move', {
            task_id: taskId,
            new_status: newStatus,
            timestamp: new Date().toISOString()
        }).catch(error => {
            console.error('Erreur log audit:', error);
        });
    }
    
    async exportDashboardData() {
        try {
            const response = await this.apiRequest('GET', '/supervisor/export-dashboard');
            
            if (response.success) {
                // Créer un lien de téléchargement
                const blob = new Blob([response.data], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `dashboard-${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showNotification('Export terminé', 'success');
            }
        } catch (error) {
            this.showNotification('Erreur lors de l\'export: ' + error.message, 'error');
        }
    }
    
    startPolling() {
        // Fallback si WebSocket non supporté
        setInterval(() => {
            this.loadDashboardData();
        }, 10000); // Poll toutes les 10 secondes
    }
}

// Initialisation
let supervisorDashboard;

document.addEventListener('DOMContentLoaded', () => {
    supervisorDashboard = new SupervisorDashboard();
});

// Export pour utilisation externe
window.supervisorDashboard = supervisorDashboard;
