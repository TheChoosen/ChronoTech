// Module Kanban pour ChronoTech Dashboard
import { apiClient } from '../utils/api.js';
import { notificationManager } from '../utils/notifications.js';

export class KanbanManager {
    constructor() {
        this.workOrders = [];
        this.statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
    }

    // Charger les données Kanban
    async loadKanbanDataFix() {
        try {
            console.log('🔧 Chargement données Kanban...');

            const data = await apiClient.getKanbanData();
            
            if (data && (data.kanban_data || data)) {
                const kanbanData = data.kanban_data || data;
                console.log('📊 Données API reçues:', kanbanData);
                
                const totalCount = Object.values(kanbanData).reduce((total, statusArray) => {
                    return total + (Array.isArray(statusArray) ? statusArray.length : 0);
                }, 0);

                console.log(`✅ ${totalCount} bons de travail chargés depuis l'API`);
                this.updateKanbanColumnsDirect(kanbanData);
                return;
            }

            throw new Error('Données API invalides');

        } catch (error) {
            console.warn('⚠️ Fallback vers données de test:', error);
            this.loadTestData();
        }
    }

    // Charger des données de test
    loadTestData() {
        const testData = {
            draft: [
                { id: 1, claim_number: 'WO-001', customer_name: 'Entreprise Alpha', description: 'Installation système de sécurité', priority: 'medium', created_at: '2025-01-20 10:00' },
                { id: 2, claim_number: 'WO-007', customer_name: 'Société Beta', description: 'Devis pour maintenance préventive', priority: 'low', created_at: '2025-01-20 11:30' }
            ],
            pending: [
                { id: 3, claim_number: 'WO-002', customer_name: 'Client Gamma', description: 'Réparation urgente climatisation', priority: 'high', created_at: '2025-01-20 09:00' },
                { id: 4, claim_number: 'WO-003', customer_name: 'Corp Delta', description: 'Panne électrique complète', priority: 'urgent', created_at: '2025-01-20 08:00' }
            ],
            assigned: [
                { id: 6, claim_number: 'WO-004', customer_name: 'Restaurant Zeta', description: 'Maintenance équipement cuisine', priority: 'medium', technician_name: 'Jean Dupont', created_at: '2025-01-20 07:00' }
            ],
            in_progress: [
                { id: 8, claim_number: 'WO-005', customer_name: 'Bureau Theta', description: 'Migration serveur informatique', priority: 'high', technician_name: 'Marie Martin', created_at: '2025-01-20 06:00' }
            ],
            completed: [
                { id: 10, claim_number: 'WO-006', customer_name: 'Boutique Kappa', description: 'Installation éclairage LED', priority: 'low', technician_name: 'Pierre Durand', created_at: '2025-01-19 15:00' }
            ],
            cancelled: []
        };

        this.updateKanbanColumnsDirect(testData);
    }

    // Mettre à jour les colonnes Kanban
    updateKanbanColumnsDirect(data) {
        console.log('🎯 Mise à jour Kanban avec données:', data);

        this.statuses.forEach(status => {
            const column = document.getElementById(`modal-column-${status}`);
            const count = document.getElementById(`count-${status}`);

            if (column && data[status]) {
                column.innerHTML = '';

                data[status].forEach(workOrder => {
                    const card = this.createKanbanCardDirect(workOrder);
                    column.appendChild(card);
                });

                if (count) {
                    count.textContent = data[status].length;
                }

                console.log(`✅ ${status}: ${data[status].length} éléments ajoutés`);
            }
        });

        setTimeout(() => {
            this.loadFilterOptions();
            this.addDragEvents();
        }, 500);
    }

    // Créer une carte Kanban
    createKanbanCardDirect(workOrder) {
        const card = document.createElement('div');
        card.className = `kanban-card ${workOrder.priority === 'urgent' ? 'urgent-priority' : workOrder.priority === 'high' ? 'high-priority' : ''}`;
        card.draggable = true;
        card.dataset.cardId = workOrder.id;
        card.dataset.currentStatus = workOrder.status;

        const priorityColor = {
            'low': 'info',
            'medium': 'warning',
            'high': 'warning',
            'urgent': 'danger'
        };

        card.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <h6 class="card-title mb-0">#${workOrder.claim_number}</h6>
                <span class="badge bg-${priorityColor[workOrder.priority] || 'info'}">${workOrder.priority}</span>
            </div>
            <p class="text-muted small mb-2">${workOrder.customer_name}</p>
            <p class="mb-2">${workOrder.description || 'Aucune description'}</p>
            <div class="d-flex justify-content-between align-items-center mb-2">
                <small class="text-muted">${workOrder.technician_name || 'Non assigné'}</small>
                <small class="text-muted">${workOrder.created_at || ''}</small>
            </div>
            <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-primary flex-fill" onclick="event.stopPropagation(); viewWorkOrderDetails(${workOrder.id})">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation(); editWorkOrder(${workOrder.id})" title="Modifier">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
        `;

        card.addEventListener('click', () => {
            if (workOrder.id > 0 && workOrder.id < 1000) {
                this.showWorkOrderDetails(workOrder.id);
            }
        });

        return card;
    }

    // Ajouter les événements de drag & drop
    addDragEvents() {
        document.querySelectorAll('.kanban-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', card.dataset.cardId);
                card.classList.add('dragging');
            });

            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
                document.querySelectorAll('.column-content').forEach(col => {
                    col.classList.remove('drag-over');
                });
            });
        });
    }

    // Charger les options de filtres
    loadFilterOptions() {
        const clientSelect = document.getElementById('kanban-filter-client');
        const techSelect = document.getElementById('kanban-filter-tech');

        if (!clientSelect || !techSelect) return;

        const clients = new Set();
        const technicians = new Set();

        document.querySelectorAll('.kanban-card').forEach(card => {
            const customer = card.querySelector('.text-muted.small')?.textContent;
            const tech = card.querySelector('.d-flex .text-muted:first-child')?.textContent;

            if (customer) clients.add(customer);
            if (tech && tech !== 'Non assigné') technicians.add(tech);
        });

        // Remplir les filtres
        clientSelect.innerHTML = '<option value="">Tous les clients</option>';
        Array.from(clients).sort().forEach(client => {
            const option = document.createElement('option');
            option.value = client;
            option.textContent = client;
            clientSelect.appendChild(option);
        });

        techSelect.innerHTML = '<option value="">Tous les techniciens</option>';
        Array.from(technicians).sort().forEach(tech => {
            const option = document.createElement('option');
            option.value = tech;
            option.textContent = tech;
            techSelect.appendChild(option);
        });

        console.log(`✅ Filtres chargés: ${clients.size} clients, ${technicians.size} techniciens`);
    }

    // Déplacer une carte entre colonnes
    async moveCard(cardId, newStatus) {
        try {
            await apiClient.updateWorkOrderStatus(cardId, newStatus);
            
            const order = this.workOrders.find(o => o.id == cardId);
            if (order) order.status = newStatus;
            
            notificationManager.showToast('Ordre de travail déplacé', 'success');
        } catch (error) {
            console.error('Erreur lors du déplacement:', error);
            notificationManager.showToast('Erreur lors du déplacement', 'error');
        }
    }

    // Filtrer le Kanban
    filterKanban() {
        const clientFilter = document.getElementById('kanban-filter-client')?.value || '';
        const techFilter = document.getElementById('kanban-filter-tech')?.value || '';

        const allCards = document.querySelectorAll('.kanban-card');
        let visibleCount = 0;

        allCards.forEach(card => {
            const customerName = card.querySelector('.text-muted.small')?.textContent || '';
            const technicianName = card.querySelector('.d-flex .text-muted:first-child')?.textContent || '';

            let showCard = true;

            if (clientFilter && !customerName.toLowerCase().includes(clientFilter.toLowerCase())) {
                showCard = false;
            }

            if (techFilter && !technicianName.toLowerCase().includes(techFilter.toLowerCase())) {
                showCard = false;
            }

            if (showCard) {
                card.style.display = 'block';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        console.log(`✅ Filtrage terminé: ${visibleCount} cartes visibles`);
    }

    // Afficher les détails d'un ordre de travail
    showWorkOrderDetails(id) {
        if (typeof showWorkOrderDetails === 'function') {
            showWorkOrderDetails(id);
        } else {
            console.log(`Affichage détails ordre de travail ${id}`);
        }
    }
}

// Instance globale
export const kanbanManager = new KanbanManager();

// Fonctions globales pour compatibilité
window.loadKanbanDataFix = () => kanbanManager.loadKanbanDataFix();
window.updateKanbanColumnsDirect = (data) => kanbanManager.updateKanbanColumnsDirect(data);
window.createKanbanCardDirect = (workOrder) => kanbanManager.createKanbanCardDirect(workOrder);
window.filterKanban = () => kanbanManager.filterKanban();

// Fonctions de drag & drop globales
window.allowDrop = function(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
};

window.drop = function(event) {
    event.preventDefault();
    const cardId = event.dataTransfer.getData('text/plain');
    const newStatus = event.currentTarget.closest('.kanban-column').dataset.status;
    
    kanbanManager.moveCard(cardId, newStatus);
    event.currentTarget.classList.remove('drag-over');
};
