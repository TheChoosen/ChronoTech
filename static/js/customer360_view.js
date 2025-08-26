// customer360_view.js
// Externalized logic for Customer 360 tab navigation, lazy loading, quick actions and utilities
(function(){
  if (window.__Customer360Initialized) return; // guard against double inclusion
  window.__Customer360Initialized = true;

  const data = window.Customer360Data || {};
  const customerId = data.id;
  const customerName = data.name || '';
  const initialTab = data.initial_tab || 'profile';
  let loadedSections = new Set(['profile']);

  function globalOverlay(){ return document.getElementById('customer360-loading-overlay'); }
  function showGlobalLoader(){ const ov = globalOverlay(); if(ov){ ov.classList.remove('d-none'); ov.setAttribute('aria-hidden','false'); }}
  function hideGlobalLoader(){ const ov = globalOverlay(); if(ov){ ov.classList.add('d-none'); ov.setAttribute('aria-hidden','true'); }}

  function showToast(message, type='info') {
    const toast = document.getElementById('globalToast');
    if(!toast) return;
    const title = document.getElementById('toastTitle');
    const body = document.getElementById('toastBody');
    const config = {
      success: { title: 'Succès', class: 'text-success', icon: 'fas fa-check-circle' },
      error: { title: 'Erreur', class: 'text-danger', icon: 'fas fa-exclamation-circle' },
      warning: { title: 'Attention', class: 'text-warning', icon: 'fas fa-exclamation-triangle' },
      info: { title: 'Information', class: 'text-info', icon: 'fas fa-info-circle' }
    };
    const typeConfig = config[type] || config.info;
    title.textContent = typeConfig.title;
    title.className = `me-auto ${typeConfig.class}`;
    body.innerHTML = `<i class="${typeConfig.icon} me-2"></i>${message}`;
    new bootstrap.Toast(toast).show();
  }
  window.showToast = showToast; // expose for other inline usages

  function quickActions(action){
    const modalEl = document.getElementById('quickActionModal');
    if(!modalEl) return;
    const modal = new bootstrap.Modal(modalEl);
    const title = document.getElementById('quickActionModalTitle');
    const body = document.getElementById('quickActionModalBody');
    const confirmBtn = document.getElementById('quickActionConfirm');
    confirmBtn.className = 'clay-button';
    confirmBtn.style.display = '';

    switch(action){
      case 'call':
        title.textContent = 'Appeler le client';
        body.innerHTML = `
          <p>Appeler <strong>${customerName}</strong> au :</p>
          <div class="list-group">
            ${data.phone ? `<a href="tel:${data.phone}" class="list-group-item list-group-item-action"><i class=\"fas fa-phone me-2\"></i>${data.phone}<span class=\"badge bg-primary ms-2\">Principal</span></a>` : ''}
            ${data.secondary_phone ? `<a href="tel:${data.secondary_phone}" class="list-group-item list-group-item-action"><i class=\"fas fa-mobile-alt me-2\"></i>${data.secondary_phone}<span class=\"badge bg-secondary ms-2\">Secondaire</span></a>` : ''}
          </div>`;
        confirmBtn.style.display = 'none';
        break;
      case 'email':
        title.textContent = 'Envoyer un email';
        body.innerHTML = `
          <form id="emailForm">
            <div class="mb-3"><label class="form-label">Destinataire :</label><input type="email" class="form-control" value="${data.email || ''}" readonly></div>
            <div class="mb-3"><label class="form-label">Objet :</label><select class="form-select" id="emailSubject">
                <option value="">Objet personnalisé...</option>
                <option value="Suivi de votre dossier">Suivi de votre dossier</option>
                <option value="Devis pour vos travaux">Devis pour vos travaux</option>
                <option value="Planification d'intervention">Planification d'intervention</option>
                <option value="Facture disponible">Facture disponible</option>
            </select></div>
            <div class="mb-3"><label class="form-label">Message :</label><textarea class="form-control" rows="4" id="emailMessage" placeholder="Votre message..."></textarea></div>
          </form>`;
        confirmBtn.textContent = 'Envoyer';
        confirmBtn.onclick = sendQuickEmail;
        break;
      case 'quote':
        window.location.href = `/quotes/new?customer_id=${customerId}`;
        return;
      case 'export':
        title.textContent = 'Exporter les données client';
        body.innerHTML = `
          <p>Sélectionnez les données à exporter pour <strong>${customerName}</strong> :</p>
          <div class="form-check mb-2"><input class="form-check-input" type="checkbox" value="profile" id="export_profile" checked><label class="form-check-label" for="export_profile">Informations profil</label></div>
          <div class="form-check mb-2"><input class="form-check-input" type="checkbox" value="finances" id="export_finances" checked><label class="form-check-label" for="export_finances">Données financières</label></div>
          <div class="form-check mb-2"><input class="form-check-input" type="checkbox" value="activity" id="export_activity"><label class="form-check-label" for="export_activity">Historique d'activité</label></div>
          <div class="form-check mb-2"><input class="form-check-input" type="checkbox" value="documents" id="export_documents"><label class="form-check-label" for="export_documents">Documents</label></div>
          <hr>
          <div class="mb-3"><label class="form-label">Format :</label><select class="form-select" id="exportFormat"><option value="pdf">PDF</option><option value="excel">Excel</option><option value="csv">CSV</option></select></div>`;
        confirmBtn.textContent = 'Exporter';
        confirmBtn.onclick = exportCustomerData;
        break;
      case 'delete':
        title.textContent = 'Supprimer le client';
        confirmBtn.className = 'btn btn-danger';
        body.innerHTML = `
          <div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i><strong>Attention !</strong> Cette action est irréversible.</div>
          <p>Êtes-vous sûr de vouloir supprimer <strong>${customerName}</strong> ?</p>
          <div class="mb-3"><label class="form-label">Raison de la suppression :</label><textarea class="form-control" rows="3" id="deleteReason" required placeholder="Veuillez indiquer la raison..."></textarea></div>
          <div class="form-check"><input class="form-check-input" type="checkbox" id="confirmDelete" required><label class="form-check-label" for="confirmDelete">Je confirme vouloir supprimer ce client et toutes ses données</label></div>`;
        confirmBtn.textContent = 'Supprimer';
        confirmBtn.onclick = deleteCustomer;
        break;
      default:
        showToast('Action non implémentée','info');
        return;
    }
    modal.show();
  }
  window.quickActions = quickActions;

  function sendQuickEmail(){
    const subject = document.getElementById('emailSubject').value;
    const message = document.getElementById('emailMessage').value;
    if(!message.trim()) { showToast('Veuillez saisir un message','warning'); return; }
    fetch(`/api/customers/${customerId}/send-email`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ subject: subject || 'Message de ChronoTech', message })
    }).then(r=>r.json()).then(d=>{
      if(d.success){ showToast('Email envoyé avec succès','success'); bootstrap.Modal.getInstance(document.getElementById('quickActionModal')).hide(); }
      else showToast('Erreur lors de l\'envoi','error');
    }).catch(err=>{ console.error(err); showToast('Erreur de connexion','error'); });
  }
  function exportCustomerData(){
    const selected = Array.from(document.querySelectorAll('#quickActionModal input[type="checkbox"]:checked')).map(cb=>cb.value);
    if(!selected.length){ showToast('Sélectionnez au moins un type de données','warning'); return; }
    const format = document.getElementById('exportFormat').value;
    const params = new URLSearchParams({ data: selected.join(','), format });
    window.open(`/api/customers/${customerId}/export?${params}`,'_blank');
    bootstrap.Modal.getInstance(document.getElementById('quickActionModal')).hide();
  }
  function deleteCustomer(){
    const reason = (document.getElementById('deleteReason').value||'').trim();
    const confirmed = document.getElementById('confirmDelete').checked;
    if(!reason){ showToast('Veuillez indiquer une raison','warning'); return; }
    if(!confirmed){ showToast('Veuillez confirmer la suppression','warning'); return; }
    fetch(`/api/customers/${customerId}`, { method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ reason }) })
      .then(r=>r.json()).then(d=>{ if(d.success){ showToast('Client supprimé avec succès','success'); setTimeout(()=>{ window.location.href='/customers'; },2000);} else showToast('Erreur lors de la suppression','error'); })
      .catch(err=>{ console.error(err); showToast('Erreur de connexion','error'); });
  }

  function formatCurrency(amount){ return new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(amount); }
  function formatDate(dateString){ return new Date(dateString).toLocaleDateString('fr-FR'); }
  function formatRelativeTime(dateString){ const date=new Date(dateString); const now=new Date(); const diff=Math.floor((now-date)/1000); if(diff<60) return 'À l\'instant'; if(diff<3600) return `Il y a ${Math.floor(diff/60)} min`; if(diff<86400) return `Il y a ${Math.floor(diff/3600)}h`; if(diff<2592000) return `Il y a ${Math.floor(diff/86400)} jours`; return formatDate(dateString); }
  window.formatCurrency = formatCurrency; window.formatDate = formatDate; window.formatRelativeTime = formatRelativeTime;

  function loadSectionIfNeeded(sectionName, forceReload=false){
    console.log('=== loadSectionIfNeeded called ===');
    console.log('Section:', sectionName, 'Force:', forceReload, 'Loaded:', Array.from(loadedSections));
    console.trace('Call stack for loadSectionIfNeeded');
    if(loadedSections.has(sectionName) && !forceReload) return;
    if(sectionName === 'profile'){ loadedSections.add('profile'); return; }
    const tabContent = document.getElementById(`tab-content-${sectionName}`); if(!tabContent) return;
    tabContent.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Chargement...</span></div><p class="mt-3">Chargement de la section ${sectionName}...</p></div>`;
    showGlobalLoader();
    fetch(`/customers/api/customers/${customerId}/sections/${sectionName}`)
      .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.text(); })
      .then(html=>{ tabContent.innerHTML = html; loadedSections.add(sectionName); document.dispatchEvent(new CustomEvent('sectionLoaded',{detail:{section:sectionName}})); })
      .catch(err=>{ console.error('Erreur chargement section', sectionName, err); tabContent.innerHTML = `<div class="text-center py-5"><i class=\"fas fa-exclamation-triangle fa-3x text-danger mb-3\"></i><h5 class=\"text-danger\">Erreur de chargement</h5><p class=\"text-muted\">Impossible de charger cette section.</p><button class=\"clay-button\" onclick=\"loadSectionIfNeeded('${sectionName}', true)\"><i class=\"fas fa-sync me-2\"></i>Réessayer</button></div>`; })
      .finally(()=> setTimeout(hideGlobalLoader,150));
  }
  window.loadSectionIfNeeded = loadSectionIfNeeded;

  document.addEventListener('DOMContentLoaded', () => {
    // Mark initial tab as loaded if its content is server-side included
    if(initialTab !== 'profile') {
      const pane = document.getElementById(`tab-content-${initialTab}`);
      if(pane && pane.querySelector(':scope > *:not(.text-center)')) loadedSections.add(initialTab);
    }
    const params = new URLSearchParams(window.location.search);
    const activeTab = params.get('tab') || 'profile';
    const btn = document.querySelector(`[data-section="${activeTab}"]`);
    if(btn && activeTab !== 'profile') {
      new bootstrap.Tab(btn).show();
      loadSectionIfNeeded(activeTab);
    }
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(b => {
      b.addEventListener('shown.bs.tab', function(){
        const sectionName = this.getAttribute('data-section');
        loadSectionIfNeeded(sectionName);
        const container = document.getElementById('customer-360-tab-content'); if(container) container.scrollTop = 0;
        const url = new URL(window.location); url.searchParams.set('tab', sectionName); window.history.pushState({},'',url);
      });
    });
    window.addEventListener('popstate', ()=>{
      const p = new URLSearchParams(window.location.search); const tab = p.get('tab') || 'profile';
      const btn2 = document.querySelector(`[data-section="${tab}"]`); if(btn2){ new bootstrap.Tab(btn2).show(); loadSectionIfNeeded(tab); }
    });
  });
})();
