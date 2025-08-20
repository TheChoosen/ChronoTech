// Simple client-side loader for /vehicles/api
(function(){
  const table = document.getElementById('vehicles-table');
  if (!table) return; // Not on vehicles page, bail out early to avoid null errors
  const tableBody = table.querySelector('tbody');
  const pagination = document.getElementById('vehicles-pagination');
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
      tableBody.innerHTML = '<tr><td colspan="8" class="text-danger">Erreur de chargement</td></tr>';
      console.error('Erreur chargement véhicules', e);
    }
  }

  if (btnFilter) btnFilter.addEventListener('click', (e)=>{ e.preventDefault(); state.page = 1; load(); });
  if (btnReset) btnReset.addEventListener('click', (e)=>{ e.preventDefault(); if(qInput) qInput.value=''; if(makeInput) makeInput.value=''; if(modelInput) modelInput.value=''; if(yearInput) yearInput.value=''; state.page=1; load(); });

  // initial load
  document.addEventListener('DOMContentLoaded', ()=>{ load(); });
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
