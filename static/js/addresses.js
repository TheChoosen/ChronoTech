// AJAX CRUD for customer addresses
(function(){
  function getCsrf(){ return (window.CT && window.CT.getCsrfToken) ? window.CT.getCsrfToken() : '' }
  function showToast(msg, type){ if(window.CT && window.CT.showToast) window.CT.showToast(msg, type); else alert(msg); }

  document.addEventListener('DOMContentLoaded', function(){
    var addrModal = document.getElementById('addressModal'); if(!addrModal) return;
    addrModal.addEventListener('show.bs.modal', function(e){
      var trigger = e.relatedTarget; var action = trigger && trigger.getAttribute('data-action');
      var form = document.getElementById('address-form'); form.reset();
      document.getElementById('address-id').value = '';
      if(action === 'edit' && trigger){
        try{
          var data = JSON.parse(trigger.getAttribute('data-address'));
          document.getElementById('address-id').value = data.id || '';
          document.getElementById('address-label').value = data.label || '';
          document.getElementById('address-street').value = data.street || '';
          document.getElementById('address-postal').value = data.postal_code || '';
          document.getElementById('address-city').value = data.city || '';
          document.getElementById('address-country').value = data.country || '';
          document.getElementById('address-phone').value = data.phone || '';
          addrModal.querySelector('.modal-title').textContent = 'Modifier l\'adresse';
        }catch(err){ console.error('Invalid address json', err); }
      } else {
        addrModal.querySelector('.modal-title').textContent = 'Ajouter une adresse';
      }
    });

    document.getElementById('address-save-btn').addEventListener('click', function(){
      var form = document.getElementById('address-form'); var fd = new FormData(form); var aid = fd.get('address_id');
      var url = aid ? ('/addresses/'+aid+'/update') : ('/'+fd.get('customer_id')+'/addresses/create');
      var headers = {'X-Requested-With':'XMLHttpRequest'}; var token = getCsrf(); if(token) headers['X-CSRF-Token'] = token;
      fetch(url, { method: 'POST', body: fd, headers: headers, credentials: 'same-origin' })
        .then(r => r.json()).then(resp => {
          if(resp && resp.success){
            var a = resp.address || {};
            if(!aid){ // created
              var container = document.getElementById('addresses-list'); var no = document.getElementById('no-addresses'); if(no) no.remove();
              var div = document.createElement('div'); div.className='border rounded p-2 mb-2 address-item'; div.setAttribute('data-address-id', resp.id || (a && a.id) || '');
              div.innerHTML = '<div class="d-flex justify-content-between align-items-start">'<
                + '<div>'
                + '<strong class="address-label">'+(a.label||fd.get('label')||'Adresse')+'</strong>'
                + '<div class="small text-muted address-street">'+(a.street||fd.get('street')||'')+'</div>'
                + '<div class="small text-muted">'+(a.postal_code||fd.get('postal_code')||'')+' '+(a.city||fd.get('city')||'')+' - '+(a.country||fd.get('country')||'')+'</div>'
                + (a.phone ? ('<div class="small">Tél: '+a.phone+'</div>') : (fd.get('phone')? '<div class="small">Tél: '+fd.get('phone')+'</div>':''))
                + '</div>'
                + '<div class="btn-group">'
                + '<button class="btn btn-sm btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#addressModal" data-action="edit" data-address="'+JSON.stringify(a || {})+'"><i class="fas fa-edit"></i></button>'
                + '<button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteAddress('+ (resp.id || (a && a.id) || '') +', '+ fd.get('customer_id') +')"><i class="fas fa-trash"></i></button>'
                + '</div>'
                + '</div>';
              container.insertBefore(div, container.firstChild);
            } else { // updated
              var el = document.querySelector('.address-item[data-address-id="'+aid+'"]');
              if(el){
                el.querySelector('.address-label').textContent = resp.address.label || fd.get('label') || '';
                el.querySelector('.address-street').textContent = resp.address.street || fd.get('street') || '';
                // update city/postal/country
                var info = el.querySelectorAll('.small.text-muted');
                if(info && info.length>=2){ info[1].textContent = (resp.address.postal_code||fd.get('postal_code')||'') + ' ' + (resp.address.city||fd.get('city')||'') + ' - ' + (resp.address.country||fd.get('country')||''); }
                var phoneEl = el.querySelector('.small');
                if(resp.address.phone){ if(phoneEl) phoneEl.textContent = 'Tél: '+resp.address.phone; else el.querySelector('div').insertAdjacentHTML('beforeend','<div class="small">Tél: '+resp.address.phone+'</div>'); }
                else if(phoneEl) phoneEl.remove();
              }
            }
            var modal = bootstrap.Modal.getInstance(document.getElementById('addressModal')); if(modal) modal.hide(); showToast('Adresse enregistrée', 'success');
          } else { alert(resp && resp.message ? resp.message : 'Erreur'); }
        }).catch(err => { console.error(err); alert('Erreur réseau'); });
    });

  });

  window.deleteAddress = function(id, customer_id){ if(!confirm('Supprimer cette adresse ?')) return; var fd=new FormData(); fd.append('customer_id', customer_id||''); var headers={'X-Requested-With':'XMLHttpRequest'}; var token=getCsrf(); if(token) headers['X-CSRF-Token']=token; fetch('/addresses/'+id+'/delete',{ method:'POST', body:fd, headers:headers, credentials:'same-origin' }).then(r=>r.json()).then(resp=>{ if(resp && resp.success){ var el=document.querySelector('.address-item[data-address-id="'+id+'"]'); if(el) el.remove(); var container=document.getElementById('addresses-list'); if(container && container.querySelectorAll('.address-item').length===0){ var p=document.createElement('p'); p.className='text-muted text-center'; p.id='no-addresses'; p.textContent='Aucune adresse de livraison'; container.appendChild(p);} showToast('Adresse supprimée','success'); } else { alert(resp && resp.message? resp.message:'Erreur suppression'); } }).catch(err=>{ console.error(err); alert('Erreur réseau'); }); };

})();
