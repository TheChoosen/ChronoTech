/**
 * ChronoTech - Système de Notifications Contextuelles IA
 * Notifications pour Kanban et Gantt (Sprint 1 requirement)
 */

class AINotificationSystem {
    constructor() {
        this.notifications = new Map();
        this.activeContexts = new Set();
        this.pollingInterval = null;
        this.updateFrequency = 30000; // 30 secondes
        
        this.init();
    }

    init() {
        this.setupNotificationContainer();
        this.startPolling();
        this.bindEvents();
    }

    setupNotificationContainer() {
        // Créer le conteneur de notifications s'il n'existe pas
        if (!document.getElementById('ai-notifications-container')) {
            const container = document.createElement('div');
            container.id = 'ai-notifications-container';
            container.className = 'ai-notifications-container position-fixed';
            container.style.cssText = `
                top: 80px;
                right: 20px;
                z-index: 1050;
                max-width: 400px;
                pointer-events: none;
            `;
            document.body.appendChild(container);
        }
    }

    bindEvents() {
        // Écouter les changements de contexte (Kanban, Gantt)
        document.addEventListener('contextChange', (e) => {
            this.handleContextChange(e.detail.context);
        });

        // Écouter les ouvertures de modales Kanban/Gantt
        const kanbanModal = document.getElementById('workOrdersKanbanModal');
        const ganttModal = document.getElementById('ganttModal');

        if (kanbanModal) {
            kanbanModal.addEventListener('shown.bs.modal', () => {
                this.activateContext('kanban');
            });
            kanbanModal.addEventListener('hidden.bs.modal', () => {
                this.deactivateContext('kanban');
            });
        }

        if (ganttModal) {
            ganttModal.addEventListener('shown.bs.modal', () => {
                this.activateContext('gantt');
            });
            ganttModal.addEventListener('hidden.bs.modal', () => {
                this.deactivateContext('gantt');
            });
        }
    }

    activateContext(context) {
        this.activeContexts.add(context);
        console.log(`🎯 Contexte IA activé: ${context}`);
        
        // Récupérer immédiatement les notifications pour ce contexte
        this.fetchContextualNotifications(context);
    }

    deactivateContext(context) {
        this.activeContexts.delete(context);
        
        // Nettoyer les notifications du contexte désactivé
        this.clearContextNotifications(context);
    }

    handleContextChange(context) {
        // Gérer les changements de contexte dynamiques
        this.activateContext(context);
    }

    startPolling() {
        // Arrêter le polling existant
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        // Démarrer le polling pour les mises à jour
        this.pollingInterval = setInterval(() => {
            this.updateNotifications();
        }, this.updateFrequency);

        // Première récupération immédiate
        this.updateNotifications();
    }

    async updateNotifications() {
        try {
            // Récupérer les suggestions globales
            const suggestionsResponse = await fetch('/ai/suggestions?context=dashboard&limit=5');
            const suggestionsData = await suggestionsResponse.json();

            if (suggestionsData.success) {
                this.processSuggestions(suggestionsData.suggestions);
            }

            // Récupérer les notifications contextuelles pour chaque contexte actif
            for (const context of this.activeContexts) {
                await this.fetchContextualNotifications(context);
            }

        } catch (error) {
            console.error('Erreur mise à jour notifications IA:', error);
        }
    }

    async fetchContextualNotifications(context) {
        try {
            const response = await fetch(`/ai/notifications/contextual?context=${context}&severity=all`);
            const data = await response.json();

            if (data.success) {
                this.processContextualNotifications(data.notifications, context);
            }

        } catch (error) {
            console.error(`Erreur notifications contextuelles ${context}:`, error);
        }
    }

    processSuggestions(suggestions) {
        suggestions.forEach(suggestion => {
            this.showNotification({
                id: `suggestion_${suggestion.type}_${Date.now()}`,
                type: 'ai_suggestion',
                title: suggestion.title,
                message: suggestion.message,
                severity: suggestion.severity,
                context: suggestion.context,
                actions: suggestion.action_suggestions || [],
                data: suggestion,
                duration: this.getDurationBySeverity(suggestion.severity)
            });
        });
    }

    processContextualNotifications(notifications, context) {
        notifications.forEach(notification => {
            this.showNotification({
                ...notification,
                context: context,
                duration: this.getDurationBySeverity(notification.severity)
            });
        });
    }

    showNotification(notification) {
        const container = document.getElementById('ai-notifications-container');
        if (!container) return;

        // Éviter les doublons
        if (this.notifications.has(notification.id)) {
            return;
        }

        // Créer l'élément de notification
        const notificationElement = this.createNotificationElement(notification);
        
        container.appendChild(notificationElement);
        this.notifications.set(notification.id, notification);

        // Animation d'entrée
        setTimeout(() => {
            notificationElement.classList.add('show');
        }, 100);

        // Auto-suppression si durée définie
        if (notification.duration && notification.duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification.id);
            }, notification.duration);
        }

        // Mettre à jour les badges de notification
        this.updateNotificationBadges();
    }

    createNotificationElement(notification) {
        const element = document.createElement('div');
        element.className = `ai-notification ai-notification-${notification.severity} mb-3`;
        element.id = `notification-${notification.id}`;
        element.style.cssText = `
            pointer-events: auto;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;

        const icon = this.getNotificationIcon(notification.type, notification.severity);
        const bgColor = this.getNotificationBgColor(notification.severity);

        element.innerHTML = `
            <div class="card ${bgColor} border-0 shadow-sm">
                <div class="card-body p-3">
                    <div class="d-flex align-items-start">
                        <div class="me-3">
                            <i class="${icon} fa-lg"></i>
                        </div>
                        <div class="flex-grow-1">
                            <h6 class="card-title mb-1 fw-bold">${notification.title}</h6>
                            <p class="card-text mb-2 small">${notification.message}</p>
                            
                            ${notification.actions && notification.actions.length > 0 ? `
                                <div class="notification-actions">
                                    ${notification.actions.slice(0, 2).map(action => `
                                        <button class="btn btn-sm btn-outline-primary me-1 mb-1 notification-action" 
                                                data-action="${this.sanitizeAction(action)}"
                                                data-notification-id="${notification.id}">
                                            ${action}
                                        </button>
                                    `).join('')}
                                </div>
                            ` : ''}
                            
                            <div class="d-flex justify-content-between align-items-center mt-2">
                                <small class="text-muted">
                                    <i class="fa-solid fa-robot me-1"></i>IA • ${notification.context || 'Général'}
                                </small>
                                <button class="btn btn-sm btn-outline-secondary notification-dismiss" 
                                        data-notification-id="${notification.id}">
                                    <i class="fa-solid fa-times"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Ajouter les événements
        this.bindNotificationEvents(element, notification);

        return element;
    }

    bindNotificationEvents(element, notification) {
        // Bouton de fermeture
        const dismissBtn = element.querySelector('.notification-dismiss');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => {
                this.removeNotification(notification.id);
            });
        }

        // Boutons d'action
        element.querySelectorAll('.notification-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.handleNotificationAction(notification, action);
            });
        });

        // Clic sur la notification
        element.addEventListener('click', (e) => {
            if (!e.target.closest('.notification-action') && !e.target.closest('.notification-dismiss')) {
                this.handleNotificationClick(notification);
            }
        });
    }

    handleNotificationAction(notification, action) {
        console.log(`🤖 Action IA: ${action} pour notification ${notification.id}`);

        switch (action) {
            case 'Réassigner les tâches non-urgentes':
            case 'reassign_tasks':
                this.handleTaskReassignment(notification);
                break;
            
            case 'Voir les alternatives':
            case 'view_suggestions':
                this.showAlternativeSuggestions(notification);
                break;
            
            case 'Assigner automatiquement':
            case 'auto_assign':
                this.handleAutoAssignment(notification);
                break;
            
            case 'prepare_resources':
                this.showResourcePreparation(notification);
                break;
            
            default:
                this.showGenericActionModal(notification, action);
        }

        // Marquer la notification comme traitée
        this.markNotificationAsHandled(notification.id);
    }

    async handleTaskReassignment(notification) {
        try {
            const modal = this.createActionModal('Réassignation de Tâches IA', `
                <div class="mb-3">
                    <h6>Tâches suggérées pour réassignation:</h6>
                    <div id="reassignment-suggestions">
                        <div class="text-center">
                            <i class="fa-solid fa-spinner fa-spin me-2"></i>
                            Analyse en cours...
                        </div>
                    </div>
                </div>
            `);

            // Récupérer les suggestions de réassignation
            if (notification.data && notification.data.technician_id) {
                const response = await fetch('/api/copilot/suggest_reassignment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        technician_id: notification.data.technician_id 
                    })
                });

                const data = await response.json();
                if (data.success) {
                    this.displayReassignmentSuggestions(data.suggestions);
                }
            }

        } catch (error) {
            console.error('Erreur réassignation:', error);
            showToast('Erreur lors de la réassignation', 'error');
        }
    }

    async handleAutoAssignment(notification) {
        if (!notification.data || !notification.data.task_id) {
            showToast('Données de tâche manquantes', 'error');
            return;
        }

        try {
            const response = await fetch('/ai/technician/best_match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: notification.data.task_id,
                    priority: notification.data.priority || 'medium'
                })
            });

            const data = await response.json();
            if (data.success && data.recommendation) {
                // Confirmer l'assignation
                const confirmed = confirm(
                    `Assigner la tâche à ${data.recommendation.technician_name}?\n` +
                    `Confiance: ${(data.recommendation.confidence * 100).toFixed(1)}%`
                );

                if (confirmed) {
                    await this.executeTaskAssignment(notification.data.task_id, data.recommendation.technician_id);
                    showToast(`Tâche assignée à ${data.recommendation.technician_name}`, 'success');
                    this.removeNotification(notification.id);
                }
            }

        } catch (error) {
            console.error('Erreur assignation automatique:', error);
            showToast('Erreur lors de l\'assignation automatique', 'error');
        }
    }

    async executeTaskAssignment(taskId, technicianId) {
        // Utiliser l'API existante pour assigner la tâche
        const response = await fetch(`/api/work_orders/${taskId}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ technician_id: technicianId })
        });

        return response.json();
    }

    handleNotificationClick(notification) {
        console.log(`🔍 Clic sur notification IA: ${notification.type}`);
        
        // Actions selon le type de notification
        switch (notification.type) {
            case 'technician_overload':
                this.showTechnicianWorkloadDetails(notification);
                break;
            case 'assignment_optimization':
                this.showAssignmentOptimizationDetails(notification);
                break;
            case 'prediction_alert':
                this.showPredictionDetails(notification);
                break;
            default:
                this.showNotificationDetails(notification);
        }
    }

    removeNotification(notificationId) {
        const element = document.getElementById(`notification-${notificationId}`);
        if (element) {
            element.style.opacity = '0';
            element.style.transform = 'translateX(100%)';
            
            setTimeout(() => {
                element.remove();
                this.notifications.delete(notificationId);
                this.updateNotificationBadges();
            }, 300);
        }
    }

    clearContextNotifications(context) {
        this.notifications.forEach((notification, id) => {
            if (notification.context === context) {
                this.removeNotification(id);
            }
        });
    }

    updateNotificationBadges() {
        const count = this.notifications.size;
        
        // Mettre à jour le badge général
        const badge = document.getElementById('ai-notification-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }

        // Mettre à jour les badges contextuels
        this.updateContextBadges();
    }

    updateContextBadges() {
        const kanbanBadge = document.getElementById('kanban-ai-badge');
        const ganttBadge = document.getElementById('gantt-ai-badge');

        let kanbanCount = 0;
        let ganttCount = 0;

        this.notifications.forEach(notification => {
            if (notification.context === 'kanban') kanbanCount++;
            if (notification.context === 'gantt') ganttCount++;
        });

        if (kanbanBadge) {
            kanbanBadge.textContent = kanbanCount;
            kanbanBadge.style.display = kanbanCount > 0 ? 'inline' : 'none';
        }

        if (ganttBadge) {
            ganttBadge.textContent = ganttCount;
            ganttBadge.style.display = ganttCount > 0 ? 'inline' : 'none';
        }
    }

    // Utilitaires
    getNotificationIcon(type, severity) {
        const icons = {
            'technician_overload': 'fa-solid fa-exclamation-triangle text-warning',
            'assignment_optimization': 'fa-solid fa-lightbulb text-info',
            'prediction_alert': 'fa-solid fa-chart-line text-primary',
            'ai_suggestion': 'fa-solid fa-robot text-success'
        };

        return icons[type] || 'fa-solid fa-info-circle text-info';
    }

    getNotificationBgColor(severity) {
        const colors = {
            'high': 'bg-danger-subtle border-danger',
            'medium': 'bg-warning-subtle border-warning',
            'low': 'bg-info-subtle border-info'
        };

        return colors[severity] || 'bg-light border-secondary';
    }

    getDurationBySeverity(severity) {
        const durations = {
            'high': 0, // Persistent
            'medium': 15000, // 15 secondes
            'low': 10000 // 10 secondes
        };

        return durations[severity] || 12000;
    }

    sanitizeAction(action) {
        return action.toLowerCase().replace(/[^a-z0-9]/g, '_');
    }

    markNotificationAsHandled(notificationId) {
        const notification = this.notifications.get(notificationId);
        if (notification) {
            notification.handled = true;
            // Optionnel: envoyer à l'API que la notification a été traitée
        }
    }

    createActionModal(title, content) {
        const modalHtml = `
            <div class="modal fade" id="aiActionModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fa-solid fa-robot me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Supprimer la modal existante si présente
        const existingModal = document.getElementById('aiActionModal');
        if (existingModal) {
            existingModal.remove();
        }

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('aiActionModal'));
        modal.show();

        return modal;
    }

    // Méthodes pour affichage des détails
    showTechnicianWorkloadDetails(notification) {
        this.createActionModal('Détails Surcharge Technicien', `
            <div class="alert alert-warning">
                <h6>Technicien en surcharge détecté</h6>
                <p>${notification.message}</p>
            </div>
            <div class="mb-3">
                <strong>Actions recommandées:</strong>
                <ul>
                    ${notification.actions ? notification.actions.map(action => `<li>${action}</li>`).join('') : ''}
                </ul>
            </div>
        `);
    }

    showAssignmentOptimizationDetails(notification) {
        this.createActionModal('Optimisation d\'Assignation', `
            <div class="alert alert-info">
                <h6>Opportunité d'optimisation</h6>
                <p>${notification.message}</p>
            </div>
            <p>L'IA a identifié des possibilités d'amélioration dans l'assignation des tâches.</p>
        `);
    }

    showPredictionDetails(notification) {
        this.createActionModal('Alerte Prédictive', `
            <div class="alert alert-primary">
                <h6>Prévision IA</h6>
                <p>${notification.message}</p>
            </div>
            <p>Cette prévision est basée sur l'analyse des données historiques et des tendances actuelles.</p>
        `);
    }

    destroy() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        this.notifications.clear();
        this.activeContexts.clear();
        
        const container = document.getElementById('ai-notifications-container');
        if (container) {
            container.remove();
        }
    }
}

// Instance globale
let aiNotificationSystem;

// Initialiser au chargement du DOM
document.addEventListener('DOMContentLoaded', function() {
    aiNotificationSystem = new AINotificationSystem();
    
    // Ajouter des badges IA aux interfaces existantes
    addAIBadgesToInterface();
});

function addAIBadgesToInterface() {
    // Badge général dans la navigation
    const navNotifications = document.querySelector('[data-bs-target="#notificationsModal"]');
    if (navNotifications && !document.getElementById('ai-notification-badge')) {
        navNotifications.insertAdjacentHTML('afterend', `
            <span id="ai-notification-badge" class="badge bg-primary ms-1" style="display: none;">0</span>
        `);
    }

    // Badge pour Kanban
    const kanbanBtn = document.querySelector('[data-bs-target="#workOrdersKanbanModal"]');
    if (kanbanBtn && !document.getElementById('kanban-ai-badge')) {
        kanbanBtn.insertAdjacentHTML('beforeend', `
            <span id="kanban-ai-badge" class="badge bg-warning ms-1" style="display: none;">0</span>
        `);
    }

    // Badge pour Gantt (si existe)
    const ganttBtn = document.querySelector('[data-bs-target="#ganttModal"]');
    if (ganttBtn && !document.getElementById('gantt-ai-badge')) {
        ganttBtn.insertAdjacentHTML('beforeend', `
            <span id="gantt-ai-badge" class="badge bg-info ms-1" style="display: none;">0</span>
        `);
    }
}

// CSS pour les notifications
const notificationStyles = `
    .ai-notification {
        max-width: 400px;
        margin-bottom: 0.75rem;
    }
    
    .ai-notification.show {
        opacity: 1 !important;
        transform: translateX(0) !important;
    }
    
    .ai-notification .card {
        border-left: 4px solid;
    }
    
    .ai-notification-high .card {
        border-left-color: var(--bs-danger) !important;
    }
    
    .ai-notification-medium .card {
        border-left-color: var(--bs-warning) !important;
    }
    
    .ai-notification-low .card {
        border-left-color: var(--bs-info) !important;
    }
    
    .notification-actions .btn {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
    }
    
    .ai-notifications-container {
        pointer-events: none;
    }
    
    .ai-notification {
        pointer-events: auto;
    }
`;

// Injecter les styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);
