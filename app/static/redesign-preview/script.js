const modules = [...document.querySelectorAll('[data-module]')];
const toast = document.querySelector('.toast');
const glow = document.querySelector('.cursor-glow');

function closeModules(except = null) {
  modules.forEach((module) => {
    if (module === except) return;
    module.classList.remove('open');
    module.setAttribute('aria-expanded', 'false');
    module.querySelector('.module-detail').setAttribute('aria-hidden', 'true');
  });
}

function toggleModule(module) {
  const shouldOpen = !module.classList.contains('open');
  closeModules(module);
  module.classList.toggle('open', shouldOpen);
  module.setAttribute('aria-expanded', String(shouldOpen));
  module.querySelector('.module-detail').setAttribute('aria-hidden', String(!shouldOpen));
}

modules.forEach((module) => {
  module.addEventListener('click', (event) => {
    if (event.target.closest('a, .close-detail')) return;
    toggleModule(module);
  });
  module.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleModule(module);
    }
    if (event.key === 'Escape') closeModules();
  });
  module.querySelector('.close-detail').addEventListener('click', (event) => {
    event.stopPropagation();
    closeModules();
    module.focus();
  });
});

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

document.querySelectorAll('[data-demo-link]').forEach((link) => {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    showToast('В прототипе переход отключён — здесь будет ссылка на раздел.');
  });
});

document.querySelectorAll('[data-demo-message]').forEach((button) => {
  button.addEventListener('click', () => showToast(button.dataset.demoMessage));
});

document.addEventListener('click', (event) => {
  if (!event.target.closest('[data-module]')) closeModules();
});

document.addEventListener('pointermove', (event) => {
  glow.style.left = `${event.clientX}px`;
  glow.style.top = `${event.clientY}px`;
});
