/**
 * ChronoTech Customer 360 - Vue complète client
 * Interface pour afficher toutes les données d'un client
 */

class Customer360Widget {
    constructor() {
        this.currentCustomerId = null;
        this.currentCustomerData = null;
        this.searchTimeout = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupSearchAutocomplete();
    }

    bindEvents() {
        // Bouton d'actualisation
        document.getElementById('refresh-customer360')?.addEventListener('click', () => {
            if (this.currentCustomerId) {
                this.loadCustomer(this.currentCustomerId, true);
            }
        });

        // Recherche de client
        const searchInput = document.getElementById('customer360-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.handleSearchInput(e.target.value);
            });

            searchInput.addEventListener('focus', () => {
                if (searchInput.value.length >= 2) {
                    this.showSearchResults();
                }
            });

            // Fermer les résultats si on clique ailleurs
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.customer-search-container')) {
                    this.hideSearchResults();
                }
            });
        }
    }

    setupSearchAutocomplete() {
        const searchInput = document.getElementById('customer360-search');
        const resultsContainer = document.getElementById('customer-search-results');

        if (!searchInput || !resultsContainer) return;

        // Gérer les touches du clavier
        searchInput.addEventListener('keydown', (e) => {
            const results = resultsContainer.querySelectorAll('.customer-search-result');
            const selected = resultsContainer.querySelector('.customer-search-result.selected');

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.selectNextResult(results, selected);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.selectPreviousResult(results, selected);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (selected) {
                        this.selectCustomer(selected.dataset.customerId);
                    }
                    break;
                case 'Escape':
                    this.hideSearchResults();
                    break;
            }
        });
    }

    handleSearchInput(query) {
        clearTimeout(this.searchTimeout);

        if (query.length < 2) {
            this.hideSearchResults();
            return;
        }

        // Délai pour éviter trop de requêtes
        this.searchTimeout = setTimeout(() => {
            this.searchCustomers(query);
        }, 300);
    }

    async searchCustomers(query) {
        try {
            const response = await fetch(`/api/customer360/customers/search?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.success) {
                this.displaySearchResults(data.customers);
            } else {
                console.error('Erreur lors de la recherche:', data.error);
            }
        } catch (error) {
            console.error('Erreur lors de la recherche de clients:', error);
        }
    }

    displaySearchResults(customers) {
        const resultsContainer = document.getElementById('customer-search-results');
        
        if (customers.length === 0) {
            resultsContainer.innerHTML = '<div class="p-3 text-muted text-center">Aucun client trouvé</div>';
        } else {
            resultsContainer.innerHTML = customers.map(customer => `
                <div class="customer-search-result" data-customer-id="${customer.id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <div class="fw-semibold">${customer.name}</div>
                            <small class="text-muted">
                                ${customer.email ? customer.email + ' • ' : ''}
                                ${customer.phone ? customer.phone + ' • ' : ''}
                                ${customer.city || ''}
                            </small>
                        </div>
                        <div class="text-end">
                            <span class="badge bg-${this.getCustomerTypeBadge(customer.customer_type)} mb-1">
                                ${this.getCustomerTypeLabel(customer.customer_type)}
                            </span>
                            <br>
                            <small class="text-muted">${customer.intervention_count || 0} intervention(s)</small>
                        </div>
                    </div>
                </div>
            `).join('');

            // Ajouter les événements de clic
            resultsContainer.querySelectorAll('.customer-search-result').forEach(item => {
                item.addEventListener('click', () => {
                    this.selectCustomer(item.dataset.customerId);
                });
            });
        }

        this.showSearchResults();
    }

    selectNextResult(results, current) {
        if (results.length === 0) return;

        if (!current) {
            results[0].classList.add('selected');
        } else {
            current.classList.remove('selected');
            const nextIndex = Array.from(results).indexOf(current) + 1;
            if (nextIndex < results.length) {
                results[nextIndex].classList.add('selected');
            } else {
                results[0].classList.add('selected');
            }
        }
    }

    selectPreviousResult(results, current) {
        if (results.length === 0) return;

        if (!current) {
            results[results.length - 1].classList.add('selected');
        } else {
            current.classList.remove('selected');
            const prevIndex = Array.from(results).indexOf(current) - 1;
            if (prevIndex >= 0) {
                results[prevIndex].classList.add('selected');
            } else {
                results[results.length - 1].classList.add('selected');
            }
        }
    }

    showSearchResults() {
        document.getElementById('customer-search-results').style.display = 'block';
    }

    hideSearchResults() {
        document.getElementById('customer-search-results').style.display = 'none';
    }

    async selectCustomer(customerId) {
        this.hideSearchResults();
        
        // Mettre à jour l'input avec le nom du client sélectionné
        const searchInput = document.getElementById('customer360-search');
        searchInput.value = 'Chargement...';
        searchInput.disabled = true;

        await this.loadCustomer(customerId);
        
        searchInput.disabled = false;
        searchInput.value = this.currentCustomerData ? this.currentCustomerData.customer.name : '';
    }

    async loadCustomer(customerId, forceRefresh = false) {
        this.currentCustomerId = customerId;
        
        this.showLoading();

        try {
            const response = await fetch(`/api/customer360/customer/${customerId}/overview`);
            const data = await response.json();

            if (data.success) {
                this.currentCustomerData = data;
                this.displayCustomerData(data);
            } else {
                this.showError('Erreur lors du chargement des données client: ' + data.error);
            }
        } catch (error) {
            console.error('Erreur lors du chargement du client:', error);
            this.showError('Erreur de connexion');
        }
    }

    displayCustomerData(data) {
        this.hideLoading();
        
        const customer = data.customer;
        const stats = data.intervention_stats;
        const satisfaction = data.satisfaction_metrics;

        // Header client
        document.getElementById('customer-initials').textContent = this.getInitials(customer.name);
        document.getElementById('customer-name').textContent = customer.name;
        document.getElementById('customer-type-badge').innerHTML = 
            `<span class="badge bg-${this.getCustomerTypeBadge(customer.customer_type)}">${this.getCustomerTypeLabel(customer.customer_type)}</span>`;
        
        document.getElementById('customer-contact').textContent = 
            [customer.email, customer.phone].filter(Boolean).join(' • ');
        
        document.getElementById('customer-location').textContent = 
            [customer.address, customer.city, customer.postal_code].filter(Boolean).join(', ');

        // Métriques de satisfaction
        document.getElementById('completion-rate').textContent = satisfaction.completion_rate + '%';
        document.getElementById('on-time-rate').textContent = satisfaction.on_time_rate + '%';
        document.getElementById('total-interventions').textContent = stats.total_interventions || 0;
        document.getElementById('total-revenue').textContent = this.formatCurrency(stats.total_revenue || 0);

        // Mise à jour des compteurs d'onglets
        document.getElementById('interventions-count').textContent = data.interventions.length;
        document.getElementById('vehicles-count').textContent = data.vehicles.length;
        document.getElementById('invoices-count').textContent = data.invoices.length;
        document.getElementById('equipment-count').textContent = data.equipment.length;
        document.getElementById('communications-count').textContent = data.communications.length;

        // Contenu des onglets
        this.displayInterventions(data.interventions);
        this.displayVehicles(data.vehicles);
        this.displayInvoices(data.invoices);
        this.displayEquipment(data.equipment);
        this.displayCommunications(data.communications);

        // Afficher le contenu principal
        document.getElementById('customer360-initial').classList.add('d-none');
        document.getElementById('customer360-main').classList.remove('d-none');
    }

    displayInterventions(interventions) {
        const container = document.getElementById('interventions-list');
        
        if (interventions.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-muted">Aucune intervention trouvée</div>';
            return;
        }

        container.innerHTML = interventions.map(intervention => `
            <div class="intervention-item priority-${intervention.priority}">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <div class="d-flex align-items-center">
                            <div class="me-3">
                                <h6 class="mb-1">#${intervention.claim_number}</h6>
                                <small class="text-muted">${new Date(intervention.created_at).toLocaleDateString()}</small>
                            </div>
                            <div>
                                <span class="badge bg-${this.getStatusBadge(intervention.status)} status-badge">
                                    ${this.getStatusLabel(intervention.status)}
                                </span>
                                <span class="badge bg-${this.getPriorityBadge(intervention.priority)} status-badge ms-1">
                                    ${this.getPriorityLabel(intervention.priority)}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-muted small">
                            <i class="fa-solid fa-user me-1"></i>
                            ${intervention.technician_name || 'Non assigné'}
                        </div>
                        <div class="text-muted small">
                            <i class="fa-solid fa-notes-medical me-1"></i>
                            ${intervention.notes_count} note(s)
                        </div>
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-sm btn-outline-primary" onclick="customer360Widget.viewIntervention(${intervention.id})">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                    </div>
                </div>
                <div class="mt-2">
                    <p class="mb-0 small">${intervention.problem_description || 'Pas de description'}</p>
                </div>
            </div>
        `).join('');
    }

    displayVehicles(vehicles) {
        const container = document.getElementById('vehicles-list');
        
        if (vehicles.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-muted">Aucun véhicule enregistré</div>';
            return;
        }

        container.innerHTML = vehicles.map(vehicle => `
            <div class="vehicle-item">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="mb-1">${vehicle.make} ${vehicle.model}</h6>
                        <div class="text-muted small">
                            <span class="me-3"><i class="fa-solid fa-hashtag me-1"></i>${vehicle.license_plate}</span>
                            <span class="me-3"><i class="fa-solid fa-calendar me-1"></i>${vehicle.year || 'N/A'}</span>
                            <span><i class="fa-solid fa-wrench me-1"></i>${vehicle.intervention_count || 0} intervention(s)</span>
                        </div>
                    </div>
                    <div class="col-md-4 text-end">
                        <button class="btn btn-sm btn-outline-primary" onclick="customer360Widget.viewVehicle(${vehicle.id})">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    displayInvoices(invoices) {
        const container = document.getElementById('invoices-list');
        
        if (invoices.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-muted">Aucune facture trouvée</div>';
            return;
        }

        container.innerHTML = invoices.map(invoice => `
            <div class="invoice-item">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h6 class="mb-1">Facture #${invoice.invoice_number}</h6>
                        <small class="text-muted">${new Date(invoice.created_at).toLocaleDateString()}</small>
                    </div>
                    <div class="col-md-3">
                        <span class="badge bg-${this.getPaymentStatusBadge(invoice.payment_status)} status-badge">
                            ${this.getPaymentStatusLabel(invoice.payment_status)}
                        </span>
                    </div>
                    <div class="col-md-3 text-end">
                        <div class="fw-semibold">${this.formatCurrency(invoice.total_amount)}</div>
                        <button class="btn btn-sm btn-outline-primary mt-1" onclick="customer360Widget.viewInvoice(${invoice.id})">
                            <i class="fa-solid fa-file-pdf"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    displayEquipment(equipment) {
        const container = document.getElementById('equipment-list');
        
        if (equipment.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-muted">Aucun équipement enregistré</div>';
            return;
        }

        container.innerHTML = equipment.map(item => `
            <div class="equipment-item">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h6 class="mb-1">${item.name}</h6>
                        <small class="text-muted">${item.model || 'Modèle non spécifié'} • ${item.serial_number || 'S/N non spécifié'}</small>
                    </div>
                    <div class="col-md-3">
                        <span class="badge bg-${this.getMaintenanceStatusBadge(item.maintenance_status)} status-badge">
                            ${this.getMaintenanceStatusLabel(item.maintenance_status)}
                        </span>
                        <div class="text-muted small mt-1">
                            ${item.hours_of_use}h d'utilisation
                        </div>
                    </div>
                    <div class="col-md-3 text-end">
                        <div class="text-muted small">
                            Prochaine maintenance:
                            <br>
                            <strong>${item.next_maintenance_due ? new Date(item.next_maintenance_due).toLocaleDateString() : 'Non planifiée'}</strong>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    displayCommunications(communications) {
        const container = document.getElementById('communications-list');
        
        if (communications.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-muted">Aucune communication récente</div>';
            return;
        }

        container.innerHTML = communications.map(comm => `
            <div class="communication-item mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="d-flex align-items-center">
                        <i class="fa-solid ${comm.type === 'note' ? 'fa-sticky-note' : 'fa-comment'} me-2 text-primary"></i>
                        <strong>${comm.author_name || 'Système'}</strong>
                        <span class="badge bg-secondary ms-2">${comm.type === 'note' ? 'Note' : 'Chat'}</span>
                    </div>
                    <small class="text-muted">${new Date(comm.created_at).toLocaleDateString()}</small>
                </div>
                <p class="mb-1">${comm.content}</p>
                <small class="text-muted">Contexte: ${comm.context_ref}</small>
            </div>
        `).join('');
    }

    // Actions
    showTimeline() {
        if (!this.currentCustomerId) return;
        
        // Ouvrir une modal avec la timeline
        this.loadAndShowTimeline(this.currentCustomerId);
    }

    async loadAndShowTimeline(customerId) {
        try {
            const response = await fetch(`/api/customer360/customer/${customerId}/timeline`);
            const data = await response.json();

            if (data.success) {
                this.displayTimelineModal(data.timeline);
            } else {
                showToast('Erreur lors du chargement de la timeline', 'error');
            }
        } catch (error) {
            console.error('Erreur timeline:', error);
            showToast('Erreur lors du chargement de la timeline', 'error');
        }
    }

    displayTimelineModal(timeline) {
        const modalHtml = `
            <div class="modal fade" id="customerTimelineModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fa-solid fa-clock-rotate-left me-2"></i>
                                Timeline - ${this.currentCustomerData.customer.name}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="timeline">
                                ${timeline.map(event => `
                                    <div class="timeline-item">
                                        <div class="timeline-marker bg-${event.badge_color}">
                                            <i class="fa-solid fa-${this.getEventIcon(event.event_type)}"></i>
                                        </div>
                                        <div class="timeline-content">
                                            <div class="timeline-header">
                                                <h6>${event.title}</h6>
                                                <small class="text-muted">${new Date(event.event_date).toLocaleString()}</small>
                                            </div>
                                            <p class="mb-1">${event.description || ''}</p>
                                            <small class="text-muted">Par: ${event.actor}</small>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
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
        const modal = new bootstrap.Modal(document.getElementById('customerTimelineModal'));
        modal.show();
        
        // Nettoyer après fermeture
        document.getElementById('customerTimelineModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }

    createIntervention() {
        if (!this.currentCustomerId) return;
        
        // Rediriger vers la création d'intervention avec le client pré-sélectionné
        if (window.ChronoTechDashboard && window.ChronoTechDashboard.createWorkOrder) {
            window.ChronoTechDashboard.createWorkOrder(this.currentCustomerId);
        } else {
            showToast('Fonction de création d\'intervention non disponible', 'warning');
        }
    }

    viewIntervention(interventionId) {
        if (window.ChronoTechDashboard && window.ChronoTechDashboard.showWorkOrderDetails) {
            window.ChronoTechDashboard.showWorkOrderDetails(interventionId);
        } else {
            showToast('Fonction d\'affichage des détails non disponible', 'warning');
        }
    }

    viewVehicle(vehicleId) {
        showToast(`Affichage du véhicule ${vehicleId} - À implémenter`, 'info');
    }

    viewInvoice(invoiceId) {
        showToast(`Affichage de la facture ${invoiceId} - À implémenter`, 'info');
    }

    // Utilitaires
    showLoading() {
        document.getElementById('customer360-initial').classList.add('d-none');
        document.getElementById('customer360-main').classList.add('d-none');
        document.getElementById('customer360-loading').classList.remove('d-none');
    }

    hideLoading() {
        document.getElementById('customer360-loading').classList.add('d-none');
    }

    showError(message) {
        this.hideLoading();
        const content = document.getElementById('customer360-content');
        content.innerHTML = `
            <div class="alert alert-danger text-center">
                <i class="fa-solid fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }

    getInitials(name) {
        return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
    }

    getCustomerTypeBadge(type) {
        const badges = {
            'company': 'primary',
            'individual': 'success',
            'government': 'info'
        };
        return badges[type] || 'secondary';
    }

    getCustomerTypeLabel(type) {
        const labels = {
            'company': 'Entreprise',
            'individual': 'Particulier',
            'government': 'Administration'
        };
        return labels[type] || type;
    }

    getStatusBadge(status) {
        const badges = {
            'pending': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        };
        return badges[status] || 'secondary';
    }

    getStatusLabel(status) {
        const labels = {
            'pending': 'En attente',
            'in_progress': 'En cours',
            'completed': 'Terminé',
            'cancelled': 'Annulé'
        };
        return labels[status] || status;
    }

    getPriorityBadge(priority) {
        const badges = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'dark'
        };
        return badges[priority] || 'secondary';
    }

    getPriorityLabel(priority) {
        const labels = {
            'low': 'Basse',
            'medium': 'Moyenne',
            'high': 'Haute',
            'urgent': 'Urgente'
        };
        return labels[priority] || priority;
    }

    getPaymentStatusBadge(status) {
        const badges = {
            'paid': 'success',
            'pending': 'warning',
            'overdue': 'danger'
        };
        return badges[status] || 'secondary';
    }

    getPaymentStatusLabel(status) {
        const labels = {
            'paid': 'Payé',
            'pending': 'En attente',
            'overdue': 'En retard'
        };
        return labels[status] || status;
    }

    getMaintenanceStatusBadge(status) {
        const badges = {
            'due': 'danger',
            'soon': 'warning',
            'ok': 'success'
        };
        return badges[status] || 'secondary';
    }

    getMaintenanceStatusLabel(status) {
        const labels = {
            'due': 'Maintenance due',
            'soon': 'Bientôt due',
            'ok': 'À jour'
        };
        return labels[status] || status;
    }

    getEventIcon(eventType) {
        const icons = {
            'work_order_created': 'plus',
            'work_order_completed': 'check',
            'invoice_created': 'file-invoice'
        };
        return icons[eventType] || 'circle';
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount);
    }
}

// Instance globale
let customer360Widget;

// Initialiser quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('customer360-widget')) {
        customer360Widget = new Customer360Widget();
    }
});
