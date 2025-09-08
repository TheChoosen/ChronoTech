/**
 * Module Kanban System - ChronoTech Dashboard
 * Gestion complète du système Kanban pour les ordres de travail
 */

export class KanbanModule {
    constructor() {
        this.workOrders = [];
        this.currentFilter = { client: '', technician: '', priority: '' };
        this.draggedElement = null;
        this.initialized = false;
    }

    /**
     * Initialiser le module Kanban
     */
    async init() {
        if (this.initialized) return;
        
        console.log('🎯 Initialisation Kanban Module...');
        
        try {
            await this.loadWorkOrders();
            this.setupEventListeners();
            this.renderBoard();
            this.updateCounts();
            this.initialized = true;
            
            console.log('✅ Kanban Module initialisé avec succès');
        } catch (error) {
            console.error('❌ Erreur initialisation Kanban:', error);
        }
    }

    /**
     * Charger les ordres de travail depuis l'API
     */
    async loadWorkOrders() {
        try {
            const response = await fetch('/api/work_orders/kanban');
            
            if (response.ok) {
                const data = await response.json();
                this.workOrders = this.processApiData(data);
                console.log(`✅ ${this.workOrders.length} ordres de travail chargés`);
            } else {
                throw new Error(`API Error: ${response.status}`);
            }
        } catch (error) {
            console.warn('⚠️ API indisponible, utilisation données test');
            this.workOrders = this.generateMockData();
        }
    }

    /**
     * Traiter les données de l'API
     */
    processApiData(data) {
        // L'API peut retourner différents formats
        if (data.kanban_data) return this.flattenKanbanData(data.kanban_data);
        if (data.work_orders) return data.work_orders;
        if (Array.isArray(data)) return data;
        
        // Format objet avec statuts comme clés
        return this.flattenKanbanData(data);
    }

    /**
     * Aplatir les données Kanban groupées par statut
     */
    flattenKanbanData(kanbanData) {
        const allOrders = [];
        const statusMapping = {
            'draft': 'draft',
            'pending': 'pending', 
            'assigned': 'assigned',
            'in_progress': 'in_progress',
            'completed': 'completed',
            'cancelled': 'cancelled'
        };

        Object.entries(kanbanData).forEach(([status, orders]) => {
            if (Array.isArray(orders)) {
                orders.forEach(order => {
                    allOrders.push({
                        ...order,
                        status: statusMapping[status] || status
                    });
                });
            }
        });

        return allOrders;
    }

    /**
     * Générer des données de test
     */
    generateMockData() {
        return [
            {
                id: 1,
                claim_number: 'WO-001',
                title: 'Installation système sécurité',
                customer_name: 'Entreprise Alpha',
                description: 'Installation complète système de sécurité avec caméras et alarmes',
                status: 'pending',
                priority: 'high',
                technician_name: null,
                created_at: new Date().toISOString(),
                estimated_duration: 8
            },
            {
                id: 2,
                claim_number: 'WO-002', 
                title: 'Maintenance préventive',
                customer_name: 'Société Beta',
                description: 'Maintenance préventive annuelle des équipements',
                status: 'in_progress',
                priority: 'medium',
                technician_name: 'Jean Dupont',
                created_at: new Date(Date.now() - 86400000).toISOString(),
                estimated_duration: 4
            },
            {
                id: 3,
                claim_number: 'WO-003',
                title: 'Réparation urgente',
                customer_name: 'Client Gamma', 
                description: 'Panne majeure nécessitant intervention immédiate',
                status: 'assigned',
                priority: 'urgent',
                technician_name: 'Marie Martin',
                created_at: new Date(Date.now() - 3600000).toISOString(),
                estimated_duration: 2
            }
        ];
    }

    /**
     * Configurer les écouteurs d'événements
     */
    setupEventListeners() {
        // Écouteurs pour le drag & drop
        document.addEventListener('dragstart', this.handleDragStart.bind(this));
        document.addEventListener('dragend', this.handleDragEnd.bind(this));
        document.addEventListener('dragover', this.handleDragOver.bind(this));
        document.addEventListener('drop', this.handleDrop.bind(this));
        
        // Écouteurs pour les filtres
        const filterElements = document.querySelectorAll('[id^="kanban-filter-"]');
        filterElements.forEach(filter => {
            filter.addEventListener('change', this.applyFilters.bind(this));
        });

        // Écouteurs pour les actions
        document.addEventListener('click', this.handleCardClick.bind(this));
    }

    /**
     * Rendre le tableau Kanban
     */
    renderBoard() {
        const statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
        
        statuses.forEach(status => {
            const container = this.getColumnContainer(status);
            if (container) {
                const orders = this.getOrdersByStatus(status);
                container.innerHTML = '';
                
                orders.forEach(order => {
                    const cardElement = this.createCard(order);
                    container.appendChild(cardElement);
                });
            }
        });
    }

    /**
     * Obtenir le conteneur d'une colonne
     */
    getColumnContainer(status) {
        // Chercher dans plusieurs formats possibles d'ID
        const possibleIds = [
            `${status}-tasks`,
            `column-${status}`,
            `modal-column-${status}`,
            `kanban-${status}`
        ];
        
        for (const id of possibleIds) {
            const element = document.getElementById(id);
            if (element) return element;
        }
        
        console.warn(`⚠️ Conteneur non trouvé pour statut: ${status}`);
        return null;
    }

    /**
     * Obtenir les ordres par statut
     */
    getOrdersByStatus(status) {
        return this.workOrders.filter(order => order.status === status);
    }

    /**
     * Créer une carte Kanban
     */
    createCard(order) {
        const card = document.createElement('div');
        card.className = `kanban-card priority-${order.priority || 'medium'}`;
        card.draggable = true;
        card.dataset.orderId = order.id;
        card.dataset.currentStatus = order.status;

        const priorityColors = {
            'low': 'success',
            'medium': 'warning', 
            'high': 'orange',
            'urgent': 'danger'
        };

        const technicianInfo = order.technician_name ? 
            `<span class="text-primary">${order.technician_name}</span>` : 
            '<span class="text-muted">Non assigné</span>';

        card.innerHTML = `
            <div class="card-header">
                <div class="d-flex justify-content-between align-items-start">
                    <h6 class="card-title mb-0">#${order.claim_number}</h6>
                    <span class="badge bg-${priorityColors[order.priority] || 'info'} priority-badge">
                        ${(order.priority || 'medium').toUpperCase()}
                    </span>
                </div>
            </div>
            <div class="card-body">
                <h6 class="customer-name text-primary mb-2">${order.customer_name}</h6>
                <p class="description mb-2">${this.truncateText(order.description || order.title, 100)}</p>
                <div class="card-meta">
                    <div class="technician">${technicianInfo}</div>
                    <div class="duration text-muted">
                        <i class="fas fa-clock me-1"></i>
                        ${order.estimated_duration || '?'}h
                    </div>
                </div>
            </div>
            <div class="card-footer">
                <small class="text-muted">${this.formatDate(order.created_at)}</small>
                <div class="card-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); this.viewDetails(${order.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); this.editOrder(${order.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                </div>
            </div>
        `;

        return card;
    }

    /**
     * Tronquer le texte
     */
    truncateText(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    /**
     * Formater la date
     */
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Mettre à jour les compteurs
     */
    updateCounts() {
        const statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
        
        statuses.forEach(status => {
            const count = this.getOrdersByStatus(status).length;
            this.updateStatusCount(status, count);
        });
    }

    /**
     * Mettre à jour le compteur d'un statut
     */
    updateStatusCount(status, count) {
        const possibleIds = [
            `count-${status}`,
            `${status}-count`,
            `summary-${status}`
        ];
        
        possibleIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = count;
            }
        });
    }

    /**
     * Gérer le début du drag
     */
    handleDragStart(event) {
        if (!event.target.classList.contains('kanban-card')) return;
        
        this.draggedElement = event.target;
        event.target.classList.add('dragging');
        event.dataTransfer.setData('text/plain', event.target.dataset.orderId);
    }

    /**
     * Gérer la fin du drag
     */
    handleDragEnd(event) {
        if (event.target.classList.contains('kanban-card')) {
            event.target.classList.remove('dragging');
        }
        
        // Nettoyer les indicateurs visuels
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
        
        this.draggedElement = null;
    }

    /**
     * Gérer le survol pendant le drag
     */
    handleDragOver(event) {
        event.preventDefault();
        
        const dropZone = event.target.closest('[id*="column"], [id*="tasks"]');
        if (dropZone && !dropZone.classList.contains('drag-over')) {
            // Supprimer les anciens indicateurs
            document.querySelectorAll('.drag-over').forEach(el => {
                el.classList.remove('drag-over');
            });
            
            // Ajouter le nouvel indicateur
            dropZone.classList.add('drag-over');
        }
    }

    /**
     * Gérer le drop
     */
    async handleDrop(event) {
        event.preventDefault();
        
        const dropZone = event.target.closest('[id*="column"], [id*="tasks"]');
        const orderId = event.dataTransfer.getData('text/plain');
        
        if (dropZone && orderId && this.draggedElement) {
            const newStatus = this.extractStatusFromDropZone(dropZone);
            const oldStatus = this.draggedElement.dataset.currentStatus;
            
            if (newStatus && newStatus !== oldStatus) {
                await this.moveOrder(orderId, oldStatus, newStatus);
            }
        }
        
        // Nettoyer
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }

    /**
     * Extraire le statut depuis la zone de drop
     */
    extractStatusFromDropZone(dropZone) {
        const id = dropZone.id;
        
        // Différents formats possibles
        if (id.includes('column-')) return id.replace('column-', '').replace('modal-', '');
        if (id.includes('-tasks')) return id.replace('-tasks', '');
        if (id.includes('kanban-')) return id.replace('kanban-', '');
        
        return null;
    }

    /**
     * Déplacer un ordre de travail
     */
    async moveOrder(orderId, oldStatus, newStatus) {
        try {
            // Mise à jour optimiste de l'interface
            this.updateOrderStatus(orderId, newStatus);
            this.renderBoard();
            this.updateCounts();
            
            // Appel API
            const response = await fetch(`/api/work_orders/${orderId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ status: newStatus })
            });
            
            if (response.ok) {
                this.showNotification(`Ordre ${orderId} déplacé vers ${newStatus}`, 'success');
            } else {
                throw new Error('Échec mise à jour serveur');
            }
            
        } catch (error) {
            console.error('Erreur déplacement ordre:', error);
            
            // Rollback en cas d'erreur
            this.updateOrderStatus(orderId, oldStatus);
            this.renderBoard();
            this.updateCounts();
            
            this.showNotification('Erreur lors du déplacement', 'error');
        }
    }

    /**
     * Mettre à jour le statut d'un ordre localement
     */
    updateOrderStatus(orderId, newStatus) {
        const order = this.workOrders.find(o => o.id == orderId);
        if (order) {
            order.status = newStatus;
        }
    }

    /**
     * Obtenir le token CSRF
     */
    getCSRFToken() {
        const token = document.querySelector('[name=csrf_token]');
        return token ? token.value : '';
    }

    /**
     * Afficher une notification
     */
    showNotification(message, type = 'info') {
        if (window.NotificationSystem) {
            window.NotificationSystem.showToast(message, type);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    /**
     * Appliquer les filtres
     */
    applyFilters() {
        const clientFilter = document.getElementById('kanban-filter-client')?.value || '';
        const techFilter = document.getElementById('kanban-filter-technician')?.value || '';
        const priorityFilter = document.getElementById('kanban-filter-priority')?.value || '';
        
        this.currentFilter = {
            client: clientFilter.toLowerCase(),
            technician: techFilter.toLowerCase(),
            priority: priorityFilter.toLowerCase()
        };
        
        this.renderFilteredBoard();
    }

    /**
     * Rendre le tableau avec filtres
     */
    renderFilteredBoard() {
        const statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
        
        statuses.forEach(status => {
            const container = this.getColumnContainer(status);
            if (container) {
                const orders = this.getFilteredOrdersByStatus(status);
                container.innerHTML = '';
                
                orders.forEach(order => {
                    const cardElement = this.createCard(order);
                    container.appendChild(cardElement);
                });
            }
        });
        
        this.updateFilteredCounts();
    }

    /**
     * Obtenir les ordres filtrés par statut
     */
    getFilteredOrdersByStatus(status) {
        return this.workOrders
            .filter(order => order.status === status)
            .filter(order => this.matchesFilters(order));
    }

    /**
     * Vérifier si un ordre correspond aux filtres
     */
    matchesFilters(order) {
        const { client, technician, priority } = this.currentFilter;
        
        if (client && !order.customer_name.toLowerCase().includes(client)) {
            return false;
        }
        
        if (technician && (!order.technician_name || !order.technician_name.toLowerCase().includes(technician))) {
            return false;
        }
        
        if (priority && order.priority !== priority) {
            return false;
        }
        
        return true;
    }

    /**
     * Mettre à jour les compteurs filtrés
     */
    updateFilteredCounts() {
        const statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
        
        statuses.forEach(status => {
            const count = this.getFilteredOrdersByStatus(status).length;
            this.updateStatusCount(status, count);
        });
    }

    /**
     * Gérer le clic sur les cartes
     */
    handleCardClick(event) {
        const card = event.target.closest('.kanban-card');
        if (card && !event.target.closest('.card-actions')) {
            const orderId = card.dataset.orderId;
            this.viewOrderDetails(orderId);
        }
    }

    /**
     * Voir les détails d'un ordre
     */
    viewOrderDetails(orderId) {
        // Déléguer à la fonction globale si elle existe
        if (typeof viewWorkOrderDetails === 'function') {
            viewWorkOrderDetails(orderId);
        } else if (typeof showWorkOrderDetails === 'function') {
            showWorkOrderDetails(orderId);
        } else {
            this.showNotification(`Détails ordre #${orderId}`, 'info');
        }
    }

    /**
     * Modifier un ordre
     */
    editOrder(orderId) {
        // Déléguer à la fonction globale si elle existe
        if (typeof editWorkOrder === 'function') {
            editWorkOrder(orderId);
        } else {
            this.showNotification(`Édition ordre #${orderId}`, 'info');
        }
    }

    /**
     * Actualiser les données
     */
    async refresh() {
        console.log('🔄 Actualisation Kanban...');
        await this.loadWorkOrders();
        this.renderBoard();
        this.updateCounts();
        this.showNotification('Kanban actualisé', 'success');
    }

    /**
     * Détruire le module
     */
    destroy() {
        this.workOrders = [];
        this.currentFilter = { client: '', technician: '', priority: '' };
        this.draggedElement = null;
        this.initialized = false;
        
        // Supprimer les écouteurs d'événements
        document.removeEventListener('dragstart', this.handleDragStart);
        document.removeEventListener('dragend', this.handleDragEnd);
        document.removeEventListener('dragover', this.handleDragOver);
        document.removeEventListener('drop', this.handleDrop);
        document.removeEventListener('click', this.handleCardClick);
    }
}

// Exposer la classe globalement pour compatibilité
window.KanbanModule = KanbanModule;

// Export par défaut
export default KanbanModule;
