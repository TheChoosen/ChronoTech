/**
 * Module JavaScript pour les interventions ChronoTech
 * Fonctionnalités IA, capture média, collaboration en temps réel
 */

class InterventionManager {
    constructor() {
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.isRecording = false;
        this.camera = null;
        this.currentWorkOrderId = null;
        this.aiSuggestions = [];
        this.translationCache = new Map();
        
        this.init();
    }

    init() {
        console.log('🤖 Initialisation du gestionnaire d\'interventions IA');
        this.bindEvents();
        this.initializeAiFeatures();
        this.setupRealTimeUpdates();
    }

    bindEvents() {
        // Filtres intelligents
        this.setupSmartFilters();
        
        // Actions rapides
        this.setupQuickActions();
        
        // Capture média
        this.setupMediaCapture();
        
        // Interface vocale
        this.setupVoiceInterface();
        
        // Assistant IA
        this.setupAiAssistant();
    }

    /**
     * FILTRES INTELLIGENTS AVEC IA
     */
    setupSmartFilters() {
        const filters = {
            priority: document.getElementById('priority-filter'),
            status: document.getElementById('status-filter'),
            technician: document.getElementById('technician-filter'),
            search: document.getElementById('search-filter'),
            aiToggle: document.getElementById('ai-filter')
        };

        // Filtrage en temps réel
        Object.entries(filters).forEach(([key, element]) => {
            if (!element) return;

            const eventType = key === 'search' ? 'input' : 'change';
            element.addEventListener(eventType, this.debounce(() => {
                this.applySmartFilters();
            }, 300));
        });

        // Tri IA automatique
        if (filters.aiToggle) {
            filters.aiToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.applyAiSorting();
                } else {
                    this.resetSorting();
                }
            });
        }
    }

    applySmartFilters() {
        const cards = document.querySelectorAll('.intervention-card');
        const filters = this.getFilterValues();
        
        let visibleCount = 0;
        
        cards.forEach(card => {
            const isVisible = this.matchesFilters(card, filters);
            card.style.display = isVisible ? 'block' : 'none';
            if (isVisible) visibleCount++;
        });

        // Mise à jour du compteur
        this.updateFilterStats(visibleCount, cards.length);
        
        // Suggestions IA basées sur les filtres
        if (filters.search && filters.search.length > 2) {
            this.generateSearchSuggestions(filters.search);
        }
    }

    matchesFilters(card, filters) {
        const data = card.dataset;
        
        return (
            (!filters.priority || data.priority === filters.priority) &&
            (!filters.status || data.status === filters.status) &&
            (!filters.technician || data.technician === filters.technician) &&
            (!filters.search || data.search.includes(filters.search.toLowerCase()))
        );
    }

    getFilterValues() {
        return {
            priority: document.getElementById('priority-filter')?.value || '',
            status: document.getElementById('status-filter')?.value || '',
            technician: document.getElementById('technician-filter')?.value || '',
            search: document.getElementById('search-filter')?.value || ''
        };
    }

    applyAiSorting() {
        const grid = document.getElementById('interventions-grid');
        if (!grid) return;

        const cards = Array.from(grid.children);
        
        // Algorithme de tri IA basé sur priorité, urgence, et patterns
        cards.sort((a, b) => {
            const scoreA = this.calculateAiScore(a);
            const scoreB = this.calculateAiScore(b);
            return scoreB - scoreA;
        });

        // Réorganisation du DOM
        cards.forEach(card => grid.appendChild(card));
        
        // Animation de tri
        this.animateSorting(cards);
        
        this.showNotification('🤖 Tri IA appliqué - Interventions optimisées', 'success');
    }

    calculateAiScore(card) {
        const data = card.dataset;
        
        // Poids des priorités
        const priorityWeights = { urgent: 100, high: 75, medium: 50, low: 25 };
        
        // Poids des statuts
        const statusWeights = { 
            in_progress: 80, 
            pending: 60, 
            scheduled: 40, 
            completed: 0 
        };
        
        // Facteurs temporels (plus ancien = plus urgent)
        const timeElement = card.querySelector('.scheduled-time');
        const timeWeight = timeElement ? this.calculateTimeUrgency(timeElement.textContent) : 0;
        
        // Score IA basé sur l'historique
        const aiWeight = this.getAiHistoryWeight(data);
        
        return (priorityWeights[data.priority] || 0) + 
               (statusWeights[data.status] || 0) + 
               timeWeight + 
               aiWeight;
    }

    calculateTimeUrgency(timeText) {
        // Logique de calcul d'urgence temporelle
        // Plus c'est proche, plus c'est urgent
        try {
            const scheduledDate = new Date(timeText.replace('Planifié: ', ''));
            const now = new Date();
            const diffHours = (scheduledDate - now) / (1000 * 60 * 60);
            
            if (diffHours < 2) return 50;
            if (diffHours < 24) return 30;
            if (diffHours < 48) return 15;
            return 0;
        } catch {
            return 0;
        }
    }

    getAiHistoryWeight(data) {
        // Poids basé sur l'historique IA (simulé pour l'instant)
        // TODO: Intégrer avec le backend pour récupérer les données historiques
        return Math.random() * 20; // Simulation
    }

    /**
     * ACTIONS RAPIDES
     */
    setupQuickActions() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-action')) {
                e.preventDefault();
                this.handleQuickAction(e.target);
            }
            
            if (e.target.classList.contains('ai-analyze')) {
                e.preventDefault();
                this.showAiAnalysis(e.target.dataset.workOrder);
            }
            
            if (e.target.classList.contains('voice-note')) {
                e.preventDefault();
                this.startQuickVoiceNote(e.target.dataset.workOrder);
            }
            
            if (e.target.classList.contains('photo-capture')) {
                e.preventDefault();
                this.openQuickPhotoCapture(e.target.dataset.workOrder);
            }
        });
    }

    async handleQuickAction(button) {
        const action = button.dataset.action;
        const workOrderId = button.dataset.workOrder;
        
        // Indication visuelle
        button.disabled = true;
        const originalText = button.textContent;
        button.textContent = '⏳ Traitement...';
        
        try {
            const response = await fetch(`/interventions/${workOrderId}/quick_actions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `action=${action}`
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                
                // Mise à jour de l'interface
                await this.updateInterventionCard(workOrderId, action);
                
                // Suggestions IA post-action
                this.generatePostActionSuggestions(action, workOrderId);
                
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Erreur de connexion', 'error');
            console.error('Erreur action rapide:', error);
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    async updateInterventionCard(workOrderId, action) {
        const card = document.querySelector(`[data-work-order="${workOrderId}"]`)?.closest('.intervention-card');
        if (!card) return;

        // Mise à jour visuelle selon l'action
        switch (action) {
            case 'start_work':
                this.updateCardStatus(card, 'in_progress');
                break;
            case 'complete_work':
                this.updateCardStatus(card, 'completed');
                break;
        }
        
        // Animation de mise à jour
        card.style.transform = 'scale(1.02)';
        setTimeout(() => {
            card.style.transform = '';
        }, 300);
    }

    updateCardStatus(card, newStatus) {
        const statusBadge = card.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `status-badge ${newStatus}`;
            statusBadge.textContent = this.getStatusText(newStatus);
        }
        card.dataset.status = newStatus;
    }

    getStatusText(status) {
        const statusMap = {
            pending: '⏳ En attente',
            in_progress: '⚡ En cours',
            completed: '✅ Terminé',
            scheduled: '📅 Planifié'
        };
        return statusMap[status] || status;
    }

    /**
     * CAPTURE MÉDIA AVEC IA
     */
    setupMediaCapture() {
        // Upload de fichiers
        const fileInput = document.getElementById('file-upload');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileUpload(e.target.files[0]);
            });
        }

        // Drag & Drop
        this.setupDragDrop();
    }

    setupDragDrop() {
        const dropZones = document.querySelectorAll('.intervention-card, .media-gallery');
        
        dropZones.forEach(zone => {
            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                zone.classList.add('drag-over');
            });
            
            zone.addEventListener('dragleave', () => {
                zone.classList.remove('drag-over');
            });
            
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('drag-over');
                
                const files = Array.from(e.dataTransfer.files);
                const workOrderId = zone.dataset.workOrder || this.currentWorkOrderId;
                
                files.forEach(file => this.handleFileUpload(file, workOrderId));
            });
        });
    }

    async handleFileUpload(file, workOrderId = null) {
        if (!file || !workOrderId) {
            this.showNotification('Fichier ou intervention non spécifiés', 'error');
            return;
        }

        // Validation du type de fichier
        if (!this.isValidFileType(file)) {
            this.showNotification('Type de fichier non autorisé', 'error');
            return;
        }

        // Indicateur de progression
        const progressId = this.showUploadProgress(file.name);
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`/interventions/${workOrderId}/upload_media`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`📷 ${file.type.includes('audio') ? 'Audio' : 'Fichier'} uploadé avec succès`, 'success');
                
                // Transcription automatique pour l'audio
                if (file.type.includes('audio') && data.transcription) {
                    this.displayTranscription(data.transcription, data.translations);
                }
                
                // Mise à jour de la galerie
                this.refreshMediaGallery(workOrderId);
                
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Erreur d\'upload', 'error');
            console.error('Erreur upload:', error);
        } finally {
            this.hideUploadProgress(progressId);
        }
    }

    isValidFileType(file) {
        const allowedTypes = [
            'image/jpeg', 'image/png', 'image/gif',
            'video/mp4', 'video/mov',
            'audio/mp3', 'audio/wav', 'audio/m4a',
            'application/pdf'
        ];
        return allowedTypes.includes(file.type);
    }

    /**
     * INTERFACE VOCALE AVEC IA
     */
    setupVoiceInterface() {
        // Vérification du support du navigateur
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('Capture audio non supportée par ce navigateur');
            return;
        }

        // Reconnaissance vocale continue (si supportée)
        this.setupSpeechRecognition();
    }

    setupSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            
            this.speechRecognition.continuous = true;
            this.speechRecognition.interimResults = true;
            this.speechRecognition.lang = 'fr-FR';
            
            this.speechRecognition.onresult = (event) => {
                this.handleSpeechResult(event);
            };
            
            this.speechRecognition.onerror = (event) => {
                console.error('Erreur reconnaissance vocale:', event.error);
                this.showNotification('Erreur de reconnaissance vocale', 'error');
            };
        }
    }

    async startVoiceRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.mediaRecorder = new MediaRecorder(stream);
            this.recordedChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                this.processVoiceRecording();
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            
            this.updateVoiceUI(true);
            
        } catch (error) {
            console.error('Erreur accès microphone:', error);
            this.showNotification('Impossible d\'accéder au microphone', 'error');
        }
    }

    stopVoiceRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateVoiceUI(false);
        }
    }

    async processVoiceRecording() {
        const audioBlob = new Blob(this.recordedChunks, { type: 'audio/wav' });
        
        // Upload et transcription
        const formData = new FormData();
        formData.append('audio_data', audioBlob, 'voice_note.wav');
        
        try {
            const response = await fetch(`/interventions/${this.currentWorkOrderId}/voice_note`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayTranscription(data.transcription, data.confidence);
                this.showNotification('🎤 Transcription terminée', 'success');
            } else {
                this.showNotification('Erreur de transcription', 'error');
            }
        } catch (error) {
            console.error('Erreur transcription:', error);
            this.showNotification('Erreur de transcription', 'error');
        }
    }

    updateVoiceUI(isRecording) {
        const recordBtn = document.getElementById('record-btn');
        const stopBtn = document.getElementById('stop-btn');
        const status = document.getElementById('voice-status');
        
        if (recordBtn) recordBtn.style.display = isRecording ? 'none' : 'inline-block';
        if (stopBtn) stopBtn.style.display = isRecording ? 'inline-block' : 'none';
        
        if (status) {
            status.innerHTML = isRecording 
                ? '<span class="recording">🔴 Enregistrement en cours...</span>'
                : '<span class="ready">Prêt pour l\'enregistrement</span>';
        }
    }

    displayTranscription(transcription, confidence) {
        const preview = document.getElementById('transcription-preview');
        if (!preview) return;
        
        const textElement = preview.querySelector('.transcription-text');
        if (textElement) {
            textElement.textContent = transcription;
        }
        
        preview.style.display = 'block';
        
        // Mise à jour du statut avec confiance
        const status = document.getElementById('voice-status');
        if (status && confidence) {
            status.innerHTML = `<span class="success">✅ Transcription terminée (${Math.round(confidence * 100)}%)</span>`;
        }
    }

    /**
     * ASSISTANT IA
     */
    setupAiAssistant() {
        this.loadAiSuggestions();
        
        // Mise à jour périodique des suggestions
        setInterval(() => {
            this.refreshAiSuggestions();
        }, 30000); // Toutes les 30 secondes
    }

    async loadAiSuggestions(workOrderId = null) {
        if (!workOrderId && !this.currentWorkOrderId) return;
        
        const id = workOrderId || this.currentWorkOrderId;
        
        try {
            const response = await fetch(`/interventions/ai/suggestions/${id}`);
            const data = await response.json();
            
            if (data.success) {
                this.aiSuggestions = data.suggestions;
                this.displayAiSuggestions(data.suggestions);
            }
        } catch (error) {
            console.error('Erreur chargement suggestions IA:', error);
        }
    }

    displayAiSuggestions(suggestions) {
        const container = document.getElementById('contextual-suggestions');
        if (!container) return;
        
        container.innerHTML = suggestions.map(suggestion => `
            <div class="suggestion-item ${suggestion.type}">
                <div class="suggestion-header">
                    <strong>${suggestion.title}</strong>
                    <span class="confidence">${Math.round(suggestion.confidence * 100)}%</span>
                </div>
                <div class="suggestion-content">
                    ${suggestion.content}
                </div>
                <div class="suggestion-actions">
                    <button class="clay-btn clay-btn-ghost" onclick="interventionManager.applySuggestion('${suggestion.type}', '${encodeURIComponent(suggestion.content)}')">
                        ✅ Appliquer
                    </button>
                </div>
            </div>
        `).join('');
    }

    applySuggestion(type, content) {
        const decodedContent = decodeURIComponent(content);
        
        switch (type) {
            case 'part_recommendation':
                this.applyPartSuggestion(decodedContent);
                break;
            case 'maintenance_tip':
                this.applyMaintenanceTip(decodedContent);
                break;
            case 'time_estimate':
                this.applyTimeEstimate(decodedContent);
                break;
            default:
                this.addSuggestionAsNote(decodedContent);
        }
        
        this.showNotification('💡 Suggestion IA appliquée', 'success');
    }

    addSuggestionAsNote(content) {
        const noteTextarea = document.getElementById('note-content');
        if (noteTextarea) {
            const currentContent = noteTextarea.value;
            const newContent = currentContent ? `${currentContent}\n\n🤖 Suggestion IA: ${content}` : `🤖 Suggestion IA: ${content}`;
            noteTextarea.value = newContent;
            noteTextarea.focus();
        }
    }

    /**
     * MISE À JOUR EN TEMPS RÉEL
     */
    setupRealTimeUpdates() {
        // WebSocket ou polling pour les mises à jour temps réel
        // TODO: Implémenter WebSocket pour les notifications temps réel
        this.startPolling();
    }

    startPolling() {
        setInterval(() => {
            this.checkForUpdates();
        }, 60000); // Toutes les minutes
    }

    async checkForUpdates() {
        // Vérification des nouvelles données
        // TODO: Implémenter la vérification des mises à jour
    }

    /**
     * UTILITIES
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    showNotification(message, type = 'info') {
        // Supprimer les notifications existantes
        document.querySelectorAll('.notification').forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto-suppression
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    showUploadProgress(filename) {
        const progressId = `progress-${Date.now()}`;
        const progress = document.createElement('div');
        progress.id = progressId;
        progress.className = 'upload-progress';
        progress.innerHTML = `
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            <span class="progress-text">Upload: ${filename}</span>
        `;
        
        document.body.appendChild(progress);
        return progressId;
    }

    hideUploadProgress(progressId) {
        const element = document.getElementById(progressId);
        if (element) {
            element.remove();
        }
    }

    refreshMediaGallery(workOrderId) {
        // TODO: Recharger la galerie média
        window.location.reload(); // Solution temporaire
    }

    animateSorting(cards) {
        cards.forEach((card, index) => {
            card.style.animation = `fadeInUp 0.3s ease ${index * 0.1}s both`;
        });
    }

    generateSearchSuggestions(searchTerm) {
        // TODO: Générer des suggestions de recherche basées sur l'IA
        console.log('🔍 Génération de suggestions pour:', searchTerm);
    }

    generatePostActionSuggestions(action, workOrderId) {
        // TODO: Générer des suggestions contextuelles après une action
        console.log('💡 Génération de suggestions post-action:', action, workOrderId);
    }

    updateFilterStats(visible, total) {
        // TODO: Mettre à jour les statistiques de filtrage
        console.log(`📊 Filtres: ${visible}/${total} interventions visibles`);
    }

    resetSorting() {
        // TODO: Remettre l'ordre original
        console.log('🔄 Remise à zéro du tri');
    }

    refreshAiSuggestions() {
        if (this.currentWorkOrderId) {
            this.loadAiSuggestions(this.currentWorkOrderId);
        }
    }
}

// Fonctions globales pour la compatibilité avec les templates
function toggleRecording() {
    if (window.interventionManager.isRecording) {
        window.interventionManager.stopVoiceRecording();
    } else {
        window.interventionManager.startVoiceRecording();
    }
}

function expandDescription(btn) {
    const card = btn.closest('.intervention-card');
    const description = card.querySelector('.description-text');
    description.style.webkitLineClamp = 'unset';
    description.style.lineClamp = 'unset';
    btn.style.display = 'none';
}

function closeQuickCapture() {
    const overlay = document.getElementById('quick-capture-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function closeAiAnalysis() {
    const modal = document.getElementById('ai-analysis-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function showAiAnalysis(workOrderId) {
    window.interventionManager.loadAiSuggestions(workOrderId);
    const modal = document.getElementById('ai-analysis-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function openQuickCapture(type, workOrderId) {
    window.interventionManager.currentWorkOrderId = workOrderId;
    const overlay = document.getElementById('quick-capture-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function startVoiceCapture(workOrderId) {
    window.interventionManager.currentWorkOrderId = workOrderId;
    window.interventionManager.startVoiceRecording();
}

// Initialisation globale
document.addEventListener('DOMContentLoaded', function() {
    window.interventionManager = new InterventionManager();
    console.log('🚀 Gestionnaire d\'interventions ChronoTech initialisé');
});

// Export pour utilisation en module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InterventionManager;
}
