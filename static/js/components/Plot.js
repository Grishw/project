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
  drawPlot('forecast_plot', target, ['x', 'y'], data, {});
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

export default { drawPlot, drawForecast, drawPP };