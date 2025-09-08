// ChronoChat Dashboard v1.0 - Interface de messagerie et gestion d'équipe temps réel
// Système complet de chat, Kanban, calendrier et assistant IA

// Vérifier si la classe existe déjà pour éviter les redéclarations
if (typeof window.ChronoChatDashboard === 'undefined') {
    
window.ChronoChatDashboard = class ChronoChatDashboard {
    constructor() {
        this.socket = null;
        this.calendar = null;
        this.currentChannel = 'global';
        this.onlineUsers = new Map();
        this.isTyping = false;
        this.typingTimeout = null;
        this.notifications = [];
        
        this.init();
    }

    init() {
        console.log('🚀 Initialisation ChronoChat Dashboard v1.0');
        
        // Initialiser Socket.IO
        this.initSocket();
        
        // Initialiser les composants
        this.initKanban();
        this.initChat();
        this.initCalendar();
        this.initNotifications();
        this.initAura();
        
        // Charger les données initiales
        this.loadDashboardStats();
        this.loadKanbanData();
        this.loadOnlineUsers();
        
        // Démarrer les mises à jour périodiques
        this.startPeriodicUpdates();
        
        // Gestion des événements
        this.setupEventHandlers();
        
        console.log('✅ ChronoChat Dashboard initialisé avec succès');
    }

    // ==================== SOCKET.IO ====================
    initSocket() {
        // Socket.IO optionnel - fonctionne sans si pas disponible
        if (typeof io !== 'undefined') {
            try {
                this.socket = io({
                    transports: ['websocket', 'polling'],
                    upgrade: true,
                    timeout: 5000,
                    autoConnect: true
                });

                this.socket.on('connect', () => {
                    console.log('📡 Connecté au serveur Socket.IO');
                    this.joinChannel(this.currentChannel);
                });

                this.socket.on('disconnect', () => {
                    console.log('📡 Déconnecté du serveur Socket.IO');
                });

                this.socket.on('connect_error', (error) => {
                    console.log('⚠️ Socket.IO non disponible, fonctionnement en mode dégradé');
                    this.socket = null; // Désactiver les tentatives de reconnexion
                });

                // Événements de chat
                this.socket.on('new_message', (data) => {
                    this.addChatMessage(data);
                });

                this.socket.on('user_joined', (data) => {
                    this.handleUserJoined(data);
                });

                this.socket.on('user_left', (data) => {
                    this.handleUserLeft(data);
                });

                this.socket.on('typing_start', (data) => {
                    this.showTypingIndicator(data);
                });

                this.socket.on('typing_stop', (data) => {
                    this.hideTypingIndicator(data);
                });

                // Événements de présence
                this.socket.on('presence_update', (data) => {
                    this.updateOnlineUsers(data);
                });

                // Événements de notifications
                this.socket.on('notification', (data) => {
                    this.addNotification(data);
                });

            } catch (error) {
                console.log('⚠️ Erreur Socket.IO:', error.message);
                this.socket = null;
            }
        } else {
            console.log('⚠️ Socket.IO non disponible, fonctionnement sans WebSocket');
            this.socket = null;
        }
    }

    joinChannel(channel) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('join_channel', { channel });
        }
    }

    // ==================== CHAT D'ÉQUIPE ====================
    initChat() {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            chatInput.addEventListener('input', () => this.handleTyping());
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });

            // Compteur de caractères
            chatInput.addEventListener('input', () => {
                const charCount = document.getElementById('char-count');
                if (charCount) {
                    charCount.textContent = `${chatInput.value.length}/500`;
                }
            });
        }
    }

    switchChannel(channel) {
        this.currentChannel = channel;
        document.getElementById('current-channel').textContent = 
            channel.charAt(0).toUpperCase() + channel.slice(1);
        
        if (this.socket) {
            this.socket.emit('leave_channel', {channel: this.currentChannel});
            this.socket.emit('join_channel', {channel: channel});
        }
        
        this.loadChatHistory(channel);
    }

    sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        if (this.socket) {
            this.socket.emit('send_message', {
                channel: this.currentChannel,
                message: message,
                timestamp: new Date().toISOString()
            });
        }
        
        input.value = '';
        this.stopTyping();
    }

    addChatMessage(data) {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${data.user_id === getCurrentUserId() ? 'own' : 'other'}`;
        
        const time = new Date(data.timestamp).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="d-flex ${data.user_id === getCurrentUserId() ? 'justify-content-end' : 'justify-content-start'} align-items-start mb-2">
                ${data.user_id !== getCurrentUserId() ? `
                    <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center me-2">
                        <span class="text-white fw-bold">${data.username.substr(0, 2).toUpperCase()}</span>
                    </div>
                ` : ''}
                <div class="message-bubble ${data.user_id === getCurrentUserId() ? 'bg-primary text-white' : 'bg-light'}">
                    ${data.user_id !== getCurrentUserId() ? `<strong>${data.username}:</strong><br>` : ''}
                    ${data.message}
                    <div class="message-time mt-1">
                        <small class="opacity-75">${time}</small>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            if (this.socket) {
                this.socket.emit('typing_start', {
                    channel: this.currentChannel
                });
            }
        }
        
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.stopTyping();
        }, 2000);
    }

    stopTyping() {
        if (this.isTyping) {
            this.isTyping = false;
            if (this.socket) {
                this.socket.emit('typing_stop', {
                    channel: this.currentChannel
                });
            }
        }
    }

    // ==================== KANBAN BOARD ====================
    initKanban() {
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        // Configuration du drag & drop pour les cartes Kanban
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('kanban-card')) {
                e.target.classList.add('dragging');
                e.dataTransfer.setData('text/plain', e.target.dataset.cardId);
            }
        });

        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('kanban-card')) {
                e.target.classList.remove('dragging');
            }
        });
    }

    allowDrop(event) {
        event.preventDefault();
    }

    handleDrop(event) {
        event.preventDefault();
        const cardId = event.dataTransfer.getData('text/plain');
        const newStatus = event.currentTarget.closest('.kanban-column').dataset.status;
        
        this.updateWorkOrderStatus(cardId, newStatus);
    }

    async updateWorkOrderStatus(workOrderId, newStatus) {
        try {
            const response = await fetch(`/api/work-orders/${workOrderId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({status: newStatus})
            });

            if (response.ok) {
                // La mise à jour sera propagée via Socket.IO
                this.showToast('Statut mis à jour avec succès', 'success');
            } else {
                throw new Error('Erreur lors de la mise à jour');
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showToast('Erreur lors de la mise à jour du statut', 'danger');
        }
    }

    loadKanbanData() {
        fetch('/api/kanban-data')
            .then(response => response.json())
            .then(data => {
                this.updateKanbanColumns(data.kanban_data);
            })
            .catch(error => {
                console.error('Erreur lors du chargement des données Kanban:', error);
            });
    }

    updateKanbanColumns(data) {
        const statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
        
        statuses.forEach(status => {
            const column = document.getElementById(`column-${status}`);
            const count = document.getElementById(`count-${status}`);
            
            if (column && data[status]) {
                column.innerHTML = '';
                data[status].forEach(workOrder => {
                    column.appendChild(this.createKanbanCard(workOrder));
                });
                
                if (count) {
                    count.textContent = data[status].length;
                }
            }
        });
    }

    createKanbanCard(workOrder) {
        const card = document.createElement('div');
        card.className = `kanban-card ${workOrder.priority === 'urgent' ? 'urgent-priority' : workOrder.priority === 'high' ? 'high-priority' : ''}`;
        card.draggable = true;
        card.dataset.cardId = workOrder.id;
        
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
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">${workOrder.technician_name || 'Non assigné'}</small>
                <small class="text-muted">${formatDate(workOrder.created_at)}</small>
            </div>
        `;
        
        card.addEventListener('click', () => {
            window.location.href = `/work-orders/${workOrder.id}`;
        });
        
        return card;
    }

    // ==================== FULLCALENDAR ====================
    initCalendar() {
        const calendarEl = document.getElementById('chronocalendar');
        if (!calendarEl) return;

        this.calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            locale: 'fr',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
            },
            height: 'auto',
            events: (info, successCallback, failureCallback) => {
                // Fonction personnalisée pour charger les événements
                fetch('/api/calendar-events?start=' + info.startStr + '&end=' + info.endStr)
                    .then(response => response.json())
                    .then(data => {
                        // S'assurer que nous avons bien les événements sous forme d'array
                        const events = data.events || [];
                        successCallback(events);
                    })
                    .catch(error => {
                        console.error('Erreur lors du chargement des événements:', error);
                        failureCallback(error);
                    });
            },
            editable: true,
            selectable: true,
            selectMirror: true,
            dayMaxEvents: true,
            weekends: true,
            
            select: (info) => {
                this.createEvent(info.start, info.end);
            },
            
            eventClick: (info) => {
                this.editEvent(info.event);
            },
            
            eventDrop: (info) => {
                this.updateEvent(info.event);
            },
            
            eventResize: (info) => {
                this.updateEvent(info.event);
            }
        });
        
        this.calendar.render();
    }

    createEvent(start = null, end = null) {
        // Ouvrir un modal pour créer un nouvel événement
        // Cette fonction sera développée selon les besoins spécifiques
        console.log('Créer un nouvel événement', start, end);
    }

    // ==================== ASSISTANT AURA ====================
    initAura() {
        // Initialiser l'assistant IA AURA
        console.log('🤖 Initialisation AURA Assistant IA');
    }

    async askAura() {
        const input = document.getElementById('aura-input');
        const question = input.value.trim();
        
        if (!question) return;
        
        // Ajouter la question de l'utilisateur
        this.addAuraMessage(question, 'user');
        input.value = '';
        
        // Afficher l'indicateur de chargement
        this.addAuraMessage('AURA analyse votre question...', 'system', true);
        
        try {
            const response = await fetch('/api/aura-assistant', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({question: question})
            });
            
            const data = await response.json();
            
            // Supprimer l'indicateur de chargement
            this.removeLoadingMessage();
            
            // Ajouter la réponse d'AURA
            this.addAuraMessage(data.response, 'system');
            
        } catch (error) {
            this.removeLoadingMessage();
            this.addAuraMessage('Désolé, je rencontre un problème technique. Veuillez réessayer.', 'system');
        }
    }

    addAuraMessage(message, type, isLoading = false) {
        const chatContainer = document.getElementById('aura-chat');
        if (!chatContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `aura-message ${type} mb-3 ${isLoading ? 'loading' : ''}`;
        
        if (type === 'user') {
            messageDiv.innerHTML = `
                <div class="d-flex justify-content-end">
                    <div class="bg-primary text-white rounded p-3" style="max-width: 70%;">
                        ${message}
                    </div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center me-3">
                        <i class="fa-solid fa-robot text-white"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="bg-light rounded p-3">
                            <strong>AURA:</strong> ${message}
                        </div>
                        <small class="text-muted">Maintenant</small>
                    </div>
                </div>
            `;
        }
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    quickAuraQuery(type) {
        const queries = {
            'revenus': 'Analyse mes revenus du mois en cours et compare avec le mois précédent',
            'performance': 'Donne-moi un rapport de performance de mes techniciens cette semaine',
            'clients': 'Quels sont mes 5 clients les plus rentables ce mois-ci?',
            'prediction': 'Prédis les tendances de revenus pour le mois prochain'
        };
        
        document.getElementById('aura-input').value = queries[type] || '';
        this.askAura();
    }

    // ==================== NOTIFICATIONS ====================
    initNotifications() {
        this.loadNotifications();
    }

    loadNotifications() {
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                // S'assurer que nous avons bien les notifications sous forme d'array
                this.notifications = data.notifications || [];
                this.updateNotificationBadge();
                this.renderNotifications();
            })
            .catch(error => {
                console.error('Erreur lors du chargement des notifications:', error);
            });
    }

    addNotification(notification) {
        if (!Array.isArray(this.notifications)) {
            this.notifications = [];
        }
        this.notifications.unshift(notification);
        this.updateNotificationBadge();
        this.renderNotifications();
        this.showToast(notification.message, 'info');
    }

    updateNotificationBadge() {
        const badge = document.getElementById('notif-badge');
        if (badge) {
            if (!Array.isArray(this.notifications)) {
                this.notifications = [];
            }
            const unreadCount = this.notifications.filter(n => !n.is_read).length;
            badge.textContent = unreadCount;
            badge.style.display = unreadCount > 0 ? 'inline' : 'none';
        }
    }

    renderNotifications() {
        // Afficher les notifications dans l'interface si un conteneur existe
        const notificationContainer = document.getElementById('notifications-list');
        if (!notificationContainer) return;

        notificationContainer.innerHTML = '';

        if (!Array.isArray(this.notifications)) {
            this.notifications = [];
        }

        if (this.notifications.length === 0) {
            notificationContainer.innerHTML = '<div class="text-center text-muted p-3">Aucune notification</div>';
            return;
        }

        this.notifications.slice(0, 10).forEach(notification => {
            const notifElement = document.createElement('div');
            notifElement.className = `notification-item ${notification.is_read ? 'read' : 'unread'}`;
            notifElement.innerHTML = `
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${new Date(notification.created_at).toLocaleString()}</div>
                </div>
                <div class="notification-actions">
                    ${!notification.is_read ? '<button class="btn btn-sm btn-outline-primary mark-read" data-id="' + notification.id + '">Marquer comme lu</button>' : ''}
                    <button class="btn btn-sm btn-outline-danger delete-notif" data-id="${notification.id}">×</button>
                </div>
            `;
            notificationContainer.appendChild(notifElement);
        });

        // Ajouter les événements pour les boutons
        notificationContainer.querySelectorAll('.mark-read').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const notifId = e.target.dataset.id;
                this.markNotificationAsRead(notifId);
            });
        });

        notificationContainer.querySelectorAll('.delete-notif').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const notifId = e.target.dataset.id;
                this.deleteNotification(notifId);
            });
        });
    }

    markNotificationAsRead(notificationId) {
        fetch(`/api/notifications/${notificationId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_read: true })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mettre à jour localement
                const notification = this.notifications.find(n => n.id == notificationId);
                if (notification) {
                    notification.is_read = true;
                    this.updateNotificationBadge();
                    this.renderNotifications();
                }
            }
        })
        .catch(error => console.error('Erreur marquage notification:', error));
    }

    deleteNotification(notificationId) {
        fetch(`/api/notifications/${notificationId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Retirer de la liste locale
                this.notifications = this.notifications.filter(n => n.id != notificationId);
                this.updateNotificationBadge();
                this.renderNotifications();
            }
        })
        .catch(error => console.error('Erreur suppression notification:', error));
    }

    // ==================== GESTION DES UTILISATEURS EN LIGNE ====================
    loadOnlineUsers() {
        fetch('/api/online-users')
            .then(response => response.json())
            .then(data => {
                // S'assurer que nous avons bien les utilisateurs sous forme d'array
                const users = data.online_users || [];
                this.updateOnlineUsers(users);
            })
            .catch(error => {
                console.error('Erreur lors du chargement des utilisateurs en ligne:', error);
            });
    }

    updateOnlineUsers(users) {
        const onlineList = document.getElementById('online-team-list');
        const chatOnlineList = document.getElementById('chat-online-users');
        const onlineCount = document.getElementById('online-count');
        const chatOnlineCount = document.getElementById('chat-online-count');
        
        // S'assurer que users est un array
        if (!Array.isArray(users)) {
            users = [];
        }
        
        if (onlineList) {
            onlineList.innerHTML = '';
            users.forEach(user => {
                onlineList.appendChild(this.createOnlineUserElement(user));
            });
        }
        
        if (chatOnlineList) {
            chatOnlineList.innerHTML = '';
            users.forEach(user => {
                chatOnlineList.appendChild(this.createOnlineUserElement(user, true));
            });
        }
        
        if (onlineCount) {
            onlineCount.textContent = users.length;
        }
        
        if (chatOnlineCount) {
            chatOnlineCount.textContent = users.length;
        }
    }

    createOnlineUserElement(user, isChat = false) {
        const div = document.createElement('div');
        div.className = 'online-user';
        
        div.innerHTML = `
            <div class="online-status"></div>
            <div class="flex-grow-1">
                <div class="fw-bold">${user.username}</div>
                <small class="text-muted">${user.role || 'Utilisateur'}</small>
            </div>
            ${isChat ? `
                <button class="btn btn-sm btn-outline-primary" onclick="startPrivateChat('${user.id}')">
                    <i class="fa-solid fa-comment"></i>
                </button>
            ` : ''}
        `;
        
        return div;
    }

    // ==================== STATISTIQUES DU TABLEAU DE BORD ====================
    loadDashboardStats() {
        fetch('/api/dashboard-stats')
            .then(response => response.json())
            .then(data => {
                this.updateStats(data);
            })
            .catch(error => {
                console.error('Erreur lors du chargement des statistiques:', error);
            });
    }

    updateStats(stats) {
        const statElements = {
            'pending-work-orders': stats.pending_work_orders || 0,
            'today-appointments': stats.today_appointments || 0,
            'online-techs': stats.online_technicians || 0,
            'monthly-revenue': stats.monthly_revenue || 0
        };
        
        Object.entries(statElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    // ==================== MISES À JOUR PÉRIODIQUES ====================
    startPeriodicUpdates() {
        // Mettre à jour les statistiques toutes les 30 secondes
        setInterval(() => {
            this.loadDashboardStats();
        }, 30000);
        
        // Mettre à jour les utilisateurs en ligne toutes les 60 secondes
        setInterval(() => {
            this.loadOnlineUsers();
        }, 60000);
        
        // Heartbeat de présence toutes les 5 minutes
        setInterval(() => {
            fetch('/api/presence-heartbeat', {method: 'POST'});
        }, 300000);
    }

    // ==================== UTILITAIRES ====================
    showToast(message, type = 'info') {
        // Créer un toast Bootstrap ou une notification simple
        const toastContainer = document.getElementById('toast-container') || document.body;
        
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        toastContainer.appendChild(toast);
        
        // Auto-remove après 5 secondes
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
    
    setupEventHandlers() {
        // Gestionnaires d'événements globaux
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                document.getElementById('open-team-chat').click();
            }
        });
    }

    showToast(message, type = 'info') {
        // Afficher une notification toast
        console.log(`Toast ${type}: ${message}`);
        // Implémenter avec Bootstrap Toast ou autre système de notification
    }
}

// ==================== FONCTIONS UTILITAIRES GLOBALES ====================
function getCSRFToken() {
    return document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
}

function getCurrentUserId() {
    return window.currentUserId || null;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('fr-FR');
}

// Fonctions globales exposées pour les événements HTML
window.switchChannel = function(channel) {
    if (window.chronochat) {
        window.chronochat.switchChannel(channel);
    }
};

window.sendMessage = function() {
    if (window.chronochat) {
        window.chronochat.sendMessage();
    }
};

window.askAura = function() {
    if (window.chronochat) {
        window.chronochat.askAura();
    }
};

window.quickAuraQuery = function(type) {
    if (window.chronochat) {
        window.chronochat.quickAuraQuery(type);
    }
};

window.allowDrop = function(event) {
    event.preventDefault();
};

window.handleDrop = function(event) {
    if (window.chronochat) {
        window.chronochat.handleDrop(event);
    }
};

window.createWorkOrder = function() {
    window.location.href = '/work-orders/create';
};

// Fonctions de calendrier
window.goToToday = function() {
    if (window.chronochat && window.chronochat.calendar) {
        window.chronochat.calendar.today();
    }
};

window.createEvent = function() {
    if (window.chronochat) {
        window.chronochat.createEvent();
    }
};

// Initialisation automatique quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si la classe existe avant d'initialiser
    if (typeof window.ChronoChatDashboard !== 'undefined' && !window.chronochat) {
        window.chronochat = new window.ChronoChatDashboard();
    }
});

// ==================== EXTENSIONS PRD CHRONOCHAT ====================

// Nouvelles fonctionnalités pour les onglets spécialisés
window.ChronoChatDashboard.prototype.initSpecializedTabs = function() {
    const tabs = document.querySelectorAll('#dashboardTabs button[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', (event) => {
            const targetTab = event.target.getAttribute('data-bs-target');
            this.loadTabData(targetTab);
        });
    });
};

window.ChronoChatDashboard.prototype.loadTabData = async function(tabId) {
    const tabName = tabId.replace('#', '').replace('-pane', '');
    
    switch(tabName) {
        case 'planning':
            this.loadPlanningData();
            break;
        case 'routes':
            this.loadRoutesData();
            break;
        case 'inventory':
            this.loadInventoryData();
            break;
        case 'reports':
            this.loadReportsData();
            break;
    }
};

window.ChronoChatDashboard.prototype.loadInventoryData = async function() {
    try {
        const response = await fetch('/api/inventory/items');
        const data = await response.json();
        
        if (data.success) {
            this.renderInventoryTable(data.items);
        }
    } catch (error) {
        console.error('Erreur chargement inventaire:', error);
    }
};

window.ChronoChatDashboard.prototype.renderInventoryTable = function(items) {
    const tbody = document.getElementById('inventory-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';
    
    items.forEach(item => {
        const statusBadge = this.getInventoryStatusBadge(item.status);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.name}</td>
            <td>${item.category || 'N/A'}</td>
            <td>${item.quantity} ${item.unit || ''}</td>
            <td>${item.minimum_threshold || 'N/A'}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editInventoryItem(${item.id})">
                    <i class="fa-solid fa-edit"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
};

window.ChronoChatDashboard.prototype.getInventoryStatusBadge = function(status) {
    const badges = {
        'disponible': '<span class="badge bg-success">Disponible</span>',
        'stock-bas': '<span class="badge bg-warning">Stock bas</span>',
        'rupture': '<span class="badge bg-danger">Rupture</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">Inconnu</span>';
};

window.ChronoChatDashboard.prototype.loadRoutesData = async function() {
    try {
        const response = await fetch('/api/routes/optimization');
        const data = await response.json();
        
        if (data.success) {
            this.updateRoutesDisplay(data);
        }
    } catch (error) {
        console.error('Erreur chargement routes:', error);
    }
};

window.ChronoChatDashboard.prototype.updateRoutesDisplay = function(data) {
    const scoreEl = document.getElementById('optimization-score');
    const distanceEl = document.getElementById('total-distance');
    const timeEl = document.getElementById('estimated-time');
    
    if (scoreEl) scoreEl.textContent = `${data.optimization_score}%`;
    if (distanceEl) distanceEl.textContent = data.total_distance;
    if (timeEl) timeEl.textContent = data.total_time;

    this.renderAvailableTechnicians(data.technician_routes);
};

window.ChronoChatDashboard.prototype.renderAvailableTechnicians = function(routes) {
    const container = document.getElementById('available-technicians');
    if (!container) return;

    container.innerHTML = '';
    routes.forEach(route => {
        const techCard = document.createElement('div');
        techCard.className = 'card mb-2';
        techCard.innerHTML = `
            <div class="card-body p-2">
                <h6 class="card-title mb-1">${route.technician_name}</h6>
                <small class="text-muted">
                    ${route.total_orders} interventions - ${Math.floor(route.total_duration/60)}h${route.total_duration%60}m
                </small>
            </div>
        `;
        container.appendChild(techCard);
    });
};

// Assistant AURA amélioré
window.ChronoChatDashboard.prototype.askAuraAdvanced = async function() {
    const input = document.getElementById('aura-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    this.addAuraMessage(message, 'user');
    input.value = '';
    
    const loadingId = this.addAuraMessage('AURA analyse votre question...', 'system', true);
    
    try {
        const response = await fetch('/api/aura/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) loadingElement.remove();
        
        if (data.success) {
            this.addAuraMessage(data.message, 'aura');
            
            if (data.suggestions && data.suggestions.length > 0) {
                this.showAuraSuggestions(data.suggestions);
            }
        } else {
            this.addAuraMessage(data.message || 'Erreur lors de l\'analyse.', 'error');
        }
        
    } catch (error) {
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) loadingElement.remove();
        
        console.error('Erreur AURA:', error);
        this.addAuraMessage('Erreur de connexion. Veuillez réessayer.', 'error');
    }
};

window.ChronoChatDashboard.prototype.addAuraMessage = function(message, type = 'aura', isLoading = false) {
    const chatContainer = document.getElementById('aura-chat');
    if (!chatContainer) return;

    const messageId = `aura-msg-${Date.now()}`;
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `aura-message ${type} mb-3`;
    
    let avatar, content;
    
    if (type === 'user') {
        avatar = '<i class="fa-solid fa-user text-white"></i>';
        content = `<div class="bg-primary text-white rounded p-3">${message}</div>`;
    } else if (type === 'error') {
        avatar = '<i class="fa-solid fa-exclamation-triangle text-white"></i>';
        content = `<div class="bg-danger text-white rounded p-3">${message}</div>`;
    } else {
        avatar = '<i class="fa-solid fa-robot text-white"></i>';
        content = `<div class="bg-light rounded p-3">
            ${isLoading ? '<i class="fa-solid fa-spinner fa-spin me-2"></i>' : '<strong>AURA:</strong> '}
            ${message.replace(/\n/g, '<br>')}
        </div>`;
    }
    
    messageDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center me-3">
                ${avatar}
            </div>
            <div class="flex-grow-1">
                ${content}
                <small class="text-muted">${new Date().toLocaleTimeString()}</small>
            </div>
        </div>
    `;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return messageId;
};

window.ChronoChatDashboard.prototype.showAuraSuggestions = function(suggestions) {
    const chatContainer = document.getElementById('aura-chat');
    if (!chatContainer) return;

    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'aura-suggestions mt-2';
    suggestionsDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="avatar-sm bg-info rounded-circle d-flex align-items-center justify-content-center me-3">
                <i class="fa-solid fa-lightbulb text-white"></i>
            </div>
            <div class="flex-grow-1">
                <div class="bg-info bg-opacity-10 rounded p-3">
                    <strong>💡 Suggestions d'actions:</strong><br>
                    ${suggestions.map(s => `• ${s}`).join('<br>')}
                </div>
            </div>
        </div>
    `;
    
    chatContainer.appendChild(suggestionsDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
};

// Fonctions globales mises à jour
window.askAura = function() {
    if (window.chronochat && window.chronochat.askAuraAdvanced) {
        window.chronochat.askAuraAdvanced();
    }
};

window.quickAuraQuery = function(type) {
    const queries = {
        'revenus': 'Analyse mes revenus de ce mois en détail',
        'performance': 'Performance de mes techniciens cette semaine',
        'clients': 'Analyse la satisfaction de mes clients'
    };
    
    const query = queries[type];
    if (query) {
        document.getElementById('aura-input').value = query;
        window.askAura();
    }
};

window.editInventoryItem = function(itemId) {
    alert(`Modification de l'article ${itemId} - Interface en développement`);
};

// Initialiser les onglets spécialisés au chargement
document.addEventListener('DOMContentLoaded', function() {
    if (window.chronochat && window.chronochat.initSpecializedTabs) {
        window.chronochat.initSpecializedTabs();
    }
});

} // Fermer la condition de vérification d'existence de la classe

console.log('📱 ChronoChat Dashboard JavaScript chargé - Prêt pour l\'initialisation');
console.log('🚀 Extensions PRD ChronoChat activées');
