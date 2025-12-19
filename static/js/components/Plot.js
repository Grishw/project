import ParserTool from "../utils/Parsers.js"

// Отрисовка графика
function drawPlot(plotId, target, features, data, timeMeta) {
  const el = document.getElementById(plotId);
  const cols = data.columns;
  const rows = data.records;
  let x = Array.from({ length: rows.length }, (_, i) => i);
  // Если в сэмпле есть временная колонка — используем её
  if (timeMeta && timeMeta.column && cols.includes(timeMeta.column)) {
    x = ParserTool.parsTime(rows, timeMeta);
  }
  const traces = [];
  if (target && !cols.includes(target)) {
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
function drawForecast(target, prediction, context, time) {
  const src = document.getElementById('pp_plot');
  const existing = src && src.data && src.data[0] ? src.data[0] : null;

  const traces = [];
  traces.push({
    y: prediction[target], 
    x: prediction[time.column], 
    mode: 'lines+markers', 
    name: 'prediction' 
  });

  const actual_time = context[time.column].map(value => ({
    [time.column]: value
  }));

  
  traces.push({
    y: context[target], 
    x: ParserTool.parsTime(actual_time,time), 
    mode: 'lines+markers', 
    name: 'context' 
  });

  // Очистка предыдущего графика и отрисовка заново
  try { Plotly.purge('forecast_plot'); } catch(_) {}
  Plotly.newPlot('forecast_plot', traces, {
    paper_bgcolor: '#111418',
    plot_bgcolor: '#111418',
    font: { color: '#e6e6e6' },
  });
}

// Отрисовка результатов предварительной обработки
function drawPP(curve, timeMeta, rows, target) {
  const cx = curve.x || [];
  const cy = curve.y || [];
  let x = [];
  // Если в сэмпле есть временная колонка — используем её
  if (timeMeta && timeMeta.column) {
    x = ParserTool.parsTime(rows, timeMeta);
  }
  let actual_x = [];
  for(let i in cx) {
    actual_x.push(x[cx[i]]);
  };

  const traces = [];
  traces.push({
    x: actual_x, 
    y: cy, 
    mode: 'lines+markers', 
    name: 'time %delta' 
  });

  traces.push({
    x: x, 
    y: rows.map((r) => r[target]), 
    mode: 'lines+markers', 
    name: 'target' 
  });

  // Очистка предыдущего графика и отрисовка заново
  try { Plotly.purge('pp_curve'); } catch(_) {}
  Plotly.newPlot('pp_curve', traces, {
    paper_bgcolor: '#111418',
    plot_bgcolor: '#111418',
    font: { color: '#e6e6e6' },
  });
}

function drawTrainCurve(data) {
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
}

export default { drawPlot, drawForecast, drawPP, drawTrainCurve };