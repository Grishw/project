const select = (selector) => document.querySelector(selector);

const getProjectIdFromAppRoot = () => {
  const appRoot = select('#app-root');
  return appRoot ? appRoot.getAttribute('data-project-id') : '';
};

export default { select, getProjectIdFromAppRoot};