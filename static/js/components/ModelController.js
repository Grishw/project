
async function setActiveModel(modelId) {
  await fetch(`/project/${PROJECT_ID}/models/activate`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ model_id: modelId })
  });
  alert(`Активная модель: ${modelId}`);
}

async function loadModels() {
  const res = await fetch(`/project/${PROJECT_ID}/models`);
  const models = await res.json();

  const tbody = document.querySelector('#models_table tbody');
  const select = document.querySelector('#active_model');

  tbody.innerHTML = '';
  select.innerHTML = '';

  models.forEach(m => {
    // таблица
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${m.id}</td>
      <td>${m.type}</td>
      <td>${m.loss.toFixed(4)}</td>
      <td>${m.val_loss?.toFixed(4) ?? '-'}</td>
      <td>${m.created_at}</td>
      <td>
        <button class="btn" data-id="${m.id}">Активировать</button>
      </td>
    `;
    tr.querySelector('button').onclick = () => setActiveModel(m.id);
    tbody.appendChild(tr);

    // селект
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = `${m.id} (${m.type})`;
    select.appendChild(opt);
  });
}




export default { loadModels, setActiveModel};