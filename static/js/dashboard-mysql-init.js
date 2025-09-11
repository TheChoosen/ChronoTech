
// Initialisation Dashboard ChronoTech MySQL
// Ce script assure que toutes les données proviennent de MySQL

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initialisation Dashboard MySQL ChronoTech');
    
    // Vérifier la connexion MySQL
    checkMySQLConnection();
    
    // Charger les données initiales
    loadInitialDashboardData();
    
    // Configurer les actualisations automatiques
    setupAutoRefresh();
});

async function checkMySQLConnection() {
    try {
        const response = await fetch('/api/dashboard/stats');
        if (response.ok) {
            console.log('✅ Connexion MySQL Dashboard OK');
            showConnectionStatus('connected');
        } else {
            throw new Error('API non accessible');
        }
    } catch (error) {
        console.error('❌ Erreur connexion MySQL:', error);
        showConnectionStatus('error');
    }
}

async function loadInitialDashboardData() {
    console.log('📊 Chargement données initiales...');
    
    try {
        // Charger en parallèle
        const [stats, kanban] = await Promise.all([
            loadDashboardStats(),
            loadKanbanDataMySQL()
        ]);
        
        if (stats && kanban) {
            console.log('✅ Données initiales chargées');
        }
        
    } catch (error) {
        console.error('❌ Erreur chargement initial:', error);
    }
}

function setupAutoRefresh() {
    // Actualisation automatique toutes les 30 secondes
    setInterval(async () => {
        console.log('🔄 Auto-refresh dashboard...');
        await loadDashboardStats();
    }, 30000);
    
    // Actualisation complète toutes les 5 minutes
    setInterval(async () => {
        console.log('🔄 Full refresh dashboard...');
        await refreshDashboardStats();
    }, 300000);
}

function showConnectionStatus(status) {
    const indicator = document.getElementById('mysql-connection-indicator');
    if (!indicator) {
        // Créer l'indicateur s'il n'existe pas
        const div = document.createElement('div');
        div.id = 'mysql-connection-indicator';
        div.style.cssText = `
            position: fixed;
            top: 10px;
            left: 10px;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 9999;
            font-weight: bold;
        `;
        document.body.appendChild(div);
    }
    
    const indicator = document.getElementById('mysql-connection-indicator');
    
    if (status === 'connected') {
        indicator.innerHTML = '🟢 MySQL OK';
        indicator.style.backgroundColor = '#d4edda';
        indicator.style.color = '#155724';
        indicator.style.border = '1px solid #c3e6cb';
    } else {
        indicator.innerHTML = '🔴 MySQL ERROR';
        indicator.style.backgroundColor = '#f8d7da';
        indicator.style.color = '#721c24';
        indicator.style.border = '1px solid #f5c6cb';
    }
}

// Export des fonctions globalement
window.ChronoTechDashboardMySQL = {
    loadDashboardStats,
    loadKanbanDataMySQL,
    refreshDashboardStats,
    checkMySQLConnection
};
