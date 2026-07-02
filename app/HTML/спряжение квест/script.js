"use strict";

const ASSETS = {
  avatars: [
    { id: "boy", label: "Мальчик", file: "мальчик_без_фона.png" },
    { id: "girl", label: "Девочка", file: "девочка_без_фона.png" },
    { id: "owl", label: "Сова", file: "сова_без_фона.png" },
    { id: "fox", label: "Лисица", file: "лисица_без_фона.png" },
    { id: "spark", label: "Огонёк", file: "огонёчек_без_фона.png" },
    { id: "pencil", label: "Карандаш", file: "карандашик_без_фона.png" }
  ]
};

const ALGORITHM_REVEAL_ZONES = [
  { id: "start", x: 26, y: 6, w: 50, h: 15 },
  { id: "question", x: 24, y: 18, w: 52, h: 13 },
  { id: "stressed", x: 11, y: 25, w: 31, h: 53 },
  { id: "prefix", x: 43, y: 30, w: 37, h: 31 },
  { id: "infinitive", x: 64, y: 35, w: 26, h: 29 },
  { id: "it", x: 59, y: 57, w: 32, h: 18 },
  { id: "exceptions", x: 49, y: 73, w: 43, h: 17 }
];

const ALGORITHM_QUESTIONS = [
  {
    question: "С чего начинаем?",
    correct: "Проспрягать глагол",
    zone: "start",
    options: ["Проспрягать глагол", "Сразу искать исключение", "Определить приставку"]
  },
  {
    question: "Что проверяем дальше?",
    correct: "Окончание ударное?",
    zone: "question",
    options: ["Окончание ударное?", "Есть ли суффикс -ова-?", "Сколько букв в слове?"]
  },
  {
    question: "Если окончание ударное, как определяем спряжение?",
    correct: "По личному окончанию",
    zone: "stressed",
    options: ["По личному окончанию", "По начальной форме", "По приставке ВЫ-"]
  },
  {
    question: "Если окончание безударное, что проверяем сначала?",
    correct: "Есть ли приставка ВЫ-?",
    zone: "prefix",
    options: ["Есть ли приставка ВЫ-?", "Есть ли буква Я?", "Сколько слогов?"]
  },
  {
    question: "Если приставки ВЫ- нет, что делаем?",
    correct: "Ставим глагол в начальную форму",
    zone: "infinitive",
    options: ["Ставим глагол в начальную форму", "Определяем по ударению", "Выбираем II спряжение"]
  },
  {
    question: "Что спрашиваем у начальной формы?",
    correct: "Оканчивается на -ить?",
    zone: "it",
    options: ["Оканчивается на -ить?", "Есть ли приставка?", "Сколько окончаний?"]
  },
  {
    question: "Что обязательно проверяем в конце?",
    correct: "Исключения",
    zone: "exceptions",
    options: ["Исключения", "Род глагола", "Падеж"]
  }
];

const CONJUGATION_TASKS = [
  ["писать", "I", "Не на -ить -> I спряжение."],
  ["читать", "I", "Не на -ить -> I спряжение."],
  ["думать", "I", "Не на -ить -> I спряжение."],
  ["играть", "I", "Не на -ить -> I спряжение."],
  ["работать", "I", "Не на -ить -> I спряжение."],
  ["сеять", "I", "Не на -ить -> I спряжение."],
  ["таять", "I", "Не на -ить -> I спряжение."],
  ["надеяться", "I", "Не на -ить -> I спряжение."],
  ["бороться", "I", "Не на -ить -> I спряжение."],
  ["колоть", "I", "Не на -ить -> I спряжение."],
  ["молоть", "I", "Не на -ить -> I спряжение."],
  ["полоть", "I", "Не на -ить -> I спряжение."],
  ["брить", "I", "Исключение: брить относится к I спряжению."],
  ["стелить", "I", "Исключение: стелить относится к I спряжению."],
  ["зиждиться", "I", "Исключение: зиждиться относится к I спряжению."],
  ["клеить", "II", "На -ить -> II спряжение."],
  ["строить", "II", "На -ить -> II спряжение."],
  ["красить", "II", "На -ить -> II спряжение."],
  ["пилить", "II", "На -ить -> II спряжение."],
  ["готовить", "II", "На -ить -> II спряжение."],
  ["чистить", "II", "На -ить -> II спряжение."],
  ["носить", "II", "На -ить -> II спряжение."],
  ["просить", "II", "На -ить -> II спряжение."],
  ["гнать", "II", "Исключение: гнать относится ко II спряжению."],
  ["держать", "II", "Исключение: держать относится ко II спряжению."],
  ["дышать", "II", "Исключение: дышать относится ко II спряжению."],
  ["слышать", "II", "Исключение: слышать относится ко II спряжению."],
  ["смотреть", "II", "Исключение: смотреть относится ко II спряжению."],
  ["видеть", "II", "Исключение: видеть относится ко II спряжению."],
  ["ненавидеть", "II", "Исключение: ненавидеть относится ко II спряжению."],
  ["обидеть", "II", "Исключение: обидеть относится ко II спряжению."],
  ["терпеть", "II", "Исключение: терпеть относится ко II спряжению."],
  ["вертеть", "II", "Исключение: вертеть относится ко II спряжению."],
  ["зависеть", "II", "Исключение: зависеть относится ко II спряжению."],
  ["тащить", "II", "На -ить -> II спряжение."],
  ["ловить", "II", "На -ить -> II спряжение."],
  ["платить", "II", "На -ить -> II спряжение."],
  ["хвалить", "II", "На -ить -> II спряжение."],
  ["учить", "II", "На -ить -> II спряжение."],
  ["лечить", "II", "На -ить -> II спряжение."],
  ["служить", "II", "На -ить -> II спряжение."],
  ["тушить", "II", "На -ить -> II спряжение."],
  ["сушить", "II", "На -ить -> II спряжение."],
  ["будить", "II", "На -ить -> II спряжение."],
  ["варить", "II", "На -ить -> II спряжение."],
  ["верить", "II", "На -ить -> II спряжение."],
  ["веять", "I", "Не на -ить -> I спряжение."],
  ["лаять", "I", "Не на -ить -> I спряжение."],
  ["краснеть", "I", "Не на -ить -> I спряжение."],
  ["желтеть", "I", "Не на -ить -> I спряжение."],
  ["умнеть", "I", "Не на -ить -> I спряжение."],
  ["гулять", "I", "Не на -ить -> I спряжение."],
  ["прыгать", "I", "Не на -ить -> I спряжение."],
  ["слушать", "I", "Не на -ить -> I спряжение."],
  ["рисовать", "I", "Не на -ить -> I спряжение."],
  ["завтракать", "I", "Не на -ить -> I спряжение."],
  ["обедать", "I", "Не на -ить -> I спряжение."],
  ["ужинать", "I", "Не на -ить -> I спряжение."],
  ["копать", "I", "Не на -ить -> I спряжение."],
  ["плакать", "I", "Не на -ить -> I спряжение."]
].map(([infinitive, answer, explanation], index) => ({ id: `conj_${index}`, infinitive, answer, explanation }));

const DEFAULT_TASKS = [
  { id: "d1", variant: "(автомобили) движ..тся", answer: "у", correct_letter: "у", correct_spelling: "(автомобили) движутся", explanation: "Глагол I спряжения: в 3-м лице множественного числа пишется -ут/-ют." },
  { id: "d2", variant: "(родители) тревож..тся", answer: "а", correct_letter: "а", correct_spelling: "(родители) тревожатся", explanation: "Глагол II спряжения: в 3-м лице множественного числа пишется -ат/-ят." },
  { id: "d3", variant: "выдел..шь цветом", answer: "и", correct_letter: "и", correct_spelling: "выделишь цветом", explanation: "Глагол II спряжения, в личном окончании пишется И." },
  { id: "d4", variant: "колебл..шься", answer: "е", correct_letter: "е", correct_spelling: "колеблешься", explanation: "Глагол I спряжения, в личном окончании пишется Е." },
  { id: "d5", variant: "кле..т", answer: "и", correct_letter: "и", correct_spelling: "клеит", explanation: "Клеить оканчивается на -ить, это II спряжение." },
  { id: "d6", variant: "пиш..м", answer: "е", correct_letter: "е", correct_spelling: "пишем", explanation: "Писать относится к I спряжению, в окончании пишется Е." },
  { id: "d7", variant: "держ..т", answer: "и", correct_letter: "и", correct_spelling: "держит", explanation: "Держать - исключение II спряжения." },
  { id: "d8", variant: "стел..шь", answer: "е", correct_letter: "е", correct_spelling: "стелешь", explanation: "Стелить - исключение I спряжения." },
  { id: "d9", variant: "слыш..т", answer: "а", correct_letter: "а", correct_spelling: "слышат", explanation: "Слышать - исключение II спряжения, во множественном числе пишется -ат/-ят." },
  { id: "d10", variant: "бор..тся", answer: "ю", correct_letter: "ю", correct_spelling: "борются", explanation: "Бороться относится к I спряжению, пишется -ют." }
];

const EXTRA_TASKS = [
  { id: "ege12u_0011", variant: "(лица) сия..т (радостью)", answer: "ю", correct_letter: "ю", correct_spelling: "(лица) сияют (радостью)", explanation: "Личное окончание глагола определяется по спряжению; учитываем исключения и форму слова." },
  { id: "ege12u_0012", variant: "(дети) жмур..тся", answer: "я", correct_letter: "я", correct_spelling: "(дети) жмурятся", explanation: "Контекст: 3-е л. мн. ч. II спряжения." },
  { id: "ege12u_0013", variant: "крикн..шь", answer: "е", correct_letter: "е", correct_spelling: "крикнешь", explanation: "Личное окончание глагола определяется по спряжению." },
  { id: "ege12u_0014", variant: "(дети) спряч..тся", answer: "у", correct_letter: "у", correct_spelling: "(дети) спрячутся", explanation: "В 3-м лице множественного числа I спряжения пишется -ут/-ют." },
  { id: "ege12u_0015", variant: "(ветер) перемен..тся", answer: "и", correct_letter: "и", correct_spelling: "(ветер) переменится", explanation: "Личное окончание глагола определяется по спряжению." },
  { id: "ege12u_0016", variant: "разве..шь (сомнения)", answer: "е", correct_letter: "е", correct_spelling: "развеешь (сомнения)", explanation: "Развеять относится к I спряжению, в окончании пишется Е." },
  { id: "ege12u_0017", variant: "(учителя) науч..т", answer: "а", correct_letter: "а", correct_spelling: "(учителя) научат", explanation: "Научить относится ко II спряжению, пишется -ат/-ят." },
  { id: "ege12u_0018", variant: "(он) смотр..т", answer: "и", correct_letter: "и", correct_spelling: "(он) смотрит", explanation: "Смотреть - исключение II спряжения." },
  { id: "ege12u_0019", variant: "(это) противореч..т (правилам)", answer: "и", correct_letter: "и", correct_spelling: "(это) противоречит (правилам)", explanation: "Личное окончание глагола определяется по спряжению." },
  { id: "ege12u_0020", variant: "терп..шь", answer: "и", correct_letter: "и", correct_spelling: "терпишь", explanation: "Терпеть - исключение II спряжения." },
  { id: "ege12u_0021", variant: "(друзья) вышл..т (посылку)", answer: "ю", correct_letter: "ю", correct_spelling: "(друзья) вышлют (посылку)", explanation: "В 3-м лице множественного числа I спряжения пишется -ут/-ют." },
  { id: "ege12u_0022", variant: "(орехи хорошо) кол..тся", answer: "ю", correct_letter: "ю", correct_spelling: "(орехи хорошо) колются", explanation: "Колоть относится к I спряжению, пишется -ют." },
  { id: "ege12u_0023", variant: "(всё) забуд..тся", answer: "е", correct_letter: "е", correct_spelling: "(всё) забудется", explanation: "Личное окончание глагола определяется по спряжению." },
  { id: "ege12u_0024", variant: "долож..шь (обстановку)", answer: "и", correct_letter: "и", correct_spelling: "доложишь (обстановку)", explanation: "Доложить относится ко II спряжению." },
  { id: "ege12u_0025", variant: "предвид..шь", answer: "и", correct_letter: "и", correct_spelling: "предвидишь", explanation: "В личном окончании глагола II спряжения пишется И." },
  { id: "ege12u_0026", variant: "(студенты) труд..тся", answer: "я", correct_letter: "я", correct_spelling: "(студенты) трудятся", explanation: "Трудиться относится ко II спряжению, пишется -ят." },
  { id: "ege12u_0027", variant: "(они мне) повер..т", answer: "я", correct_letter: "я", correct_spelling: "(они мне) поверят", explanation: "Поверить относится ко II спряжению, пишется -ят." },
  { id: "ege12u_0028", variant: "став..шь (цветы в вазу)", answer: "и", correct_letter: "и", correct_spelling: "ставишь (цветы в вазу)", explanation: "Ставить относится ко II спряжению." },
  { id: "ege12u_0029", variant: "(звери) чу..т", answer: "ю", correct_letter: "ю", correct_spelling: "(звери) чуют", explanation: "Чуять относится к I спряжению, пишется -ют." },
  { id: "ege12u_0030", variant: "(пассажиры) дремл..т", answer: "ю", correct_letter: "ю", correct_spelling: "(пассажиры) дремлют", explanation: "Дремать относится к I спряжению, пишется -ют." },
  { id: "ege12u_0031", variant: "(они) выдерж..т", answer: "а", correct_letter: "а", correct_spelling: "(они) выдержат", explanation: "Выдержать относится ко II спряжению в этой форме." },
  { id: "ege12u_0032", variant: "заблещ..т (ягнята)", answer: "у", correct_letter: "у", correct_spelling: "заблещут (ягнята)", explanation: "В 3-м лице множественного числа I спряжения пишется -ут/-ют." },
  { id: "ege12u_0033", variant: "верт..шься", answer: "и", correct_letter: "и", correct_spelling: "вертишься", explanation: "Вертеть - исключение II спряжения." },
  { id: "ege12u_0034", variant: "отгон..шь (в сторону)", answer: "и", correct_letter: "и", correct_spelling: "отгонишь (в сторону)", explanation: "Отгонить относится ко II спряжению." },
  { id: "ege12u_0035", variant: "(дачники) кос..т (траву)", answer: "я", correct_letter: "я", correct_spelling: "(дачники) косят (траву)", explanation: "Косить относится ко II спряжению, пишется -ят." },
  { id: "ege12u_0036", variant: "(они) трат..т (деньги)", answer: "я", correct_letter: "я", correct_spelling: "(они) тратят (деньги)", explanation: "Тратить относится ко II спряжению." },
  { id: "ege12u_0037", variant: "(водопады) клокоч..т", answer: "у", correct_letter: "у", correct_spelling: "(водопады) клокочут", explanation: "Клокотать относится к I спряжению." },
  { id: "ege12u_0038", variant: "(ветры) гон..т (волны)", answer: "я", correct_letter: "я", correct_spelling: "(ветры) гонят (волны)", explanation: "Гнать - исключение II спряжения." },
  { id: "ege12u_0039", variant: "замес..шь (тесто)", answer: "и", correct_letter: "и", correct_spelling: "замесишь (тесто)", explanation: "Замесить относится ко II спряжению." },
  { id: "ege12u_0040", variant: "(кулинары) замес..т (тесто)", answer: "я", correct_letter: "я", correct_spelling: "(кулинары) замесят (тесто)", explanation: "Замесить относится ко II спряжению, пишется -ят." },
  { id: "ege12u_0041", variant: "(они) посел..тся (в деревне)", answer: "я", correct_letter: "я", correct_spelling: "(они) поселятся (в деревне)", explanation: "Поселиться относится ко II спряжению." },
  { id: "ege12u_0042", variant: "излеч..шься", answer: "и", correct_letter: "и", correct_spelling: "излечишься", explanation: "Излечиться относится ко II спряжению." },
  { id: "ege12u_0043", variant: "(ветер) засвищ..т", answer: "е", correct_letter: "е", correct_spelling: "(ветер) засвищет", explanation: "Засвистеть относится к I спряжению в этой форме." },
  { id: "ege12u_0044", variant: "загон..шь", answer: "и", correct_letter: "и", correct_spelling: "загонишь", explanation: "Загонить относится ко II спряжению." },
  { id: "ege12u_0045", variant: "(он) наточ..т (ножницы)", answer: "и", correct_letter: "и", correct_spelling: "(он) наточит (ножницы)", explanation: "Наточить относится ко II спряжению." },
  { id: "ege12u_0046", variant: "(они) топч..т (траву)", answer: "а", correct_letter: "а", correct_spelling: "(они) топчат (траву)", explanation: "Топтать относится ко II спряжению в этой форме." },
  { id: "ege12u_0047", variant: "раздел..шь (на части)", answer: "и", correct_letter: "и", correct_spelling: "разделишь (на части)", explanation: "Разделить относится ко II спряжению." },
  { id: "ege12u_0048", variant: "посе..шь (зёрна)", answer: "е", correct_letter: "е", correct_spelling: "посеешь (зёрна)", explanation: "Посеять относится к I спряжению." },
  { id: "ege12u_0049", variant: "(оладьи) жар..тся", answer: "я", correct_letter: "я", correct_spelling: "(оладьи) жарятся", explanation: "Жариться относится ко II спряжению." },
  { id: "ege12u_0050", variant: "обсуд..шь", answer: "и", correct_letter: "и", correct_spelling: "обсудишь", explanation: "Обсудить относится ко II спряжению." },
  { id: "ege12u_0051", variant: "(зёрна) перемел..тся", answer: "ю", correct_letter: "ю", correct_spelling: "(зёрна) перемелются", explanation: "Перемолоть относится к I спряжению в этой форме." },
  { id: "ege12u_0052", variant: "(бабушки) нянч..тся (с внуками)", answer: "а", correct_letter: "а", correct_spelling: "(бабушки) нянчатся (с внуками)", explanation: "Нянчиться относится ко II спряжению." },
  { id: "ege12u_0053", variant: "(он) ропщ..т (на судьбу)", answer: "е", correct_letter: "е", correct_spelling: "(он) ропщет (на судьбу)", explanation: "Роптать относится к I спряжению." },
  { id: "ege12u_0054", variant: "(продавец) назнач..т (цену)", answer: "и", correct_letter: "и", correct_spelling: "(продавец) назначит (цену)", explanation: "Назначить относится ко II спряжению." },
  { id: "ege12u_0055", variant: "танцу..шь", answer: "е", correct_letter: "е", correct_spelling: "танцуешь", explanation: "Танцевать относится к I спряжению." },
  { id: "ege12u_0056", variant: "(дети) завяж..т (шнурки)", answer: "у", correct_letter: "у", correct_spelling: "(дети) завяжут (шнурки)", explanation: "Завязать относится к I спряжению в этой форме." },
  { id: "ege12u_0057", variant: "(они) шепч..тся", answer: "у", correct_letter: "у", correct_spelling: "(они) шепчутся", explanation: "Шептаться относится к I спряжению." },
  { id: "ege12u_0058", variant: "постигн..шь (умом)", answer: "е", correct_letter: "е", correct_spelling: "постигнешь (умом)", explanation: "Постигнуть относится к I спряжению." },
  { id: "ege12u_0059", variant: "(родители) щекоч..т (ребёнка)", answer: "у", correct_letter: "у", correct_spelling: "(родители) щекочут (ребёнка)", explanation: "Щекотать относится к I спряжению." },
  { id: "ege12u_0060", variant: "перевяж..шь (руку)", answer: "е", correct_letter: "е", correct_spelling: "перевяжешь (руку)", explanation: "Перевязать относится к I спряжению в этой форме." }
];

const BUILT_IN_TASKS = [...DEFAULT_TASKS, ...EXTRA_TASKS];

const MAZE = [
  [0, 0, 0, 1, 0, 0],
  [1, 1, 0, 1, 0, 1],
  [0, 0, 0, 0, 0, 0],
  [0, 1, 1, 1, 1, 0],
  [0, 0, 0, 0, 1, 0],
  [1, 1, 0, 0, 0, 0]
];

const state = {
  selectedAvatar: ASSETS.avatars[0],
  mana: 0,
  stage: 0,
  algorithmStep: 0,
  algorithmUnlocked: [],
  algorithmQuestionIndex: 0,
  algorithmPracticeQueue: [],
  algorithmPracticeDone: 0,
  cauldronQueue: [],
  cauldronDone: 0,
  cauldronMistakes: 0,
  cauldronFx: "",
  cauldronTarget: "",
  tasks: BUILT_IN_TASKS,
  mazeTaskIndex: 0,
  mazePos: { r: 0, c: 0 },
  pendingMove: null,
  bonusClaimed: false,
  mazeReward: "",
  correctStreak: 0,
  successStar: "",
  reviewMistakes: [],
  reviewIndex: 0,
  reviewAnswer: "",
  musicEnabled: false,
  sfxEnabled: true,
  stats: { answered: 0, correct: 0, mistakes: 0 },
  mistakes: [],
  reviewMode: false
};

let audioContext = null;
let backgroundMusic = null;

const el = {
  startScreen: document.getElementById("startScreen"),
  gameScreen: document.getElementById("gameScreen"),
  finishScreen: document.getElementById("finishScreen"),
  avatarPicker: document.getElementById("avatarPicker"),
  startBtn: document.getElementById("startBtn"),
  stageKicker: document.getElementById("stageKicker"),
  stageTitle: document.getElementById("stageTitle"),
  manaText: document.getElementById("manaText"),
  musicToggle: document.getElementById("musicToggle"),
  sfxToggle: document.getElementById("sfxToggle"),
  mount: document.getElementById("stageMount"),
  statsPanel: document.getElementById("statsPanel"),
  mistakesPanel: document.getElementById("mistakesPanel"),
  restartBtn: document.getElementById("restartBtn"),
  reviewBtn: document.getElementById("reviewBtn")
};

function assetUrl(file) {
  return file;
}

function hydrateAssetImages(root = document) {
  root.querySelectorAll("img[data-asset]").forEach((img) => {
    const file = img.dataset.asset;
    if (img.dataset.hydratedAsset === file) return;
    img.dataset.hydratedAsset = file;
    img.onerror = () => {
      img.style.display = "none";
    };
    img.src = assetUrl(file);
  });
}

function setScreen(screen) {
  [el.startScreen, el.gameScreen, el.finishScreen].forEach((node) => node.classList.remove("active"));
  screen.classList.add("active");
}

function updateMana() {
  el.manaText.textContent = `Мана: ${state.mana}`;
}

function ensureBackgroundMusic() {
  if (backgroundMusic) return backgroundMusic;
  backgroundMusic = new Audio(assetUrl("Лунный Компас.mp3"));
  backgroundMusic.loop = true;
  backgroundMusic.volume = 0.32;
  return backgroundMusic;
}

function updateAudioButtons() {
  el.musicToggle.textContent = `Мелодия: ${state.musicEnabled ? "вкл" : "выкл"}`;
  el.sfxToggle.textContent = `Звуки: ${state.sfxEnabled ? "вкл" : "выкл"}`;
  el.musicToggle.classList.toggle("active", state.musicEnabled);
  el.sfxToggle.classList.toggle("active", state.sfxEnabled);
}

function setMusicEnabled(enabled) {
  state.musicEnabled = enabled;
  const music = ensureBackgroundMusic();
  if (enabled) {
    music.play().catch((error) => {
      state.musicEnabled = false;
      updateAudioButtons();
      console.warn("Браузер не дал включить мелодию без действия пользователя.", error);
    });
  } else {
    music.pause();
  }
  updateAudioButtons();
}

function toggleMusic() {
  setMusicEnabled(!state.musicEnabled);
}

function toggleSfx() {
  state.sfxEnabled = !state.sfxEnabled;
  updateAudioButtons();
}

function playTone(type) {
  if (!state.sfxEnabled) return;
  try {
    audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
    const now = audioContext.currentTime;
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();
    osc.type = type === "ok" ? "sine" : "triangle";
    osc.frequency.setValueAtTime(type === "ok" ? 620 : 190, now);
    osc.frequency.exponentialRampToValueAtTime(type === "ok" ? 980 : 90, now + 0.18);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(type === "ok" ? 0.18 : 0.13, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.24);
    osc.connect(gain).connect(audioContext.destination);
    osc.start(now);
    osc.stop(now + 0.26);
  } catch (error) {
    console.warn("Звук недоступен в этом браузере.", error);
  }
}

function awardCorrectStep() {
  state.correctStreak += 1;
  if (state.correctStreak > 0 && state.correctStreak % 5 === 0) {
    state.mana += 5;
    state.successStar = `Звезда успеха! ${state.correctStreak} верных шагов подряд, +5 маны.`;
    return state.successStar;
  }
  state.successStar = "";
  return "";
}

function resetCorrectStreak() {
  state.correctStreak = 0;
  state.successStar = "";
}

function renderSuccessStar() {
  if (!state.successStar) return "";
  return `
    <div class="success-star" aria-live="polite">
      <img data-asset="маленькая_звезда_успеха_без_фона.png" alt="">
      <span>${state.successStar}</span>
    </div>
  `;
}

function recordMistake(mistake) {
  state.stats.mistakes += 1;
  state.mistakes.push({
    id: mistake.id || `mistake_${state.mistakes.length + 1}`,
    mode: mistake.mode || "Задание",
    type: mistake.type || "letter",
    prompt: mistake.prompt || mistake.variant || "",
    variant: mistake.variant || mistake.prompt || "",
    chosen: mistake.chosen || "",
    correct: mistake.correct || mistake.correct_letter || "",
    correct_letter: mistake.correct_letter || mistake.correct || "",
    correct_spelling: mistake.correct_spelling || "",
    explanation: mistake.explanation || "",
    options: mistake.options || []
  });
}

function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5);
}

function renderAvatarFigure(className) {
  return `<img class="${className}" data-asset="${state.selectedAvatar.file}" alt="">`;
}

function normalizeLetter(value) {
  return String(value || "").trim().toLowerCase().slice(0, 1);
}

function renderAvatars() {
  el.avatarPicker.innerHTML = ASSETS.avatars.map((avatar, index) => `
    <button class="avatar-card ${index === 0 ? "selected" : ""}" type="button" data-avatar="${avatar.id}">
      <img data-asset="${avatar.file}" alt="">
      <span>${avatar.label}</span>
    </button>
  `).join("");
  hydrateAssetImages(el.avatarPicker);
  el.avatarPicker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-avatar]");
    if (!button) return;
    state.selectedAvatar = ASSETS.avatars.find((avatar) => avatar.id === button.dataset.avatar) || ASSETS.avatars[0];
    el.avatarPicker.querySelectorAll(".avatar-card").forEach((node) => node.classList.remove("selected"));
    button.classList.add("selected");
  });
}

function startGame() {
  if (state.musicEnabled) {
    ensureBackgroundMusic().play().catch((error) => console.warn("Не удалось продолжить мелодию.", error));
  }
  state.mana = 0;
  state.stage = 1;
  state.algorithmStep = 0;
  state.algorithmUnlocked = [];
  state.algorithmQuestionIndex = 0;
  state.algorithmPracticeQueue = [];
  state.algorithmPracticeDone = 0;
  state.stats = { answered: 0, correct: 0, mistakes: 0 };
  state.mistakes = [];
  state.reviewMode = false;
  state.mazeTaskIndex = 0;
  state.mazePos = { r: 0, c: 0 };
  state.pendingMove = null;
  state.bonusClaimed = false;
  state.mazeReward = "";
  state.correctStreak = 0;
  state.successStar = "";
  state.reviewMistakes = [];
  state.reviewIndex = 0;
  setScreen(el.gameScreen);
  updateMana();
  renderAlgorithmStage();
}

function setStageTitle(kicker, title) {
  el.stageKicker.textContent = kicker;
  el.stageTitle.textContent = title;
}

function renderAlgorithmStage(feedback = "") {
  setStageTitle("Этап 1", "Открываем алгоритм");
  const currentQuestion = ALGORITHM_QUESTIONS[state.algorithmQuestionIndex];
  const done = state.algorithmQuestionIndex >= ALGORITHM_QUESTIONS.length;
  const practiceTask = done ? getAlgorithmPracticeTask() : null;
  el.mount.innerHTML = `
    <div class="algorithm-stage ${done ? "algorithm-stage-open" : ""}">
      <div class="algorithm-board reveal-board ${done ? "clean-board" : ""} asset-panel">
        <img class="algorithm-full-image" data-asset="Алгоритм полный.png" alt="Как определить спряжение глагола">
        ${renderAvatarFigure("algorithm-mascot")}
        ${done ? "" : `
          <div class="algorithm-overlays" aria-hidden="true">
            ${renderAlgorithmMask()}
            ${ALGORITHM_REVEAL_ZONES.map(renderAlgorithmOverlay).join("")}
          </div>
        `}
      </div>
      <div class="algorithm-side">
        <div class="scroll-card asset-panel">
          <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
        <div class="algorithm-panel-content">
          <h3>${done ? "Тренировка по алгоритму" : `Вопрос ${state.algorithmQuestionIndex + 1} из ${ALGORITHM_QUESTIONS.length}`}</h3>
          ${renderSuccessStar()}
          ${done ? renderAlgorithmPractice(practiceTask) : renderAlgorithmQuestion(currentQuestion)}
          ${feedback ? renderAlgorithmFeedback(feedback) : ""}
        </div>
        </div>
      </div>
    </div>
  `;
  hydrateAssetImages(el.mount);
  wireAlgorithmQuiz();
}

function renderAlgorithmOverlay(zone) {
  const opened = state.algorithmUnlocked.includes(zone.id);
  return `
    <div class="algorithm-cover ${opened ? "opened" : ""}" style="--x:${zone.x}%; --y:${zone.y}%; --w:${zone.w}%; --h:${zone.h}%;">
      <span>?</span>
    </div>
  `;
}

function renderAlgorithmMask() {
  const opened = ALGORITHM_REVEAL_ZONES.filter((zone) => state.algorithmUnlocked.includes(zone.id));
  const xCuts = uniqueSorted([0, 100, ...opened.flatMap((zone) => [zone.x, zone.x + zone.w])]);
  const yCuts = uniqueSorted([0, 100, ...opened.flatMap((zone) => [zone.y, zone.y + zone.h])]);
  const pieces = [];
  for (let yi = 0; yi < yCuts.length - 1; yi += 1) {
    for (let xi = 0; xi < xCuts.length - 1; xi += 1) {
      const x = xCuts[xi];
      const y = yCuts[yi];
      const w = xCuts[xi + 1] - x;
      const h = yCuts[yi + 1] - y;
      if (w <= 0 || h <= 0) continue;
      const centerX = x + w / 2;
      const centerY = y + h / 2;
      if (opened.some((zone) => isPointInZone(centerX, centerY, zone))) continue;
      pieces.push(`<span class="algorithm-mask-piece" style="--x:${x}%; --y:${y}%; --w:${w}%; --h:${h}%;"></span>`);
    }
  }
  return `<div class="algorithm-mask">${pieces.join("")}</div>`;
}

function uniqueSorted(values) {
  return [...new Set(values.map((value) => Math.max(0, Math.min(100, Number(value.toFixed(2))))))].sort((a, b) => a - b);
}

function isPointInZone(x, y, zone) {
  return x >= zone.x && x <= zone.x + zone.w && y >= zone.y && y <= zone.y + zone.h;
}

function renderAlgorithmQuestion(question) {
  const options = shuffleOptions(question.options, question.correct);
  return `
    <div class="algorithm-task-box">
      <p class="algorithm-question">${question.question}</p>
    </div>
    <div class="choice-grid algorithm-answer-grid">
      ${options.map((option) => `
        <button class="choice-btn asset-choice algorithm-answer" type="button" data-answer="${escapeHtml(option)}">
          <img class="asset-bg" data-asset="плашка_алгоритм_2_без_фона.png" alt="">
          <span>${option}</span>
        </button>
      `).join("")}
    </div>
  `;
}

function shuffleOptions(options, correct) {
  const shuffled = shuffle(options);
  if (shuffled.length > 1 && shuffled[0] === correct) {
    shuffled.push(shuffled.shift());
  }
  return shuffled;
}

function renderAlgorithmFeedback(message) {
  const ok = message.startsWith("Верно") || message.includes("+");
  return `
    <div class="algorithm-feedback ${ok ? "ok" : "bad"}">
      <span>${message}</span>
    </div>
  `;
}

function renderAlgorithmDone() {
  return renderAlgorithmPractice(getAlgorithmPracticeTask());
}

function getAlgorithmPracticeTask() {
  if (!state.algorithmPracticeQueue.length || state.algorithmPracticeDone >= 10) return null;
  return state.algorithmPracticeQueue[0];
}

function renderAlgorithmPractice(task) {
  const ready = state.algorithmPracticeDone >= 10;
  if (!task || ready) {
    return `
      <div class="algorithm-task-box">
        <p class="algorithm-question">Тренировка готова: ${state.algorithmPracticeDone} из 10.</p>
        <div class="progress-line">Ману можно нести к котелкам.</div>
      </div>
      <button class="primary-btn asset-button go-cauldron" type="button">
        <img class="asset-bg" data-asset="плашка_алгоритм_5_без_фона.png" alt="">
        <span>К котелкам</span>
      </button>
    `;
  }
  return `
    <div class="algorithm-task-box">
      <p class="algorithm-question">Определи спряжение</p>
      <div class="practice-word">${task.infinitive}</div>
      <div class="progress-line">Тренировка: ${state.algorithmPracticeDone} из 10 · запас слов: ${state.algorithmPracticeQueue.length}</div>
    </div>
    <div class="choice-grid algorithm-answer-grid">
      <button class="choice-btn asset-choice algorithm-practice-answer" type="button" data-answer="I">
        <img class="asset-bg" data-asset="плашка_алгоритм_2_без_фона.png" alt="">
        <span>I спряжение</span>
      </button>
      <button class="choice-btn asset-choice algorithm-practice-answer" type="button" data-answer="II">
        <img class="asset-bg" data-asset="плашка_алгоритм_5_без_фона.png" alt="">
        <span>II спряжение</span>
      </button>
    </div>
  `;
}

function wireAlgorithmQuiz() {
  el.mount.querySelectorAll(".algorithm-answer").forEach((button) => {
    button.addEventListener("click", () => answerAlgorithmQuestion(button.dataset.answer));
  });
  el.mount.querySelectorAll(".algorithm-practice-answer").forEach((button) => {
    button.addEventListener("click", () => answerAlgorithmPractice(button.dataset.answer));
  });
  const next = el.mount.querySelector(".go-cauldron");
  if (next) next.addEventListener("click", () => renderCauldronStage("Переходим к котелкам. Если будет трудно, можно вернуться к алгоритму."));
}

function answerAlgorithmQuestion(answer) {
  const question = ALGORITHM_QUESTIONS[state.algorithmQuestionIndex];
  if (!question) return;
  if (answer === question.correct) {
    playTone("ok");
    const streakMessage = awardCorrectStep();
    if (!state.algorithmUnlocked.includes(question.zone)) {
      state.algorithmUnlocked.push(question.zone);
    }
    state.algorithmQuestionIndex += 1;
    if (state.algorithmQuestionIndex >= ALGORITHM_QUESTIONS.length) {
      state.algorithmUnlocked = ALGORITHM_REVEAL_ZONES.map((zone) => zone.id);
      state.mana += 3;
      state.algorithmPracticeQueue = shuffle(CONJUGATION_TASKS).slice(0, 20);
      state.algorithmPracticeDone = 0;
      updateMana();
      renderAlgorithmStage(`Верно! Алгоритм открыт, +3 маны.${streakMessage ? " " + streakMessage : ""}`);
      return;
    }
    updateMana();
    renderAlgorithmStage(`Верно! Открылась новая часть алгоритма.${streakMessage ? " " + streakMessage : ""}`);
  } else {
    playTone("bad");
    resetCorrectStreak();
    recordMistake({
      mode: "Алгоритм",
      type: "choice",
      prompt: question.question,
      chosen: answer,
      correct: question.correct,
      explanation: "Повтори этот шаг по схеме алгоритма.",
      options: question.options
    });
    renderAlgorithmStage("Пока нет. Посмотри на уже открытую часть и попробуй ещё раз.");
  }
}

function answerAlgorithmPractice(answer) {
  const task = state.algorithmPracticeQueue.shift();
  if (!task) return;
  if (answer === task.answer) {
    playTone("ok");
    state.mana += 1;
    const streakMessage = awardCorrectStep();
    state.algorithmPracticeDone += 1;
    updateMana();
    renderAlgorithmStage(`Верно! ${task.explanation} +1 мана.${streakMessage ? " " + streakMessage : ""}`);
  } else {
    playTone("bad");
    resetCorrectStreak();
    state.algorithmPracticeQueue.push(task);
    recordMistake({
      id: task.id,
      mode: "Тренировка по алгоритму",
      type: "conjugation",
      prompt: task.infinitive,
      chosen: answer,
      correct: task.answer,
      explanation: task.explanation,
      options: ["I", "II"]
    });
    renderAlgorithmStage(`Нужно ещё раз по алгоритму. ${task.explanation}`);
  }
}

function renderCauldronStage(message = "") {
  setStageTitle("Этап 2", "Магические котелки");
  if (!state.cauldronQueue.length) {
    state.cauldronQueue = shuffle(CONJUGATION_TASKS).slice(0, 20);
    state.cauldronDone = 0;
    state.cauldronMistakes = 0;
  }
  state.cauldronFx = "";
  state.cauldronTarget = "";
  drawCauldronTask(message);
}

function drawCauldronTask(message = "") {
  const task = state.cauldronQueue[0];
  if (state.cauldronDone >= 10 && state.mana >= 8) {
    renderMazeStage("Маны достаточно. Портал в лабиринт открыт.");
    return;
  }
  if (!task) {
    returnToAlgorithmPractice("Запас слов в котелках закончился. Возвращаемся к алгоритму и копим ману.");
    return;
  }
  const fxClass = state.cauldronFx ? `fx-${state.cauldronFx} target-${state.cauldronTarget}` : "";
  el.mount.innerHTML = `
    <div class="cauldron-stage ${fxClass}">
      <div class="mana-ribbon asset-card">
        <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
        <span>Мана: ${state.mana} · верно: ${state.cauldronDone}/10 · запас слов: ${state.cauldronQueue.length}</span>
      </div>
      <button class="return-algorithm asset-button" type="button" data-action="algorithm">
        <img class="asset-bg" data-asset="плашка_алгоритм_5_без_фона.png" alt="">
        <span>Вернуться к алгоритму</span>
      </button>
      ${renderSuccessStar()}
      <button class="cauldron cauldron-left" type="button" data-answer="I" aria-label="I спряжение">
        <img data-asset="котелок_1_без_фона.png" alt="">
        <span>I спряжение</span>
      </button>
      <div class="spell-scroll asset-card">
        <img class="asset-bg" data-asset="свиток_задания_без_фона.png" alt="">
        <div class="spell-text">
          <div class="task-word">${task.infinitive}</div>
          <p>В какой котелок отправить глагол?</p>
        </div>
      </div>
      <button class="cauldron cauldron-right" type="button" data-answer="II" aria-label="II спряжение">
        <img data-asset="котелок_2_без_фона.png" alt="">
        <span>II спряжение</span>
      </button>
      <div class="cauldron-effect" aria-hidden="true"></div>
      ${state.cauldronFx ? `
        <img class="cauldron-result-pop" data-asset="${state.cauldronFx === "ok" ? "котелок_верно_без_фона.png" : "котелок_неверно_без_фона.png"}" alt="">
      ` : ""}
      <img class="mana-drop drop-a" data-asset="капля_маны_без_фона.png" alt="">
      <img class="mana-drop drop-b" data-asset="капля_маны_без_фона.png" alt="">
      <div class="cauldron-feedback feedback asset-card ${message.startsWith("Верно") || message.includes("открыт") ? "ok" : message ? "bad" : ""}">
        <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
        <span>${message}</span>
      </div>
    </div>
  `;
  hydrateAssetImages(el.mount);
  el.mount.querySelectorAll(".cauldron").forEach((node) => node.addEventListener("click", () => answerCauldron(node.dataset.answer)));
  el.mount.querySelector("[data-action='algorithm']").addEventListener("click", () => returnToAlgorithmPractice());
}

function answerCauldron(answer) {
  const task = state.cauldronQueue.shift();
  if (!task) return;
  if (answer === task.answer) {
    playTone("ok");
    state.mana += 1;
    const streakMessage = awardCorrectStep();
    state.cauldronDone += 1;
    state.cauldronMistakes = 0;
    state.cauldronFx = "ok";
    state.cauldronTarget = answer;
    updateMana();
    drawCauldronTask(`Верно! ${task.explanation}${streakMessage ? " " + streakMessage : ""}`);
  } else {
    playTone("bad");
    resetCorrectStreak();
    state.cauldronQueue.push(task);
    state.cauldronMistakes += 1;
    state.cauldronFx = "bad";
    state.cauldronTarget = answer;
    recordMistake({
      id: task.id,
      mode: "Котелки",
      type: "conjugation",
      prompt: task.infinitive,
      chosen: answer,
      correct: task.answer,
      explanation: task.explanation,
      options: ["I", "II"]
    });
    if (state.cauldronMistakes >= 3 || state.mana < 1) {
      returnToAlgorithmPractice("Много ошибок в котелках. Возвращаемся к алгоритму и копим ману.");
      return;
    }
    drawCauldronTask(`Нужно повторить. ${task.explanation}`);
  }
}

function returnToAlgorithmPractice(message = "Возвращаемся к алгоритму: потренируй спряжение и накопи ману.") {
  state.algorithmUnlocked = ALGORITHM_REVEAL_ZONES.map((zone) => zone.id);
  state.algorithmQuestionIndex = ALGORITHM_QUESTIONS.length;
  state.algorithmPracticeQueue = shuffle(CONJUGATION_TASKS).slice(0, 20);
  state.algorithmPracticeDone = 0;
  state.cauldronMistakes = 0;
  renderAlgorithmStage(message);
}

function renderMazeStage(message = "") {
  setStageTitle("Этап 3", "Лабиринт");
  state.stage = 3;
  state.pendingMove = null;
  drawMaze(message);
}

function drawMaze(message = "") {
  const currentTask = getCurrentMazeTask();
  el.mount.innerHTML = `
    <div class="maze-stage">
      <div class="maze-scene">
        <img class="maze-scene-bg" data-asset="Фон_лабиринт.png" alt="">
        <div class="maze-board">
          ${MAZE.flatMap((row, r) => row.map((cell, c) => renderCell(cell, r, c))).join("")}
        </div>
      </div>
      <aside class="maze-task scroll-card asset-panel">
        <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
        <h3>Выбери ход</h3>
        <p>Перед переходом на клетку нужно решить задание.</p>
        <div class="move-grid">
          ${renderMoveButton("up", "↑", "Вверх")}
          ${renderMoveButton("right", "→", "Вправо")}
          ${renderMoveButton("left", "←", "Влево")}
          ${renderMoveButton("down", "↓", "Вниз")}
        </div>
        ${state.mazeReward ? `
          <div class="maze-reward" aria-live="polite">
            <img data-asset="орден_без_фона.png" alt="">
            <span>${state.mazeReward}</span>
          </div>
        ` : ""}
        ${renderSuccessStar()}
        <div class="maze-scroll-task asset-card">
          <img class="asset-bg" data-asset="свиток1_без_фона.png" alt="">
          <div class="maze-scroll-content">
            <div class="progress-line">Заданий решено: ${state.stats.answered}</div>
            <div class="task-word">${escapeHtml(currentTask.variant)}</div>
            <div class="letter-grid">
              ${buildLetterOptions(currentTask.correct_letter).map((letter) => `
                <button class="letter-btn asset-button" type="button" data-letter="${letter}" ${state.pendingMove ? "" : "disabled"}>
                  <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
                  <span>${letter.toUpperCase()}</span>
                </button>
              `).join("")}
            </div>
            <div class="feedback ${message.startsWith("Верно") ? "ok" : message ? "bad" : ""}">${message}</div>
          </div>
        </div>
      </aside>
    </div>
  `;
  hydrateAssetImages(el.mount);
  el.mount.querySelectorAll(".move-btn.available").forEach((button) => {
    button.addEventListener("click", () => chooseMazeMove(button.dataset.move));
  });
  el.mount.querySelectorAll(".letter-btn").forEach((button) => {
    button.addEventListener("click", () => answerMaze(button.dataset.letter));
  });
}

function renderCell(cell, r, c) {
  const classes = ["cell", `tile-${(r + c) % 3}`];
  if (cell === 1) classes.push("wall");
  if (r === 0 && c === 0) classes.push("start");
  if (r === 5 && c === 5) classes.push("finish");
  if (r === 4 && c === 2) classes.push("bonus");
  const tileFile = cell === 1
    ? "лабиринт_библиотека_без_фона.png"
    : r === 5 && c === 5
      ? "лабиринт_портал_без_фона.png"
      : r === 0 && c === 0
        ? "лабиринт_проход_без_фона.png"
        : ["лабиринт_дорожка_1_без_фона.png", "лабиринт_дорожка_2_без_фона.png", "лабиринт_дорожка_3_без_фона.png"][(r + c) % 3];
  const player = state.mazePos.r === r && state.mazePos.c === c ? renderAvatarFigure("player-token") : "";
  return `<div class="${classes.join(" ")}"><img class="tile-bg" data-asset="${tileFile}" alt="">${player}</div>`;
}

function renderMoveButton(move, icon, label) {
  const next = getNextPos(move);
  const available = isOpen(next.r, next.c);
  const selected = state.pendingMove === move;
  return `
    <button class="move-btn asset-button ${available ? "available" : ""} ${selected ? "selected" : ""}" type="button" data-move="${move}" aria-label="${label}" ${available ? "" : "disabled"}>
      <img class="asset-bg" data-asset="алгоритм_1_без_фона.png" alt="">
      <span>${icon}</span>
    </button>
  `;
}

function chooseMazeMove(move) {
  const next = getNextPos(move);
  if (!isOpen(next.r, next.c)) {
    state.pendingMove = null;
    state.mazeReward = "";
    drawMaze("Туда нельзя: библиотечная полка не пропускает.");
    return;
  }
  state.pendingMove = move;
  state.mazeReward = "";
  drawMaze("Ход выбран. Теперь выбери букву.");
}

function getNextPos(move) {
  const delta = {
    up: [-1, 0],
    down: [1, 0],
    left: [0, -1],
    right: [0, 1]
  }[move] || [0, 0];
  return { r: state.mazePos.r + delta[0], c: state.mazePos.c + delta[1] };
}

function isOpen(r, c) {
  return r >= 0 && r < MAZE.length && c >= 0 && c < MAZE[0].length && MAZE[r][c] === 0;
}

function getCurrentMazeTask() {
  return state.tasks[state.mazeTaskIndex % state.tasks.length] || DEFAULT_TASKS[0];
}

function buildLetterOptions(answer) {
  const letter = normalizeLetter(answer);
  const pairs = {
    е: ["е", "и"],
    и: ["е", "и"],
    у: ["у", "а"],
    а: ["у", "а"],
    ю: ["ю", "я"],
    я: ["ю", "я"],
    о: ["о", "а"],
    ы: ["ы", "и"]
  };
  return pairs[letter] || shuffle([letter, "е", "и", "а"].filter(Boolean)).slice(0, 4);
}

function answerMaze(letter) {
  const task = getCurrentMazeTask();
  if (!state.pendingMove) {
    drawMaze("Сначала выбери направление стрелкой.");
    return;
  }
  const next = getNextPos(state.pendingMove);
  if (!isOpen(next.r, next.c)) {
    state.pendingMove = null;
    drawMaze("Туда нельзя: библиотечная полка не пропускает.");
    return;
  }
  const correct = normalizeLetter(letter) === normalizeLetter(task.correct_letter);
  state.stats.answered += 1;
  if (correct) {
    playTone("ok");
    state.stats.correct += 1;
    state.mana += 1;
    const streakMessage = awardCorrectStep();
    state.mazeTaskIndex += 1;
    state.mazePos = next;
    state.pendingMove = null;
    if (next.r === 4 && next.c === 2 && !state.bonusClaimed) {
      state.bonusClaimed = true;
      state.mana += 20;
      state.mazeReward = "Орден найден! +20 маны";
    } else {
      state.mazeReward = "";
    }
    updateMana();
    if (next.r === 5 && next.c === 5) {
      showFinish();
      return;
    }
    const spelling = task.correct_spelling ? ` Верно: ${task.correct_spelling}.` : " Верно.";
    drawMaze(`${spelling} ${task.explanation}${state.mazeReward ? " " + state.mazeReward + "." : ""}${streakMessage ? " " + streakMessage : ""}`);
  } else {
    playTone("bad");
    resetCorrectStreak();
    state.mazeReward = "";
    recordMistake({
      id: task.id,
      mode: "Лабиринт",
      type: "letter",
      prompt: task.variant,
      variant: task.variant,
      chosen: letter,
      correct: task.correct_letter,
      correct_letter: task.correct_letter,
      correct_spelling: task.correct_spelling,
      explanation: task.explanation,
      options: buildLetterOptions(task.correct_letter)
    });
    drawMaze(`Неверно. Правильная буква: ${String(task.correct_letter).toUpperCase()}. ${task.explanation}`);
  }
}

function showFinish() {
  setScreen(el.finishScreen);
  el.statsPanel.innerHTML = `
    <div class="stat">Заданий пройдено: ${state.stats.answered}</div>
    <div class="stat">Правильных ответов: ${state.stats.correct}</div>
    <div class="stat">Ошибок: ${state.stats.mistakes}</div>
    <div class="stat">Мана: ${state.mana}</div>
  `;
  el.mistakesPanel.innerHTML = state.mistakes.length
    ? `<h3>Слова для повторения</h3>${state.mistakes.map((item) => `
      <div class="mistake-item">
        <strong>${escapeHtml(item.mode)}: ${escapeHtml(item.prompt || item.variant)}</strong><br>
        Выбрано: ${escapeHtml(formatReviewAnswer(item.chosen))}; нужно: ${escapeHtml(formatReviewAnswer(getReviewCorrectAnswer(item)))}.
        ${item.correct_spelling ? `<br>Правильно: ${escapeHtml(item.correct_spelling)}` : ""}
        <br>${escapeHtml(item.explanation || "")}
      </div>
    `).join("")}`
    : "<p>Ошибок нет. Отличный проход!</p>";
  el.reviewBtn.disabled = state.mistakes.length === 0;
  hydrateAssetImages(el.finishScreen);
}

function startMistakeReview() {
  if (!state.mistakes.length) return;
  state.stage = 1;
  state.reviewMode = true;
  state.reviewMistakes = [...state.mistakes];
  state.reviewIndex = 0;
  state.reviewAnswer = "";
  state.successStar = "";
  state.pendingMove = null;
  setScreen(el.gameScreen);
  updateMana();
  renderMistakeReview();
}

function renderMistakeReview(message = "") {
  setStageTitle("Разбор", "Ошибки по алгоритму");
  const item = state.reviewMistakes[state.reviewIndex];
  const answered = Boolean(state.reviewAnswer);
  if (!item) {
    el.mount.innerHTML = `
      <div class="algorithm-stage algorithm-stage-open">
        <div class="algorithm-board reveal-board clean-board asset-panel">
          <img class="algorithm-full-image" data-asset="Алгоритм полный.png" alt="Как определить спряжение глагола">
        </div>
        <div class="algorithm-side">
          <div class="scroll-card asset-panel">
            <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
            <div class="algorithm-panel-content">
              <h3>Ошибки разобраны</h3>
              <p>Можно вернуться к результатам или начать заново.</p>
              <button class="primary-btn asset-button review-finish" type="button">
                <img class="asset-bg" data-asset="плашка_алгоритм_5_без_фона.png" alt="">
                <span>К результатам</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    hydrateAssetImages(el.mount);
    el.mount.querySelector(".review-finish").addEventListener("click", () => setScreen(el.finishScreen));
    return;
  }
  const options = getReviewOptions(item);
  const correct = getReviewCorrectAnswer(item);
  el.mount.innerHTML = `
    <div class="algorithm-stage algorithm-stage-open">
      <div class="algorithm-board reveal-board clean-board asset-panel">
        <img class="algorithm-full-image" data-asset="Алгоритм полный.png" alt="Как определить спряжение глагола">
      </div>
      <div class="algorithm-side">
        <div class="scroll-card asset-panel">
          <img class="asset-bg" data-asset="плашка_задание_без_фона.png" alt="">
          <div class="algorithm-panel-content mistake-review-card">
            <h3>Ошибка ${state.reviewIndex + 1} из ${state.reviewMistakes.length}</h3>
            <div class="algorithm-task-box">
              <p class="algorithm-question">${escapeHtml(item.prompt || item.variant)}</p>
              <div class="progress-line">${escapeHtml(item.mode)} · попробуй решить ещё раз</div>
              ${answered ? `
                <div class="progress-line">Сейчас выбрано: ${escapeHtml(formatReviewAnswer(state.reviewAnswer))} · верно: ${escapeHtml(formatReviewAnswer(correct))}</div>
                ${item.correct_spelling ? `<div class="practice-word">${escapeHtml(item.correct_spelling)}</div>` : ""}
                <p>${escapeHtml(item.explanation || "")}</p>
              ` : ""}
            </div>
            ${answered ? "" : `
              <div class="choice-grid algorithm-answer-grid">
                ${options.map((option) => `
                  <button class="choice-btn asset-choice review-answer" type="button" data-answer="${escapeHtml(option)}">
                    <img class="asset-bg" data-asset="плашка_алгоритм_2_без_фона.png" alt="">
                    <span>${escapeHtml(formatReviewAnswer(option))}</span>
                  </button>
                `).join("")}
              </div>
            `}
            ${message ? renderAlgorithmFeedback(message) : ""}
            ${answered ? `
              <button class="primary-btn asset-button review-next" type="button">
                <img class="asset-bg" data-asset="плашка_алгоритм_5_без_фона.png" alt="">
                <span>${state.reviewIndex + 1 >= state.reviewMistakes.length ? "Завершить" : "Следующая ошибка"}</span>
              </button>
            ` : ""}
          </div>
        </div>
      </div>
    </div>
  `;
  hydrateAssetImages(el.mount);
  el.mount.querySelectorAll(".review-answer").forEach((button) => {
    button.addEventListener("click", () => answerMistakeReview(button.dataset.answer));
  });
  const next = el.mount.querySelector(".review-next");
  if (next) next.addEventListener("click", () => {
    state.reviewIndex += 1;
    state.reviewAnswer = "";
    renderMistakeReview();
  });
}

function getReviewCorrectAnswer(item) {
  return item.correct || item.correct_letter || "";
}

function getReviewOptions(item) {
  const correct = getReviewCorrectAnswer(item);
  if (item.options && item.options.length) return [...new Set(item.options.map(String))];
  if (item.type === "conjugation") return ["I", "II"];
  if (item.type === "letter") return buildLetterOptions(correct);
  return [correct, item.chosen, "По личному окончанию", "Исключения"].filter(Boolean);
}

function formatReviewAnswer(value) {
  if (value === "I") return "I спряжение";
  if (value === "II") return "II спряжение";
  const text = String(value);
  return text.length <= 2 ? text.toUpperCase() : text;
}

function answerMistakeReview(answer) {
  const item = state.reviewMistakes[state.reviewIndex];
  if (!item) return;
  const correct = getReviewCorrectAnswer(item);
  state.reviewAnswer = answer;
  const ok = normalizeReviewAnswer(answer) === normalizeReviewAnswer(correct);
  playTone(ok ? "ok" : "bad");
  renderMistakeReview(ok ? "Верно, ошибка разобрана." : "Пока нет. Посмотри на алгоритм и правильный ответ.");
}

function normalizeReviewAnswer(value) {
  return String(value || "").trim().toLowerCase();
}

function handleMazeKeydown(event) {
  if (state.stage !== 3 || !el.gameScreen.classList.contains("active")) return;
  const moveByKey = {
    ArrowUp: "up",
    ArrowRight: "right",
    ArrowDown: "down",
    ArrowLeft: "left"
  };
  const move = moveByKey[event.key];
  if (!move) return;
  event.preventDefault();
  chooseMazeMove(move);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function init() {
  renderAvatars();
  hydrateAssetImages();
  updateMana();
  updateAudioButtons();
  el.startBtn.addEventListener("click", startGame);
  el.restartBtn.addEventListener("click", startGame);
  el.reviewBtn.addEventListener("click", startMistakeReview);
  el.musicToggle.addEventListener("click", toggleMusic);
  el.sfxToggle.addEventListener("click", toggleSfx);
  document.addEventListener("keydown", handleMazeKeydown);
}

init();
