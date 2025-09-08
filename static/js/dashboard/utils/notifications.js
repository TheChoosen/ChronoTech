// Système de notifications global pour ChronoTech Dashboard
export class NotificationManager {
    constructor() {
        this.toastContainer = null;
        this.notificationCenter = null;
        this.init();
    }

    init() {
        this.createToastContainer();
        this.setupNotificationCenter();
    }

    createToastContainer() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        this.toastContainer = container;
    }

    setupNotificationCenter() {
        this.notificationCenter = document.getElementById('notificationCenter');
    }

    // Afficher un toast
    showToast(message, type = 'info', duration = 4000) {
        const toastId = 'toast_' + Date.now();
        
        const toastHtml = `
            <div class="toast toast-custom toast-${type}" id="${toastId}" role="alert">
                <div class="toast-body d-flex align-items-center">
                    <i class="fas fa-${this.getIconForType(type)} me-2"></i>
                    <span class="flex-grow-1">${message}</span>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        this.toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: duration });
        toast.show();
        
        // Supprimer le toast après fermeture
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    // Icône selon le type
    getIconForType(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Afficher notification système
    showSystemNotification(title, message, icon = 'bell') {
        if (Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/static/favicon.ico'
            });
        }
    }

    // Demander permission pour les notifications
    async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        }
        return Notification.permission === 'granted';
    }
}

// Instance globale
export const notificationManager = new NotificationManager();

// Compatibilité avec l'ancien système
window.NotificationSystem = {
    showToast: (message, type, duration) => notificationManager.showToast(message, type, duration),
    loadNotifications: () => notificationManager.loadNotifications?.(),
    renderNotifications: (notifications) => notificationManager.renderNotifications?.(notifications),
    formatTime: (timestamp) => notificationManager.formatTime?.(timestamp)
};
