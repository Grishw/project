(() => {
  // Функция выбора элемента по селектору
  const select = (sel) => document.querySelector(sel);
  // Текущее клиентское состояние (минимальный снапшот)
  let currentSnap = null;

  function setCurrentSnap(partial) {
    currentSnap = Object.assign({}, currentSnap || {}, partial || {});
    updateSteps(currentSnap);
  }

  function updateSteps(snap) {
    try {
      const list = document.querySelectorAll('.steps .step');
      if (!list || !list.length) return;
      const hasPreview = !!(snap && snap.preview && snap.preview.info);
      const hasSample = !!(snap && snap.sample && snap.sample.columns);
      const hasPP = !!(snap && snap.preprocess && snap.preprocess.segment);
      const hasTrain = !!(snap && snap.train && (snap.train.loss !== undefined));

      // Индексы шагов в разметке:
      // 0: Загрузка данных
      // 1: Информация о данных
      // 2: Предподготовка
      // 3: Выбор модели
      // 4: Обучение и прогноз
      // 5: Экспорт PDF

      const done = [
        hasPreview,       // 0
        hasPreview || hasSample, // 1 — после загрузки уже есть информация
        hasPP,            // 2
        hasSample || hasPP || hasTrain, // 3 — модель можно выбирать после выборки/PP
        hasTrain,         // 4
        false,            // 5 — помечаем вручную при экспорте
      ];

      // Сброс классов
      list.forEach(li => {
        li.classList.remove('step-done');
        li.classList.remove('step-active');
      });

      // Проставить done
      done.forEach((isDone, i) => {
        if (list[i] && isDone) list[i].classList.add('step-done');
      });

      // Активный — первый не завершенный
      const activeIdx = done.findIndex(v => !v);
      if (activeIdx >= 0 && list[activeIdx]) {
        list[activeIdx].classList.add('step-active');
      }
    } catch (_) {
      // без падения UI
    }
  }

  // Вспомогательные парсеры времени
  function parseCompactYYYYMMDDTHHMM(s) {
    const m = /^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})$/.exec(String(s));
    if (!m) return null;
    const [, y, mo, d, h, mi] = m;
    return new Date(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi));
  }

  // Простой парсер форматов вида %Y-%m-%d %H:%M:%S, %Y%m%dT%H%M и т.п.
  function parseByFormat(input, fmt) {
    if (!fmt || input == null) return null;
    const s = String(input);
    const map = {
      '%Y': '(?<Y>\\d{4})',
      '%m': '(?<m>\\d{2})',
      '%d': '(?<d>\\d{2})',
      '%H': '(?<H>\\d{2})',
      '%M': '(?<M>\\d{2})',
      '%S': '(?<S>\\d{2})',
    };
    const escapeRe = (t) => t.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    let reStr = '';
    for (let i = 0; i < fmt.length; ) {
      if (fmt[i] === '%' && i + 1 < fmt.length) {
        const tok = fmt.slice(i, i + 2);
        if (map[tok]) { reStr += map[tok]; i += 2; continue; }
      }
      reStr += escapeRe(fmt[i]);
      i += 1;
    }
    const re = new RegExp('^' + reStr + '$');
    const m = re.exec(s);
    if (!m || !m.groups) return null;
    const Y = Number(m.groups.Y ?? '1970');
    const mo = Number(m.groups.m ?? '1');
    const d = Number(m.groups.d ?? '1');
    const H = Number(m.groups.H ?? '0');
    const M = Number(m.groups.M ?? '0');
    const S = Number(m.groups.S ?? '0');
    return new Date(Y, (mo || 1) - 1, d || 1, H || 0, M || 0, S || 0);
  }

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
      setCurrentSnap({ preview: data.preview });
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
    // Справочники времени
    const TIME_KINDS = [
      { v: 'index', t: 'Индекс (0..N-1)' },
      { v: 'timestamp_sec', t: 'Unix timestamp (сек)' },
      { v: 'timestamp_ms', t: 'Unix timestamp (мс)' },
      { v: 'datetime_format', t: 'Дата/время по формату' },
      { v: 'iso_date', t: 'ISO-формат даты' },
      { v: 'rfc_2822', t: 'RFC 2822 формат' },
      { v: 'human_readable', t: 'Читаемый человеком формат' },
    ];
    const TIME_EXAMPLES = [
      { v: 0, t: 'Индекс (0..N-1)' },
      { v: 1685234567, t: 'Unix timestamp (сек)' },
      { v: 1685234567890, t: 'Unix timestamp (мс)' },
      { v: '2023-05-28T12:34:56+03:00', t: 'Дата/время по формату' },
      { v: '2023-05-28', t: 'ISO-формат даты' },
      { v: 'Sun, 28 May 2023 12:34:56 +0300', t: 'RFC 2822 формат' },
      { v: '28 мая 2023 г., воскресенье, 12:34:56', t: 'Читаемый человеком формат' },
    ];
    const t = document.createElement('select');
    t.id = 'target';
    columns.forEach((c) => {
      const o = document.createElement('option');
      o.value = c;
      o.textContent = c;
      t.appendChild(o);
    });
    sel.appendChild(labelWrap('Target', t));

    // Временная колонка
    const timeCol = document.createElement('select');
    timeCol.id = 'time_column';
    const noneOpt = document.createElement('option');
    noneOpt.value = '';
    noneOpt.textContent = '— не использовать —';
    timeCol.appendChild(noneOpt);
    columns.forEach((c) => {
      const o = document.createElement('option');
      o.value = c;
      o.textContent = c;
      timeCol.appendChild(o);
    });
    sel.appendChild(labelWrap('Временная колонка', timeCol));

    // Тип времени
    const timeKind = document.createElement('select');
    timeKind.id = 'time_kind';
    TIME_KINDS.forEach(({ v, t }) => {
      const o = document.createElement('option');
      o.value = v;
      o.textContent = t;
      timeKind.appendChild(o);
    });
    sel.appendChild(labelWrap('Тип времени', timeKind));

    // Формат времени
    const timeFmt = document.createElement('input');
    timeFmt.type = 'text';
    timeFmt.placeholder = 'Напр.: %Y-%m-%d %H:%M:%S';
    timeFmt.id = 'time_format';
    timeFmt.style.maxWidth = '320px';
    sel.appendChild(labelWrap('Формат (если выбран)', timeFmt));

    // Примеры
    const exWrap = document.createElement('div');
    exWrap.id = 'time_examples';
    exWrap.style.fontSize = '12px';
    exWrap.style.color = '#8b97a7';
    exWrap.style.marginTop = '4px';
    sel.appendChild(labelWrap('Примеры значений времени', exWrap));

    function updateTimeExamples() {
      const kind = timeKind.value;
      const examples = TIME_EXAMPLES.filter(e => {
        if (kind === 'index') return e.t.includes('Индекс');
        if (kind === 'timestamp_sec') return e.t.includes('сек)');
        if (kind === 'timestamp_ms') return e.t.includes('мс)');
        if (kind === 'datetime_format') return e.t.includes('по формату');
        if (kind === 'iso_date') return e.t.includes('ISO-формат');
        if (kind === 'rfc_2822') return e.t.includes('RFC 2822');
        if (kind === 'human_readable') return e.t.includes('Читаемый человеком');
        return false;
      });
      exWrap.innerHTML = '';
      examples.forEach(ex => {
        const div = document.createElement('div');
        div.textContent = `${ex.t}: ${ex.v}`;
        exWrap.appendChild(div);
      });
      // Плейсхолдер формата включаем только для режима форматной даты
      if (kind === 'datetime_format') {
        timeFmt.disabled = false;
        timeFmt.placeholder = 'Напр.: %Y-%m-%d %H:%M:%S';
      } else {
        timeFmt.disabled = true;
        timeFmt.placeholder = 'Не требуется для выбранного типа';
      }
    }
    timeKind.addEventListener('change', updateTimeExamples);
    updateTimeExamples();
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
    const time = {
      column: document.getElementById('time_column')?.value || null,
      kind: document.getElementById('time_kind')?.value || 'index',
      format: document.getElementById('time_format')?.value || null,
    };
    const res = await fetch(`/project/${projectId}/select`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({target, features, time })});
    const data = await res.json();
    tableData = [];
    for (let i=0 ; i < 5; i++) {
      tableData.push(data.data.records[i]);
    }

    if(data.data){
      renderTable('seleted-table', data.data.columns, tableData);
      drawPlot('plot', target, features, data.data, data.time);
      setCurrentSnap({ sample: data.data, selection: { target, features }, time: data.time });
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
  function drawPlot(plotId, target, features, data, timeMeta) {
    const el = document.getElementById(plotId);
    const cols = data.columns;
    const rows = data.records;
    let x = Array.from({ length: rows.length }, (_, i) => i);
    // Если в сэмпле есть временная колонка — используем её
    if (timeMeta && timeMeta.column && cols.includes(timeMeta.column)) {
      const col = timeMeta.column;
      const fmt = timeMeta.format || '';
      if (timeMeta.kind === 'timestamp_sec') {
        x = rows.map((r) => new Date(Number(r[col]) * 1000));
      } else if (timeMeta.kind === 'timestamp_ms') {
        x = rows.map((r) => new Date(Number(r[col])));
      } else if (timeMeta.kind === 'datetime_format') {
        if (fmt) {
          x = rows.map((r) => parseByFormat(r[col], fmt) || r[col]);
        } else {
          x = rows.map((r) => parseCompactYYYYMMDDTHHMM(r[col]) || r[col]);
        }
      } else if (timeMeta.kind === 'iso_date' || timeMeta.kind === 'rfc_2822') {
        x = rows.map((r) => new Date(r[col]));
      } else if (timeMeta.kind === 'human_readable') {
        x = rows.map((r) => r[col]);
      }
    }
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
    // Очистка предыдущего графика и отрисовка заново
    try { Plotly.purge(el); } catch(_) {}
    Plotly.newPlot(el, traces, {
      paper_bgcolor: '#111418',
      plot_bgcolor: '#111418',
      font: { color: '#e6e6e6' },
    });
  }

  // Обновленная функция прорисовки прогноза
  function drawForecast(target, prediction, xAxes) {
    const src = document.getElementById('pp_plot');
    const existing = src && src.data && src.data[0] ? src.data[0] : null;
    let baseX = [], baseY = [];
    if (existing) {
      baseX = existing.x;
      baseY = existing.y;
    }

    // Формируем оси X для будущего периода прогнозирования
    const xFuture = xAxes && xAxes.future ? xAxes.future : Array.from({ length: prediction.length }, (_, i) => baseX.length + i);

    // Данные текущего временного ряда
    const trace1 = { x: xAxes && xAxes.base ? xAxes.base : baseX, y: baseY, name: target, mode: 'lines' };

    // Прогнозируемые значения
    const trace2 = { x: xFuture, y: prediction, name: 'Прогноз', mode: 'lines' };

    // Объединяем данные в одну структуру
    const historicalData = trace1.y.map((_, idx) => ({ x: trace1.x[idx], y: trace1.y[idx] }));
    const forecastData = trace2.y.map((_, idx) => ({ x: trace2.x[idx], y: trace2.y[idx] }));

    const data = {
      columns: ['x', 'y'],
      records: [...historicalData, ...forecastData]
    };
    // Передаем массив трассировочных объектов в функцию рисования графиков
    drawPlot('forecast_plot', target, [], data, {});
  }

  // Запуск тренировки модели
  async function runTrain() {
    const target = document.getElementById('target')?.value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    appendTrainLog('Старт обучения...');
    const model = document.getElementById('mdl').value;
    const windowSize = parseInt(document.getElementById('win').value, 10);
    const horizon = parseInt(document.getElementById('hor').value, 10);
    const epochs = parseInt(document.getElementById('ep').value, 10);
    const batchSize = parseInt(document.getElementById('bs').value, 10);
    const lr = parseFloat(document.getElementById('lr').value);
    const val = parseFloat(document.getElementById('val').value);
    const res = await fetch(`/project/${projectId}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, model, window: windowSize, horizon, epochs, batch_size: batchSize, learning_rate: lr, val_split: val }),
    });
    let data = null;
    try {
      data = await res.json();
    } catch(err){
      appendTrainLog('Ошибка парсинга ответа сервера');
      throw err;
    }
    if (!data.ok) {
      alert(data.error || 'Ошибка');
      appendTrainLog(`Ошибка: ${data.error || 'неизвестно'}`);
      return;
    }
    const info = [];
    info.push(`Обучено. Loss: ${Number(data.loss).toFixed(6)}`);
    if (typeof data.val_loss === 'number') info.push(`Val loss: ${Number(data.val_loss).toFixed(6)}`);
    if (typeof data.val_mae === 'number') info.push(`Val MAE: ${Number(data.val_mae).toFixed(6)}`);
    if (data.model_file) info.push(`Файл: ${data.model_file}`);
    if (data.continued) info.push('(дообучение)');
    document.getElementById('train_info').textContent = info.join(' | ');
    setCurrentSnap({ train: { loss: data.loss, val_loss: data.val_loss, val_mae: data.val_mae, model_file: data.model_file, x: data.x } });
    appendTrainLog(info.join(' | '));
    appendTrainLog('Обучение завершено.');

    // График кривых обучения
    try {
      const epochs = (data.loss_curve || []).map((_, i) => i + 1);
      const traces = [];
      if (Array.isArray(data.loss_curve) && data.loss_curve.length) {
        traces.push({ x: epochs, y: data.loss_curve, name: 'loss', mode: 'lines' });
      }
      if (Array.isArray(data.val_loss_curve) && data.val_loss_curve.length) {
        traces.push({ x: epochs.slice(0, data.val_loss_curve.length), y: data.val_loss_curve, name: 'val_loss', mode: 'lines' });
      }
      if (traces.length) {
        try { Plotly.purge('train_curve'); } catch(_) {}
        Plotly.newPlot('train_curve', traces, {
          paper_bgcolor: '#111418',
          plot_bgcolor: '#111418',
          font: { color: '#e6e6e6' },
        });
      }
    } catch (_) {}
  }
  async function runForecast() {
    const target = document.getElementById('target')?.value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    const steps = parseInt(document.getElementById('fc_steps').value, 10);
    const context = parseInt(document.getElementById('fc_ctx').value, 10);
    const res = await fetch(`/project/${projectId}/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, steps, context }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || 'Ошибка прогноза');
      return;
    }
    drawForecast(target, data.prediction, data.x);
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
    setCurrentSnap({ preprocess: data });
  }

  // Отрисовка результатов предварительной обработки
  function drawPP(data) {
    const rows = data.segment.records;
    const cols = data.segment.columns;
    const target = document.getElementById('target').value;
    let x = Array.from({ length: rows.length }, (_, i) => i);
    if (Array.isArray(data.x) && data.x.length === rows.length) {
      x = data.x;
    }
    const y = rows.map((r) => r[target]);
    try { Plotly.purge('pp_plot'); } catch(_) {}
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
    try { Plotly.purge('pp_curve'); } catch(_) {}
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
    currentSnap = snap;
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
      drawPlot("plot", t, f, snap.sample, snap.time);
      if (t) {
        const tgtSel = document.getElementById('target');
        if (tgtSel) {
          tgtSel.value = t;
        }
      }
      if (snap.time) {
        const tc = document.getElementById('time_column');
        const tk = document.getElementById('time_kind');
        const tf = document.getElementById('time_format');
        if (tc && snap.time.column) tc.value = snap.time.column;
        if (tk && snap.time.kind) tk.value = snap.time.kind;
        if (tf && snap.time.format) tf.value = snap.time.format;
      }
    }
    if (snap.preprocess) {
      drawPP(snap.preprocess);
    }
    if (snap.train) {
      document.getElementById('train_info').textContent = `Loss: ${Number(snap.train.loss).toFixed(6)}`;
      const target = document.getElementById('target')?.value;
      if (target) {
        drawForecast(target, snap.train.prediction, snap.train.x);
      }
    }
    updateSteps(snap);
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
    const fr = document.getElementById('forecast_run');
    if(fr){ fr.addEventListener('click', runForecast); }
    
    const ex = document.getElementById('export_pdf');
    if(ex){ ex.addEventListener('click', () => window.print()); }
  }

  document.addEventListener('DOMContentLoaded', () => {
    bind();
    restore();
  });

  function appendTrainLog(line){
    const host = document.getElementById('train_log');
    if (!host) return;
    const ts = new Date().toLocaleTimeString();
    host.textContent += `[${ts}] ${line}\n`;
  }
})();


