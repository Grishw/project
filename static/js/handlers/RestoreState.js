import renderPreview from '../components/Preview.js';
import renderSelectors from '../components/Selector.js';
import renderTable from '../components/Table.js';
import drawPlotfrom from '../components/Plot.js';
import drawForecast from '../components/Plot.js';
import drawPP from '../components/Plot.js';


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

  

  // Восстановление ранее сохранённых состояний
  function restore() {
    const snap = getSnapshot();
    if (!snap) return;
    if (snap.preview && snap.preview.info) {
      renderPreview(snap.preview.head, snap.preview.info.column_names);
      renderSelectors(snap.preview.info.column_names);
    }
    if (snap.sample) {
      renderTable(snap.sample.columns, snap.sample.records);
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

  export default restore;