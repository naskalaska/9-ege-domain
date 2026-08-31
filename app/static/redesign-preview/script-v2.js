const stage = document.querySelector('.module-stage');
const modules = [...document.querySelectorAll('[data-module]')];
const toast = document.querySelector('.toast');
const glow = document.querySelector('.cursor-glow');
const views = [...document.querySelectorAll('[data-view]')];

function closeModules(except = null) {
  modules.forEach((module) => {
    if (module === except) return;
    module.classList.remove('open');
    module.setAttribute('aria-expanded', 'false');
    module.querySelector('.module-detail').setAttribute('aria-hidden', 'true');
  });
  if (!except) stage.classList.remove('is-active');
}

function toggleModule(module) {
  const shouldOpen = !module.classList.contains('open');
  closeModules(module);
  module.classList.toggle('open', shouldOpen);
  module.setAttribute('aria-expanded', String(shouldOpen));
  module.querySelector('.module-detail').setAttribute('aria-hidden', String(!shouldOpen));
  stage.classList.toggle('is-active', shouldOpen);
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

function showView(name, updateHash = true) {
  const target = views.find((view) => view.dataset.view === name) || views[0];
  views.forEach((view) => view.classList.toggle('is-visible', view === target));
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.classList.toggle('active', link.dataset.viewTarget === target.dataset.view);
  });
  closeModules();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (updateHash) history.replaceState(null, '', `#${target.dataset.view}`);
}

document.querySelectorAll('[data-view-target]').forEach((control) => {
  control.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    showView(control.dataset.viewTarget);
  });
});

function bindFilter(buttonSelector, cardSelector, categoryAttribute) {
  document.querySelectorAll(buttonSelector).forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll(buttonSelector).forEach((item) => item.classList.toggle('active', item === button));
      const filter = button.dataset.filter || button.dataset.shopFilter;
      document.querySelectorAll(cardSelector).forEach((card) => {
        const categories = card.getAttribute(categoryAttribute)?.split(' ') || [];
        card.classList.toggle('filtered-out', filter !== 'all' && !categories.includes(filter));
      });
    });
  });
}

bindFilter('[data-filter]', '.game-grid > article', 'data-category');
bindFilter('[data-shop-filter]', '.shop-grid > article', 'data-shop-category');

document.querySelectorAll('[data-placeholder]').forEach((button) => {
  button.addEventListener('click', () => showToast('Это демонстрационная заглушка — действие появится в рабочей версии.'));
});

document.querySelectorAll('[data-demo-form]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    showToast('Форма показана только для оценки дизайна. Данные не отправляются.');
  });
});

const roleCards = [...document.querySelectorAll('[data-role-card]')];
const teacherCodeField = document.querySelector('[data-teacher-code]');

function selectRole(role) {
  roleCards.forEach((card) => {
    const selected = card.dataset.roleCard === role;
    card.classList.toggle('selected', selected);
    card.querySelector('input').checked = selected;
  });
  teacherCodeField?.classList.toggle('is-hidden', role === 'teacher');
}

roleCards.forEach((card) => {
  card.addEventListener('click', () => selectRole(card.dataset.roleCard));
  card.querySelector('input').addEventListener('change', () => selectRole(card.dataset.roleCard));
});

document.addEventListener('click', (event) => {
  if (!event.target.closest('[data-module]')) closeModules();
});

document.addEventListener('pointermove', (event) => {
  glow.style.left = `${event.clientX}px`;
  glow.style.top = `${event.clientY}px`;
});

const initialView = location.hash.replace('#', '');
if (views.some((view) => view.dataset.view === initialView)) showView(initialView, false);
