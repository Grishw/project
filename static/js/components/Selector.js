
function renderSelectors(columns) {
    const sel = document.getElementById('selectors');
    sel.innerHTML = '';
    const t = document.createElement('select');
    t.id = 'target';
    columns.forEach((c) => {
      const o = document.createElement('option');
      o.value = c;
      o.textContent = c;
      t.appendChild(o);
    });
    sel.appendChild(labelWrap('Target', t));
    const feats = document.createElement('div');
    columns.forEach((c) => {
      const l = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.name = 'feat';
      cb.value = c;
      l.appendChild(cb);
      l.append(` ${c}`);
      l.style.marginRight = '8px';
      feats.appendChild(l);
    });
    sel.appendChild(labelWrap('Features', feats));
    const btn = document.createElement('button');
    btn.className = 'btn primary';
    btn.type = 'button';
    btn.textContent = 'Применить';
    btn.addEventListener('click', applySelection);
    sel.appendChild(btn);
  }

  
  async function applySelection(){
    const target = document.getElementById('target').value;
    const features = Array.from(document.querySelectorAll('input[name="feat"]:checked')).map(i=>i.value);
    const res = await fetch(`/project/${projectId}/select`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({target, features})});
    const data = await res.json();

    if(data.data){
      renderTable('seleted-table', data.data.columns, data.data.records);
      drawPlot(target, features, data.data);
    }
  }

  export default { renderSelectors, applySelection };