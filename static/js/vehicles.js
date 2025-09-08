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
  const perPageSelect = document.getElementById('per-page-select');
  const gotoPageInput = document.getElementById('goto-page');
  const gotoPageBtn = document.getElementById('goto-page-btn');
  const vehiclesInfo = document.getElementById('vehicles-info');
  const totalVehicles = document.getElementById('total-vehicles');

  let state = { page: 1, per_page: 20, sort_by: 'id', sort_dir: 'desc' };

  function buildQuery() {
    const params = new URLSearchParams();
    if (qInput && qInput.value) params.set('q', qInput.value);
    if (makeInput && makeInput.value) params.set('make', makeInput.value);
    if (modelInput && modelInput.value) params.set('model', modelInput.value);
    if (yearInput && yearInput.value) params.set('year', yearInput.value);
    params.set('page', state.page);
    params.set('per_page', state.per_page);
    params.set('sort_by', state.sort_by);
    params.set('sort_dir', state.sort_dir);
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
        <td>${(v.notes || '').slice(0,80)}${(v.notes || '').length > 80 ? '...' : ''}</td>
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

  function updateInfo(page, pages, total, currentCount) {
    if (!vehiclesInfo) return;
    const startItem = ((page - 1) * state.per_page) + 1;
    const endItem = Math.min(startItem + currentCount - 1, total);
    vehiclesInfo.innerHTML = `
      <i class="fas fa-info-circle"></i> 
      Affichage de <strong>${startItem}</strong> à <strong>${endItem}</strong> sur <strong>${total}</strong> véhicules
    `;
    
    // Mise à jour du badge total
    if (totalVehicles) {
      totalVehicles.innerHTML = `<i class="fas fa-car"></i> ${total} véhicules`;
    }
  }

  function renderPagination(page, pages) {
    if(!pagination) return; // no pagination controls on some pages
    pagination.innerHTML = '';
    if (pages <= 1) return;

    // Helper function to create page item
    function createPageItem(pageNum, text = null, isActive = false, isDisabled = false) {
      const li = document.createElement('li');
      li.className = 'page-item' + (isActive ? ' active' : '') + (isDisabled ? ' disabled' : '');
      const a = document.createElement('a');
      a.className = 'page-link';
      a.href = '#';
      a.textContent = text || pageNum;
      if (!isDisabled) {
        a.addEventListener('click', (e) => {
          e.preventDefault();
          state.page = pageNum;
          load();
        });
      }
      li.appendChild(a);
      return li;
    }

    // Helper function to create ellipsis
    function createEllipsis() {
      const li = document.createElement('li');
      li.className = 'page-item disabled';
      const span = document.createElement('span');
      span.className = 'page-link';
      span.textContent = '...';
      li.appendChild(span);
      return li;
    }

    // Bouton Précédent
    if (page > 1) {
      pagination.appendChild(createPageItem(page - 1, '← Précédent'));
    } else {
      pagination.appendChild(createPageItem(1, '← Précédent', false, true));
    }

    // Logic for smart pagination
    let startPage, endPage;
    
    if (pages <= 7) {
      // Moins de 7 pages, on affiche tout
      startPage = 1;
      endPage = pages;
    } else {
      // Plus de 7 pages, on utilise des ellipses
      if (page <= 4) {
        startPage = 1;
        endPage = 5;
      } else if (page >= pages - 3) {
        startPage = pages - 4;
        endPage = pages;
      } else {
        startPage = page - 2;
        endPage = page + 2;
      }
    }

    // Page 1 (toujours visible si pas dans la plage)
    if (startPage > 1) {
      pagination.appendChild(createPageItem(1, '1', page === 1));
      if (startPage > 2) {
        pagination.appendChild(createEllipsis());
      }
    }

    // Pages dans la plage
    for (let p = startPage; p <= endPage; p++) {
      pagination.appendChild(createPageItem(p, p.toString(), p === page));
    }

    // Dernière page (toujours visible si pas dans la plage)
    if (endPage < pages) {
      if (endPage < pages - 1) {
        pagination.appendChild(createEllipsis());
      }
      pagination.appendChild(createPageItem(pages, pages.toString(), page === pages));
    }

    // Bouton Suivant
    if (page < pages) {
      pagination.appendChild(createPageItem(page + 1, 'Suivant →'));
    } else {
      pagination.appendChild(createPageItem(pages, 'Suivant →', false, true));
    }

    // Ajout d'informations sur la pagination
    const info = document.createElement('li');
    info.className = 'page-item disabled d-none d-md-flex';
    info.innerHTML = `<span class="page-link bg-light">Page ${page} sur ${pages}</span>`;
    pagination.appendChild(info);
  }

  async function load() {
    const qs = buildQuery();
    
    // Indicateur de chargement
    if (pagination) pagination.classList.add('pagination-loading');
    if (vehiclesInfo) vehiclesInfo.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Chargement...';
    
    try {
      const resp = await fetch('/vehicles/api?' + qs, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error('Erreur réseau');
      const data = await resp.json();
      renderRows(data.items || []);
      renderPagination(data.page || 1, data.pages || 1);
      updateInfo(data.page || 1, data.pages || 1, data.total || 0, (data.items || []).length);
      
      // Update goto page input max
      if (gotoPageInput) {
        gotoPageInput.max = data.pages || 1;
        gotoPageInput.placeholder = `1-${data.pages || 1}`;
      }
    } catch (e) {
      if(tableBody) tableBody.innerHTML = '<tr><td colspan="8" class="text-danger"><i class="fas fa-exclamation-triangle"></i> Erreur de chargement</td></tr>';
      if(vehiclesInfo) vehiclesInfo.innerHTML = '<i class="fas fa-exclamation-triangle text-danger"></i> Erreur de chargement des données';
      console.error('Erreur chargement véhicules', e);
    } finally {
      // Retirer l'indicateur de chargement
      if (pagination) pagination.classList.remove('pagination-loading');
    }
  }

  if (btnFilter) btnFilter.addEventListener('click', (e)=>{ e.preventDefault(); state.page = 1; load(); });
  if (btnReset) btnReset.addEventListener('click', (e)=>{ e.preventDefault(); if(qInput) qInput.value=''; if(makeInput) makeInput.value=''; if(modelInput) modelInput.value=''; if(yearInput) yearInput.value=''; state.page=1; load(); });

  // Gestion du nombre d'éléments par page
  if (perPageSelect) {
    perPageSelect.addEventListener('change', (e) => {
      state.per_page = parseInt(e.target.value);
      state.page = 1; // Reset to first page
      load();
    });
  }

  // Navigation directe à une page
  if (gotoPageBtn && gotoPageInput) {
    gotoPageBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetPage = parseInt(gotoPageInput.value);
      if (targetPage && targetPage >= 1) {
        state.page = targetPage;
        load();
        gotoPageInput.value = ''; // Clear input
      }
    });

    // Support de la touche Entrée
    gotoPageInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        gotoPageBtn.click();
      }
    });
  }

  // Gestion du tri par colonnes
  if (table) {
    table.addEventListener('click', (e) => {
      const th = e.target.closest('th[data-sort]');
      if (!th) return;
      
      const sortField = th.getAttribute('data-sort');
      if (state.sort_by === sortField) {
        // Même colonne : basculer la direction
        state.sort_dir = state.sort_dir === 'asc' ? 'desc' : 'asc';
      } else {
        // Nouvelle colonne : tri ascendant par défaut
        state.sort_by = sortField;
        state.sort_dir = 'asc';
      }
      
      state.page = 1; // Reset à la première page
      updateSortIcons();
      load();
    });
  }

  function updateSortIcons() {
    // Reset tous les indicateurs
    document.querySelectorAll('#vehicles-table th[data-sort]').forEach(th => {
      th.classList.remove('sort-active', 'sort-asc', 'sort-desc');
      const icon = th.querySelector('i');
      if (icon) {
        icon.className = 'fas fa-sort text-muted';
      }
    });
    
    // Mettre à jour l'indicateur actif
    const activeHeader = document.querySelector(`#vehicles-table th[data-sort="${state.sort_by}"]`);
    if (activeHeader) {
      activeHeader.classList.add('sort-active', `sort-${state.sort_dir}`);
      const icon = activeHeader.querySelector('i');
      if (icon) {
        icon.className = `fas fa-sort-${state.sort_dir === 'asc' ? 'up' : 'down'} text-primary`;
      }
    }
  }

  // initial load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      updateSortIcons();
      load();
    });
  } else {
    updateSortIcons();
    load();
  }
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
