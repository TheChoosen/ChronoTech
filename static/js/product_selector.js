// Minimal AJAX product selector helper
// Usage: create an input with class 'product-search' and a data-target attribute where selected id will be written

async function fetchProducts(q){
    const url = `/products/api/list?q=${encodeURIComponent(q)}&limit=20`;
    const res = await fetch(url);
    if(!res.ok) return [];
    return await res.json();
}

function initProductSelectors(){
    document.querySelectorAll('.product-search').forEach(input => {
        const dropdown = document.createElement('div');
        dropdown.className = 'product-search-dropdown list-group position-absolute';
        dropdown.style.zIndex = 1050;
        dropdown.style.display = 'none';
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(dropdown);

        let timeout = null;
        input.addEventListener('input', function(){
            clearTimeout(timeout);
            const q = this.value.trim();
            if(!q){ dropdown.style.display='none'; return; }
            timeout = setTimeout(async ()=>{
                const items = await fetchProducts(q);
                dropdown.innerHTML = '';
                if(!items || items.length===0){ dropdown.style.display='none'; return; }
                items.forEach(it=>{
                    const el = document.createElement('button');
                    el.type='button';
                    el.className='list-group-item list-group-item-action';
                    el.textContent = `${it.name} ${it.sku ? '('+it.sku+')' : ''} ${it.price ? '- '+it.price+'€' : ''}`;
                    el.addEventListener('click', function(){
                        input.value = it.name;
                        const target = input.dataset.target;
                        if(target){
                            const hidden = document.querySelector(target);
                            if(hidden) hidden.value = it.id;
                        }
                        dropdown.style.display='none';
                    });
                    dropdown.appendChild(el);
                });
                dropdown.style.display = 'block';
            }, 250);
        });
        document.addEventListener('click', function(e){
            if(!input.contains(e.target) && !dropdown.contains(e.target)) dropdown.style.display='none';
        });
    });
}

window.initProductSelectors = initProductSelectors;
document.addEventListener('DOMContentLoaded', initProductSelectors);
