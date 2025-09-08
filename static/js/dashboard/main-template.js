/**
 * JavaScript pour le template dashboard main.html
 * Fonctions de compatibilité et logique spécifique au template
 */

// Bootstrap et initialisation principale
document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Initialisation du dashboard ChronoTech...');

    // Laisser app.js gérer l'initialisation principale
    if (window.chronoTechApp) {
        window.chronoTechApp.init();
    } else {
        console.log('⏰ En attente du module principal...');
    }
});

// ==================== FONCTIONS GLOBALES DE COMPATIBILITÉ ====================

// Fonctions globales de compatibilité maintenues pour onclick
window.createWorkOrder = function () {
    if (window.ChronoTechDashboard && window.ChronoTechDashboard.createWorkOrder) {
        window.ChronoTechDashboard.createWorkOrder();
    } else {
        console.log('Création d\'ordre de travail...');
    }
};

window.showWorkOrderDetails = function (id) {
    if (window.ChronoTechDashboard && window.ChronoTechDashboard.viewWorkOrderDetails) {
        window.ChronoTechDashboard.viewWorkOrderDetails(id);
    } else {
        console.log('Affichage détails ordre:', id);
    }
};

// Fallback pour fonctions qui n'existent pas encore
window.refreshStatsModal = function () {
    console.log('🔄 Actualisation des statistiques...');
};

window.exportStats = function () {
    console.log('📊 Export des statistiques...');
};

// ==================== FONCTIONS DE COMPATIBILITÉ KANBAN ====================

// Fonctions de compatibilité pour l'interface existante
window.loadKanbanDataFix = function () {
    console.log('📍 Appel de compatibilité - le module principal gère maintenant les données');
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.loadData();
    }
};

// Fonctions de compatibilité - logique déplacée vers les modules ES6
window.updateKanbanColumnsDirect = function (data) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.updateColumns(data);
    }
};

window.createKanbanCardDirect = function (workOrder) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        return window.chronoTechDashboard.kanbanManager.createCard(workOrder);
    }
    return document.createElement('div');
};

// Fonctions de compatibilité pour déplacement et mise à jour
window.moveWorkOrderToColumn = function (workOrderId, fromStatus, toStatus) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.moveCard(workOrderId, fromStatus, toStatus);
    }
};

window.updateWorkOrderCard = function (workOrderId, workOrderData) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.updateCard(workOrderId, workOrderData);
    }
};

// Fonctions de compatibilité pour les filtres
window.filterKanban = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.applyFilters();
    }
};

window.loadFilterOptions = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.loadFilterOptions();
    }
};

// Fonctions de compatibilité pour drag & drop
window.allowDrop = function (ev) {
    ev.preventDefault();
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.allowDrop(ev);
    }
};

window.handleDrop = function (ev) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.handleDrop(ev);
    }
};

window.addDragEvents = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.addDragEvents();
    }
};

window.updateKanbanCounts = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.updateCounts();
    }
};

// Fonctions de compatibilité pour les statistiques
window.syncStatsToModal = function () {
    console.log('📊 Synchronisation des statistiques via les modules ES6');
};

window.refreshStatsModal = function () {
    console.log('🔄 Actualisation des statistiques via les modules ES6');
    if (window.chronoTechDashboard) {
        window.chronoTechDashboard.refreshStats();
    }
};

window.exportStats = function () {
    console.log('📊 Export des statistiques via les modules ES6');
    if (window.chronoTechDashboard) {
        window.chronoTechDashboard.exportStats();
    }
};

// === GESTION DU KANBAN BONS DE TRAVAIL - DELEGUEE AUX MODULES ES6 ===

// Fonction de compatibilité pour le chargement des bons de travail
window.loadWorkOrdersModal = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.loadWorkOrders();
    }
};

// Fonctions de compatibilité pour la mise à jour des bons de travail
window.updateWorkOrdersModal = function (data) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.updateModal(data);
    }
};

window.updateWorkOrdersSummary = function (data) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.updateSummary(data);
    }
};

// ==================== FONCTIONS WORK ORDER KANBAN ====================

// Créer une carte bon de travail pour la modal Kanban
function createWorkOrderKanbanCard(workOrder, status) {
    const card = document.createElement('div');
    card.className = `wo-kanban-card ${workOrder.priority === 'urgent' ? 'urgent-priority' : workOrder.priority === 'high' ? 'high-priority' : ''}`;
    card.draggable = true;
    card.dataset.cardId = workOrder.id;
    card.dataset.currentStatus = status;

    const priorityColor = {
        'low': 'info',
        'medium': 'warning',
        'high': 'warning',
        'urgent': 'danger'
    };

    const priorityText = {
        'low': 'Basse',
        'medium': 'Moyenne',
        'high': 'Haute',
        'urgent': 'Urgente'
    };

    const dept = workOrder.vehicle_department || workOrder.department_name || workOrder.department || workOrder.dept || '';
    const vehicleInfo = workOrder.vehicle_make && workOrder.vehicle_model ?
        `${workOrder.vehicle_make} ${workOrder.vehicle_model}` : '';
    const vehicleDisplay = vehicleInfo && dept ? `${vehicleInfo} (${dept})` :
        vehicleInfo || dept || '';

    card.innerHTML = `
        <div class="wo-kanban-card-header">
            <h6 class="wo-kanban-card-title">#${workOrder.id}</h6>
            <span class="badge bg-${priorityColor[workOrder.priority] || 'secondary'} wo-priority-badge">
                ${priorityText[workOrder.priority] || workOrder.priority}
            </span>
        </div>
        <p class="wo-kanban-card-customer">${workOrder.customer_name}</p>
        <p class="wo-kanban-card-description">${workOrder.description || 'Aucune description'}</p>
        <div class="d-flex justify-content-between align-items-center mb-1 small text-muted">
            <span>${vehicleDisplay}</span>
        </div>
        <div class="wo-kanban-card-footer">
            <span class="wo-kanban-card-technician">${workOrder.assigned_technician_name || workOrder.technician_name || 'Non assigné'}</span>
            <span class="wo-kanban-card-date">${workOrder.scheduled_date ? new Date(workOrder.scheduled_date).toLocaleDateString('fr-FR') : 'Non planifié'}</span>
        </div>
    `;

    // Événements drag & drop
    card.addEventListener('dragstart', handleWorkOrderDragStart);
    card.addEventListener('dragend', handleWorkOrderDragEnd);

    // Événement click pour détails
    card.addEventListener('click', () => {
        showWorkOrderDetails(workOrder.id);
    });

    return card;
}

// Gérer le début du drag pour les bons de travail
function handleWorkOrderDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.dataset.cardId);
    e.dataTransfer.setData('application/json', JSON.stringify({
        cardId: e.target.dataset.cardId,
        currentStatus: e.target.dataset.currentStatus
    }));

    e.target.classList.add('dragging');

    // Marquer les zones de drop valides
    document.querySelectorAll('.wo-kanban-content').forEach(zone => {
        zone.classList.add('drop-zone-active');
    });
}

// Gérer la fin du drag pour les bons de travail
function handleWorkOrderDragEnd(e) {
    e.target.classList.remove('dragging');

    // Nettoyer les zones de drop
    document.querySelectorAll('.wo-kanban-content').forEach(zone => {
        zone.classList.remove('drop-zone-active', 'drag-over');
    });

    document.querySelectorAll('.wo-kanban-column').forEach(column => {
        column.classList.remove('drag-over');
    });
}

// Gérer le drop des bons de travail
function handleWorkOrderDrop(e) {
    e.preventDefault();

    const dropZone = e.target.closest('.wo-kanban-content');
    const column = e.target.closest('.wo-kanban-column');

    if (dropZone && column) {
        const newStatus = column.dataset.status;

        try {
            const dragData = JSON.parse(e.dataTransfer.getData('application/json'));
            const cardId = dragData.cardId;
            const oldStatus = dragData.currentStatus;

            if (newStatus !== oldStatus) {
                moveWorkOrderToModalStatus(cardId, oldStatus, newStatus);
            }
        } catch (error) {
            console.error('Erreur lors du drop:', error);
        }
    }

    // Nettoyer les styles de drag
    if (column) {
        column.classList.remove('drag-over');
    }
}

// ==================== FONCTIONS UTILITAIRES ====================

// Fonction utilitaire pour afficher des notifications toast
function showToast(message, type = 'info') {
    // Créer le toast
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        color: white;
        font-weight: 500;
        z-index: 9999;
        max-width: 300px;
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;

    // Couleurs selon le type
    switch (type) {
        case 'success':
            toast.style.background = '#28a745';
            break;
        case 'error':
            toast.style.background = '#dc3545';
            break;
        case 'warning':
            toast.style.background = '#ffc107';
            toast.style.color = '#000';
            break;
        default:
            toast.style.background = '#17a2b8';
    }

    toast.innerHTML = message;
    document.body.appendChild(toast);

    // Animation d'apparition
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);

    // Suppression automatique
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 4000);

    // Clic pour fermer
    toast.addEventListener('click', () => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    });
}

// ==================== GESTION TECHNICIENS ====================

// Fonctions de compatibilité pour la gestion des techniciens
window.loadTechniciansData = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.techniciansManager) {
        window.chronoTechDashboard.techniciansManager.loadData();
    }
};

window.updateTechnicianColumns = function (data) {
    console.log('📊 Données techniciens chargées via modules ES6');
};

window.updateTechnicianModal = function (data) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.techniciansManager) {
        window.chronoTechDashboard.techniciansManager.updateModal(data);
    }
};

window.updateTechniciansSummary = function (data) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.techniciansManager) {
        window.chronoTechDashboard.techniciansManager.updateSummary(data);
    }
};

// Fonctions de compatibilité pour les cartes techniciens
window.createTechnicianKanbanCard = function (tech, status) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.techniciansManager) {
        return window.chronoTechDashboard.techniciansManager.createKanbanCard(tech, status);
    }
};

// Fonctions de compatibilité pour les mouvements techniciens
window.moveTechnicianToStatus = function (techId, fromStatus, toStatus) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.techniciansManager) {
        window.chronoTechDashboard.techniciansManager.moveToStatus(techId, fromStatus, toStatus);
    }
};

// ==================== GESTION WORK ORDER DETAILS ====================

// Fonctions de compatibilité pour les détails work orders
window.viewWorkOrderDetails = function (workOrderId) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.viewDetails(workOrderId);
    }
};

window.closeWorkOrderDetails = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.closeDetails();
    }
};

window.saveWorkOrderDetails = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.saveDetails();
    }
};

// Fonctions de compatibilité pour actions work orders
window.editWorkOrder = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.editWorkOrder();
    }
};

window.printWorkOrder = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.printWorkOrder();
    }
};

window.exportWorkOrderPDF = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.exportToPDF();
    }
};

window.updateWorkOrderStatus = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.kanbanManager) {
        window.chronoTechDashboard.kanbanManager.updateStatus();
    }
};

// ==================== GESTION GANTT ====================

// Fonctions de compatibilité pour le Gantt
window.loadGanttData = function () {
    if (window.chronoTechDashboard && window.chronoTechDashboard.ganttManager) {
        window.chronoTechDashboard.ganttManager.loadData();
    }
};

window.generateGanttData = function (period) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.ganttManager) {
        return window.chronoTechDashboard.ganttManager.generateData(period);
    }
    return null;
};

// Actualiser le Gantt
function refreshGantt() {
    console.log('🔄 Actualisation du Gantt...');
    loadGanttData();
}

// Exporter le Gantt
function exportGantt() {
    console.log('📊 Export du Gantt...');

    // Ici on pourrait implémenter l'export en PDF ou Excel
    const period = document.getElementById('gantt-period')?.value || 'week';
    const data = generateGanttData(period);

    const exportData = {
        period: period,
        export_date: new Date().toISOString(),
        data: data
    };

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `gantt_planning_${period}_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

// ==================== FONCTIONS UTILITAIRES DELEGEES ====================

// Fonctions de compatibilité pour le rechargement des données
window.refreshDashboardData = function () {
    if (window.chronoTechDashboard) {
        window.chronoTechDashboard.refreshAllData();
    }
};

window.debugDashboardElements = function () {
    if (window.chronoTechDashboard) {
        window.chronoTechDashboard.debugElements();
    }
};

// Fonctions utilitaires délégées aux modules ES6
window.formatDateTimeLocal = function (dateString) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.utils) {
        return window.chronoTechDashboard.utils.formatDateTimeLocal(dateString);
    }
    return dateString;
};

window.formatDateTime = function (dateString) {
    if (window.chronoTechDashboard && window.chronoTechDashboard.utils) {
        return window.chronoTechDashboard.utils.formatDateTime(dateString);
    }
    return dateString;
};

// ==================== INITIALISATION SIMPLIFIÉE ====================

// Initialisation simplifiée - déléguée aux modules ES6
setTimeout(() => {
    if (window.chronoTechDashboard) {
        window.chronoTechDashboard.init();
    }
}, 500);

console.log('✅ Scripts de compatibilité dashboard main.html chargés - Le module principal prend le relais');
