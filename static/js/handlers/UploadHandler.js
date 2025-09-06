// Загрузка CSV файла
import renderPreview from '../components/Preview.js';
import renderSelectors from '../components/Selector.js';
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

  export default uploadCsv;