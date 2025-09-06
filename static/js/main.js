// Импортируем компоненты и обрабатываем события
import uploadCsv from './handlers/UploadHandler.js';
import runTrain from './handlers/TrainHandler.js';
import runPP from './handlers/PreprocessingHandler.js';
import restore from './handlers/RestoreState.js';
import getProjectIdFromAppRoot from './utils/DOMUtils.js';

const projectId = getProjectIdFromAppRoot();

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('upload-form');
    if(form) form.addEventListener('submit', uploadCsv);

    const dz = document.getElementById('dropzone');
    if(dz){ 
        dz.addEventListener('drop', handleDrop); 
        dz.addEventListener('dragover', handleDrag); }

    const pp = document.getElementById('pp_run');
    if(pp){ pp.addEventListener('click', runPP); }

    const tr = document.getElementById('train_run');
    if(tr){ tr.addEventListener('click', runTrain); }

    const ex = document.getElementById('export_pdf');
    if(ex){ ex.addEventListener('click', () => window.print()); }

    restore(); // Восстанавливаем состояние страницы
});