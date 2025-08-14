/**
 * Module JavaScript pour les détails d'intervention
 * Interface complète avec IA, capture photo/vidéo, transcription temps réel
 */

class InterventionDetailsManager {
    constructor(workOrderId) {
        this.workOrderId = workOrderId;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.isRecording = false;
        this.camera = null;
        this.photoStream = null;
        this.speechRecognition = null;
        this.isListening = false;
        this.translationCache = new Map();
        this.aiContext = {
            notes: [],
            media: [],
            suggestions: []
        };
        
        this.init();
    }

    init() {
        console.log('🔧 Initialisation des détails d\'intervention:', this.workOrderId);
        this.bindEvents();
        this.initializeTabs();
        this.setupVoiceInterface();
        this.setupPhotoCapture();
        this.setupFileUpload();
        this.loadAiContext();
        this.startRealTimeUpdates();
    }

    bindEvents() {
        // Actions principales
        this.setupMainActions();
        
        // Gestion des notes
        this.setupNoteInterface();
        
        // Médias
        this.setupMediaInterface();
        
        // IA
        this.setupAiInterface();
        
        // Outils rapides
        this.setupQuickTools();
    }

    /**
     * GESTION DES ONGLETS
     */
    initializeTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
                
                // Actions spéciales selon l'onglet
                switch(tabName) {
                    case 'voice':
                        this.prepareVoiceInterface();
                        break;
                    case 'ai':
                        this.loadAiSuggestions();
                        break;
                }
            });
        });
    }

    switchTab(tabName) {
        // Mise à jour des boutons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');
        
        // Mise à jour du contenu
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.querySelector(`.tab-content[data-tab="${tabName}"]`)?.classList.add('active');
    }

    /**
     * ACTIONS PRINCIPALES
     */
    setupMainActions() {
        // Actions rapides depuis l'en-tête
        document.addEventListener('click', (e) => {
            if (e.target.onclick) return; // Éviter les doubles événements
            
            const buttonText = e.target.textContent.trim();
            
            if (buttonText.includes('Démarrer l\'intervention')) {
                this.quickAction('start_work');
            } else if (buttonText.includes('Terminer l\'intervention')) {
                this.quickAction('complete_work');
            } else if (buttonText.includes('Note vocale')) {
                this.startVoiceNote();
            } else if (buttonText.includes('Photo')) {
                this.openPhotoCapture();
            } else if (buttonText.includes('Assistant IA')) {
                this.openAiAssistant();
            }
        });
    }

    async quickAction(action) {
        const actionMap = {
            start_work: { text: '⏳ Démarrage...', success: '✅ Intervention démarrée' },
            complete_work: { text: '⏳ Finalisation...', success: '✅ Intervention terminée' }
        };

        const config = actionMap[action];
        this.showNotification(config.text, 'info');

        try {
            const response = await fetch(`/interventions/${this.workOrderId}/quick_actions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `action=${action}`
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(config.success, 'success');
                this.updateInterfaceAfterAction(action);
                this.generatePostActionSuggestions(action);
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Erreur de connexion', 'error');
            console.error('Erreur action rapide:', error);
        }
    }

    updateInterfaceAfterAction(action) {
        const header = document.querySelector('.intervention-header');
        
        switch(action) {
            case 'start_work':
                // Mise à jour du statut
                const statusBadge = header.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge in_progress';
                    statusBadge.textContent = '⚡ En cours';
                }
                // Mise à jour des boutons
                this.updateActionButtons('in_progress');
                break;
                
            case 'complete_work':
                const completedBadge = header.querySelector('.status-badge');
                if (completedBadge) {
                    completedBadge.className = 'status-badge completed';
                    completedBadge.textContent = '✅ Terminé';
                }
                this.updateActionButtons('completed');
                break;
        }
    }

    updateActionButtons(status) {
        const actionButtons = document.querySelector('.header-actions');
        if (!actionButtons) return;

        const buttons = actionButtons.querySelectorAll('.clay-btn');
        buttons.forEach(btn => {
            if (btn.textContent.includes('Démarrer') || btn.textContent.includes('Terminer')) {
                if (status === 'completed') {
                    btn.style.display = 'none';
                } else if (status === 'in_progress') {
                    if (btn.textContent.includes('Démarrer')) {
                        btn.style.display = 'none';
                    } else {
                        btn.style.display = 'inline-block';
                    }
                }
            }
        });
    }

    /**
     * INTERFACE DE NOTES AVEC IA
     */
    setupNoteInterface() {
        // Bouton d'ajout de note
        const addNoteBtn = document.querySelector('[onclick="addNote()"]');
        if (addNoteBtn) {
            addNoteBtn.removeAttribute('onclick');
            addNoteBtn.addEventListener('click', () => this.addNote());
        }

        // Traduction automatique
        const translateBtn = document.querySelector('[onclick="translateNote()"]');
        if (translateBtn) {
            translateBtn.removeAttribute('onclick');
            translateBtn.addEventListener('click', () => this.translateCurrentNote());
        }

        // Auto-sauvegarde
        const noteTextarea = document.getElementById('note-content');
        if (noteTextarea) {
            noteTextarea.addEventListener('input', this.debounce(() => {
                this.autoSaveNote();
            }, 2000));
        }
    }

    async addNote() {
        const content = document.getElementById('note-content')?.value.trim();
        const noteType = document.getElementById('note-type')?.value || 'private';
        
        if (!content) {
            this.showNotification('Veuillez saisir le contenu de la note', 'error');
            return;
        }

        // Indication visuelle
        this.showNoteProgress('Ajout de la note...');

        try {
            const formData = new FormData();
            formData.append('content', content);
            formData.append('note_type', noteType);
            
            const response = await fetch(`/interventions/${this.workOrderId}/add_note`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('📝 Note ajoutée avec succès', 'success');
                
                // Nettoyage du formulaire
                document.getElementById('note-content').value = '';
                
                // Ajout de la note à l'interface
                this.addNoteToList(data.note);
                
                // Mise à jour du contexte IA
                this.aiContext.notes.push(data.note);
                this.updateAiSuggestions();
                
                // Traductions automatiques
                if (data.translations) {
                    this.displayTranslations(data.translations);
                }
                
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Erreur lors de l\'ajout de la note', 'error');
            console.error('Erreur note:', error);
        } finally {
            this.hideNoteProgress();
        }
    }

    addNoteToList(note) {
        const notesList = document.querySelector('.notes-list');
        if (!notesList) return;

        const noteElement = document.createElement('div');
        noteElement.className = `note-item clay-card-nested ${note.note_type}`;
        noteElement.innerHTML = `
            <div class="note-header">
                <div class="note-meta">
                    <strong>${note.technician_name}</strong>
                    <span class="note-date">${this.formatDate(note.created_at)}</span>
                    <span class="note-type-badge ${note.note_type}">
                        ${this.getNoteTypeIcon(note.note_type)} ${note.note_type}
                    </span>
                </div>
            </div>
            <div class="note-content">${note.content}</div>
        `;

        notesList.insertBefore(noteElement, notesList.firstChild);
        
        // Animation d'apparition
        noteElement.style.opacity = '0';
        noteElement.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            noteElement.style.transition = 'all 0.3s ease';
            noteElement.style.opacity = '1';
            noteElement.style.transform = 'translateY(0)';
        }, 100);
    }

    getNoteTypeIcon(type) {
        const icons = { private: '🔒', internal: '👥', customer: '👤' };
        return icons[type] || '📝';
    }

    async translateCurrentNote() {
        const content = document.getElementById('note-content')?.value.trim();
        if (!content) {
            this.showNotification('Aucun texte à traduire', 'error');
            return;
        }

        // Vérification du cache
        if (this.translationCache.has(content)) {
            this.displayTranslations(this.translationCache.get(content));
            return;
        }

        this.showNotification('🌐 Traduction en cours...', 'info');

        try {
            // TODO: Implémenter la traduction via API
            // Simulation pour l'instant
            const translations = {
                en: '[EN] ' + content.replace(/problème/gi, 'problem').replace(/nécessaire/gi, 'necessary'),
                es: '[ES] ' + content.replace(/problème/gi, 'problema').replace(/nécessaire/gi, 'necesario')
            };

            this.translationCache.set(content, translations);
            this.displayTranslations(translations);
            this.showNotification('✅ Traduction terminée', 'success');

        } catch (error) {
            this.showNotification('Erreur de traduction', 'error');
            console.error('Erreur traduction:', error);
        }
    }

    displayTranslations(translations) {
        // Affichage temporaire des traductions
        const translationDiv = document.createElement('div');
        translationDiv.className = 'translation-preview';
        translationDiv.innerHTML = `
            <h4>🌐 Traductions automatiques:</h4>
            ${translations.en ? `<div class="translation en"><strong>🇬🇧 English:</strong><p>${translations.en}</p></div>` : ''}
            ${translations.es ? `<div class="translation es"><strong>🇪🇸 Español:</strong><p>${translations.es}</p></div>` : ''}
            <button class="clay-btn clay-btn-ghost" onclick="this.parentElement.remove()">Fermer</button>
        `;

        const noteForm = document.querySelector('.note-form');
        const existing = noteForm.querySelector('.translation-preview');
        if (existing) existing.remove();
        
        noteForm.appendChild(translationDiv);
    }

    autoSaveNote() {
        const content = document.getElementById('note-content')?.value.trim();
        if (content) {
            localStorage.setItem(`note_draft_${this.workOrderId}`, content);
            this.showNotification('💾 Brouillon sauvegardé', 'info', 2000);
        }
    }

    /**
     * INTERFACE VOCALE AVANCÉE
     */
    setupVoiceInterface() {
        this.initializeSpeechRecognition();
        
        // Boutons de contrôle vocal
        const recordBtn = document.getElementById('record-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (recordBtn) {
            recordBtn.removeAttribute('onclick');
            recordBtn.addEventListener('click', () => this.toggleRecording());
        }
        
        if (stopBtn) {
            stopBtn.removeAttribute('onclick');
            stopBtn.addEventListener('click', () => this.stopRecording());
        }
    }

    initializeSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            
            this.speechRecognition.continuous = true;
            this.speechRecognition.interimResults = true;
            this.speechRecognition.lang = 'fr-FR';
            
            this.speechRecognition.onstart = () => {
                console.log('🎤 Reconnaissance vocale démarrée');
                this.updateVoiceStatus('Écoute en cours...', 'listening');
            };
            
            this.speechRecognition.onresult = (event) => {
                this.handleSpeechResult(event);
            };
            
            this.speechRecognition.onerror = (event) => {
                console.error('Erreur reconnaissance vocale:', event.error);
                this.updateVoiceStatus('Erreur de reconnaissance', 'error');
                this.isListening = false;
            };
            
            this.speechRecognition.onend = () => {
                this.isListening = false;
                this.updateVoiceStatus('Reconnaissance terminée', 'success');
            };
        }
    }

    prepareVoiceInterface() {
        this.updateVoiceStatus('Prêt pour la dictée vocale', 'ready');
        this.loadVoiceDraft();
    }

    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }

    async startRecording() {
        try {
            // Enregistrement audio
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
            
            // Reconnaissance vocale en temps réel
            if (this.speechRecognition && !this.isListening) {
                this.speechRecognition.start();
                this.isListening = true;
            }
            
            this.updateVoiceControls(true);
            this.updateVoiceStatus('🔴 Enregistrement en cours...', 'recording');
            
        } catch (error) {
            console.error('Erreur accès microphone:', error);
            this.showNotification('Impossible d\'accéder au microphone', 'error');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
        }
        
        if (this.speechRecognition && this.isListening) {
            this.speechRecognition.stop();
            this.isListening = false;
        }
        
        this.updateVoiceControls(false);
        this.updateVoiceStatus('⚡ Traitement en cours...', 'processing');
    }

    handleSpeechResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Mise à jour en temps réel
        this.updateTranscriptionPreview(finalTranscript, interimTranscript);
    }

    updateTranscriptionPreview(finalText, interimText) {
        const preview = document.getElementById('transcription-preview');
        if (!preview) return;
        
        const textElement = preview.querySelector('.transcription-text');
        if (textElement) {
            textElement.innerHTML = `
                <span class="final-text">${finalText}</span>
                <span class="interim-text">${interimText}</span>
            `;
        }
        
        preview.style.display = 'block';
    }

    async processVoiceRecording() {
        const audioBlob = new Blob(this.recordedChunks, { type: 'audio/wav' });
        
        const formData = new FormData();
        formData.append('audio_data', audioBlob, 'voice_note.wav');
        
        try {
            const response = await fetch(`/interventions/${this.workOrderId}/voice_note`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.finalizeTranscription(data.transcription, data.confidence);
                this.showNotification('🎤 Transcription terminée', 'success');
            } else {
                this.showNotification('Erreur de transcription', 'error');
            }
        } catch (error) {
            console.error('Erreur transcription:', error);
            this.showNotification('Erreur de transcription', 'error');
        }
    }

    finalizeTranscription(transcription, confidence) {
        const preview = document.getElementById('transcription-preview');
        if (!preview) return;
        
        const textElement = preview.querySelector('.transcription-text');
        if (textElement) {
            textElement.textContent = transcription;
        }
        
        this.updateVoiceStatus(`✅ Transcription terminée (${Math.round(confidence * 100)}%)`, 'success');
        
        // Affichage des actions
        const actions = preview.querySelector('.transcription-actions');
        if (actions) {
            actions.style.display = 'flex';
        }
    }

    updateVoiceControls(isRecording) {
        const recordBtn = document.getElementById('record-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (recordBtn) recordBtn.style.display = isRecording ? 'none' : 'inline-block';
        if (stopBtn) stopBtn.style.display = isRecording ? 'inline-block' : 'none';
    }

    updateVoiceStatus(message, type) {
        const status = document.getElementById('voice-status');
        if (status) {
            status.innerHTML = `<span class="${type}">${message}</span>`;
        }
    }

    /**
     * CAPTURE PHOTO/VIDÉO
     */
    setupPhotoCapture() {
        // Modal de capture photo
        this.setupCameraInterface();
    }

    setupCameraInterface() {
        const captureBtn = document.getElementById('capture-btn');
        const retakeBtn = document.getElementById('retake-btn');
        const saveBtn = document.getElementById('save-photo-btn');
        
        if (captureBtn) {
            captureBtn.addEventListener('click', () => this.capturePhoto());
        }
        
        if (retakeBtn) {
            retakeBtn.addEventListener('click', () => this.retakePhoto());
        }
        
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.savePhoto());
        }
    }

    async openPhotoCapture() {
        const modal = document.getElementById('photo-capture-modal');
        if (!modal) return;
        
        modal.style.display = 'flex';
        
        try {
            this.photoStream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' } // Caméra arrière sur mobile
            });
            
            const video = document.getElementById('camera-feed');
            if (video) {
                video.srcObject = this.photoStream;
            }
            
        } catch (error) {
            console.error('Erreur accès caméra:', error);
            this.showNotification('Impossible d\'accéder à la caméra', 'error');
            this.closePhotoCapture();
        }
    }

    capturePhoto() {
        const video = document.getElementById('camera-feed');
        const canvas = document.getElementById('photo-canvas');
        
        if (!video || !canvas) return;
        
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        context.drawImage(video, 0, 0);
        
        // Masquer la vidéo, afficher le canvas
        video.style.display = 'none';
        canvas.style.display = 'block';
        
        // Mise à jour des boutons
        document.getElementById('capture-btn').style.display = 'none';
        document.getElementById('retake-btn').style.display = 'inline-block';
        document.getElementById('save-photo-btn').style.display = 'inline-block';
    }

    retakePhoto() {
        const video = document.getElementById('camera-feed');
        const canvas = document.getElementById('photo-canvas');
        
        // Retour à la vidéo
        video.style.display = 'block';
        canvas.style.display = 'none';
        
        // Mise à jour des boutons
        document.getElementById('capture-btn').style.display = 'inline-block';
        document.getElementById('retake-btn').style.display = 'none';
        document.getElementById('save-photo-btn').style.display = 'none';
    }

    async savePhoto() {
        const canvas = document.getElementById('photo-canvas');
        if (!canvas) return;
        
        // Conversion en blob
        canvas.toBlob(async (blob) => {
            if (!blob) {
                this.showNotification('Erreur de capture', 'error');
                return;
            }
            
            // Upload de la photo
            const formData = new FormData();
            formData.append('file', blob, `photo_${Date.now()}.jpg`);
            
            try {
                const response = await fetch(`/interventions/${this.workOrderId}/upload_media`, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showNotification('📷 Photo sauvegardée', 'success');
                    this.closePhotoCapture();
                    this.refreshMediaGallery();
                } else {
                    this.showNotification(data.message, 'error');
                }
            } catch (error) {
                this.showNotification('Erreur de sauvegarde', 'error');
                console.error('Erreur upload photo:', error);
            }
        }, 'image/jpeg', 0.8);
    }

    closePhotoCapture() {
        const modal = document.getElementById('photo-capture-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        
        // Arrêt du stream caméra
        if (this.photoStream) {
            this.photoStream.getTracks().forEach(track => track.stop());
            this.photoStream = null;
        }
    }

    /**
     * GESTION DES MÉDIAS
     */
    setupMediaInterface() {
        // Upload de fichiers
        const fileInput = document.getElementById('file-upload');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.handleFileUpload(file);
                }
            });
        }
    }

    async handleFileUpload(file) {
        if (!this.isValidFileType(file)) {
            this.showNotification('Type de fichier non autorisé', 'error');
            return;
        }

        const progressId = this.showUploadProgress(file.name);
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`/interventions/${this.workOrderId}/upload_media`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`📁 ${file.name} uploadé avec succès`, 'success');
                
                // Transcription pour audio
                if (file.type.includes('audio') && data.transcription) {
                    this.showTranscriptionResult(data.transcription, data.translations);
                }
                
                this.refreshMediaGallery();
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
            'video/mp4', 'video/mov', 'video/webm',
            'audio/mp3', 'audio/wav', 'audio/m4a', 'audio/ogg',
            'application/pdf'
        ];
        return allowedTypes.includes(file.type);
    }

    showTranscriptionResult(transcription, translations) {
        const result = document.createElement('div');
        result.className = 'transcription-result';
        result.innerHTML = `
            <div class="transcription-header">
                <h4>🎵 Transcription audio</h4>
                <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="transcription-content">
                <p><strong>Français:</strong> ${transcription}</p>
                ${translations?.en ? `<p><strong>English:</strong> ${translations.en}</p>` : ''}
                ${translations?.es ? `<p><strong>Español:</strong> ${translations.es}</p>` : ''}
            </div>
        `;
        
        document.body.appendChild(result);
        
        setTimeout(() => {
            result.remove();
        }, 10000);
    }

    /**
     * ASSISTANT IA
     */
    setupAiInterface() {
        this.loadAiSuggestions();
        
        // Génération de notes IA
        const generateBtn = document.querySelector('[onclick="generateAiNote()"]');
        if (generateBtn) {
            generateBtn.removeAttribute('onclick');
            generateBtn.addEventListener('click', () => this.generateAiNote());
        }
    }

    async loadAiSuggestions() {
        try {
            const response = await fetch(`/interventions/ai/suggestions/${this.workOrderId}`);
            const data = await response.json();
            
            if (data.success) {
                this.aiContext.suggestions = data.suggestions;
                this.displayAiSuggestions(data.suggestions);
            }
        } catch (error) {
            console.error('Erreur chargement suggestions IA:', error);
        }
    }

    displayAiSuggestions(suggestions) {
        const container = document.getElementById('ai-suggestions');
        if (!container) return;
        
        container.innerHTML = suggestions.map(suggestion => `
            <div class="ai-suggestion ${suggestion.type}">
                <div class="suggestion-header">
                    <strong>${suggestion.title}</strong>
                    <span class="confidence">${Math.round(suggestion.confidence * 100)}%</span>
                </div>
                <div class="suggestion-content">${suggestion.content}</div>
                <div class="suggestion-actions">
                    <button class="clay-btn clay-btn-ghost" onclick="interventionDetails.applySuggestion('${suggestion.type}', '${encodeURIComponent(suggestion.content)}')">
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
                this.addPartToNote(decodedContent);
                break;
            case 'maintenance_tip':
                this.addTipToNote(decodedContent);
                break;
            case 'time_estimate':
                this.updateTimeEstimate(decodedContent);
                break;
            default:
                this.addSuggestionToNote(decodedContent);
        }
        
        this.showNotification('💡 Suggestion IA appliquée', 'success');
    }

    addSuggestionToNote(content) {
        const noteTextarea = document.getElementById('note-content');
        if (noteTextarea) {
            const currentContent = noteTextarea.value;
            const newContent = currentContent 
                ? `${currentContent}\n\n🤖 Suggestion IA: ${content}` 
                : `🤖 Suggestion IA: ${content}`;
            noteTextarea.value = newContent;
            noteTextarea.focus();
        }
    }

    async generateAiNote() {
        const promptInput = document.getElementById('ai-prompt-input');
        const prompt = promptInput?.value.trim();
        
        if (!prompt) {
            this.showNotification('Veuillez saisir une demande', 'error');
            return;
        }

        this.showNotification('🤖 Génération en cours...', 'info');

        try {
            // TODO: Intégrer avec l'API IA pour génération de notes
            // Simulation pour l'instant
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const generatedNote = `[Note générée par IA]\n\nBasé sur votre demande: "${prompt}"\n\nAnalyse de la situation:\n- Diagnostic préliminaire effectué\n- Pièces potentiellement nécessaires identifiées\n- Estimation temps d'intervention: 2h\n\nRecommandations:\n- Vérifier l'état des composants adjacents\n- Prévoir un suivi dans 30 jours\n\n[Cette note a été générée automatiquement et doit être vérifiée]`;
            
            const noteTextarea = document.getElementById('note-content');
            if (noteTextarea) {
                noteTextarea.value = generatedNote;
            }
            
            promptInput.value = '';
            this.showNotification('✅ Note générée avec succès', 'success');
            
        } catch (error) {
            this.showNotification('Erreur de génération IA', 'error');
            console.error('Erreur génération IA:', error);
        }
    }

    /**
     * OUTILS RAPIDES
     */
    setupQuickTools() {
        document.addEventListener('click', (e) => {
            const buttonText = e.target.textContent?.trim();
            
            if (buttonText?.includes('Rapport auto')) {
                this.generateReport();
            } else if (buttonText?.includes('Planifier suivi')) {
                this.scheduleFollowUp();
            } else if (buttonText?.includes('Demander pièces')) {
                this.requestParts();
            } else if (buttonText?.includes('Notifier client')) {
                this.customerNotification();
            }
        });
    }

    generateReport() {
        this.showNotification('📊 Génération du rapport automatique...', 'info');
        // TODO: Implémenter la génération de rapport
    }

    scheduleFollowUp() {
        this.showNotification('📅 Planification du suivi...', 'info');
        // TODO: Implémenter la planification
    }

    requestParts() {
        this.showNotification('🔧 Demande de pièces envoyée...', 'info');
        // TODO: Implémenter la demande de pièces
    }

    customerNotification() {
        this.showNotification('📧 Notification client envoyée...', 'info');
        // TODO: Implémenter la notification client
    }

    /**
     * MISES À JOUR TEMPS RÉEL
     */
    startRealTimeUpdates() {
        // Vérification périodique des mises à jour
        setInterval(() => {
            this.checkForUpdates();
        }, 30000); // Toutes les 30 secondes
    }

    async checkForUpdates() {
        // TODO: Vérifier les nouvelles notes, médias, etc.
    }

    loadAiContext() {
        // Chargement du contexte IA existant
        // TODO: Charger les données existantes pour enrichir l'IA
    }

    updateAiSuggestions() {
        // Mise à jour des suggestions basées sur les nouvelles données
        setTimeout(() => {
            this.loadAiSuggestions();
        }, 1000);
    }

    /**
     * UTILITAIRES
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

    showNotification(message, type = 'info', duration = 5000) {
        document.querySelectorAll('.notification').forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, duration);
    }

    showUploadProgress(filename) {
        const progressId = `progress-${Date.now()}`;
        // TODO: Afficher une vraie barre de progression
        return progressId;
    }

    hideUploadProgress(progressId) {
        // TODO: Masquer la barre de progression
    }

    showNoteProgress(message) {
        // TODO: Afficher un indicateur de progression pour les notes
    }

    hideNoteProgress() {
        // TODO: Masquer l'indicateur de progression
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    loadVoiceDraft() {
        const draft = localStorage.getItem(`voice_draft_${this.workOrderId}`);
        if (draft) {
            const textElement = document.querySelector('#transcription-preview .transcription-text');
            if (textElement) {
                textElement.textContent = draft;
                document.getElementById('transcription-preview').style.display = 'block';
            }
        }
    }

    refreshMediaGallery() {
        // TODO: Recharger la galerie sans recharger la page
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    generatePostActionSuggestions(action) {
        // TODO: Générer des suggestions contextuelles après action
        console.log('Génération de suggestions post-action:', action);
    }
}

// Fonctions globales pour compatibilité avec les templates
function addNote() {
    window.interventionDetails?.addNote();
}

function translateNote() {
    window.interventionDetails?.translateCurrentNote();
}

function toggleRecording() {
    window.interventionDetails?.toggleRecording();
}

function stopRecording() {
    window.interventionDetails?.stopRecording();
}

function generateAiNote() {
    window.interventionDetails?.generateAiNote();
}

function useTranscription() {
    const transcriptionText = document.querySelector('#transcription-preview .transcription-text')?.textContent;
    if (transcriptionText) {
        const noteTextarea = document.getElementById('note-content');
        if (noteTextarea) {
            noteTextarea.value = transcriptionText;
            noteTextarea.focus();
        }
    }
}

function retryRecording() {
    window.interventionDetails?.toggleRecording();
}

function openPhotoCapture() {
    window.interventionDetails?.openPhotoCapture();
}

function closePhotoCapture() {
    window.interventionDetails?.closePhotoCapture();
}

function openMediaViewer(filePath, mediaType) {
    const modal = document.getElementById('media-viewer-modal');
    const content = document.getElementById('media-viewer-content');
    
    if (modal && content) {
        if (mediaType === 'photo') {
            content.innerHTML = `<img src="${filePath}" alt="Photo d'intervention">`;
        } else if (mediaType === 'video') {
            content.innerHTML = `<video controls><source src="${filePath}"></video>`;
        }
        modal.style.display = 'flex';
    }
}

function closeMediaViewer() {
    const modal = document.getElementById('media-viewer-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function playAudio(filePath) {
    const audio = new Audio(filePath);
    audio.play();
}

function toggleTranslations(noteId) {
    const translations = document.getElementById(`translations-${noteId}`);
    if (translations) {
        translations.style.display = translations.style.display === 'none' ? 'block' : 'none';
    }
}

function showMediaTranslations(mediaId) {
    // TODO: Afficher les traductions pour un média
    console.log('Affichage traductions média:', mediaId);
}

function applySuggestion(type, content) {
    window.interventionDetails?.applySuggestion(type, content);
}

function generateReport() {
    window.interventionDetails?.generateReport();
}

function scheduleFollowUp() {
    window.interventionDetails?.scheduleFollowUp();
}

function requestParts() {
    window.interventionDetails?.requestParts();
}

function customerNotification() {
    window.interventionDetails?.customerNotification();
}

function quickAction(action) {
    window.interventionDetails?.quickAction(action);
}

function startVoiceNote() {
    window.interventionDetails?.startVoiceNote();
}

function openAiAssistant() {
    window.interventionDetails?.openAiAssistant();
}

function uploadFile(input) {
    const file = input.files[0];
    if (file) {
        window.interventionDetails?.handleFileUpload(file);
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    // Récupération de l'ID du bon de travail depuis la page
    const workOrderElement = document.querySelector('[data-work-order-id]');
    const workOrderId = workOrderElement?.dataset.workOrderId || window.workOrderId;
    
    if (workOrderId) {
        window.interventionDetails = new InterventionDetailsManager(workOrderId);
        console.log('🔧 Gestionnaire de détails d\'intervention initialisé pour:', workOrderId);
    } else {
        console.error('❌ ID de bon de travail non trouvé');
    }
});

// Export pour utilisation en module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InterventionDetailsManager;
}
