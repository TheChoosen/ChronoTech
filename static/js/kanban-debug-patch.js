/**
 * PATCH KANBAN DASHBOARD - Corrections drag & drop
 * À injecter dans le dashboard pour résoudre les problèmes Kanban
 */

(function() {
    'use strict';
    
    console.log('🔧 Patch Kanban Dashboard - ChronoTech');
    
    // 1. Fonction de debug global
    window.kanbanDebug = {
        version: '1.0.0',
        
        // Test de base
        test: function() {
            console.log('🔍 Test des composants Kanban...');
            
            const results = {
                columns: this.testColumns(),
                cards: this.testCards(),
                api: this.testAPI(),
                events: this.testEvents()
            };
            
            console.log('📊 Résultats des tests:', results);
            return results;
        },
        
        // Test des colonnes
        testColumns: function() {
            const statuses = ['draft', 'pending', 'assigned', 'in_progress', 'completed', 'cancelled'];
            const results = {};
            
            statuses.forEach(status => {
                const column = document.getElementById(`modal-column-${status}`);
                results[status] = {
                    exists: !!column,
                    hasDropHandler: column && column.ondrop !== null,
                    hasAllowDrop: column && column.ondragover !== null,
                    cardCount: column ? column.children.length : 0
                };
            });
            
            return results;
        },
        
        // Test des cartes
        testCards: function() {
            const cards = document.querySelectorAll('.wo-kanban-card');
            let draggableCount = 0;
            let withEvents = 0;
            
            cards.forEach(card => {
                if (card.draggable) draggableCount++;
                if (card.ondragstart) withEvents++;
            });
            
            return {
                total: cards.length,
                draggable: draggableCount,
                withEvents: withEvents,
                percentage: cards.length > 0 ? Math.round((draggableCount / cards.length) * 100) : 0
            };
        },
        
        // Test API
        testAPI: async function() {
            try {
                const response = await fetch('/api/work-orders');
                if (response.ok) {
                    const data = await response.json();
                    return {
                        status: 'OK',
                        count: data.length,
                        statusDistribution: this.analyzeStatusDistribution(data)
                    };
                } else {
                    return { status: 'ERROR', code: response.status };
                }
            } catch (error) {
                return { status: 'ERROR', message: error.message };
            }
        },
        
        // Test des événements
        testEvents: function() {
            const functions = [
                'allowDrop',
                'handleWorkOrderDrop', 
                'handleWorkOrderDragStart',
                'handleWorkOrderDragEnd'
            ];
            
            const results = {};
            functions.forEach(func => {
                results[func] = typeof window[func] === 'function';
            });
            
            return results;
        },
        
        // Analyse distribution des statuts
        analyzeStatusDistribution: function(workOrders) {
            const distribution = {};
            workOrders.forEach(wo => {
                const status = wo.status || 'unknown';
                distribution[status] = (distribution[status] || 0) + 1;
            });
            return distribution;
        },
        
        // Réparation automatique
        autoFix: function() {
            console.log('🔧 Tentative de réparation automatique...');
            
            let fixes = 0;
            
            // Fix 1: Rendre les cartes draggables
            const cards = document.querySelectorAll('.wo-kanban-card');
            cards.forEach(card => {
                if (!card.draggable) {
                    card.draggable = true;
                    fixes++;
                }
                
                // Réattacher les événements si manquants
                if (!card.ondragstart && typeof handleWorkOrderDragStart === 'function') {
                    card.addEventListener('dragstart', handleWorkOrderDragStart);
                    fixes++;
                }
                
                if (!card.ondragend && typeof handleWorkOrderDragEnd === 'function') {
                    card.addEventListener('dragend', handleWorkOrderDragEnd);
                    fixes++;
                }
            });
            
            // Fix 2: Vérifier les zones de drop
            const dropZones = document.querySelectorAll('.wo-kanban-content');
            dropZones.forEach(zone => {
                if (!zone.ondrop && typeof handleWorkOrderDrop === 'function') {
                    zone.addEventListener('drop', handleWorkOrderDrop);
                    fixes++;
                }
                
                if (!zone.ondragover && typeof allowDrop === 'function') {
                    zone.addEventListener('dragover', allowDrop);
                    fixes++;
                }
            });
            
            console.log(`✅ ${fixes} corrections appliquées`);
            return fixes;
        },
        
        // Simulation de drag & drop
        simulateDragDrop: function(fromStatus, toStatus) {
            console.log(`🎯 Simulation: ${fromStatus} → ${toStatus}`);
            
            const fromColumn = document.getElementById(`modal-column-${fromStatus}`);
            const toColumn = document.getElementById(`modal-column-${toStatus}`);
            
            if (!fromColumn || !toColumn) {
                console.error('❌ Colonnes non trouvées');
                return false;
            }
            
            const card = fromColumn.querySelector('.wo-kanban-card');
            if (!card) {
                console.error('❌ Aucune carte dans la colonne source');
                return false;
            }
            
            const cardId = card.dataset.cardId;
            if (!cardId) {
                console.error('❌ Card ID manquant');
                return false;
            }
            
            // Simuler le déplacement
            if (typeof moveWorkOrderToModalStatus === 'function') {
                moveWorkOrderToModalStatus(cardId, fromStatus, toStatus);
                console.log('✅ Déplacement simulé avec succès');
                return true;
            } else {
                console.error('❌ Fonction moveWorkOrderToModalStatus non trouvée');
                return false;
            }
        }
    };
    
    // 2. Améliorations des fonctions existantes
    
    // Override de la fonction createWorkOrderCard si elle existe
    if (typeof window.createWorkOrderCard === 'function') {
        const originalCreateCard = window.createWorkOrderCard;
        
        window.createWorkOrderCard = function(workOrder) {
            const card = originalCreateCard.call(this, workOrder);
            
            // S'assurer que la carte est draggable
            if (!card.draggable) {
                card.draggable = true;
                console.log(`🔧 Carte WO-${workOrder.id} rendue draggable`);
            }
            
            // Vérifier les attributs data
            if (!card.dataset.cardId) {
                card.dataset.cardId = workOrder.id;
            }
            if (!card.dataset.currentStatus) {
                card.dataset.currentStatus = workOrder.status;
            }
            
            return card;
        };
    }
    
    // 3. Notification améliorée des erreurs
    function showKanbanError(message, details = null) {
        console.error(`❌ Kanban Error: ${message}`, details);
        
        // Affichage visuel si possible
        if (typeof showErrorNotification === 'function') {
            showErrorNotification(message);
        } else {
            // Fallback: alerte simple
            alert(`Erreur Kanban: ${message}`);
        }
    }
    
    // 4. Override de saveWorkOrderStatusChange pour meilleure gestion d'erreurs
    if (typeof window.saveWorkOrderStatusChange === 'function') {
        const originalSave = window.saveWorkOrderStatusChange;
        
        window.saveWorkOrderStatusChange = function(cardId, newStatus) {
            console.log(`💾 Sauvegarde améliorée: WO-${cardId} → ${newStatus}`);
            
            return fetch(`/api/work-orders/${cardId}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ status: newStatus })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`✅ Sauvegarde réussie: WO-${cardId} → ${newStatus}`);
                
                // Feedback visuel positif
                const card = document.querySelector(`[data-card-id="${cardId}"]`);
                if (card) {
                    card.style.border = '2px solid #28a745';
                    setTimeout(() => {
                        card.style.border = '';
                    }, 2000);
                }
                
                return data;
            })
            .catch(error => {
                showKanbanError(`Erreur sauvegarde WO-${cardId}: ${error.message}`, error);
                
                // Rollback visuel
                const card = document.querySelector(`[data-card-id="${cardId}"]`);
                if (card) {
                    card.style.border = '2px solid #dc3545';
                    card.style.opacity = '0.7';
                    
                    setTimeout(() => {
                        card.style.border = '';
                        card.style.opacity = '';
                    }, 3000);
                }
                
                throw error;
            });
        };
    }
    
    // 5. Auto-diagnostic au chargement
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(() => {
            console.log('🔍 Auto-diagnostic Kanban...');
            const results = window.kanbanDebug.test();
            
            // Auto-fix si nécessaire
            if (results.cards.percentage < 100) {
                console.log('🔧 Corrections automatiques nécessaires...');
                window.kanbanDebug.autoFix();
            }
            
            console.log('✅ Patch Kanban chargé et testé');
        }, 1000);
    });
    
    // 6. Commandes console rapides
    console.log(`
🔧 COMMANDES KANBAN DISPONIBLES:
- kanbanDebug.test()                           // Test complet
- kanbanDebug.autoFix()                        // Réparations auto
- kanbanDebug.simulateDragDrop('draft', 'pending')  // Test drag&drop
- kanbanDebug.testAPI()                        // Test API

Patch Kanban v${window.kanbanDebug.version} chargé ✅
    `);
    
})();
