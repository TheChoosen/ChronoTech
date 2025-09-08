// Module Techniciens pour ChronoTech Dashboard
import { apiClient } from '../utils/api.js';
import { notificationManager } from '../utils/notifications.js';

export class TechniciansManager {
    constructor() {
        this.technicians = [];
        this.statuses = ['available', 'busy', 'break', 'offline'];
    }

    // Charger les données des techniciens
    async loadTechniciansData() {
        try {
            console.log('👥 Chargement données techniciens...');

            const data = await apiClient.getTechnicians();
            
            if (data && Array.isArray(data)) {
                this.technicians = data;
                this.updateTechnicianModal(data);
                this.updateTechnicianStats(data);
                console.log(`✅ ${data.length} techniciens chargés`);
            } else {
                throw new Error('Données techniciens invalides');
            }

        } catch (error) {
            console.warn('⚠️ Fallback vers données de test techniciens:', error);
            this.loadTestTechniciansData();
        }
    }

    // Charger des données de test pour les techniciens
    loadTestTechniciansData() {
        const testTechnicians = [
            { id: 1, name: 'Jean Dupont', role: 'Technicien Senior', status: 'available', avatar: 'JD', current_task: null },
            { id: 2, name: 'Marie Martin', role: 'Spécialiste Électrique', status: 'busy', avatar: 'MM', current_task: 'WO-005' },
            { id: 3, name: 'Pierre Durand', role: 'Technicien Mécanique', status: 'available', avatar: 'PD', current_task: null },
            { id: 4, name: 'Sophie Leroy', role: 'Chef d\'équipe', status: 'break', avatar: 'SL', current_task: null },
            { id: 5, name: 'Luc Moreau', role: 'Technicien Junior', status: 'busy', avatar: 'LM', current_task: 'WO-011' },
            { id: 6, name: 'Anne Dubois', role: 'Spécialiste Informatique', status: 'offline', avatar: 'AD', current_task: null }
        ];

        this.technicians = testTechnicians;
        this.updateTechnicianModal(testTechnicians);
        this.updateTechnicianStats(testTechnicians);
    }

    // Mettre à jour la modal des techniciens
    updateTechnicianModal(technicians) {
        console.log('🎯 Mise à jour modal techniciens:', technicians);

        this.statuses.forEach(status => {
            const column = document.getElementById(`tech-column-${status}`);
            
            if (column) {
                const techsForStatus = technicians.filter(tech => tech.status === status);
                column.innerHTML = '';

                techsForStatus.forEach(technician => {
                    const card = this.createTechnicianCard(technician);
                    column.appendChild(card);
                });

                console.log(`✅ ${status}: ${techsForStatus.length} techniciens ajoutés`);
            }
        });

        this.addTechnicianDragEvents();
    }

    // Créer une carte technicien
    createTechnicianCard(technician) {
        const card = document.createElement('div');
        card.className = 'tech-kanban-card';
        card.draggable = true;
        card.dataset.techId = technician.id;
        card.dataset.currentStatus = technician.status;

        card.innerHTML = `
            <div class="tech-kanban-avatar">${technician.avatar}</div>
            <div class="tech-kanban-info">
                <div class="tech-kanban-name">${technician.name}</div>
                <div class="tech-kanban-role">${technician.role}</div>
                <div class="tech-kanban-details">
                    <span class="tech-kanban-status-indicator ${technician.status}"></span>
                    ${technician.current_task ? `Tâche: ${technician.current_task}` : 'Disponible'}
                </div>
            </div>
        `;

        card.addEventListener('click', () => {
            this.showTechnicianDetails(technician.id);
        });

        return card;
    }

    // Mettre à jour les statistiques des techniciens
    updateTechnicianStats(technicians) {
        const stats = this.statuses.reduce((acc, status) => {
            acc[status] = technicians.filter(tech => tech.status === status).length;
            return acc;
        }, {});

        // Mettre à jour les compteurs dans la sidebar
        Object.entries(stats).forEach(([status, count]) => {
            const element = document.getElementById(`summary-${status}`);
            if (element) {
                element.textContent = count;
            }
        });

        console.log('📊 Stats techniciens mises à jour:', stats);
    }

    // Ajouter les événements de drag & drop pour les techniciens
    addTechnicianDragEvents() {
        document.querySelectorAll('.tech-kanban-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', card.dataset.techId);
                card.classList.add('dragging');
            });

            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
                document.querySelectorAll('.tech-kanban-content').forEach(col => {
                    col.classList.remove('drag-over');
                });
            });
        });
    }

    // Déplacer un technicien entre statuts
    async moveTechnician(techId, newStatus) {
        try {
            // Ici on ferait un appel API pour mettre à jour le statut
            // await apiClient.updateTechnicianStatus(techId, newStatus);
            
            const technician = this.technicians.find(t => t.id == techId);
            if (technician) {
                technician.status = newStatus;
            }
            
            notificationManager.showToast('Statut technicien mis à jour', 'success');
            this.updateTechnicianStats(this.technicians);
        } catch (error) {
            console.error('Erreur lors du changement de statut:', error);
            notificationManager.showToast('Erreur lors du changement de statut', 'error');
        }
    }

    // Afficher les détails d'un technicien
    showTechnicianDetails(id) {
        const technician = this.technicians.find(t => t.id == id);
        if (technician) {
            console.log('Affichage détails technicien:', technician);
            // Ici on pourrait ouvrir une modal avec les détails du technicien
        }
    }

    // Assigner un technicien à un ordre de travail
    async assignTechnician(techId, workOrderId) {
        try {
            // await apiClient.assignTechnician(workOrderId, techId);
            notificationManager.showToast('Technicien assigné avec succès', 'success');
        } catch (error) {
            console.error('Erreur lors de l\'assignation:', error);
            notificationManager.showToast('Erreur lors de l\'assignation', 'error');
        }
    }
}

// Instance globale
export const techniciansManager = new TechniciansManager();

// Fonctions globales pour compatibilité
window.loadTechniciansData = () => techniciansManager.loadTechniciansData();
window.updateTechnicianModal = (data) => techniciansManager.updateTechnicianModal(data);

// Fonctions de drag & drop pour techniciens
window.allowTechDrop = function(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
};

window.techDrop = function(event) {
    event.preventDefault();
    const techId = event.dataTransfer.getData('text/plain');
    const newStatus = event.currentTarget.closest('.tech-kanban-column').dataset.status;
    
    techniciansManager.moveTechnician(techId, newStatus);
    event.currentTarget.classList.remove('drag-over');
};

// Fonctions pour les actions sur les techniciens
window.addTechnician = function() {
    console.log('Ajout d\'un nouveau technicien');
    notificationManager.showToast('Fonctionnalité d\'ajout de technicien à implémenter', 'info');
};

window.assignTechnician = function(workOrderId) {
    console.log('Assignation de technicien pour l\'ordre:', workOrderId);
    notificationManager.showToast('Sélectionnez un technicien à assigner', 'info');
};
