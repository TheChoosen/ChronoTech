// Client API pour ChronoTech Dashboard
export class ApiClient {
    constructor() {
        this.baseUrl = '/api';
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
    }

    // Obtenir le token CSRF
    getCsrfToken() {
        const csrfInput = document.querySelector('[name=csrf_token]');
        return csrfInput ? csrfInput.value : null;
    }

    // Requête générique
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = { ...this.defaultHeaders, ...options.headers };
        
        // Ajouter le token CSRF pour les requêtes non-GET
        if (options.method && options.method !== 'GET') {
            const csrfToken = this.getCsrfToken();
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // Méthodes spécifiques
    async getKanbanData() {
        return this.request('/kanban-data');
    }

    async getWorkOrders(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/work_orders${queryString ? '?' + queryString : ''}`);
    }

    async updateWorkOrderStatus(id, status) {
        return this.request(`/work_orders/${id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    }

    async getTechnicians() {
        return this.request('/technicians');
    }

    async getCalendarEvents(start, end) {
        return this.request(`/calendar/events?start=${start}&end=${end}`);
    }

    async getAnalytics(period = 30) {
        return this.request(`/analytics?period=${period}`);
    }

    async getNotifications() {
        return this.request('/notifications');
    }

    async markNotificationRead(id) {
        return this.request(`/notifications/${id}/read`, {
            method: 'POST'
        });
    }
}

// Instance globale
export const apiClient = new ApiClient();
