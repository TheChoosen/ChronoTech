/**
 * ChronoTech - Système d'Annotations Visuelles Sprint 3
 * Interface canvas pour annotations sur photos
 */

class VisualAnnotationTool {
    constructor(canvasId, imageUrl, workOrderId, attachmentId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.imageUrl = imageUrl;
        this.workOrderId = workOrderId;
        this.attachmentId = attachmentId;
        
        this.image = new Image();
        this.annotations = [];
        this.currentTool = 'select';
        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.currentAnnotation = null;
        this.selectedAnnotation = null;
        
        // Configuration des outils
        this.tools = {
            select: { cursor: 'default' },
            arrow: { cursor: 'crosshair', color: '#ff0000', strokeWidth: 3 },
            circle: { cursor: 'crosshair', color: '#00ff00', strokeWidth: 3 },
            rectangle: { cursor: 'crosshair', color: '#0000ff', strokeWidth: 3 },
            text: { cursor: 'text', color: '#000000', fontSize: 16 },
            freehand: { cursor: 'crosshair', color: '#ff00ff', strokeWidth: 2 },
            highlight: { cursor: 'crosshair', color: '#ffff00', strokeWidth: 10, alpha: 0.3 }
        };
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.loadImage();
        this.bindEvents();
        this.loadExistingAnnotations();
    }
    
    setupCanvas() {
        // Configuration responsive du canvas
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
        
        // Style du curseur
        this.updateCursor();
    }
    
    resizeCanvas() {
        const container = this.canvas.parentElement;
        const rect = container.getBoundingClientRect();
        
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
        
        // Redessiner après redimensionnement
        this.redraw();
    }
    
    loadImage() {
        this.image.crossOrigin = 'anonymous';
        this.image.onload = () => {
            this.fitImageToCanvas();
            this.redraw();
        };
        this.image.src = this.imageUrl;
    }
    
    fitImageToCanvas() {
        const imgRatio = this.image.width / this.image.height;
        const canvasRatio = this.canvas.width / this.canvas.height;
        
        if (imgRatio > canvasRatio) {
            // Image plus large que le canvas
            this.imageWidth = this.canvas.width;
            this.imageHeight = this.canvas.width / imgRatio;
            this.imageX = 0;
            this.imageY = (this.canvas.height - this.imageHeight) / 2;
        } else {
            // Image plus haute que le canvas
            this.imageWidth = this.canvas.height * imgRatio;
            this.imageHeight = this.canvas.height;
            this.imageX = (this.canvas.width - this.imageWidth) / 2;
            this.imageY = 0;
        }
    }
    
    bindEvents() {
        // Événements souris
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('click', (e) => this.onClick(e));
        
        // Événements tactiles (mobile)
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.onTouchEnd(e));
        
        // Empêcher le scroll sur mobile
        this.canvas.addEventListener('touchmove', (e) => e.preventDefault());
    }
    
    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    getTouchPos(e) {
        const rect = this.canvas.getBoundingClientRect();
        const touch = e.touches[0] || e.changedTouches[0];
        return {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top
        };
    }
    
    onMouseDown(e) {
        const pos = this.getMousePos(e);
        this.startDrawing(pos.x, pos.y);
    }
    
    onMouseMove(e) {
        const pos = this.getMousePos(e);
        this.continueDrawing(pos.x, pos.y);
    }
    
    onMouseUp(e) {
        const pos = this.getMousePos(e);
        this.finishDrawing(pos.x, pos.y);
    }
    
    onClick(e) {
        if (this.currentTool === 'text') {
            const pos = this.getMousePos(e);
            this.addTextAnnotation(pos.x, pos.y);
        }
    }
    
    onTouchStart(e) {
        e.preventDefault();
        const pos = this.getTouchPos(e);
        this.startDrawing(pos.x, pos.y);
    }
    
    onTouchMove(e) {
        e.preventDefault();
        const pos = this.getTouchPos(e);
        this.continueDrawing(pos.x, pos.y);
    }
    
    onTouchEnd(e) {
        e.preventDefault();
        const pos = this.getTouchPos(e);
        this.finishDrawing(pos.x, pos.y);
    }
    
    startDrawing(x, y) {
        if (this.currentTool === 'select') {
            this.selectAnnotationAt(x, y);
            return;
        }
        
        this.isDrawing = true;
        this.startX = x;
        this.startY = y;
        
        // Créer une nouvelle annotation temporaire
        this.currentAnnotation = {
            id: 'temp_' + Date.now(),
            type: this.currentTool,
            coordinates: this.getInitialCoordinates(x, y),
            color: this.tools[this.currentTool].color,
            strokeWidth: this.tools[this.currentTool].strokeWidth,
            alpha: this.tools[this.currentTool].alpha || 1.0
        };
        
        if (this.currentTool === 'freehand') {
            this.currentAnnotation.coordinates = [{ x, y }];
        }
    }
    
    continueDrawing(x, y) {
        if (!this.isDrawing || !this.currentAnnotation) return;
        
        if (this.currentTool === 'freehand') {
            this.currentAnnotation.coordinates.push({ x, y });
        } else {
            this.updateAnnotationCoordinates(this.currentAnnotation, x, y);
        }
        
        this.redraw();
        this.drawAnnotation(this.currentAnnotation);
    }
    
    finishDrawing(x, y) {
        if (!this.isDrawing || !this.currentAnnotation) return;
        
        this.isDrawing = false;
        
        // Finaliser les coordonnées
        if (this.currentTool !== 'freehand') {
            this.updateAnnotationCoordinates(this.currentAnnotation, x, y);
        }
        
        // Vérifier que l'annotation est valide (pas juste un clic)
        if (this.isValidAnnotation(this.currentAnnotation)) {
            this.saveAnnotation(this.currentAnnotation);
        }
        
        this.currentAnnotation = null;
    }
    
    getInitialCoordinates(x, y) {
        return { x, y, width: 0, height: 0 };
    }
    
    updateAnnotationCoordinates(annotation, x, y) {
        const coords = annotation.coordinates;
        coords.width = x - coords.x;
        coords.height = y - coords.y;
    }
    
    isValidAnnotation(annotation) {
        if (annotation.type === 'freehand') {
            return annotation.coordinates.length > 2;
        }
        
        const coords = annotation.coordinates;
        return Math.abs(coords.width) > 5 || Math.abs(coords.height) > 5;
    }
    
    addTextAnnotation(x, y) {
        const text = prompt('Entrez votre annotation:');
        if (!text) return;
        
        const annotation = {
            id: 'temp_' + Date.now(),
            type: 'text',
            coordinates: { x, y },
            text_content: text,
            color: this.tools.text.color,
            fontSize: this.tools.text.fontSize
        };
        
        this.saveAnnotation(annotation);
    }
    
    selectAnnotationAt(x, y) {
        this.selectedAnnotation = null;
        
        // Rechercher l'annotation à la position cliquée (ordre inverse pour prendre la plus récente)
        for (let i = this.annotations.length - 1; i >= 0; i--) {
            if (this.isPointInAnnotation(x, y, this.annotations[i])) {
                this.selectedAnnotation = this.annotations[i];
                break;
            }
        }
        
        this.redraw();
        this.showContextMenu(x, y);
    }
    
    isPointInAnnotation(x, y, annotation) {
        const coords = annotation.coordinates;
        
        switch (annotation.type) {
            case 'rectangle':
            case 'highlight':
                return x >= coords.x && x <= coords.x + coords.width &&
                       y >= coords.y && y <= coords.y + coords.height;
            
            case 'circle':
                const centerX = coords.x + coords.width / 2;
                const centerY = coords.y + coords.height / 2;
                const radius = Math.max(Math.abs(coords.width), Math.abs(coords.height)) / 2;
                const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
                return distance <= radius;
            
            case 'text':
                // Zone approximative du texte
                const textWidth = annotation.text_content.length * (annotation.fontSize * 0.6);
                return x >= coords.x && x <= coords.x + textWidth &&
                       y >= coords.y - annotation.fontSize && y <= coords.y;
            
            case 'freehand':
                // Vérifier proximité avec la ligne
                return coords.some((point, i) => {
                    if (i === 0) return false;
                    const prevPoint = coords[i - 1];
                    return this.distanceToLine(x, y, prevPoint.x, prevPoint.y, point.x, point.y) < 10;
                });
            
            default:
                return false;
        }
    }
    
    distanceToLine(px, py, x1, y1, x2, y2) {
        const A = px - x1;
        const B = py - y1;
        const C = x2 - x1;
        const D = y2 - y1;
        
        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        
        if (lenSq === 0) return Math.sqrt(A * A + B * B);
        
        const param = dot / lenSq;
        let xx, yy;
        
        if (param < 0) {
            xx = x1;
            yy = y1;
        } else if (param > 1) {
            xx = x2;
            yy = y2;
        } else {
            xx = x1 + param * C;
            yy = y1 + param * D;
        }
        
        const dx = px - xx;
        const dy = py - yy;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    showContextMenu(x, y) {
        if (!this.selectedAnnotation) return;
        
        // Créer le menu contextuel
        const menu = document.createElement('div');
        menu.className = 'annotation-context-menu';
        menu.style.cssText = `
            position: absolute;
            left: ${x}px;
            top: ${y}px;
            background: white;
            border: 1px solid #ccc;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            padding: 5px;
        `;
        
        menu.innerHTML = `
            <button onclick="annotationTool.editAnnotation('${this.selectedAnnotation.id}')" 
                    class="btn btn-sm btn-outline-primary d-block mb-1">
                <i class="fas fa-edit"></i> Modifier
            </button>
            <button onclick="annotationTool.deleteAnnotation('${this.selectedAnnotation.id}')" 
                    class="btn btn-sm btn-outline-danger d-block">
                <i class="fas fa-trash"></i> Supprimer
            </button>
        `;
        
        document.body.appendChild(menu);
        
        // Supprimer le menu après 3 secondes ou au clic
        setTimeout(() => menu.remove(), 5000);
        document.addEventListener('click', () => menu.remove(), { once: true });
    }
    
    redraw() {
        // Effacer le canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Dessiner l'image de fond
        if (this.image.complete) {
            this.ctx.drawImage(this.image, this.imageX, this.imageY, this.imageWidth, this.imageHeight);
        }
        
        // Dessiner toutes les annotations
        this.annotations.forEach(annotation => {
            this.drawAnnotation(annotation, annotation === this.selectedAnnotation);
        });
    }
    
    drawAnnotation(annotation, isSelected = false) {
        const ctx = this.ctx;
        const coords = annotation.coordinates;
        
        // Configuration du style
        ctx.strokeStyle = annotation.color;
        ctx.fillStyle = annotation.color;
        ctx.lineWidth = annotation.strokeWidth || 2;
        ctx.globalAlpha = annotation.alpha || 1.0;
        
        // Style de sélection
        if (isSelected) {
            ctx.strokeStyle = '#ff6b35';
            ctx.lineWidth = (annotation.strokeWidth || 2) + 2;
            ctx.setLineDash([5, 5]);
        } else {
            ctx.setLineDash([]);
        }
        
        switch (annotation.type) {
            case 'rectangle':
            case 'highlight':
                if (annotation.type === 'highlight') {
                    ctx.fillRect(coords.x, coords.y, coords.width, coords.height);
                } else {
                    ctx.strokeRect(coords.x, coords.y, coords.width, coords.height);
                }
                break;
            
            case 'circle':
                const centerX = coords.x + coords.width / 2;
                const centerY = coords.y + coords.height / 2;
                const radius = Math.max(Math.abs(coords.width), Math.abs(coords.height)) / 2;
                
                ctx.beginPath();
                ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
                ctx.stroke();
                break;
            
            case 'arrow':
                this.drawArrow(ctx, coords.x, coords.y, coords.x + coords.width, coords.y + coords.height);
                break;
            
            case 'text':
                ctx.font = `${annotation.fontSize || 16}px Arial`;
                ctx.fillText(annotation.text_content, coords.x, coords.y);
                break;
            
            case 'freehand':
                ctx.beginPath();
                coords.forEach((point, i) => {
                    if (i === 0) {
                        ctx.moveTo(point.x, point.y);
                    } else {
                        ctx.lineTo(point.x, point.y);
                    }
                });
                ctx.stroke();
                break;
        }
        
        ctx.globalAlpha = 1.0;
        ctx.setLineDash([]);
    }
    
    drawArrow(ctx, startX, startY, endX, endY) {
        const headlen = 15;
        const angle = Math.atan2(endY - startY, endX - startX);
        
        // Ligne principale
        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        
        // Pointe de flèche
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(endX - headlen * Math.cos(angle - Math.PI / 6), endY - headlen * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(endX, endY);
        ctx.lineTo(endX - headlen * Math.cos(angle + Math.PI / 6), endY - headlen * Math.sin(angle + Math.PI / 6));
        ctx.stroke();
    }
    
    setTool(toolName) {
        this.currentTool = toolName;
        this.updateCursor();
        this.selectedAnnotation = null;
        this.redraw();
    }
    
    updateCursor() {
        this.canvas.style.cursor = this.tools[this.currentTool]?.cursor || 'default';
    }
    
    async loadExistingAnnotations() {
        try {
            const response = await fetch(`/api/annotations/workorder/${this.workOrderId}/photos`);
            const data = await response.json();
            
            if (data.success) {
                const photo = data.photos.find(p => p.id === this.attachmentId);
                if (photo) {
                    this.annotations = photo.annotations.map(ann => ({
                        ...ann,
                        coordinates: JSON.parse(ann.coordinates)
                    }));
                    this.redraw();
                }
            }
        } catch (error) {
            console.error('Erreur chargement annotations:', error);
        }
    }
    
    async saveAnnotation(annotation) {
        try {
            const response = await fetch('/api/annotations/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    work_order_id: this.workOrderId,
                    attachment_id: this.attachmentId,
                    annotation_type: annotation.type,
                    coordinates: annotation.coordinates,
                    text_content: annotation.text_content || '',
                    color: annotation.color,
                    stroke_width: annotation.strokeWidth
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Remplacer l'annotation temporaire par l'annotation sauvegardée
                annotation.id = result.annotation_id;
                this.annotations.push(annotation);
                this.redraw();
                
                // Notification de succès
                this.showToast('Annotation sauvegardée', 'success');
            } else {
                this.showToast('Erreur lors de la sauvegarde', 'error');
            }
        } catch (error) {
            console.error('Erreur sauvegarde annotation:', error);
            this.showToast('Erreur de connexion', 'error');
        }
    }
    
    async deleteAnnotation(annotationId) {
        if (!confirm('Supprimer cette annotation ?')) return;
        
        try {
            const response = await fetch(`/api/annotations/delete/${annotationId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.annotations = this.annotations.filter(ann => ann.id !== annotationId);
                this.selectedAnnotation = null;
                this.redraw();
                this.showToast('Annotation supprimée', 'info');
            } else {
                this.showToast('Erreur lors de la suppression', 'error');
            }
        } catch (error) {
            console.error('Erreur suppression annotation:', error);
            this.showToast('Erreur de connexion', 'error');
        }
    }
    
    editAnnotation(annotationId) {
        const annotation = this.annotations.find(ann => ann.id === annotationId);
        if (!annotation) return;
        
        if (annotation.type === 'text') {
            const newText = prompt('Modifier le texte:', annotation.text_content);
            if (newText !== null) {
                annotation.text_content = newText;
                this.saveAnnotation(annotation);
            }
        } else {
            // Pour les autres types, permettre de changer la couleur
            const newColor = prompt('Nouvelle couleur (hex):', annotation.color);
            if (newColor && /^#[0-9A-F]{6}$/i.test(newColor)) {
                annotation.color = newColor;
                this.saveAnnotation(annotation);
            }
        }
    }
    
    showToast(message, type = 'info') {
        // Créer un toast Bootstrap ou une notification simple
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 2000; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-dismiss après 3 secondes
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    }
}

// Instance globale pour accès depuis les menus contextuels
let annotationTool;

// Fonction d'initialisation
function initAnnotationTool(canvasId, imageUrl, workOrderId, attachmentId) {
    annotationTool = new VisualAnnotationTool(canvasId, imageUrl, workOrderId, attachmentId);
    return annotationTool;
}
