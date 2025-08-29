/**
 * JavaScript Mobile Interface - Sprint 3
 * Actions rapides et interactions optimisées tactile
 */

class MobileInterface {
    constructor() {
        this.currentTimer = null;
        this.activeTaskId = null;
        this.timerInterval = null;
        this.startTime = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupPullToRefresh();
        this.loadActiveTimer();
        this.updateClock();
        this.setupServiceWorker();
    }
    
    setupEventListeners() {
        // Actions rapides sur les tâches
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-start')) {
                this.handleStartTask(e);
            } else if (e.target.closest('.btn-pause')) {
                this.handlePauseTask(e);
            } else if (e.target.closest('.btn-stop')) {
                this.handleStopTask(e);
            } else if (e.target.closest('.btn-note')) {
                this.handleQuickNote(e);
            } else if (e.target.closest('.btn-photo')) {
                this.handlePhotoCapture(e);
            }
        });
        
        // Gestion des modales
        document.addEventListener('click', (e) => {
            if (e.target.closest('.close-modal')) {
                this.closeModal(e.target.closest('.modal'));
            }
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });
        
        // Gestion formulaire note rapide
        const noteForm = document.getElementById('quick-note-form');
        if (noteForm) {
            noteForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveQuickNote();
            });
        }
        
        // Raccourcis clavier
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'Enter':
                        if (this.activeTaskId) {
                            this.toggleTimer();
                        }
                        break;
                    case 'n':
                        e.preventDefault();
                        this.openQuickNote();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.refreshTasks();
                        break;
                }
            }
        });
        
        // Gestion hors ligne
        window.addEventListener('online', () => {
            this.showToast('Connexion rétablie', 'success');
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.showToast('Mode hors ligne activé', 'warning');
        });
    }
    
    // ===== GESTION DES TÂCHES =====
    
    async handleStartTask(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        const taskTitle = taskCard.querySelector('.task-title').textContent;
        
        if (this.activeTaskId && this.activeTaskId !== taskId) {
            const confirm = await this.showConfirm(
                'Une autre tâche est en cours. Voulez-vous l\'arrêter et démarrer celle-ci ?'
            );
            if (!confirm) return;
            await this.stopCurrentTask();
        }
        
        try {
            this.showButtonLoading(e.target);
            
            const response = await this.apiRequest('POST', `/mobile/start-task/${taskId}`);
            
            if (response.success) {
                this.startTimer(taskId, taskTitle);
                this.updateTaskStatus(taskId, 'in-progress');
                this.showToast(`Tâche "${taskTitle}" démarrée`, 'success');
                this.updateBottomActions(taskId);
            } else {
                throw new Error(response.message || 'Erreur lors du démarrage');
            }
        } catch (error) {
            this.showToast('Erreur: ' + error.message, 'error');
        } finally {
            this.hideButtonLoading(e.target);
        }
    }
    
    async handlePauseTask(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        
        try {
            this.showButtonLoading(e.target);
            
            const response = await this.apiRequest('POST', `/mobile/pause-task/${taskId}`);
            
            if (response.success) {
                this.pauseTimer();
                this.showToast('Tâche mise en pause', 'warning');
            } else {
                throw new Error(response.message || 'Erreur lors de la pause');
            }
        } catch (error) {
            this.showToast('Erreur: ' + error.message, 'error');
        } finally {
            this.hideButtonLoading(e.target);
        }
    }
    
    async handleStopTask(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        const taskTitle = taskCard.querySelector('.task-title').textContent;
        
        const confirm = await this.showConfirm(
            `Êtes-vous sûr de vouloir terminer la tâche "${taskTitle}" ?`
        );
        if (!confirm) return;
        
        try {
            this.showButtonLoading(e.target);
            
            const response = await this.apiRequest('POST', `/mobile/stop-task/${taskId}`);
            
            if (response.success) {
                this.stopTimer();
                this.updateTaskStatus(taskId, 'done');
                this.showToast(`Tâche "${taskTitle}" terminée`, 'success');
                this.clearBottomActions();
            } else {
                throw new Error(response.message || 'Erreur lors de l\'arrêt');
            }
        } catch (error) {
            this.showToast('Erreur: ' + error.message, 'error');
        } finally {
            this.hideButtonLoading(e.target);
        }
    }
    
    // ===== GESTION DU TIMER =====
    
    startTimer(taskId, taskTitle) {
        this.activeTaskId = taskId;
        this.startTime = new Date();
        
        // Mettre à jour l'en-tête
        const timerSection = document.querySelector('.active-timer');
        if (timerSection) {
            timerSection.style.display = 'block';
            document.querySelector('.timer-task').textContent = taskTitle;
        }
        
        // Démarrer le timer
        this.timerInterval = setInterval(() => {
            this.updateTimerDisplay();
        }, 1000);
        
        // Sauvegarder dans le localStorage
        localStorage.setItem('activeTask', JSON.stringify({
            taskId,
            taskTitle,
            startTime: this.startTime.toISOString()
        }));
    }
    
    pauseTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        
        // Sauvegarder le temps écoulé
        const elapsed = this.getElapsedTime();
        localStorage.setItem('pausedTime', elapsed.toString());
    }
    
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        
        this.activeTaskId = null;
        this.startTime = null;
        
        // Cacher l'en-tête timer
        const timerSection = document.querySelector('.active-timer');
        if (timerSection) {
            timerSection.style.display = 'none';
        }
        
        // Nettoyer le localStorage
        localStorage.removeItem('activeTask');
        localStorage.removeItem('pausedTime');
    }
    
    updateTimerDisplay() {
        const elapsed = this.getElapsedTime();
        const hours = Math.floor(elapsed / 3600);
        const minutes = Math.floor((elapsed % 3600) / 60);
        const seconds = elapsed % 60;
        
        const display = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        const timerDisplay = document.querySelector('.timer-display');
        if (timerDisplay) {
            timerDisplay.textContent = display;
        }
    }
    
    getElapsedTime() {
        if (!this.startTime) return 0;
        
        const now = new Date();
        const elapsed = Math.floor((now - this.startTime) / 1000);
        const pausedTime = parseInt(localStorage.getItem('pausedTime') || '0');
        
        return elapsed + pausedTime;
    }
    
    loadActiveTimer() {
        const activeTask = localStorage.getItem('activeTask');
        if (activeTask) {
            try {
                const task = JSON.parse(activeTask);
                this.activeTaskId = task.taskId;
                this.startTime = new Date(task.startTime);
                
                // Redémarrer le timer
                this.timerInterval = setInterval(() => {
                    this.updateTimerDisplay();
                }, 1000);
                
                // Afficher l'en-tête
                const timerSection = document.querySelector('.active-timer');
                if (timerSection) {
                    timerSection.style.display = 'block';
                    document.querySelector('.timer-task').textContent = task.taskTitle;
                }
                
                this.updateBottomActions(task.taskId);
            } catch (error) {
                console.error('Erreur lors du chargement du timer:', error);
                localStorage.removeItem('activeTask');
            }
        }
    }
    
    // ===== NOTES RAPIDES =====
    
    handleQuickNote(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        const taskTitle = taskCard.querySelector('.task-title').textContent;
        
        this.openQuickNote(taskId, taskTitle);
    }
    
    openQuickNote(taskId = null, taskTitle = '') {
        const modal = document.getElementById('quick-note-modal');
        if (!modal) {
            this.createQuickNoteModal();
            return this.openQuickNote(taskId, taskTitle);
        }
        
        // Pré-remplir les données
        if (taskId) {
            modal.dataset.taskId = taskId;
            modal.querySelector('.quick-note-title').textContent = `Note - ${taskTitle}`;
        }
        
        modal.style.display = 'flex';
        modal.querySelector('.note-input').focus();
    }
    
    async saveQuickNote() {
        const modal = document.getElementById('quick-note-modal');
        const taskId = modal.dataset.taskId;
        const noteText = modal.querySelector('.note-input').value.trim();
        
        if (!noteText) {
            this.showToast('Veuillez saisir une note', 'warning');
            return;
        }
        
        try {
            const saveBtn = modal.querySelector('.save-note-btn');
            this.showButtonLoading(saveBtn);
            
            const response = await this.apiRequest('POST', `/mobile/add-note/${taskId}`, {
                note: noteText
            });
            
            if (response.success) {
                this.showToast('Note ajoutée avec succès', 'success');
                this.closeModal(modal);
                modal.querySelector('.note-input').value = '';
            } else {
                throw new Error(response.message || 'Erreur lors de la sauvegarde');
            }
        } catch (error) {
            this.showToast('Erreur: ' + error.message, 'error');
        } finally {
            const saveBtn = modal.querySelector('.save-note-btn');
            this.hideButtonLoading(saveBtn);
        }
    }
    
    // ===== CAPTURE PHOTO =====
    
    async handlePhotoCapture(e) {
        const taskCard = e.target.closest('.task-card');
        const taskId = taskCard.dataset.taskId;
        
        try {
            // Vérifier si l'appareil supporte la capture photo
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                this.showFileSelector(taskId);
                return;
            }
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' } 
            });
            
            this.openCameraModal(stream, taskId);
        } catch (error) {
            console.log('Camera non disponible, utilisation du sélecteur de fichier');
            this.showFileSelector(taskId);
        }
    }
    
    showFileSelector(taskId) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.capture = 'environment';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.uploadPhoto(file, taskId);
            }
        };
        
        input.click();
    }
    
    async uploadPhoto(file, taskId) {
        try {
            const formData = new FormData();
            formData.append('photo', file);
            
            const response = await fetch(`/mobile/upload-photo/${taskId}`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Photo ajoutée avec succès', 'success');
            } else {
                throw new Error(result.message || 'Erreur lors de l\'upload');
            }
        } catch (error) {
            this.showToast('Erreur: ' + error.message, 'error');
        }
    }
    
    // ===== INTERFACE UTILISATEUR =====
    
    updateTaskStatus(taskId, status) {
        const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);
        if (taskCard) {
            taskCard.classList.remove('pending', 'assigned', 'in-progress', 'done');
            taskCard.classList.add(status);
            
            const statusIndicator = taskCard.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.classList.remove('pending', 'assigned', 'in-progress', 'done');
                statusIndicator.classList.add(status);
            }
            
            // Mettre à jour les boutons
            this.updateTaskButtons(taskCard, status);
        }
    }
    
    updateTaskButtons(taskCard, status) {
        const actions = taskCard.querySelector('.quick-actions');
        if (!actions) return;
        
        // Nettoyer les boutons existants
        actions.innerHTML = '';
        
        // Ajouter les boutons selon le statut
        switch (status) {
            case 'pending':
            case 'assigned':
                actions.innerHTML = `
                    <button class="action-btn btn-start">
                        <span>▶️</span> Démarrer
                    </button>
                    <button class="action-btn btn-note">
                        <span>📝</span> Note
                    </button>
                `;
                break;
            case 'in-progress':
                actions.innerHTML = `
                    <button class="action-btn btn-pause">
                        <span>⏸️</span> Pause
                    </button>
                    <button class="action-btn btn-stop">
                        <span>⏹️</span> Terminer
                    </button>
                    <button class="action-btn btn-note">
                        <span>📝</span> Note
                    </button>
                    <button class="action-btn btn-photo">
                        <span>📷</span> Photo
                    </button>
                `;
                break;
            case 'done':
                actions.innerHTML = `
                    <button class="action-btn btn-secondary" disabled>
                        <span>✅</span> Terminé
                    </button>
                `;
                break;
        }
    }
    
    updateBottomActions(taskId) {
        const bottomActions = document.querySelector('.mobile-bottom-actions');
        if (bottomActions) {
            bottomActions.innerHTML = `
                <div class="bottom-actions-grid">
                    <button class="bottom-action-btn bottom-btn-primary" onclick="mobileInterface.toggleTimer()">
                        <span>⏸️</span> Pause
                    </button>
                    <button class="bottom-action-btn bottom-btn-secondary" onclick="mobileInterface.openQuickNote('${taskId}')">
                        <span>📝</span> Note Rapide
                    </button>
                </div>
            `;
        }
    }
    
    clearBottomActions() {
        const bottomActions = document.querySelector('.mobile-bottom-actions');
        if (bottomActions) {
            bottomActions.innerHTML = `
                <div class="bottom-actions-grid">
                    <button class="bottom-action-btn bottom-btn-primary" onclick="mobileInterface.refreshTasks()">
                        <span>🔄</span> Actualiser
                    </button>
                    <button class="bottom-action-btn bottom-btn-secondary" onclick="mobileInterface.openQuickNote()">
                        <span>📝</span> Note Générale
                    </button>
                </div>
            `;
        }
    }
    
    // ===== GESTION DES MODALES =====
    
    closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    createQuickNoteModal() {
        const modal = document.createElement('div');
        modal.id = 'quick-note-modal';
        modal.className = 'quick-note-modal';
        modal.style.display = 'none';
        
        modal.innerHTML = `
            <div class="quick-note-content">
                <div class="quick-note-header">
                    <h3 class="quick-note-title">Ajouter une note</h3>
                    <button class="close-modal" type="button">&times;</button>
                </div>
                <form id="quick-note-form">
                    <textarea class="note-input" placeholder="Saisissez votre note ici..." required></textarea>
                    <div class="note-actions">
                        <button type="submit" class="save-note-btn">Sauvegarder</button>
                        <button type="button" class="cancel-note-btn close-modal">Annuler</button>
                    </div>
                </form>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    // ===== NOTIFICATIONS =====
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Animation d'entrée
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Suppression automatique
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
    
    async showConfirm(message) {
        return new Promise((resolve) => {
            const result = confirm(message);
            resolve(result);
        });
    }
    
    // ===== UTILITAIRES =====
    
    showButtonLoading(button) {
        button.classList.add('loading');
        button.disabled = true;
    }
    
    hideButtonLoading(button) {
        button.classList.remove('loading');
        button.disabled = false;
    }
    
    async apiRequest(method, url, data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    updateClock() {
        const clockElement = document.querySelector('.current-time');
        if (clockElement) {
            setInterval(() => {
                const now = new Date();
                clockElement.textContent = now.toLocaleTimeString('fr-FR', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }, 1000);
        }
    }
    
    async refreshTasks() {
        try {
            const refreshBtn = document.querySelector('.bottom-btn-primary');
            if (refreshBtn) {
                this.showButtonLoading(refreshBtn);
            }
            
            window.location.reload();
        } catch (error) {
            this.showToast('Erreur lors de l\'actualisation', 'error');
        }
    }
    
    toggleTimer() {
        if (this.activeTaskId) {
            if (this.timerInterval) {
                this.pauseTimer();
                this.showToast('Timer en pause', 'warning');
            } else {
                // Reprendre le timer
                this.timerInterval = setInterval(() => {
                    this.updateTimerDisplay();
                }, 1000);
                this.showToast('Timer repris', 'success');
            }
        }
    }
    
    // ===== PULL TO REFRESH =====
    
    setupPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let pullDistance = 0;
        let isPulling = false;
        
        const container = document.querySelector('.mobile-container');
        if (!container) return;
        
        container.addEventListener('touchstart', (e) => {
            if (container.scrollTop === 0) {
                startY = e.touches[0].clientY;
                isPulling = true;
            }
        }, { passive: true });
        
        container.addEventListener('touchmove', (e) => {
            if (!isPulling) return;
            
            currentY = e.touches[0].clientY;
            pullDistance = currentY - startY;
            
            if (pullDistance > 0 && pullDistance < 100) {
                e.preventDefault();
                // Afficher l'indicateur de pull to refresh
                this.showPullToRefresh(pullDistance);
            }
        }, { passive: false });
        
        container.addEventListener('touchend', () => {
            if (isPulling && pullDistance > 60) {
                this.refreshTasks();
            }
            
            isPulling = false;
            pullDistance = 0;
            this.hidePullToRefresh();
        }, { passive: true });
    }
    
    showPullToRefresh(distance) {
        let indicator = document.querySelector('.pull-to-refresh');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'pull-to-refresh';
            indicator.innerHTML = '🔄 Tirez pour actualiser';
            document.querySelector('.mobile-container').prepend(indicator);
        }
        
        if (distance > 60) {
            indicator.classList.add('active');
            indicator.innerHTML = '📱 Relâchez pour actualiser';
        } else {
            indicator.classList.remove('active');
            indicator.innerHTML = '🔄 Tirez pour actualiser';
        }
    }
    
    hidePullToRefresh() {
        const indicator = document.querySelector('.pull-to-refresh');
        if (indicator) {
            indicator.classList.remove('active');
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.parentNode.removeChild(indicator);
                }
            }, 300);
        }
    }
    
    // ===== SERVICE WORKER =====
    
    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker enregistré');
            } catch (error) {
                console.log('Erreur Service Worker:', error);
            }
        }
    }
    
    async syncOfflineData() {
        // Synchroniser les données hors ligne si nécessaire
        const offlineData = localStorage.getItem('offlineData');
        if (offlineData) {
            try {
                const data = JSON.parse(offlineData);
                // Envoyer les données au serveur
                await this.apiRequest('POST', '/mobile/sync-offline', data);
                localStorage.removeItem('offlineData');
                this.showToast('Données synchronisées', 'success');
            } catch (error) {
                console.error('Erreur synchronisation:', error);
            }
        }
    }
}

// Initialisation
let mobileInterface;

document.addEventListener('DOMContentLoaded', () => {
    mobileInterface = new MobileInterface();
});

// Export pour utilisation externe
window.mobileInterface = mobileInterface;
