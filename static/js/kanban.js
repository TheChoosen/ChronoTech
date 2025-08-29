/**
 * JavaScript Kanban Board - Sprint 3
 * Bibliothèque spécialisée pour interface Kanban drag & drop
 */

class KanbanBoard {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            columns: ['pending', 'assigned', 'in-progress', 'done'],
            editable: true,
            sortable: true,
            onTaskMove: null,
            onTaskClick: null,
            ...options
        };
        
        this.tasks = [];
        this.draggedTask = null;
        this.dropZones = [];
        
        this.init();
    }
    
    init() {
        this.setupBoard();
        this.setupEventListeners();
    }
    
    setupBoard() {
        this.container.className = 'kanban-board';
        this.container.innerHTML = '';
        
        this.options.columns.forEach(columnId => {
            const column = this.createColumn(columnId);
            this.container.appendChild(column);
        });
    }
    
    createColumn(columnId) {
        const column = document.createElement('div');
        column.className = 'kanban-column';
        column.dataset.status = columnId;
        
        column.innerHTML = `
            <div class="column-header">
                <h3 class="column-title">${this.getColumnTitle(columnId)}</h3>
                <span class="column-count">0</span>
            </div>
            <div class="column-body" data-column="${columnId}">
                <div class="drop-zone">
                    Glissez une tâche ici
                </div>
            </div>
        `;
        
        return column;
    }
    
    getColumnTitle(columnId) {
        const titles = {
            pending: 'En attente',
            assigned: 'Assigné',
            'in-progress': 'En cours',
            done: 'Terminé',
            cancelled: 'Annulé'
        };
        return titles[columnId] || columnId;
    }
    
    setupEventListeners() {
        // Drag & Drop
        this.container.addEventListener('dragstart', this.handleDragStart.bind(this));
        this.container.addEventListener('dragover', this.handleDragOver.bind(this));
        this.container.addEventListener('drop', this.handleDrop.bind(this));
        this.container.addEventListener('dragend', this.handleDragEnd.bind(this));
        
        // Click events
        this.container.addEventListener('click', this.handleClick.bind(this));
        
        // Touch events pour mobile
        this.container.addEventListener('touchstart', this.handleTouchStart.bind(this));
        this.container.addEventListener('touchmove', this.handleTouchMove.bind(this));
        this.container.addEventListener('touchend', this.handleTouchEnd.bind(this));
    }
    
    // ===== DRAG & DROP =====
    
    handleDragStart(e) {
        if (!e.target.classList.contains('task-card')) return;
        
        this.draggedTask = e.target;
        e.target.classList.add('dragging');
        
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', e.target.outerHTML);
        
        // Masquer les drop zones vides
        this.showDropZones();
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const dropZone = e.target.closest('.column-body');
        if (dropZone && this.draggedTask) {
            this.highlightDropZone(dropZone);
            this.positionDropPlaceholder(dropZone, e.clientY);
        }
    }
    
    handleDrop(e) {
        e.preventDefault();
        
        const dropZone = e.target.closest('.column-body');
        if (!dropZone || !this.draggedTask) return;
        
        const newColumn = dropZone.dataset.column;
        const oldColumn = this.draggedTask.closest('.column-body').dataset.column;
        
        if (newColumn !== oldColumn) {
            this.moveTask(this.draggedTask, newColumn, dropZone);
        }
        
        this.clearDropEffects();
    }
    
    handleDragEnd(e) {
        if (e.target.classList.contains('task-card')) {
            e.target.classList.remove('dragging');
        }
        
        this.clearDropEffects();
        this.draggedTask = null;
    }
    
    // ===== TOUCH SUPPORT =====
    
    handleTouchStart(e) {
        if (!e.target.classList.contains('task-card')) return;
        
        this.touchStartTime = Date.now();
        this.touchStartPos = {
            x: e.touches[0].clientX,
            y: e.touches[0].clientY
        };
        
        // Démarrer le drag après un long press
        this.longPressTimer = setTimeout(() => {
            this.startTouchDrag(e.target);
        }, 500);
    }
    
    handleTouchMove(e) {
        if (this.longPressTimer) {
            const touch = e.touches[0];
            const distance = Math.sqrt(
                Math.pow(touch.clientX - this.touchStartPos.x, 2) +
                Math.pow(touch.clientY - this.touchStartPos.y, 2)
            );
            
            if (distance > 10) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
        }
        
        if (this.draggedTask) {
            e.preventDefault();
            this.updateTouchDrag(e.touches[0]);
        }
    }
    
    handleTouchEnd(e) {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        
        if (this.draggedTask) {
            this.endTouchDrag(e.changedTouches[0]);
        }
    }
    
    startTouchDrag(element) {
        this.draggedTask = element;
        element.classList.add('touch-dragging');
        
        // Créer un clone pour le feedback visuel
        this.createDragClone(element);
        this.showDropZones();
    }
    
    updateTouchDrag(touch) {
        if (this.dragClone) {
            this.dragClone.style.left = touch.clientX - 50 + 'px';
            this.dragClone.style.top = touch.clientY - 25 + 'px';
        }
        
        // Détecter la zone de drop
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
        const dropZone = elementBelow ? elementBelow.closest('.column-body') : null;
        
        if (dropZone) {
            this.highlightDropZone(dropZone);
        }
    }
    
    endTouchDrag(touch) {
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
        const dropZone = elementBelow ? elementBelow.closest('.column-body') : null;
        
        if (dropZone && this.draggedTask) {
            const newColumn = dropZone.dataset.column;
            const oldColumn = this.draggedTask.closest('.column-body').dataset.column;
            
            if (newColumn !== oldColumn) {
                this.moveTask(this.draggedTask, newColumn, dropZone);
            }
        }
        
        this.cleanupTouchDrag();
    }
    
    createDragClone(element) {
        this.dragClone = element.cloneNode(true);
        this.dragClone.classList.add('drag-clone');
        this.dragClone.style.position = 'fixed';
        this.dragClone.style.pointerEvents = 'none';
        this.dragClone.style.zIndex = '1000';
        this.dragClone.style.opacity = '0.8';
        this.dragClone.style.transform = 'rotate(5deg)';
        
        document.body.appendChild(this.dragClone);
    }
    
    cleanupTouchDrag() {
        if (this.draggedTask) {
            this.draggedTask.classList.remove('touch-dragging');
        }
        
        if (this.dragClone) {
            document.body.removeChild(this.dragClone);
            this.dragClone = null;
        }
        
        this.clearDropEffects();
        this.draggedTask = null;
    }
    
    // ===== GESTION DES TÂCHES =====
    
    moveTask(taskElement, newColumn, dropZone) {
        const taskId = taskElement.dataset.taskId;
        const oldColumn = taskElement.closest('.column-body').dataset.column;
        
        // Animation de déplacement
        taskElement.style.transition = 'transform 0.2s ease';
        taskElement.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            // Déplacer physiquement l'élément
            const placeholder = dropZone.querySelector('.drop-placeholder');
            if (placeholder) {
                dropZone.insertBefore(taskElement, placeholder);
                dropZone.removeChild(placeholder);
            } else {
                // Trouver la position d'insertion
                const tasks = Array.from(dropZone.querySelectorAll('.task-card'));
                let insertBefore = null;
                
                for (let task of tasks) {
                    if (task === taskElement) continue;
                    
                    const rect = task.getBoundingClientRect();
                    const dropZoneRect = dropZone.getBoundingClientRect();
                    
                    if (this.lastDropY < rect.top + rect.height / 2) {
                        insertBefore = task;
                        break;
                    }
                }
                
                if (insertBefore) {
                    dropZone.insertBefore(taskElement, insertBefore);
                } else {
                    dropZone.appendChild(taskElement);
                }
            }
            
            // Réinitialiser les styles
            taskElement.style.transition = '';
            taskElement.style.transform = '';
            
            // Mettre à jour les compteurs
            this.updateColumnCounts();
            
            // Callback
            if (this.options.onTaskMove) {
                this.options.onTaskMove(taskId, newColumn, oldColumn);
            }
        }, 100);
    }
    
    addTask(task, columnId = null) {
        const taskElement = this.createTaskElement(task);
        const column = columnId ? 
            this.container.querySelector(`[data-column="${columnId}"] .column-body`) :
            this.container.querySelector(`[data-column="${task.status}"] .column-body`);
        
        if (column) {
            // Retirer la drop zone si c'est la première tâche
            const dropZone = column.querySelector('.drop-zone');
            if (dropZone && column.children.length === 1) {
                dropZone.style.display = 'none';
            }
            
            column.appendChild(taskElement);
            this.updateColumnCounts();
        }
        
        this.tasks.push(task);
        return taskElement;
    }
    
    removeTask(taskId) {
        const taskElement = this.container.querySelector(`[data-task-id="${taskId}"]`);
        if (taskElement) {
            const column = taskElement.closest('.column-body');
            taskElement.remove();
            
            // Réafficher la drop zone si plus de tâches
            if (column.querySelectorAll('.task-card').length === 0) {
                const dropZone = column.querySelector('.drop-zone');
                if (dropZone) {
                    dropZone.style.display = 'flex';
                }
            }
            
            this.updateColumnCounts();
        }
        
        this.tasks = this.tasks.filter(task => task.id !== taskId);
    }
    
    updateTask(taskId, updates) {
        const taskIndex = this.tasks.findIndex(task => task.id === taskId);
        if (taskIndex !== -1) {
            this.tasks[taskIndex] = { ...this.tasks[taskIndex], ...updates };
            
            const taskElement = this.container.querySelector(`[data-task-id="${taskId}"]`);
            if (taskElement) {
                this.updateTaskElement(taskElement, this.tasks[taskIndex]);
            }
        }
    }
    
    createTaskElement(task) {
        const element = document.createElement('div');
        element.className = 'task-card';
        element.draggable = this.options.sortable;
        element.dataset.taskId = task.id;
        element.dataset.priority = task.priority || 'medium';
        
        element.innerHTML = `
            <div class="task-header">
                <span class="task-id">#${task.id}</span>
                <span class="task-priority ${task.priority || 'medium'}">${(task.priority || 'medium').toUpperCase()}</span>
            </div>
            <div class="task-title">${task.title}</div>
            <div class="task-customer">${task.customer_name || 'Client non défini'}</div>
            ${task.description ? `<div class="task-description">${task.description}</div>` : ''}
            <div class="task-meta">
                <div class="task-technician">
                    <div class="technician-avatar">${this.getInitials(task.technician_name)}</div>
                    <span>${task.technician_name || 'Non assigné'}</span>
                </div>
                <div class="task-time">${this.formatTime(task.estimated_minutes)}</div>
            </div>
        `;
        
        return element;
    }
    
    updateTaskElement(element, task) {
        element.dataset.priority = task.priority || 'medium';
        
        const title = element.querySelector('.task-title');
        if (title) title.textContent = task.title;
        
        const priority = element.querySelector('.task-priority');
        if (priority) {
            priority.textContent = (task.priority || 'medium').toUpperCase();
            priority.className = `task-priority ${task.priority || 'medium'}`;
        }
        
        const customer = element.querySelector('.task-customer');
        if (customer) customer.textContent = task.customer_name || 'Client non défini';
        
        const technician = element.querySelector('.task-technician span');
        if (technician) technician.textContent = task.technician_name || 'Non assigné';
        
        const avatar = element.querySelector('.technician-avatar');
        if (avatar) avatar.textContent = this.getInitials(task.technician_name);
        
        const time = element.querySelector('.task-time');
        if (time) time.textContent = this.formatTime(task.estimated_minutes);
    }
    
    // ===== EFFETS VISUELS =====
    
    showDropZones() {
        this.container.querySelectorAll('.drop-zone').forEach(zone => {
            if (zone.parentElement.querySelectorAll('.task-card').length === 0) {
                zone.style.display = 'flex';
            }
        });
    }
    
    highlightDropZone(dropZone) {
        // Réinitialiser tous les highlights
        this.container.querySelectorAll('.column-body').forEach(zone => {
            zone.classList.remove('drag-over');
        });
        
        // Surligner la zone courante
        dropZone.classList.add('drag-over');
    }
    
    positionDropPlaceholder(dropZone, clientY) {
        // Supprimer les placeholders existants
        this.container.querySelectorAll('.drop-placeholder').forEach(placeholder => {
            placeholder.remove();
        });
        
        // Sauvegarder la position pour le touch
        this.lastDropY = clientY;
        
        // Créer un nouveau placeholder
        const placeholder = document.createElement('div');
        placeholder.className = 'drop-placeholder';
        placeholder.textContent = 'Déposer ici';
        
        // Trouver la position d'insertion
        const tasks = Array.from(dropZone.querySelectorAll('.task-card:not(.dragging)'));
        let insertBefore = null;
        
        const dropZoneRect = dropZone.getBoundingClientRect();
        const relativeY = clientY - dropZoneRect.top;
        
        for (let task of tasks) {
            const taskRect = task.getBoundingClientRect();
            const taskRelativeY = taskRect.top - dropZoneRect.top + taskRect.height / 2;
            
            if (relativeY < taskRelativeY) {
                insertBefore = task;
                break;
            }
        }
        
        if (insertBefore) {
            dropZone.insertBefore(placeholder, insertBefore);
        } else {
            dropZone.appendChild(placeholder);
        }
    }
    
    clearDropEffects() {
        // Supprimer les highlights
        this.container.querySelectorAll('.column-body').forEach(zone => {
            zone.classList.remove('drag-over');
        });
        
        // Supprimer les placeholders
        this.container.querySelectorAll('.drop-placeholder').forEach(placeholder => {
            placeholder.remove();
        });
        
        // Masquer les drop zones si nécessaire
        this.container.querySelectorAll('.drop-zone').forEach(zone => {
            if (zone.parentElement.querySelectorAll('.task-card').length > 0) {
                zone.style.display = 'none';
            }
        });
    }
    
    updateColumnCounts() {
        this.container.querySelectorAll('.kanban-column').forEach(column => {
            const tasks = column.querySelectorAll('.task-card');
            const count = column.querySelector('.column-count');
            if (count) {
                count.textContent = tasks.length;
            }
        });
    }
    
    // ===== EVENTS =====
    
    handleClick(e) {
        const taskCard = e.target.closest('.task-card');
        if (taskCard && this.options.onTaskClick) {
            const taskId = taskCard.dataset.taskId;
            this.options.onTaskClick(taskId, taskCard);
        }
    }
    
    // ===== UTILITAIRES =====
    
    getInitials(name) {
        if (!name) return '?';
        return name.split(' ')
            .map(word => word[0])
            .join('')
            .substr(0, 2)
            .toUpperCase();
    }
    
    formatTime(minutes) {
        if (!minutes) return '';
        
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        
        if (hours > 0) {
            return `${hours}h${mins > 0 ? mins + 'm' : ''}`;
        } else {
            return `${mins}m`;
        }
    }
    
    // ===== API PUBLIQUE =====
    
    loadTasks(tasks) {
        // Vider le board
        this.container.querySelectorAll('.task-card').forEach(task => task.remove());
        this.tasks = [];
        
        // Ajouter les nouvelles tâches
        tasks.forEach(task => {
            this.addTask(task);
        });
    }
    
    getTasksByColumn(columnId) {
        return this.tasks.filter(task => task.status === columnId);
    }
    
    getTask(taskId) {
        return this.tasks.find(task => task.id === taskId);
    }
    
    setOptions(options) {
        this.options = { ...this.options, ...options };
    }
    
    destroy() {
        this.container.innerHTML = '';
        this.tasks = [];
        this.draggedTask = null;
    }
    
    // ===== FILTRES =====
    
    filterTasks(filterFn) {
        this.container.querySelectorAll('.task-card').forEach(taskElement => {
            const taskId = taskElement.dataset.taskId;
            const task = this.getTask(taskId);
            
            if (task && filterFn(task)) {
                taskElement.style.display = 'block';
            } else {
                taskElement.style.display = 'none';
            }
        });
        
        this.updateColumnCounts();
    }
    
    clearFilters() {
        this.container.querySelectorAll('.task-card').forEach(taskElement => {
            taskElement.style.display = 'block';
        });
        
        this.updateColumnCounts();
    }
    
    // ===== RECHERCHE =====
    
    searchTasks(query) {
        const searchQuery = query.toLowerCase();
        
        this.filterTasks(task => {
            return task.title.toLowerCase().includes(searchQuery) ||
                   (task.description && task.description.toLowerCase().includes(searchQuery)) ||
                   (task.customer_name && task.customer_name.toLowerCase().includes(searchQuery)) ||
                   (task.technician_name && task.technician_name.toLowerCase().includes(searchQuery));
        });
    }
    
    // ===== ANIMATIONS =====
    
    animateTaskAdd(taskElement) {
        taskElement.style.transform = 'scale(0) rotate(180deg)';
        taskElement.style.opacity = '0';
        
        requestAnimationFrame(() => {
            taskElement.style.transition = 'all 0.3s ease';
            taskElement.style.transform = 'scale(1) rotate(0deg)';
            taskElement.style.opacity = '1';
            
            setTimeout(() => {
                taskElement.style.transition = '';
            }, 300);
        });
    }
    
    animateTaskRemove(taskElement, callback) {
        taskElement.style.transition = 'all 0.3s ease';
        taskElement.style.transform = 'scale(0) rotate(-180deg)';
        taskElement.style.opacity = '0';
        
        setTimeout(() => {
            if (callback) callback();
        }, 300);
    }
}

// Export pour utilisation
window.KanbanBoard = KanbanBoard;
