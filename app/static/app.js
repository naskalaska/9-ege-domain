const state = {
  token: localStorage.getItem("ege_token"),
  user: null,
  bootstrap: null,
  mode: "rule",
  selectedCategory: null,
  selectedCategories: [],
  selectedRuleIds: [],
  ruleSelectionTouched: false,
  currentSession: null,
  answers: {},
  startedAt: null,
  questionCount: 10,
  manualInput: false,
  errorTrainingMode: "cards",
  currentQuestionIndex: 0,
  liveResults: [],
  currentActivity: null,
  currentMiniGame: null,
};

const fallbackTeacherCode = "T-DDC378";

const activityMeta = {
  ege9: {
    title: "ЕГЭ. Задание 9",
    shortTitle: "Задание 9",
    description: "Орфография: корни, гласные, строки с общей буквой.",
    mark: "9",
  },
  ege10: {
    title: "ЕГЭ. Задание 10",
    shortTitle: "Задание 10",
    description: "Приставки, Ь/Ъ, И/Ы и другие орфограммы.",
    mark: "10",
  },
  ege11: {
    title: "ЕГЭ. Задание 11",
    shortTitle: "Задание 11",
    description: "Правописание суффиксов слов разных частей речи.",
    mark: "11",
  },
  "html-games": {
    title: "Игры",
    shortTitle: "Игры",
    description: "Небольшие HTML-игры для тренировки орфографии.",
    mark: "GAME",
  },
};

const miniGames = [
  {
    slug: "suffixes-nouns",
    title: "Суффиксы существительных",
    description: "Поймайте пушинки и выберите правильную букву в словах с суффиксами.",
    button: "Играть",
    path: "/html-games/suffixes-nouns/index.html",
  },
  {
    slug: "homogeneous-members-magic",
    title: "Магия однородных членов предложения",
    description: "Раскройте грамматический фокус: выбирайте свитки с правильными цифрами для запятых.",
    button: "Играть",
    path: "/html-games/homogeneous-members-magic/index.html",
  },
  {
    slug: "berry-season-ik-ek",
    title: "Ягодный сезон: ИК-ЕК",
    description: "Собирайте слова в корзинки Е и И, тренируя суффиксы -ек- и -ик-.",
    button: "Играть",
    path: "/html-games/berry-season-ik-ek/index.html",
  },
];

const modes = {
  rule: {
    title: "Правило",
    hint: "Большая группа и подвыбор внутри нее",
    eyebrow: "точечная отработка",
  },
  word_letter: {
    title: "Слово - буква",
    hint: "Одно слово на экране, ввод буквы и мгновенная проверка",
    eyebrow: "быстрая отработка",
  },
  mix: {
    title: "Микс",
    hint: "Разные правила в формате слово = буква",
    eyebrow: "перемешанные орфограммы",
  },
  line: {
    title: "Строка",
    hint: "Ряд с одной и той же буквой",
    eyebrow: "формат задания 9",
  },
  errors: {
    title: "Копилка ошибок",
    hint: "Слова, где уже были промахи",
    eyebrow: "личное повторение",
  },
};

const view = document.querySelector("#view");
const topActions = document.querySelector("#topActions");

function activityApi(path) {
  return state.currentActivity ? `/api/apps/${state.currentActivity}${path}` : path;
}

function legalLinks(className = "legal-links") {
  return `
    <nav class="${className}">
      <a href="/privacy">Политика обработки персональных данных</a>
      <a href="/consent">Согласие на обработку персональных данных</a>
      <a href="/terms">Пользовательское соглашение</a>
    </nav>
  `;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  return fetch(path, { ...options, headers }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Ошибка запроса");
    return data;
  });
}

async function downloadRequest(path, filename, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ error: "Ошибка скачивания" }));
    throw new Error(data.error || "Ошибка скачивания");
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function pct(correct, total) {
  if (!total) return "0%";
  return `${Math.round((correct / total) * 100)}%`;
}

function ruleCategories() {
  return Object.keys(state.bootstrap.rules);
}

function selectedCategorySet() {
  return new Set(state.selectedCategories || []);
}

function selectedRules() {
  const categories = state.selectedCategories?.length ? state.selectedCategories : [state.selectedCategory].filter(Boolean);
  return categories.flatMap((category) => state.bootstrap.rules[category] || []);
}

function selectedRuleSet() {
  return new Set(state.selectedRuleIds);
}

function ensureRuleSelection() {
  const categories = ruleCategories();
  state.selectedCategories = (state.selectedCategories || []).filter((category) => state.bootstrap.rules[category]);
  if (!state.selectedCategories.length && state.selectedCategory && state.bootstrap.rules[state.selectedCategory]) {
    state.selectedCategories = [state.selectedCategory];
  }
  if (!state.selectedCategories.length && categories.length) {
    state.selectedCategories = [categories[0]];
  }
  state.selectedCategory = state.selectedCategories[0] || null;
  const rules = selectedRules();
  const available = new Set(rules.map((rule) => rule.rule_id));
  state.selectedRuleIds = state.selectedRuleIds.filter((ruleId) => available.has(ruleId));
  if (!state.ruleSelectionTouched && !state.selectedRuleIds.length && rules.length) {
    state.selectedRuleIds = rules.map((rule) => rule.rule_id);
  }
}

function ruleIdsForCategory(category) {
  return (state.bootstrap.rules[category] || []).map((rule) => rule.rule_id);
}

function toggleRuleCategory(category) {
  state.ruleSelectionTouched = true;
  const categories = selectedCategorySet();
  const selected = selectedRuleSet();
  const ids = ruleIdsForCategory(category);

  if (categories.has(category)) {
    categories.delete(category);
    ids.forEach((ruleId) => selected.delete(ruleId));
  } else {
    categories.add(category);
    ids.forEach((ruleId) => selected.add(ruleId));
  }

  state.selectedCategories = [...categories].filter((item) => state.bootstrap.rules[item]);
  state.selectedCategory = state.selectedCategories[0] || null;
  state.selectedRuleIds = [...selected];
  ensureRuleSelection();
}

function updateRuleSelectorSummary(root) {
  const rules = selectedRules();
  const selected = selectedRuleSet();
  const visibleSelected = rules.filter((rule) => selected.has(rule.rule_id));
  const selectedCount = visibleSelected.reduce((sum, rule) => sum + rule.count, 0);
  const allRules = root.querySelector("#allRules");
  const selectedWordCount = root.querySelector("[data-selected-word-count]");

  if (allRules) {
    allRules.checked = rules.length > 0 && visibleSelected.length === rules.length;
    allRules.indeterminate = visibleSelected.length > 0 && visibleSelected.length < rules.length;
  }
  if (selectedWordCount) selectedWordCount.textContent = selectedCount;
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      // Fall through to the textarea fallback below.
    }
  }

  const input = document.createElement("textarea");
  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.left = "-9999px";
  input.style.top = "0";
  document.body.append(input);
  input.focus();
  input.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } finally {
    input.remove();
  }
  return copied;
}

function renderTopActions() {
  topActions.innerHTML = "";
  if (!state.user) return;
  if (state.currentActivity) {
    const catalog = document.createElement("button");
    catalog.className = "ghost-button";
    catalog.textContent = "Каталог";
    catalog.addEventListener("click", () => {
      state.currentActivity = null;
      history.pushState(null, "", "/");
      renderDashboard();
    });
    topActions.append(catalog);
  }
  const role = document.createElement("span");
  role.className = "muted";
  const roleNames = { admin: "администратор", teacher: "учитель", student: "ученик" };
  role.textContent = `${state.user.display_name} · ${roleNames[state.user.role] || state.user.role}`;
  const logout = document.createElement("button");
  logout.className = "ghost-button";
  logout.textContent = "Выйти";
  logout.addEventListener("click", async () => {
    await api("/api/logout", { method: "POST", body: "{}" }).catch(() => null);
    localStorage.removeItem("ege_token");
    state.token = null;
    state.user = null;
    renderLogin();
  });
  topActions.append(role);
  if (state.user.role === "admin") {
    const admin = document.createElement("button");
    admin.className = "ghost-button";
    admin.textContent = "Админ";
    admin.addEventListener("click", showAdmin);
    topActions.append(admin);
  }
  topActions.append(logout);
}

function renderLogin() {
  renderTopActions();
  const template = document.querySelector("#loginTemplate").content.cloneNode(true);
  view.replaceChildren(template);
  document.querySelector("#loginForm").insertAdjacentHTML("afterend", `
    <form class="login-panel register-panel" id="registerForm">
      <h2>Регистрация</h2>
      <div class="role-choice" aria-label="Роль">
        <label>
          <input type="radio" name="role" value="student" checked />
          <span>Ученик</span>
        </label>
        <label>
          <input type="radio" name="role" value="teacher" />
          <span>Учитель</span>
        </label>
      </div>
      <label>
        Имя
        <input name="display_name" autocomplete="name" required />
      </label>
      <label>
        Email
        <input name="email" type="email" autocomplete="email" required />
      </label>
      <label>
        Пароль
        <input name="password" type="password" autocomplete="new-password" required />
      </label>
      <label id="teacherCodeLabel">
        Код учителя
        <input name="teacher_code" placeholder="например, TEACHER-2026" />
      </label>
      <button class="secondary-button" type="submit">Создать аккаунт</button>
      <p class="error" id="registerError"></p>
    </form>
  `);
  document.querySelector("#teacherCodeLabel").insertAdjacentHTML("afterend", `
    <label class="consent-check">
      <input name="consent_accepted" type="checkbox" required />
      <span>
      <a href="/privacy">Политика обработки персональных данных</a>
      <a href="/consent">Согласие на обработку персональных данных</a>
      <a href="/terms">Пользовательское соглашение</a>
      </span>
    </label>
  `);
  view.insertAdjacentHTML("beforeend", legalLinks("legal-links login-legal"));
  document.querySelector("#loginForm button").insertAdjacentHTML(
    "afterend",
    `<button class="ghost-button" id="forgotPasswordLink" type="button">Забыли пароль?</button>`
  );
  document.querySelector("#forgotPasswordLink").addEventListener("click", () => {
    history.pushState(null, "", "/forgot-password");
    renderForgotPassword();
  });
  document.querySelector("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const error = document.querySelector("#loginError");
    error.textContent = "";
    try {
      const data = await api("/api/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("username"),
          password: form.get("password"),
        }),
      });
      state.token = data.token;
      state.user = data.user;
      localStorage.setItem("ege_token", data.token);
      const target = activityFromPath();
      if (userNeedsConsent()) {
        await renderConsentGate();
      } else if (target) {
        await loadActivity(target, false);
      } else {
        await loadBootstrap();
        renderDashboard();
      }
    } catch (err) {
      error.textContent = err.message;
    }
  });
  const codeLabel = document.querySelector("#teacherCodeLabel");
  document.querySelectorAll("input[name='role']").forEach((input) => {
    input.addEventListener("change", () => {
      const role = document.querySelector("input[name='role']:checked").value;
      codeLabel.classList.toggle("hidden", role === "teacher");
    });
  });
  document.querySelector("#registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const error = document.querySelector("#registerError");
    const role = String(form.get("role") || "student");
    let teacherCode = String(form.get("teacher_code") || "").trim();
    error.textContent = "";
    if (role === "student" && !teacherCode) {
      const ok = confirm("Вы уверены, что вам не нужен код учителя? Ваш педагог не сможет отслеживать прогресс.");
      if (!ok) return;
      teacherCode = fallbackTeacherCode;
    }
    try {
      const data = await api("/api/register", {
        method: "POST",
        body: JSON.stringify({
          display_name: form.get("display_name"),
          email: form.get("email"),
          password: form.get("password"),
          role,
          teacher_code: teacherCode,
          consent_accepted: form.get("consent_accepted") === "on",
        }),
      });
      state.token = data.token;
      state.user = data.user;
      localStorage.setItem("ege_token", data.token);
      const target = activityFromPath();
      if (userNeedsConsent()) {
        await renderConsentGate();
      } else if (target) {
        await loadActivity(target, false);
      } else {
        await loadBootstrap();
        renderDashboard();
      }
    } catch (err) {
      error.textContent = err.message;
    }
  });
}

function renderForgotPassword() {
  renderTopActions();
  view.innerHTML = `
    <section class="auth-page">
      <form class="login-panel auth-panel" id="forgotPasswordForm">
        <h2>Восстановление пароля</h2>
        <label>
          Email
          <input name="email" type="email" autocomplete="email" required />
        </label>
        <button class="primary-button" type="submit">Отправить ссылку</button>
        <button class="ghost-button" id="backToLogin" type="button">Назад ко входу</button>
        <p class="muted" id="forgotPasswordMessage"></p>
        <p class="error" id="forgotPasswordError"></p>
      </form>
    </section>
  `;
  view.querySelector("#backToLogin").addEventListener("click", () => {
    history.pushState(null, "", "/login");
    renderLogin();
  });
  view.querySelector("#forgotPasswordForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const message = view.querySelector("#forgotPasswordMessage");
    const error = view.querySelector("#forgotPasswordError");
    message.textContent = "";
    error.textContent = "";
    try {
      const data = await api("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email") }),
      });
      message.textContent = data.message;
    } catch (err) {
      error.textContent = err.message;
    }
  });
}

function renderResetPassword() {
  renderTopActions();
  const token = new URLSearchParams(window.location.search).get("token") || "";
  view.innerHTML = `
    <section class="auth-page">
      <form class="login-panel auth-panel" id="resetPasswordForm">
        <h2>Новый пароль</h2>
        <label>
          Новый пароль
          <input name="password" type="password" autocomplete="new-password" />
        </label>
        <label>
          Повтор пароля
          <input name="password_repeat" type="password" autocomplete="new-password" />
        </label>
        <button class="primary-button" type="submit">Сохранить пароль</button>
        <p class="muted" id="resetPasswordMessage"></p>
        <p class="error" id="resetPasswordError"></p>
      </form>
    </section>
  `;
  view.querySelector("#resetPasswordForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") || "");
    const repeat = String(form.get("password_repeat") || "");
    const message = view.querySelector("#resetPasswordMessage");
    const error = view.querySelector("#resetPasswordError");
    message.textContent = "";
    error.textContent = "";
    if (password !== repeat) {
      error.textContent = "Пароли не совпадают.";
      return;
    }
    try {
      await api("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      message.textContent = "Пароль изменен. Теперь можно войти.";
      setTimeout(() => {
        history.pushState(null, "", "/login");
        renderLogin();
      }, 1200);
    } catch (err) {
      error.textContent = err.message;
    }
  });
}

async function renderDocumentPage(type) {
  renderTopActions();
  const endpoints = {
    privacy: "/api/documents/privacy",
    consent: "/api/documents/consent",
    terms: "/api/documents/terms",
  };
  const endpoint = endpoints[type] || endpoints.privacy;
  view.innerHTML = `
    <section class="document-page">
      <article class="document-panel">
        <p class="muted">Загрузка документа...</p>
      </article>
    </section>
  `;
  const panel = view.querySelector(".document-panel");
  try {
    const documentData = await api(endpoint);
    panel.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="eyebrow">версия ${documentData.version}</p>
          <h2>${documentData.title}</h2>
        </div>
        <button class="secondary-button" id="backFromDocument" type="button">Назад</button>
      </div>
      <p class="muted">Дата редакции: ${new Date(documentData.updated_at).toLocaleDateString()}</p>
      <div class="document-content">
        ${String(documentData.content || "").split("\n").map((line) => line.trim() ? `<p>${line}</p>` : "").join("")}
      </div>
      <p class="muted">Текст является шаблоном и должен быть заменен на финальный юридически выверенный текст перед запуском регистрации реальных пользователей.</p>
      ${legalLinks()}
    `;
    panel.querySelector("#backFromDocument").addEventListener("click", () => {
      const referrer = document.referrer ? new URL(document.referrer, window.location.origin) : null;
      if (referrer && referrer.origin === window.location.origin) {
        history.back();
      } else {
        window.location.href = "/login";
      }
    });
  } catch (err) {
    panel.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

async function renderConsentGate() {
  renderTopActions();
  const data = await api("/api/me/consents").catch(() => ({
    required: [{ document_version: "2026-06-02", privacy_policy_version: "2026-06-02" }],
  }));
  const required = data.required?.[0] || {};
  view.innerHTML = `
    <section class="auth-page">
      <form class="login-panel consent-panel" id="requiredConsentForm">
        <p class="eyebrow">персональные данные</p>
        <h2>Перед началом работы ознакомьтесь с документами</h2>
        <p class="muted">Текущая версия согласия: ${required.document_version || ""}. Версия политики: ${required.privacy_policy_version || ""}.</p>
        ${legalLinks("legal-links consent-doc-links")}
        <label class="consent-check">
          <input name="consent_accepted" type="checkbox" />
          <span>
            Я ознакомился/ознакомилась с Политикой обработки персональных данных и даю согласие на обработку персональных данных.
          </span>
        </label>
        <button class="primary-button" type="submit">Продолжить</button>
        <p class="error" id="requiredConsentError"></p>
      </form>
    </section>
  `;
  view.querySelector("#requiredConsentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const error = view.querySelector("#requiredConsentError");
    error.textContent = "";
    if (form.get("consent_accepted") !== "on") {
      error.textContent = "Для продолжения необходимо принять документы.";
      return;
    }
    try {
      const status = await api("/api/me/consents", { method: "POST", body: JSON.stringify({ consent_type: "personal_data_processing" }) });
      state.user = { ...state.user, has_required_consents: status.has_required_consents };
      renderDashboard();
    } catch (err) {
      error.textContent = err.message;
    }
  });
}

function userNeedsConsent() {
  return state.user && !state.user.has_required_consents;
}

async function loadBootstrap() {
  state.bootstrap = await api("/api/bootstrap");
}

async function loadActivity(slug, updateUrl = true) {
  if (slug === "html-games") {
    state.currentActivity = slug;
    state.currentMiniGame = null;
    if (updateUrl) history.pushState(null, "", "/apps/mini");
    renderMiniActivity();
    return;
  }
  state.currentActivity = slug;
  state.bootstrap = await api(`/api/apps/${slug}/bootstrap`);
  state.mode = "rule";
  state.selectedCategory = null;
  state.selectedCategories = [];
  state.selectedRuleIds = [];
  state.ruleSelectionTouched = false;
  state.currentSession = null;
  state.answers = {};
  ensureRuleSelection();
  if (updateUrl) history.pushState(null, "", `/apps/${slug}`);
  renderDashboard();
}

function activityFromPath() {
  const path = window.location.pathname;
  if (path === "/apps/ege9") return "ege9";
  if (path === "/apps/ege10") return "ege10";
  if (path === "/apps/ege11") return "ege11";
  if (path === "/apps/mini" || path.startsWith("/apps/mini/")) return "html-games";
  return null;
}

function miniGameFromPath() {
  const match = window.location.pathname.match(/^\/apps\/mini\/games\/([^/]+)$/);
  return match ? match[1] : null;
}

async function restoreSession() {
  await loadBootstrap();
  if (window.location.pathname === "/privacy") {
    await renderDocumentPage("privacy");
    return;
  }
  if (window.location.pathname === "/consent") {
    await renderDocumentPage("consent");
    return;
  }
  if (window.location.pathname === "/terms") {
    await renderDocumentPage("terms");
    return;
  }
  if (!state.token) {
    if (window.location.pathname === "/forgot-password") {
      renderForgotPassword();
      return;
    }
    if (window.location.pathname === "/reset-password") {
      renderResetPassword();
      return;
    }
    renderLogin();
    return;
  }
  const data = await api("/api/me").catch(() => ({ user: null }));
  state.user = data.user;
  if (!state.user) {
    localStorage.removeItem("ege_token");
    state.token = null;
    renderLogin();
    return;
  }
  if (userNeedsConsent()) {
    await renderConsentGate();
    return;
  }
  const pathActivity = activityFromPath();
  if (pathActivity) {
    await loadActivity(pathActivity, false);
    return;
  }
  renderDashboard();
}

function renderDashboard() {
  renderTopActions();
  if (state.user.role === "admin") {
    renderAdminDashboard();
    return;
  }
  if (!state.currentActivity) {
    renderCatalog();
    return;
  }
  ensureRuleSelection();
  const template = document.querySelector("#dashboardTemplate").content.cloneNode(true);
  view.replaceChildren(template);
  renderSidebar();
  renderMode();
  document.querySelector("#progressButton").addEventListener("click", showProgress);
  if (state.user.role === "teacher") {
    renderTeacherDashboardPreview();
  }
}

function renderCatalog() {
  renderTopActions();
  const activities = state.bootstrap.activities || Object.entries(activityMeta).map(([slug, meta]) => ({ slug, ...meta }));
  const cards = activities.map((activity) => {
    const meta = activityMeta[activity.slug] || activity;
    return `
      <article class="activity-card">
        <div class="activity-mark">${meta.mark || "A"}</div>
        <div>
          <p class="eyebrow">${activity.kind === "mini" ? "мини-приложение" : "учебный модуль"}</p>
          <h2>${activity.title || meta.title}</h2>
          <p>${activity.description || meta.description}</p>
        </div>
        <button class="primary-button open-activity" data-activity="${activity.slug}" type="button">
          ${activity.button || "Открыть"}
        </button>
      </article>
    `;
  }).join("");
  view.innerHTML = `
    <section class="catalog-page">
      <div class="catalog-head">
        <div>
          <p class="eyebrow">каталог активностей</p>
          <h2>Выберите тренажер</h2>
        </div>
        <div class="catalog-user">
          <strong>${state.user.display_name}</strong>
          <span class="muted">${state.user.role}</span>
        </div>
      </div>
      <div class="activity-grid">${cards}</div>
      ${state.user.role === "teacher" ? `<div class="catalog-actions"><button class="secondary-button" id="teacherCabinet" type="button">Кабинет учителя</button></div>` : ""}
    </section>
  `;
  view.querySelector(".catalog-page").insertAdjacentHTML("beforeend", legalLinks("legal-links catalog-legal"));
  view.querySelectorAll(".open-activity").forEach((button) => {
    button.addEventListener("click", () => loadActivity(button.dataset.activity));
  });
  view.querySelector("#teacherCabinet")?.addEventListener("click", async () => {
    await loadActivity("ege9");
    showProgress();
  });
}

function renderMiniActivity() {
  renderTopActions();
  const gameSlug = state.currentMiniGame || miniGameFromPath();
  const selectedGame = miniGames.find((game) => game.slug === gameSlug);
  const gameCards = miniGames.map((game) => `
    <article class="mini-game-card">
      <div>
        <p class="eyebrow">мини-игра</p>
        <h3>${game.title}</h3>
        <p>${game.description}</p>
      </div>
      <button class="primary-button open-mini-game" data-game="${game.slug}" type="button">${game.button}</button>
    </article>
  `).join("");
  const teacherBuilder = !selectedGame && state.user.role === "teacher" ? `
    <section class="game-builder" id="gameBuilder">
      <div class="panel-head">
        <div>
          <p class="eyebrow">для учителя</p>
          <h3>Создать HTML-игру</h3>
        </div>
      </div>
      <div class="builder-grid">
        <form class="builder-panel" id="baseGameForm">
          <h4>Из моих баз</h4>
          <label>Механика
            <select name="mechanic">
              <option value="fluffs">Пушинки - рекомендуется для орфографии</option>
              <option value="focus" disabled>Фокус - скоро</option>
            </select>
          </label>
          <label>База
            <select name="source" id="gameSourceSelect"></select>
          </label>
          <div class="game-rule-picker" id="gameRulePicker"></div>
          <label>Количество
            <input name="count" type="number" min="1" max="200" value="10" />
          </label>
          <label>Название игры
            <input name="title" placeholder="Пушинки: тренировка" />
          </label>
          <label>Описание
            <input name="description" placeholder="Поймайте пушинки и выберите правильную букву" />
          </label>
          <button class="primary-button" type="submit">Создать ссылку</button>
          <p class="error" id="baseGameError"></p>
        </form>
        <form class="builder-panel" id="uploadGameForm">
          <h4>Загрузить свой JSON</h4>
          <label>JSON-файл
            <input name="file" type="file" accept="application/json,.json" />
          </label>
          <button class="primary-button" type="submit">Загрузить JSON</button>
          <details class="prompt-box">
            <summary>Промпт для нейросети: подготовить JSON для игры</summary>
            <textarea readonly>Ты опытный преподаватель русского языка. Преврати мой список слов/заданий в JSON для HTML-игры «Пушинки».

Нужен строго валидный JSON без комментариев, без пояснений до и после, без Markdown-разметки.

Формат JSON:
{
  "title": "Название игры",
  "description": "Короткое описание",
  "mechanic": "fluffs",
  "items": [
    {
      "variant": "слово или предложение с пропуском",
      "answer": "правильный ответ",
      "options": ["вариант 1", "вариант 2"],
      "correct_spelling": "правильное написание полностью",
      "explanation": "краткое объяснение правила"
    }
  ]
}

Правила:
1. В поле variant поставь пропуск двумя точками: ..
2. В поле answer укажи только то, что должно быть вставлено на место пропуска.
3. Если на месте пропуска ничего не пишется, в answer поставь "-".
4. В correct_spelling напиши слово полностью без пропуска.
5. В explanation дай короткое объяснение для ученика.
6. В options дай 2-4 варианта ответа.
7. Для орфографии часто подходят варианты ["а", "о"], ["е", "и"], ["е", "ё", "о"], ["ь", "ъ", "-"].
8. Не добавляй лишних полей.
9. Верни только JSON.

Мой список:
[ВСТАВЬТЕ СЮДА СВОЙ СПИСОК СЛОВ ИЛИ ЗАДАНИЙ]</textarea>
          </details>
          <p class="error" id="uploadGameError"></p>
        </form>
      </div>
      <div class="builder-result hidden" id="gameBuilderResult">
        <span class="muted">Ссылка для учеников</span>
        <a id="gameBuilderLink" target="_blank" rel="noopener"></a>
        <button class="secondary-button" id="copyGameLink" type="button">Скопировать ссылку</button>
      </div>
    </section>
  ` : "";
  view.innerHTML = `
    <section class="mini-page">
      <div class="panel-head">
        <div>
          <p class="eyebrow">игры</p>
          <h2>${selectedGame ? selectedGame.title : "Выберите игру"}</h2>
        </div>
        <div class="button-row">
          ${selectedGame ? `<button class="secondary-button" id="backToMiniMenu" type="button">К списку игр</button>` : ""}
          <button class="secondary-button" id="backToCatalogFromMini" type="button">Назад в каталог</button>
        </div>
      </div>
      ${selectedGame
        ? `<iframe class="mini-frame" title="${selectedGame.title}" src="${selectedGame.path}"></iframe>`
        : `<div class="mini-game-grid">${gameCards}</div>`}
      ${teacherBuilder}
    </section>
  `;
  view.querySelectorAll(".open-mini-game").forEach((button) => {
    button.addEventListener("click", () => {
      state.currentMiniGame = button.dataset.game;
      history.pushState(null, "", `/apps/mini/games/${button.dataset.game}`);
      renderMiniActivity();
    });
  });
  view.querySelector("#backToMiniMenu")?.addEventListener("click", () => {
    state.currentMiniGame = null;
    history.pushState(null, "", "/apps/mini");
    renderMiniActivity();
  });
  view.querySelector("#backToCatalogFromMini").addEventListener("click", () => {
    state.currentActivity = null;
    state.currentMiniGame = null;
    history.pushState(null, "", "/");
    renderDashboard();
  });
  if (!selectedGame && state.user.role === "teacher") setupGameBuilder();
}

async function setupGameBuilder() {
  const builder = view.querySelector("#gameBuilder");
  if (!builder) return;

  const sourceSelect = builder.querySelector("#gameSourceSelect");
  const rulePicker = builder.querySelector("#gameRulePicker");
  const result = builder.querySelector("#gameBuilderResult");
  const link = builder.querySelector("#gameBuilderLink");
  let sources = [];
  let selectedGameRuleIds = new Set();

  function showResult(data) {
    result.classList.remove("hidden");
    link.href = data.url;
    link.textContent = data.url;
  }

  function showBuilderError(id, message) {
    builder.querySelector(id).textContent = message || "";
  }

  function sourceRules() {
    const source = sources.find((item) => item.id === sourceSelect.value);
    return source?.rules || {};
  }

  function updateGameRuleSummary() {
    const rules = Object.values(sourceRules()).flat();
    const selectedWords = rules
      .filter((rule) => selectedGameRuleIds.has(rule.rule_id))
      .reduce((sum, rule) => sum + rule.count, 0);
    const summary = rulePicker.querySelector("[data-game-rule-summary]");
    if (summary) summary.textContent = `${selectedGameRuleIds.size} подгрупп, ${selectedWords} слов`;
    rulePicker.querySelectorAll("[data-game-rule-id]").forEach((checkbox) => {
      checkbox.checked = selectedGameRuleIds.has(checkbox.dataset.gameRuleId);
    });
  }

  function fillRules() {
    const grouped = sourceRules();
    const allRuleIds = Object.values(grouped).flat().map((rule) => rule.rule_id);
    selectedGameRuleIds = new Set([...selectedGameRuleIds].filter((ruleId) => allRuleIds.includes(ruleId)));
    if (!selectedGameRuleIds.size && allRuleIds.length) selectedGameRuleIds.add(allRuleIds[0]);

    const groups = Object.entries(grouped).map(([category, rules]) => `
      <div class="game-rule-group">
        <button class="ghost-button game-rule-category" data-game-category="${escapeHtml(category)}" type="button">
          ${escapeHtml(category)}
        </button>
        <div class="game-rule-checks">
          ${rules.map((rule) => `
            <label class="rule-check">
              <input type="checkbox" data-game-rule-id="${escapeHtml(rule.rule_id)}" ${selectedGameRuleIds.has(rule.rule_id) ? "checked" : ""} />
              <span>${escapeHtml(rule.rule_name)}</span>
              <b>${rule.count}</b>
            </label>
          `).join("")}
        </div>
      </div>
    `).join("");

    rulePicker.innerHTML = `
      <div class="game-rule-head">
        <b>Рубрики</b>
        <span class="muted" data-game-rule-summary></span>
      </div>
      ${groups || `<p class="muted">В этой базе нет рубрик.</p>`}
    `;

    rulePicker.querySelectorAll("[data-game-category]").forEach((button) => {
      button.addEventListener("click", () => {
        const category = button.dataset.gameCategory;
        const ids = (grouped[category] || []).map((rule) => rule.rule_id);
        const allSelected = ids.length > 0 && ids.every((ruleId) => selectedGameRuleIds.has(ruleId));
        ids.forEach((ruleId) => {
          if (allSelected) {
            selectedGameRuleIds.delete(ruleId);
          } else {
            selectedGameRuleIds.add(ruleId);
          }
        });
        updateGameRuleSummary();
      });
    });

    rulePicker.querySelectorAll("[data-game-rule-id]").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selectedGameRuleIds.add(checkbox.dataset.gameRuleId);
        } else {
          selectedGameRuleIds.delete(checkbox.dataset.gameRuleId);
        }
        updateGameRuleSummary();
      });
    });

    updateGameRuleSummary();
  }

  try {
    const data = await api("/api/games/sources");
    sources = data.sources || [];
    sourceSelect.innerHTML = sources.map((source) =>
      `<option value="${escapeHtml(source.id)}">${escapeHtml(source.title)}</option>`
    ).join("");
    fillRules();
  } catch (error) {
    showBuilderError("#baseGameError", error.message);
  }

  sourceSelect.addEventListener("change", () => {
    selectedGameRuleIds = new Set();
    fillRules();
  });

  builder.querySelector("#baseGameForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    showBuilderError("#baseGameError", "");
    const form = new FormData(event.currentTarget);
    try {
      const data = await api("/api/games/sets/from-base", {
        method: "POST",
        body: JSON.stringify({
          mechanic: form.get("mechanic"),
          source: form.get("source"),
          rule_ids: [...selectedGameRuleIds],
          count: Number(form.get("count") || 10),
          title: form.get("title"),
          description: form.get("description"),
        }),
      });
      showResult(data);
    } catch (error) {
      showBuilderError("#baseGameError", error.message);
    }
  });

  builder.querySelector("#uploadGameForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    showBuilderError("#uploadGameError", "");
    const file = new FormData(event.currentTarget).get("file");
    if (!file || !file.name) {
      showBuilderError("#uploadGameError", "Выберите JSON-файл.");
      return;
    }
    if (file.size > 200000) {
      showBuilderError("#uploadGameError", "Файл слишком большой.");
      return;
    }
    try {
      const payload = JSON.parse(await file.text());
      const data = await api("/api/games/sets/upload-json", {
        method: "POST",
        body: JSON.stringify({ payload }),
      });
      showResult(data);
    } catch (error) {
      showBuilderError("#uploadGameError", error.message || "JSON не удалось прочитать.");
    }
  });

  builder.querySelector("#copyGameLink").addEventListener("click", async () => {
    if (!link.href) return;
    const button = builder.querySelector("#copyGameLink");
    const copied = await copyTextToClipboard(link.href);
    button.textContent = copied ? "Ссылка скопирована" : "Не удалось скопировать";
    setTimeout(() => {
      button.textContent = "Скопировать ссылку";
    }, 1800);
  });
}

function renderSidebar() {
  const activity = activityMeta[state.currentActivity] || activityMeta.ege9;
  const teacherCode = state.user.role === "teacher" && state.user.teacher_code
    ? `<span class="muted">Код для учеников: <b>${state.user.teacher_code}</b></span>`
    : "";
  document.querySelector("#userBlock").innerHTML = `
    <span class="activity-badge">${activity.shortTitle}</span>
    <strong>${state.user.display_name}</strong>
    <span class="muted">${state.user.role === "admin" ? "Кабинет администратора" : state.user.role === "teacher" ? "Кабинет учителя" : "Кабинет ученика"}</span>
    ${teacherCode}
  `;
  const list = document.querySelector("#modeList");
  list.innerHTML = "";
  Object.entries(modes).forEach(([modeId, mode]) => {
    const button = document.createElement("button");
    button.className = `mode-button ${state.mode === modeId ? "active" : ""}`;
    button.innerHTML = `<b>${mode.title}</b><span>${mode.hint}</span>`;
    button.addEventListener("click", () => {
      state.mode = modeId;
      state.currentSession = null;
      state.answers = {};
      renderSidebar();
      renderMode();
    });
    list.append(button);
  });
  document.querySelector("#quickStats").innerHTML = `
    <div class="stat"><b>${state.bootstrap.word_count}</b><span>слов в базе</span></div>
    <div class="stat"><b>${Object.values(state.bootstrap.rules).flat().length}</b><span>подправила</span></div>
  `;
}

function renderMode() {
  const mode = modes[state.mode];
  document.querySelector("#modeEyebrow").textContent = mode.eyebrow;
  document.querySelector("#modeTitle").textContent = mode.title;
  document.querySelector("#practiceView").classList.add("hidden");
  document.querySelector("#resultView").classList.add("hidden");
  renderSetup();
}

function backToMenu() {
  state.currentSession = null;
  state.answers = {};
  renderMode();
  document.querySelector("#modeList")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderSetup() {
  const setup = document.querySelector("#setupView");
  const ruleSelector = ["rule", "word_letter"].includes(state.mode) ? renderRuleSelector() : "";
  const errorModeSelector = state.mode === "errors" ? `
    <label>
      Режим в копилке
      <select id="errorTrainingMode">
        <option value="cards" ${state.errorTrainingMode === "cards" ? "selected" : ""}>Карточки с вариантами</option>
        <option value="word_letter" ${state.errorTrainingMode === "word_letter" ? "selected" : ""}>Слово - буква</option>
      </select>
    </label>
  ` : "";
  setup.innerHTML = `
    <div class="setup-grid">
      <label>
        Количество вопросов: <b id="questionCountValue">${state.questionCount}</b>
        <input id="questionCount" type="range" min="1" max="30" value="${state.questionCount}" />
      </label>
      <button class="primary-button" id="startPractice" type="button">Начать</button>
    </div>
    ${errorModeSelector}
    <label class="manual-toggle">
      <input id="manualInput" type="checkbox" ${state.manualInput || state.mode === "word_letter" ? "checked" : ""} ${state.mode === "word_letter" ? "disabled" : ""} />
      <span>Самостоятельно вводить ответ с клавиатуры</span>
    </label>
    <div class="practice-actions setup-actions">
      <button class="ghost-button" id="backToMenu" type="button">Назад к меню</button>
    </div>
    ${ruleSelector}
  `;
  setup.querySelector("#startPractice").addEventListener("click", startPractice);
  setup.querySelector("#questionCount").addEventListener("input", (event) => {
    state.questionCount = Number(event.target.value);
    setup.querySelector("#questionCountValue").textContent = state.questionCount;
  });
  setup.querySelector("#manualInput").addEventListener("change", (event) => {
    state.manualInput = event.target.checked;
  });
  setup.querySelector("#errorTrainingMode")?.addEventListener("change", (event) => {
    state.errorTrainingMode = event.target.value;
  });
  setup.querySelector("#backToMenu").addEventListener("click", backToMenu);
  bindRuleSelector(setup, renderSetup);
}

function renderRuleSelector() {
  ensureRuleSelection();
  const activeCategories = selectedCategorySet();
  const categoryButtons = ruleCategories()
    .map((category) => `
      <button class="category-pill ${activeCategories.has(category) ? "active" : ""}" data-category="${category}" type="button">
        <span>${category}</span>
        <b>${state.bootstrap.rules[category].reduce((sum, rule) => sum + rule.count, 0)}</b>
      </button>
    `)
    .join("");
  const selected = selectedRuleSet();
  const rules = selectedRules();
  const selectedVisible = rules.filter((rule) => selected.has(rule.rule_id));
  const allSelected = rules.length > 0 && selectedVisible.length === rules.length;
  const selectedCount = rules
    .filter((rule) => selected.has(rule.rule_id))
    .reduce((sum, rule) => sum + rule.count, 0);
  const ruleOptions = rules
    .map((rule) => `
      <label class="rule-check">
        <input type="checkbox" data-rule-id="${rule.rule_id}" ${selected.has(rule.rule_id) ? "checked" : ""} />
        <span>${rule.rule_name}</span>
        <b>${rule.count}</b>
      </label>
    `)
    .join("");
  return `
    <section class="rule-picker">
      <div class="category-grid">${categoryButtons}</div>
      <div class="rule-select-row">
        <div class="rule-check-list">
          <label class="rule-check rule-check-all">
            <input id="allRules" type="checkbox" ${allSelected ? "checked" : ""} />
            <span>Все подгруппы в выбранных разделах</span>
            <b>${rules.reduce((sum, rule) => sum + rule.count, 0)}</b>
          </label>
          ${ruleOptions}
        </div>
        <div class="selected-rule">
          <b data-selected-word-count>${selectedCount}</b>
          <span>слов в выбранных подгруппах</span>
        </div>
      </div>
    </section>
  `;
}

function bindRuleSelector(root, rerenderCategories) {
  root.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleRuleCategory(button.dataset.category);
      rerenderCategories();
    });
  });
  root.querySelector("#allRules")?.addEventListener("change", (event) => {
    state.ruleSelectionTouched = true;
    const next = selectedRuleSet();
    const ids = selectedRules().map((rule) => rule.rule_id);
    if (event.target.checked) {
      ids.forEach((ruleId) => next.add(ruleId));
    } else {
      ids.forEach((ruleId) => next.delete(ruleId));
    }
    state.selectedRuleIds = [...next];
    root.querySelectorAll("[data-rule-id]").forEach((checkbox) => {
      checkbox.checked = event.target.checked;
    });
    updateRuleSelectorSummary(root);
  });
  root.querySelectorAll("[data-rule-id]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      state.ruleSelectionTouched = true;
      const next = selectedRuleSet();
      if (checkbox.checked) {
        next.add(checkbox.dataset.ruleId);
      } else {
        next.delete(checkbox.dataset.ruleId);
      }
      state.selectedRuleIds = [...next];
      updateRuleSelectorSummary(root);
    });
  });
  updateRuleSelectorSummary(root);
}

async function startPractice() {
  const count = state.questionCount;
  const payload = { mode: state.mode, count };
  if (state.mode === "errors") payload.error_training_mode = state.errorTrainingMode;
  if (["rule", "word_letter"].includes(state.mode)) payload.rule_ids = state.selectedRuleIds;
  const setup = document.querySelector("#setupView");
  try {
    const data = await api(activityApi("/practice/start"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.currentSession = data;
    state.answers = {};
    state.liveResults = [];
    state.currentQuestionIndex = 0;
    state.startedAt = Date.now();
    setup.innerHTML = "";
    if (state.mode === "word_letter" || (state.mode === "errors" && state.errorTrainingMode === "word_letter")) {
      renderLiveQuestion();
    } else {
      renderQuestions();
    }
  } catch (err) {
    setup.insertAdjacentHTML("beforeend", `<p class="error">${err.message}</p>`);
  }
}

function normalizeLetter(value) {
  return String(value || "").trim().toLowerCase().replace("ё", "ё").slice(0, 1);
}

function renderLiveQuestion(feedback = null) {
  const practice = document.querySelector("#practiceView");
  const result = document.querySelector("#resultView");
  result.classList.add("hidden");
  practice.classList.remove("hidden");
  const question = state.currentSession.questions[state.currentQuestionIndex];
  if (!question) {
    renderResults({
      results: state.liveResults,
      correct: state.liveResults.filter((item) => item.is_correct).length,
      total: state.liveResults.length,
    });
    return;
  }
  practice.innerHTML = `
    <article class="question live-question">
      <div class="question-head">
        <span>Слово ${state.currentQuestionIndex + 1} из ${state.currentSession.questions.length}</span>
        <span>${question.rule_name}</span>
      </div>
      <div class="word-prompt">${question.prompt}</div>
      <div class="letter-input-row">
        <input id="liveAnswer" maxlength="1" autocomplete="off" inputmode="text" aria-label="Введите букву" />
        <button class="primary-button" id="checkLiveAnswer" type="button">Проверить</button>
      </div>
      <div id="liveFeedback">${feedback || ""}</div>
    </article>
    <div class="practice-actions">
      <button class="ghost-button" id="backPractice" type="button">Назад</button>
      <button class="ghost-button" id="cancelPractice" type="button">Сбросить</button>
    </div>
  `;
  const input = practice.querySelector("#liveAnswer");
  const check = practice.querySelector("#checkLiveAnswer");
  const send = async () => {
    const answer = normalizeLetter(input.value);
    if (!answer) return;
    check.disabled = true;
    const elapsed = Math.round((Date.now() - state.startedAt) / 1000);
    const item = await api(activityApi("/practice/check"), {
      method: "POST",
      body: JSON.stringify({
        session_id: state.currentSession.session_id,
        question_id: question.question_id,
        answer,
        time_spent_sec: elapsed,
      }),
    });
    state.liveResults.push(item);
    if (item.is_correct) {
      state.currentQuestionIndex += 1;
      renderLiveQuestion();
      return;
    }
    renderLiveQuestion(`
      <div class="result-item bad">
        <b>Неверно. Правильно: ${item.correct_answer}</b>
        <p>${item.correct_spelling || ""}</p>
        <p class="muted">${item.explanation || ""}</p>
        <button class="secondary-button" id="nextAfterRule" type="button">Дальше</button>
      </div>
    `);
    document.querySelector("#liveAnswer").disabled = true;
    document.querySelector("#checkLiveAnswer").disabled = true;
    const next = document.querySelector("#nextAfterRule");
    next.disabled = true;
    setTimeout(() => { next.disabled = false; }, 2500);
    next.addEventListener("click", () => {
      state.currentQuestionIndex += 1;
      renderLiveQuestion();
    });
  };
  check.addEventListener("click", send);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") send();
  });
  practice.querySelector("#cancelPractice").addEventListener("click", renderMode);
  practice.querySelector("#backPractice").addEventListener("click", backToMenu);
  input.focus();
}

function renderQuestions() {
  const practice = document.querySelector("#practiceView");
  practice.classList.remove("hidden");
  practice.innerHTML = `
    <div class="question-stack">
      ${state.currentSession.questions.map(renderQuestion).join("")}
    </div>
    <div class="practice-actions">
      <button class="ghost-button" id="backPractice" type="button">Назад</button>
      <button class="ghost-button" id="cancelPractice" type="button">Сбросить</button>
      <button class="primary-button" id="submitPractice" type="button">Проверить</button>
    </div>
  `;
  practice.querySelector("#backPractice").addEventListener("click", backToMenu);
  practice.querySelector("#cancelPractice").addEventListener("click", renderMode);
  practice.querySelector("#submitPractice").addEventListener("click", submitPractice);
  practice.querySelectorAll("[data-manual-answer]").forEach((input) => {
    input.addEventListener("input", () => {
      state.answers[input.dataset.manualAnswer] = input.dataset.kind === "line"
        ? input.value
        : normalizeLetter(input.value);
    });
  });
  practice.querySelectorAll("[data-answer]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.multi === "true") {
        const current = new Set((state.answers[button.dataset.questionId] || "").split("").filter(Boolean));
        if (current.has(button.dataset.answer)) {
          current.delete(button.dataset.answer);
        } else {
          current.add(button.dataset.answer);
        }
        state.answers[button.dataset.questionId] = [...current].sort().join("");
      } else {
        state.answers[button.dataset.questionId] = button.dataset.answer;
      }
      renderQuestions();
    });
  });
}

function renderQuestion(question, index) {
  if (question.kind === "line") {
    if (state.manualInput) {
      return `
        <article class="question">
          <div class="question-head"><span>Вопрос ${index + 1}</span><span>${question.rule_name}</span></div>
          <div>${question.prompt}</div>
          ${question.rows.map((row, rowIndex) => `
            <div class="line-row static-line-row">
              <b>${rowIndex + 1}</b>
              <span class="line-words">${row.map((word) => `<span>${word}</span>`).join("")}</span>
            </div>
          `).join("")}
          <label class="answer-input-label">
            Ответ вручную
            <input data-manual-answer="${question.question_id}" data-kind="line" placeholder="например, 135" value="${state.answers[question.question_id] || ""}" />
          </label>
        </article>
      `;
    }
    const rows = question.rows
      .map((row, rowIndex) => {
        const answer = String(rowIndex + 1);
        const selected = (state.answers[question.question_id] || "").includes(answer);
        return `
          <button class="line-row ${selected ? "selected" : ""}" data-multi="true" data-question-id="${question.question_id}" data-answer="${answer}" type="button">
            <b>${answer}</b>
            <span class="line-words">${row.map((word) => `<span>${word}</span>`).join("")}</span>
          </button>
        `;
      })
      .join("");
    return `
      <article class="question">
        <div class="question-head"><span>Вопрос ${index + 1}</span><span>${question.rule_name}</span></div>
        <div>${question.prompt}</div>
        ${rows}
      </article>
    `;
  }
  const choices = question.choices
    .map((choice) => {
      const selected = state.answers[question.question_id] === choice;
      return `<button class="choice ${selected ? "selected" : ""}" data-question-id="${question.question_id}" data-answer="${choice}" type="button">${choice}</button>`;
    })
    .join("");
  if (state.manualInput) {
    return `
      <article class="question">
        <div class="question-head"><span>Вопрос ${index + 1}</span><span>${question.rule_name}</span></div>
        <div class="word-prompt">${question.prompt}</div>
        <label class="answer-input-label">
          Введите букву
          <input data-manual-answer="${question.question_id}" maxlength="1" autocomplete="off" value="${state.answers[question.question_id] || ""}" />
        </label>
      </article>
    `;
  }
  return `
    <article class="question">
      <div class="question-head"><span>Вопрос ${index + 1}</span><span>${question.rule_name}</span></div>
      <div class="word-prompt">${question.prompt}</div>
      <div class="choice-row">${choices}</div>
    </article>
  `;
}

async function submitPractice() {
  const total = state.currentSession.questions.length;
  const answered = state.currentSession.questions.every((question) => String(state.answers[question.question_id] || "").trim());
  if (Object.keys(state.answers).length < total || !answered) {
    alert("Ответьте на все вопросы перед проверкой.");
    return;
  }
  const elapsed = Math.round((Date.now() - state.startedAt) / 1000);
  const data = await api(activityApi("/practice/submit"), {
    method: "POST",
    body: JSON.stringify({
      session_id: state.currentSession.session_id,
      answers: state.answers,
      time_spent_sec: elapsed,
    }),
  });
  renderResults(data);
}

function renderResults(data) {
  document.querySelector("#practiceView").classList.add("hidden");
  const result = document.querySelector("#resultView");
  result.classList.remove("hidden");
  result.innerHTML = `
    <div class="stat"><b>${data.correct}/${data.total}</b><span>${pct(data.correct, data.total)} правильных ответов</span></div>
    <div class="result-list">
      ${data.results.map((item, index) => `
        <div class="result-item ${item.is_correct ? "ok" : "bad"}">
          <b>${index + 1}. ${item.is_correct ? "Верно" : "Повторим еще"}</b>
          <p>Ответ: ${item.given_answer || "—"} · правильно: ${item.correct_answer}</p>
          <p>${item.correct_spelling || ""}</p>
          ${item.is_correct ? "" : `<p class="muted">${item.explanation || ""}</p>`}
        </div>
      `).join("")}
    </div>
    <div class="practice-actions">
      <button class="ghost-button" type="button" id="backFromResults">Назад</button>
      <button class="primary-button" type="button" id="againButton">Новая тренировка</button>
    </div>
  `;
  result.querySelector("#backFromResults").addEventListener("click", backToMenu);
  result.querySelector("#againButton").addEventListener("click", renderMode);
}

function renderTeacherStudentCards(students) {
  if (!students.length) {
    return `<p class="muted">Пока нет учеников, зарегистрированных по вашему коду.</p>`;
  }
  return students.map((student) => {
    const teacher = { consent_accepted: student.consent_accepted };
    const topErrors = student.top_errors.length
      ? student.top_errors.map((item) => `<li>${item.rule_name}: ${item.errors}</li>`).join("")
      : "<li>ошибок пока нет</li>";
    const pending = student.not_worked_out.length
      ? student.not_worked_out.slice(0, 5).map((item) => `<li>${item.correct_spelling || item.word}</li>`).join("")
      : "<li>очередь повторения пуста</li>";
    const errorBank = student.error_bank.length
      ? student.error_bank.slice(0, 6).map((item) => `<li>${item.correct_spelling || item.word}</li>`).join("")
      : "<li>копилка пуста</li>";
    return `
      <article class="student-card">
        <div class="student-card-head">
          <div>
            <b>${student.display_name}</b>
            <span class="muted">${student.email || student.username}</span>
          </div>
          <div class="mini-stat"><b>${pct(student.correct, student.total)}</b><span>точность</span></div>
        </div>
        <div class="teacher-metrics">
          <div class="stat"><b>${teacher.consent_accepted ? "да" : "нет"}</b><span>согласие принято</span></div>
          <div class="stat"><b>${student.total}</b><span>заданий решено</span></div>
          <div class="stat"><b>${student.untouched}</b><span>слов не затронуто</span></div>
          <div class="stat"><b>${student.error_bank.length}</b><span>в копилке ошибок</span></div>
        </div>
        <div class="student-lists">
          <div><h4>Больше ошибок</h4><ul>${topErrors}</ul></div>
          <div><h4>Не отработано</h4><ul>${pending}</ul></div>
          <div><h4>Копилка</h4><ul>${errorBank}</ul></div>
        </div>
      </article>
    `;
  }).join("");
}

async function renderTeacherDashboardPreview() {
  const main = document.querySelector(".main-panel");
  const old = document.querySelector("#teacherQuickPanel");
  old?.remove();
  const panel = document.createElement("section");
  panel.className = "teacher-quick-panel";
  panel.id = "teacherQuickPanel";
  panel.innerHTML = `<p class="muted">Загружаю быструю статистику...</p>`;
  main.insertBefore(panel, document.querySelector("#setupView"));
  try {
    const data = await api("/api/progress");
    panel.innerHTML = `
      <div class="section-head">
        <div>
          <p class="eyebrow">быстрая статистика</p>
          <h3>Ученики и зоны отработки</h3>
        </div>
        <div class="button-row">
          <button class="secondary-button" id="makeTestButton" type="button">Составить тест</button>
          <button class="secondary-button" id="downloadStudents" type="button">Скачать статистику</button>
          <button class="secondary-button" id="openFullProgress" type="button">Полная активность</button>
        </div>
      </div>
      <div class="student-card-grid">${renderTeacherStudentCards(data.teacher_dashboard.students)}</div>
    `;
    panel.querySelector("#openFullProgress").addEventListener("click", showProgress);
    panel.querySelector("#makeTestButton").addEventListener("click", showTestComposer);
    panel.querySelector("#downloadStudents").addEventListener("click", () => downloadRequest("/api/progress/export?section=students", "ege_students.csv"));
  } catch (err) {
    panel.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

function downloadButton(section, label) {
  return `<button class="ghost-button download-stat" data-section="${section}" type="button">${label}</button>`;
}

async function showProgress() {
  const data = await api("/api/progress");
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  const summary = data.summary;
  const studentRows = data.by_student.map((row) => `
    <tr><td>${row.display_name}</td><td>${row.total}</td><td>${pct(row.correct, row.total)}</td></tr>
  `).join("");
  const ruleRows = data.by_rule.map((row) => `
    <tr><td>${row.category}</td><td>${row.rule_name}</td><td>${row.total}</td><td>${pct(row.correct, row.total)}</td></tr>
  `).join("");
  const categoryRows = data.by_category.map((row) => `
    <tr><td>${row.category}</td><td>${row.total}</td><td>${pct(row.correct, row.total)}</td></tr>
  `).join("");
  const answerListRows = (rows) => rows.slice(0, 30).map((row) => `
    <tr>
      <td>${row.display_name}</td>
      <td>${row.category || ""}</td>
      <td>${row.rule_name || ""}</td>
      <td>${row.prompt}</td>
      <td>${row.given_answer || "—"} / ${row.correct_answer}</td>
    </tr>
  `).join("");
  const recentRows = data.recent.map((row) => `
    <tr>
      <td>${new Date(row.created_at).toLocaleString()}</td>
      <td>${row.display_name}</td>
      <td>${row.category || ""}</td>
      <td>${row.rule_name || ""}</td>
      <td>${row.prompt}</td>
      <td>${row.given_answer} / ${row.correct_answer}</td>
      <td>${row.is_correct ? "да" : "нет"}</td>
    </tr>
  `).join("");
  const teacherOverview = state.user.role === "teacher" && data.teacher_dashboard
    ? `<h3>Быстрая статистика учеников</h3><div class="student-card-grid">${renderTeacherStudentCards(data.teacher_dashboard.students)}</div>`
    : "";
  backdrop.innerHTML = `
    <section class="progress-modal">
      <div class="panel-head">
        <div><p class="eyebrow">прогресс</p><h2>${state.user.role === "teacher" ? "Журнал класса" : "Мои результаты"}</h2></div>
        <button class="secondary-button" id="closeProgress" type="button">Закрыть</button>
      </div>
      <div class="progress-grid">
        <div class="stat"><b>${summary.total}</b><span>ответов</span></div>
        <div class="stat"><b>${summary.correct}</b><span>верно</span></div>
        <div class="stat"><b>${pct(summary.correct, summary.total)}</b><span>точность</span></div>
      </div>
      ${state.user.role !== "teacher" ? `
        <div class="progress-grid">
          <div class="stat"><b>${data.due_reviews}</b><span>слов в очереди повторения</span></div>
          <div class="stat"><b>${data.error_bank_count}</b><span>слов в копилке ошибок</span></div>
        </div>
      ` : ""}
      ${teacherOverview}
      ${state.user.role === "teacher" ? `<div class="table-head"><h3>Ученики</h3>${downloadButton("students", "Скачать статистику")}</div><table class="table"><tr><th>Имя</th><th>Ответов</th><th>Точность</th></tr>${studentRows}</table>` : ""}
      <div class="table-head"><h3>Группы</h3>${downloadButton("categories", "Скачать статистику")}</div>
      <table class="table"><tr><th>Группа</th><th>Ответов</th><th>Точность</th></tr>${categoryRows}</table>
      <table class="table"><tr><th>Группа</th><th>Подгруппа</th><th>Ответов</th><th>Точность</th></tr>${ruleRows}</table>
      <details class="activity-details">
        <summary>Развернуть полную активность</summary>
        <div class="table-head"><h3>Решено верно</h3>${downloadButton("correct", "Скачать статистику")}</div>
        <table class="table"><tr><th>Ученик</th><th>Группа</th><th>Подгруппа</th><th>Задание</th><th>Ответ</th></tr>${answerListRows(data.correct_attempts)}</table>
        <div class="table-head"><h3>Решено неверно</h3>${downloadButton("incorrect", "Скачать статистику")}</div>
        <table class="table"><tr><th>Ученик</th><th>Группа</th><th>Подгруппа</th><th>Задание</th><th>Ответ</th></tr>${answerListRows(data.incorrect_attempts)}</table>
        <div class="table-head"><h3>Последние попытки</h3>${downloadButton("recent", "Скачать статистику")}</div>
        <table class="table"><tr><th>Дата</th><th>Пользователь</th><th>Группа</th><th>Подгруппа</th><th>Задание</th><th>Ответ</th><th>Верно</th></tr>${recentRows}</table>
      </details>
    </section>
  `;
  document.body.append(backdrop);
  backdrop.querySelector("#closeProgress").addEventListener("click", () => backdrop.remove());
  backdrop.querySelectorAll(".download-stat").forEach((button) => {
    button.addEventListener("click", () => downloadRequest(`/api/progress/export?section=${button.dataset.section}`, `ege_${button.dataset.section}.csv`));
  });
}

function showTestComposer() {
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  const ruleSelector = renderRuleSelector();
  backdrop.innerHTML = `
    <section class="progress-modal">
      <div class="panel-head">
        <div><p class="eyebrow">тест</p><h2>Составить тест</h2></div>
        <button class="secondary-button" id="closeTestComposer" type="button">Закрыть</button>
      </div>
      <div class="setup-grid">
        <label>
          Режим
          <select id="testMode">
            <option value="rule">Выбранные темы</option>
            <option value="mix">Микс</option>
            <option value="errors">Копилка ошибок</option>
            <option value="line">Строки</option>
          </select>
        </label>
        <label>
          Количество заданий
          <input id="testCount" type="number" min="1" max="60" value="${state.questionCount}" />
        </label>
      </div>
      <label class="manual-toggle">
        <input id="testIncludeErrors" type="checkbox" />
        <span>Добавить слова из копилки ошибок класса</span>
      </label>
      <div id="testRuleSelector">${ruleSelector}</div>
      <p class="error" id="testComposerError"></p>
      <div class="practice-actions">
        <button class="primary-button" id="downloadTest" type="button">Скачать .txt</button>
      </div>
    </section>
  `;
  document.body.append(backdrop);
  const mountTestRuleSelector = () => {
    backdrop.querySelector("#testRuleSelector").innerHTML = renderRuleSelector();
    bindRuleSelector(backdrop.querySelector("#testRuleSelector"), mountTestRuleSelector);
    refreshRules();
  };
  const refreshRules = () => {
    backdrop.querySelector("#testRuleSelector").classList.toggle("hidden", backdrop.querySelector("#testMode").value !== "rule");
  };
  backdrop.querySelector("#closeTestComposer").addEventListener("click", () => backdrop.remove());
  backdrop.querySelector("#testMode").addEventListener("change", refreshRules);
  bindRuleSelector(backdrop.querySelector("#testRuleSelector"), mountTestRuleSelector);
  backdrop.querySelector("#downloadTest").addEventListener("click", async () => {
    const error = backdrop.querySelector("#testComposerError");
    error.textContent = "";
    try {
      await downloadRequest("/api/teacher/test", "ege_test.txt", {
        method: "POST",
        body: JSON.stringify({
          mode: backdrop.querySelector("#testMode").value,
          count: backdrop.querySelector("#testCount").value,
          include_errors: backdrop.querySelector("#testIncludeErrors").checked,
          rule_ids: state.selectedRuleIds,
        }),
      });
    } catch (err) {
      error.textContent = err.message;
    }
  });
  refreshRules();
}

function renderAdminContent(data, closeButton = "") {
  const platform = data.platform;
  const consentLabel = (row) => row.consent_accepted
    ? `да${row.consent_accepted_at ? `, ${new Date(row.consent_accepted_at).toLocaleDateString()}` : ""}`
    : "нет";
  const teacherCards = data.teachers.map((teacher) => {
    const teacherEmail = teacher.email || teacher.username;
    const students = teacher.students_list.length
      ? teacher.students_list.map((student) => `
        <tr>
          <td>${student.display_name}</td>
          <td>${student.email || student.username}<br><span class="muted">согласие: ${consentLabel(student)}</span></td>
          <td>${student.attempts}</td>
          <td>${pct(student.correct, student.attempts)}</td>
          <td>
            <button class="ghost-button reset-password" data-user-id="${student.user_id}" data-username="${student.email || student.username}" type="button">
              ${student.password_reset_required ? "Ожидает новый пароль" : "Сбросить пароль"}
            </button>
          </td>
        </tr>
      `).join("")
      : `<tr><td colspan="5">Учеников пока нет</td></tr>`;
    return `
      <article class="admin-card">
        <div class="student-card-head">
          <div>
            <b>${teacher.display_name}</b>
            <span class="muted">${teacherEmail} · код ${teacher.teacher_code || "не задан"}</span>
          </div>
          <div class="button-row">
            <button class="ghost-button reset-password" data-user-id="${teacher.user_id}" data-username="${teacherEmail}" type="button">
              ${teacher.password_reset_required ? "Ожидает новый пароль" : "Сбросить пароль"}
            </button>
          </div>
        </div>
        <div class="teacher-metrics">
          <div class="stat"><b>${teacher.attempts}</b><span>ответов</span></div>
          <div class="stat"><b>${pct(teacher.correct, teacher.attempts)}</b><span>точность</span></div>
        </div>
        <table class="table"><tr><th>Ученик</th><th>Email</th><th>Ответов</th><th>Точность</th><th>Пароль</th></tr>${students}</table>
      </article>
    `;
  }).join("");
  return `
    <div class="panel-head">
      <div><p class="eyebrow">админ</p><h2>Обзор платформы</h2></div>
      ${closeButton}
    </div>
    <div class="progress-grid">
      <div class="stat"><b>${platform.total}</b><span>ответов всего</span></div>
      <div class="stat"><b>${platform.active_users}</b><span>активных пользователей</span></div>
      <div class="stat"><b>${pct(platform.correct, platform.total)}</b><span>общая точность</span></div>
    </div>
    <div class="admin-list">${teacherCards}</div>
  `;
}

async function renderAdminDashboard() {
  view.innerHTML = `
    <section class="workspace admin-workspace">
      <section class="main-panel admin-page">
        <p class="muted">Загружаю админ-панель...</p>
      </section>
    </section>
  `;
  const panel = view.querySelector(".admin-page");
  try {
    const data = await api("/api/admin");
    panel.innerHTML = renderAdminContent(data);
    bindAdminActions(panel);
  } catch (err) {
    panel.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

async function showAdmin() {
  const data = await api("/api/admin");
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <section class="progress-modal admin-modal">
      ${renderAdminContent(data, `<button class="secondary-button" id="closeAdmin" type="button">Закрыть</button>`)}
    </section>
  `;
  document.body.append(backdrop);
  backdrop.querySelector("#closeAdmin").addEventListener("click", () => backdrop.remove());
  bindAdminActions(backdrop);
}

function bindAdminActions(root) {
  root.querySelectorAll(".reset-password").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm(`Сбросить пароль пользователю ${button.dataset.username}?`)) return;
      button.disabled = true;
      try {
        await api("/api/admin/reset-password", {
          method: "POST",
          body: JSON.stringify({ user_id: button.dataset.userId }),
        });
        button.textContent = "Ожидает новый пароль";
      } catch (err) {
        alert(err.message);
        button.disabled = false;
      }
    });
  });
}

window.addEventListener("popstate", async () => {
  if (window.location.pathname === "/privacy") {
    await renderDocumentPage("privacy");
    return;
  }
  if (window.location.pathname === "/consent") {
    await renderDocumentPage("consent");
    return;
  }
  if (window.location.pathname === "/terms") {
    await renderDocumentPage("terms");
    return;
  }
  if (!state.user && window.location.pathname === "/forgot-password") {
    renderForgotPassword();
    return;
  }
  if (!state.user && window.location.pathname === "/reset-password") {
    renderResetPassword();
    return;
  }
  const slug = activityFromPath();
  if (slug && state.user) {
    await loadActivity(slug, false);
    return;
  }
  state.currentActivity = null;
  if (state.user) renderDashboard();
});

restoreSession();


