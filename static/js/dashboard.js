(function(){
  const cfg = window.__DASHBOARD__ && window.__DASHBOARD__.endpoints ? window.__DASHBOARD__.endpoints : {};
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  async function fetchJSON(url, opts={}){
    const res = await fetch(url, Object.assign({headers: {'X-Requested-With':'XMLHttpRequest'}}, opts));
    if(!res.ok) throw new Error('HTTP '+res.status);
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
      }
    }catch(e){ /* silent */ }
  }
  // Presence heartbeat and list
  async function heartbeat(){
    if(!cfg.heartbeat) return;
    try{ await fetchJSON(cfg.heartbeat, {method:'POST'}); }catch(e){}
  }
  async function refreshPresence(){
    if(!cfg.presence) return;
    try{
      const data = await fetchJSON(cfg.presence);
      const users = data.users || [];
      const container = $('#online-users');
      const badge = $('#online-count');
      if(badge) badge.textContent = users.length;
      if(container){
        container.innerHTML = '';
        users.forEach(u=>{
          const el = document.createElement('span');
          el.className = 'user-chip';
          el.textContent = `${u.name || 'Utilisateur'} (${u.role || ''})`;
          container.appendChild(el);
        });
      }
    }catch(e){ /* silent */ }
  }

  // Kanban
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
  if(!group){ group = document.createElement('div'); group.className='select-group'; channelEl.parentNode.appendChild(group); }
  sel = document.createElement('select'); sel.id='chat-department-select'; sel.className='form-select form-select-sm';
  sel.style.minWidth='160px';
      // accessibility
      sel.setAttribute('aria-label', 'Sélectionner un département');
      sel.setAttribute('title', 'Sélectionner un département');
  group.appendChild(sel);
      // toggle visibility based on channel type
      channelEl.addEventListener('change', ()=>{ sel.style.display = (channelEl.value==='department') ? 'inline-block' : 'none'; });
    }
  sel.innerHTML = '';
    const noneOpt = document.createElement('option'); noneOpt.value=''; noneOpt.textContent='-- Sélectionner le département --'; sel.appendChild(noneOpt);
    list.forEach(d => { const o = document.createElement('option'); o.value = d.id; o.textContent = d.name; sel.appendChild(o); });
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
  if(!group){ group = document.createElement('div'); group.className='select-group'; channelEl.parentNode.appendChild(group); }
  sel = document.createElement('select'); sel.id='chat-technician-select'; sel.className='form-select form-select-sm';
  sel.style.minWidth='160px';
        // accessibility
        sel.setAttribute('aria-label', 'Sélectionner un technicien');
        sel.setAttribute('title', 'Sélectionner un technicien');
  group.appendChild(sel);
        channelEl.addEventListener('change', ()=>{ sel.style.display = (channelEl.value==='technician') ? 'inline-block' : 'none'; });
      }
  sel.innerHTML = '';
  const noneOpt = document.createElement('option'); noneOpt.value=''; noneOpt.textContent='-- Sélectionner le technicien --'; sel.appendChild(noneOpt);
  // announce initial state
  const live = document.querySelector('#chat-channel-live');
  const channelSel = document.querySelector('#chat-channel-select');
  if(live) live.textContent = channelSel && channelSel.value === 'technician' ? 'Canal technicien sélectionné' : '';
  techs.forEach(t => { const o = document.createElement('option'); o.value = t.id; o.textContent = t.name; sel.appendChild(o); });
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
