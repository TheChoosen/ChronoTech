/**
 * ChronoChat WebSocket Client - Chat Temps Réel
 * Interface de chat conventionnelle avec sélection utilisateur/département
 */

class ChronoChatClient {
    constructor() {
        this.socket = null;
        this.currentUser = null;
        this.isConnected = false;
        this.currentRoom = 'general';
        this.recipientType = 'general'; // general, user, department
        this.recipientId = null;
        this.typingTimer = null;
        this.departments = [];
        this.users = [];
        this.messages = [];
        
        this.init();
    }
    
    async init() {
        console.log('💬 Initialisation ChronoChat Client...');
        
        // Récupérer les informations utilisateur
        this.currentUser = await this.getCurrentUser();
        
        // Créer l'interface
        this.createChatInterface();
        
        // Initialiser WebSocket
        this.initWebSocket();
        
        // Charger les données initiales
        await this.loadInitialData();
        
        console.log('✅ ChronoChat Client initialisé');
    }
    
    async getCurrentUser() {
        try {
            const response = await fetch('http://localhost:5002/api/current-user');
            return await response.json();
        } catch (error) {
            console.error('Erreur récupération utilisateur:', error);
            return { id: 1, name: 'Admin System', role: 'admin' };
        }
    }
    
    initWebSocket() {
        // Connexion au serveur WebSocket
        this.socket = io('http://localhost:5001', {
            query: {
                user_id: this.currentUser.id,
                username: this.currentUser.name
            },
            autoConnect: false
        });
        
        // Événements WebSocket
        this.socket.on('connect', () => {
            console.log('🔗 WebSocket Chat connecté');
            this.isConnected = true;
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('🔌 WebSocket Chat déconnecté');
            this.isConnected = false;
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('connection_established', (data) => {
            console.log('✅ Connexion établie:', data);
            this.departments = data.departments || [];
            this.updateRecipientOptions();
        });
        
        this.socket.on('new_message', (data) => {
            this.handleNewMessage(data);
        });
        
        this.socket.on('user_connected', (data) => {
            this.showSystemMessage(`${data.username} s'est connecté`);
        });
        
        this.socket.on('user_disconnected', (data) => {
            this.showSystemMessage(`${data.username} s'est déconnecté`);
        });
        
        this.socket.on('user_typing', (data) => {
            this.handleTypingIndicator(data);
        });
        
        this.socket.on('departments_list', (data) => {
            this.departments = data.departments;
            this.updateRecipientOptions();
        });
        
        this.socket.on('department_users', (data) => {
            this.users = data.users;
            this.updateUserOptions(data.department);
        });
        
        this.socket.on('error', (data) => {
            console.error('Erreur WebSocket:', data);
            this.showErrorMessage(data.message);
        });
        
        // Connexion automatique
        setTimeout(() => {
            this.socket.connect();
        }, 500);
    }
    
    createChatInterface() {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) {
            console.error('Container chat non trouvé');
            return;
        }
        
        chatContainer.innerHTML = `
            <div class="chat-wrapper">
                <div class="chat-header">
                    <h3>💬 ChronoChat</h3>
                    <div class="connection-status" id="connection-status">
                        <span class="status-indicator offline"></span>
                        <span class="status-text">Déconnecté</span>
                    </div>
                </div>
                
                <div class="chat-controls">
                    <div class="recipient-selector">
                        <label>Destinataire:</label>
                        <div class="recipient-controls">
                            <select id="recipient-type" class="form-select">
                                <option value="general">💬 Chat général</option>
                                <option value="department">🏢 Département</option>
                                <option value="user">👤 Utilisateur privé</option>
                            </select>
                            
                            <select id="recipient-target" class="form-select" disabled>
                                <option value="">-- Sélectionner --</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <div class="chat-messages" id="chat-messages">
                    <div class="welcome-message">
                        <h4>Bienvenue dans ChronoChat! 👋</h4>
                        <p>Sélectionnez un destinataire pour commencer à discuter.</p>
                    </div>
                </div>
                
                <div class="typing-indicator" id="typing-indicator" style="display: none;">
                    <span class="typing-dots">
                        <span></span><span></span><span></span>
                    </span>
                    <span class="typing-text"></span>
                </div>
                
                <div class="chat-input-container">
                    <div class="chat-input-wrapper">
                        <input type="text" 
                               id="chat-input" 
                               class="form-control" 
                               placeholder="💬 Tapez votre message..." 
                               disabled>
                        <button id="send-button" 
                                class="btn btn-primary" 
                                disabled>
                            📤 Envoyer
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        this.initChatEventListeners();
    }
    
    initChatEventListeners() {
        // Sélection du type de destinataire
        const recipientType = document.getElementById('recipient-type');
        const recipientTarget = document.getElementById('recipient-target');
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        
        recipientType.addEventListener('change', () => {
            this.handleRecipientTypeChange();
        });
        
        recipientTarget.addEventListener('change', () => {
            this.handleRecipientTargetChange();
        });
        
        // Gestion de l'input de chat
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            } else {
                this.handleTyping();
            }
        });
        
        chatInput.addEventListener('input', () => {
            this.handleTyping();
        });
        
        sendButton.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Auto-scroll pour les messages
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.addEventListener('scroll', () => {
            // Marquer les messages comme lus si l'utilisateur scroll vers le bas
            if (messagesContainer.scrollTop + messagesContainer.clientHeight >= messagesContainer.scrollHeight - 10) {
                this.markMessagesAsRead();
            }
        });
    }
    
    async loadInitialData() {
        try {
            // Demander la liste des départements
            if (this.socket && this.socket.connected) {
                this.socket.emit('get_departments');
            }
            
            // Charger l'historique des messages
            await this.loadMessageHistory();
            
        } catch (error) {
            console.error('Erreur chargement données chat:', error);
        }
    }
    
    handleRecipientTypeChange() {
        const recipientType = document.getElementById('recipient-type').value;
        const recipientTarget = document.getElementById('recipient-target');
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        
        this.recipientType = recipientType;
        this.recipientId = null;
        
        // Réinitialiser la sélection
        recipientTarget.innerHTML = '<option value="">-- Sélectionner --</option>';
        
        if (recipientType === 'general') {
            // Chat général - pas besoin de sélection
            recipientTarget.disabled = true;
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.placeholder = "💬 Message général à tous...";
            this.currentRoom = 'general';
            
        } else if (recipientType === 'department') {
            // Départements
            recipientTarget.disabled = false;
            chatInput.disabled = true;
            sendButton.disabled = true;
            chatInput.placeholder = "Sélectionnez d'abord un département...";
            
            // Remplir avec les départements
            this.departments.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = `🏢 ${dept}`;
                recipientTarget.appendChild(option);
            });
            
        } else if (recipientType === 'user') {
            // Utilisateurs - d'abord sélectionner un département
            recipientTarget.disabled = false;
            chatInput.disabled = true;
            sendButton.disabled = true;
            chatInput.placeholder = "Sélectionnez d'abord un département...";
            
            // Remplir avec les départements pour choisir les utilisateurs
            this.departments.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = `🏢 ${dept} (voir utilisateurs)`;
                recipientTarget.appendChild(option);
            });
        }
        
        // Effacer les messages précédents
        this.clearMessages();
    }
    
    handleRecipientTargetChange() {
        const recipientType = document.getElementById('recipient-type').value;
        const recipientTarget = document.getElementById('recipient-target');
        const selectedValue = recipientTarget.value;
        
        if (!selectedValue) return;
        
        if (recipientType === 'department') {
            // Chat de département sélectionné
            this.recipientId = selectedValue;
            this.currentRoom = `dept_${selectedValue}`;
            this.enableChatInput(`💬 Message au département ${selectedValue}...`);
            
            // Rejoindre la room du département
            if (this.socket && this.socket.connected) {
                this.socket.emit('join_room', { room: this.currentRoom });
            }
            
        } else if (recipientType === 'user') {
            // Département sélectionné - charger les utilisateurs
            if (this.socket && this.socket.connected) {
                this.socket.emit('get_users_by_department', { department: selectedValue });
            }
        }
        
        this.clearMessages();
    }
    
    updateUserOptions(department) {
        const recipientTarget = document.getElementById('recipient-target');
        
        // Effacer et remplir avec les utilisateurs
        recipientTarget.innerHTML = '<option value="">-- Sélectionner un utilisateur --</option>';
        
        this.users.forEach(user => {
            if (user.id !== this.currentUser.id) { // Exclure l'utilisateur actuel
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `👤 ${user.name} (${user.role})`;
                recipientTarget.appendChild(option);
            }
        });
        
        // Ajouter un gestionnaire pour la sélection d'utilisateur
        recipientTarget.onchange = () => {
            const userId = recipientTarget.value;
            if (userId) {
                this.recipientId = parseInt(userId);
                const userName = this.users.find(u => u.id == userId)?.name;
                this.currentRoom = `user_${Math.min(this.currentUser.id, userId)}_${Math.max(this.currentUser.id, userId)}`;
                this.enableChatInput(`💬 Message privé à ${userName}...`);
                
                // Rejoindre la room privée
                if (this.socket && this.socket.connected) {
                    this.socket.emit('join_room', { room: this.currentRoom });
                }
                
                this.clearMessages();
            }
        };
    }
    
    enableChatInput(placeholder) {
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.placeholder = placeholder;
        chatInput.focus();
    }
    
    sendMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (!message || !this.isConnected) return;
        
        // Envoyer via WebSocket
        this.socket.emit('send_message', {
            message: message,
            recipient_type: this.recipientType,
            recipient_id: this.recipientId
        });
        
        // Effacer l'input
        chatInput.value = '';
        
        // Arrêter l'indicateur de frappe
        this.stopTyping();
    }
    
    handleNewMessage(data) {
        // Ajouter le message à l'affichage
        this.addMessageToDisplay(data);
        
        // Faire défiler vers le bas
        this.scrollToBottom();
        
        // Jouer un son de notification (optionnel)
        this.playNotificationSound();
    }
    
    addMessageToDisplay(messageData) {
        const messagesContainer = document.getElementById('chat-messages');
        const isOwnMessage = messageData.user_id === this.currentUser.id;
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${isOwnMessage ? 'own-message' : 'other-message'}`;
        
        const timestamp = new Date(messageData.timestamp).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // Déterminer l'icône du type de message
        let typeIcon = '💬';
        if (messageData.recipient_type === 'department') typeIcon = '🏢';
        else if (messageData.recipient_type === 'user') typeIcon = '👤';
        
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="sender-name">${messageData.username}</span>
                <span class="message-type">${typeIcon}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">
                ${this.formatMessageContent(messageData.message)}
            </div>
        `;
        
        messagesContainer.appendChild(messageElement);
        
        // Supprimer le message de bienvenue s'il existe
        const welcomeMessage = messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
    }
    
    formatMessageContent(content) {
        // Formater le contenu du message (liens, mentions, etc.)
        return content
            .replace(/\n/g, '<br>')
            .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>')
            .replace(/@(\w+)/g, '<span class="mention">@$1</span>');
    }
    
    showSystemMessage(message) {
        const messagesContainer = document.getElementById('chat-messages');
        
        const systemMessage = document.createElement('div');
        systemMessage.className = 'system-message';
        systemMessage.innerHTML = `
            <span class="system-icon">ℹ️</span>
            <span class="system-text">${message}</span>
            <span class="system-time">${new Date().toLocaleTimeString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit'
            })}</span>
        `;
        
        messagesContainer.appendChild(systemMessage);
        this.scrollToBottom();
    }
    
    showErrorMessage(message) {
        const messagesContainer = document.getElementById('chat-messages');
        
        const errorMessage = document.createElement('div');
        errorMessage.className = 'error-message';
        errorMessage.innerHTML = `
            <span class="error-icon">❌</span>
            <span class="error-text">${message}</span>
        `;
        
        messagesContainer.appendChild(errorMessage);
        this.scrollToBottom();
    }
    
    handleTyping() {
        if (!this.isConnected) return;
        
        // Envoyer l'indicateur de frappe
        this.socket.emit('typing_start', { room: this.currentRoom });
        
        // Réinitialiser le timer
        clearTimeout(this.typingTimer);
        this.typingTimer = setTimeout(() => {
            this.stopTyping();
        }, 1000);
    }
    
    stopTyping() {
        if (!this.isConnected) return;
        
        this.socket.emit('typing_stop', { room: this.currentRoom });
        clearTimeout(this.typingTimer);
    }
    
    handleTypingIndicator(data) {
        const typingIndicator = document.getElementById('typing-indicator');
        const typingText = typingIndicator.querySelector('.typing-text');
        
        if (data.typing && data.user_id !== this.currentUser.id) {
            typingText.textContent = `${data.username} est en train d'écrire...`;
            typingIndicator.style.display = 'flex';
            this.scrollToBottom();
        } else {
            typingIndicator.style.display = 'none';
        }
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        
        if (connected) {
            statusIndicator.className = 'status-indicator online';
            statusText.textContent = 'Connecté';
            if (this.recipientType === 'general' || this.recipientId) {
                chatInput.disabled = false;
                sendButton.disabled = false;
            }
        } else {
            statusIndicator.className = 'status-indicator offline';
            statusText.textContent = 'Déconnecté';
            chatInput.disabled = true;
            sendButton.disabled = true;
        }
    }
    
    updateRecipientOptions() {
        // Mettre à jour les options de destinataire quand les données changent
        const recipientType = document.getElementById('recipient-type').value;
        if (recipientType !== 'general') {
            this.handleRecipientTypeChange();
        }
    }
    
    async loadMessageHistory() {
        try {
            // Charger l'historique des messages pour la room actuelle
            const response = await fetch(`http://localhost:5002/api/chat-history?room=${this.currentRoom}&limit=50`);
            if (response.ok) {
                const data = await response.json();
                this.messages = data.messages || [];
                
                // Afficher les messages historiques
                this.clearMessages();
                this.messages.forEach(message => {
                    this.addMessageToDisplay(message);
                });
                
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('Erreur chargement historique:', error);
        }
    }
    
    clearMessages() {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';
    }
    
    scrollToBottom() {
        const messagesContainer = document.getElementById('chat-messages');
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
    }
    
    markMessagesAsRead() {
        // Marquer les messages comme lus (à implémenter si nécessaire)
        console.log('Messages marked as read');
    }
    
    playNotificationSound() {
        // Jouer un son de notification (optionnel)
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Son non disponible, pas grave
            });
        } catch (error) {
            // Pas de son disponible
        }
    }
}

// Initialisation globale
let chatClient = null;

// Démarrage automatique
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chat-container')) {
        chatClient = new ChronoChatClient();
    }
});

// Export pour utilisation externe
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChronoChatClient;
}
