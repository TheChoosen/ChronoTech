/**
 * Debug Script pour analyser les problèmes Kanban
 * Diagnostique les conflits et problèmes d'initialisation
 */

class KanbanDebugger {
    constructor() {
        this.errors = [];
        this.warnings = [];
        this.info = [];
        
        this.runDiagnostics();
    }
    
    runDiagnostics() {
        console.log('🔍 === DÉBUT DIAGNOSTIC KANBAN ===');
        
        this.checkGlobalVariables();
        this.checkDOMElements();
        this.checkEventListeners();
        this.checkCSRFToken();
        this.checkAPIEndpoints();
        this.checkDragDropSetup();
        
        this.displayResults();
    }
    
    checkGlobalVariables() {
        console.log('📋 Vérification des variables globales...');
        
        // Vérifier window.chronochat
        if (typeof window.chronochat === 'undefined') {
            this.errors.push('❌ window.chronochat n\'est pas défini');
        } else {
            this.info.push('✅ window.chronochat est défini');
            
            // Vérifier les méthodes essentielles
            const essentialMethods = ['handleDrop', 'allowDrop', 'updateWorkOrderStatus', 'loadKanbanData'];
            essentialMethods.forEach(method => {
                if (typeof window.chronochat[method] === 'function') {
                    this.info.push(`✅ window.chronochat.${method}() existe`);
                } else {
                    this.errors.push(`❌ window.chronochat.${method}() manquant`);
                }
            });
        }
        
        // Vérifier les fonctions globales
        const globalFunctions = ['allowDrop', 'handleDrop', 'createWorkOrder'];
        globalFunctions.forEach(func => {
            if (typeof window[func] === 'function') {
                this.info.push(`✅ window.${func}() existe`);
            } else {
                this.errors.push(`❌ window.${func}() manquant`);
            }
        });
        
        // Vérifier les classes
        if (typeof window.ChronoChatDashboard === 'function') {
            this.info.push('✅ Classe ChronoChatDashboard disponible');
        } else {
            this.errors.push('❌ Classe ChronoChatDashboard manquante');
        }
    }
    
    checkDOMElements() {
        console.log('🏗️ Vérification des éléments DOM...');
        
        // Vérifier les colonnes Kanban (d'abord dans le modal, puis les versions standard)
        const columnIds = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
        columnIds.forEach(id => {
            // Chercher d'abord dans le modal
            let column = document.getElementById(`modal-column-${id}`);
            let isModal = true;
            
            // Si pas trouvé dans le modal, chercher version standard
            if (!column) {
                column = document.getElementById(`column-${id}`);
                isModal = false;
            }
            
            if (column) {
                const location = isModal ? 'modal' : 'page';
                this.info.push(`✅ Colonne #${isModal ? 'modal-' : ''}column-${id} trouvée (${location})`);
                
                // Vérifier les attributs drag-drop
                if (column.hasAttribute('ondrop')) {
                    this.info.push(`✅ Attribut ondrop sur #${isModal ? 'modal-' : ''}column-${id}`);
                } else {
                    this.warnings.push(`⚠️ Attribut ondrop manquant sur #${isModal ? 'modal-' : ''}column-${id}`);
                }
                
                if (column.hasAttribute('ondragover')) {
                    this.info.push(`✅ Attribut ondragover sur #${isModal ? 'modal-' : ''}column-${id}`);
                } else {
                    this.warnings.push(`⚠️ Attribut ondragover manquant sur #${isModal ? 'modal-' : ''}column-${id}`);
                }
            } else {
                this.errors.push(`❌ Colonne #column-${id} et #modal-column-${id} manquantes`);
            }
        });
        
        // Vérifier les cartes existantes
        const cards = document.querySelectorAll('.kanban-card, .wo-kanban-card');
        this.info.push(`📊 ${cards.length} cartes Kanban trouvées`);
        
        cards.forEach((card, index) => {
            if (card.draggable) {
                this.info.push(`✅ Carte ${index + 1} est draggable`);
            } else {
                this.warnings.push(`⚠️ Carte ${index + 1} n'est pas draggable`);
            }
            
            if (card.dataset.cardId) {
                this.info.push(`✅ Carte ${index + 1} a un cardId: ${card.dataset.cardId}`);
            } else {
                this.errors.push(`❌ Carte ${index + 1} manque data-card-id`);
            }
        });
    }
    
    checkEventListeners() {
        console.log('👂 Vérification des event listeners...');
        
        // Test des événements drag
        const testCard = document.querySelector('.kanban-card');
        if (testCard) {
            // Simuler dragstart
            const dragStartEvent = new DragEvent('dragstart', {
                bubbles: true,
                cancelable: true,
                dataTransfer: new DataTransfer()
            });
            
            try {
                testCard.dispatchEvent(dragStartEvent);
                this.info.push('✅ Événement dragstart peut être déclenché');
            } catch (error) {
                this.errors.push(`❌ Erreur événement dragstart: ${error.message}`);
            }
        } else {
            this.warnings.push('⚠️ Aucune carte pour tester les événements');
        }
    }
    
    checkCSRFToken() {
        console.log('🔐 Vérification du token CSRF...');
        
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            const token = csrfMeta.getAttribute('content');
            if (token) {
                this.info.push('✅ Token CSRF trouvé');
            } else {
                this.warnings.push('⚠️ Token CSRF vide');
            }
        } else {
            this.warnings.push('⚠️ Meta tag csrf-token manquant');
        }
        
        // Tester la fonction getCSRFToken
        try {
            const token = getCSRFToken();
            this.info.push(`✅ getCSRFToken() retourne: ${token ? 'token valide' : 'token vide'}`);
        } catch (error) {
            this.errors.push(`❌ Erreur getCSRFToken(): ${error.message}`);
        }
    }
    
    async checkAPIEndpoints() {
        console.log('🌐 Vérification des endpoints API...');
        
        try {
            // Test endpoint kanban-data
            const response = await fetch('/api/kanban-data');
            if (response.ok) {
                const data = await response.json();
                this.info.push('✅ Endpoint /api/kanban-data accessible');
                this.info.push(`📊 Données: ${JSON.stringify(Object.keys(data)).slice(0, 100)}...`);
            } else {
                this.errors.push(`❌ Endpoint /api/kanban-data erreur: ${response.status}`);
            }
        } catch (error) {
            this.errors.push(`❌ Erreur réseau /api/kanban-data: ${error.message}`);
        }
        
        // Test endpoint de mise à jour (récupérer un vrai ID d'abord)
        try {
            // D'abord, récupérer un vrai work order ID
            const kanbanResponse = await fetch('/api/kanban-data');
            if (kanbanResponse.ok) {
                const kanbanData = await kanbanResponse.json();
                const allWorkOrders = [
                    ...kanbanData.pending || [],
                    ...kanbanData.assigned || [],
                    ...kanbanData.in_progress || [],
                    ...kanbanData.completed || []
                ];
                
                if (allWorkOrders.length > 0) {
                    const testId = allWorkOrders[0].id;
                    const originalStatus = allWorkOrders[0].status;
                    
                    const response = await fetch(`/api/work-orders/${testId}/status`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken()
                        },
                        body: JSON.stringify({status: originalStatus}) // Garde le même status
                    });
                    
                    if (response.ok) {
                        this.info.push(`✅ Endpoint /api/work-orders/{id}/status fonctionne (testé avec ID ${testId})`);
                    } else {
                        this.errors.push(`❌ Endpoint /api/work-orders/{id}/status erreur: ${response.status}`);
                    }
                } else {
                    this.info.push('ℹ️ Aucun work order disponible pour tester l\'endpoint de mise à jour');
                }
            } else {
                // Fallback: test avec un ID fictif mais ne pas traiter 404 comme erreur
                const response = await fetch('/api/work-orders/999/status', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({status: 'pending'})
                });
                
                // 404 est normal pour un ID inexistant, 400/401 indique un problème d'auth
                if (response.status === 404) {
                    this.info.push('✅ Endpoint /api/work-orders/{id}/status accessible (404 normal pour ID fictif)');
                } else if (response.status === 401 || response.status === 403) {
                    this.warnings.push('⚠️ Problème d\'authentification API');
                } else {
                    this.warnings.push(`⚠️ Réponse inattendue: ${response.status}`);
                }
            }
        } catch (error) {
            this.errors.push(`❌ Erreur réseau API update: ${error.message}`);
        }
    }
    
    checkDragDropSetup() {
        console.log('🎯 Vérification spécifique du drag-drop...');
        
        // Vérifier si les événements sont attachés au document
        const events = ['dragstart', 'dragend', 'dragover', 'drop'];
        events.forEach(eventType => {
            // Impossible de détecter directement les listeners, mais on peut tester
            this.info.push(`ℹ️ Test événement ${eventType} prévu`);
        });
        
        // Vérifier les styles CSS nécessaires
        const styles = window.getComputedStyle(document.body);
        this.info.push('✅ Styles CSS accessibles');
        
        // Vérifier la structure des colonnes (d'abord modal, puis page)
        let kanbanSection = document.querySelector('#work-orders-kanban-board');
        if (kanbanSection) {
            this.info.push('✅ Section Kanban Modal trouvée');
            
            const columns = kanbanSection.querySelectorAll('.wo-kanban-column');
            this.info.push(`📊 ${columns.length} colonnes dans le modal kanban`);
        } else {
            // Fallback vers section kanban classique
            kanbanSection = document.querySelector('#kanban-section');
            if (kanbanSection) {
                this.info.push('✅ Section Kanban classique trouvée');
                
                const columns = kanbanSection.querySelectorAll('.kanban-column');
                this.info.push(`📊 ${columns.length} colonnes dans la section`);
            } else {
                this.warnings.push('⚠️ Aucune section kanban trouvée (#work-orders-kanban-board ou #kanban-section)');
            }
        }
    }
    
    displayResults() {
        console.log('📊 === RÉSULTATS DIAGNOSTIC ===');
        
        // Afficher les erreurs
        if (this.errors.length > 0) {
            console.log('🚨 ERREURS CRITIQUES:');
            this.errors.forEach(error => console.log(error));
        }
        
        // Afficher les avertissements
        if (this.warnings.length > 0) {
            console.log('⚠️ AVERTISSEMENTS:');
            this.warnings.forEach(warning => console.log(warning));
        }
        
        // Afficher les informations
        if (this.info.length > 0) {
            console.log('ℹ️ INFORMATIONS:');
            this.info.forEach(info => console.log(info));
        }
        
        // Résumé
        const totalIssues = this.errors.length + this.warnings.length;
        console.log(`\n📋 RÉSUMÉ: ${this.errors.length} erreurs, ${this.warnings.length} avertissements, ${this.info.length} infos`);
        
        if (totalIssues === 0) {
            console.log('✅ Aucun problème détecté !');
        } else {
            console.log('🔧 Problèmes détectés - voir les détails ci-dessus');
        }
        
        console.log('🔍 === FIN DIAGNOSTIC ===\n');
        
        // Recommandations
        this.provideRecommendations();
    }
    
    provideRecommendations() {
        console.log('💡 === RECOMMANDATIONS ===');
        
        if (this.errors.some(e => e.includes('window.chronochat'))) {
            console.log('🔧 Problème d\'initialisation détecté:');
            console.log('   - Vérifier que chronochat-dashboard.js est chargé');
            console.log('   - Exécuter: window.chronochat = new window.ChronoChatDashboard()');
        }
        
        if (this.errors.some(e => e.includes('Colonne') && e.includes('manquante'))) {
            console.log('🔧 Colonnes Kanban manquantes:');
            console.log('   - Vérifier le template HTML');
            console.log('   - S\'assurer que les IDs correspondent');
        }
        
        if (this.warnings.some(w => w.includes('draggable'))) {
            console.log('🔧 Cartes non-draggable:');
            console.log('   - Recharger les données Kanban');
            console.log('   - Vérifier createKanbanCard()');
        }
        
        console.log('💡 === FIN RECOMMANDATIONS ===');
    }
    
    // Méthode pour tester manuellement le drag-drop
    testDragDrop() {
        console.log('🧪 Test manuel du drag-drop...');
        
        const card = document.querySelector('.kanban-card');
        const dropZone = document.querySelector('.kanban-content');
        
        if (!card || !dropZone) {
            console.log('❌ Impossible de tester: éléments manquants');
            return;
        }
        
        // Simuler drag-drop
        const dataTransfer = new DataTransfer();
        dataTransfer.setData('text/plain', card.dataset.cardId || 'test-id');
        
        const dragEvent = new DragEvent('dragstart', {
            bubbles: true,
            cancelable: true,
            dataTransfer: dataTransfer
        });
        
        const dropEvent = new DragEvent('drop', {
            bubbles: true,
            cancelable: true,
            dataTransfer: dataTransfer
        });
        
        try {
            card.dispatchEvent(dragEvent);
            dropZone.dispatchEvent(dropEvent);
            console.log('✅ Test drag-drop exécuté');
        } catch (error) {
            console.log(`❌ Erreur test drag-drop: ${error.message}`);
        }
    }
}

// Fonctions utilitaires globales pour debugging
window.debugKanban = function() {
    return new KanbanDebugger();
};

window.testKanbanDragDrop = function() {
    const dbg = new KanbanDebugger();
    dbg.testDragDrop();
};

window.forceKanbanReload = function() {
    if (window.chronochat && window.chronochat.loadKanbanData) {
        console.log('🔄 Rechargement forcé des données Kanban...');
        window.chronochat.loadKanbanData();
    } else {
        console.log('❌ Impossible de recharger: window.chronochat non disponible');
    }
};

window.initKanbanManual = function() {
    console.log('🔧 Initialisation manuelle du Kanban...');
    if (typeof window.ChronoChatDashboard !== 'undefined') {
        window.chronochat = new window.ChronoChatDashboard();
        console.log('✅ Kanban initialisé manuellement');
    } else {
        console.log('❌ Classe ChronoChatDashboard non disponible');
    }
};

console.log('🐛 Debug Kanban chargé. Utilisez debugKanban() pour diagnostiquer.');
console.log('📝 Commandes disponibles:');
console.log('   - debugKanban() : Diagnostic complet');
console.log('   - testKanbanDragDrop() : Test manuel drag-drop');
console.log('   - forceKanbanReload() : Recharger données');
console.log('   - initKanbanManual() : Initialisation manuelle');

// Auto-diagnostic au chargement si demandé
if (window.location.search.includes('debug=kanban')) {
    setTimeout(() => {
        console.log('🔍 Auto-diagnostic activé via URL parameter');
        window.debugKanban();
    }, 2000);
}
