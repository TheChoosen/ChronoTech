/**
 * ChronoTech Copilote IA - Interface JavaScript
 * Gère l'affichage des insights et recommandations
 */

class CopilotAI {
    constructor() {
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.refreshRate = 30000; // 30 secondes
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInsights();
        this.startAutoRefresh();
    }

    bindEvents() {
        // Bouton d'actualisation
        document.getElementById('refresh-copilot')?.addEventListener('click', () => {
            this.loadInsights(true);
        });

        // Optimisation automatique
        document.getElementById('auto-optimize')?.addEventListener('click', () => {
            this.executeAutoOptimization();
        });

        // Bouton paramètres
        document.getElementById('copilot-settings')?.addEventListener('click', () => {
            this.showSettings();
        });
    }

    async loadInsights(forceRefresh = false) {
        const loadingEl = document.getElementById('copilot-loading');
        const insightsEl = document.getElementById('copilot-insights');
        
        if (forceRefresh) {
            this.showLoading();
        }

        try {
            const response = await fetch('/api/copilot/insights', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                this.displayInsights(data.insights);
                this.updateLastAnalysisTime(data.timestamp);
            } else {
                this.showError(data.error);
            }

        } catch (error) {
            console.error('Erreur lors du chargement des insights:', error);
            this.showError('Erreur de connexion au service IA');
        }
    }

    displayInsights(insights) {
        this.hideLoading();
        
        const alertsContainer = document.getElementById('copilot-alerts');
        const recommendationsContainer = document.getElementById('copilot-recommendations');
        const emptyState = document.getElementById('copilot-empty');
        const actionsContainer = document.getElementById('copilot-actions');
        
        // Réinitialiser l'affichage
        alertsContainer.classList.add('d-none');
        recommendationsContainer.classList.add('d-none');
        emptyState.classList.add('d-none');
        actionsContainer.classList.add('d-none');

        let hasAlerts = false;
        let hasRecommendations = false;

        // Afficher les anomalies de charge
        if (insights.workload_anomalies && insights.workload_anomalies.length > 0) {
            this.displayWorkloadAnomalies(insights.workload_anomalies);
            hasAlerts = true;
        }

        // Afficher les recommandations
        if (insights.recommendations && insights.recommendations.length > 0) {
            this.displayRecommendations(insights.recommendations);
            hasRecommendations = true;
        }

        // Mettre à jour le compteur
        const totalInsights = (insights.workload_anomalies?.length || 0) + 
                             (insights.recommendations?.length || 0);
        document.getElementById('insights-count').textContent = totalInsights;

        // Afficher l'état approprié
        if (hasAlerts || hasRecommendations) {
            actionsContainer.classList.remove('d-none');
        } else {
            emptyState.classList.remove('d-none');
        }
    }

    displayWorkloadAnomalies(anomalies) {
        const alertsContainer = document.getElementById('copilot-alerts');
        const alertsList = document.getElementById('alerts-list');
        
        alertsList.innerHTML = '';
        
        anomalies.forEach(anomaly => {
            const alertElement = this.createAlertElement(anomaly);
            alertsList.appendChild(alertElement);
        });
        
        alertsContainer.classList.remove('d-none');
    }

    createAlertElement(anomaly) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${this.getSeverityColor(anomaly.severity)} alert-dismissible fade show mb-2`;
        
        alertDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${anomaly.technician_name}</strong>
                    <p class="mb-1">${anomaly.message}</p>
                    <small class="text-muted">${anomaly.suggestion}</small>
                </div>
                <div class="ms-2">
                    ${anomaly.action ? this.createActionButton(anomaly) : ''}
                </div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        return alertDiv;
    }

    createActionButton(anomaly) {
        if (anomaly.action === 'reassign_tasks') {
            return `
                <button class="btn btn-sm btn-outline-primary" 
                        onclick="copilotAI.suggestReassignment(${anomaly.technician_id})"
                        title="Suggérer des réassignations">
                    <i class="fa-solid fa-exchange-alt me-1"></i>Réassigner
                </button>
            `;
        }
        return '';
    }

    displayRecommendations(recommendations) {
        const recommendationsContainer = document.getElementById('copilot-recommendations');
        const recommendationsList = document.getElementById('recommendations-list');
        
        recommendationsList.innerHTML = '';
        
        recommendations.forEach(rec => {
            const recElement = this.createRecommendationElement(rec);
            recommendationsList.appendChild(recElement);
        });
        
        recommendationsContainer.classList.remove('d-none');
    }

    createRecommendationElement(recommendation) {
        const recDiv = document.createElement('div');
        recDiv.className = 'border rounded p-2 mb-2 bg-light';
        
        recDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <i class="fa-solid fa-lightbulb text-warning me-2"></i>
                    <span>${recommendation.message}</span>
                </div>
                <span class="badge bg-${this.getPriorityColor(recommendation.priority)}">
                    ${recommendation.priority}
                </span>
            </div>
        `;
        
        return recDiv;
    }

    async suggestReassignment(technicianId) {
        try {
            const response = await fetch('/api/copilot/suggest_reassignment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    technician_id: technicianId
                })
            });

            const data = await response.json();

            if (data.success && data.suggestions.length > 0) {
                this.showReassignmentModal(data.suggestions);
            } else {
                showToast('Aucune réassignation possible pour le moment', 'info');
            }

        } catch (error) {
            console.error('Erreur lors de la suggestion de réassignation:', error);
            showToast('Erreur lors de la suggestion de réassignation', 'error');
        }
    }

    showReassignmentModal(suggestions) {
        // Créer et afficher une modal avec les suggestions
        const modalHtml = `
            <div class="modal fade" id="reassignmentModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fa-solid fa-exchange-alt me-2"></i>Suggestions de réassignation
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${suggestions.map(suggestion => `
                                <div class="card mb-2">
                                    <div class="card-body p-3">
                                        <h6>${suggestion.task_name}</h6>
                                        <p class="mb-2">
                                            <strong>Recommandation:</strong> Réassigner à 
                                            <span class="text-primary">${suggestion.suggested_tech_name}</span>
                                        </p>
                                        <small class="text-muted">${suggestion.reason}</small>
                                        <div class="mt-2">
                                            <button class="btn btn-sm btn-success" 
                                                    onclick="copilotAI.executeReassignment(${suggestion.task_id}, ${suggestion.suggested_tech_id})">
                                                <i class="fa-solid fa-check me-1"></i>Appliquer
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fermer</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Ajouter la modal au DOM
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Afficher la modal
        const modal = new bootstrap.Modal(document.getElementById('reassignmentModal'));
        modal.show();
        
        // Nettoyer après fermeture
        document.getElementById('reassignmentModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }

    async executeReassignment(taskId, newTechId) {
        try {
            const response = await fetch('/api/copilot/execute_suggestion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: 'reassign_task',
                    task_id: taskId,
                    new_technician_id: newTechId
                })
            });

            const data = await response.json();

            if (data.success) {
                showToast('Tâche réassignée avec succès', 'success');
                
                // Fermer la modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('reassignmentModal'));
                modal.hide();
                
                // Actualiser les insights
                setTimeout(() => {
                    this.loadInsights(true);
                    // Actualiser le Kanban si disponible
                    if (window.ChronoTechDashboard && window.ChronoTechDashboard.loadKanbanDataFix) {
                        window.ChronoTechDashboard.loadKanbanDataFix();
                    }
                }, 1000);
                
            } else {
                showToast('Erreur lors de la réassignation: ' + data.error, 'error');
            }

        } catch (error) {
            console.error('Erreur lors de l\'exécution de la réassignation:', error);
            showToast('Erreur lors de la réassignation', 'error');
        }
    }

    async executeAutoOptimization() {
        // Afficher un loader sur le bouton
        const button = document.getElementById('auto-optimize');
        const originalHtml = button.innerHTML;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Optimisation...';
        button.disabled = true;

        try {
            // Récupérer les insights actuels
            const insights = await this.getInsights();
            
            let optimizationCount = 0;
            
            // Traiter automatiquement les recommandations prioritaires
            if (insights.recommendations) {
                for (const rec of insights.recommendations) {
                    if (rec.priority === 'high' && rec.type === 'redistribute') {
                        // Exécuter la redistribution automatique
                        await this.executeAutoReassignment(rec.technician_id);
                        optimizationCount++;
                    }
                }
            }
            
            if (optimizationCount > 0) {
                showToast(`${optimizationCount} optimisation(s) appliquée(s)`, 'success');
                setTimeout(() => this.loadInsights(true), 2000);
            } else {
                showToast('Aucune optimisation automatique disponible', 'info');
            }

        } catch (error) {
            console.error('Erreur lors de l\'optimisation automatique:', error);
            showToast('Erreur lors de l\'optimisation automatique', 'error');
        } finally {
            // Restaurer le bouton
            button.innerHTML = originalHtml;
            button.disabled = false;
        }
    }

    async getInsights() {
        const response = await fetch('/api/copilot/insights');
        const data = await response.json();
        return data.success ? data.insights : {};
    }

    showLoading() {
        document.getElementById('copilot-loading')?.classList.remove('d-none');
        document.getElementById('copilot-alerts')?.classList.add('d-none');
        document.getElementById('copilot-recommendations')?.classList.add('d-none');
        document.getElementById('copilot-empty')?.classList.add('d-none');
    }

    hideLoading() {
        document.getElementById('copilot-loading')?.classList.add('d-none');
    }

    showError(message) {
        this.hideLoading();
        const insightsEl = document.getElementById('copilot-insights');
        insightsEl.innerHTML = `
            <div class="alert alert-danger">
                <i class="fa-solid fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }

    updateLastAnalysisTime(timestamp) {
        const timeEl = document.getElementById('last-analysis-time');
        if (timeEl) {
            const date = new Date(timestamp);
            timeEl.textContent = date.toLocaleTimeString();
        }
    }

    getSeverityColor(severity) {
        const colors = {
            'critical': 'danger',
            'high': 'warning',
            'warning': 'warning',
            'medium': 'info',
            'info': 'info',
            'low': 'secondary'
        };
        return colors[severity] || 'secondary';
    }

    getPriorityColor(priority) {
        const colors = {
            'high': 'danger',
            'medium': 'warning',
            'low': 'success'
        };
        return colors[priority] || 'secondary';
    }

    startAutoRefresh() {
        if (this.autoRefreshEnabled) {
            this.refreshInterval = setInterval(() => {
                this.loadInsights();
            }, this.refreshRate);
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showSettings() {
        // Afficher les paramètres du copilote
        showToast('Paramètres du copilote - À implémenter', 'info');
    }

    destroy() {
        this.stopAutoRefresh();
    }
}

// Instance globale
let copilotAI;

// Initialiser quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('copilot-widget')) {
        copilotAI = new CopilotAI();
    }
});

// Nettoyer à la fermeture de la page
window.addEventListener('beforeunload', function() {
    if (copilotAI) {
        copilotAI.destroy();
    }
});
