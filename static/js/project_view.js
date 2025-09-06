(() => {
  // Функция выбора элемента по селектору
  const select = (sel) => document.querySelector(sel);

  // Получаем корневой элемент приложения
  const appRoot = select('#app-root');
  const projectId = appRoot ? appRoot.getAttribute('data-project-id') : '';

  // Получение сохранённого состояния проекта
  function getSnapshot() {
    const el = document.getElementById('snapshot-data');
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || 'null');
    } catch {
      return null;
    }
  }

  // Обработчик перетаскивания файлов
  function handleDrop(e) {
    e.preventDefault();
    const input = document.getElementById('file');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      input.files = e.dataTransfer.files;
    }
  }

  function handleDrag(e) {
    e.preventDefault();
  }

  // Загрузка CSV файла
  async function uploadCsv(e) {
    e.preventDefault();
    const form = e.target.closest('form');
    const fd = new FormData(form);
    const res = await fetch(form.action, { method: 'POST', body: fd });
    const data = await res.json();
    if (data.preview && data.preview.info) {
      renderPreview(data.preview.head, data.preview.info.column_names);
      renderSelectors(data.preview.info.column_names);
    }
  }

  
  
   

  // Рендер выборочных элементов интерфейса
  function renderPreview(data, column_names){
    if(data){
      renderTable('preview-table', column_names, data);
    }
  }

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

  function labelWrap(title, el) {
    const wrap = document.createElement('div');
    const h = document.createElement('div');
    h.textContent = title;
    h.style.color = '#8b97a7';
    h.style.margin = '8px 0 4px';
    wrap.appendChild(h);
    wrap.appendChild(el);
    return wrap;
  }


  async function applySelection(){
    const target = document.getElementById('target').value;
    const features = Array.from(document.querySelectorAll('input[name="feat"]:checked')).map(i=>i.value);
    const res = await fetch(`/project/${projectId}/select`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({target, features, })});
    const data = await res.json();
    tableData = [];
    for (let i=0 ; i < 5; i++) {
      tableData.push(data.data.records[i]);
    }

    if(data.data){
      renderTable('seleted-table', data.data.columns, tableData);
      drawPlot(target, features, data.data);
    }
  }

  function renderTable(tableName, columns, rows) {
    const host = document.getElementById(tableName);
    host.innerHTML = '';
    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    const thead = document.createElement('thead');
    const thtr = document.createElement('tr');
    columns.forEach((c) => {
      const th = document.createElement('th');
      th.textContent = c;
      th.style.borderBottom = '1px solid #1d222a';
      th.style.textAlign = 'left';
      th.style.padding = '4px 6px';
      thtr.appendChild(th);
    });
    thead.appendChild(thtr);
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    rows.forEach((r) => {
      const tr = document.createElement('tr');
      columns.forEach((c) => {
        const td = document.createElement('td');
        td.textContent = r[c];
        td.style.padding = '4px 6px';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    host.appendChild(table);
  }

  // Отрисовка графика
  function drawPlot(target, features, data) {
    const el = document.getElementById('plot');
    const cols = data.columns;
    const rows = data.records;
    const x = Array.from({ length: rows.length }, (_, i) => i);
    const traces = [];
    if (target && cols.includes(target)) {
      traces.push({
        x,
        y: rows.map((r) => r[target]),
        name: target,
        mode: 'lines',
      });
    }
    features.forEach((f) => {
      if (cols.includes(f)) {
        traces.push({
          x,
          y: rows.map((r) => r[f]),
          name: f,
          mode: 'lines',
        });
      }
    });
    Plotly.newPlot(el, traces, {
      paper_bgcolor: '#111418',
      plot_bgcolor: '#111418',
      font: { color: '#e6e6e6' },
    });
  }

  // Отрисовка прогноза
  function drawForecast(target, prediction) {
    const src = document.getElementById('pp_plot');
    const existing = src && src.data && src.data[0] ? src.data[0] : null;
    let baseX = [], baseY = [];
    if (existing) {
      baseX = existing.x;
      baseY = existing.y;
    }
    const start = baseX.length;
    const x2 = Array.from({ length: prediction.length }, (_, i) => start + i);
    const trace1 = { x: baseX, y: baseY, name: target, mode: 'lines' };
    const trace2 = { x: x2, y: prediction, name: 'Прогноз', mode: 'lines' };
    Plotly.newPlot('forecast_plot', [trace1, trace2], {
      paper_bgcolor: '#111418',
      plot_bgcolor: '#111418',
      font: { color: '#e6e6e6' },
    });
  }

  // Запуск тренировки модели
  async function runTrain() {
    const target = document.getElementById('target')?.value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    const model = document.getElementById('mdl').value;
    const windowSize = parseInt(document.getElementById('win').value, 10);
    const horizon = parseInt(document.getElementById('hor').value, 10);
    const epochs = parseInt(document.getElementById('ep').value, 10);
    const res = await fetch(`/project/${projectId}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, model, window: windowSize, horizon, epochs }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || 'Ошибка');
      return;
    }
    document.getElementById('train_info').textContent = `Loss: ${data.loss.toFixed(6)}`;
    drawForecast(target, data.prediction);
  }


  // Предварительная обработка данных
  async function runPP() {
    const target = document.getElementById('target')?.value;
    const method = document.getElementById('pp_method').value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    const res = await fetch(`/project/${projectId}/preprocess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, method }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || 'Ошибка');
      return;
    }
    drawPP(data);
  }

  // Отрисовка результатов предварительной обработки
  function drawPP(data) {
    const rows = data.segment.records;
    const cols = data.segment.columns;
    const target = document.getElementById('target').value;
    const x = Array.from({ length: rows.length }, (_, i) => i);
    const y = rows.map((r) => r[target]);
    Plotly.newPlot('pp_plot', [
      { x, y, name: target, mode: 'lines' },
    ], {
      paper_bgcolor: '#111418',
      plot_bgcolor: '#111418',
      font: { color: '#e6e6e6' },
      shapes: (data.bounds || []).map((b) => ({
        type: 'line',
        x0: b,
        x1: b,
        y0: Math.min(...y),
        y1: Math.max(...y),
        line: { color: '#ef4444', dash: 'dot' },
      })),
    });
    const cx = data.curve.x || [];
    const cy = data.curve.y || [];
    Plotly.newPlot('pp_curve', [
      { x: cx, y: cy, mode: 'lines+markers', name: 'Δ% длительность' },
    ], {
      paper_bgcolor: '#111418',
      plot_bgcolor: '#111418',
      font: { color: '#e6e6e6' },
    });
  }

  // Восстановление ранее сохранённых состояний
  function restore() {
    const snap = getSnapshot();
    if (!snap) return;
    if (snap.preview && snap.preview.info) {
      renderPreview(snap.preview.head, snap.preview.info.column_names);
      renderSelectors(snap.preview.info.column_names);
    }
    if (snap.sample) {
      tableData = [];
      for (let i=0 ; i < 5; i++) {
        tableData.push(snap.sample.records[i]);
      }

      const features = Array.from(document.getElementsByName('feat'))
      for (h of snap.sample.columns) {
        elem = features.find(el => el.value == h);
        elem.checked = true;
      }

      renderTable("seleted-table", snap.sample.columns, tableData);
      const sel = snap.selection || {};
      const t = sel.target;
      const f = sel.features || [];
      drawPlot(t, f, snap.sample);
      if (t) {
        const tgtSel = document.getElementById('target');
        if (tgtSel) {
          tgtSel.value = t;
        }
      }
    }
    if (snap.preprocess) {
      drawPP(snap.preprocess);
    }
    if (snap.train) {
      document.getElementById('train_info').textContent = `Loss: ${Number(snap.train.loss).toFixed(6)}`;
      const target = document.getElementById('target')?.value;
      if (target) {
        drawForecast(target, snap.train.prediction);
      }
    }
  }

  function bind(){
    const form = document.getElementById('upload-form');
    if(form){ form.addEventListener('submit', uploadCsv); }

    const dz = document.getElementById('dropzone');
    if(dz){ dz.addEventListener('drop', handleDrop); dz.addEventListener('dragover', handleDrag); }

    const pp = document.getElementById('pp_run');
    if(pp){ pp.addEventListener('click', runPP); }
    
    const tr = document.getElementById('train_run');
    if(tr){ tr.addEventListener('click', runTrain); }
    
    const ex = document.getElementById('export_pdf');
    if(ex){ ex.addEventListener('click', () => window.print()); }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bind();
    restore();
  });
})();


