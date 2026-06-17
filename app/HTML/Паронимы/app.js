(function () {
  "use strict";

  const MAX_CARDS = 20;
  const HISTORY_KEY = "paronyms-picture-game-issued-v1";
  const TURN_EFFECT_MS = 1080;
  const PRAISES = [
    "Отлично!",
    "Точно!",
    "Верно!",
    "Так держать!",
    "Прекрасно!"
  ];

  const cards = Array.isArray(window.PARONIMS_ASSETS) ? window.PARONIMS_ASSETS : [];
  const playableCards = cards.filter((card) => card && card.words && card.words.length >= 2 && card.images);
  const letters = Array.from(new Set(playableCards.map((card) => firstLetter(card)).filter(Boolean))).sort((a, b) => a.localeCompare(b, "ru"));
  const state = {
    mode: "fresh",
    originalSet: [],
    queue: [],
    current: null,
    selectedWord: "",
    assignments: {},
    locked: false,
    totalGroups: 0,
    solved: 0,
    errors: 0,
    repeatsSent: 0,
    customSelected: new Set(),
    search: "",
    activeLetter: letters[0] || "",
  };

  const el = {
    startScreen: document.querySelector("#startScreen"),
    playScreen: document.querySelector("#playScreen"),
    explanationScreen: document.querySelector("#explanationScreen"),
    finishScreen: document.querySelector("#finishScreen"),
    gameMenuLink: document.querySelector("#gameMenuLink"),
    turnEffect: document.querySelector("#turnEffect"),
    successBurst: document.querySelector("#successBurst"),
    successText: document.querySelector("#successText"),
    startButton: document.querySelector("#startButton"),
    resetHistoryButton: document.querySelector("#resetHistoryButton"),
    startStatus: document.querySelector("#startStatus"),
    modeButtons: Array.from(document.querySelectorAll("[data-mode]")),
    groupPicker: document.querySelector("#groupPicker"),
    groupSearch: document.querySelector("#groupSearch"),
    letterGrid: document.querySelector("#letterGrid"),
    groupList: document.querySelector("#groupList"),
    selectedCount: document.querySelector("#selectedCount"),
    clearSelectionButton: document.querySelector("#clearSelectionButton"),
    groupTitle: document.querySelector("#groupTitle"),
    cardProgress: document.querySelector("#cardProgress"),
    errorProgress: document.querySelector("#errorProgress"),
    repeatProgress: document.querySelector("#repeatProgress"),
    message: document.querySelector("#message"),
    cardsGrid: document.querySelector("#cardsGrid"),
    wordsRow: document.querySelector("#wordsRow"),
    checkButton: document.querySelector("#checkButton"),
    resetButton: document.querySelector("#resetButton"),
    nextButton: document.querySelector("#nextButton"),
    explanationTitle: document.querySelector("#explanationTitle"),
    explanationImage: document.querySelector("#explanationImage"),
    explanationNextButton: document.querySelector("#explanationNextButton"),
    finishGroups: document.querySelector("#finishGroups"),
    finishErrors: document.querySelector("#finishErrors"),
    againButton: document.querySelector("#againButton"),
    newSetButton: document.querySelector("#newSetButton"),
  };

  function normalize(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/ё/g, "ё")
      .replace(/ё/g, "е")
      .replace(/[‐‑‒–—―−]/g, "-")
      .replace(/[_\s]+/g, " ")
      .replace(/\s*-\s*/g, "-");
  }

  function firstLetter(card) {
    const source = String(card?.title || card?.words?.[0] || "").trim();
    return source ? source[0].toLocaleUpperCase("ru-RU") : "";
  }

  function assetPath(card, file) {
    return `assets/${encodeURIComponent(card.folder)}/${encodeURIComponent(file)}`;
  }

  function showOnly(screen) {
    [el.startScreen, el.playScreen, el.explanationScreen, el.finishScreen].forEach((node) => {
      node.classList.toggle("hidden", node !== screen);
    });
  }

  function goToGamesMenu() {
    if (window.location.protocol === "file:") {
      if (window.history.length > 1) window.history.back();
      return;
    }
    let target = "/games";
    try {
      if (window.top && window.top !== window.self && window.top.location.pathname.startsWith("/apps/mini")) {
        target = "/apps/mini";
      }
      window.top.location.href = target;
    } catch {
      window.location.href = target;
    }
  }

  function shuffle(items) {
    const copy = items.slice();
    for (let index = copy.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1));
      [copy[index], copy[randomIndex]] = [copy[randomIndex], copy[index]];
    }
    return copy;
  }

  function playTurnEffect(after) {
    if (!el.turnEffect) {
      after();
      return;
    }
    el.turnEffect.classList.remove("active");
    void el.turnEffect.offsetWidth;
    el.turnEffect.classList.add("active");
    window.setTimeout(() => {
      after();
      window.setTimeout(() => el.turnEffect.classList.remove("active"), 90);
    }, TURN_EFFECT_MS);
  }

  function showSuccessBurst() {
    if (!el.successBurst) return;
    el.successText.textContent = PRAISES[Math.floor(Math.random() * PRAISES.length)];
    el.successBurst.classList.remove("active");
    void el.successBurst.offsetWidth;
    el.successBurst.classList.add("active");
    window.setTimeout(() => el.successBurst.classList.remove("active"), 1200);
  }

  function readHistory() {
    try {
      const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
      return Array.isArray(value) ? value : [];
    } catch {
      return [];
    }
  }

  function writeHistory(ids) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(Array.from(new Set(ids))));
  }

  function pickSet(mode) {
    if (mode === "custom") {
      return playableCards.filter((card) => state.customSelected.has(card.id)).slice(0, MAX_CARDS);
    }

    if (mode === "random") return shuffle(playableCards).slice(0, MAX_CARDS);

    const history = readHistory();
    const historySet = new Set(history);
    let fresh = playableCards.filter((card) => !historySet.has(card.id));
    let nextHistory = history.slice();

    if (fresh.length < MAX_CARDS) {
      fresh = playableCards.slice();
      nextHistory = [];
    }

    const selected = shuffle(fresh).slice(0, MAX_CARDS);
    writeHistory(nextHistory.concat(selected.map((card) => card.id)));
    return selected;
  }

  function startGame(mode) {
    const selected = pickSet(mode);
    if (!selected.length) {
      el.startStatus.textContent = mode === "custom"
        ? "Выберите хотя бы одну группу паронимов."
        : "Не нашлось карточек с изображениями.";
      return;
    }
    state.originalSet = selected.map((card) => ({ ...card, retry: false }));
    state.queue = shuffle(state.originalSet);
    state.current = null;
    state.selectedWord = "";
    state.assignments = {};
    state.locked = false;
    state.totalGroups = selected.length;
    state.solved = 0;
    state.errors = 0;
    state.repeatsSent = 0;
    showOnly(el.playScreen);
    nextCard(false);
  }

  function updateProgress() {
    const currentNumber = Math.min(state.solved + 1, state.totalGroups);
    const repeatCount = state.queue.filter((card) => card.retry).length + (state.current?.retry ? 1 : 0);
    el.cardProgress.textContent = `Карточка ${currentNumber} из ${state.totalGroups}`;
    el.errorProgress.textContent = `Ошибок: ${state.errors}`;
    el.repeatProgress.textContent = `На повторе: ${repeatCount}`;
  }

  function renderCard() {
    const card = state.current;
    state.selectedWord = "";
    state.assignments = {};
    state.locked = false;
    el.groupTitle.textContent = card.title || card.words.join(" — ");
    el.message.textContent = "";
    el.message.className = "message";
    el.checkButton.classList.remove("hidden");
    el.resetButton.classList.remove("hidden");
    el.nextButton.classList.add("hidden");
    el.checkButton.disabled = false;
    el.resetButton.disabled = false;
    updateProgress();

    const shuffledWords = shuffle(card.words);
    el.cardsGrid.innerHTML = card.words.map((word) => {
      const file = card.images[word];
      const imageSrc = assetPath(card, file);
      return `
        <button class="picture-card" type="button" data-target="${escapeAttr(word)}">
          <span class="picture-wrap">
            <img src="${imageSrc}" alt="${escapeAttr(word)}" />
          </span>
          <span class="caption-slot" data-caption="${escapeAttr(word)}">Выбери слово</span>
        </button>
      `;
    }).join("");

    el.wordsRow.innerHTML = shuffledWords.map((word) => (
      `<button class="word-chip" type="button" data-word="${escapeAttr(word)}">${escapeHtml(word)}</button>`
    )).join("");
  }

  function nextCard(withEffect = true) {
    const openNext = () => {
      if (!state.queue.length) {
        finishGame();
        return;
      }
      state.current = state.queue.shift();
      renderCard();
      showOnly(el.playScreen);
    };
    if (withEffect) playTurnEffect(openNext);
    else openNext();
  }

  function chooseWord(word) {
    if (state.locked) return;
    state.selectedWord = word;
    el.wordsRow.querySelectorAll(".word-chip").forEach((button) => {
      button.classList.toggle("selected", button.dataset.word === word);
    });
    el.message.textContent = "";
    el.message.className = "message";
  }

  function assignWord(targetWord) {
    if (state.locked) return;
    if (!state.selectedWord) {
      el.message.textContent = "Сначала выбери слово.";
      return;
    }

    Object.keys(state.assignments).forEach((target) => {
      if (state.assignments[target] === state.selectedWord) delete state.assignments[target];
    });
    state.assignments[targetWord] = state.selectedWord;
    state.selectedWord = "";
    renderAssignments();
  }

  function renderAssignments() {
    el.cardsGrid.querySelectorAll(".picture-card").forEach((cardNode) => {
      const target = cardNode.dataset.target;
      const assigned = state.assignments[target];
      const caption = cardNode.querySelector(".caption-slot");
      cardNode.classList.toggle("assigned", Boolean(assigned));
      caption.classList.toggle("filled", Boolean(assigned));
      caption.textContent = assigned || "Выбери слово";
    });

    const used = new Set(Object.values(state.assignments));
    el.wordsRow.querySelectorAll(".word-chip").forEach((button) => {
      button.classList.toggle("selected", false);
      button.classList.toggle("used", used.has(button.dataset.word));
    });
  }

  function checkAnswer() {
    if (state.locked || !state.current) return;
    const words = state.current.words;
    if (words.some((word) => !state.assignments[word])) {
      el.message.textContent = "Подпиши все картинки.";
      return;
    }

    state.locked = true;
    const isCorrect = words.every((word) => normalize(state.assignments[word]) === normalize(word));
    el.cardsGrid.querySelectorAll(".picture-card").forEach((cardNode) => {
      const target = cardNode.dataset.target;
      const correct = normalize(state.assignments[target]) === normalize(target);
      const caption = cardNode.querySelector(".caption-slot");
      cardNode.classList.add(correct ? "correct" : "wrong");
      if (!correct) caption.textContent = `Верно: ${target}`;
    });

    el.checkButton.classList.add("hidden");
    el.resetButton.classList.add("hidden");

    if (isCorrect) {
      state.solved += 1;
      el.message.textContent = "Верно. Можно идти дальше.";
      el.message.className = "message good";
      el.nextButton.classList.remove("hidden");
      showSuccessBurst();
    } else {
      state.errors += 1;
      state.repeatsSent += 1;
      state.current.retry = true;
      state.queue.push(state.current);
      el.message.textContent = "Есть ошибка. Смотри разбор, эта группа вернётся позже.";
      el.message.className = "message bad";
      updateProgress();
      window.setTimeout(() => showExplanation(), 520);
      return;
    }
    updateProgress();
  }

  function showExplanation() {
    if (!state.current?.explanationImage) {
      nextCard();
      return;
    }
    el.explanationTitle.textContent = state.current.title || "Разбор";
    el.explanationImage.src = assetPath(state.current, state.current.explanationImage);
    playTurnEffect(() => showOnly(el.explanationScreen));
  }

  function resetCurrent() {
    if (state.locked) return;
    state.selectedWord = "";
    state.assignments = {};
    el.message.textContent = "";
    el.message.className = "message";
    renderAssignments();
  }

  function finishGame() {
    el.finishGroups.textContent = `Групп: ${state.totalGroups}`;
    el.finishErrors.textContent = `Ошибок: ${state.errors}`;
    showOnly(el.finishScreen);
  }

  function renderGroupPicker() {
    if (!el.groupList) return;
    const query = normalize(state.search);
    const selectedCount = state.customSelected.size;
    const byLetter = letters.map((letter) => ({
      letter,
      cards: playableCards.filter((card) => firstLetter(card) === letter),
    }));

    if (!query && !letters.includes(state.activeLetter)) {
      state.activeLetter = letters[0] || "";
    }

    const filtered = query
      ? playableCards.filter((card) => normalize(`${card.title} ${card.words.join(" ")}`).includes(query))
      : playableCards.filter((card) => firstLetter(card) === state.activeLetter);

    el.selectedCount.textContent = `Выбрано: ${selectedCount} из ${MAX_CARDS}`;
    el.letterGrid.innerHTML = byLetter.map((group) => {
      const active = !query && group.letter === state.activeLetter ? "active" : "";
      return `
        <button class="letter-button ${active}" type="button" data-letter="${escapeAttr(group.letter)}">
          ${escapeHtml(group.letter)}
          <span>${group.cards.length}</span>
        </button>
      `;
    }).join("");

    el.groupList.innerHTML = filtered.map((card) => {
      const checked = state.customSelected.has(card.id) ? "checked" : "";
      const disabled = !checked && selectedCount >= MAX_CARDS ? "disabled" : "";
      return `
        <label class="group-option">
          <input type="checkbox" value="${escapeAttr(card.id)}" ${checked} ${disabled} />
          <span>${escapeHtml(card.title || card.words.join(" — "))}</span>
        </label>
      `;
    }).join("");

    if (!filtered.length) {
      el.groupList.innerHTML = `<p class="status-line">Ничего не найдено.</p>`;
    }
  }

  function setMode(mode) {
    state.mode = mode;
    el.modeButtons.forEach((item) => item.classList.toggle("selected", item.dataset.mode === mode));
    el.groupPicker.classList.toggle("hidden", mode !== "custom");
    el.startStatus.textContent = "";
    renderGroupPicker();
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
  }

  el.modeButtons.forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  el.groupSearch.addEventListener("input", () => {
    state.search = el.groupSearch.value;
    renderGroupPicker();
  });

  el.letterGrid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-letter]");
    if (!button) return;
    state.activeLetter = button.dataset.letter;
    state.search = "";
    el.groupSearch.value = "";
    renderGroupPicker();
  });

  el.groupList.addEventListener("change", (event) => {
    const input = event.target.closest("input[type='checkbox']");
    if (!input) return;
    if (input.checked) {
      if (state.customSelected.size >= MAX_CARDS) {
        input.checked = false;
        el.startStatus.textContent = `Можно выбрать не больше ${MAX_CARDS} групп.`;
        return;
      }
      state.customSelected.add(input.value);
    } else {
      state.customSelected.delete(input.value);
    }
    el.startStatus.textContent = "";
    renderGroupPicker();
  });

  el.clearSelectionButton.addEventListener("click", () => {
    state.customSelected.clear();
    renderGroupPicker();
  });

  el.gameMenuLink.addEventListener("click", goToGamesMenu);
  el.startButton.addEventListener("click", () => startGame(state.mode));
  el.resetHistoryButton.addEventListener("click", () => {
    localStorage.removeItem(HISTORY_KEY);
    el.startStatus.textContent = "История сброшена.";
  });
  el.checkButton.addEventListener("click", checkAnswer);
  el.resetButton.addEventListener("click", resetCurrent);
  el.nextButton.addEventListener("click", () => nextCard());
  el.explanationNextButton.addEventListener("click", () => nextCard());
  el.againButton.addEventListener("click", () => {
    state.queue = shuffle(state.originalSet.map((card) => ({ ...card, retry: false })));
    state.solved = 0;
    state.errors = 0;
    state.repeatsSent = 0;
    state.current = null;
    showOnly(el.playScreen);
    nextCard();
  });
  el.newSetButton.addEventListener("click", () => {
    showOnly(el.startScreen);
    setMode("fresh");
  });

  el.wordsRow.addEventListener("click", (event) => {
    const button = event.target.closest("[data-word]");
    if (button) chooseWord(button.dataset.word);
  });

  el.cardsGrid.addEventListener("click", (event) => {
    const cardNode = event.target.closest("[data-target]");
    if (cardNode) assignWord(cardNode.dataset.target);
  });

  renderGroupPicker();
  el.startStatus.textContent = playableCards.length ? `Доступно групп: ${playableCards.length}.` : "Manifest не найден.";
}());
