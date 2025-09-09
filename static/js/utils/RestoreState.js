import PlotModule from "../components/Plot.js"
import SelectionModule from "../components/Selector.js"
import DOMUtils from "./DOMUtils.js";

import renderPreview from "../components/Preview.js";
import renderTable from "../components/Table.js";
import updateSteps from "../components/Steps.js"



function setCurrentSnap(partial) {
  let currentSnap = DOMUtils.getSnapshot();
  currentSnap = Object.assign({}, currentSnap || {}, partial || {});
  updateSteps(currentSnap);
}
  
// Восстановление ранее сохранённых состояний
function restore() {
  const snap = DOMUtils.getSnapshot();
  console.log(snap);
  if (!snap) return;
  
  if (snap.preview && snap.preview.info) {
    renderPreview(snap.preview.head, snap.preview.info.column_names);
    SelectionModule.renderSelectors(snap.preview.info.column_names);
  }
  if (snap.sample) {
    let tableData = [];
    for (let i=0 ; i < 5; i++) {
      tableData.push(snap.sample.records[i]);
    }

    const features = Array.from(document.getElementsByName('feat'))
    for (let h of snap.selection.features) {
      let elem = features.find(el => el.value == h);
      elem.checked = true;
    }

    renderTable("seleted-table", snap.sample.columns, tableData);
    const sel = snap.selection || {};
    const t = sel.target;
    const f = sel.features || [];
    PlotModule.drawPlot("plot", t, f, snap.sample, snap.time);
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
    const rows = snap.preprocess.segment.records;
    const cols = snap.preprocess.segment.columns;

    // Передаем в drawPlot массив координат, название графика, список характеристик и сами данные
    PlotModule.drawPlot(
      'pp_plot',           // ID элемента для вставки графика
      snap.selection.target,              // Название целевой переменной
      [],                  // Дополнительные характеристики (если нужны)
      { columns: cols, records: rows}, // Данные таблицы
      snap.time                // Метаданные о времени 
    );

    // Дополнительно выводим график кривых изменений длительности
    PlotModule.drawPP(snap.preprocess.curve);
  }
  if (snap.train) {
    document.getElementById('train_info').textContent = `Loss: ${Number(snap.train.loss).toFixed(6)}`;
    const target = snap.selection.target;
    if (target) {
      PlotModule.drawForecast(target, snap.train.prediction, snap.train.x);
    }
  }
  updateSteps(snap);
}
  

export default {restore, setCurrentSnap};