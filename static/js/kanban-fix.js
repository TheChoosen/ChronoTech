/**
 * Kanban Fix - Correction des problèmes d'initialisation et conflits
 * Solution temporaire pour assurer le fonctionnement du drag-drop
 */

(function() {
    'use strict';
    
    console.log('🔧 Chargement du correctif Kanban...');
    
    // Attendre que le DOM soit prêt
    function waitForDOM() {
        return new Promise(resolve => {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', resolve);
            } else {
                resolve();
            }
        });
    }
    
    // Attendre qu'une condition soit remplie
    function waitFor(condition, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const start = Date.now();
            
            function check() {
                if (condition()) {
                    resolve();
                } else if (Date.now() - start > timeout) {
                    reject(new Error('Timeout'));
                } else {
                    setTimeout(check, 100);
                }
            }
            
            check();
        });
    }
    
    // Fonction de correction principale
    async function applyKanbanFix() {
        try {
            console.log('🔄 Application du correctif Kanban...');
            
            // Attendre que le DOM soit prêt
            await waitForDOM();
            
            // Attendre que ChronoChatDashboard soit disponible
            await waitFor(() => typeof window.ChronoChatDashboard !== 'undefined');
            
            // Vérifier si window.chronochat existe, sinon l'initialiser
            if (!window.chronochat) {
                console.log('🔧 Initialisation manuelle de window.chronochat...');
                window.chronochat = new window.ChronoChatDashboard();
                
                // Attendre un peu pour que l'initialisation se termine
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            
            // Vérifier que les fonctions globales sont disponibles
            ensureGlobalFunctions();
            
            // Forcer le rechargement des données Kanban
            if (window.chronochat && typeof window.chronochat.loadKanbanData === 'function') {
                console.log('📊 Rechargement des données Kanban...');
                window.chronochat.loadKanbanData();
            }
            
            // Optimiser les cartes existantes
            optimizeExistingCards();
            
            // Ajouter des listeners de sécurité
            addSafetyListeners();
            
            console.log('✅ Correctif Kanban appliqué avec succès');
            
        } catch (error) {
            console.error('❌ Erreur lors de l\'application du correctif:', error);
            
            // Solution de fallback
            applyFallbackSolution();
        }
    }
    
    // S'assurer que les fonctions globales existent
    function ensureGlobalFunctions() {
        console.log('🔧 Vérification des fonctions globales...');
        
        if (typeof window.allowDrop !== 'function') {
            window.allowDrop = function(event) {
                event.preventDefault();
                event.dataTransfer.dropEffect = 'move';
            };
            console.log('✅ window.allowDrop créée');
        }
        
        if (typeof window.handleDrop !== 'function') {
            window.handleDrop = function(event) {
                event.preventDefault();
                
                const cardId = event.dataTransfer.getData('text/plain');
                const dropTarget = event.currentTarget;
                const column = dropTarget.closest('.kanban-column');
                
                if (!column) {
                    console.error('❌ Colonne cible non trouvée');
                    return;
                }
                
                const newStatus = column.dataset.status;
                
                if (!cardId || !newStatus) {
                    console.error('❌ Données de drop invalides', {cardId, newStatus});
                    return;
                }
                
                console.log(`🔄 Drop détecté: ${cardId} → ${newStatus}`);
                
                if (window.chronochat && typeof window.chronochat.updateWorkOrderStatus === 'function') {
                    window.chronochat.updateWorkOrderStatus(cardId, newStatus);
                } else {
                    // Fallback direct
                    updateWorkOrderStatusDirect(cardId, newStatus);
                }
            };
            console.log('✅ window.handleDrop créée');
        }
        
        if (typeof window.createWorkOrder !== 'function') {
            window.createWorkOrder = function() {
                window.location.href = '/work-orders/create';
            };
            console.log('✅ window.createWorkOrder créée');
        }
    }
    
    // Mise à jour directe du statut (fallback)
    async function updateWorkOrderStatusDirect(workOrderId, newStatus) {
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            
            const response = await fetch(`/api/work-orders/${workOrderId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({status: newStatus})
            });
            
            if (response.ok) {
                console.log('✅ Statut mis à jour avec succès');
                showToast('Statut mis à jour avec succès', 'success');
                
                // Recharger les données
                setTimeout(() => {
                    if (window.chronochat && window.chronochat.loadKanbanData) {
                        window.chronochat.loadKanbanData();
                    }
                }, 500);
            } else {
                throw new Error(`Erreur ${response.status}`);
            }
        } catch (error) {
            console.error('❌ Erreur mise à jour statut:', error);
            showToast('Erreur lors de la mise à jour', 'danger');
        }
    }
    
    // Optimiser les cartes existantes
    function optimizeExistingCards() {
        console.log('🔧 Optimisation des cartes existantes...');
        
        const cards = document.querySelectorAll('.kanban-card');
        let optimized = 0;
        
        cards.forEach(card => {
            // S'assurer que la carte est draggable
            if (!card.draggable) {
                card.draggable = true;
                optimized++;
            }
            
            // S'assurer qu'elle a un cardId
            if (!card.dataset.cardId) {
                // Essayer d'extraire l'ID depuis le contenu
                const title = card.querySelector('h6');
                if (title) {
                    const match = title.textContent.match(/#(\d+)/);
                    if (match) {
                        card.dataset.cardId = match[1];
                        optimized++;
                    }
                }
            }
        });
        
        console.log(`✅ ${optimized} cartes optimisées`);
    }
    
    // Ajouter des listeners de sécurité
    function addSafetyListeners() {
        console.log('🛡️ Ajout des listeners de sécurité...');
        
        // Listener global pour dragstart
        document.addEventListener('dragstart', function(event) {
            if (event.target.classList.contains('kanban-card')) {
                const cardId = event.target.dataset.cardId;
                if (cardId) {
                    event.dataTransfer.setData('text/plain', cardId);
                    event.dataTransfer.effectAllowed = 'move';
                    event.target.classList.add('dragging');
                    
                    console.log(`🎯 Drag démarré: ${cardId}`);
                } else {
                    console.warn('⚠️ Carte sans cardId, drag annulé');
                    event.preventDefault();
                }
            }
        }, true);
        
        // Listener global pour dragend
        document.addEventListener('dragend', function(event) {
            if (event.target.classList.contains('kanban-card')) {
                event.target.classList.remove('dragging');
            }
        }, true);
        
        console.log('✅ Listeners de sécurité ajoutés');
    }
    
    // Solution de fallback si tout échoue
    function applyFallbackSolution() {
        console.log('🆘 Application de la solution de fallback...');
        
        // Créer des fonctions minimales
        window.allowDrop = window.allowDrop || function(e) { e.preventDefault(); };
        window.handleDrop = window.handleDrop || function(e) { 
            e.preventDefault();
            console.log('🔄 Drop fallback déclenché');
        };
        window.createWorkOrder = window.createWorkOrder || function() {
            window.location.href = '/work-orders/create';
        };
        
        // Ajouter un message d'information
        showToast('Mode de compatibilité activé', 'info');
        
        console.log('✅ Solution de fallback appliquée');
    }
    
    // Système de toast simple
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed`;
        toast.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        }, 10);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Observer pour détecter les nouvelles cartes ajoutées dynamiquement
    function setupCardObserver() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            if (node.classList && node.classList.contains('kanban-card')) {
                                optimizeCard(node);
                            } else {
                                // Chercher des cartes dans les enfants
                                const cards = node.querySelectorAll('.kanban-card');
                                cards.forEach(optimizeCard);
                            }
                        }
                    });
                }
            });
        });
        
        // Observer les sections kanban
        const kanbanSection = document.querySelector('#kanban-section');
        if (kanbanSection) {
            observer.observe(kanbanSection, {
                childList: true,
                subtree: true
            });
        }
    }
    
    function optimizeCard(card) {
        if (!card.draggable) {
            card.draggable = true;
        }
        
        if (!card.dataset.cardId) {
            const title = card.querySelector('h6');
            if (title) {
                const match = title.textContent.match(/#(\d+)/);
                if (match) {
                    card.dataset.cardId = match[1];
                }
            }
        }
    }
    
    // Démarrer le correctif
    applyKanbanFix().then(() => {
        setupCardObserver();
        
        // Diagnostic après correction
        setTimeout(() => {
            if (typeof window.debugKanban === 'function') {
                console.log('🔍 Diagnostic post-correction...');
                window.debugKanban();
            }
        }, 2000);
    });
    
    console.log('🔧 Correctif Kanban initialisé');
    
})();
