// Shared JS helpers for Work Orders pages
// Handles: data-action delegation, file previews, geolocation, estimates, and progress bars

(function () {
    'use strict';

    function setProgressBars() {
        document.querySelectorAll('[data-progress]').forEach(function(el) {
            const val = parseFloat(el.getAttribute('data-progress')) || 0;
            el.style.width = val + '%';
        });
    }

    function getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function(position) {
                const lat = position.coords.latitude.toFixed(6);
                const lng = position.coords.longitude.toFixed(6);
                const latEl = document.querySelector('[name="location_latitude"]');
                const lngEl = document.querySelector('[name="location_longitude"]');
                if (latEl) latEl.value = lat;
                if (lngEl) lngEl.value = lng;
                const mapContainer = document.getElementById('editMapContainer') || document.getElementById('map');
                if (mapContainer) mapContainer.style.display = 'block';
            }, function() {
                alert('Impossible d\'obtenir votre position actuelle.');
            });
        } else {
            alert('La géolocalisation n\'est pas supportée par ce navigateur.');
        }
    }

    function calculateEstimate() {
        const priorityEl = document.querySelector('[name="priority"]');
        const descriptionEl = document.querySelector('[name="description"]');
        const durationEl = document.querySelector('[name="estimated_duration"]');
        const costEl = document.querySelector('[name="estimated_cost"]');

        if (!priorityEl) return;
        let baseDuration = 2;
        let baseRate = 80;
        const priority = priorityEl.value;
        const description = descriptionEl ? descriptionEl.value : '';

        if (priority === 'urgent') {
            baseDuration *= 1.5; baseRate *= 1.3;
        } else if (priority === 'high') {
            baseDuration *= 1.2; baseRate *= 1.1;
        }
        if (description.length > 200) baseDuration *= 1.3;

        if (durationEl) durationEl.value = baseDuration.toFixed(1);
        if (costEl) costEl.value = (baseDuration * baseRate).toFixed(2);
    }

    function previewFiles(inputEl, previewContainerSelector) {
        const preview = document.querySelector(previewContainerSelector);
        if (!preview) return;
        preview.innerHTML = '';
        if (!inputEl.files || inputEl.files.length === 0) {
            preview.style.display = 'none';
            return;
        }
        preview.style.display = 'flex';
        Array.from(inputEl.files).forEach(file => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-4 mb-3';
            const isImage = file.type.startsWith('image/');
            if (isImage) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    col.innerHTML = `
                        <div class="card">
                            <img src="${e.target.result}" class="card-img-top" style="height: 120px; object-fit: cover;">
                            <div class="card-body p-2">
                                <h6 class="card-title small mb-1">${file.name}</h6>
                                <small class="text-muted">${(file.size/1024).toFixed(1)} KB</small>
                            </div>
                        </div>
                    `;
                };
                reader.readAsDataURL(file);
            } else {
                col.innerHTML = `
                    <div class="card">
                        <div class="card-img-top d-flex align-items-center justify-content-center" style="height: 120px; background-color: #f8f9fa;">
                            <i class="fas fa-file fa-3x text-muted"></i>
                        </div>
                        <div class="card-body p-2">
                            <h6 class="card-title small mb-1">${file.name}</h6>
                            <small class="text-muted">${(file.size/1024).toFixed(1)} KB</small>
                        </div>
                    </div>
                `;
            }
            preview.appendChild(col);
        });
    }

    // Global click delegation for data-action
    document.addEventListener('click', function(e) {
        const el = e.target.closest('[data-action]');
        if (!el) return;
        const action = el.dataset.action;

        switch(action) {
            case 'location':
                getCurrentLocation();
                break;
            case 'calculate':
                calculateEstimate();
                break;
            case 'remove-media':
            case 'delete-media':
                const mediaId = el.dataset.mediaId;
                if (mediaId && confirm('Êtes-vous sûr de vouloir supprimer ce fichier ?')) {
                    fetch('/work_orders/delete_media', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
                        body: JSON.stringify({media_id: mediaId})
                    }).then(r => {
                        if (r.ok) location.reload(); else alert('Erreur lors de la suppression');
                    }).catch(() => alert('Erreur de connexion'));
                }
                break;
            case 'delete':
                if (confirm('Êtes-vous sûr de vouloir supprimer ?')) {
                    alert('Suppression non implémentée');
                }
                break;
        }
    });

    // Init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        setProgressBars();

        // File preview bindings
        const newFiles = document.getElementById('new_files');
        if (newFiles) {
            newFiles.addEventListener('change', function() {
                previewFiles(this, '#newFilesPreview');
            });
        }

        // Trigger customer info if select exists
        const customerSelect = document.getElementById('customer_id');
        if (customerSelect) customerSelect.dispatchEvent(new Event('change'));

    });

})();
