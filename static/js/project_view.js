import PlotModule from "./components/Plot.js"
import SelectionModule from "./components/Selector.js"
import DOMUtils from "./utils/DOMUtils.js";
import RestoreModule from "./utils/RestoreState.js"

import renderPreview from "./components/Preview.js";
import renderTable from "./components/Table.js";
import appendTrainLog from "./components/TrainLog.js";

(() => {
  initApp(); 
})();

function initApp() {
  // Текущее клиентское состояние (минимальный снапшот)
  let currentSnap = null;

  

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
      SelectionModule.renderSelectors(data.preview.info.column_names);
      RestoreModule.setCurrentSnap({ preview: data.preview });
    }
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
    const res = await fetch(`/project/${DOMUtils.getProjectIdFromAppRoot()}/train`, {
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
    RestoreModule.setCurrentSnap({ train: { loss: data.loss, val_loss: data.val_loss, val_mae: data.val_mae, model_file: data.model_file, x: data.x } });
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
    const res = await fetch(`/project/${DOMUtils.getProjectIdFromAppRoot()}/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, steps, context }),
    });
    const data = await res.json();
    comsole.log("predict",data);
    if (!data.ok) {
      alert(data.error || 'Ошибка прогноза');
      return;
    }
    PlotModule.drawForecast(target, data.prediction, data.x);
  }


  // Предварительная обработка данных
  async function runPP() {
    const target = document.getElementById('target')?.value;
    const method = document.getElementById('pp_method').value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    const res = await fetch(`/project/${DOMUtils.getProjectIdFromAppRoot()}/preprocess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, method }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || 'Ошибка');
      return;
    }

    const rows = data.segment.records;
    const cols = data.segment.columns;
    
    const time = {
      column: document.getElementById('time_column')?.value || null,
      kind: document.getElementById('time_kind')?.value || 'index',
      format: document.getElementById('time_format')?.value || null,
    };

    const time_col = time.column


    // Передаем в drawPlot массив координат, название графика, список характеристик и сами данные
    PlotModule.drawPlot(
      'pp_plot',           // ID элемента для вставки графика
      target,              // Название целевой переменной
      [],                  // Дополнительные характеристики (если нужны)
      { columns: cols, records: rows}, // Данные таблицы
      time                 // Метаданные о времени 
    );

    // Дополнительно выводим график кривых изменений длительности
    PlotModule.drawPP(data.curve);
    RestoreModule.setCurrentSnap({ preprocess: data });
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
    RestoreModule.restore();
  });
};


