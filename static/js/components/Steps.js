
function updateSteps(snap) {
    try {
      const list = document.querySelectorAll('.steps .step');
      if (!list || !list.length) return;
      const hasPreview = !!(snap && snap.preview && snap.preview.info);
      const hasSample = !!(snap && snap.sample && snap.sample.columns);
      const hasPP = !!(snap && snap.preprocess && snap.preprocess.segment);
      const hasTrain = !!(snap && snap.train && (snap.train.loss !== undefined));
  
      // Индексы шагов в разметке:
      // 0: Загрузка данных
      // 1: Информация о данных
      // 2: Предподготовка
      // 3: Выбор модели
      // 4: Обучение и прогноз
      // 5: Экспорт PDF
  
      const done = [
        hasPreview,       // 0
        hasPreview || hasSample, // 1 — после загрузки уже есть информация
        hasPP,            // 2
        hasSample || hasPP || hasTrain, // 3 — модель можно выбирать после выборки/PP
        hasTrain,         // 4
        false,            // 5 — помечаем вручную при экспорте
      ];
  
      // Сброс классов
      list.forEach(li => {
        li.classList.remove('step-done');
        li.classList.remove('step-active');
      });
  
      // Проставить done
      done.forEach((isDone, i) => {
        if (list[i] && isDone) list[i].classList.add('step-done');
      });
  
      // Активный — первый не завершенный
      const activeIdx = done.findIndex(v => !v);
      if (activeIdx >= 0 && list[activeIdx]) {
        list[activeIdx].classList.add('step-active');
      }
    } catch (_) {
      // без падения UI
    }
}

export default updateSteps;