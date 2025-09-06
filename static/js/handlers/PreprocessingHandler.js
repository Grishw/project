import drawPP from '../components/Plot.js';
  // Предварительная обработка данных
  async function runPP() {
    const target = document.getElementById('target')?.value;
    const method = document.getElementById('pp_method').value;
    if (!target) {
      alert('Сначала выберите target');
      return;
    }
    const res = await fetch(`/project/${projectId}/preprocess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, method }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert(data.error || 'Ошибка');
      return;
    }
    drawPP(data);
  }

  export default runPP;