// Simple client-side loader for /vehicles/api
(function(){
  // initialize lazily because this script is loaded on multiple pages
  let tableBody = null;
  let pagination = null;
  const qInput = document.getElementById('filter-search');
  const makeInput = document.getElementById('filter-make');
  const modelInput = document.getElementById('filter-model');
  const yearInput = document.getElementById('filter-year');
  const btnFilter = document.getElementById('btn-filter');
  const btnReset = document.getElementById('btn-reset');

  let state = { page: 1, per_page: 20 };

  function buildQuery() {
    const params = new URLSearchParams();
    if (qInput && qInput.value) params.set('q', qInput.value);
    if (makeInput && makeInput.value) params.set('make', makeInput.value);
    if (modelInput && modelInput.value) params.set('model', modelInput.value);
    if (yearInput && yearInput.value) params.set('year', yearInput.value);
    params.set('page', state.page);
    params.set('per_page', state.per_page);
    return params.toString();
  }

  function renderRows(items) {
    if(!tableBody) return; // nothing to render on pages without the table
    tableBody.innerHTML = '';
    if (!items || items.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="8" class="text-center">Aucun véhicule trouvé</td>';
      tableBody.appendChild(tr);
      return;
    }

    items.forEach(v => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${v.id}</td>
        <td>${v.make || ''}</td>
        <td>${v.model || ''}</td>
        <td>${v.year || ''}</td>
        <td>${v.license_plate || ''}</td>
        <td>${v.vin || ''}</td>
        <td>${(v.notes || '').slice(0,80)}</td>
        <td>
          <a href="/vehicles/${v.id}/edit" class="btn btn-sm btn-outline-primary">Éditer</a>
          <form method="post" action="/vehicles/${v.id}/delete" style="display:inline" onsubmit="return confirm('Supprimer ce véhicule ?')">
            <button class="btn btn-sm btn-danger">Supprimer</button>
          </form>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  }

  function renderPagination(page, pages) {
    if(!pagination) return; // no pagination controls on some pages
    pagination.innerHTML = '';
    if (pages <= 1) return;
    for (let p = 1; p <= pages; p++) {
      const li = document.createElement('li');
      li.className = 'page-item' + (p === page ? ' active' : '');
      const a = document.createElement('a');
      a.className = 'page-link';
      a.href = '#';
      a.textContent = p;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        state.page = p;
        load();
      });
      li.appendChild(a);
      pagination.appendChild(li);
    }
  }

  async function load() {
    const qs = buildQuery();
    try {
      const resp = await fetch('/vehicles/api?' + qs, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error('Erreur réseau');
      const data = await resp.json();
      renderRows(data.items || []);
      renderPagination(data.page || 1, data.pages || 1);
    } catch (e) {
      if(tableBody) tableBody.innerHTML = '<tr><td colspan="8" class="text-danger">Erreur de chargement</td></tr>';
      console.error('Erreur chargement véhicules', e);
    }
  }

  if (btnFilter) btnFilter.addEventListener('click', (e)=>{ e.preventDefault(); state.page = 1; load(); });
  if (btnReset) btnReset.addEventListener('click', (e)=>{ e.preventDefault(); if(qInput) qInput.value=''; if(makeInput) makeInput.value=''; if(modelInput) modelInput.value=''; if(yearInput) yearInput.value=''; state.page=1; load(); });

  // initial load: set DOM-dependent refs then load
  document.addEventListener('DOMContentLoaded', ()=>{
    tableBody = document.querySelector('#vehicles-table tbody');
    pagination = document.getElementById('vehicles-pagination');
    load();
  });
})();

// Global handlers: intercept delete forms under #vehicles-table and modal add form already handled
document.addEventListener('submit', function(e){
  // intercept delete forms for vehicles to perform AJAX delete
  var form = e.target;
  if(form && form.matches && form.matches('form[action^="/vehicles/"][action$="/delete"]')){
    e.preventDefault();
    if(!confirm('Supprimer ce véhicule ?')) return false;
    // determine id from action
    var action = form.getAttribute('action');
    var token = (window.CT && window.CT.getCsrfToken) ? window.CT.getCsrfToken() : null;
    var headers = {'X-Requested-With': 'XMLHttpRequest'};
    if(token) headers['X-CSRF-Token'] = token;
    fetch(action, { method: 'POST', headers: headers, credentials: 'same-origin' })
      .then(r => r.json()).then(resp => {
        if(resp && resp.success){
          // remove row from DOM if present
          var rid = null;
          // try data-vehicle-id on parent li or table row
          var li = form.closest('li[data-vehicle-id]');
          if(li) rid = li.getAttribute('data-vehicle-id');
          var tr = form.closest('tr');
          if(tr && !rid){
            // assume first cell is id
            var cell = tr.querySelector('td'); if(cell) rid = cell.textContent.trim();
          }
          if(rid){
            var selector = '[data-vehicle-id="'+rid+'"]';
            var el = document.querySelector(selector);
            if(el) el.remove();
          }
          if(window.CT && window.CT.showToast) window.CT.showToast('Véhicule supprimé', 'success');
        } else {
          alert(resp && resp.message ? resp.message : 'Erreur suppression');
        }
    }).catch(()=> alert('Erreur réseau'));
    return false;
  }

  // intercept standalone create form on /vehicles/new if present
  if(form && form.matches && form.matches('form[action="/vehicles/create"]')){
    // allow modal add-vehicle form to continue (it's handled inline in _vehicles_modal)
    if(form.id === 'add-vehicle-form') return true;
    e.preventDefault();
    var token = (window.CT && window.CT.getCsrfToken) ? window.CT.getCsrfToken() : null;
    var headers = {'X-Requested-With': 'XMLHttpRequest'};
    if(token) headers['X-CSRF-Token'] = token;
    var fd = new FormData(form);
    fetch(form.action, { method: 'POST', body: fd, headers: headers, credentials: 'same-origin' })
      .then(r => r.json()).then(resp => {
        if(resp && resp.success){
          if(window.CT && window.CT.showToast) window.CT.showToast('Véhicule créé', 'success');
          // redirect to customer view if possible
          if(fd.get('customer_id')){
            window.location = '/customers/' + fd.get('customer_id');
          } else {
            // fallback to refresh index
            window.location.reload();
          }
        } else {
          alert(resp && resp.message ? resp.message : 'Erreur création');
        }
      }).catch(()=> alert('Erreur réseau'));
    return false;
  }
});

// Intercept the inline customer add vehicle form and submit via AJAX to update the list in-place
document.addEventListener('DOMContentLoaded', function(){
  var inlineForm = document.getElementById('customer-add-vehicle-form');
  if(!inlineForm) return;
  inlineForm.addEventListener('submit', function(e){
    e.preventDefault();
    var form = e.target;
    var fd = new FormData(form);
    var token = (window.CT && window.CT.getCsrfToken) ? window.CT.getCsrfToken() : null;
    var headers = {'X-Requested-With': 'XMLHttpRequest'};
    if(token) headers['X-CSRF-Token'] = token;

    fetch(form.action, { method: 'POST', body: fd, headers: headers, credentials: 'same-origin' })
      .then(function(r){
        if(!r.ok) throw new Error('Erreur serveur');
        return r.json();
      }).then(function(resp){
        if(resp && resp.success){
          var v = resp.vehicle || {};
          // create list-group-item element
          var container = document.querySelector('#vehicles-section .list-group');
          if(!container){
            // create container if missing
            container = document.createElement('div');
            container.className = 'list-group mb-3';
            var alert = document.querySelector('#vehicles-section .alert'); if(alert) alert.remove();
            var hr = document.querySelector('#vehicles-section hr');
            if(hr) hr.parentNode.insertBefore(container, hr);
            else document.querySelector('#vehicles-section .card-body').prepend(container);
          }
          var item = document.createElement('div');
          item.className = 'list-group-item d-flex justify-content-between align-items-start';
          item.setAttribute('data-vehicle-id', resp.id || (v.id || 'new'));
          item.innerHTML = `
            <div>
              <strong>${v.make || fd.get('make') || ''} ${v.model || fd.get('model') || ''}</strong>
              <div class="small text-muted">${v.year || fd.get('year') || ''} - ${v.license_plate || fd.get('license_plate') || ''}</div>
              ${v.notes ? '<div class="mt-1">'+(v.notes||'')+'</div>' : (fd.get('notes') ? '<div class="mt-1">'+fd.get('notes')+'</div>' : '')}
            </div>
            <div class="btn-group" role="group">
              <a href="/vehicles/${resp.id || (v.id||'')}/edit" class="btn btn-sm btn-outline-secondary">Modifier</a>
              <form method="POST" action="/vehicles/${resp.id || (v.id||'')}/delete" style="display:inline; margin:0;">
                <button type="submit" class="btn btn-sm btn-outline-danger">Supprimer</button>
              </form>
            </div>
          `;
          container.insertBefore(item, container.firstChild);
          // clear form
          form.reset();
          if(window.CT && window.CT.showToast) window.CT.showToast('Véhicule ajouté', 'success');
        } else {
          alert(resp && resp.message ? resp.message : 'Erreur création véhicule');
        }
      }).catch(function(err){
        console.error(err);
        alert('Erreur réseau');
      });
  });
});
