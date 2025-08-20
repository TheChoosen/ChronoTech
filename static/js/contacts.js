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

})();
