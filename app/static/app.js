const state = {
  token: localStorage.getItem("ege_token"),
  user: null,
  bootstrap: null,
  mode: "rule",
  selectedCategory: null,
  selectedRuleIds: [],
  currentSession: null,
  answers: {},
  startedAt: null,
  questionCount: 10,
  manualInput: false,
  errorTrainingMode: "cards",
  currentQuestionIndex: 0,
  liveResults: [],
  currentActivity: null,
};

const activityMeta = {
  ege9: {
    title: "Р•Р“Р­. Р—Р°РґР°РЅРёРµ 9",
    shortTitle: "Р—Р°РґР°РЅРёРµ 9",
    description: "РћСЂС„РѕРіСЂР°С„РёСЏ: РєРѕСЂРЅРё, РіР»Р°СЃРЅС‹Рµ, СЃС‚СЂРѕРєРё СЃ РѕР±С‰РµР№ Р±СѓРєРІРѕР№.",
    mark: "9",
  },
  ege10: {
    title: "Р•Р“Р­. Р—Р°РґР°РЅРёРµ 10",
    shortTitle: "Р—Р°РґР°РЅРёРµ 10",
    description: "РџСЂРёСЃС‚Р°РІРєРё, Р¬/РЄ, Р/Р« Рё РґСЂСѓРіРёРµ РѕСЂС„РѕРіСЂР°РјРјС‹.",
    mark: "10",
  },
  "demo-mini": {
    title: "HTML-РјРёРЅРё-РїСЂРёР»РѕР¶РµРЅРёРµ",
    shortTitle: "РњРёРЅРё",
    description: "РћР±РµСЂС‚РєР° РґР»СЏ Р±СѓРґСѓС‰РёС… РјРёРЅРё-РёРіСЂ Рё РёРЅС‚РµСЂР°РєС‚РёРІРЅС‹С… РєР°СЂС‚РѕС‡РµРє.",
    mark: "HTML",
  },
};

const modes = {
  rule: {
    title: "РџСЂР°РІРёР»Рѕ",
    hint: "Р‘РѕР»СЊС€Р°СЏ РіСЂСѓРїРїР° Рё РїРѕРґРІС‹Р±РѕСЂ РІРЅСѓС‚СЂРё РЅРµРµ",
    eyebrow: "С‚РѕС‡РµС‡РЅР°СЏ РѕС‚СЂР°Р±РѕС‚РєР°",
  },
  word_letter: {
    title: "РЎР»РѕРІРѕ - Р±СѓРєРІР°",
    hint: "РћРґРЅРѕ СЃР»РѕРІРѕ РЅР° СЌРєСЂР°РЅРµ, РІРІРѕРґ Р±СѓРєРІС‹ Рё РјРіРЅРѕРІРµРЅРЅР°СЏ РїСЂРѕРІРµСЂРєР°",
    eyebrow: "Р±С‹СЃС‚СЂР°СЏ РѕС‚СЂР°Р±РѕС‚РєР°",
  },
  mix: {
    title: "РњРёРєСЃ",
    hint: "Р Р°Р·РЅС‹Рµ РїСЂР°РІРёР»Р° РІ С„РѕСЂРјР°С‚Рµ СЃР»РѕРІРѕ = Р±СѓРєРІР°",
    eyebrow: "РїРµСЂРµРјРµС€Р°РЅРЅС‹Рµ РѕСЂС„РѕРіСЂР°РјРјС‹",
  },
  line: {
    title: "РЎС‚СЂРѕРєР°",
    hint: "Р СЏРґ СЃ РѕРґРЅРѕР№ Рё С‚РѕР№ Р¶Рµ Р±СѓРєРІРѕР№",
    eyebrow: "С„РѕСЂРјР°С‚ Р·Р°РґР°РЅРёСЏ 9",
  },
  errors: {
    title: "РљРѕРїРёР»РєР° РѕС€РёР±РѕРє",
    hint: "РЎР»РѕРІР°, РіРґРµ СѓР¶Рµ Р±С‹Р»Рё РїСЂРѕРјР°С…Рё",
    eyebrow: "Р»РёС‡РЅРѕРµ РїРѕРІС‚РѕСЂРµРЅРёРµ",
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

function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  return fetch(path, { ...options, headers }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "РћС€РёР±РєР° Р·Р°РїСЂРѕСЃР°");
    return data;
  });
}

async function downloadRequest(path, filename, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ error: "РћС€РёР±РєР° СЃРєР°С‡РёРІР°РЅРёСЏ" }));
    throw new Error(data.error || "РћС€РёР±РєР° СЃРєР°С‡РёРІР°РЅРёСЏ");
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

function selectedRules() {
  return state.bootstrap.rules[state.selectedCategory] || [];
}

function selectedRuleSet() {
  return new Set(state.selectedRuleIds);
}

function ensureRuleSelection() {
  const categories = ruleCategories();
  if (!state.selectedCategory || !state.bootstrap.rules[state.selectedCategory]) {
    state.selectedCategory = categories[0] || null;
  }
  const rules = selectedRules();
  const available = new Set(rules.map((rule) => rule.rule_id));
  state.selectedRuleIds = state.selectedRuleIds.filter((ruleId) => available.has(ruleId));
  if (!state.selectedRuleIds.length && rules.length) {
    state.selectedRuleIds = rules.map((rule) => rule.rule_id);
  }
}

function renderTopActions() {
  topActions.innerHTML = "";
  if (!state.user) return;
  if (state.currentActivity) {
    const catalog = document.createElement("button");
    catalog.className = "ghost-button";
    catalog.textContent = "РљР°С‚Р°Р»РѕРі";
    catalog.addEventListener("click", () => {
      state.currentActivity = null;
      history.pushState(null, "", "/");
      renderDashboard();
    });
    topActions.append(catalog);
  }
  const role = document.createElement("span");
  role.className = "muted";
  const roleNames = { admin: "Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂ", teacher: "СѓС‡РёС‚РµР»СЊ", student: "СѓС‡РµРЅРёРє" };
  role.textContent = `${state.user.display_name} В· ${roleNames[state.user.role] || state.user.role}`;
  const logout = document.createElement("button");
  logout.className = "ghost-button";
  logout.textContent = "Р’С‹Р№С‚Рё";
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
    admin.textContent = "РђРґРјРёРЅ";
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
      <h2>Р РµРіРёСЃС‚СЂР°С†РёСЏ</h2>
      <div class="role-choice" aria-label="Р РѕР»СЊ">
        <label>
          <input type="radio" name="role" value="student" checked />
          <span>РЈС‡РµРЅРёРє</span>
        </label>
        <label>
          <input type="radio" name="role" value="teacher" />
          <span>РЈС‡РёС‚РµР»СЊ</span>
        </label>
      </div>
      <label>
        РРјСЏ
        <input name="display_name" autocomplete="name" />
      </label>
      <label>
        Р›РѕРіРёРЅ
        <input name="username" autocomplete="username" />
      </label>
      <label>
        РџР°СЂРѕР»СЊ
        <input name="password" type="password" autocomplete="new-password" />
      </label>
      <label id="teacherCodeLabel">
        РљРѕРґ СѓС‡РёС‚РµР»СЏ
        <input name="teacher_code" placeholder="РЅР°РїСЂРёРјРµСЂ, TEACHER-2026" />
      </label>
      <button class="secondary-button" type="submit">РЎРѕР·РґР°С‚СЊ Р°РєРєР°СѓРЅС‚</button>
      <p class="muted">РЈС‡РµРЅРёРєРё СЂРµРіРёСЃС‚СЂРёСЂСѓСЋС‚СЃСЏ С‚РѕР»СЊРєРѕ РїРѕ РєРѕРґСѓ СѓС‡РёС‚РµР»СЏ.</p>
      <p class="muted warning-note">Р—Р°РїРёС€РёС‚Рµ РїР°СЂРѕР»СЊ Рё Р»РѕРіРёРЅ: РїР»Р°С‚С„РѕСЂРјР° РЅРµ СЃРѕР±РёСЂР°РµС‚ РџР”, РїРѕСЌС‚РѕРјСѓ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёРµ РїР°СЂРѕР»СЏ Р±СѓРґРµС‚ РЅРµРІРѕР·РјРѕР¶РЅС‹Рј РІ СЃР»СѓС‡Р°Рµ СѓС‚РµСЂРё.</p>
      <p class="error" id="registerError"></p>
    </form>
  `);
  document.querySelector("#teacherCodeLabel").insertAdjacentHTML("afterend", `
    <label class="consent-check">
      <input name="consent_accepted" type="checkbox" />
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
    `<button class="ghost-button" id="forgotPasswordLink" type="button">Р—Р°Р±С‹Р»Рё РїР°СЂРѕР»СЊ?</button>`
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
    error.textContent = "";
    try {
      const data = await api("/api/register", {
        method: "POST",
        body: JSON.stringify({
          display_name: form.get("display_name"),
          email: form.get("username"),
          password: form.get("password"),
          role: form.get("role"),
          teacher_code: form.get("teacher_code"),
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
        <h2>Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёРµ РїР°СЂРѕР»СЏ</h2>
        <label>
          Email
          <input name="email" autocomplete="email" />
        </label>
        <button class="primary-button" type="submit">РћС‚РїСЂР°РІРёС‚СЊ СЃСЃС‹Р»РєСѓ</button>
        <button class="ghost-button" id="backToLogin" type="button">РќР°Р·Р°Рґ РєРѕ РІС…РѕРґСѓ</button>
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
        <h2>РќРѕРІС‹Р№ РїР°СЂРѕР»СЊ</h2>
        <label>
          РќРѕРІС‹Р№ РїР°СЂРѕР»СЊ
          <input name="password" type="password" autocomplete="new-password" />
        </label>
        <label>
          РџРѕРІС‚РѕСЂ РїР°СЂРѕР»СЏ
          <input name="password_repeat" type="password" autocomplete="new-password" />
        </label>
        <button class="primary-button" type="submit">РЎРѕС…СЂР°РЅРёС‚СЊ РїР°СЂРѕР»СЊ</button>
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
      error.textContent = "РџР°СЂРѕР»Рё РЅРµ СЃРѕРІРїР°РґР°СЋС‚.";
      return;
    }
    try {
      await api("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      message.textContent = "РџР°СЂРѕР»СЊ РёР·РјРµРЅРµРЅ. РўРµРїРµСЂСЊ РјРѕР¶РЅРѕ РІРѕР№С‚Рё.";
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
        <p class="muted">Р—Р°РіСЂСѓР·РєР° РґРѕРєСѓРјРµРЅС‚Р°...</p>
      </article>
    </section>
  `;
  const panel = view.querySelector(".document-panel");
  try {
    const documentData = await api(endpoint);
    panel.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="eyebrow">РІРµСЂСЃРёСЏ ${documentData.version}</p>
          <h2>${documentData.title}</h2>
        </div>
        <button class="secondary-button" id="backFromDocument" type="button">РќР°Р·Р°Рґ</button>
      </div>
      <p class="muted">Р”Р°С‚Р° СЂРµРґР°РєС†РёРё: ${new Date(documentData.updated_at).toLocaleDateString()}</p>
      <div class="document-content">
        ${String(documentData.content || "").split("\n").map((line) => line.trim() ? `<p>${line}</p>` : "").join("")}
      </div>
      <p class="muted">РўРµРєСЃС‚ СЏРІР»СЏРµС‚СЃСЏ С€Р°Р±Р»РѕРЅРѕРј Рё РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ Р·Р°РјРµРЅРµРЅ РЅР° С„РёРЅР°Р»СЊРЅС‹Р№ СЋСЂРёРґРёС‡РµСЃРєРё РІС‹РІРµСЂРµРЅРЅС‹Р№ С‚РµРєСЃС‚ РїРµСЂРµРґ Р·Р°РїСѓСЃРєРѕРј СЂРµРіРёСЃС‚СЂР°С†РёРё СЂРµР°Р»СЊРЅС‹С… РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№.</p>
      ${legalLinks()}
    `;
    panel.querySelector("#backFromDocument").addEventListener("click", () => {
      if (history.length > 1) {
        history.back();
      } else if (state.user) {
        history.pushState(null, "", "/");
        renderDashboard();
      } else {
        history.pushState(null, "", "/login");
        renderLogin();
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
        <p class="eyebrow">РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ РґР°РЅРЅС‹Рµ</p>
        <h2>РџРµСЂРµРґ РЅР°С‡Р°Р»РѕРј СЂР°Р±РѕС‚С‹ РѕР·РЅР°РєРѕРјСЊС‚РµСЃСЊ СЃ РґРѕРєСѓРјРµРЅС‚Р°РјРё</h2>
        <p class="muted">РўРµРєСѓС‰Р°СЏ РІРµСЂСЃРёСЏ СЃРѕРіР»Р°СЃРёСЏ: ${required.document_version || ""}. Р’РµСЂСЃРёСЏ РїРѕР»РёС‚РёРєРё: ${required.privacy_policy_version || ""}.</p>
        ${legalLinks("legal-links consent-doc-links")}
        <label class="consent-check">
          <input name="consent_accepted" type="checkbox" />
          <span>
            РЇ РѕР·РЅР°РєРѕРјРёР»СЃСЏ/РѕР·РЅР°РєРѕРјРёР»Р°СЃСЊ СЃ РџРѕР»РёС‚РёРєРѕР№ РѕР±СЂР°Р±РѕС‚РєРё РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹С… РґР°РЅРЅС‹С… Рё РґР°СЋ СЃРѕРіР»Р°СЃРёРµ РЅР° РѕР±СЂР°Р±РѕС‚РєСѓ РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹С… РґР°РЅРЅС‹С….
          </span>
        </label>
        <button class="primary-button" type="submit">РџСЂРѕРґРѕР»Р¶РёС‚СЊ</button>
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
      error.textContent = "Р”Р»СЏ РїСЂРѕРґРѕР»Р¶РµРЅРёСЏ РЅРµРѕР±С…РѕРґРёРјРѕ РїСЂРёРЅСЏС‚СЊ РґРѕРєСѓРјРµРЅС‚С‹.";
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
  if (slug === "demo-mini") {
    state.currentActivity = slug;
    if (updateUrl) history.pushState(null, "", `/apps/mini/${slug}`);
    renderMiniActivity();
    return;
  }
  state.currentActivity = slug;
  state.bootstrap = await api(`/api/apps/${slug}/bootstrap`);
  state.mode = "rule";
  state.selectedCategory = null;
  state.selectedRuleIds = [];
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
  if (path.startsWith("/apps/mini/")) return "demo-mini";
  return null;
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
          <p class="eyebrow">${activity.kind === "mini" ? "РјРёРЅРё-РїСЂРёР»РѕР¶РµРЅРёРµ" : "СѓС‡РµР±РЅС‹Р№ РјРѕРґСѓР»СЊ"}</p>
          <h2>${activity.title || meta.title}</h2>
          <p>${activity.description || meta.description}</p>
        </div>
        <button class="primary-button open-activity" data-activity="${activity.slug}" type="button">
          ${activity.button || "РћС‚РєСЂС‹С‚СЊ"}
        </button>
      </article>
    `;
  }).join("");
  view.innerHTML = `
    <section class="catalog-page">
      <div class="catalog-head">
        <div>
          <p class="eyebrow">РєР°С‚Р°Р»РѕРі Р°РєС‚РёРІРЅРѕСЃС‚РµР№</p>
          <h2>Р’С‹Р±РµСЂРёС‚Рµ С‚СЂРµРЅР°Р¶РµСЂ</h2>
        </div>
        <div class="catalog-user">
          <strong>${state.user.display_name}</strong>
          <span class="muted">${state.user.role}</span>
        </div>
      </div>
      <div class="activity-grid">${cards}</div>
      ${state.user.role === "teacher" ? `<div class="catalog-actions"><button class="secondary-button" id="teacherCabinet" type="button">РљР°Р±РёРЅРµС‚ СѓС‡РёС‚РµР»СЏ</button></div>` : ""}
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
  view.innerHTML = `
    <section class="mini-page">
      <div class="panel-head">
        <div>
          <p class="eyebrow">HTML-РјРёРЅРё-РїСЂРёР»РѕР¶РµРЅРёРµ</p>
          <h2>Р”РµРјРѕ-Р°РєС‚РёРІРЅРѕСЃС‚СЊ</h2>
        </div>
        <button class="secondary-button" id="backToCatalogFromMini" type="button">РќР°Р·Р°Рґ РІ РєР°С‚Р°Р»РѕРі</button>
      </div>
      <iframe class="mini-frame" title="Р”РµРјРѕ-РјРёРЅРё-РїСЂРёР»РѕР¶РµРЅРёРµ" srcdoc="
        <style>
          body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f7fbff;color:#202124;display:grid;place-items:center;min-height:100vh}
          main{width:min(720px,calc(100vw - 32px));padding:28px;border:1px solid #d8dee8;border-radius:8px;background:white}
          h1{margin:0 0 12px;font-size:30px}
          button{height:42px;border:0;border-radius:7px;background:#2f7d5c;color:white;font-weight:700;padding:0 16px}
        </style>
        <main>
          <h1>РњРёРЅРё-РїСЂРёР»РѕР¶РµРЅРёРµ РїРѕРґРєР»СЋС‡РµРЅРѕ</h1>
          <p>Р­С‚Р° СЃС‚СЂР°РЅРёС†Р° Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ РІРЅСѓС‚СЂРё РѕР±С‰РµР№ РїР»Р°С‚С„РѕСЂРјРµРЅРЅРѕР№ РѕР±РµСЂС‚РєРё Рё РіРѕС‚РѕРІР° РґР»СЏ Р·Р°РјРµРЅС‹ РЅР° РёРіСЂСѓ, РєР°СЂС‚РѕС‡РєРё РёР»Рё РѕРґРЅРѕСЃС‚СЂР°РЅРёС‡РЅС‹Р№ С‚СЂРµРЅР°Р¶РµСЂ.</p>
          <button onclick='document.querySelector(&quot;output&quot;).textContent = &quot;Р“РѕС‚РѕРІРѕ&quot;'>РџСЂРѕРІРµСЂРёС‚СЊ</button>
          <output style='display:block;margin-top:14px'></output>
        </main>
      "></iframe>
    </section>
  `;
  view.querySelector("#backToCatalogFromMini").addEventListener("click", () => {
    state.currentActivity = null;
    history.pushState(null, "", "/");
    renderDashboard();
  });
}

function renderSidebar() {
  const activity = activityMeta[state.currentActivity] || activityMeta.ege9;
  const teacherCode = state.user.role === "teacher" && state.user.teacher_code
    ? `<span class="muted">РљРѕРґ РґР»СЏ СѓС‡РµРЅРёРєРѕРІ: <b>${state.user.teacher_code}</b></span>`
    : "";
  document.querySelector("#userBlock").innerHTML = `
    <span class="activity-badge">${activity.shortTitle}</span>
    <strong>${state.user.display_name}</strong>
    <span class="muted">${state.user.role === "admin" ? "РљР°Р±РёРЅРµС‚ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°" : state.user.role === "teacher" ? "РљР°Р±РёРЅРµС‚ СѓС‡РёС‚РµР»СЏ" : "РљР°Р±РёРЅРµС‚ СѓС‡РµРЅРёРєР°"}</span>
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
    <div class="stat"><b>${state.bootstrap.word_count}</b><span>СЃР»РѕРІ РІ Р±Р°Р·Рµ</span></div>
    <div class="stat"><b>${Object.values(state.bootstrap.rules).flat().length}</b><span>РїРѕРґРїСЂР°РІРёР»Р°</span></div>
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
      Р РµР¶РёРј РІ РєРѕРїРёР»РєРµ
      <select id="errorTrainingMode">
        <option value="cards" ${state.errorTrainingMode === "cards" ? "selected" : ""}>РљР°СЂС‚РѕС‡РєРё СЃ РІР°СЂРёР°РЅС‚Р°РјРё</option>
        <option value="word_letter" ${state.errorTrainingMode === "word_letter" ? "selected" : ""}>РЎР»РѕРІРѕ - Р±СѓРєРІР°</option>
      </select>
    </label>
  ` : "";
  setup.innerHTML = `
    <div class="setup-grid">
      <label>
        РљРѕР»РёС‡РµСЃС‚РІРѕ РІРѕРїСЂРѕСЃРѕРІ: <b id="questionCountValue">${state.questionCount}</b>
        <input id="questionCount" type="range" min="1" max="30" value="${state.questionCount}" />
      </label>
      <button class="primary-button" id="startPractice" type="button">РќР°С‡Р°С‚СЊ</button>
    </div>
    ${errorModeSelector}
    <label class="manual-toggle">
      <input id="manualInput" type="checkbox" ${state.manualInput || state.mode === "word_letter" ? "checked" : ""} ${state.mode === "word_letter" ? "disabled" : ""} />
      <span>РЎР°РјРѕСЃС‚РѕСЏС‚РµР»СЊРЅРѕ РІРІРѕРґРёС‚СЊ РѕС‚РІРµС‚ СЃ РєР»Р°РІРёР°С‚СѓСЂС‹</span>
    </label>
    <div class="practice-actions setup-actions">
      <button class="ghost-button" id="backToMenu" type="button">РќР°Р·Р°Рґ Рє РјРµРЅСЋ</button>
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
  setup.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedCategory = button.dataset.category;
      state.selectedRuleIds = [];
      ensureRuleSelection();
      renderSetup();
    });
  });
  setup.querySelector("#allRules")?.addEventListener("change", (event) => {
    state.selectedRuleIds = event.target.checked ? selectedRules().map((rule) => rule.rule_id) : [];
    renderSetup();
  });
  setup.querySelectorAll("[data-rule-id]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const next = selectedRuleSet();
      if (checkbox.checked) {
        next.add(checkbox.dataset.ruleId);
      } else {
        next.delete(checkbox.dataset.ruleId);
      }
      state.selectedRuleIds = [...next];
      renderSetup();
    });
  });
}

function renderRuleSelector() {
  ensureRuleSelection();
  const categoryButtons = ruleCategories()
    .map((category) => `
      <button class="category-pill ${category === state.selectedCategory ? "active" : ""}" data-category="${category}" type="button">
        <span>${category}</span>
        <b>${state.bootstrap.rules[category].reduce((sum, rule) => sum + rule.count, 0)}</b>
      </button>
    `)
    .join("");
  const selected = selectedRuleSet();
  const rules = selectedRules();
  const allSelected = rules.length > 0 && selected.size === rules.length;
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
            <span>Р’СЃРµ РїРѕРґРіСЂСѓРїРїС‹ РІРЅСѓС‚СЂРё РѕСЂС„РѕРіСЂР°РјРјС‹</span>
            <b>${rules.reduce((sum, rule) => sum + rule.count, 0)}</b>
          </label>
          ${ruleOptions}
        </div>
        <div class="selected-rule">
          <b>${selectedCount}</b>
          <span>СЃР»РѕРІ РІ РІС‹Р±СЂР°РЅРЅС‹С… РїРѕРґРіСЂСѓРїРїР°С…</span>
        </div>
      </div>
    </section>
  `;
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
  return String(value || "").trim().toLowerCase().replace("РµМ€", "С‘").slice(0, 1);
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
        <span>РЎР»РѕРІРѕ ${state.currentQuestionIndex + 1} РёР· ${state.currentSession.questions.length}</span>
        <span>${question.rule_name}</span>
      </div>
      <div class="word-prompt">${question.prompt}</div>
      <div class="letter-input-row">
        <input id="liveAnswer" maxlength="1" autocomplete="off" inputmode="text" aria-label="Р’РІРµРґРёС‚Рµ Р±СѓРєРІСѓ" />
        <button class="primary-button" id="checkLiveAnswer" type="button">РџСЂРѕРІРµСЂРёС‚СЊ</button>
      </div>
      <div id="liveFeedback">${feedback || ""}</div>
    </article>
    <div class="practice-actions">
      <button class="ghost-button" id="backPractice" type="button">РќР°Р·Р°Рґ</button>
      <button class="ghost-button" id="cancelPractice" type="button">РЎР±СЂРѕСЃРёС‚СЊ</button>
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
        <b>РќРµРІРµСЂРЅРѕ. РџСЂР°РІРёР»СЊРЅРѕ: ${item.correct_answer}</b>
        <p>${item.correct_spelling || ""}</p>
        <p class="muted">${item.explanation || ""}</p>
        <button class="secondary-button" id="nextAfterRule" type="button">Р”Р°Р»СЊС€Рµ</button>
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
      <button class="ghost-button" id="backPractice" type="button">РќР°Р·Р°Рґ</button>
      <button class="ghost-button" id="cancelPractice" type="button">РЎР±СЂРѕСЃРёС‚СЊ</button>
      <button class="primary-button" id="submitPractice" type="button">РџСЂРѕРІРµСЂРёС‚СЊ</button>
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
          <div class="question-head"><span>Р’РѕРїСЂРѕСЃ ${index + 1}</span><span>${question.rule_name}</span></div>
          <div>${question.prompt}</div>
          ${question.rows.map((row, rowIndex) => `
            <div class="line-row static-line-row">
              <b>${rowIndex + 1}</b>
              <span class="line-words">${row.map((word) => `<span>${word}</span>`).join("")}</span>
            </div>
          `).join("")}
          <label class="answer-input-label">
            РћС‚РІРµС‚ РІСЂСѓС‡РЅСѓСЋ
            <input data-manual-answer="${question.question_id}" data-kind="line" placeholder="РЅР°РїСЂРёРјРµСЂ, 135" value="${state.answers[question.question_id] || ""}" />
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
        <div class="question-head"><span>Р’РѕРїСЂРѕСЃ ${index + 1}</span><span>${question.rule_name}</span></div>
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
        <div class="question-head"><span>Р’РѕРїСЂРѕСЃ ${index + 1}</span><span>${question.rule_name}</span></div>
        <div class="word-prompt">${question.prompt}</div>
        <label class="answer-input-label">
          Р’РІРµРґРёС‚Рµ Р±СѓРєРІСѓ
          <input data-manual-answer="${question.question_id}" maxlength="1" autocomplete="off" value="${state.answers[question.question_id] || ""}" />
        </label>
      </article>
    `;
  }
  return `
    <article class="question">
      <div class="question-head"><span>Р’РѕРїСЂРѕСЃ ${index + 1}</span><span>${question.rule_name}</span></div>
      <div class="word-prompt">${question.prompt}</div>
      <div class="choice-row">${choices}</div>
    </article>
  `;
}

async function submitPractice() {
  const total = state.currentSession.questions.length;
  const answered = state.currentSession.questions.every((question) => String(state.answers[question.question_id] || "").trim());
  if (Object.keys(state.answers).length < total || !answered) {
    alert("РћС‚РІРµС‚СЊС‚Рµ РЅР° РІСЃРµ РІРѕРїСЂРѕСЃС‹ РїРµСЂРµРґ РїСЂРѕРІРµСЂРєРѕР№.");
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
    <div class="stat"><b>${data.correct}/${data.total}</b><span>${pct(data.correct, data.total)} РїСЂР°РІРёР»СЊРЅС‹С… РѕС‚РІРµС‚РѕРІ</span></div>
    <div class="result-list">
      ${data.results.map((item, index) => `
        <div class="result-item ${item.is_correct ? "ok" : "bad"}">
          <b>${index + 1}. ${item.is_correct ? "Р’РµСЂРЅРѕ" : "РџРѕРІС‚РѕСЂРёРј РµС‰Рµ"}</b>
          <p>РћС‚РІРµС‚: ${item.given_answer || "вЂ”"} В· РїСЂР°РІРёР»СЊРЅРѕ: ${item.correct_answer}</p>
          <p>${item.correct_spelling || ""}</p>
          ${item.is_correct ? "" : `<p class="muted">${item.explanation || ""}</p>`}
        </div>
      `).join("")}
    </div>
    <div class="practice-actions">
      <button class="ghost-button" type="button" id="backFromResults">РќР°Р·Р°Рґ</button>
      <button class="primary-button" type="button" id="againButton">РќРѕРІР°СЏ С‚СЂРµРЅРёСЂРѕРІРєР°</button>
    </div>
  `;
  result.querySelector("#backFromResults").addEventListener("click", backToMenu);
  result.querySelector("#againButton").addEventListener("click", renderMode);
}

function renderTeacherStudentCards(students) {
  if (!students.length) {
    return `<p class="muted">РџРѕРєР° РЅРµС‚ СѓС‡РµРЅРёРєРѕРІ, Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅРЅС‹С… РїРѕ РІР°С€РµРјСѓ РєРѕРґСѓ.</p>`;
  }
  return students.map((student) => {
    const teacher = { consent_accepted: student.consent_accepted };
    const topErrors = student.top_errors.length
      ? student.top_errors.map((item) => `<li>${item.rule_name}: ${item.errors}</li>`).join("")
      : "<li>РѕС€РёР±РѕРє РїРѕРєР° РЅРµС‚</li>";
    const pending = student.not_worked_out.length
      ? student.not_worked_out.slice(0, 5).map((item) => `<li>${item.correct_spelling || item.word}</li>`).join("")
      : "<li>РѕС‡РµСЂРµРґСЊ РїРѕРІС‚РѕСЂРµРЅРёСЏ РїСѓСЃС‚Р°</li>";
    const errorBank = student.error_bank.length
      ? student.error_bank.slice(0, 6).map((item) => `<li>${item.correct_spelling || item.word}</li>`).join("")
      : "<li>РєРѕРїРёР»РєР° РїСѓСЃС‚Р°</li>";
    return `
      <article class="student-card">
        <div class="student-card-head">
          <div>
            <b>${student.display_name}</b>
            <span class="muted">@${student.username}</span>
          </div>
          <div class="mini-stat"><b>${pct(student.correct, student.total)}</b><span>С‚РѕС‡РЅРѕСЃС‚СЊ</span></div>
        </div>
        <div class="teacher-metrics">
          <div class="stat"><b>${teacher.consent_accepted ? "РґР°" : "РЅРµС‚"}</b><span>СЃРѕРіР»Р°СЃРёРµ РїСЂРёРЅСЏС‚Рѕ</span></div>
          <div class="stat"><b>${student.total}</b><span>Р·Р°РґР°РЅРёР№ СЂРµС€РµРЅРѕ</span></div>
          <div class="stat"><b>${student.untouched}</b><span>СЃР»РѕРІ РЅРµ Р·Р°С‚СЂРѕРЅСѓС‚Рѕ</span></div>
          <div class="stat"><b>${student.error_bank.length}</b><span>РІ РєРѕРїРёР»РєРµ РѕС€РёР±РѕРє</span></div>
        </div>
        <div class="student-lists">
          <div><h4>Р‘РѕР»СЊС€Рµ РѕС€РёР±РѕРє</h4><ul>${topErrors}</ul></div>
          <div><h4>РќРµ РѕС‚СЂР°Р±РѕС‚Р°РЅРѕ</h4><ul>${pending}</ul></div>
          <div><h4>РљРѕРїРёР»РєР°</h4><ul>${errorBank}</ul></div>
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
  panel.innerHTML = `<p class="muted">Р—Р°РіСЂСѓР¶Р°СЋ Р±С‹СЃС‚СЂСѓСЋ СЃС‚Р°С‚РёСЃС‚РёРєСѓ...</p>`;
  main.insertBefore(panel, document.querySelector("#setupView"));
  try {
    const data = await api("/api/progress");
    panel.innerHTML = `
      <div class="section-head">
        <div>
          <p class="eyebrow">Р±С‹СЃС‚СЂР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР°</p>
          <h3>РЈС‡РµРЅРёРєРё Рё Р·РѕРЅС‹ РѕС‚СЂР°Р±РѕС‚РєРё</h3>
        </div>
        <div class="button-row">
          <button class="secondary-button" id="makeTestButton" type="button">РЎРѕСЃС‚Р°РІРёС‚СЊ С‚РµСЃС‚</button>
          <button class="secondary-button" id="downloadStudents" type="button">РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ</button>
          <button class="secondary-button" id="openFullProgress" type="button">РџРѕР»РЅР°СЏ Р°РєС‚РёРІРЅРѕСЃС‚СЊ</button>
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
      <td>${row.given_answer || "вЂ”"} / ${row.correct_answer}</td>
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
      <td>${row.is_correct ? "РґР°" : "РЅРµС‚"}</td>
    </tr>
  `).join("");
  const teacherOverview = state.user.role === "teacher" && data.teacher_dashboard
    ? `<h3>Р‘С‹СЃС‚СЂР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР° СѓС‡РµРЅРёРєРѕРІ</h3><div class="student-card-grid">${renderTeacherStudentCards(data.teacher_dashboard.students)}</div>`
    : "";
  backdrop.innerHTML = `
    <section class="progress-modal">
      <div class="panel-head">
        <div><p class="eyebrow">РїСЂРѕРіСЂРµСЃСЃ</p><h2>${state.user.role === "teacher" ? "Р–СѓСЂРЅР°Р» РєР»Р°СЃСЃР°" : "РњРѕРё СЂРµР·СѓР»СЊС‚Р°С‚С‹"}</h2></div>
        <button class="secondary-button" id="closeProgress" type="button">Р—Р°РєСЂС‹С‚СЊ</button>
      </div>
      <div class="progress-grid">
        <div class="stat"><b>${summary.total}</b><span>РѕС‚РІРµС‚РѕРІ</span></div>
        <div class="stat"><b>${summary.correct}</b><span>РІРµСЂРЅРѕ</span></div>
        <div class="stat"><b>${pct(summary.correct, summary.total)}</b><span>С‚РѕС‡РЅРѕСЃС‚СЊ</span></div>
      </div>
      ${state.user.role !== "teacher" ? `
        <div class="progress-grid">
          <div class="stat"><b>${data.due_reviews}</b><span>СЃР»РѕРІ РІ РѕС‡РµСЂРµРґРё РїРѕРІС‚РѕСЂРµРЅРёСЏ</span></div>
          <div class="stat"><b>${data.error_bank_count}</b><span>СЃР»РѕРІ РІ РєРѕРїРёР»РєРµ РѕС€РёР±РѕРє</span></div>
        </div>
      ` : ""}
      ${teacherOverview}
      ${state.user.role === "teacher" ? `<div class="table-head"><h3>РЈС‡РµРЅРёРєРё</h3>${downloadButton("students", "РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ")}</div><table class="table"><tr><th>РРјСЏ</th><th>РћС‚РІРµС‚РѕРІ</th><th>РўРѕС‡РЅРѕСЃС‚СЊ</th></tr>${studentRows}</table>` : ""}
      <div class="table-head"><h3>Р“СЂСѓРїРїС‹</h3>${downloadButton("categories", "РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ")}</div>
      <table class="table"><tr><th>Р“СЂСѓРїРїР°</th><th>РћС‚РІРµС‚РѕРІ</th><th>РўРѕС‡РЅРѕСЃС‚СЊ</th></tr>${categoryRows}</table>
      <div class="table-head"><h3>РџРѕРґРіСЂСѓРїРїС‹</h3>${downloadButton("rules", "РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ")}</div>
      <table class="table"><tr><th>Р“СЂСѓРїРїР°</th><th>РџРѕРґРіСЂСѓРїРїР°</th><th>РћС‚РІРµС‚РѕРІ</th><th>РўРѕС‡РЅРѕСЃС‚СЊ</th></tr>${ruleRows}</table>
      <details class="activity-details">
        <summary>Р Р°Р·РІРµСЂРЅСѓС‚СЊ РїРѕР»РЅСѓСЋ Р°РєС‚РёРІРЅРѕСЃС‚СЊ</summary>
        <div class="table-head"><h3>Р РµС€РµРЅРѕ РІРµСЂРЅРѕ</h3>${downloadButton("correct", "РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ")}</div>
        <table class="table"><tr><th>РЈС‡РµРЅРёРє</th><th>Р“СЂСѓРїРїР°</th><th>РџРѕРґРіСЂСѓРїРїР°</th><th>Р—Р°РґР°РЅРёРµ</th><th>РћС‚РІРµС‚</th></tr>${answerListRows(data.correct_attempts)}</table>
        <div class="table-head"><h3>Р РµС€РµРЅРѕ РЅРµРІРµСЂРЅРѕ</h3>${downloadButton("incorrect", "РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ")}</div>
        <table class="table"><tr><th>РЈС‡РµРЅРёРє</th><th>Р“СЂСѓРїРїР°</th><th>РџРѕРґРіСЂСѓРїРїР°</th><th>Р—Р°РґР°РЅРёРµ</th><th>РћС‚РІРµС‚</th></tr>${answerListRows(data.incorrect_attempts)}</table>
        <div class="table-head"><h3>РџРѕСЃР»РµРґРЅРёРµ РїРѕРїС‹С‚РєРё</h3>${downloadButton("recent", "РЎРєР°С‡Р°С‚СЊ СЃС‚Р°С‚РёСЃС‚РёРєСѓ")}</div>
        <table class="table"><tr><th>Р”Р°С‚Р°</th><th>РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ</th><th>Р“СЂСѓРїРїР°</th><th>РџРѕРґРіСЂСѓРїРїР°</th><th>Р—Р°РґР°РЅРёРµ</th><th>РћС‚РІРµС‚</th><th>Р’РµСЂРЅРѕ</th></tr>${recentRows}</table>
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
        <div><p class="eyebrow">С‚РµСЃС‚</p><h2>РЎРѕСЃС‚Р°РІРёС‚СЊ С‚РµСЃС‚</h2></div>
        <button class="secondary-button" id="closeTestComposer" type="button">Р—Р°РєСЂС‹С‚СЊ</button>
      </div>
      <div class="setup-grid">
        <label>
          Р РµР¶РёРј
          <select id="testMode">
            <option value="rule">Р’С‹Р±СЂР°РЅРЅС‹Рµ С‚РµРјС‹</option>
            <option value="mix">РњРёРєСЃ</option>
            <option value="errors">РљРѕРїРёР»РєР° РѕС€РёР±РѕРє</option>
            <option value="line">РЎС‚СЂРѕРєРё</option>
          </select>
        </label>
        <label>
          РљРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°РґР°РЅРёР№
          <input id="testCount" type="number" min="1" max="60" value="${state.questionCount}" />
        </label>
      </div>
      <label class="manual-toggle">
        <input id="testIncludeErrors" type="checkbox" />
        <span>Р”РѕР±Р°РІРёС‚СЊ СЃР»РѕРІР° РёР· РєРѕРїРёР»РєРё РѕС€РёР±РѕРє РєР»Р°СЃСЃР°</span>
      </label>
      <div id="testRuleSelector">${ruleSelector}</div>
      <p class="error" id="testComposerError"></p>
      <div class="practice-actions">
        <button class="primary-button" id="downloadTest" type="button">РЎРєР°С‡Р°С‚СЊ .txt</button>
      </div>
    </section>
  `;
  document.body.append(backdrop);
  const refreshRules = () => {
    backdrop.querySelector("#testRuleSelector").classList.toggle("hidden", backdrop.querySelector("#testMode").value !== "rule");
  };
  backdrop.querySelector("#closeTestComposer").addEventListener("click", () => backdrop.remove());
  backdrop.querySelector("#testMode").addEventListener("change", refreshRules);
  backdrop.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedCategory = button.dataset.category;
      state.selectedRuleIds = [];
      ensureRuleSelection();
      backdrop.remove();
      showTestComposer();
    });
  });
  backdrop.querySelector("#allRules")?.addEventListener("change", (event) => {
    state.selectedRuleIds = event.target.checked ? selectedRules().map((rule) => rule.rule_id) : [];
    backdrop.remove();
    showTestComposer();
  });
  backdrop.querySelectorAll("[data-rule-id]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const next = selectedRuleSet();
      checkbox.checked ? next.add(checkbox.dataset.ruleId) : next.delete(checkbox.dataset.ruleId);
      state.selectedRuleIds = [...next];
    });
  });
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
    ? `РґР°${row.consent_accepted_at ? `, ${new Date(row.consent_accepted_at).toLocaleDateString()}` : ""}`
    : "РЅРµС‚";
  const teacherCards = data.teachers.map((teacher) => {
    const students = teacher.students_list.length
      ? teacher.students_list.map((student) => `
        <tr>
          <td>${student.display_name}</td>
          <td>${student.username}<br><span class="muted">СЃРѕРіР»Р°СЃРёРµ: ${consentLabel(student)}</span></td>
          <td>${student.attempts}</td>
          <td>${pct(student.correct, student.attempts)}</td>
          <td>
            <button class="ghost-button reset-password" data-user-id="${student.user_id}" data-username="${student.username}" type="button">
              ${student.password_reset_required ? "РћР¶РёРґР°РµС‚ РЅРѕРІС‹Р№ РїР°СЂРѕР»СЊ" : "РЎР±СЂРѕСЃРёС‚СЊ РїР°СЂРѕР»СЊ"}
            </button>
          </td>
        </tr>
      `).join("")
      : `<tr><td colspan="5">РЈС‡РµРЅРёРєРѕРІ РїРѕРєР° РЅРµС‚</td></tr>`;
    return `
      <article class="admin-card">
        <div class="student-card-head">
          <div>
            <b>${teacher.display_name}</b>
            <span class="muted">@${teacher.username} В· РєРѕРґ ${teacher.teacher_code || "РЅРµ Р·Р°РґР°РЅ"}</span>
          </div>
          <div class="button-row">
            <div class="mini-stat"><b>${teacher.students}</b><span>СѓС‡РµРЅРёРєРѕРІ</span></div>
            <button class="ghost-button reset-password" data-user-id="${teacher.user_id}" data-username="${teacher.username}" type="button">
              ${teacher.password_reset_required ? "РћР¶РёРґР°РµС‚ РЅРѕРІС‹Р№ РїР°СЂРѕР»СЊ" : "РЎР±СЂРѕСЃРёС‚СЊ РїР°СЂРѕР»СЊ"}
            </button>
          </div>
        </div>
        <div class="teacher-metrics">
          <div class="stat"><b>${teacher.attempts}</b><span>РѕС‚РІРµС‚РѕРІ</span></div>
          <div class="stat"><b>${pct(teacher.correct, teacher.attempts)}</b><span>С‚РѕС‡РЅРѕСЃС‚СЊ</span></div>
        </div>
        <table class="table"><tr><th>РЈС‡РµРЅРёРє</th><th>Р›РѕРіРёРЅ</th><th>РћС‚РІРµС‚РѕРІ</th><th>РўРѕС‡РЅРѕСЃС‚СЊ</th><th>РџР°СЂРѕР»СЊ</th></tr>${students}</table>
      </article>
    `;
  }).join("");
  return `
    <div class="panel-head">
      <div><p class="eyebrow">Р°РґРјРёРЅ</p><h2>РћР±Р·РѕСЂ РїР»Р°С‚С„РѕСЂРјС‹</h2></div>
      ${closeButton}
    </div>
    <div class="progress-grid">
      <div class="stat"><b>${platform.total}</b><span>РѕС‚РІРµС‚РѕРІ РІСЃРµРіРѕ</span></div>
      <div class="stat"><b>${platform.active_users}</b><span>Р°РєС‚РёРІРЅС‹С… РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№</span></div>
      <div class="stat"><b>${pct(platform.correct, platform.total)}</b><span>РѕР±С‰Р°СЏ С‚РѕС‡РЅРѕСЃС‚СЊ</span></div>
    </div>
    <div class="admin-list">${teacherCards}</div>
  `;
}

async function renderAdminDashboard() {
  view.innerHTML = `
    <section class="workspace admin-workspace">
      <section class="main-panel admin-page">
        <p class="muted">Р—Р°РіСЂСѓР¶Р°СЋ Р°РґРјРёРЅ-РїР°РЅРµР»СЊ...</p>
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
      ${renderAdminContent(data, `<button class="secondary-button" id="closeAdmin" type="button">Р—Р°РєСЂС‹С‚СЊ</button>`)}
    </section>
  `;
  document.body.append(backdrop);
  backdrop.querySelector("#closeAdmin").addEventListener("click", () => backdrop.remove());
  bindAdminActions(backdrop);
}

function bindAdminActions(root) {
  root.querySelectorAll(".reset-password").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm(`РЎР±СЂРѕСЃРёС‚СЊ РїР°СЂРѕР»СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ ${button.dataset.username}?`)) return;
      button.disabled = true;
      try {
        await api("/api/admin/reset-password", {
          method: "POST",
          body: JSON.stringify({ user_id: button.dataset.userId }),
        });
        button.textContent = "РћР¶РёРґР°РµС‚ РЅРѕРІС‹Р№ РїР°СЂРѕР»СЊ";
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


