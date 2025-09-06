import drawForecast from '../components/Plot.js';

  // Запуск тренировки модели
  async function runTrain() {
    const target = document.getElementById('target')?.value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    const model = document.getElementById('mdl').value;
    const windowSize = parseInt(document.getElementById('win').value, 10);
    const horizon = parseInt(document.getElementById('hor').value, 10);
    const epochs = parseInt(document.getElementById('ep').value, 10);
    const res = await fetch(`/project/${projectId}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, model, window: windowSize, horizon, epochs }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || 'Ошибка');
      return;
    }
    document.getElementById('train_info').textContent = `Loss: ${data.loss.toFixed(6)}`;
    drawForecast(target, data.prediction);
  }

  export default runTrain;