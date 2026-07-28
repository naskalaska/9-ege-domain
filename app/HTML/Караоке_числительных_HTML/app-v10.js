(() => {
  const { lessons, readings } = window.KARAOKE_DATA;
  const demoLimit = Number(window.KARAOKE_DEMO_LIMIT || 0);
  const practiceSets = (() => {
    const source = window.KARAOKE_PRACTICE;
    if (!demoLimit) return source;
    const entries = Object.entries(source);
    const demo = Object.fromEntries(entries.map(([key]) => [key, []]));
    let added = 0;
    for (let row = 0; added < demoLimit; row += 1) {
      let found = false;
      entries.forEach(([key, items]) => {
        if (added < demoLimit && items[row]) {
          demo[key].push(items[row]);
          added += 1;
          found = true;
        }
      });
      if (!found) break;
    }
    return demo;
  })();
  const theory = window.KARAOKE_THEORY;
  const readingAnswers = window.KARAOKE_READING_ANSWERS;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const normalize = (value) => value.trim().toLowerCase().replaceAll("ё", "е").replace(/[.,!?;:—–-]/g, " ").replace(/\s+/g, " ");
  const storageKey = "karaoke-numerals-v4";
  const soundKey = "karaoke-numerals-sound";
  let soundEnabled = localStorage.getItem(soundKey) !== "off";
  let audioContext = null;
  const totalPracticeItems = Object.values(practiceSets).reduce((sum, items) => sum + items.length, 0);
  const totalTextFields = readings.reduce((sum, item) => sum + (readingAnswers[item.id] || []).length, 0);

  function tone(frequency, duration = .09, type = "sine", volume = .055, delay = 0) {
    if (!soundEnabled) return;
    try {
      audioContext ||= new (window.AudioContext || window.webkitAudioContext)();
      const start = audioContext.currentTime + delay;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = type; oscillator.frequency.setValueAtTime(frequency, start);
      gain.gain.setValueAtTime(.0001, start); gain.gain.exponentialRampToValueAtTime(volume, start + .012); gain.gain.exponentialRampToValueAtTime(.0001, start + duration);
      oscillator.connect(gain); gain.connect(audioContext.destination); oscillator.start(start); oscillator.stop(start + duration + .02);
    } catch {}
  }
  function playSound(kind) {
    if (kind === "countdown") tone(620, .07, "sine", .045);
    if (kind === "slide") { tone(380, .07, "sine", .04); tone(610, .09, "sine", .045, .065); }
    if (kind === "correct") { tone(523, .08, "sine", .05); tone(659, .1, "sine", .05, .075); tone(784, .13, "sine", .05, .15); }
    if (kind === "wrong") { tone(190, .18, "sawtooth", .035); tone(145, .2, "sawtooth", .028, .12); }
  }

  const lessonMeta = {
    simple: { formula: "5–20, 30 + свои модели 1–4", norm: "Сначала выберите модель в карусели: формы один, два, три и четыре нельзя выводить из модели пяти.", colors: ["#b9f34a", "#eefbd4", "#4c7d20"] },
    special: { formula: "40 / 90 / 100 → по две формы", norm: "Самостоятельное сто: только сто и ста. В 200–900 часть -сто- склоняется иначе.", colors: ["#ff9a55", "#fff0dc", "#a9581d"] },
    "one-half": { formula: "полтора / полторы / полтораста", norm: "Две модели в одном разделе: полтора / полторы → полутора; полтораста → полутораста.", colors: ["#9677f2", "#eee8ff", "#5e49a9"] },
    complex: { formula: "обе части изменяются", norm: "50–80 и каждая сотня имеют собственную схему: пролистайте все четыре модели.", colors: ["#74c9ff", "#e3f4ff", "#3277a3"] },
    compound: { formula: "меняем каждый разряд", norm: "К трёмстам двадцати четырём; с тремястами двадцатью четырьмя.", colors: ["#b9f34a", "#edf9d5", "#4c7d20"] },
    fractions: { formula: "целая + десятых / сотых", norm: "Числитель — количественное, знаменатель — порядковое.", colors: ["#ff9a55", "#fff0dc", "#a9581d"] },
    ordinals: { formula: "меняется только финал", norm: "В две тысячи двадцать четвёртом году: изменяется только «четвёртом».", colors: ["#9677f2", "#eee8ff", "#5e49a9"] },
    collective: { formula: "двое / трое как группа", norm: "Двое авторов, но две певицы: со взрослыми женщинами — количественное.", colors: ["#ff765f", "#ffe7e1", "#ad4938"] }
  };

  const drawnMemoArt = {
    simple: ["memo-simple-5-20.webp", "memo-simple-one.webp", "memo-simple-two.webp", "memo-simple-three.webp", "memo-simple-four.webp"],
    special: ["memo-special-40.webp", "memo-special-90.webp", "memo-special-100.webp"],
    complex: ["memo-complex-50-80.webp", "memo-complex-200.webp", "memo-complex-300-400.webp", "memo-complex-500-900.webp"],
    "one-half": ["memo-one-half.webp", "memo-one-fifty.webp"], compound: ["memo-compound.webp"],
    fractions: ["memo-fractions.webp"], ordinals: ["memo-ordinals.webp"], collective: ["memo-collective.webp"]
  };

  let progress = { lessons: [], practices: {}, readings: {}, readingChecks: {} };
  try { progress = { ...progress, ...JSON.parse(localStorage.getItem(storageKey) || "{}") }; } catch {}
  progress.lessons = [...new Set((progress.lessons || []).filter((id) => id !== "one-fifty" && lessons.some((lesson) => lesson.id === id)))];
  if (progress.practices?.["one-fifty"]?.length) {
    progress.practices["one-half"] = [...new Set([...(progress.practices["one-half"] || []), ...progress.practices["one-fifty"].map((index) => index + 10)])];
    delete progress.practices["one-fifty"];
  }

  const state = { screen: "theory", lesson: 0, model: 0, karaokeExample: 0, posterLine: 0, line: 0, practice: 0, reading: 0, topic: "Все", phase: "idle", char: 0, countdown: 5, timer: null, paused: false, panelFocus: "memo" };

  const asLine = (line) => Array.isArray(line) ? { caseName: line[0], cue: line[1], form: line[2] } : line;
  const baseModel = (lesson) => ({ label: lesson.title, digit: "", title: lesson.short, principle: theory.principles[lesson.id] || lessonMeta[lesson.id].formula.toUpperCase(), formula: lessonMeta[lesson.id].formula, rule: lesson.rule, tips: lesson.tips, lines: lesson.lines.map(asLine) });
  const modelsFor = (lesson) => (theory[lesson.id]?.models || [baseModel(lesson)]).map((model) => ({ ...model, lines: model.lines.map(asLine) }));
  const currentModel = () => modelsFor(lessons[state.lesson])[state.model];
  const karaokeSetsFor = (lesson) => theory.karaoke[lesson.id].map((set) => ({ ...set, lines: set.lines.map(asLine) }));
  const currentKaraoke = () => karaokeSetsFor(lessons[state.lesson])[Math.min(state.karaokeExample, karaokeSetsFor(lessons[state.lesson]).length - 1)];

  function save() { localStorage.setItem(storageKey, JSON.stringify(progress)); updateGlobalProgress(); }
  function countCorrectTextFields() {
    return readings.reduce((total, item) => {
      const saved = progress.readings[item.id] || []; const expected = readingAnswers[item.id] || [];
      return total + expected.reduce((count, answer, index) => count + (saved[index]?.trim() && answer.split("|").map(normalize).includes(normalize(saved[index])) ? 1 : 0), 0);
    }, 0);
  }
  function updateGlobalProgress() {
    const lessonDone = progress.lessons.length;
    const practiceCorrect = lessons.reduce((sum, lesson) => sum + (progress.practices[lesson.id] || []).filter((index) => index < (practiceSets[lesson.id] || []).length).length, 0);
    const fieldCorrect = countCorrectTextFields();
    const readingDone = Object.values(progress.readingChecks || {}).filter(Boolean).length;
    const percent = Math.round((lessonDone + practiceCorrect + fieldCorrect) / (lessons.length + totalPracticeItems + totalTextFields) * 100);
    $("#globalProgress").textContent = `${percent}%`;
    $("#lessonBar").style.width = `${lessonDone / lessons.length * 100}%`;
    $("#lessonCount").textContent = `${lessonDone} из ${lessons.length} разделов`;
    $("#readingBar").style.width = `${readingDone / readings.length * 100}%`;
    $("#readingCount").textContent = `${readingDone} из ${readings.length} текстов`;
    if ($("#readingTotal")) $("#readingTotal").textContent = readings.length;
    $("#statsPercent").textContent = `${percent}%`; $("#statsRing").style.setProperty("--progress", `${percent}%`);
    $("#statsLessons").textContent = `${lessonDone} / ${lessons.length}`; $("#statsLessonsBar").style.width = `${lessonDone / lessons.length * 100}%`;
    $("#statsPractice").textContent = `${practiceCorrect} / ${totalPracticeItems}`; $("#statsPracticeBar").style.width = `${practiceCorrect / totalPracticeItems * 100}%`;
    $("#statsFields").textContent = `${fieldCorrect} / ${totalTextFields}`; $("#statsFieldsBar").style.width = `${fieldCorrect / totalTextFields * 100}%`;
    $("#statsTexts").textContent = `${readingDone} / ${readings.length}`; $("#statsTextsBar").style.width = `${readingDone / readings.length * 100}%`;
  }

  function setScreen(screen) {
    if (demoLimit && screen === "reading") {
      window.alert("Тексты входят в полную версию «Караоке числительных». В демо доступны памятки, караоке и 20 упражнений.");
      return;
    }
    stopKaraoke(); state.screen = screen;
    $("#theoryScreen").hidden = screen !== "theory"; $("#readingScreen").hidden = screen !== "reading";
    $$('[data-screen]').forEach((button) => button.classList.toggle("active", button.dataset.screen === screen));
    if (screen === "theory") renderTheory(); else renderReading();
  }
  $$('[data-screen]').forEach((button) => button.addEventListener("click", () => setScreen(button.dataset.screen)));
  function renderSoundToggle() {
    const button = $("#soundToggle"); button.textContent = soundEnabled ? "♪" : "×"; button.setAttribute("aria-pressed", String(soundEnabled)); button.title = soundEnabled ? "Выключить звуки" : "Включить звуки"; button.setAttribute("aria-label", button.title);
  }
  $("#soundToggle").addEventListener("click", () => { soundEnabled = !soundEnabled; localStorage.setItem(soundKey, soundEnabled ? "on" : "off"); renderSoundToggle(); if (soundEnabled) playSound("slide"); });
  $("#statsButton").addEventListener("click", () => { playSound("slide"); updateGlobalProgress(); $("#statsDialog").showModal(); });
  $("#closeStats").addEventListener("click", () => $("#statsDialog").close());
  $("#statsDialog").addEventListener("click", (event) => { if (event.target === $("#statsDialog")) $("#statsDialog").close(); });

  function setTheme(lesson) {
    const [accent, soft, deep] = lessonMeta[lesson.id].colors;
    document.documentElement.style.setProperty("--accent", accent); document.documentElement.style.setProperty("--accent-soft", soft); document.documentElement.style.setProperty("--accent-deep", deep);
  }

  function focusPanel(next) {
    const mobile = window.matchMedia("(max-width: 920px)").matches;
    const focus = mobile ? next : state.panelFocus === next && next !== "memo" ? "memo" : next;
    const apply = () => { state.panelFocus = focus; $("#studyStage").dataset.focus = focus; updateFocusButtons(); };
    playSound("slide");
    if (document.startViewTransition) document.startViewTransition(apply); else { $("#studyStage").classList.add("swapping"); apply(); window.setTimeout(() => $("#studyStage").classList.remove("swapping"), 420); }
  }
  function updateFocusButtons() {
    $$('[data-focus-panel]').forEach((button) => { const active = button.dataset.focusPanel === state.panelFocus; button.textContent = active && state.panelFocus !== "memo" ? "↙" : "↗"; button.setAttribute("aria-pressed", String(active)); });
    $$('[data-mobile-focus]').forEach((button) => { const active = button.dataset.mobileFocus === state.panelFocus; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); });
  }
  $$('[data-focus-panel]').forEach((button) => button.addEventListener("click", () => focusPanel(button.dataset.focusPanel)));
  $$('[data-mobile-focus]').forEach((button) => button.addEventListener("click", () => focusPanel(button.dataset.mobileFocus)));

  function renderLessonNav() {
    $("#lessonNav").innerHTML = lessons.map((lesson, index) => `<button class="${index === state.lesson ? "active" : ""}" data-lesson="${index}"><span>${String(index + 1).padStart(2, "0")}</span><b>${escapeHtml(lesson.short)}</b>${progress.lessons.includes(lesson.id) ? "<i>✓</i>" : ""}</button>`).join("");
    $$('[data-lesson]', $("#lessonNav")).forEach((button) => button.addEventListener("click", () => { stopKaraoke(); state.lesson = Number(button.dataset.lesson); state.model = 0; state.karaokeExample = 0; state.posterLine = 0; state.line = 0; state.practice = 0; state.phase = "idle"; state.char = 0; renderTheory(); }));
  }

  function renderPoster() {
    const lesson = lessons[state.lesson]; const model = currentModel(); const models = modelsFor(lesson);
    $("#posterNumber").textContent = String(state.lesson + 1).padStart(2, "0"); $("#posterKicker").textContent = lesson.kicker;
    $("#posterFormula").textContent = model.formula || lessonMeta[lesson.id].formula; $("#posterTitle").textContent = model.title;
    $("#posterRule").textContent = model.rule; $("#posterPrinciple").textContent = model.principle;
    $("#posterImage").src = lesson.art; $("#posterImage").alt = `Иллюстрация памятки «${model.title}»`;
    const memoArt = `assets/drawn-memos/${drawnMemoArt[lesson.id][state.model]}`;
    $("#drawnMemoImage").src = memoArt;
    $("#drawnMemoImage").parentElement.style.setProperty("--memo-art", `url("${memoArt}")`);
    $("#drawnMemoImage").alt = `Нарисованная памятка «${model.title}»: ${model.principle}`;
    $("#posterTips").innerHTML = model.tips.map((tip) => `<span>${escapeHtml(tip)}</span>`).join("");
    $("#posterTable").innerHTML = model.lines.map((line, index) => `<button class="poster-row ${index === state.posterLine ? "active" : ""}" data-poster-line="${index}"><span>${escapeHtml(line.caseName)}</span><i>${escapeHtml(line.cue)}</i><b>${escapeHtml(line.form)}</b></button>`).join("");
    $("#posterNorm").innerHTML = `<b>Запомнить</b><span>${escapeHtml(lessonMeta[lesson.id].norm)}</span>`;
    $("#modelCarousel").hidden = models.length < 2; $("#modelPosition").textContent = `${state.model + 1} / ${models.length}`; $("#modelLabel").textContent = model.label;
    $$('[data-poster-line]').forEach((button) => button.addEventListener("click", () => { state.posterLine = Number(button.dataset.posterLine); renderPoster(); }));
  }
  function changeModel(delta) {
    const count = modelsFor(lessons[state.lesson]).length; if (count < 2) return;
    playSound("slide"); stopKaraoke(); state.model = (state.model + delta + count) % count; state.karaokeExample = state.model; state.posterLine = 0; state.line = 0; state.phase = "idle"; state.char = 0; state.countdown = 5; renderPoster(); renderKaraoke();
  }
  $("#modelPrev").addEventListener("click", (event) => { event.stopPropagation(); changeModel(-1); }); $("#modelNext").addEventListener("click", (event) => { event.stopPropagation(); changeModel(1); });

  function renderTheory() { const lesson = lessons[state.lesson]; setTheme(lesson); renderLessonNav(); renderPoster(); renderKaraoke(); renderPractice(); updateFocusButtons(); updateGlobalProgress(); }
  function selectLine(index) { stopKaraoke(); state.line = index; state.phase = "idle"; state.char = 0; state.countdown = 5; renderKaraoke(); }
  function stopKaraoke() { if (state.timer) window.clearTimeout(state.timer); state.timer = null; state.paused = true; }
  function resetKaraoke() { stopKaraoke(); state.karaokeExample = 0; state.model = 0; state.posterLine = 0; state.line = 0; state.phase = "idle"; state.char = 0; state.countdown = 5; state.paused = false; renderPoster(); renderKaraoke(); }
  function selectKaraokeExample(index, { syncPoster = true } = {}) {
    const sets = karaokeSetsFor(lessons[state.lesson]);
    stopKaraoke(); state.karaokeExample = (index + sets.length) % sets.length; state.line = 0; state.phase = "idle"; state.char = 0; state.countdown = 5; state.paused = false;
    if (syncPoster) { state.model = Math.min(state.karaokeExample, modelsFor(lessons[state.lesson]).length - 1); state.posterLine = 0; renderPoster(); }
    playSound("slide"); renderKaraoke();
  }

  const karaokeNounRoot = /^(?:хит|трек|альбом|песн|запис|минут|клип|исполнител)/i;
  const karaokePrefix = /^(?:к|с|со|о|об|около|более|до|за|перед|в)$/i;
  function splitKaraokeForm(form) {
    const words = form.trim().split(/\s+/);
    let firstNumeral = 0;
    while (firstNumeral < words.length && karaokePrefix.test(words[firstNumeral])) firstNumeral += 1;
    const nounAt = words.findIndex((word, index) => index >= firstNumeral && karaokeNounRoot.test(word));
    const numeralEnd = nounAt < 0 ? words.length : nounAt;
    return {
      prefix: words.slice(0, firstNumeral).join(" "),
      numeral: words.slice(firstNumeral, numeralEnd).join(" "),
      noun: nounAt < 0 ? "" : words.slice(nounAt).join(" ")
    };
  }

  function renderKaraoke() {
    const sets = karaokeSetsFor(lessons[state.lesson]); const karaoke = currentKaraoke(); const line = karaoke.lines[state.line];
    $("#karaokeCase").textContent = line.caseName; $("#karaokeCue").textContent = line.cue; $("#karaokeDigit").textContent = karaoke.digit; $("#karaokePosition").textContent = `падеж ${state.line + 1} / ${karaoke.lines.length}`;
    $("#karaokeExampleLabel").textContent = `Пример ${state.karaokeExample + 1} из ${sets.length} · ${karaoke.digit}`;
    $("#karaokeExamplePrev").disabled = sets.length < 2; $("#karaokeExampleNext").disabled = sets.length < 2;
    const word = $("#karaokeWord"); const form = splitKaraokeForm(line.form); word.className = "karaoke-word";
    if (state.phase === "idle" || state.phase === "thinking") word.classList.add("waiting"); if (state.phase === "revealing") word.classList.add("revealing");
    const shownNumeral = state.phase === "revealing" || state.phase === "done" ? form.numeral.slice(0, state.char) : "?";
    word.innerHTML = `${form.prefix ? `<span class="karaoke-static karaoke-prefix">${escapeHtml(form.prefix)}</span>` : ""}<span class="karaoke-numeral ${state.phase === "revealing" ? "is-revealing" : ""}">${escapeHtml(shownNumeral)}</span>${form.noun ? `<span class="karaoke-static karaoke-noun">${escapeHtml(form.noun)}</span>` : ""}`;
    const countdown = $("#thinkCountdown"); countdown.className = `countdown ${state.phase === "thinking" ? "live" : ""}`;
    countdown.innerHTML = state.phase === "thinking" ? String(state.countdown) : state.phase === "revealing" || state.phase === "done" ? "числительное<br>открывается" : "ответьте<br>про себя";
    $("#karaokeStatus").textContent = state.paused ? "Пауза" : state.phase === "thinking" ? "Время ответить самостоятельно" : state.phase === "revealing" ? "Числительное появляется по буквам" : state.phase === "done" ? "Числительное открыто" : "Нажмите: сначала будет пауза";
    $("#playButton").textContent = state.phase === "thinking" || state.phase === "revealing" ? "Ⅱ" : "▶";
    $("#caseDots").innerHTML = karaoke.lines.map((item, index) => `<button class="${index === state.line ? "active" : ""}" data-case-dot="${index}" title="${escapeHtml(item.caseName)}">${item.caseName[0]}</button>`).join("");
    $$('[data-case-dot]').forEach((button) => button.addEventListener("click", () => selectLine(Number(button.dataset.caseDot))));
  }
  function startThinking() { state.paused = false; state.phase = "thinking"; state.countdown = 5; state.char = 0; playSound("countdown"); renderKaraoke(); thinkingTick(); }
  function thinkingTick() { if (state.paused || state.phase !== "thinking") return; state.timer = window.setTimeout(() => { if (state.countdown > 1) { state.countdown -= 1; playSound("countdown"); renderKaraoke(); thinkingTick(); } else { state.phase = "revealing"; state.char = 0; tone(880, .12, "sine", .055); renderKaraoke(); revealTick(); } }, 1000); }
  function revealTick() {
    if (state.paused || state.phase !== "revealing") return; const lines = currentKaraoke().lines; const line = lines[state.line];
    const numeral = splitKaraokeForm(line.form).numeral;
    if (state.char < numeral.length) { state.timer = window.setTimeout(() => { state.char += 1; while (state.char < numeral.length && /\s/.test(numeral[state.char])) state.char += 1; renderKaraoke(); revealTick(); }, Number($("#speedRange").value)); return; }
    state.phase = "done"; renderKaraoke();
    if (state.line < lines.length - 1) state.timer = window.setTimeout(() => { state.line += 1; startThinking(); }, 1900);
    else {
      const sets = karaokeSetsFor(lessons[state.lesson]);
      if (state.karaokeExample < sets.length - 1) state.timer = window.setTimeout(() => { state.karaokeExample += 1; state.model = Math.min(state.karaokeExample, modelsFor(lessons[state.lesson]).length - 1); state.posterLine = 0; state.line = 0; state.phase = "idle"; state.char = 0; playSound("slide"); renderPoster(); startThinking(); }, 1900);
      else { const lesson = lessons[state.lesson]; if (!progress.lessons.includes(lesson.id)) progress.lessons.push(lesson.id); save(); renderLessonNav(); }
    }
  }
  $("#playButton").addEventListener("click", () => { if (state.phase === "thinking" || state.phase === "revealing") { stopKaraoke(); renderKaraoke(); return; } if (state.phase === "done") state.char = 0; startThinking(); });
  $("#replayButton").addEventListener("click", resetKaraoke);
  $("#karaokeExamplePrev").addEventListener("click", () => selectKaraokeExample(state.karaokeExample - 1));
  $("#karaokeExampleNext").addEventListener("click", () => selectKaraokeExample(state.karaokeExample + 1));
  $("#speedRange").addEventListener("input", (event) => { $("#speedValue").textContent = `${(Number(event.target.value) / 1000).toFixed(1).replace(".", ",")} с`; });

  function practiceItems() { return practiceSets[lessons[state.lesson].id] || []; }
  function renderPractice() {
    const lesson = lessons[state.lesson]; const items = practiceItems(); const item = items[state.practice]; const done = progress.practices[lesson.id] || [];
    if (!item) {
      $("#practiceTitle").textContent = demoLimit ? "Полная версия" : "Нет фактов";
      $("#practicePosition").textContent = "—";
      $("#practiceDots").innerHTML = "";
      $("#practiceCase").textContent = "Демо";
      $("#practiceSentence").textContent = "Для этой темы упражнения доступны в полной версии.";
      const input = $("#practiceInput"); input.value = ""; input.disabled = true;
      $("#practiceFeedback").className = "";
      $("#practiceFeedback").textContent = "В демо открыты первые 20 упражнений из общей базы.";
      $("#skipPractice").disabled = true;
      return;
    }
    $("#practiceInput").disabled = false; $("#skipPractice").disabled = false;
    $("#practiceTitle").textContent = `${items.length} фактов`; $("#practicePosition").textContent = `${state.practice + 1}/${items.length}`; $("#practiceDots").innerHTML = items.map((_, index) => `<i class="${done.includes(index) ? "done" : index === state.practice ? "active" : ""}"></i>`).join("");
    $("#practiceCase").textContent = item.caseName; const match = item.sentence.match(/\(([^)]+)\)/);
    $("#practiceSentence").innerHTML = match ? escapeHtml(item.sentence.slice(0, match.index)) + `<mark>(${escapeHtml(match[1])})</mark>` + escapeHtml(item.sentence.slice(match.index + match[0].length)) : escapeHtml(item.sentence);
    const input = $("#practiceInput"); input.value = ""; input.className = ""; $("#practiceFeedback").className = ""; $("#practiceFeedback").textContent = item.note || "Введите форму и нажмите Enter — верный ответ сразу откроет следующий факт.";
  }
  function advancePractice() { const items = practiceItems(); if (!items.length) return; state.practice = (state.practice + 1) % items.length; renderPractice(); window.setTimeout(() => $("#practiceInput").focus(), 0); }
  $("#practiceInput").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return; event.preventDefault(); const lesson = lessons[state.lesson]; const item = practiceItems()[state.practice]; const variants = [item.answer, ...(item.accepted || [])].map(normalize); const correct = variants.includes(normalize(event.target.value));
    if (correct) { playSound("correct"); event.target.className = "correct"; $("#practiceFeedback").className = "correct"; $("#practiceFeedback").textContent = `Верно: ${item.answer}.`; progress.practices[lesson.id] ||= []; if (!progress.practices[lesson.id].includes(state.practice)) progress.practices[lesson.id].push(state.practice); save(); window.setTimeout(advancePractice, 650); }
    else { playSound("wrong"); event.target.className = "wrong"; $("#practiceFeedback").className = "wrong"; $("#practiceFeedback").textContent = `Эталон: ${item.answer}.`; event.target.select(); }
  });
  $("#practiceInput").addEventListener("input", (event) => { event.target.className = ""; $("#practiceFeedback").className = ""; }); $("#skipPractice").addEventListener("click", advancePractice);

  const tokenPattern = /\d[\d\s]*(?:[,.]\d+)?(?:[–—-]\d[\d\s]*(?:[,.]\d+)?)?(?:-[а-яА-ЯёЁ]+)?/g;
  const getTokens = (text) => (text.match(tokenPattern) || []).map((token) => token.trim());
  const visibleReadings = () => state.topic === "Все" ? readings : readings.filter((item) => item.topic === state.topic);
  function renderTopicFilters() {
    const topics = ["Все", ...new Set(readings.map((item) => item.topic))]; $("#topicFilters").innerHTML = topics.map((topic) => `<button class="${topic === state.topic ? "active" : ""}" data-topic="${escapeHtml(topic)}">${escapeHtml(topic === "Все" ? "Все" : topic.replace(/[«»]/g, ""))}</button>`).join("");
    $$('[data-topic]').forEach((button) => button.addEventListener("click", () => { state.topic = button.dataset.topic; const first = visibleReadings()[0]; if (first) state.reading = readings.indexOf(first); renderReading(); }));
  }
  function renderReadingList() {
    $("#readingList").innerHTML = visibleReadings().map((item) => { const index = readings.indexOf(item); const displayNumber = index + 1; const done = Boolean(progress.readingChecks?.[item.id]); return `<button class="${index === state.reading ? "active" : ""}" data-reading="${index}"><span>${String(displayNumber).padStart(2, "0")}</span><span><b>Текст ${displayNumber}</b><i>${escapeHtml(item.topic)}</i></span>${done ? "<em>✓</em>" : ""}</button>`; }).join("");
    $$('[data-reading]').forEach((button) => button.addEventListener("click", () => { state.reading = Number(button.dataset.reading); renderReadingList(); renderText(); }));
  }
  function inlineTextHtml(item) {
    const tokens = getTokens(item.text); if (!tokens.length) return escapeHtml(item.text); const pattern = new RegExp(`(${[...new Set(tokens)].sort((a, b) => b.length - a.length).map(escapeRegExp).join("|")})`, "g"); let index = 0;
    const sentences = item.text.split(/(?<=[.!?])\s+(?=[А-ЯЁ«])/u);
    return sentences.map((sentence) => `<p class="inline-sentence">${sentence.split(pattern).map((part) => { if (!tokens.includes(part.trim())) return escapeHtml(part); const answer = (progress.readings[item.id] || [])[index] || ""; const expected = (readingAnswers[item.id] || [])[index]?.split("|")[0] || ""; const width = Math.min(500, Math.max(170, expected.length * 8.4)); const html = `<span class="inline-number"><span class="inline-entry">(<b>${escapeHtml(part.trim())}</b><input data-inline-index="${index}" value="${escapeHtml(answer)}" style="--answer-width:${width}px" placeholder="числительное словами" aria-label="Запишите ${escapeHtml(part.trim())} словами">)</span><small class="field-hint" data-hint-index="${index}"></small></span>`; index += 1; return html; }).join("")}</p>`).join("");
  }
  function updateTextFooter() {
    const item = readings[state.reading]; const inputs = $$('[data-inline-index]', $("#inlineText")); const filled = inputs.filter((input) => input.value.trim()).length; $("#textFilled").textContent = `${filled} / ${inputs.length}`; $("#textSaved").textContent = filled === inputs.length ? "Все поля заполнены — нажмите «Проверить»" : "Ответы сохраняются автоматически";
    inputs.forEach((input) => input.classList.toggle("filled", Boolean(input.value.trim()))); progress.readings[item.id] = inputs.map((input) => input.value.trim()); save();
  }
  function checkText() {
    const item = readings[state.reading]; const expected = readingAnswers[item.id] || []; const inputs = $$('[data-inline-index]', $("#inlineText")); let correct = 0;
    inputs.forEach((input, index) => { const variants = (expected[index] || "").split("|").map(normalize); const ok = Boolean(input.value.trim()) && variants.includes(normalize(input.value)); const reference = (expected[index] || "—").split("|")[0]; const hint = $(`[data-hint-index="${index}"]`, $("#inlineText")); input.classList.remove("correct", "wrong", "revealed"); input.classList.add(ok ? "correct" : "wrong"); input.title = ok ? "Верно" : `Эталон: ${reference}`; if (hint) hint.textContent = ok ? "" : item.id === 1 && index === 4 ? `Эталон: ${reference}. Год читается без слова «одна».` : `Эталон: ${reference}`; if (ok) correct += 1; });
    const allCorrect = correct === inputs.length; playSound(allCorrect ? "correct" : "wrong"); progress.readingChecks ||= {}; progress.readingChecks[item.id] = allCorrect; $("#textSaved").textContent = allCorrect ? `Верно: ${correct} из ${inputs.length} ✓` : `Верно ${correct} из ${inputs.length}. Под ошибочными формами показан эталон.`; save(); renderReadingList();
  }
  function showTextAnswers() {
    const item = readings[state.reading]; const expected = readingAnswers[item.id] || []; const inputs = $$('[data-inline-index]', $("#inlineText")); playSound("slide"); inputs.forEach((input, index) => { input.value = (expected[index] || "").split("|")[0]; input.classList.remove("wrong", "correct"); input.classList.add("revealed"); const hint = $(`[data-hint-index="${index}"]`, $("#inlineText")); if (hint) hint.textContent = ""; }); progress.readingChecks ||= {}; progress.readingChecks[item.id] = false; updateTextFooter(); $("#textSaved").textContent = "Эталонные формы показаны фиолетовым.";
  }
  function bindInlineInputs() {
    const inputs = $$('[data-inline-index]', $("#inlineText")); inputs.forEach((input, index) => { input.addEventListener("input", () => { input.classList.remove("correct", "wrong", "revealed"); const hint = $(`[data-hint-index="${index}"]`, $("#inlineText")); if (hint) hint.textContent = ""; updateTextFooter(); }); input.addEventListener("keydown", (event) => { if (event.key !== "Enter") return; event.preventDefault(); if (inputs[index + 1]) inputs[index + 1].focus(); else checkText(); }); });
  }
  function renderText() { const item = readings[state.reading]; $("#textTopic").textContent = item.topic; $("#textTitle").textContent = `Текст ${state.reading + 1}`; $("#textSource").textContent = item.source; $("#inlineText").innerHTML = inlineTextHtml(item); bindInlineInputs(); updateTextFooter(); }
  function renderReading() { renderTopicFilters(); renderReadingList(); renderText(); updateGlobalProgress(); }
  function nextReading() { playSound("slide"); state.reading = (state.reading + 1) % readings.length; state.topic = "Все"; renderReading(); }
  $("#checkText").addEventListener("click", checkText); $("#showTextAnswers").addEventListener("click", showTextAnswers); $("#nextText").addEventListener("click", nextReading);

  renderSoundToggle(); renderTheory();
})();
