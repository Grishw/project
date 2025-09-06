import renderTable from './Table.js';
// Рендер выборочных элементов интерфейса
function renderPreview(data, column_names){
    if(data){
      renderTable('preview-table', column_names, data);
    }
  }

  export default renderPreview;