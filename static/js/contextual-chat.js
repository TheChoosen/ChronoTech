/**
 * ChronoTech - Chat Contextuel
 * Système de chat en temps réel avec Socket.IO
 */

class ContextualChat {
    constructor() {
        this.socket = null;
        this.currentContext = null;
        this.currentContextId = null;
        this.currentUser = null;
        this.typingTimeout = null;
        this.isTyping = false;
        this.onlineUsers = new Map();
        this.messages = [];
        
        this.init();
    }

    init() {
        this.initSocketConnection();
        this.bindEvents();
        this.getCurrentUser();
    }

    initSocketConnection() {
        // Initialiser Socket.IO
        this.socket = io('/chat', {
            autoConnect: false
        });

        this.setupSocketEvents();
    }

    setupSocketEvents() {
        this.socket.on('connect', () => {
            console.log('Connecté au chat');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('Déconnecté du chat');
            this.updateConnectionStatus(false);
        });

        this.socket.on('chat_history', (data) => {
            this.loadChatHistory(data.messages);
        });

        this.socket.on('new_message', (message) => {
            this.addMessage(message);
        });

        this.socket.on('user_joined', (data) => {
            this.handleUserJoined(data);
        });

        this.socket.on('user_left', (data) => {
            this.handleUserLeft(data);
        });

        this.socket.on('user_typing', (data) => {
            this.handleUserTyping(data);
        });

        this.socket.on('error', (error) => {
            showToast('Erreur de chat: ' + error.message, 'error');
        });
    }

    bindEvents() {
        // Boutons de sélection de contexte
        document.querySelectorAll('.chat-context-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.selectContext(btn.dataset.context);
            });
        });

        // Retour à la sélection de contexte
        document.getElementById('back-to-context-selector')?.addEventListener('click', () => {
            this.leaveCurrentChat();
        });

        // Envoi de message
        document.getElementById('chat-send-message')?.addEventListener('click', () => {
            this.sendMessage();
        });

        // Saisie de message
        const messageInput = document.getElementById('chat-message-input');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });

            messageInput.addEventListener('input', () => {
                this.handleTyping();
            });

            messageInput.addEventListener('blur', () => {
                this.stopTyping();
            });
        }

        // Upload de fichier
        document.getElementById('chat-attach-file')?.addEventListener('click', () => {
            document.getElementById('chat-file-input').click();
        });

        document.getElementById('chat-file-input')?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.uploadFile(e.target.files[0]);
            }
        });

        // Sidebar utilisateurs
        document.getElementById('toggle-chat-sidebar')?.addEventListener('click', () => {
            this.toggleUsersSidebar();
        });

        document.getElementById('close-chat-sidebar')?.addEventListener('click', () => {
            this.hideUsersSidebar();
        });
    }

    async getCurrentUser() {
        try {
            const response = await fetch('/api/auth/me');
            const data = await response.json();
            if (data.success) {
                this.currentUser = data.user;
            }
        } catch (error) {
            console.error('Erreur lors de la récupération de l\'utilisateur:', error);
        }
    }

    selectContext(contextType) {
        this.showEntitySelector(contextType);
    }

    showEntitySelector(contextType) {
        const modal = new bootstrap.Modal(document.getElementById('chatEntitySelectorModal'));
        const entityTypeLabel = document.getElementById('entity-type-label');
        const searchInput = document.getElementById('entity-search-input');
        
        // Mettre à jour le label selon le type
        const labels = {
            'work_order': 'une intervention',
            'customer': 'un client',
            'vehicle': 'un véhicule'
        };
        
        entityTypeLabel.textContent = labels[contextType] || 'un élément';
        
        // Vider la recherche précédente
        searchInput.value = '';
        document.getElementById('entity-search-results').innerHTML = `
            <div class="text-center text-muted p-4">
                <i class="fa-solid fa-search fa-2x mb-2"></i>
                <p>Tapez au moins 2 caractères pour rechercher</p>
            </div>
        `;

        // Configurer la recherche
        this.setupEntitySearch(contextType, searchInput);
        
        modal.show();
    }

    setupEntitySearch(contextType, searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                document.getElementById('entity-search-results').innerHTML = `
                    <div class="text-center text-muted p-4">
                        <i class="fa-solid fa-search fa-2x mb-2"></i>
                        <p>Tapez au moins 2 caractères pour rechercher</p>
                    </div>
                `;
                return;
            }

            searchTimeout = setTimeout(() => {
                this.searchEntities(contextType, query);
            }, 300);
        });
    }

    async searchEntities(contextType, query) {
        try {
            const endpoints = {
                'work_order': `/api/workorders/search?q=${encodeURIComponent(query)}`,
                'customer': `/api/customers/search?q=${encodeURIComponent(query)}`,
                'vehicle': `/api/vehicles/search?q=${encodeURIComponent(query)}`
            };

            const response = await fetch(endpoints[contextType]);
            const data = await response.json();

            if (data.success) {
                this.displayEntityResults(contextType, data.results || data.customers || data.vehicles);
            } else {
                this.showSearchError('Erreur lors de la recherche');
            }
        } catch (error) {
            console.error('Erreur de recherche:', error);
            this.showSearchError('Erreur de connexion');
        }
    }

    displayEntityResults(contextType, results) {
        const container = document.getElementById('entity-search-results');
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="fa-solid fa-search fa-2x mb-2"></i>
                    <p>Aucun résultat trouvé</p>
                </div>
            `;
            return;
        }

        container.innerHTML = results.map(item => {
            return this.renderEntityResult(contextType, item);
        }).join('');

        // Ajouter les événements de clic
        container.querySelectorAll('.entity-search-result').forEach(result => {
            result.addEventListener('click', () => {
                const entityId = result.dataset.entityId;
                const entityData = JSON.parse(result.dataset.entityData);
                this.selectEntity(contextType, entityId, entityData);
            });
        });
    }

    renderEntityResult(contextType, item) {
        switch (contextType) {
            case 'work_order':
                return `
                    <div class="entity-search-result" data-entity-id="${item.id}" data-entity-data='${JSON.stringify(item)}'>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">#${item.claim_number}</div>
                                <div class="text-muted small">${item.customer_name || 'Client non spécifié'}</div>
                                <div class="text-muted small">${item.problem_description || 'Pas de description'}</div>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-${this.getStatusBadge(item.status)}">${this.getStatusLabel(item.status)}</span>
                                <br>
                                <small class="text-muted">${new Date(item.created_at).toLocaleDateString()}</small>
                            </div>
                        </div>
                    </div>
                `;
            
            case 'customer':
                return `
                    <div class="entity-search-result" data-entity-id="${item.id}" data-entity-data='${JSON.stringify(item)}'>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">${item.name}</div>
                                <div class="text-muted small">
                                    ${item.email ? item.email + ' • ' : ''}
                                    ${item.phone || ''}
                                </div>
                                <div class="text-muted small">${item.city || ''}</div>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-${this.getCustomerTypeBadge(item.customer_type)}">
                                    ${this.getCustomerTypeLabel(item.customer_type)}
                                </span>
                                <br>
                                <small class="text-muted">${item.intervention_count || 0} intervention(s)</small>
                            </div>
                        </div>
                    </div>
                `;
            
            case 'vehicle':
                return `
                    <div class="entity-search-result" data-entity-id="${item.id}" data-entity-data='${JSON.stringify(item)}'>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">${item.make} ${item.model}</div>
                                <div class="text-muted small">${item.license_plate}</div>
                                <div class="text-muted small">${item.customer_name || 'Client non spécifié'}</div>
                            </div>
                            <div class="text-end">
                                <div class="text-muted small">Année: ${item.year || 'N/A'}</div>
                                <div class="text-muted small">${item.intervention_count || 0} intervention(s)</div>
                            </div>
                        </div>
                    </div>
                `;
            
            default:
                return '';
        }
    }

    selectEntity(contextType, entityId, entityData) {
        // Fermer la modal
        bootstrap.Modal.getInstance(document.getElementById('chatEntitySelectorModal')).hide();
        
        // Démarrer le chat pour cette entité
        this.startChat(contextType, entityId, entityData);
    }

    startChat(contextType, entityId, entityData) {
        this.currentContext = contextType;
        this.currentContextId = entityId;
        
        // Mettre à jour l'interface
        this.updateChatHeader(contextType, entityData);
        this.showChatInterface();
        
        // Se connecter au socket et rejoindre la room
        if (!this.socket.connected) {
            this.socket.connect();
        }
        
        this.socket.emit('join_chat', {
            context_type: contextType,
            context_id: entityId
        });
    }

    updateChatHeader(contextType, entityData) {
        const titleElement = document.getElementById('chat-context-title');
        const subtitleElement = document.getElementById('chat-context-subtitle');
        
        switch (contextType) {
            case 'work_order':
                titleElement.textContent = `Intervention #${entityData.claim_number}`;
                subtitleElement.textContent = `${entityData.customer_name || 'Client non spécifié'} • ${this.getStatusLabel(entityData.status)}`;
                break;
            
            case 'customer':
                titleElement.textContent = entityData.name;
                subtitleElement.textContent = `Client • ${entityData.city || 'Ville non spécifiée'}`;
                break;
            
            case 'vehicle':
                titleElement.textContent = `${entityData.make} ${entityData.model}`;
                subtitleElement.textContent = `${entityData.license_plate} • ${entityData.customer_name || 'Client non spécifié'}`;
                break;
        }
    }

    showChatInterface() {
        document.getElementById('chat-context-selector').classList.add('d-none');
        document.getElementById('chat-interface').classList.remove('d-none');
        
        // Vider les messages précédents
        document.getElementById('chat-messages').innerHTML = `
            <div class="text-center text-muted small mb-3" id="chat-loading">
                <i class="fa-solid fa-spinner fa-spin me-2"></i>
                Chargement des messages...
            </div>
        `;
    }

    hideChatInterface() {
        document.getElementById('chat-interface').classList.add('d-none');
        document.getElementById('chat-context-selector').classList.remove('d-none');
    }

    loadChatHistory(messages) {
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted small">
                    <i class="fa-solid fa-comments me-2"></i>
                    Aucun message. Commencez la conversation !
                </div>
            `;
            return;
        }

        messages.forEach(message => {
            this.addMessage(message, false);
        });

        this.scrollToBottom();
    }

    addMessage(message, animate = true) {
        const container = document.getElementById('chat-messages');
        const messageElement = this.createMessageElement(message);
        
        if (animate) {
            messageElement.style.opacity = '0';
            messageElement.style.transform = 'translateY(20px)';
        }
        
        container.appendChild(messageElement);
        
        if (animate) {
            setTimeout(() => {
                messageElement.style.transition = 'all 0.3s ease';
                messageElement.style.opacity = '1';
                messageElement.style.transform = 'translateY(0)';
            }, 10);
        }
        
        this.scrollToBottom();
    }

    createMessageElement(message) {
        const isOwnMessage = this.currentUser && message.user_id === this.currentUser.id;
        const template = message.message_type === 'file' ? 
            document.getElementById('chat-file-message-template') : 
            document.getElementById('chat-message-template');
        
        const messageElement = template.content.cloneNode(true);
        const messageDiv = messageElement.querySelector('.chat-message');
        
        // Marquer comme message personnel
        if (isOwnMessage) {
            messageDiv.classList.add('own');
        }
        
        // Remplir les données
        messageDiv.dataset.messageId = message.id;
        messageDiv.querySelector('.message-author').textContent = message.user_name;
        messageDiv.querySelector('.message-time').textContent = this.formatTime(message.created_at || message.timestamp);
        
        // Avatar
        const avatar = messageDiv.querySelector('.avatar-circle');
        avatar.textContent = this.getInitials(message.user_name);
        avatar.style.background = this.getAvatarColor(message.user_id);
        
        // Contenu du message
        if (message.message_type === 'file') {
            // Message avec fichier
            const fileName = this.extractFileName(message.content);
            messageDiv.querySelector('.file-name').textContent = fileName;
            messageDiv.querySelector('.file-info').textContent = 'Fichier partagé';
            
            messageDiv.querySelector('.download-file').addEventListener('click', () => {
                this.downloadFile(message.id);
            });
        } else {
            // Message texte
            messageDiv.querySelector('.message-body').textContent = message.content;
        }
        
        return messageDiv;
    }

    sendMessage() {
        const input = document.getElementById('chat-message-input');
        const message = input.value.trim();
        
        if (!message || !this.currentContext || !this.currentContextId) {
            return;
        }

        this.socket.emit('send_message', {
            context_type: this.currentContext,
            context_id: this.currentContextId,
            message: message,
            type: 'text'
        });

        input.value = '';
        this.stopTyping();
    }

    handleTyping() {
        if (!this.currentContext || !this.currentContextId) return;

        if (!this.isTyping) {
            this.isTyping = true;
            this.socket.emit('typing_start', {
                context_type: this.currentContext,
                context_id: this.currentContextId
            });
        }

        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.stopTyping();
        }, 3000);
    }

    stopTyping() {
        if (this.isTyping && this.currentContext && this.currentContextId) {
            this.isTyping = false;
            this.socket.emit('typing_stop', {
                context_type: this.currentContext,
                context_id: this.currentContextId
            });
        }
        clearTimeout(this.typingTimeout);
    }

    handleUserTyping(data) {
        const indicator = document.getElementById('typing-indicator');
        const usersSpan = document.getElementById('typing-users');
        
        if (data.typing) {
            usersSpan.textContent = data.user_name;
            indicator.classList.remove('d-none');
        } else {
            indicator.classList.add('d-none');
        }
    }

    handleUserJoined(data) {
        this.onlineUsers.set(data.user_id, data);
        this.updateOnlineCount();
        this.updateParticipantsList();
        
        // Notification discrète
        showToast(`${data.user_name} a rejoint la conversation`, 'info', 2000);
    }

    handleUserLeft(data) {
        this.onlineUsers.delete(data.user_id);
        this.updateOnlineCount();
        this.updateParticipantsList();
    }

    updateOnlineCount() {
        const count = this.onlineUsers.size;
        document.getElementById('chat-online-count').textContent = count;
    }

    updateParticipantsList() {
        const container = document.getElementById('chat-participants-list');
        const template = document.getElementById('chat-participant-template');
        
        container.innerHTML = '';
        
        this.onlineUsers.forEach(user => {
            const participantElement = template.content.cloneNode(true);
            const participant = participantElement.querySelector('.participant-item');
            
            participant.querySelector('.participant-name').textContent = user.user_name;
            participant.querySelector('.participant-status').textContent = 'En ligne';
            
            const avatar = participant.querySelector('.avatar-circle');
            avatar.textContent = this.getInitials(user.user_name);
            avatar.style.background = this.getAvatarColor(user.user_id);
            
            container.appendChild(participant);
        });
    }

    async uploadFile(file) {
        if (!this.currentContext || !this.currentContextId) return;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('context_type', this.currentContext);
        formData.append('context_id', this.currentContextId);

        try {
            const response = await fetch('/api/chat/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (!data.success) {
                showToast('Erreur lors de l\'upload: ' + data.error, 'error');
            }
            // Le message sera automatiquement ajouté via Socket.IO
        } catch (error) {
            console.error('Erreur upload:', error);
            showToast('Erreur lors de l\'upload du fichier', 'error');
        }
    }

    leaveCurrentChat() {
        if (this.currentContext && this.currentContextId) {
            this.socket.emit('leave_chat', {
                context_type: this.currentContext,
                context_id: this.currentContextId
            });
        }
        
        this.currentContext = null;
        this.currentContextId = null;
        this.onlineUsers.clear();
        this.hideChatInterface();
        this.hideUsersSidebar();
    }

    toggleUsersSidebar() {
        const sidebar = document.getElementById('chat-sidebar');
        sidebar.classList.toggle('d-none');
    }

    hideUsersSidebar() {
        document.getElementById('chat-sidebar').classList.add('d-none');
    }

    updateConnectionStatus(connected) {
        const status = document.getElementById('chat-status');
        if (connected) {
            status.textContent = 'En ligne';
            status.className = 'text-success small';
        } else {
            status.textContent = 'Hors ligne';
            status.className = 'text-danger small';
        }
    }

    scrollToBottom() {
        const container = document.getElementById('chat-messages');
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }

    // Utilitaires
    getInitials(name) {
        return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
    }

    getAvatarColor(userId) {
        const colors = [
            'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
            'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
            'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
            'linear-gradient(135deg, #ff8a80 0%, #ea6100 100%)'
        ];
        return colors[userId % colors.length];
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    extractFileName(content) {
        const match = content.match(/📎 Fichier partagé: (.+)/);
        return match ? match[1] : 'Fichier';
    }

    downloadFile(messageId) {
        window.open(`/api/chat/download/${messageId}`, '_blank');
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

    showSearchError(message) {
        document.getElementById('entity-search-results').innerHTML = `
            <div class="text-center text-danger p-4">
                <i class="fa-solid fa-exclamation-triangle fa-2x mb-2"></i>
                <p>${message}</p>
            </div>
        `;
    }
}

// Instance globale
let contextualChat;

// Initialiser quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('contextual-chat-widget')) {
        contextualChat = new ContextualChat();
    }
});
