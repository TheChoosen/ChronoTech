// Module Gantt pour ChronoTech Dashboard
import { apiClient } from '../utils/api.js';
import { notificationManager } from '../utils/notifications.js';

export class GanttManager {
    constructor() {
        this.tasks = [];
        this.currentPeriod = 'month';
        this.currentDate = new Date();
    }

    // Charger les données Gantt
    async loadGanttData() {
        try {
            console.log('📊 Chargement données Gantt...');

            // Calculer les dates de début et fin selon la période
            const { startDate, endDate } = this.getPeriodDates();
            const data = await apiClient.getWorkOrders({
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0],
                include_schedule: true
            });
            
            if (data && Array.isArray(data)) {
                this.tasks = data;
                this.renderGanttChart(data);
                console.log(`✅ ${data.length} tâches chargées pour le Gantt`);
            } else {
                throw new Error('Données Gantt invalides');
            }

        } catch (error) {
            console.warn('⚠️ Fallback vers données de test Gantt:', error);
            this.loadTestGanttData();
        }
    }

    // Charger des données de test pour le Gantt
    loadTestGanttData() {
        const today = new Date();
        const testTasks = [
            {
                id: 1,
                claim_number: 'WO-001',
                title: 'Installation système sécurité',
                customer_name: 'Entreprise Alpha',
                technician_name: 'Jean Dupont',
                start_date: new Date(today.getTime() + 1*24*60*60*1000),
                end_date: new Date(today.getTime() + 3*24*60*60*1000),
                priority: 'medium',
                progress: 0
            },
            {
                id: 2,
                claim_number: 'WO-002',
                title: 'Réparation climatisation',
                customer_name: 'Client Gamma',
                technician_name: 'Marie Martin',
                start_date: new Date(today.getTime() + 2*24*60*60*1000),
                end_date: new Date(today.getTime() + 4*24*60*60*1000),
                priority: 'high',
                progress: 25
            },
            {
                id: 3,
                claim_number: 'WO-003',
                title: 'Panne électrique',
                customer_name: 'Corp Delta',
                technician_name: 'Pierre Durand',
                start_date: today,
                end_date: new Date(today.getTime() + 1*24*60*60*1000),
                priority: 'urgent',
                progress: 75
            },
            {
                id: 4,
                claim_number: 'WO-004',
                title: 'Maintenance cuisine',
                customer_name: 'Restaurant Zeta',
                technician_name: 'Sophie Leroy',
                start_date: new Date(today.getTime() + 5*24*60*60*1000),
                end_date: new Date(today.getTime() + 7*24*60*60*1000),
                priority: 'medium',
                progress: 0
            },
            {
                id: 5,
                claim_number: 'WO-005',
                title: 'Migration serveur',
                customer_name: 'Bureau Theta',
                technician_name: 'Luc Moreau',
                start_date: new Date(today.getTime() + 3*24*60*60*1000),
                end_date: new Date(today.getTime() + 10*24*60*60*1000),
                priority: 'high',
                progress: 40
            }
        ];

        this.tasks = testTasks;
        this.renderGanttChart(testTasks);
    }

    // Obtenir les dates de début et fin selon la période
    getPeriodDates() {
        const today = new Date();
        let startDate, endDate;

        switch (this.currentPeriod) {
            case 'week':
                startDate = new Date(today);
                startDate.setDate(today.getDate() - today.getDay());
                endDate = new Date(startDate);
                endDate.setDate(startDate.getDate() + 6);
                break;
            case 'month':
                startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                break;
            case 'quarter':
                const quarter = Math.floor(today.getMonth() / 3);
                startDate = new Date(today.getFullYear(), quarter * 3, 1);
                endDate = new Date(today.getFullYear(), (quarter + 1) * 3, 0);
                break;
            default:
                startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        }

        return { startDate, endDate };
    }

    // Rendre le diagramme de Gantt
    renderGanttChart(tasks) {
        const container = document.getElementById('gantt-container');
        if (!container) return;

        const { startDate, endDate } = this.getPeriodDates();
        const days = this.getDaysBetween(startDate, endDate);

        // Générer la timeline
        this.renderTimeline(days);

        // Générer les barres de tâches
        this.renderTasks(tasks, startDate, endDate);

        console.log('✅ Diagramme de Gantt rendu avec', tasks.length, 'tâches');
    }

    // Générer la timeline des jours
    renderTimeline(days) {
        const timeline = document.getElementById('gantt-timeline');
        if (!timeline) return;

        timeline.innerHTML = days.map(date => {
            const isToday = this.isToday(date);
            const isWeekend = date.getDay() === 0 || date.getDay() === 6;
            
            return `
                <div class="gantt-day ${isToday ? 'today' : ''} ${isWeekend ? 'weekend' : ''}">
                    <div class="day-name">${date.toLocaleDateString('fr-FR', { weekday: 'short' })}</div>
                    <div class="day-number">${date.getDate()}</div>
                </div>
            `;
        }).join('');
    }

    // Générer les barres de tâches
    renderTasks(tasks, startDate, endDate) {
        const ganttBody = document.getElementById('gantt-body');
        if (!ganttBody) return;

        const totalDays = this.getDaysBetween(startDate, endDate).length;

        ganttBody.innerHTML = tasks.map(task => {
            const taskStart = new Date(task.start_date);
            const taskEnd = new Date(task.end_date);
            
            // Calculer la position et la largeur de la barre
            const startOffset = Math.max(0, this.getDaysBetween(startDate, taskStart).length);
            const duration = this.getDaysBetween(taskStart, taskEnd).length + 1;
            
            const leftPercent = (startOffset / totalDays) * 100;
            const widthPercent = (duration / totalDays) * 100;

            const priorityClass = `priority-${task.priority}`;

            return `
                <div class="gantt-row">
                    <div class="gantt-task ${priorityClass}" 
                         style="left: ${leftPercent}%; width: ${widthPercent}%;"
                         onclick="openWorkOrderDetails(${task.id})"
                         title="${task.title} - ${task.customer_name}">
                        <div class="gantt-task-label">${task.claim_number}</div>
                        <div class="gantt-task-progress" style="width: ${task.progress}%"></div>
                    </div>
                    <div class="gantt-task-info">
                        <div class="task-title">${task.title}</div>
                        <div class="task-technician">${task.technician_name}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Obtenir les jours entre deux dates
    getDaysBetween(startDate, endDate) {
        const days = [];
        const currentDate = new Date(startDate);
        
        while (currentDate <= endDate) {
            days.push(new Date(currentDate));
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        return days;
    }

    // Vérifier si une date est aujourd'hui
    isToday(date) {
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }

    // Changer la période d'affichage
    changePeriod(period) {
        this.currentPeriod = period;
        this.loadGanttData();
        
        // Mettre à jour le sélecteur
        const selector = document.getElementById('gantt-period');
        if (selector) {
            selector.value = period;
        }
    }

    // Actualiser le Gantt
    refresh() {
        notificationManager.showToast('Actualisation du diagramme de Gantt...', 'info');
        this.loadGanttData();
    }

    // Exporter le Gantt
    export() {
        const ganttData = {
            period: this.currentPeriod,
            tasks: this.tasks.map(task => ({
                id: task.id,
                claim_number: task.claim_number,
                title: task.title,
                customer: task.customer_name,
                technician: task.technician_name,
                start_date: task.start_date,
                end_date: task.end_date,
                priority: task.priority,
                progress: task.progress
            })),
            exported_at: new Date().toISOString()
        };

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(ganttData, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `gantt_${this.currentPeriod}_${new Date().toISOString().split('T')[0]}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();

        notificationManager.showToast('Diagramme de Gantt exporté', 'success');
    }
}

// Instance globale
export const ganttManager = new GanttManager();

// Fonctions globales pour compatibilité
window.loadGanttData = () => ganttManager.loadGanttData();
window.refreshGantt = () => ganttManager.refresh();
window.exportGantt = () => ganttManager.export();

// Gestionnaire de changement de période
document.addEventListener('DOMContentLoaded', () => {
    const periodSelector = document.getElementById('gantt-period');
    if (periodSelector) {
        periodSelector.addEventListener('change', (e) => {
            ganttManager.changePeriod(e.target.value);
        });
    }
});
