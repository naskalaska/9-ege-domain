const ASSET = "assets/";
const DEBUG_CELLS = false;
const DEMO_MODE = !window.location.pathname.startsWith("/full-games/");
const DEMO_TURN_LIMIT = 20;

const characters = [
  { id: "cat", label: "Кот", file: "кот_без_фона.png" },
  { id: "grayCat", label: "Серый кот", file: "серый_кот_без_фона.png" },
  { id: "bunny", label: "Зайчик", file: "зайчик_без_фона.png" },
  { id: "fox", label: "Лисица", file: "лисица_без_фона.png" },
  { id: "raccoon", label: "Енот", file: "енот_без_фона.png" },
  { id: "hedgehog", label: "Ёжик", file: "ёжик_без_фона.png" },
  { id: "owl", label: "Сова", file: "сова_без_фона.png" },
  { id: "teacher", label: "Учитель", file: "учитель_без_фона.png", role: "teacher" }
];

const boardCells = [
  { id: 1, x: 10.8, y: 53.9, type: "truth", oge: 1 },
  { id: 2, x: 15.7, y: 44.5, type: "action", oge: 2 },
  { id: 3, x: 23.0, y: 39.8, type: "truth", oge: 3 },
  { id: 4, x: 31.1, y: 32.9, type: "surprise" },
  { id: 5, x: 38.2, y: 22.5, type: "action", oge: 4 },
  { id: 6, x: 47.6, y: 29.8, type: "truth", oge: 5 },
  { id: 7, x: 58.4, y: 34.2, type: "action", oge: 6 },
  { id: 8, x: 70.5, y: 33.5, type: "surprise" },
  { id: 9, x: 80.2, y: 40.8, type: "truth", oge: 7 },
  { id: 10, x: 83.2, y: 52.7, type: "action", oge: 8 },
  { id: 11, x: 74.7, y: 62.1, type: "truth", oge: 9 },
  { id: 12, x: 64.5, y: 69.2, type: "action", oge: 10 },
  { id: 13, x: 54.6, y: 72.9, type: "surprise" },
  { id: 14, x: 42.6, y: 74.1, type: "truth", oge: 11 },
  { id: 15, x: 31.0, y: 72.3, type: "action", oge: 12 },
  { id: 16, x: 19.1, y: 66.1, type: "truth", oge: 13 },
  { id: 17, x: 15.1, y: 57.8, type: "surprise" },
  { id: 18, x: 8.8, y: 46.0, type: "action", oge: 5 }
];

const ogeTitles = {
  1: "Изложение",
  2: "Синтаксический анализ: грамматическая основа",
  3: "Синтаксический анализ: характеристика предложения",
  4: "Пунктуационный анализ: правило и пример",
  5: "Пунктуационный анализ: расстановка знаков",
  6: "Орфографический анализ: объяснение написания",
  7: "Орфографический анализ: применение правил",
  8: "Грамматические нормы",
  9: "Грамматическая синонимия словосочетаний",
  10: "Анализ содержания текста",
  11: "Средства выразительности",
  12: "Лексический анализ",
  13: "Сочинение"
};

const pairCards = [
  {
    oge: 1,
    studentTruth: "Как ты пишешь изложения? Расскажи, какие приёмы сжатия ты знаешь",
    studentTruthHint: "Опиши любой приём сжатия из известных. Какую оценку ты обычно получаешь за содержание, какую - за грамотность?",
    studentAction: "Сократи фрагмент до 2 предложений, сохранив главную мысль.\n\nФрагмент:\nВ начале учебного года класс кажется собранием случайных людей. Кто-то громко шутит, кто-то молчит, кто-то делает вид, что ему всё равно. Но постепенно появляются общие воспоминания: первая контрольная, смешная ошибка у доски, удачный проект, разговор после урока. Именно такие мелочи превращают группу учеников в команду.",
    studentAnswer: "В начале учебного года класс кажется случайной группой людей. Но общие события и воспоминания постепенно превращают учеников в команду.",
    teacherTruth: "Расскажите, как лучше всего подготовиться к изложению?",
    teacherAction: "За 30 секунд покажите на этом фрагменте два приёма сжатия: что можно исключить, а что можно обобщить. \nФрагмент:\nВ начале учебного года класс кажется собранием случайных людей. Кто-то громко шутит, кто-то молчит, кто-то делает вид, что ему всё равно. Но постепенно появляются общие воспоминания: первая контрольная, смешная ошибка у доски, удачный проект, разговор после урока. Именно такие мелочи превращают группу учеников в команду.",
    teacherHint: "Можно показать исключение деталей и обобщение отдельных примеров общей формулировкой."
  },
  {
    oge: 2,
    studentTruth: "Объясни разницу между простым глагольным сказуемым, составным глагольным сказуемым и составным именным сказуемым. Приведи по одному примеру о себе или о классе.",
    studentTruthHint: "ПГС: я читаю.\nСГС: я хочу читать.\nСИС: урок был интересным.",
    studentAction: "Найди грамматические основы.\n\n1. Девятиклассники быстро привыкли к новому кабинету.\n2. Первое задание оказалось неожиданно простым.\n3. Учитель сказал повторять правила маленькими порциями.",
    studentAnswer: "1. девятиклассники привыкли;\n2. задание оказалось простым;\n3. Учитель сказал",
    teacherTruth: "Расскажите о двух подвохах, которые нужно всегда проверять при поиске Грамматической основы",
    teacherAction: "Объясните за 30 секунд, как не потерять составное именное сказуемое.",
    teacherHint: "Ищем не только один глагол, а весь смысловой центр сказуемого."
  },
  {
    oge: 3,
    studentTruth: "Какие типы предложений ты знаешь? По количеству грамматических основ, по характеру грамматической основы?",
    studentTruthHint: "Он писал. Он писал, потому что хотел разобраться. Мне сегодня прохладно. Видишь того воробья? В дверь стучат.",
    studentAction: "Дай характеристику предложения.\n\n Уставший отвсей суеты, я больше не хотел туда возвращаться",
    studentAnswer: "Простое предложение, двусоставное, полное, осложнено обособленным определением, выраженным причастным оборотом",
    teacherTruth: "Нужно ли вести конспекты, копить теорию в отдельной тетрадке?",
    teacherAction: "Объясните короткий алгоритм: как отличить простое осложнённое предложение от сложного.",
    teacherHint: "Ключевой шаг: найти грамматические основы, а потом уже искать осложняющие элементы."
  },
  {
    oge: 4,
    studentTruth: "Расскажи, какая пунктуационная тема кажется тебе самой понятной, а какая - самой опасной. Объясни почему: однородные члены, обращение, вводные слова, причастный/деепричастный оборот, сложное предложение.",
    studentTruthHint: "Назови тему, правило, один пример и место, где чаще всего ошибаешься.",
    studentAction: "Соотнеси правило и пример.\n\nПравила:\nА) Запятая между частями сложного предложения.\nБ) Запятая при обращении.\nВ) Запятая при вводном слове.\n\nПримеры:\n1. Ребята, попробуем сыграть ещё один круг.\n2. Кажется, эта игра поможет нам познакомиться.\n3. Прозвенел звонок, и класс быстро собрался.",
    studentAnswer: "А3, Б1, В2.",
    teacherTruth: "Я постоянно теряю запятые, закрывающие придаточное предложение. Что делать?",
    teacherAction: "Покажите одну из платформ, с которой вы работаете для закрепления пунктуации",
    
  },
  {
    oge: 5,
    studentTruth: "Как много пунктуационных ошибок ты совершаешь в сочинениях, изложениях? Можешь ли ты назвать правило, которое вызывает особенные сложности?",
    studentTruthHint: "-",
    studentAction: "Поставь запятые.\n\nОбезумевший от жары он носился между местными ларьками но никто не мог ему помочь ни кассир музея ни продавец из сувенирной лавки ни аниматор охравнявший опустевшие аттракционы.",
    studentAnswer: "Обезумевший от жары, он носился между местными ларьками, но никто не мог ему помочь: ни кассир музея, ни продавец из сувенирной лавки, ни аниматор, охранявший опустевшие аттракционы.",
    explanation: "Причастные обороты обособляются после определяемого слова, в любом положении, если ОС - личное местоимение. Запятая в СПП (перед но). Обобщающее слово (никто) перед однородными членами преложения, поэтому двоеточие",
    teacherTruth: "Расскажите, почему «слышу паузу - ставлю запятую» не работает как надёжный способ.",
    teacherAction: "Дайте лайфхак: что сначала искать в сложном предложении перед расстановкой запятых.",
    teacherHint: "Сначала основы и границы частей, потом союзы и правило."
  },
  {
    oge: 6,
    studentTruth: "Расскажи, какое орфографическое правило ты можешь объяснить другому человеку без подготовки. Обязательно назови правило и приведи пример.",
    studentTruthHint: "Формула: правило - сигнал - пример - почему именно так.",
    studentAction: "Выбери варианты, где объяснение написания верное.\n\n1. РУМЯНЫЙ - В отымённых прилагательных с суффиксом -ЯН- пишется одна Н.\n2. ПРИШКОЛЬНЫЙ - приставка ПРИ- пишется в значении приближения.\n3. Она была ВОСПИТАНА в строгости - пишется Н в кратком прилагателном.\n4. СБЕЖАТЬ - приставка С- неизменяемая.\n5. НЕВЕЖЛИВЫЙ - НЕ с прилагательным пишется слитно, если слово можно заменить синонимом без НЕ.",
    studentAnswer: "4, 5.",
    explanation: "1 неверно; 2 неверно: «пришкольный» - близость, а не приближение; 3 неверно в формулировке; 4 и 5 верно.",
    teacherTruth: "Расскажите, почему ученики часто знают слово, но не могут выбрать правильное объяснение написания.",
    teacherAction: "Покажите одну из ваших любимых игр/приёмов/активностей на уроках по орфографии"
  },
  {
    oge: 7,
    studentTruth: "Расскажи, какие орфограммы тебе легче узнавать в словах: приставки, корни, суффиксы, Н/НН, НЕ с разными частями речи. Почему именно они?",
    studentTruthHint: "Назови орфограмму, её сигнал и пример.",
    studentAction: "Вставь пропущенные буквы.\n\n1. пр..коснуться к теме\n2. ра..сказать историю\n3. деревя..ый стол\n4. не..громкий голос\n5. выб..рать ответ",
    studentAnswer: "1. прикоснуться;\n2. рассказать;\n3. деревянный;\n4. негромкий;\n5. выбирать.",
    explanation: "прикоснуться - приставка ПРИ-; рассказать - рас- перед глухим согласным; деревянный - исключение; негромкий - можно заменить синонимом «тихий»; выбирать - БИР/БЕР, есть суффикс -А-.",
    teacherTruth: "Ваше любимое правило орфографии?",
    teacherAction: "За 30 секунд расскажите о любимом приёме для запоминания словарных слов"
  },
  {
    oge: 8,
    studentTruth: "Прочитай слова: договоры, торты, красивее.",
    studentTruthHint: "Можно привести бытовую фразу и исправить её по норме.",
    studentAction: "Раскрой скобки, соблюдая грамматическую норму.\n\n1. Я купила пару классных (носки).\n2. Я подошёл к (оба) ученикам.\n3. Этот ответ оказался (удачный) предыдущего.\n4. В коридоре стояло около (полтораста) человек.",
    studentAnswer: "1. носков;\n2. обоим;\n3. удачнее;\n4. полутораста.",
    teacherTruth: "Правда ли, что просмотр глупых передач может помочь выучить грамматические нормы?",
    teacherAction: "Назовите топ-3 грамматические ошибки на экзамене"
  },
  {
    oge: 9,
    studentTruth: "Объясни разницу между согласованием, управлением и примыканием. Приведи по одному примеру из школьной жизни.",
    studentTruthHint: "Согласование: осенний день. Управление: день осени. Примыкание: говорить уверенно.",
    studentAction: "Замени словосочетание синонимичным, изменив тип связи.\n\n1. кабинет школы\n2. говорить с уверенностью\n3. осенний воздух",
    studentAnswer: "1. школьный кабинет;\n2. уверенно говорить;\n3. воздух осени.",
    teacherTruth: "Расскажите историю о типах отношений между словами",
    teacherAction: "Объясните на примере «мамина улыбка - улыбка мамы», почему меняется тип связи.",
  },
  {
    oge: 10,
    studentTruth: "Расскажи, как ты понимаешь основную мысль текста. Чем она отличается от темы? Приведи пример: тема - «дружба», основная мысль - «дружба проверяется поступками».",
    studentTruthHint: "Тема отвечает «о чём?», основная мысль - «что хотел сказать автор?».",
    studentAction: "Прочитай мини-текст и выбери утверждения, которые соответствуют его содержанию.\n\nВ начале сентября Илья почти ни с кем не разговаривал. На переменах он стоял у окна и делал вид, что рассматривает двор. Однажды на уроке русского языка учитель предложил ребятам объяснить правило соседу по парте. Илья тихо, но очень понятно рассказал Маше о грамматической основе. После урока она сказала: «Ты объясняешь лучше учебника». С этого дня Илья стал чаще поднимать руку.\n\nУтверждения:\n1. Илья любил быть в центре внимания.\n2. Илья помог однокласснице разобраться в теме.\n3. После похвалы Илья стал увереннее.\n4. Маша объяснила Илье грамматическую основу.\n5. Учитель предложил ребятам работать в парах.",
    studentAnswer: "2, 3, 5.",
    teacherTruth: "Вам нравятся тексты ОГЭ?",
    teacherAction: "Дайте быстрый алгоритм проверки утверждения по тексту.",
    teacherHint: "Найти место в тексте, сопоставить смысл, не добавлять того, чего нет."
  },
  {
    oge: 11,
    studentTruth: "Расскажи, какое средство выразительности ты узнаёшь увереннее всего: эпитет, метафору, сравнение, олицетворение, фразеологизм. Объясни на своём примере.",
    studentTruthHint: "Назови средство, признак и придумай короткий пример.",
    studentAction: "Найди средство выразительности.\n\n1. Осенний город светился, как раскрытая книга.\n2. Фонари подмигивали прохожим.\n3. Тёплый, медовый свет лился из окон.\n4. После первой игры лёд между ребятами растаял.",
    studentAnswer: "1. сравнение;\n2. олицетворение;\n3. эпитет;\n4. метафора.",
    teacherTruth: "Расскажите, какое средство выразительности дети чаще всего путают с метафорой.",
    teacherAction: "Объясните разницу между сравнением и метафорой на одной паре примеров.",
  },
  {
    oge: 12,
    studentTruth: "Расскажи, что тебе легче искать в тексте: синоним, антоним, фразеологизм, разговорное слово, слово по лексическому значению. Почему?",
    studentTruthHint: "Опиши, по каким признакам ты находишь нужное слово в контексте.",
    studentAction: "Выполни лексический анализ.\n\nМини-текст:\nСначала Артём держался особняком, но потом втянулся в разговор. Он оказался человеком наблюдательным: заметил, кто в классе шутит, кто стесняется, а кто берёт на себя роль организатора. «Ты прямо психолог», - улыбнулась Лена.\n\nЗадания:\n1. Найди слово со значением «в стороне от других, отдельно».\n2. Найди слово со значением «включился, начал участвовать».\n3. Найди разговорное выражение со значением «очень похож на кого-то по качеству».",
    studentAnswer: "1. особняком;\n2. втянулся;\n3. прямо психолог.",
    teacherTruth: "Расскажите, почему лексический анализ - это не только словарный запас, но и внимательное чтение контекста.",
    teacherAction: "Покажите, как искать слово по значению."
  },
  {
    oge: 13,
    studentTruth: "Расскажи, какой тип сочинения тебе ближе: о языке, по фрагменту текста или по нравственному понятию. Что легче: сформулировать тезис, найти пример, объяснить пример или написать вывод?",
    studentTruthHint: "Ответ можно построить по схеме: тезис - трудность - пример - что помогает.",
    studentAction: "Выбери один вопрос и ответь устно по схеме: тезис - пример - объяснение - вывод.\n\n1. Почему важно уметь слушать других?\n2. Какую роль в общении играет точное слово?\n3. Что помогает человеку почувствовать себя частью класса?\n\nМини-схема:\nЯ считаю, что...\nЭто видно, например, когда...\nЭтот пример показывает, что...\nЗначит,...",
    studentAnswer: "Я считаю, что человеку помогает почувствовать себя частью класса общее дело. Например, когда ребята вместе готовят проект или играют в командную игру, они начинают замечать сильные стороны друг друга. Такой опыт показывает, что класс становится ближе не из-за случайных разговоров, а из-за совместных действий. Значит, общее дело помогает людям почувствовать себя нужными.",
    teacherTruth: "Расскажите, какая часть сочинения чаще всего «сыпется»: тезис, комментарий к примеру, связь с темой или вывод.",
    teacherAction: "За 40 секунд покажите, как превратить одно слово «дружба» в нормальный тезис для сочинения."
  }
];

const studentSurprises = [
  "Назови три вещи, по которым тебя можно узнать: привычка, интерес, любимое занятие, фраза, предмет, музыка, стиль. Используй формулу «Причастие + существительное». Например: захватывающие фильмы.",
  "Назови причастие, которое опишет твоё настроение сегодня. Объясни выбор одним предложением.",
  "Расскажи о навыке, который не связан напрямую со школой, но может пригодиться в учёбе. Используй одно деепричастие.",
  "Ты считаешь себя удачливым человеком? У тебя есть какие-то ритуалы перед важной контрольной? Используй возвратный глагол при ответе.",
  "Вспомни самый яркий урок русского языка в школе. О чём он был? Хлопни, когда назовёшь в ответе местоимение",
  "Ты больше любишь работать в команде или один на один с задачей? Используй в ответе причастный оборот.",
  "Собаки или кошки? Арбуз или дыня? Огурец или помидор? Объясни один из выборов, используя причастный оборот",
  "Скажи, какие качества ты особенно ценишь в людях? Почему? Используй краткое причастие в ответе.",
  "Назови одну вещь, которую ты хотел бы улучшить в своём русском языке в этом году.",
  "Расскажи о слове, которое тебе нравится по звучанию или значению.",
  "Продолжи фразу: Мой идеальный урок... ",
  "Выбери: ты скорее «внимательный редактор», «быстрый спорщик», «тихий наблюдатель», «генератор идей» или «человек дедлайна»? Объясни.",
  "Ты используешь нейросети? Какие?",
  "Назови три блога/видео, которые ты открывала последними.",
  "Покажи/расскажи три любимых мема."
];

const teacherSurprises = [
  "Расскажите, какой Вы были в девятом классе: спокойной, спорящей, ответственной, ленивой, любопытной, тревожной, очень старательной?",
  "Назовите одну тему русского языка, которую Вы когда-то сами поняли не сразу.",
  "Расскажите о трёх ваших самых масштабных педагогических успехах",
  "Назовите ваш любимый репетиторский кейс",
  "Назовите платформы, с которыми вы работаете",
  "Как вы относитесь к невыполнению ДЗ, пропуску уроков?",
  "Назовите качество ученика, которое Вы цените больше правильного ответа.",
  "Расскажите о своих любимых приёмах"
];

const gameData = {
  student: {
    truth: pairCards.map((card) => ({
      id: `student_truth_${card.oge}`,
      oge: card.oge,
      title: `Задание ${card.oge}. ${ogeTitles[card.oge]}`,
      prompt: card.studentTruth,
      hint: card.studentTruthHint
    })),
    action: pairCards.map((card) => ({
      id: `student_action_${card.oge}`,
      oge: card.oge,
      title: `Задание ${card.oge}. ${ogeTitles[card.oge]}`,
      prompt: card.studentAction,
      answer: card.studentAnswer,
      explanation: card.explanation || ""
    })),
    surprise: studentSurprises.map((prompt, index) => ({
      id: `student_surprise_${index + 1}`,
      title: `Сюрприз ${index + 1}`,
      prompt
    }))
  },
  teacher: {
    truth: pairCards.map((card) => ({
      id: `teacher_truth_${card.oge}`,
      oge: card.oge,
      title: `Задание ${card.oge}. ${ogeTitles[card.oge]}`,
      prompt: card.teacherTruth,
      hint: card.teacherHint
    })),
    action: pairCards.map((card) => ({
      id: `teacher_action_${card.oge}`,
      oge: card.oge,
      title: `Задание ${card.oge}. ${ogeTitles[card.oge]}`,
      prompt: card.teacherAction,
      answer: card.teacherHint
    })),
    surprise: teacherSurprises.map((prompt, index) => ({
      id: `teacher_surprise_${index + 1}`,
      title: `Сюрприз ${index + 1}`,
      prompt
    }))
  }
};

const typeMeta = {
  truth: { label: "Правда", icon: "конверт.png", reveal: "Показать подсказку" },
  action: { label: "Действие", icon: "карандаш.png", reveal: "Показать ответ" },
  surprise: { label: "Сюрприз", icon: "подарочек.png", reveal: "" }
};

const state = {
  selectedCharacter: characters[0].id,
  players: [],
  currentIndex: 0,
  isRolling: false,
  activeCardType: null,
  activeCard: null,
  timerSeconds: 30,
  timerId: null,
  pendingPlayerId: null,
  pendingCellIndex: null,
  demoTurns: 0,
  debugLabelsVisible: true
};

const $ = (selector) => document.querySelector(selector);

const screens = {
  start: $("#startScreen"),
  players: $("#playersScreen"),
  game: $("#gameScreen"),
  final: $("#finalScreen")
};

function showScreen(name) {
  Object.values(screens).forEach((screen) => screen.classList.remove("active"));
  screens[name].classList.add("active");
}

function asset(file) {
  return ASSET + file;
}

function getCharacter(id) {
  return characters.find((character) => character.id === id) || characters[0];
}

function renderCharacters() {
  const grid = $("#characterGrid");
  grid.innerHTML = characters.map((character) => `
    <button class="character-option ${character.id === state.selectedCharacter ? "selected" : ""}" type="button" data-character="${character.id}">
      <img src="${asset(character.file)}" alt="${character.label}">
      <span>${character.label}</span>
    </button>
  `).join("");
}

function renderPlayers() {
  const list = $("#playersList");
  if (!state.players.length) {
    list.className = "players-list empty";
    list.textContent = "Пока никого нет";
    return;
  }

  list.className = "players-list";
  list.innerHTML = state.players.map((player, index) => {
    const character = getCharacter(player.characterId);
    return `
      <div class="player-row">
        <img src="${asset(character.file)}" alt="${character.label}">
        <div>
          <strong>${escapeHtml(player.name)}</strong>
          <span>${character.label}${player.role === "teacher" ? " · teacher" : ""}</span>
        </div>
        <button class="remove-btn" type="button" data-remove="${index}" aria-label="Удалить игрока">×</button>
      </div>
    `;
  }).join("");
}

function renderScoreboard() {
  const board = $("#scoreboard");
  if (!board) return;

  board.innerHTML = state.players.map((player, index) => `
    <div class="score-row ${index === state.currentIndex ? "current" : ""}">
      <strong>${escapeHtml(player.name)}</strong>
      <span>Очки: ${player.score || 0}</span>
    </div>
  `).join("");
}

function addPlayer(event) {
  event.preventDefault();
  const input = $("#playerName");
  const name = input.value.trim();
  const message = $("#setupMessage");

  if (!name) {
    message.textContent = "Введите имя игрока.";
    input.focus();
    return;
  }

  const character = getCharacter(state.selectedCharacter);
  state.players.push({
    id: window.crypto && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}_${Math.random()}`,
    name,
    characterId: character.id,
    role: character.role === "teacher" ? "teacher" : "student",
    position: 0,
    score: 0,
    truthCount: 0,
    actionCount: 0,
    surpriseCount: 0,
    totalTurns: 0,
    growthAreas: [],
    missedTasks: []
  });

  input.value = "";
  message.textContent = state.players.length < 2 ? "Минимум 2 игрока." : "Можно начинать партию.";
  updateDuplicateNotice();
  renderPlayers();
}

function removePlayer(index) {
  state.players.splice(index, 1);
  state.currentIndex = 0;
  $("#setupMessage").textContent = state.players.length < 2 ? "Минимум 2 игрока." : "Можно начинать партию.";
  updateDuplicateNotice();
  renderPlayers();
}

function updateDuplicateNotice() {
  const character = getCharacter(state.selectedCharacter);
  const used = state.players.some((player) => player.characterId === character.id);
  $("#duplicateNotice").textContent = used ? "Этот персонаж уже выбран" : "";
}

function startGame() {
  if (state.players.length < 2) {
    $("#setupMessage").textContent = "Добавьте минимум 2 игрока.";
    return;
  }

  state.currentIndex = 0;
  state.players.forEach((player) => {
    player.position = player.position || 0;
  });
  showScreen("game");
  renderBoard();
  renderTokens();
  renderScoreboard();
  updateCurrentPanel();
}

function renderBoard() {
  if (!DEBUG_CELLS) {
    $("#cellMarkers").innerHTML = "";
    removeDebugPanel();
    return;
  }

  $("#cellMarkers").innerHTML = boardCells.map((cell, index) => `
    <span class="cell-marker ${cell.type}" style="left:${cell.x}%; top:${cell.y}%;" title="${typeMeta[cell.type].label} ${index + 1}">
      <span class="cell-number">${cell.id || index + 1}</span>
    </span>
  `).join("");
  renderDebugPanel();
}

function getCellPosition(index) {
  const cell = boardCells[((index % boardCells.length) + boardCells.length) % boardCells.length];
  return { x: cell.x, y: cell.y };
}

function getTokenOffset(playerIndex, cellIndex) {
  const sameCellPlayers = state.players
    .map((player, index) => ({ player, index }))
    .filter((item) => item.player.position === cellIndex);
  const order = sameCellPlayers.findIndex((item) => item.index === playerIndex);
  const total = sameCellPlayers.length;

  if (total <= 1) return { x: 0, y: 0 };

  const radius = total <= 3 ? 1.35 : 1.85;
  const angle = (-Math.PI / 2) + ((Math.PI * 2) / total) * order;
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius
  };
}

function renderTokens() {
  const layer = $("#tokensLayer");
  layer.innerHTML = state.players.map((player, index) => {
    const character = getCharacter(player.characterId);
    const cell = getCellPosition(player.position);
    const offset = getTokenOffset(index, player.position);
    const isCurrent = index === state.currentIndex;
    const roleClass = player.role === "teacher" ? "teacher-token" : "student-token";
    return `
      <div class="token ${roleClass} ${isCurrent ? "active-token" : ""}" id="token_${player.id}" style="left:${cell.x + offset.x}%; top:${cell.y + offset.y}%;">
        <img src="${asset(character.file)}" alt="${escapeHtml(player.name)}">
        <span class="token-name">${escapeHtml(player.name)}</span>
      </div>
    `;
  }).join("");
}

function placeToken(player, index) {
  const token = document.getElementById(`token_${player.id}`);
  const cell = getCellPosition(player.position);
  const offset = getTokenOffset(index, player.position);
  token.style.left = `${cell.x + offset.x}%`;
  token.style.top = `${cell.y + offset.y}%`;
}

function placeAllTokens() {
  state.players.forEach(placeToken);
}

function updateActiveCellRing(player) {
  const ring = $("#activeCellRing");
  const position = getCellPosition(player.position);
  ring.style.left = `${position.x}%`;
  ring.style.top = `${position.y}%`;
  ring.classList.add("visible");
}

function updateCurrentPanel() {
  const player = state.players[state.currentIndex];
  const character = getCharacter(player.characterId);
  const cell = boardCells[player.position];
  $("#currentAvatar").src = asset(character.file);
  $("#currentAvatar").alt = character.label;
  $("#currentName").textContent = player.name;
  $("#currentPosition").textContent = `Позиция ${player.position + 1} из ${boardCells.length}`;
  $("#cellInfo").innerHTML = `
    <img src="${asset(typeMeta[cell.type].icon)}" alt="">
    <div>
      <strong>${typeMeta[cell.type].label}${cell.oge ? ` · ОГЭ ${cell.oge}` : ""}</strong>
      <span>${cell.oge ? ogeTitles[cell.oge] : "Карточка для знакомства и короткого разговора"}</span>
    </div>
  `;
  document.querySelectorAll(".token").forEach((token, index) => {
    token.classList.toggle("active-token", index === state.currentIndex);
  });
  renderScoreboard();
  updateActiveCellRing(player);
}

function rollDice() {
  if (state.isRolling) return;
  state.isRolling = true;
  $("#rollBtn").disabled = true;

  const value = Math.floor(Math.random() * 6) + 1;
  const dice = $("#dice");
  dice.classList.remove("rolling");
  dice.dataset.value = value;
  requestAnimationFrame(() => dice.classList.add("rolling"));

  setTimeout(() => moveCurrentPlayer(value), 650);
}

function moveCurrentPlayer(steps) {
  const player = state.players[state.currentIndex];
  let moved = 0;
  const interval = setInterval(() => {
    player.position = (player.position + 1) % boardCells.length;
    placeAllTokens();
    updateCurrentPanel();
    moved += 1;

    if (moved >= steps) {
      clearInterval(interval);
      setTimeout(() => openCardFor(player), 360);
    }
  }, 360);
}

function openCardFor(player) {
  const cell = boardCells[player.position];
  if (cell.type === "surprise") {
    openTaskCard(player, "surprise");
    return;
  }

  state.pendingPlayerId = player.id;
  state.pendingCellIndex = player.position;
  const topic = cell.oge ? `ОГЭ ${cell.oge}. ${ogeTitles[cell.oge]}` : "Карточка на выбор";
  $("#choiceTitle").textContent = "Правда или действие?";
  $("#choiceTopic").textContent = topic;
  $("#choiceTruthSubtitle").textContent = "Устный вопрос по этой теме";
  $("#choiceActionSubtitle").textContent = "Мини-задание по этой теме";
  openModal($("#choiceModal"));
}

function openChosenCard(type) {
  const player = state.players.find((item) => item.id === state.pendingPlayerId) || state.players[state.currentIndex];
  closeModal($("#choiceModal"));
  openTaskCard(player, type);
}

function openTaskCard(player, type) {
  if (DEMO_MODE && state.demoTurns >= DEMO_TURN_LIMIT) {
    showDemoPurchasePrompt();
    return;
  }
  const cell = boardCells[player.position];
  const role = player.role === "teacher" ? "teacher" : "student";
  const card = pickCard(role, type, cell.oge);
  state.activeCardType = type;
  state.activeCard = {
    ...card,
    role,
    type,
    topic: cell.oge ? `ОГЭ ${cell.oge}. ${ogeTitles[cell.oge]}` : typeMeta[type].label
  };
  player.totalTurns += 1;
  if (DEMO_MODE) {
    state.demoTurns += 1;
  }

  const meta = typeMeta[type];
  const taskCard = $("#taskCard");
  taskCard.className = `task-card ${type}`;
  $("#cardPrompt").textContent = card.prompt;

  const answer = [card.hint, card.answer, card.explanation].filter(Boolean).join("\n\n");
  $("#answerBlock").textContent = answer;
  $("#answerBlock").classList.add("hidden");
  $("#revealBtn").classList.toggle("hidden", !answer || type === "surprise");
  $("#revealBtn").textContent = meta.reveal || "Показать";
  setupCardTimer(card.prompt);
  openModal($("#cardModal"));
}

function showDemoPurchasePrompt() {
  state.isRolling = false;
  $("#rollBtn").disabled = false;
  if (confirm("Демо-версия завершена: сыграно 20 действий. Купить полный комплект игры «Правда, действие, ОГЭ»?")) {
    window.location.href = "/shop/truth-action-oge";
  }
}

function pickCard(role, type, oge) {
  const cards = gameData[role][type];
  if (oge) {
    const exact = cards.filter((card) => card.oge === oge);
    if (exact.length) return exact[Math.floor(Math.random() * exact.length)];
  }
  return cards[Math.floor(Math.random() * cards.length)];
}

function setupCardTimer(prompt) {
  stopTimer();
  const timer = $("#cardTimer");
  const hasTimer = /за\s+30\s+секунд/i.test(prompt);
  timer.classList.toggle("hidden", !hasTimer);
  timer.classList.remove("is-finished");
  $("#timerValue").textContent = "30";

  if (hasTimer) {
    startTimer();
  }
}

function startTimer() {
  stopTimer(false);
  state.timerSeconds = 30;
  $("#timerValue").textContent = state.timerSeconds;
  $("#cardTimer").classList.remove("is-finished");
  state.timerId = window.setInterval(() => {
    state.timerSeconds -= 1;
    $("#timerValue").textContent = state.timerSeconds;

    if (state.timerSeconds <= 0) {
      stopTimer(false);
      $("#cardTimer").classList.add("is-finished");
    }
  }, 1000);
}

function stopTimer(reset = true) {
  if (state.timerId) {
    window.clearInterval(state.timerId);
    state.timerId = null;
  }
  if (reset) {
    state.timerSeconds = 30;
  }
}

function getActiveTaskLabel() {
  if (!state.activeCard) return "Карточка";
  const typeLabel = typeMeta[state.activeCard.type]?.label || "Карточка";
  return `${state.activeCard.topic} · ${typeLabel}`;
}

function addGrowthRecord(player, reason) {
  const label = getActiveTaskLabel();
  const record = reason ? `${label}: ${reason}` : label;
  player.growthAreas.push(record);
}

function completeCard(outcome) {
  const player = state.players[state.currentIndex];
  if (outcome === "done" && state.activeCardType) {
    player[`${state.activeCardType}Count`] += 1;
    player.score += 1;
  }

  if (outcome === "growth") {
    addGrowthRecord(player, "вернуться к теме и разобрать ошибку");
  }

  if (outcome === "skip") {
    const label = getActiveTaskLabel();
    player.missedTasks.push(label);
    addGrowthRecord(player, "ответ был пропущен");
  }

  stopTimer();
  closeModal($("#cardModal"));
  state.pendingPlayerId = null;
  state.pendingCellIndex = null;
  state.activeCard = null;
  state.activeCardType = null;
  state.currentIndex = (state.currentIndex + 1) % state.players.length;
  state.isRolling = false;
  $("#rollBtn").disabled = false;
  updateCurrentPanel();
}

function skipPendingChoice() {
  closeModal($("#choiceModal"));
  state.pendingPlayerId = null;
  state.pendingCellIndex = null;
  state.activeCard = null;
  state.activeCardType = null;
  state.currentIndex = (state.currentIndex + 1) % state.players.length;
  state.isRolling = false;
  $("#rollBtn").disabled = false;
  updateCurrentPanel();
}

function buildGrowthAdvice(player) {
  const records = [...player.growthAreas];
  const unique = [...new Set(records)].slice(0, 4);
  if (!unique.length) {
    return "закрепить сильные стороны и попробовать более сложные задания.";
  }
  return unique.join("; ") + ".";
}

function showFinal() {
  stopTimer();
  const rows = state.players.map((player) => {
    const character = getCharacter(player.characterId);
    return `
      <div class="stat-row">
        <strong>${escapeHtml(player.name)} · ${character.label}</strong>
        <span>Баллы: ${player.score || 0}</span>
        <span>Правд: ${player.truthCount}</span>
        <span>Действий: ${player.actionCount}</span>
        <span>Сюрпризов: ${player.surpriseCount}</span>
        <span>Пропущено: ${player.missedTasks.length}</span>
        <span>Всего: ${player.totalTurns}</span>
      </div>
    `;
  }).join("");
  const growthItems = state.players
    .filter((player) => player.growthAreas.length || player.missedTasks.length)
    .map((player) => `
      <li>
        <strong>${escapeHtml(player.name)}:</strong>
        ${escapeHtml(buildGrowthAdvice(player))}
      </li>
    `).join("");
  const growthSummary = `
    <div class="growth-summary">
      <h3>На что обратить внимание</h3>
      ${growthItems ? `<ul>${growthItems}</ul>` : "<p>Все отмеченные задания выполнены. Можно двигаться дальше и усложнять вопросы.</p>"}
    </div>
  `;
  $("#finalStats").innerHTML = rows + growthSummary;
  showScreen("final");
}

function resetSessionStats() {
  state.demoTurns = 0;
  state.players.forEach((player) => {
    player.position = 0;
    player.score = 0;
    player.truthCount = 0;
    player.actionCount = 0;
    player.surpriseCount = 0;
    player.totalTurns = 0;
    player.growthAreas = [];
    player.missedTasks = [];
  });
  state.currentIndex = 0;
  state.isRolling = false;
  state.activeCard = null;
  state.activeCardType = null;
  stopTimer();
  $("#rollBtn").disabled = false;
  startGame();
}

function renderDebugPanel() {
  let panel = $("#debugPanel");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "debugPanel";
    panel.className = "debug-panel";
    panel.innerHTML = `
      <div class="debug-actions">
        <button type="button" id="showCellNumbersBtn">Показать номера клеток</button>
        <button type="button" id="hideCellNumbersBtn">Скрыть номера клеток</button>
      </div>
      <div id="debugCoords">Кликните по полю, чтобы получить x/y в процентах.</div>
    `;
    $(".board-wrap").appendChild(panel);
  }
  toggleDebugLabels(state.debugLabelsVisible);
}

function removeDebugPanel() {
  const panel = $("#debugPanel");
  if (panel) panel.remove();
}

function toggleDebugLabels(visible) {
  state.debugLabelsVisible = visible;
  $(".board-wrap").classList.toggle("hide-debug-labels", !visible);
}

function showClickCoordinates(event) {
  if (!DEBUG_CELLS) return;
  const board = event.currentTarget;
  const rect = board.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 100;
  const y = ((event.clientY - rect.top) / rect.height) * 100;
  const output = $("#debugCoords");
  if (output) {
    output.textContent = `x: ${x.toFixed(1)}, y: ${y.toFixed(1)}`;
  }
  console.log(`board click: x: ${x.toFixed(1)}, y: ${y.toFixed(1)}`);
}

function openModal(modal) {
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal(modal) {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

function bindEvents() {
  $("#goPlayersBtn").addEventListener("click", () => showScreen("players"));
  $("#backToStartBtn").addEventListener("click", () => showScreen("start"));
  $("#rulesBtn").addEventListener("click", () => openModal($("#rulesModal")));
  $("#playerForm").addEventListener("submit", addPlayer);
  $("#startGameBtn").addEventListener("click", startGame);
  $("#rollBtn").addEventListener("click", rollDice);
  $("#finishBtn").addEventListener("click", showFinal);
  $("#toSetupBtn").addEventListener("click", () => showScreen("players"));
  $("#playAgainBtn").addEventListener("click", resetSessionStats);
  $("#finalSetupBtn").addEventListener("click", () => showScreen("players"));
  $("#revealBtn").addEventListener("click", () => $("#answerBlock").classList.toggle("hidden"));
  $("#restartTimerBtn").addEventListener("click", startTimer);
  $("#doneCardBtn").addEventListener("click", () => completeCard("done"));
  $("#growthCardBtn").addEventListener("click", () => completeCard("growth"));
  $("#skipCardBtn").addEventListener("click", () => completeCard("skip"));
  $("#skipCardBtn2").addEventListener("click", () => completeCard("skip"));
  $("#skipChoiceBtn").addEventListener("click", skipPendingChoice);
  $(".board-wrap").addEventListener("click", showClickCoordinates);

  document.addEventListener("click", (event) => {
    const characterButton = event.target.closest("[data-character]");
    if (characterButton) {
      state.selectedCharacter = characterButton.dataset.character;
      renderCharacters();
      updateDuplicateNotice();
    }

    const removeButton = event.target.closest("[data-remove]");
    if (removeButton) {
      removePlayer(Number(removeButton.dataset.remove));
    }

    if (event.target.matches("[data-close-modal]")) {
      closeModal(event.target.closest(".modal"));
    }

    const choiceButton = event.target.closest("[data-choice-type]");
    if (choiceButton) {
      openChosenCard(choiceButton.dataset.choiceType);
    }

    if (event.target.id === "showCellNumbersBtn") {
      toggleDebugLabels(true);
    }

    if (event.target.id === "hideCellNumbersBtn") {
      toggleDebugLabels(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if ($("#cardModal").classList.contains("open")) {
        completeCard("skip");
        return;
      }
      if ($("#choiceModal").classList.contains("open")) {
        skipPendingChoice();
        return;
      }
      document.querySelectorAll(".modal.open").forEach(closeModal);
    }
  });
}

function init() {
  renderCharacters();
  renderPlayers();
  updateDuplicateNotice();
  $("#dice").dataset.value = 1;
  bindEvents();
}

init();
