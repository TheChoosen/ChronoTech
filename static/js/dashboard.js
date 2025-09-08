// ChronoTech Dashboard v2.0 - Enhanced avec rate limiting optimisé
(function(){
  const cfg = window.__DASHBOARD__ && window.__DASHBOARD__.endpoints ? window.__DASHBOARD__.endpoints : {};
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  // Optimisation du rate limiting
  let presenceUpdateInterval = 10 * 60 * 1000; // 10 minutes au lieu de 1 minute
  let lastPresenceUpdate = 0;

  // Get CSRF token from meta tag
  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  async function fetchJSON(url, opts={}){
    // Add CSRF token to POST requests
    if (opts.method === 'POST' || opts.method === 'PUT' || opts.method === 'DELETE') {
      const csrfToken = getCSRFToken();
      if (csrfToken) {
        opts.headers = opts.headers || {};
        opts.headers['X-CSRFToken'] = csrfToken;
      }
    }
    
    const res = await fetch(url, Object.assign({headers: {'X-Requested-With':'XMLHttpRequest'}}, opts));
    if(!res.ok) {
      // Gestion spéciale pour rate limiting
      if (res.status === 429) {
        console.warn('⏳ Rate limit atteint - ajustement de la fréquence');
        throw new Error('RATE_LIMITED');
      }
      throw new Error('HTTP '+res.status);
    }
    return res.json();
  }

  // Stats polling
  async function refreshStats(){
    if(!cfg.stats) return;
    try{
      const data = await fetchJSON(cfg.stats);
      if(data){
        if($('#stat-active-orders')) $('#stat-active-orders').textContent = data.active_orders ?? 0;
        if($('#stat-completed-today')) $('#stat-completed-today').textContent = data.completed_today ?? 0;
        if($('#stat-urgent-orders')) $('#stat-urgent-orders').textContent = data.urgent_orders ?? 0;
        if($('#stat-active-technicians')) $('#stat-active-technicians').textContent = data.active_technicians ?? 0;
        if($('#pending-work-orders')) $('#pending-work-orders').textContent = data.pending_work_orders ?? 0;
        if($('#today-appointments')) $('#today-appointments').textContent = data.today_appointments ?? 0;
        if($('#online-techs')) $('#online-techs').textContent = data.online_technicians ?? 0;
        if($('#monthly-revenue')) $('#monthly-revenue').textContent = formatCurrency(data.monthly_revenue ?? 0);
      }
    }catch(e){ 
      if (e.message !== 'RATE_LIMITED') {
        console.error('Erreur chargement stats:', e);
      }
    }
  }
  
  // Presence heartbeat optimisé avec statut
  async function heartbeat(){
    if(!cfg.heartbeat) return;
    try{ 
      // Détecter le statut utilisateur (simple détection d'activité)
      const isAway = document.hidden || (Date.now() - lastUserActivity > 5 * 60 * 1000); // 5 min
      const status = isAway ? 'away' : 'online';
      
      await fetchJSON(cfg.heartbeat, {
        method:'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ status: status })
      }); 
      console.log(`💓 Heartbeat envoyé (${status})`);
    }catch(e){
      if (e.message !== 'RATE_LIMITED') {
        console.error('Erreur heartbeat:', e);
      }
    }
  }
  
  // Tracking activité utilisateur pour statut away
  let lastUserActivity = Date.now();
  document.addEventListener('mousemove', () => lastUserActivity = Date.now());
  document.addEventListener('keypress', () => lastUserActivity = Date.now());
  document.addEventListener('click', () => lastUserActivity = Date.now());
  
  // Détection visibilité page pour statut away automatique
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      lastUserActivity = Date.now();
      // Heartbeat immédiat au retour
      if (cfg.heartbeat) heartbeat();
    }
  });
  
  // Presence refresh avec statistiques enrichies
  async function refreshPresence(){
    if(!cfg.presence) return;
    
    const now = Date.now();
    if (now - lastPresenceUpdate < presenceUpdateInterval) {
      return; // Skip si appelé trop fréquemment
    }
    
    try{
      const data = await fetchJSON(cfg.presence);
      if (data.success && data.online_users) {
        lastPresenceUpdate = now;
        
        updateOnlineUsersList(data.online_users);
        updatePresenceStatistics(data.statistics);
        
        // Reset interval en cas de succès (30 sec optimal)
        if (presenceUpdateInterval > 30 * 1000) {
          presenceUpdateInterval = 30 * 1000; // Revenir à 30 secondes
        }
      }
      
    }catch(e){ 
      if (e.message === 'RATE_LIMITED') {
        // Augmenter l'intervalle en cas de rate limit
        presenceUpdateInterval = Math.min(presenceUpdateInterval * 1.5, 2 * 60 * 1000); // Max 2 minutes
        console.warn(`⏳ Rate limit - nouvel intervalle: ${presenceUpdateInterval/1000} secondes`);
      } else {
        console.error('Erreur presence:', e);
      }
    }
  }

  function updateOnlineUsersList(users) {
    const container = $('#online-users');
    const badge = $('#online-count');
    const teamList = $('#online-team-list');
    
    // Compter seulement les utilisateurs vraiment en ligne
    const onlineCount = users.filter(u => u.is_online).length;
    if(badge) badge.textContent = onlineCount;
    
    if(container){
      container.innerHTML = '';
      users.forEach(u=>{
        const el = document.createElement('span');
        el.className = `user-chip status-${u.status}`;
        el.innerHTML = `
          <span class="status-indicator status-${u.status}"></span>
          ${escapeHtml(u.name || 'Utilisateur')} 
          <small>(${escapeHtml(u.role || '')})</small>
        `;
        container.appendChild(el);
      });
    }
    
    if(teamList){
      teamList.innerHTML = '';
      users.forEach(user => {
        const userDiv = document.createElement('div');
        userDiv.className = `online-user d-flex align-items-center p-2 mb-1 rounded status-${user.status}`;
        
        // Calcul du temps depuis dernière activité
        const timeAgo = formatTimeSince(user.seconds_since_last_seen);
        
        userDiv.innerHTML = `
          <div class="online-status status-${user.status} me-2"></div>
          <div class="flex-grow-1">
            <div class="fw-bold small">${escapeHtml(user.name || 'Utilisateur')}</div>
            <small class="text-muted">
              ${escapeHtml(user.role || 'Équipe')} • ${getStatusLabel(user.status)}
            </small>
          </div>
          <small class="text-muted">${timeAgo}</small>
        `;
        teamList.appendChild(userDiv);
      });
    }
  }
  
  function updatePresenceStatistics(stats) {
    const statsContainer = $('#presence-stats');
    if (statsContainer && stats) {
      statsContainer.innerHTML = `
        <div class="d-flex gap-3 small">
          <span class="text-success">
            <i class="fa-solid fa-circle me-1"></i>${stats.total_online} en ligne
          </span>
          <span class="text-warning">
            <i class="fa-solid fa-circle me-1"></i>${stats.total_away} absent
          </span>
          <span class="text-info">
            <i class="fa-solid fa-circle me-1"></i>${stats.total_busy} occupé
          </span>
        </div>
      `;
    }
  }
  
  function getStatusLabel(status) {
    const labels = {
      'online': 'En ligne',
      'away': 'Absent',
      'busy': 'Occupé', 
      'offline': 'Hors ligne'
    };
    return labels[status] || 'Inconnu';
  }
  
  function formatTimeSince(seconds) {
    if (seconds < 60) return 'À l\'instant';
    if (seconds < 3600) return `${Math.floor(seconds/60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds/3600)}h`;
    return `${Math.floor(seconds/86400)}j`;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-CA', {
      style: 'currency',
      currency: 'CAD'
    }).format(amount || 0);
  }

  function formatLastSeen(dateString) {
    if (!dateString) return 'Hors ligne';
    
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 5 * 60 * 1000) { // Moins de 5 minutes
      return 'En ligne';
    } else if (diff < 60 * 60 * 1000) { // Moins d'1 heure
      return `${Math.floor(diff / (60 * 1000))}m`;
    } else if (diff < 24 * 60 * 60 * 1000) { // Moins de 24h
      return `${Math.floor(diff / (60 * 60 * 1000))}h`;
    } else {
      return date.toLocaleDateString('fr-FR');
    }
  }

  // Kanban functions
  function cardEl(item){
    const el = document.createElement('div');
    el.className = 'kanban-card';
    el.setAttribute('draggable','true');
    el.dataset.id = item.id;
    el.innerHTML = `
      <div class="title">${item.claim_number || ('#'+item.id)}</div>
      <div class="meta">${item.customer_name || ''} · ${item.technician_name || '—'} · ${item.priority || ''}</div>
    `;
    return el;
  }
  
  function bindDnD(){
    $$('.kanban-card').forEach(card => {
      card.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', card.dataset.id);
      });
    });
    $$('.kanban-col-body').forEach(col => {
      col.addEventListener('dragover', (e) => { e.preventDefault(); });
      col.addEventListener('drop', async (e) => {
        e.preventDefault();
        const id = e.dataTransfer.getData('text/plain');
        const newStatus = col.dataset.list;
        try{
          const url = cfg.updateStatus && cfg.updateStatus(id);
          if(url){
            const form = new URLSearchParams();
            form.set('status', newStatus);
    // Add CSRF token to form data
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      form.set('csrf_token', csrfToken);
    }
    const res = await fetchJSON(url, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: form.toString()});
    if(res && res.success){ renderKanban(); refreshStats(); }
          }
        }catch(err){ /* silent */ }
      });
    });
  }
  async function renderKanban(){
    if(!cfg.kanban) return;
    try{
      const data = await fetchJSON(cfg.kanban);
      const cols = data.columns || {};
      Object.keys(cols).forEach(k => {
        const body = document.querySelector(`.kanban-col-body[data-list="${k}"]`);
        const countBadge = document.querySelector(`.kanban-col[data-status="${k}"] [data-count]`);
        if(body){ body.innerHTML = ''; cols[k].forEach(item => body.appendChild(cardEl(item))); }
        if(countBadge){ countBadge.textContent = (cols[k] || []).length; }
      });
      bindDnD();
    }catch(e){ /* silent */ }
  }

  // Chat
  async function loadChat(sinceId){
    if(!cfg.chatHistory) return;
    try{
      // channel scoping
      const channelTypeEl = document.querySelector('#chat-channel-select');
      const deptSelect = document.querySelector('#chat-department-select');
      const channel_type = channelTypeEl ? channelTypeEl.value : null;
  const channel_id = (channel_type === 'department' && deptSelect && deptSelect.value) ? parseInt(deptSelect.value, 10) : null;
      const params = new URLSearchParams();
      if(sinceId) params.set('since_id', sinceId);
      if(channel_type) params.set('channel_type', channel_type);
      if(channel_id) params.set('channel_id', channel_id);
  const url = `${cfg.chatHistory}${params.toString() ? ('?' + params.toString()) : ''}`;
  console.debug('loadChat ->', { sinceId, channel_type, channel_id, url });
  const data = await fetchJSON(url);
      const list = data.messages || [];
      const box = $('#chat-messages');
      if(!box) return;
  // Auto-scroll logic: keep at bottom if user was near bottom
  const nearBottom = Math.abs(box.scrollHeight - box.scrollTop - box.clientHeight) < 40;
  if(!sinceId) {
        box.innerHTML = '';
        if(list.length === 0){
          const empty = document.createElement('div');
          empty.className = 'text-muted py-2';
          empty.textContent = "Aucun message pour l'instant. Démarrez la discussion ci-dessous.";
          box.appendChild(empty);
        }
      }
  let lastId = sinceId || 0;
      list.forEach(m => {
        const row = document.createElement('div');
        row.className = 'mb-2 chat-row';
        const who = m.is_bot ? 'Assistant' : (m.user_name || 'Utilisateur');
        const header = document.createElement('div'); header.className = 'd-flex align-items-center gap-2';
        const strong = document.createElement('strong');
        strong.textContent = who;
        const small = document.createElement('small');
        small.className = 'text-muted ms-1';
        small.textContent = (m.created_at||'').replace('T',' ').substring(0,16);
        if(m.is_bot){
          const badge = document.createElement('span');
          badge.className = 'badge bg-info ms-2';
          badge.textContent = '🤖';
          header.appendChild(badge);
        }
        header.appendChild(strong);
        header.appendChild(small);
        const msg = document.createElement('div');
        msg.className = 'chat-text';
        msg.textContent = m.message || '';
        row.appendChild(header);
        row.appendChild(msg);
        box.appendChild(row);
        lastId = Math.max(lastId, m.id || 0);
      });
  console.debug('loadChat <- messages', list.length, 'lastId', lastId);
  if(nearBottom) box.scrollTop = box.scrollHeight;
      return lastId;
    }catch(e){ /* silent */ }
  }
  async function sendChat(){
    const input = $('#chat-input');
    if(!input || !input.value.trim()) return;
    const msg = input.value.trim();
    input.value='';
    const sendBtn = $('#chat-send');
    const assistBtn = $('#chat-assist');
    if(sendBtn) sendBtn.disabled = true;
    if(assistBtn) assistBtn.disabled = true;
    try{
      // include channel context
      const channelTypeEl = document.querySelector('#chat-channel-select');
      const deptSelect = document.querySelector('#chat-department-select');
      const channel_type = channelTypeEl ? channelTypeEl.value : null;
  const channel_id = (channel_type === 'department' && deptSelect && deptSelect.value) ? parseInt(deptSelect.value, 10) : null;
  const body = { message: msg };
  console.debug('sendChat ->', body);
      if(channel_type) body.channel_type = channel_type;
      if(channel_id) body.channel_id = channel_id;
      await fetchJSON(cfg.chatSend, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      await loadChat();
    }catch(e){}
    finally{
      if(sendBtn) sendBtn.disabled = false;
      if(assistBtn) assistBtn.disabled = false;
    }
  }
  async function askAssistant(){
    const input = $('#chat-input');
    const prompt = (input && input.value.trim()) || 'Aide-moi à prioriser les bons urgents et à assigner rapidement.';
    const box = $('#chat-messages');
    const loader = document.createElement('div');
    loader.className = 'text-muted small my-2';
    loader.textContent = 'Assistant en cours de réflexion…';
    if(box) box.appendChild(loader);
    const sendBtn = $('#chat-send');
    const assistBtn = $('#chat-assist');
    if(sendBtn) sendBtn.disabled = true;
    if(assistBtn) assistBtn.disabled = true;
    try{
      // include channel context for assistant
      const channelTypeEl = document.querySelector('#chat-channel-select');
      const deptSelect = document.querySelector('#chat-department-select');
      const channel_type = channelTypeEl ? channelTypeEl.value : null;
      const channel_id = (channel_type === 'department' && deptSelect && deptSelect.value) ? deptSelect.value : null;
      const body = { message: prompt };
      if(channel_type) body.channel_type = channel_type;
      if(channel_id) body.channel_id = channel_id;
      const res = await fetchJSON(cfg.chatAssistant, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      if(res && res.reply){ await loadChat(); }
    }catch(e){}
    finally{
      if(box && loader) box.removeChild(loader);
      if(sendBtn) sendBtn.disabled = false;
      if(assistBtn) assistBtn.disabled = false;
    }
  }

  // Departments management (AJAX)
  async function loadDepartments(){
    try{
      const url = '/api/departments';
      const data = await fetchJSON(url);
      const list = data.departments || [];
      renderDepartmentsList(list);
      populateChatDepartments(list);
    }catch(e){ console.error('loadDepartments', e); }
  }

  function renderDepartmentsList(list){
    const container = $('#departments-list');
    if(!container) return;
    container.innerHTML = '';
    if(list.length === 0){
      const empty = document.createElement('div'); empty.className = 'text-muted'; empty.textContent = 'Aucun département.'; container.appendChild(empty); return;
    }
    list.forEach(d => {
      const row = document.createElement('div');
      row.className = 'd-flex align-items-start justify-content-between gap-2 mb-2';
      const left = document.createElement('div');
      left.innerHTML = `<strong>${d.name}</strong><div class="small text-muted">${d.description || ''}</div>`;
      const right = document.createElement('div');
      const edit = document.createElement('button'); edit.className='btn btn-sm btn-outline-primary me-2'; edit.textContent='Éditer';
      const del = document.createElement('button'); del.className='btn btn-sm btn-outline-danger'; del.textContent='Supprimer';
      edit.addEventListener('click', ()=>{ $('#dept-id').value = d.id; $('#dept-name').value = d.name; $('#dept-desc').value = d.description || ''; $('#dept-name').focus(); });
      del.addEventListener('click', async ()=>{
        if(!confirm('Supprimer le département ?')) return;
        try{
          const res = await fetchJSON(`/api/departments/${d.id}`, {method:'DELETE'});
          await loadDepartments();
        }catch(e){ console.error(e); }
      });
      right.appendChild(edit); right.appendChild(del);
      row.appendChild(left); row.appendChild(right);
      container.appendChild(row);
    });
  }

  function populateChatDepartments(list){
    let sel = document.querySelector('#chat-department-select');
    if(!sel){
      // create select next to channel select
      const channelEl = document.querySelector('#chat-channel-select');
      if(!channelEl) return;
      // container for selects to keep header compact
      let group = document.querySelector('.chat-controls .select-group');
      if(!group){ 
        group = document.createElement('div'); 
        group.className='select-group'; 
        channelEl.parentNode.appendChild(group); 
      }
      sel = document.createElement('select'); 
      sel.id='chat-department-select'; 
      sel.className='form-select form-select-sm';
      sel.style.minWidth='160px';
      // accessibility
      sel.setAttribute('aria-label', 'Sélectionner un département');
      sel.setAttribute('title', 'Sélectionner un département');
      group.appendChild(sel);
      // toggle visibility based on channel type
      channelEl.addEventListener('change', ()=>{ 
        sel.style.display = (channelEl.value==='department') ? 'inline-block' : 'none'; 
      });
    }
    sel.innerHTML = '';
    const noneOpt = document.createElement('option'); 
    noneOpt.value=''; 
    noneOpt.textContent='-- Sélectionner le département --'; 
    sel.appendChild(noneOpt);
    list.forEach(d => { 
      const o = document.createElement('option'); 
      o.value = d.id; 
      o.textContent = d.name; 
      sel.appendChild(o); 
    });
    // if channel not department hide
    const channelSel = document.querySelector('#chat-channel-select');
    if(channelSel && channelSel.value !== 'department') sel.style.display='none';
    // announce initial selection state (include the department name if already selected)
    const live = document.querySelector('#chat-channel-live');
    if(live){
      if(channelSel && channelSel.value === 'department'){
        const selOpt = sel.options[sel.selectedIndex];
        live.textContent = selOpt && selOpt.value ? `Département ${selOpt.text} sélectionné` : 'Canal département sélectionné';
      }else{
        live.textContent = '';
      }
    }
    // announce when user picks a department
    sel.addEventListener('change', ()=>{
      if(!live) return;
      const opt = sel.options[sel.selectedIndex];
      live.textContent = opt && opt.value ? `Département ${opt.text} sélectionné` : 'Canal département sélectionné';
    });
  }

  async function loadTechnicians(){
    try{
      const res = await fetchJSON('/api/technicians', {method: 'GET'});
      const techs = res.technicians || [];
      let sel = document.querySelector('#chat-technician-select');
      if(!sel){
        const channelEl = document.querySelector('#chat-channel-select');
        if(!channelEl) return;
        // ensure select group exists
        let group = document.querySelector('.chat-controls .select-group');
        if(!group){ 
          group = document.createElement('div'); 
          group.className='select-group'; 
          channelEl.parentNode.appendChild(group); 
        }
        sel = document.createElement('select'); 
        sel.id='chat-technician-select'; 
        sel.className='form-select form-select-sm';
        sel.style.minWidth='160px';
        // accessibility
        sel.setAttribute('aria-label', 'Sélectionner un technicien');
        sel.setAttribute('title', 'Sélectionner un technicien');
        group.appendChild(sel);
        channelEl.addEventListener('change', ()=>{ 
          sel.style.display = (channelEl.value==='technician') ? 'inline-block' : 'none'; 
        });
      }
      sel.innerHTML = '';
      const noneOpt = document.createElement('option'); 
      noneOpt.value=''; 
      noneOpt.textContent='-- Sélectionner le technicien --'; 
      sel.appendChild(noneOpt);
      // announce initial state
      const live = document.querySelector('#chat-channel-live');
      const channelSel = document.querySelector('#chat-channel-select');
      if(live) live.textContent = channelSel && channelSel.value === 'technician' ? 'Canal technicien sélectionné' : '';
      techs.forEach(t => { 
        const o = document.createElement('option'); 
        o.value = t.id; 
        o.textContent = t.name; 
        sel.appendChild(o); 
      });
      if(channelSel && channelSel.value !== 'technician') sel.style.display='none';
    }catch(e){ console.error('loadTechnicians', e); }
  }

  async function saveDepartment(ev){
    ev && ev.preventDefault();
    const id = $('#dept-id').value;
    const name = $('#dept-name').value && $('#dept-name').value.trim();
    const desc = $('#dept-desc').value && $('#dept-desc').value.trim();
    if(!name) { alert('Nom requis'); return; }
    try{
      if(id){
        await fetchJSON(`/api/departments/${id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description: desc})});
      }else{
        await fetchJSON('/api/departments', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name, description: desc})});
      }
      // refresh
      $('#dept-id').value=''; $('#dept-name').value=''; $('#dept-desc').value='';
      await loadDepartments();
    }catch(e){ console.error('saveDepartment', e); }
  }

  function wireChat(){
    const sendBtn = $('#chat-send');
    const assistBtn = $('#chat-assist');
    const input = $('#chat-input');
    if(sendBtn) sendBtn.addEventListener('click', sendChat);
    if(assistBtn) assistBtn.addEventListener('click', askAssistant);
    if(input) input.addEventListener('keydown', (e)=>{ if(e.key==='Enter'){ sendChat(); }});
    const refreshBtn = $('#chat-refresh');
    if(refreshBtn) refreshBtn.addEventListener('click', ()=> loadChat());
    const clearBtn = $('#chat-clear');
    if(clearBtn && cfg.chatClear){
      clearBtn.addEventListener('click', async ()=>{
        try{
          clearBtn.disabled = true;
          const res = await fetchJSON(cfg.chatClear, {method:'POST'});
          if(res && res.ok){ await loadChat(); }
        }catch(e){}
        finally{ clearBtn.disabled = false; }
      });
    }
    // Departments / Technicians wiring
    const manageBtn = document.querySelector('#manage-departments-btn');
    if(manageBtn){
      manageBtn.addEventListener('click', async ()=>{ await loadDepartments(); });
    }
    // preload departments + technicians so selects appear quickly
    loadDepartments();
    loadTechnicians();
    // show/hide selects when channel changes
    const channelSel = document.querySelector('#chat-channel-select');
    if(channelSel){
      channelSel.addEventListener('change', (e)=>{
        const v = e.target.value;
        const dept = document.querySelector('#chat-department-select');
        const tech = document.querySelector('#chat-technician-select');
        if(dept) dept.style.display = (v === 'department') ? 'inline-block' : 'none';
        if(tech) tech.style.display = (v === 'technician') ? 'inline-block' : 'none';
        // announce to screen readers
        const live = document.querySelector('#chat-channel-live');
        if(live){
          if(v === 'department') live.textContent = 'Canal département sélectionné';
          else if(v === 'technician') live.textContent = 'Canal technicien sélectionné';
          else live.textContent = 'Canal global sélectionné';
        }
      });
    }
    // announce department/technician select changes
    document.addEventListener('change', (ev)=>{
      const live = document.querySelector('#chat-channel-live');
      if(!live) return;
      const target = ev.target;
      if(target && target.id === 'chat-department-select'){
        const name = target.options[target.selectedIndex] ? target.options[target.selectedIndex].text : '';
        live.textContent = name ? `Département ${name} sélectionné` : 'Aucun département sélectionné';
      }
      if(target && target.id === 'chat-technician-select'){
        const name = target.options[target.selectedIndex] ? target.options[target.selectedIndex].text : '';
        live.textContent = name ? `Technicien ${name} sélectionné` : 'Aucun technicien sélectionné';
      }
    });
    const deptForm = document.querySelector('#department-form');
    if(deptForm){ deptForm.addEventListener('submit', saveDepartment); }
  }

  // Init
  document.addEventListener('DOMContentLoaded', async function(){
    wireChat();
    await refreshStats();
    await renderKanban();
    await refreshPresence();
    await heartbeat();
    // load chat only when modal opened (AJAX modal)
    try{
      const chatModalEl = document.getElementById('teamChatModal');
      if(chatModalEl){
        chatModalEl.addEventListener('shown.bs.modal', async function(){
          await loadChat();
        });
      } else {
        // fallback for inline mode
        await loadChat();
      }
    }catch(e){ /* ignore if bootstrap not present */ }
    // schedulers
    setInterval(refreshStats, 15000);
    setInterval(renderKanban, 20000);
    setInterval(refreshPresence, 12000);
    setInterval(heartbeat, 30000);
  });
})();
