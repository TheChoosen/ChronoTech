/**
 * ChronoTech - JavaScript Principal
 * Design Claymorphism avec interactions fluides
 */

// Variables globales
let isLoading = false;

/**
 * === FONCTIONS POUR work_orders.html ===
 */

// Alias pour la compatibilité avec le template work_orders.html
function showModal(modalId) {
    return openModal(modalId);
}

// Fonction de loading global
function showLoading() {
    if (!document.getElementById('global-loader')) {
        const loader = document.createElement('div');
        loader.id = 'global-loader';
        loader.className = 'global-loader';
        loader.innerHTML = `
            <div class="loader-content">
                <div class="clay-spinner"></div>
                <p>Chargement...</p>
            </div>
        `;
        document.body.appendChild(loader);
    }
    document.getElementById('global-loader').style.display = 'flex';
}

function hideLoading() {
    const loader = document.getElementById('global-loader');
    if (loader) {
        loader.style.display = 'none';
    }
}

// Variables globales pour les travaux demandés
let currentView = 'cards';
let selectedWorkOrders = new Set();
let filteredWorkOrders = [];
let sortColumn = 'created_at';
let sortDirection = 'desc';

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 ChronoTech - Application initialisée');
    initializeApp();
    initializeAnimations();
    initializeInteractions();
    initializeFormValidation();
});

/**
 * Initialisation de l'application
 */
function initializeApp() {
    // Gestion du mode sombre automatique
    detectColorScheme();
    
    // Gestion de la connectivité
    handleNetworkStatus();
    
    // Initialisation des tooltips Bootstrap
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

/**
 * Initialisation des animations
 */
function initializeAnimations() {
    // Animation d'entrée progressive pour les cartes
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observer toutes les cartes
    document.querySelectorAll('.clay-card').forEach(card => {
        if (!card.style.opacity) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = 'all 0.6s cubic-bezier(0.25, 0.8, 0.25, 1)';
            observer.observe(card);
        }
    });
}

/**
 * Initialisation des interactions
 */
function initializeInteractions() {
    // Effet de ripple sur les boutons
    addRippleEffect();
    
    // Amélioration des inputs avec focus
    enhanceInputs();
    
    // Gestion des clics extérieurs pour fermer les dropdowns
    handleOutsideClicks();
    
    // Smooth scroll pour les ancres
    initializeSmoothScroll();
}

/**
 * Effet de ripple sur les boutons
 */
function addRippleEffect() {
    // CSS pour l'effet ripple
    if (!document.querySelector('#ripple-styles')) {
        const style = document.createElement('style');
        style.id = 'ripple-styles';
        style.textContent = `
            .clay-btn {
                position: relative;
                overflow: hidden;
            }
            
            .ripple {
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.3);
                transform: scale(0);
                animation: ripple-animation 0.6s linear;
                pointer-events: none;
            }
            
            @keyframes ripple-animation {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.querySelectorAll('.clay-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * Amélioration des inputs
 */
function enhanceInputs() {
    // CSS pour les animations d'input
    if (!document.querySelector('#input-styles')) {
        const style = document.createElement('style');
        style.id = 'input-styles';
        style.textContent = `
            .input-focused .clay-label {
                color: var(--clay-accent-primary);
                transform: scale(0.95);
            }
            
            .clay-label {
                transition: all 0.3s ease;
            }
            
            .input-valid {
                border-left: 3px solid var(--clay-success) !important;
            }
            
            .input-invalid {
                border-left: 3px solid var(--clay-danger) !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    document.querySelectorAll('.clay-input, .clay-textarea, .clay-select').forEach(input => {
        // Animation de focus
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('input-focused');
        });
        
        // Validation en temps réel
        input.addEventListener('input', function() {
            validateInput(this);
        });
    });
}

/**
 * Validation des inputs
 */
function validateInput(input) {
    const value = input.value.trim();
    const type = input.type;
    
    input.classList.remove('input-valid', 'input-invalid');
    
    if (value === '') return;
    
    let isValid = true;
    
    switch (type) {
        case 'email':
            isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
            break;
        case 'password':
            isValid = value.length >= 6;
            break;
        case 'text':
            isValid = value.length >= 2;
            break;
        default:
            isValid = input.checkValidity();
    }
    
    input.classList.add(isValid ? 'input-valid' : 'input-invalid');
    return isValid;
}

/**
 * Initialisation de la validation des formulaires (version unifiée)
 */
function initializeFormValidation() {
    // Validation pour tous les formulaires
    document.querySelectorAll('form').forEach(form => {
        // Sélectionner les inputs avec classes clay ou standards
        const inputs = form.querySelectorAll(
            '.clay-input[required], .clay-textarea[required], .clay-select[required], ' +
            'input[required], textarea[required], select[required]'
        );
        
        // Validation en temps réel pour les formulaires clay
        if (form.classList.contains('clay-form')) {
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    validateField(this);
                });
                
                input.addEventListener('input', function() {
                    if (this.classList.contains('clay-input-error')) {
                        validateField(this);
                    }
                    // Validation pour les inputs clay également
                    if (this.classList.contains('clay-input') || 
                        this.classList.contains('clay-textarea') || 
                        this.classList.contains('clay-select')) {
                        validateInput(this);
                    }
                });
            });
        }
        
        // Validation à la soumission
        form.addEventListener('submit', function(e) {
            let isFormValid = true;
            
            inputs.forEach(input => {
                let inputValid = true;
                
                // Utiliser la validation appropriée selon le type d'input
                if (input.classList.contains('clay-input') || 
                    input.classList.contains('clay-textarea') || 
                    input.classList.contains('clay-select')) {
                    inputValid = validateInput(input);
                } else {
                    inputValid = validateField(input);
                }
                
                if (!inputValid) {
                    isFormValid = false;
                    if (!input.focused) {
                        input.focus();
                        input.focused = true;
                    }
                }
            });
            
            if (!isFormValid) {
                e.preventDefault();
                // Utiliser la notification appropriée
                if (form.classList.contains('clay-form')) {
                    showToast('Veuillez corriger les erreurs dans le formulaire', 'error');
                } else {
                    showNotification('Veuillez corriger les erreurs dans le formulaire', 'warning');
                }
            } else {
                showLoadingState(this);
            }
        });
    });
}

/**
 * Affichage de l'état de chargement
 */
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Chargement...';
        submitBtn.disabled = true;
        
        // Restaurer après 5 secondes si pas de redirection
        setTimeout(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }, 5000);
    }
}

/**
 * Gestion des clics extérieurs
 */
function handleOutsideClicks() {
    document.addEventListener('click', function(event) {
        // Fermer les dropdowns ouverts
        const dropdowns = document.querySelectorAll('.dropdown.show');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(event.target)) {
                const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
                if (toggle && bootstrap.Dropdown) {
                    const instance = bootstrap.Dropdown.getInstance(toggle);
                    if (instance) instance.hide();
                }
            }
        });
    });
}

/**
 * Smooth scroll
 */
function initializeSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Détection du mode sombre
 */
function detectColorScheme() {
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addListener(handleColorSchemeChange);
        handleColorSchemeChange(mediaQuery);
    }
}

function handleColorSchemeChange(e) {
    if (e.matches) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
}

/**
 * Gestion du statut réseau
 */
function handleNetworkStatus() {
    window.addEventListener('online', () => {
        showNotification('Connexion rétablie', 'success');
    });
    
    window.addEventListener('offline', () => {
        showNotification('Mode hors ligne activé', 'warning');
    });
}

/**
 * Système de notifications
 */
function showNotification(message, type = 'info', duration = 4000) {
    const notification = document.createElement('div');
    notification.className = `clay-notification clay-notification-${type}`;
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fa-solid fa-${getNotificationIcon(type)} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    // Styles pour les notifications
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .clay-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--clay-surface-light);
                border-radius: var(--clay-radius-medium);
                box-shadow: var(--clay-shadow-heavy);
                padding: 1rem 1.5rem;
                margin-bottom: 10px;
                z-index: 1050;
                min-width: 300px;
                animation: slideInRight 0.3s ease;
            }
            
            .clay-notification-success { border-left: 4px solid var(--clay-success); }
            .clay-notification-warning { border-left: 4px solid var(--clay-warning); }
            .clay-notification-danger { border-left: 4px solid var(--clay-danger); }
            .clay-notification-info { border-left: 4px solid var(--clay-info); }
            
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // Auto-suppression
    setTimeout(() => {
        notification.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'warning': return 'exclamation-triangle';
        case 'danger': return 'times-circle';
        default: return 'info-circle';
    }
}

/**
 * Fonctions utilitaires spécifiques pour les templates intervention et work_order_lines
 */

// Animation d'entrée staggered pour les éléments
function initStaggeredAnimations() {
    const fadeElements = document.querySelectorAll('.clay-fade-in');
    fadeElements.forEach((element, index) => {
        element.style.animationDelay = `${0.1 * (index + 1)}s`;
    });
}

// Notification toast
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `clay-toast clay-toast-${type}`;
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Afficher le toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Masquer et supprimer après 3 secondes
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
}

// Validation en temps réel des formulaires (fonction supprimée - maintenant dans initializeFormValidation)

function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    
    if (field.hasAttribute('required') && value === '') {
        isValid = false;
    }
    
    if (field.type === 'email' && value && !isValidEmail(value)) {
        isValid = false;
    }
    
    if (field.type === 'number' && value && isNaN(value)) {
        isValid = false;
    }
    
    if (isValid) {
        field.classList.remove('clay-input-error');
    } else {
        field.classList.add('clay-input-error');
        field.classList.add('clay-shake');
        setTimeout(() => field.classList.remove('clay-shake'), 500);
    }
    
    return isValid;
}

function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Animation de chargement pour les boutons
function addLoadingToButton(button, text = 'Chargement...') {
    const originalText = button.innerHTML;
    button.classList.add('clay-loading');
    button.disabled = true;
    button.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>${text}`;
    
    return function removeLoading() {
        button.classList.remove('clay-loading');
        button.disabled = false;
        button.innerHTML = originalText;
    };
}

// Gestion des modals claymorphism
function initModalHandlers() {
    // Boutons d'ouverture de modal
    document.addEventListener('click', (e) => {
        const modalTrigger = e.target.closest('[data-modal-target]');
        if (modalTrigger) {
            const modalId = modalTrigger.getAttribute('data-modal-target');
            openModal(modalId);
        }
    });
    
    // Boutons de fermeture de modal
    document.addEventListener('click', (e) => {
        if (e.target.matches('[data-dismiss="modal"]') || e.target.closest('[data-dismiss="modal"]')) {
            const modal = e.target.closest('.clay-modal');
            if (modal) {
                closeModal(modal.id);
            }
        }
        
        if (e.target.classList.contains('clay-modal-backdrop')) {
            const modal = e.target.closest('.clay-modal');
            if (modal) {
                closeModal(modal.id);
            }
        }
    });
    
    // Fermeture par Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.clay-modal:not(.clay-modal-hidden)');
            if (openModal) {
                closeModal(openModal.id);
            }
        }
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('clay-modal-hidden');
        document.body.classList.add('clay-modal-open');
        
        // Focus sur le premier élément focusable
        const focusable = modal.querySelector('input, textarea, select, button');
        if (focusable) {
            setTimeout(() => focusable.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('clay-modal-hidden');
        document.body.classList.remove('clay-modal-open');
    }
}

// Calcul automatique pour les montants
function initAutoCalculation() {
    const forms = document.querySelectorAll('.clay-form');
    
    forms.forEach(form => {
        const quantInput = form.querySelector('#QUANT');
        const coutInput = form.querySelector('#COUT');
        const montantInput = form.querySelector('#MONTANT');
        const montantDisplay = form.querySelector('#montant-display');
        
        if (quantInput && coutInput && (montantInput || montantDisplay)) {
            function calculate() {
                const quant = parseFloat(quantInput.value) || 0;
                const cout = parseFloat(coutInput.value) || 0;
                const total = quant * cout;
                
                if (montantInput) {
                    montantInput.value = total.toFixed(2);
                }
                
                if (montantDisplay) {
                    montantDisplay.textContent = total.toFixed(2) + ' €';
                    montantDisplay.style.transform = 'scale(1.1)';
                    setTimeout(() => {
                        montantDisplay.style.transform = 'scale(1)';
                    }, 200);
                }
            }
            
            quantInput.addEventListener('input', calculate);
            coutInput.addEventListener('input', calculate);
        }
    });
}

// Gestion des messages flash
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.clay-flash');
    
    flashMessages.forEach((flash, index) => {
        // Animation d'entrée décalée
        flash.style.animationDelay = `${index * 0.1}s`;
        
        // Auto-suppression après 5 secondes
        setTimeout(() => {
            hideFlashMessage(flash);
        }, 5000 + (index * 100));
    });
}

function hideFlashMessage(flashElement) {
    // Ajouter l'animation CSS si elle n'existe pas
    if (!document.querySelector('#flash-animation-styles')) {
        const style = document.createElement('style');
        style.id = 'flash-animation-styles';
        style.textContent = `
            @keyframes clay-slide-out {
                0% {
                    transform: translateX(0);
                    opacity: 1;
                }
                100% {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    flashElement.style.animation = 'clay-slide-out 0.3s ease-in forwards';
    setTimeout(() => {
        if (flashElement.parentElement) {
            flashElement.parentElement.removeChild(flashElement);
        }
    }, 300);
}

// Confirmation de suppression améliorée
function confirmDelete(type, name) {
    return confirm(`Êtes-vous sûr de vouloir supprimer ${type} "${name}" ?\n\nCette action est irréversible.`);
}

// Amélioration des confirmations dans les formulaires
function initDeleteConfirmations() {
    const deleteForms = document.querySelectorAll('form[onsubmit*="confirm"]');
    
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const action = this.action;
            const name = this.dataset.itemName || 'cet élément';
            const type = this.dataset.itemType || 'élément';
            
            if (!confirmDelete(type, name)) {
                e.preventDefault();
                return false;
            }
            
            // Ajouter un indicateur de chargement
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                const removeLoading = addLoadingToButton(submitBtn, 'Suppression...');
                
                // Supprimer le loading si l'utilisateur annule
                setTimeout(() => {
                    if (submitBtn.disabled) {
                        removeLoading();
                    }
                }, 100);
            }
        });
    });
}

// Mise à jour de l'initialisation
document.addEventListener('DOMContentLoaded', function() {
    initStaggeredAnimations();
    initializeFormValidation(); // Utilise la fonction unifiée
    initModalHandlers();
    initAutoCalculation();
    initFlashMessages();
    initDeleteConfirmations();
    
    // Ajouter les effets ripple aux boutons existants
    addRippleEffect();
    
    console.log('🎨 Interface claymorphism initialisée avec gestion d\'erreurs !');
});

/**
 * ==========================================================================
 * TRAVAUX DEMANDÉS - FONCTIONNALITÉS AVANCÉES
 * ==========================================================================
 */

/**
 * Basculer entre vue cartes et tableau
 */
function switchView(view) {
    currentView = view;
    
    // Mettre à jour les boutons
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-view="${view}"]`).classList.add('active');
    
    // Basculer les vues avec animation
    const cardsView = document.getElementById('cardsView');
    const tableView = document.getElementById('tableView');
    
    if (view === 'cards') {
        tableView.style.display = 'none';
        cardsView.style.display = 'grid';
        animateCardsEntrance();
    } else {
        cardsView.style.display = 'none';
        tableView.style.display = 'block';
        enhanceTableInteractions();
    }
    
    // Sauvegarder la préférence
    localStorage.setItem('workOrdersView', view);
}

/**
 * Animation d'entrée pour les cartes
 */
function animateCardsEntrance() {
    const cards = document.querySelectorAll('.work-order-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

/**
 * Améliorer les interactions du tableau
 */
function enhanceTableInteractions() {
    const table = document.getElementById('workOrdersTable');
    if (!table) return;
    
    // Tri par colonne
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        if (index < headers.length - 1) { // Pas la colonne actions
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';
            header.addEventListener('click', () => sortTable(index));
            
            // Ajouter indicateur de tri
            if (!header.querySelector('.sort-indicator')) {
                const indicator = document.createElement('i');
                indicator.className = 'fas fa-sort sort-indicator';
                indicator.style.marginLeft = '0.5rem';
                indicator.style.opacity = '0.5';
                header.appendChild(indicator);
            }
        }
    });
    
    // Sélection multiple avec Ctrl+Click
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.addEventListener('click', (e) => {
            if (e.ctrlKey || e.metaKey) {
                toggleRowSelection(row);
            } else {
                selectSingleRow(row);
            }
        });
    });
}

/**
 * Tri du tableau
 */
function sortTable(columnIndex) {
    const table = document.getElementById('workOrdersTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Déterminer la direction du tri
    const currentHeader = table.querySelectorAll('th')[columnIndex];
    const indicator = currentHeader.querySelector('.sort-indicator');
    
    if (sortColumn === columnIndex) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortDirection = 'asc';
        // Réinitialiser les autres indicateurs
        table.querySelectorAll('.sort-indicator').forEach(ind => {
            ind.className = 'fas fa-sort sort-indicator';
        });
    }
    
    sortColumn = columnIndex;
    
    // Mettre à jour l'indicateur
    indicator.className = `fas fa-sort-${sortDirection === 'asc' ? 'up' : 'down'} sort-indicator`;
    
    // Trier les lignes
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();
        
        // Tri numérique pour certaines colonnes
        if (columnIndex === 6) { // Colonne produits
            const aNum = parseInt(aText) || 0;
            const bNum = parseInt(bText) || 0;
            return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // Tri par date
        if (columnIndex === 7) {
            const aDate = new Date(aText.split(' ').reverse().join(' '));
            const bDate = new Date(bText.split(' ').reverse().join(' '));
            return sortDirection === 'asc' ? aDate - bDate : bDate - aDate;
        }
        
        // Tri alphabétique
        return sortDirection === 'asc' 
            ? aText.localeCompare(bText)
            : bText.localeCompare(aText);
    });
    
    // Réinsérer les lignes triées avec animation
    rows.forEach((row, index) => {
        row.style.transform = 'translateX(-100%)';
        row.style.opacity = '0';
        setTimeout(() => {
            tbody.appendChild(row);
            row.style.transition = 'all 0.3s ease';
            row.style.transform = 'translateX(0)';
            row.style.opacity = '1';
        }, index * 20);
    });
}

/**
 * Sélection de ligne unique
 */
function selectSingleRow(row) {
    // Désélectionner toutes les autres lignes
    document.querySelectorAll('tr.selected').forEach(r => r.classList.remove('selected'));
    selectedWorkOrders.clear();
    
    // Sélectionner la ligne actuelle
    row.classList.add('selected');
    selectedWorkOrders.add(row.dataset.id);
    
    updateSelectionInfo();
}

/**
 * Basculer la sélection d'une ligne
 */
function toggleRowSelection(row) {
    const id = row.dataset.id;
    
    if (row.classList.contains('selected')) {
        row.classList.remove('selected');
        selectedWorkOrders.delete(id);
    } else {
        row.classList.add('selected');
        selectedWorkOrders.add(id);
    }
    
    updateSelectionInfo();
}

/**
 * Sélectionner un travail (pour cartes et tableau)
 */
function selectWorkOrder(element) {
    if (currentView === 'cards') {
        // Désélectionner toutes les autres cartes
        document.querySelectorAll('.work-order-card.selected').forEach(card => {
            card.classList.remove('selected');
        });
        selectedWorkOrders.clear();
        
        // Sélectionner la carte actuelle
        element.classList.add('selected');
        selectedWorkOrders.add(element.dataset.id);
    }
    
    updateSelectionInfo();
}

/**
 * Mettre à jour les informations de sélection
 */
function updateSelectionInfo() {
    const count = selectedWorkOrders.size;
    const itemsCount = document.getElementById('itemsCount');
    
    // Vérifier que l'élément existe avant de le modifier
    if (!itemsCount) {
        return;
    }
    
    if (count > 0) {
        itemsCount.textContent = `${count} sélectionné(s)`;
        itemsCount.style.color = 'var(--clay-accent-primary)';
        itemsCount.style.fontWeight = '600';
    } else {
        const totalItems = document.querySelectorAll(currentView === 'cards' ? '.work-order-card' : '#workOrdersTable tbody tr').length;
        itemsCount.textContent = `${totalItems} travaux`;
        itemsCount.style.color = 'var(--clay-text-secondary)';
        itemsCount.style.fontWeight = '500';
    }
}

/**
 * Recherche avancée avec highlighting
 */
function handleSearchKeyup(event) {
    const searchTerm = event.target.value.toLowerCase();
    
    if (event.key === 'Enter') {
        performSearch(searchTerm);
    } else {
        // Recherche en temps réel avec debounce
        clearTimeout(window.searchTimeout);
        window.searchTimeout = setTimeout(() => {
            performSearch(searchTerm);
        }, 300);
    }
}

/**
 * Effectuer la recherche
 */
function performSearch(searchTerm) {
    const items = currentView === 'cards' 
        ? document.querySelectorAll('.work-order-card')
        : document.querySelectorAll('#workOrdersTable tbody tr');
    
    let visibleCount = 0;
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        const isVisible = searchTerm === '' || text.includes(searchTerm);
        
        if (isVisible) {
            item.style.display = '';
            visibleCount++;
            
            // Highlighting du terme recherché
            if (searchTerm !== '') {
                highlightSearchTerm(item, searchTerm);
            } else {
                removeHighlights(item);
            }
        } else {
            item.style.display = 'none';
        }
    });
    
    // Mettre à jour le compteur
    const itemsCount = document.getElementById('itemsCount');
    if (itemsCount) {
        itemsCount.textContent = `${visibleCount} travaux${searchTerm ? ' trouvés' : ''}`;
    }
}

/**
 * Surligner le terme recherché
 */
function highlightSearchTerm(element, term) {
    // Retirer les anciens highlights
    removeHighlights(element);
    
    const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    const textNodes = [];
    let node;
    
    while (node = walker.nextNode()) {
        if (node.textContent.toLowerCase().includes(term)) {
            textNodes.push(node);
        }
    }
    
    textNodes.forEach(textNode => {
        const text = textNode.textContent;
        const regex = new RegExp(`(${term})`, 'gi');
        const highlightedText = text.replace(regex, '<mark class="search-highlight">$1</mark>');
        
        if (highlightedText !== text) {
            const wrapper = document.createElement('span');
            wrapper.innerHTML = highlightedText;
            textNode.parentNode.replaceChild(wrapper, textNode);
        }
    });
}

/**
 * Retirer les highlights
 */
function removeHighlights(element) {
    const highlights = element.querySelectorAll('.search-highlight');
    highlights.forEach(highlight => {
        const parent = highlight.parentNode;
        parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
        parent.normalize();
    });
}

/**
 * Appliquer les filtres
 */
function applyFilters() {
    const statusFilter = document.getElementById('statusFilter').value;
    const priorityFilter = document.getElementById('priorityFilter').value;
    const technicianFilter = document.getElementById('technicianFilter').value;
    
    const items = currentView === 'cards' 
        ? document.querySelectorAll('.work-order-card')
        : document.querySelectorAll('#workOrdersTable tbody tr');
    
    let visibleCount = 0;
    
    items.forEach(item => {
        const status = getItemAttribute(item, 'status');
        const priority = getItemAttribute(item, 'priority');
        const technician = getItemAttribute(item, 'technician');
        
        const statusMatch = !statusFilter || status === statusFilter;
        const priorityMatch = !priorityFilter || priority === priorityFilter;
        const technicianMatch = !technicianFilter || technician === technicianFilter;
        
        if (statusMatch && priorityMatch && technicianMatch) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Mettre à jour le compteur
    const itemsCount = document.getElementById('itemsCount');
    if (itemsCount) {
        itemsCount.textContent = `${visibleCount} travaux filtrés`;
    }
}

/**
 * Obtenir un attribut d'un élément (carte ou ligne)
 */
function getItemAttribute(item, attribute) {
    if (currentView === 'cards') {
        switch (attribute) {
            case 'status':
                const statusBadge = item.querySelector('.status-badge');
                return statusBadge ? statusBadge.className.match(/status-(\w+)/)?.[1] : '';
            case 'priority':
                const priorityBadge = item.querySelector('.priority-badge');
                return priorityBadge ? priorityBadge.className.match(/priority-(\w+)/)?.[1] : '';
            case 'technician':
                const technicianSpan = item.querySelector('.technician-assigned');
                return technicianSpan ? technicianSpan.textContent.trim() : '';
            default:
                return '';
        }
    } else {
        // Pour le tableau, utiliser les données dans les cellules
        const cells = item.querySelectorAll('td');
        switch (attribute) {
            case 'status':
                return cells[3]?.querySelector('.status-badge')?.className.match(/status-(\w+)/)?.[1] || '';
            case 'priority':
                return cells[4]?.querySelector('.priority-badge')?.className.match(/priority-(\w+)/)?.[1] || '';
            case 'technician':
                return cells[5]?.textContent.trim() || '';
            default:
                return '';
        }
    }
}

/**
 * Actualiser la liste des travaux
 */
function refreshWorkOrders() {
    // Animation de chargement
    const container = document.querySelector('.work-orders-container');
    container.classList.add('clay-loading');
    
    // Simuler le rechargement (remplacer par un appel AJAX réel)
    setTimeout(() => {
        container.classList.remove('clay-loading');
        location.reload(); // Pour l'instant, rechargement complet
    }, 1000);
}

/**
 * Raccourcis clavier
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Échapper pour désélectionner
        if (e.key === 'Escape') {
            clearSelection();
        }
        
        // Ctrl+A pour tout sélectionner
        if (e.ctrlKey && e.key === 'a') {
            e.preventDefault();
            selectAll();
        }
        
        // F2 pour basculer la vue
        if (e.key === 'F2') {
            e.preventDefault();
            switchView(currentView === 'cards' ? 'table' : 'cards');
        }
        
        // F4 pour modifier le premier sélectionné
        if (e.key === 'F4' && selectedWorkOrders.size > 0) {
            e.preventDefault();
            const firstSelected = Array.from(selectedWorkOrders)[0];
            editWorkOrder(firstSelected);
        }
        
        // F8 pour voir les produits
        if (e.key === 'F8' && selectedWorkOrders.size > 0) {
            e.preventDefault();
            const firstSelected = Array.from(selectedWorkOrders)[0];
            viewProducts(firstSelected);
        }
        
        // F9 pour supprimer
        if (e.key === 'F9' && selectedWorkOrders.size > 0) {
            e.preventDefault();
            const firstSelected = Array.from(selectedWorkOrders)[0];
            const element = document.querySelector(`[data-id="${firstSelected}"]`);
            if (element) {
                const claimElement = element.querySelector('.claim-number, .claim-compact');
                const claimNumber = claimElement ? claimElement.textContent : 'Élément sélectionné';
                if (confirmDelete('travail demandé', claimNumber)) {
                    // Rediriger vers la suppression ou exécuter l'action de suppression
                    deleteWorkOrder(firstSelected);
                }
            }
        }
    });
}

/**
 * Désélectionner tout
 */
function clearSelection() {
    document.querySelectorAll('.selected').forEach(item => {
        item.classList.remove('selected');
    });
    selectedWorkOrders.clear();
    updateSelectionInfo();
}

/**
 * Sélectionner tout
 */
function selectAll() {
    const items = currentView === 'cards' 
        ? document.querySelectorAll('.work-order-card')
        : document.querySelectorAll('#workOrdersTable tbody tr');
    
    items.forEach(item => {
        if (item.style.display !== 'none') {
            item.classList.add('selected');
        }
    });
    
    showNotification(`${items.length} éléments sélectionnés`, 'info');
}

/**
 * Initialisation des travaux demandés
 */
function initializeWorkOrders() {
    // Restaurer la vue préférée
    const savedView = localStorage.getItem('workOrdersView') || 'cards';
    switchView(savedView);
    
    // Configurer les raccourcis clavier
    setupKeyboardShortcuts();
    
    // Améliorer les interactions
    enhanceTableInteractions();
    
    console.log('✅ Module Travaux Demandés initialisé');
}

// CSS pour le highlighting
const searchStyles = `
    .search-highlight {
        background: var(--clay-warning);
        color: var(--clay-text-primary);
        padding: 0.125rem 0.25rem;
        border-radius: 3px;
        font-weight: 600;
    }
    
    .sort-indicator {
        transition: var(--clay-transition);
    }
    
    .sort-indicator:hover {
        opacity: 1 !important;
    }
`;

// Ajouter les styles
if (!document.querySelector('#search-styles')) {
    const style = document.createElement('style');
    style.id = 'search-styles';
    style.textContent = searchStyles;
    document.head.appendChild(style);
}

// Initialiser quand la page est chargée
document.addEventListener('DOMContentLoaded', function() {
    if (document.querySelector('.work-orders-container')) {
        initializeWorkOrders();
    }
});

/**
 * Éditer un travail demandé
 */
function editWorkOrder(workOrderId) {
    if (!workOrderId) {
        console.warn('ID du travail demandé manquant');
        return;
    }
    
    // Rediriger vers la page d'édition
    window.location.href = `/work_order_lines/${workOrderId}/edit`;
}

/**
 * Voir les produits d'un travail demandé
 */
function viewProducts(workOrderId) {
    if (!workOrderId) {
        console.warn('ID du travail demandé manquant');
        return;
    }
    
    // Rediriger vers la page des produits
    window.location.href = `/work_order_lines/${workOrderId}/products`;
}

/**
 * Supprimer un travail demandé
 */
function deleteWorkOrder(workOrderId) {
    if (!workOrderId) {
        console.warn('ID du travail demandé manquant');
        return;
    }
    
    // Créer un formulaire temporaire pour la suppression
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/work_order_lines/${workOrderId}/delete`;
    form.style.display = 'none';
    
    // Ajouter le token CSRF si disponible
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken.getAttribute('content');
        form.appendChild(csrfInput);
    }
    
    document.body.appendChild(form);
    form.submit();
}

// CSS pour le loader global
const globalLoaderStyles = `
    .global-loader {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        display: none;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    .loader-content {
        text-align: center;
        padding: 2rem;
        background: var(--clay-card-bg, #ffffff);
        border-radius: 1rem;
        box-shadow: var(--clay-shadow-elevated, 0 20px 50px rgba(0, 0, 0, 0.1));
    }
    
    .clay-spinner {
        width: 40px;
        height: 40px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid var(--primary-color, #007bff);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 1rem;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;

// Ajouter les styles du loader global
if (!document.getElementById('global-loader-styles')) {
    const style = document.createElement('style');
    style.id = 'global-loader-styles';
    style.textContent = globalLoaderStyles;
    document.head.appendChild(style);
}
