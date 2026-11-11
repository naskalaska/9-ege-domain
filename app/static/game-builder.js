async function setupGameBuilder() {
  const builder = view.querySelector("#gameBuilder");
  if (!builder) return;

  const sourceSelect = builder.querySelector("#gameSourceSelect");
  const mechanicSelect = builder.querySelector("[data-game-mechanic-select]");
  const rulePicker = builder.querySelector("#gameRulePicker");
  const result = builder.querySelector("#gameBuilderResult");
  const link = builder.querySelector("#gameBuilderLink");
  let sources = [];
  let mechanics = [];
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
    const mechanic = mechanicSelect.value;
    return Object.fromEntries(Object.entries(source?.rules || {})
      .map(([category, rules]) => [category, rules
        .filter((rule) => Number(rule.mechanic_counts?.[mechanic] || 0) > 0)
        .map((rule) => ({ ...rule, count: Number(rule.mechanic_counts?.[mechanic] || 0) }))])
      .filter(([, rules]) => rules.length));
  }

  function updateMechanicCompatibility() {
    const note = builder.querySelector("[data-game-compatibility]");
    const submit = builder.querySelector("#baseGameForm button[type='submit']");
    const mechanic = mechanics.find((item) => item.id === mechanicSelect.value);
    const incompatible = !sourceSelect.value || !(mechanic?.compatible_sources || []).includes(sourceSelect.value);
    if (note) note.textContent = mechanicSelect.value === "autumn-leaves"
        ? "В «Осени» варианты ответа берутся из набора: буквы, части слова или варианты написания. Выбранная механика применяется и при загрузке своего JSON."
        : mechanicSelect.value === "butterflies"
        ? "В «Бабочках» ученик самостоятельно вписывает букву, часть слова или вариант написания."
        : "Показаны только базы, совместимые с выбранной механикой.";
    if (submit) submit.disabled = incompatible;
  }

  function fillSources() {
    const mechanic = mechanics.find((item) => item.id === mechanicSelect.value);
    const compatible = new Set(mechanic?.compatible_sources || []);
    const visibleSources = sources.filter((source) => compatible.has(source.id) &&
      Object.values(source.rules || {}).flat().some((rule) => Number(rule.mechanic_counts?.[mechanicSelect.value] || 0) > 0));
    sourceSelect.innerHTML = visibleSources
      .map((source) => `<option value="${escapeHtml(source.id)}">${escapeHtml(source.title)}</option>`)
      .join("");
    selectedGameRuleIds = new Set();
    fillRules();
    updateMechanicCompatibility();
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
              <b>${rule.count}</b>${state.bootstrap.rule_progress?.[rule.rule_id] ? `<small>${state.bootstrap.rule_progress[rule.rule_id].solved}/${state.bootstrap.rule_progress[rule.rule_id].total} · ${pct(state.bootstrap.rule_progress[rule.rule_id].solved,state.bootstrap.rule_progress[rule.rule_id].total)}</small>` : ''}
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
    mechanics = data.mechanics || [];
    mechanicSelect.innerHTML = mechanics
      .map((mechanic) => `<option value="${escapeHtml(mechanic.id)}" ${mechanic.available ? "" : "disabled"}>${escapeHtml(mechanic.title)}${mechanic.available ? "" : " — скоро"}</option>`)
      .join("");
    fillSources();
  } catch (error) {
    showBuilderError("#baseGameError", error.message);
  }

  sourceSelect.addEventListener("change", () => {
    selectedGameRuleIds = new Set();
    fillRules();
    updateMechanicCompatibility();
  });
  mechanicSelect.addEventListener("change", fillSources);

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
      if (mechanicSelect.value === "autumn-leaves") payload.mechanic = "autumn-leaves";
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
