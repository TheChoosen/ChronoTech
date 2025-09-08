// AJAX CRUD for customer contacts
(function(){
  function getCsrf(){ return (window.CT && window.CT.getCsrfToken) ? window.CT.getCsrfToken() : '' }

  function showToast(msg, type){ if(window.CT && window.CT.showToast) window.CT.showToast(msg, type); else alert(msg); }

  // Populate modal when opened for edit
  document.addEventListener('DOMContentLoaded', function(){
    var contactModal = document.getElementById('contactModal');
    if(!contactModal) return;

    contactModal.addEventListener('show.bs.modal', function(e){
      var trigger = e.relatedTarget; // button that opened modal
      var action = trigger && trigger.getAttribute('data-action');
      var form = document.getElementById('contact-form');
      form.reset();
      document.getElementById('contact-id').value = '';
      if(action === 'edit' && trigger){
        try{
          var data = JSON.parse(trigger.getAttribute('data-contact'));
          document.getElementById('contact-id').value = data.id || '';
          document.getElementById('contact-name').value = data.name || '';
          document.getElementById('contact-role').value = data.role || '';
          document.getElementById('contact-email').value = data.email || '';
          document.getElementById('contact-phone').value = data.phone || '';
          contactModal.querySelector('.modal-title').textContent = 'Modifier le contact';
        }catch(err){
          console.error('Invalid contact json', err);
        }
      } else {
        contactModal.querySelector('.modal-title').textContent = 'Ajouter un contact';
      }
    });

    // Save button
    document.getElementById('contact-save-btn').addEventListener('click', function(){
      var form = document.getElementById('contact-form');
      var fd = new FormData(form);
      var cid = fd.get('contact_id');
      var url = cid ? ('/contacts/'+cid+'/update') : ('/'+fd.get('customer_id')+'/contacts/create');
      var headers = {'X-Requested-With':'XMLHttpRequest'};
      var token = getCsrf(); if(token) headers['X-CSRF-Token'] = token;

      fetch(url, { method: 'POST', body: fd, headers: headers, credentials: 'same-origin' })
        .then(r => r.json())
        .then(resp => {
          if(resp && resp.success){
            var contact = resp.contact || resp.contact || {};
            if(!cid){ // created -> prepend
              var container = document.getElementById('contacts-list');
              var noEl = document.getElementById('no-contacts'); if(noEl) noEl.remove();
              var div = document.createElement('div');
              div.className = 'border rounded p-2 mb-2 contact-item';
              div.setAttribute('data-contact-id', resp.id || (contact && contact.id) || '');
              div.innerHTML = `<div class="d-flex justify-content-between align-items-start">\
                <div>\
                  <h6 class="mb-1 contact-name">${contact.name || fd.get('name') || ''}</h6>\
                  <small class="text-muted contact-role">${contact.role || fd.get('role') || ''}</small>\
                  ${contact.email ? ('<br><a class="contact-email" href="mailto:'+contact.email+'">'+contact.email+'</a>') : (fd.get('email')? '<br><a class="contact-email" href="mailto:'+fd.get('email')+'">'+fd.get('email')+'</a>': '')}\
                  ${contact.phone ? ('<br><a class="contact-phone" href="tel:'+contact.phone+'">'+contact.phone+'</a>') : (fd.get('phone')? '<br><a class="contact-phone" href="tel:'+fd.get('phone')+'">'+fd.get('phone')+'</a>':'')}\
                </div>\
                <div class="btn-group">\
                  <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#contactModal" data-action="edit" data-contact='${JSON.stringify(contact)}'>\
                    <i class="fas fa-edit"></i>\
                  </button>\
                  <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteContact(${resp.id || (contact && contact.id) || ''}, ${fd.get('customer_id')})">\
                    <i class="fas fa-trash"></i>\
                  </button>\
                </div>\
              </div>`;
              container.insertBefore(div, container.firstChild);
            } else { // updated -> update DOM
              var el = document.querySelector('.contact-item[data-contact-id="'+cid+'"]');
              if(el){
                el.querySelector('.contact-name').textContent = resp.contact.name || fd.get('name') || '';
                el.querySelector('.contact-role').textContent = resp.contact.role || fd.get('role') || '';
                var emailEl = el.querySelector('.contact-email');
                if(resp.contact.email){
                  if(emailEl) { emailEl.href = 'mailto:'+resp.contact.email; emailEl.textContent = resp.contact.email; }
                  else el.querySelector('div').insertAdjacentHTML('beforeend', '<br><a class="contact-email" href="mailto:'+resp.contact.email+'">'+resp.contact.email+'</a>');
                } else if(emailEl) emailEl.remove();
                var phoneEl = el.querySelector('.contact-phone');
                if(resp.contact.phone){
                  if(phoneEl) { phoneEl.href = 'tel:'+resp.contact.phone; phoneEl.textContent = resp.contact.phone; }
                  else el.querySelector('div').insertAdjacentHTML('beforeend', '<br><a class="contact-phone" href="tel:'+resp.contact.phone+'">'+resp.contact.phone+'</a>');
                } else if(phoneEl) phoneEl.remove();
              }
            }
            var modal = bootstrap.Modal.getInstance(document.getElementById('contactModal'));
            if(modal) modal.hide();
            showToast('Contact enregistré', 'success');
          } else {
            alert(resp && resp.message ? resp.message : 'Erreur');
          }
        }).catch(err => { console.error(err); alert('Erreur réseau'); });
    });

  });

  // Expose deleteContact globally so inline onclick can call it
  window.deleteContact = function(id, customer_id){
    if(!confirm('Supprimer ce contact ?')) return;
    var fd = new FormData(); fd.append('customer_id', customer_id || '');
    var headers = {'X-Requested-With':'XMLHttpRequest'}; var token = getCsrf(); if(token) headers['X-CSRF-Token'] = token;
    fetch('/contacts/'+id+'/delete', { method: 'POST', body: fd, headers: headers, credentials: 'same-origin' })
      .then(r => r.json()).then(resp => {
        if(resp && resp.success){
          var el = document.querySelector('.contact-item[data-contact-id="'+id+'"]'); if(el) el.remove();
          // if list empty, show placeholder
          var container = document.getElementById('contacts-list');
          if(container && container.querySelectorAll('.contact-item').length === 0){
            var p = document.createElement('p'); p.className='text-muted text-center'; p.id='no-contacts'; p.textContent='Aucun contact supplémentaire'; container.appendChild(p);
          }
          showToast('Contact supprimé', 'success');
        } else {
          alert(resp && resp.message ? resp.message : 'Erreur suppression');
        }
      }).catch(err => { console.error(err); alert('Erreur réseau'); });
  };

  let contacts = [];
  let currentIndex = 0;

  function openContactForm(mode, index = null) {
      const modal = new bootstrap.Modal(document.getElementById('contactModal'));
      const form = document.getElementById('contactForm');
      const title = document.getElementById('contactModalTitle');
      const deleteBtn = document.getElementById('deleteContactBtn');
      form.reset();
      deleteBtn.style.display = 'none';

      if (mode === 'new') {
          title.textContent = 'Nouveau contact';
          document.getElementById('contactClient').value = window.CustomerName || '';
          document.getElementById('contactId').value = '';
      } else if (mode === 'edit' && index !== null) {
          title.textContent = 'Modifier contact';
          const c = contacts[index];
          Object.keys(c).forEach(k => {
              if (document.getElementById('contact' + capitalize(k))) {
                  document.getElementById('contact' + capitalize(k)).value = c[k];
              }
          });
          document.getElementById('contactId').value = c.id;
          deleteBtn.style.display = 'inline-block';
      }
      modal.show();
  }

  function capitalize(str) {
      return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function renderContactsGrid() {
      const tbody = document.querySelector('#contactsGrid tbody');
      tbody.innerHTML = contacts.map((c, i) => `
          <tr${i === currentIndex ? ' class="table-primary"' : ''}>
              <td>${c.name}</td>
              <td>${c.category}</td>
              <td>${c.phone_office}</td>
              <td>${c.phone_home}</td>
              <td>${c.cell}</td>
              <td>${c.email}</td>
              <td>${c.entry_date || ''}</td>
              <td><input type="checkbox" disabled ${c.order ? 'checked' : ''}></td>
              <td><input type="checkbox" disabled ${c.invoice ? 'checked' : ''}></td>
              <td>
                  <button class="btn btn-sm btn-outline-primary" onclick="openContactForm('edit',${i})"><i class="fa-solid fa-edit"></i></button>
              </td>
          </tr>
      `).join('');
      document.getElementById('contactsCount').textContent = contacts.length;
      document.getElementById('contactIndex').textContent = contacts.length ? currentIndex + 1 : 0;
      document.getElementById('contactTotal').textContent = contacts.length;
  }

  function navigateContact(action) {
      if (!contacts.length) return;
      switch(action) {
          case 'first': currentIndex = 0; break;
          case 'prev': currentIndex = Math.max(0, currentIndex - 1); break;
          case 'next': currentIndex = Math.min(contacts.length - 1, currentIndex + 1); break;
          case 'last': currentIndex = contacts.length - 1; break;
      }
      renderContactsGrid();
  }

  function searchContact() {
      const term = prompt('Recherche par nom ou email:');
      if (!term) return;
      const idx = contacts.findIndex(c => c.name.includes(term) || c.email.includes(term));
      if (idx >= 0) {
          currentIndex = idx;
          renderContactsGrid();
      } else {
          alert('Aucun contact trouvé');
      }
  }

  function printContacts() {
      const html = document.getElementById('contactsGrid').outerHTML;
      const frame = document.getElementById('printFrame');
      frame.contentDocument.write('<html><head><title>Contacts</title></head><body>' + html + '</body></html>');
      frame.contentDocument.close();
      frame.contentWindow.print();
  }

  // CRUD

  document.getElementById('contactForm').addEventListener('submit', function(e) {
      e.preventDefault();
      // Validation
      const name = document.getElementById('contactName').value.trim();
      if (!name) {
          alert('Le nom du contact est obligatoire');
          return;
      }
      const contact = {};
      Array.from(this.elements).forEach(el => {
          if (el.name) {
              if (el.type === 'checkbox') {
                  contact[el.name] = el.checked;
              } else {
                  contact[el.name] = el.value;
              }
          }
      });
      if (!contact.contact_id) {
          // Nouveau
          contact.id = Date.now();
          contacts.push(contact);
          currentIndex = contacts.length - 1;
      } else {
          // Edition
          const idx = contacts.findIndex(c => c.id == contact.contact_id);
          if (idx >= 0) contacts[idx] = contact;
      }
      renderContactsGrid();
      bootstrap.Modal.getInstance(document.getElementById('contactModal')).hide();
  });

  function deleteContact() {
      const id = document.getElementById('contactId').value;
      if (!id) return;
      if (!confirm('Supprimer ce contact ?')) return;
      const idx = contacts.findIndex(c => c.id == id);
      if (idx >= 0) {
          contacts.splice(idx, 1);
          currentIndex = Math.max(0, currentIndex - 1);
          renderContactsGrid();
          bootstrap.Modal.getInstance(document.getElementById('contactModal')).hide();
      }
  }

  // Initialisation
  window.addEventListener('DOMContentLoaded', function() {
      // TODO: Charger les contacts depuis l'API si disponible
      renderContactsGrid();
  });

})();
