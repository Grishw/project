import DOMUtils from "../utils/DOMUtils.js";
import renderTable from "./Table.js";
import PlotModule from "./Plot.js"
import RestoreModule from "../utils/RestoreState.js"

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
  timeFmt.value = '%Y%m%dT%H%M';
  timeFmt.placeholder = '%Y-%m-%d %H:%M:%S';
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
  

async function applySelection(){
  const target = document.getElementById('target').value;
  const features = Array.from(document.querySelectorAll('input[name="feat"]:checked')).map(i=>i.value);
  const time = {
    column: document.getElementById('time_column')?.value || null,
    kind: document.getElementById('time_kind')?.value || 'index',
    format: document.getElementById('time_format')?.value || null,
  };
  const res = await fetch(`/project/${DOMUtils.getProjectIdFromAppRoot()}/select`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({target, features, time })});
  const data = await res.json();
  let tableData = [];
  for (let i=0 ; i < 5; i++) {
    tableData.push(data.data.records[i]);
  }

  if(data.data){
    renderTable('seleted-table', data.data.columns, tableData);
    PlotModule.drawPlot('plot', target, features, data.data, data.time);
    RestoreModule.setCurrentSnap({ selection: { target, features }, time: time, sample: data.data });
  }
}

  export default { renderSelectors, applySelection };