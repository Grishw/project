const select = (selector) => document.querySelector(selector);

const getProjectIdFromAppRoot = () => {
  const appRoot = select('#app-root');
  return appRoot ? appRoot.getAttribute('data-project-id') : '';
};

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

export default {getProjectIdFromAppRoot, getSnapshot};