// Point d'entrée principal pour ChronoTech Dashboard
import { kanbanManager } from './modules/kanban_module.js';
import { techniciansManager } from './modules/technicians.js';
import { ganttManager } from './modules/gantt.js';
import { notificationManager } from './utils/notifications.js';
import { apiClient } from './utils/api.js';

// Dashboard principal ChronoTech
class ChronoTechDashboard {
    constructor() {
        this.initialized = false;
        this.modules = {
            kanban: kanbanManager,
            technicians: techniciansManager,
            gantt: ganttManager,
            notifications: notificationManager,
            api: apiClient
        };
    }

    // Initialisation centralisée
    async init() {
        if (this.initialized) return;

        console.log('🚀 Initialisation ChronoTech Dashboard v2.0...');

        // Attendre que toutes les librairies soient chargées
        if (!this.checkDependencies()) {
            console.log('⏳ Attente des dépendances...');
            setTimeout(() => this.init(), 100);
            return;
        }

        try {
            // Initialiser les modules
            await this.initializeModules();
            
            // Exposer les fonctions pour compatibilité avec l'ancien code
            this.exposeGlobalFunctions();
            
            // Configurer les événements globaux
            this.setupGlobalEvents();

            this.initialized = true;
            console.log('✅ ChronoTech Dashboard initialisé avec succès');

            // Charger les données initiales
            await this.loadInitialData();

        } catch (error) {
            console.error('❌ Erreur lors de l\'initialisation:', error);
            notificationManager.showToast('Erreur lors de l\'initialisation du dashboard', 'error');
        }
    }

    // Vérifier les dépendances
    checkDependencies() {
        const dependencies = [
            { name: 'FullCalendar', check: () => typeof FullCalendar !== 'undefined' },
            { name: 'Bootstrap', check: () => typeof bootstrap !== 'undefined' },
            { name: 'DOM', check: () => document.readyState === 'complete' || document.readyState === 'interactive' }
        ];

        return dependencies.every(dep => {
            const available = dep.check();
            if (!available) {
                console.log(`⏳ En attente de ${dep.name}...`);
            }
            return available;
        });
    }

    // Initialiser les modules
    async initializeModules() {
        console.log('🔧 Initialisation des modules...');

        // Demander permission pour les notifications
        await notificationManager.requestNotificationPermission();

        // Initialiser les gestionnaires de composants
        this.initializeComponents();

        console.log('✅ Modules initialisés');
    }

    // Initialiser les composants
    initializeComponents() {
        // Initialiser les panels s'ils existent
        if (document.getElementById('kanbanPanel')) {
            window.KanbanSystem?.init?.();
        }

        if (document.getElementById('calendarPanel')) {
            window.CalendarSystem?.init?.();
        }

        if (document.getElementById('analyticsPanel')) {
            window.AnalyticsSystem?.init?.();
        }

        // Initialiser le système de notifications global
        if (document.getElementById('notificationSystem')) {
            window.NotificationSystem = notificationManager;
        }
    }

    // Exposer les fonctions pour compatibilité
    exposeGlobalFunctions() {
        // Fonctions Kanban
        window.loadKanbanDataFix = () => this.modules.kanban.loadKanbanDataFix();
        window.updateKanbanColumnsDirect = (data) => this.modules.kanban.updateKanbanColumnsDirect(data);
        window.createKanbanCardDirect = (workOrder) => this.modules.kanban.createKanbanCardDirect(workOrder);
        window.filterKanban = () => this.modules.kanban.filterKanban();

        // Fonctions Techniciens
        window.loadTechniciansData = () => this.modules.technicians.loadTechniciansData();
        window.updateTechnicianModal = (data) => this.modules.technicians.updateTechnicianModal(data);
        window.addTechnician = () => this.modules.technicians.addTechnician?.() || console.log('Ajouter technicien');

        // Fonctions Gantt
        window.loadGanttData = () => this.modules.gantt.loadGanttData();
        window.refreshGantt = () => this.modules.gantt.refresh();
        window.exportGantt = () => this.modules.gantt.export();

        // Fonctions utilitaires
        window.createWorkOrder = () => this.createWorkOrder();
        window.viewWorkOrderDetails = (id) => this.viewWorkOrderDetails(id);
        window.editWorkOrder = (id) => this.editWorkOrder(id);

        console.log('✅ Fonctions globales exposées');
    }

    // Configurer les événements globaux
    setupGlobalEvents() {
        // Gestionnaire d'erreurs global
        window.addEventListener('error', (event) => {
            console.error('Erreur globale:', event.error);
            notificationManager.showToast('Une erreur inattendue s\'est produite', 'error');
        });

        // Gestionnaire de promesses rejetées
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Promesse rejetée:', event.reason);
            event.preventDefault();
        });

        // Rechargement périodique des données (toutes les 5 minutes)
        setInterval(() => {
            if (this.initialized) {
                this.refreshData();
            }
        }, 5 * 60 * 1000);

        console.log('✅ Événements globaux configurés');
    }

    // Charger les données initiales
    async loadInitialData() {
        console.log('📊 Chargement des données initiales...');

        const loadPromises = [];

        // Charger les données avec délais pour éviter les races conditions
        setTimeout(() => {
            loadPromises.push(this.modules.kanban.loadKanbanDataFix());
        }, 100);

        setTimeout(() => {
            loadPromises.push(this.modules.technicians.loadTechniciansData());
        }, 200);

        setTimeout(() => {
            loadPromises.push(this.modules.gantt.loadGanttData());
        }, 300);

        try {
            await Promise.allSettled(loadPromises);
            console.log('✅ Données initiales chargées');
            notificationManager.showToast('Dashboard chargé avec succès', 'success');
        } catch (error) {
            console.error('Erreur lors du chargement des données:', error);
            notificationManager.showToast('Certaines données n\'ont pas pu être chargées', 'warning');
        }
    }

    // Actualiser les données
    async refreshData() {
        console.log('🔄 Actualisation des données...');
        
        try {
            await Promise.allSettled([
                this.modules.kanban.loadKanbanDataFix(),
                this.modules.technicians.loadTechniciansData(),
                this.modules.gantt.loadGanttData()
            ]);
            
            console.log('✅ Données actualisées');
        } catch (error) {
            console.error('Erreur lors de l\'actualisation:', error);
        }
    }

    // Créer un nouvel ordre de travail
    createWorkOrder() {
        console.log('➕ Création d\'un nouvel ordre de travail');
        
        // Vérifier si une modal spécifique existe
        const createModal = document.getElementById('createWorkOrderModal');
        if (createModal) {
            const modal = new bootstrap.Modal(createModal);
            modal.show();
        } else {
            notificationManager.showToast('Modal de création à implémenter', 'info');
        }
    }

    // Voir les détails d'un ordre de travail
    viewWorkOrderDetails(id) {
        console.log('👁️ Affichage détails ordre de travail:', id);
        
        const detailsModal = document.getElementById('workOrderDetailsModal');
        if (detailsModal) {
            // Charger les données de l'ordre de travail
            this.loadWorkOrderDetails(id);
            const modal = new bootstrap.Modal(detailsModal);
            modal.show();
        } else {
            notificationManager.showToast(`Détails ordre de travail #${id}`, 'info');
        }
    }

    // Modifier un ordre de travail
    editWorkOrder(id) {
        console.log('✏️ Modification ordre de travail:', id);
        notificationManager.showToast(`Modification ordre de travail #${id}`, 'info');
    }

    // Charger les détails d'un ordre de travail
    async loadWorkOrderDetails(id) {
        try {
            const workOrder = await apiClient.request(`/work_orders/${id}`);
            this.populateWorkOrderModal(workOrder);
        } catch (error) {
            console.error('Erreur chargement détails:', error);
            notificationManager.showToast('Impossible de charger les détails', 'error');
        }
    }

    // Remplir la modal avec les détails
    populateWorkOrderModal(workOrder) {
        // Remplir les champs de la modal avec les données
        const fields = {
            'modal-wo-number': workOrder.claim_number,
            'modal-wo-customer': workOrder.customer_name,
            'modal-wo-description': workOrder.description,
            'modal-wo-technician': workOrder.technician_name,
            'modal-wo-status': workOrder.status,
            'modal-wo-priority': workOrder.priority
        };

        Object.entries(fields).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value || 'N/A';
            }
        });
    }

    // Obtenir le statut du dashboard
    getStatus() {
        return {
            initialized: this.initialized,
            modules: Object.keys(this.modules),
            version: '2.0'
        };
    }
}

// Créer l'instance globale
const dashboard = new ChronoTechDashboard();

// Exposer l'instance globalement pour compatibilité
window.ChronoTechDashboard = dashboard;

// Initialisation automatique
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 DOM Ready - Démarrage ChronoTech Dashboard');
    
    // Délai pour que tous les scripts se chargent
    setTimeout(() => {
        dashboard.init();
    }, 500);
});

// Fallback si DOMContentLoaded est déjà passé
if (document.readyState !== 'loading') {
    setTimeout(() => {
        dashboard.init();
    }, 100);
}

// Export pour utilisation comme module
export default dashboard;
