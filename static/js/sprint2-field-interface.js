// ChronoTech Sprint 2 - Interface Voice-to-Action + AR Frontend
// Interface utilisateur pour commandes vocales et AR

class Sprint2FieldInterface {
    constructor() {
        this.voiceRecognition = null;
        this.isListening = false;
        this.arSession = null;
        this.offlineMode = false;
        this.currentWorkOrderId = null;
        
        this.init();
    }
    
    init() {
        this.initVoiceInterface();
        this.initARInterface();
        this.initOfflineMode();
        this.bindEvents();
        this.checkOfflineStatus();
        
        console.log('🎤 Sprint 2 - Interface Terrain Augmentée initialisée');
    }
    
    // =============================================================================
    // VOICE-TO-ACTION Interface
    // =============================================================================
    
    initVoiceInterface() {
        // Vérifier le support du navigateur
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('⚠️ Reconnaissance vocale non supportée');
            this.showNotification('Reconnaissance vocale non disponible', 'warning');
            return;
        }
        
        // Configurer la reconnaissance vocale
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.voiceRecognition = new SpeechRecognition();
        
        this.voiceRecognition.continuous = true;
        this.voiceRecognition.interimResults = true;
        this.voiceRecognition.lang = 'fr-FR';
        
        // Événements de reconnaissance
        this.voiceRecognition.onstart = () => {
            this.isListening = true;
            this.updateVoiceUI(true);
            this.showNotification('🎤 Écoute vocale activée', 'info');
        };
        
        this.voiceRecognition.onend = () => {
            this.isListening = false;
            this.updateVoiceUI(false);
        };
        
        this.voiceRecognition.onresult = (event) => {
            this.handleVoiceResult(event);
        };
        
        this.voiceRecognition.onerror = (event) => {
            console.error('Erreur reconnaissance vocale:', event.error);
            this.showNotification(`Erreur vocale: ${event.error}`, 'error');
        };
    }
    
    handleVoiceResult(event) {
        let finalTranscript = '';
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Afficher la transcription en temps réel
        this.updateTranscriptionDisplay(finalTranscript, interimTranscript);
        
        // Traiter la commande finale
        if (finalTranscript.trim()) {
            this.processVoiceCommand(finalTranscript.trim());
        }
    }
    
    async processVoiceCommand(transcript) {
        try {
            // Afficher un feedback visuel
            this.showVoiceProcessing(transcript);
            
            // Simuler les données audio (en production, utiliser le vrai audio)
            const audioData = this.simulateAudioData(transcript);
            
            const response = await fetch('/api/sprint2/voice/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    audio_data: audioData,
                    work_order_id: this.currentWorkOrderId,
                    transcript: transcript
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.handleVoiceCommandSuccess(result);
            } else {
                this.handleVoiceCommandError(result);
            }
            
        } catch (error) {
            console.error('Erreur traitement commande vocale:', error);
            this.showNotification('Erreur de traitement vocal', 'error');
        }
    }
    
    handleVoiceCommandSuccess(result) {
        // Afficher le résultat
        this.showNotification(result.message, 'success');
        
        // Mettre à jour l'interface selon le type de commande
        switch (result.command_type) {
            case 'start_task':
                this.updateWorkOrderStatus('in_progress');
                this.showTaskStartedFeedback();
                break;
                
            case 'complete_task':
                this.updateWorkOrderStatus('completed');
                this.showTaskCompletedFeedback(result.action_result);
                break;
                
            case 'add_note':
                this.addVoiceNoteToUI(result.action_result.note_content);
                break;
                
            case 'report_issue':
                this.showIssueReportedFeedback(result.action_result);
                break;
        }
        
        // Mettre à jour l'historique
        this.addToVoiceHistory(result);
    }
    
    handleVoiceCommandError(result) {
        this.showNotification(result.message || 'Commande non reconnue', 'warning');
        
        if (result.suggestion) {
            this.showVoiceSuggestion(result.suggestion);
        }
    }
    
    // Interface vocale UI
    updateVoiceUI(listening) {
        const voiceButton = document.getElementById('voice-toggle-btn');
        const voiceStatus = document.getElementById('voice-status');
        
        if (voiceButton) {
            voiceButton.classList.toggle('listening', listening);
            voiceButton.innerHTML = listening ? 
                '<i class="fas fa-microphone-slash"></i> Arrêter' : 
                '<i class="fas fa-microphone"></i> Parler';
        }
        
        if (voiceStatus) {
            voiceStatus.textContent = listening ? 'En écoute...' : 'Appuyez pour parler';
            voiceStatus.className = listening ? 'voice-listening' : 'voice-idle';
        }
    }
    
    updateTranscriptionDisplay(finalText, interimText) {
        const transcriptionDiv = document.getElementById('voice-transcription');
        if (transcriptionDiv) {
            transcriptionDiv.innerHTML = `
                <div class="final-text">${finalText}</div>
                <div class="interim-text">${interimText}</div>
            `;
        }
    }
    
    showVoiceProcessing(transcript) {
        const processingDiv = document.getElementById('voice-processing');
        if (processingDiv) {
            processingDiv.innerHTML = `
                <div class="processing-command">
                    <i class="fas fa-cog fa-spin"></i>
                    Traitement: "${transcript}"
                </div>
            `;
            processingDiv.style.display = 'block';
            
            setTimeout(() => {
                processingDiv.style.display = 'none';
            }, 3000);
        }
    }
    
    // =============================================================================
    // AR INTERFACE
    // =============================================================================
    
    initARInterface() {
        this.arCanvas = document.getElementById('ar-canvas');
        this.arVideo = document.getElementById('ar-video');
        this.arOverlay = document.getElementById('ar-overlay');
        
        if (!this.arCanvas || !this.arVideo) {
            console.warn('⚠️ Éléments AR non trouvés dans le DOM');
            return;
        }
        
        this.arContext = this.arCanvas.getContext('2d');
        this.arActive = false;
    }
    
    async startARSession(workOrderId, checklistType) {
        try {
            // Démarrer la session AR côté serveur
            const response = await fetch('/api/sprint2/ar/start-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    work_order_id: workOrderId,
                    checklist_type: checklistType
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.arSession = result;
                await this.initCamera();
                this.startARProcessing();
                this.showNotification('📱 Session AR démarrée', 'success');
                return true;
            } else {
                this.showNotification(result.message, 'error');
                return false;
            }
            
        } catch (error) {
            console.error('Erreur démarrage AR:', error);
            this.showNotification('Erreur démarrage AR', 'error');
            return false;
        }
    }
    
    async initCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'environment', // Caméra arrière
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            this.arVideo.srcObject = stream;
            this.arVideo.play();
            
            this.arVideo.onloadedmetadata = () => {
                this.arCanvas.width = this.arVideo.videoWidth;
                this.arCanvas.height = this.arVideo.videoHeight;
            };
            
        } catch (error) {
            console.error('Erreur accès caméra:', error);
            this.showNotification('Erreur accès caméra', 'error');
        }
    }
    
    startARProcessing() {
        this.arActive = true;
        this.processARFrame();
    }
    
    async processARFrame() {
        if (!this.arActive || !this.arVideo.videoWidth) {
            return;
        }
        
        try {
            // Capturer la frame courante
            const canvas = document.createElement('canvas');
            canvas.width = this.arVideo.videoWidth;
            canvas.height = this.arVideo.videoHeight;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.arVideo, 0, 0);
            
            // Convertir en base64
            const frameData = canvas.toDataURL('image/jpeg', 0.8);
            
            // Envoyer au serveur pour traitement AR
            const response = await fetch('/api/sprint2/ar/process-frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    frame_data: frameData
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Afficher la frame avec overlay
                this.displayARFrame(result.frame, result.overlay_info);
            }
            
        } catch (error) {
            console.error('Erreur traitement frame AR:', error);
        }
        
        // Continuer le traitement (30 FPS)
        if (this.arActive) {
            setTimeout(() => this.processARFrame(), 33);
        }
    }
    
    displayARFrame(frameData, overlayInfo) {
        // Afficher la frame traitée
        const img = new Image();
        img.onload = () => {
            this.arContext.clearRect(0, 0, this.arCanvas.width, this.arCanvas.height);
            this.arContext.drawImage(img, 0, 0);
            
            // Mettre à jour les informations d'overlay
            this.updateAROverlayInfo(overlayInfo);
        };
        img.src = frameData;
    }
    
    updateAROverlayInfo(overlayInfo) {
        if (!overlayInfo || !this.arOverlay) return;
        
        this.arOverlay.innerHTML = `
            <div class="ar-progress">
                <h3>${overlayInfo.checklist_type}</h3>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${overlayInfo.global_progress || 0}%"></div>
                </div>
                <span>${overlayInfo.completed_items || 0}/${overlayInfo.total_items || 0} items</span>
            </div>
            <div class="ar-zones">
                ${this.renderARZones(overlayInfo.zone_progress)}
            </div>
        `;
    }
    
    renderARZones(zoneProgress) {
        if (!zoneProgress) return '';
        
        return Object.entries(zoneProgress).map(([zoneName, progress]) => `
            <div class="ar-zone ${progress.status}">
                <h4>${zoneName}</h4>
                <span>${progress.completed.length}/${progress.total}</span>
                <div class="zone-items">
                    ${progress.completed.map(item => `<span class="completed-item">✓ ${item}</span>`).join('')}
                </div>
            </div>
        `).join('');
    }
    
    async completeARItem(zoneName, itemName) {
        try {
            const response = await fetch('/api/sprint2/ar/complete-item', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    zone_name: zoneName,
                    item_name: itemName
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`✅ ${itemName} complété`, 'success');
                // L'interface se mettra à jour au prochain processARFrame
            } else {
                this.showNotification(result.message, 'warning');
            }
            
        } catch (error) {
            console.error('Erreur completion item AR:', error);
        }
    }
    
    stopARSession() {
        this.arActive = false;
        
        if (this.arVideo.srcObject) {
            this.arVideo.srcObject.getTracks().forEach(track => track.stop());
        }
        
        // Finaliser la session côté serveur
        fetch('/api/sprint2/ar/finalize-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        }).then(response => response.json())
        .then(result => {
            if (result.success) {
                this.showNotification('Session AR terminée', 'success');
                this.showARReport(result.report);
            }
        });
    }
    
    // =============================================================================
    // OFFLINE MODE
    // =============================================================================
    
    initOfflineMode() {
        // Vérifier le statut offline au démarrage
        this.checkOfflineStatus();
        
        // Écouter les changements de connectivité
        window.addEventListener('online', () => {
            this.offlineMode = false;
            this.updateOfflineUI();
            this.syncWhenOnline();
        });
        
        window.addEventListener('offline', () => {
            this.offlineMode = true;
            this.updateOfflineUI();
        });
    }
    
    async checkOfflineStatus() {
        try {
            const response = await fetch('/api/sprint2/offline/status');
            const result = await response.json();
            
            if (result.success) {
                this.offlineMode = result.offline_mode;
                this.updateOfflineUI();
                this.updateOfflineStats(result.offline_stats);
            }
            
        } catch (error) {
            // En cas d'erreur réseau, considérer en offline
            this.offlineMode = true;
            this.updateOfflineUI();
        }
    }
    
    updateOfflineUI() {
        const offlineIndicator = document.getElementById('offline-indicator');
        const syncButton = document.getElementById('sync-now-btn');
        
        if (offlineIndicator) {
            offlineIndicator.style.display = this.offlineMode ? 'block' : 'none';
            offlineIndicator.innerHTML = this.offlineMode ? 
                '<i class="fas fa-wifi-slash"></i> Mode Offline' : 
                '<i class="fas fa-wifi"></i> En ligne';
        }
        
        if (syncButton) {
            syncButton.disabled = this.offlineMode;
            syncButton.innerHTML = this.offlineMode ? 
                '<i class="fas fa-sync-alt"></i> Sync (Hors ligne)' : 
                '<i class="fas fa-sync-alt"></i> Synchroniser';
        }
        
        // Afficher notification si passage en offline
        if (this.offlineMode) {
            this.showNotification('📱 Mode offline activé - Les données seront synchronisées automatiquement', 'info');
        }
    }
    
    async syncWhenOnline() {
        if (this.offlineMode) return;
        
        try {
            const response = await fetch('/api/sprint2/offline/sync-now', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('🔄 Synchronisation terminée', 'success');
                this.updateOfflineStats(result.stats);
            }
            
        } catch (error) {
            console.error('Erreur synchronisation:', error);
        }
    }
    
    updateOfflineStats(stats) {
        const statsDiv = document.getElementById('offline-stats');
        if (statsDiv && stats) {
            statsDiv.innerHTML = `
                <div class="stat-item">
                    <label>En attente de sync:</label>
                    <span>${stats.pending_sync_items || 0}</span>
                </div>
                <div class="stat-item">
                    <label>Commandes vocales:</label>
                    <span>${stats.pending_voice_commands || 0}</span>
                </div>
                <div class="stat-item">
                    <label>Work orders:</label>
                    <span>${stats.pending_work_orders || 0}</span>
                </div>
            `;
        }
    }
    
    // =============================================================================
    // EVENT HANDLERS
    // =============================================================================
    
    bindEvents() {
        // Bouton vocal
        const voiceToggle = document.getElementById('voice-toggle-btn');
        if (voiceToggle) {
            voiceToggle.addEventListener('click', () => this.toggleVoiceListening());
        }
        
        // Bouton AR
        const arStartBtn = document.getElementById('ar-start-btn');
        if (arStartBtn) {
            arStartBtn.addEventListener('click', () => this.handleARStart());
        }
        
        // Bouton sync
        const syncBtn = document.getElementById('sync-now-btn');
        if (syncBtn) {
            syncBtn.addEventListener('click', () => this.syncWhenOnline());
        }
        
        // Raccourcis clavier
        document.addEventListener('keydown', (e) => {
            // Espace pour activer/désactiver la voix
            if (e.code === 'Space' && e.ctrlKey) {
                e.preventDefault();
                this.toggleVoiceListening();
            }
            
            // F12 pour AR (en mode développement)
            if (e.key === 'F12' && e.shiftKey) {
                e.preventDefault();
                this.handleARStart();
            }
        });
    }
    
    toggleVoiceListening() {
        if (this.isListening) {
            this.stopVoiceListening();
        } else {
            this.startVoiceListening();
        }
    }
    
    startVoiceListening() {
        if (!this.voiceRecognition) {
            this.showNotification('Reconnaissance vocale non disponible', 'error');
            return;
        }
        
        // Informer le serveur
        fetch('/api/sprint2/voice/start-listening', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                work_order_id: this.currentWorkOrderId
            })
        });
        
        this.voiceRecognition.start();
    }
    
    stopVoiceListening() {
        if (this.voiceRecognition && this.isListening) {
            this.voiceRecognition.stop();
            
            // Informer le serveur
            fetch('/api/sprint2/voice/stop-listening', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
        }
    }
    
    handleARStart() {
        const modal = document.getElementById('ar-checklist-modal');
        if (modal) {
            modal.style.display = 'block';
            this.loadARTemplates();
        }
    }
    
    async loadARTemplates() {
        try {
            const response = await fetch('/api/sprint2/ar/templates');
            const result = await response.json();
            
            if (result.success) {
                this.displayARTemplates(result.templates);
            }
            
        } catch (error) {
            console.error('Erreur chargement templates AR:', error);
        }
    }
    
    displayARTemplates(templates) {
        const templatesDiv = document.getElementById('ar-templates-list');
        if (templatesDiv) {
            templatesDiv.innerHTML = Object.entries(templates).map(([key, template]) => `
                <div class="ar-template-card" data-template="${key}">
                    <h4>${template.title}</h4>
                    <p>${template.description}</p>
                    <div class="template-stats">
                        <span><i class="fas fa-list"></i> ${template.total_items} items</span>
                        <span><i class="fas fa-map-marker-alt"></i> ${template.zones_count} zones</span>
                    </div>
                    <button class="btn btn-primary start-ar-btn" data-template="${key}">
                        Démarrer AR
                    </button>
                </div>
            `).join('');
            
            // Bind events pour les boutons AR
            templatesDiv.querySelectorAll('.start-ar-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const template = e.target.dataset.template;
                    this.startARWithTemplate(template);
                });
            });
        }
    }
    
    async startARWithTemplate(template) {
        const workOrderId = this.currentWorkOrderId || prompt('ID du Work Order:');
        if (!workOrderId) return;
        
        const success = await this.startARSession(workOrderId, template);
        if (success) {
            // Fermer le modal et afficher l'interface AR
            document.getElementById('ar-checklist-modal').style.display = 'none';
            document.getElementById('ar-interface').style.display = 'block';
        }
    }
    
    // =============================================================================
    // UTILITAIRES
    // =============================================================================
    
    simulateAudioData(transcript) {
        // En production, capturer et encoder le vrai audio
        return btoa(transcript); // Simulation simple
    }
    
    setCurrentWorkOrder(workOrderId) {
        this.currentWorkOrderId = workOrderId;
    }
    
    showNotification(message, type = 'info') {
        // Utiliser le système de notifications existant
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
    
    addToVoiceHistory(commandResult) {
        const historyDiv = document.getElementById('voice-history');
        if (historyDiv) {
            const entry = document.createElement('div');
            entry.className = 'voice-history-entry';
            entry.innerHTML = `
                <div class="entry-time">${new Date().toLocaleTimeString()}</div>
                <div class="entry-command">${commandResult.command_type}</div>
                <div class="entry-result">${commandResult.message}</div>
            `;
            historyDiv.insertBefore(entry, historyDiv.firstChild);
            
            // Limiter l'historique
            while (historyDiv.children.length > 10) {
                historyDiv.removeChild(historyDiv.lastChild);
            }
        }
    }
    
    showTaskStartedFeedback() {
        this.showNotification('🚀 Tâche démarrée par commande vocale', 'success');
        // Ajouter des effets visuels si nécessaire
    }
    
    showTaskCompletedFeedback(actionResult) {
        this.showNotification('✅ Intervention terminée par commande vocale', 'success');
        // Afficher le résumé si disponible
    }
    
    addVoiceNoteToUI(noteContent) {
        const notesSection = document.getElementById('work-order-notes');
        if (notesSection) {
            const noteDiv = document.createElement('div');
            noteDiv.className = 'voice-note';
            noteDiv.innerHTML = `
                <div class="note-header">
                    <i class="fas fa-microphone"></i>
                    <span>Note vocale - ${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="note-content">${noteContent}</div>
            `;
            notesSection.appendChild(noteDiv);
        }
    }
    
    showIssueReportedFeedback(actionResult) {
        this.showNotification('⚠️ Problème signalé par commande vocale', 'warning');
        // Afficher les détails du problème
    }
    
    showVoiceSuggestion(suggestion) {
        const suggestionDiv = document.getElementById('voice-suggestions');
        if (suggestionDiv) {
            suggestionDiv.innerHTML = `
                <div class="suggestion-content">
                    <i class="fas fa-lightbulb"></i>
                    ${suggestion}
                </div>
            `;
            suggestionDiv.style.display = 'block';
            
            setTimeout(() => {
                suggestionDiv.style.display = 'none';
            }, 5000);
        }
    }
    
    updateWorkOrderStatus(newStatus) {
        // Mettre à jour l'interface du work order
        const statusElement = document.querySelector('.work-order-status');
        if (statusElement) {
            statusElement.textContent = newStatus;
            statusElement.className = `work-order-status status-${newStatus}`;
        }
    }
    
    showARReport(report) {
        const reportModal = document.getElementById('ar-report-modal');
        const reportContent = document.getElementById('ar-report-content');
        
        if (reportModal && reportContent) {
            reportContent.innerHTML = `
                <h3>Rapport d'Inspection AR</h3>
                <div class="report-summary">
                    <div class="summary-item">
                        <label>Taux de completion:</label>
                        <span>${report.completion_rate.toFixed(1)}%</span>
                    </div>
                    <div class="summary-item">
                        <label>Items complétés:</label>
                        <span>${report.completed_items}/${report.total_items}</span>
                    </div>
                    <div class="summary-item">
                        <label>Durée:</label>
                        <span>${this.calculateDuration(report.started_at, report.completed_at)}</span>
                    </div>
                </div>
                <div class="report-zones">
                    ${Object.entries(report.zone_details).map(([zone, details]) => `
                        <div class="zone-report">
                            <h4>${zone}</h4>
                            <span class="zone-status ${details.status}">${details.status}</span>
                            <div class="zone-progress">${details.completed.length}/${details.total}</div>
                        </div>
                    `).join('')}
                </div>
            `;
            
            reportModal.style.display = 'block';
        }
    }
    
    calculateDuration(startTime, endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const duration = Math.round((end - start) / 1000 / 60); // minutes
        return `${duration} min`;
    }
}

// Initialisation
let sprint2Interface = null;

document.addEventListener('DOMContentLoaded', function() {
    sprint2Interface = new Sprint2FieldInterface();
    
    // Exposer globalement pour les autres scripts
    window.sprint2Interface = sprint2Interface;
});

// Export pour les modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Sprint2FieldInterface;
}
