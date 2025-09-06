// import * as Plotly from 'https://cdn.plot.ly/plotly-latest.min.js';

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

  export default { drawPlot, drawForecast, drawPP };