const $ = (s) => document.querySelector(s);
const app = $('#app');
const STORAGE_KEY = 'summerGerundQuest_v2';
let state = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') || { unlocked: 0, completed: [], trainingIndex: 0, score: 0, answers: [], lessonSteps: {}, lessonScores: {} };
state.lessonSteps ||= {};
state.lessonScores ||= {};
let soundOn = false;
let activeLesson = 0;

const lessons = [
  {
    title:'Лимонад двух действий', emoji:'🍋', short:'Что такое деепричастный оборот', art:'assets/lemon-lemonade.png', recipe:'Лимонный лимонад: 1 л воды · 1 лимон · 2–3 ложки мёда или сиропа · мята. Смешайте сок с водой, добавьте подсластитель и охладите.',
    intro:'В хорошем лимонаде есть основа и добавка. В предложении тоже: основное действие выражает сказуемое, а добавочное — деепричастие.',
    formula:'деепричастие + зависимые слова = деепричастный оборот',
    rules:['Обозначает <strong>добавочное действие того же лица или предмета</strong>, который выполняет основное действие.','Отвечает на вопросы <strong>что делая? что сделав?</strong>','В предложении весь оборот является <strong>обстоятельством</strong>.'],
    examples:['Бариста <span class="accent">нарезал</span> лимон, <span class="accent">удаляя из него косточки</span>.','Бариста нарезал и одновременно удалял: исполнитель у действий один.'],
    question:'Где деепричастный оборот?', options:['добавил сироп','перемешивая напиток ложкой','холодный ягодный морс'], answer:1,
    explain:'«Перемешивая» — деепричастие, «напиток ложкой» — зависимые слова.'
  },
  {
    title:'Компот с запятыми', emoji:'🍒', short:'Как обособлять оборот', art:'assets/cherry-compote.png', recipe:'Яблочно-вишнёвый компот: 1,5 л воды · 2 яблока · 200 г вишни · сахар по вкусу. Варите 10–15 минут и дайте настояться под крышкой.',
    intro:'Запятые здесь работают как края этикетки: показывают границы добавочного действия.',
    formula:'деепричастный оборот обычно отделяется от остального предложения запятой или запятыми',
    rules:['В начале: <strong>Нарезав яблоки,</strong> мы вскипятили воду.','В середине: Компот, <strong>остывая под крышкой,</strong> становился насыщеннее.','В конце: Мы разлили морс, <strong>добавив в него лёд.</strong>'],
    examples:['Место оборота не отменяет правило: сначала найдите его границы, затем поставьте запятые.'],
    question:'Какой вариант оформлен верно?', options:['Смешав соки мы добавили лёд.','Мы, смешав соки добавили лёд.','Смешав соки, мы добавили лёд.'], answer:2,
    explain:'Оборот стоит перед основным предложением и отделяется одной запятой.'
  },
  {
    title:'Смузи без лишних запятых', emoji:'🥤', short:'Фразеологические обороты', art:'assets/berry-smoothie.png', recipe:'Ягодный смузи: 1 банан · горсть ягод · 200 мл молока или натурального йогурта. Взбейте всё до однородности.',
    intro:'Иногда сочетание с деепричастием стало цельным выражением и значит уже не отдельное действие, а образ действия.',
    formula:'устойчивое выражение ≠ обычный деепричастный оборот',
    rules:['Обычно не обособляются: <strong>работать спустя рукава</strong>, <strong>бежать сломя голову</strong>, <strong>трудиться не покладая рук</strong>.','Проверьте смысл: выражение можно заменить наречием или кратким описанием образа действия.','Одинаковые слова в буквальном значении снова становятся обычным оборотом.'],
    examples:['Повар работал <span class="accent">засучив рукава</span>. — усердно, без запятой.','<span class="accent">Засучив рукава рубашки,</span> повар вымыл ягоды. — реальное действие, нужна запятая.'],
    question:'Где запятая НЕ нужна?', options:['Нарезав лайм бариста взял мяту.','Бариста трудился не покладая рук.','Охладив кувшин мы налили морс.'], answer:1,
    explain:'«Не покладая рук» — устойчивое выражение со значением «усердно».'
  },
  {
    title:'Морс из однородных действий', emoji:'🫐', short:'Однородные обороты', art:'assets/berry-mors.png', recipe:'Ягодный морс: 250 г ягод · 1 л воды · мёд или сахар по вкусу. Разомните ягоды, залейте водой, процедите и охладите.',
    intro:'В один напиток можно добавить несколько ингредиентов, а к одному сказуемому — несколько одинаково относящихся добавочных действий.',
    formula:'одиночный И соединяет обороты — запятая перед И не ставится',
    rules:['<strong>Нарезав лимон и добавив мяту,</strong> мы залили всё водой.','Без союза: <strong>Нарезав лимон, добавив мяту,</strong> мы залили всё водой.','При повторяющемся союзе: <strong>И нарезав лимон, и добавив мяту,</strong> мы подготовили основу.'],
    examples:['Сначала найдите все добавочные действия и проверьте, как они соединены между собой.'],
    question:'В каком варианте запятые стоят верно?', options:['Выжав сок, и добавив лёд, мы подали лимонад.','Выжав сок и добавив лёд, мы подали лимонад.','Выжав сок и, добавив лёд мы подали лимонад.'], answer:1,
    explain:'Два однородных оборота соединены одиночным «и»: между ними запятая не нужна.'
  }
];

const lessonTasks = [
  [
    {type:'choice', label:'Найди', prompt:'В каком сочетании есть деепричастный оборот?', options:['охладил ягодный морс','нарезая лимон тонкими кружочками','свежая веточка мяты'], answer:1, explain:'«Нарезая» — деепричастие, «лимон тонкими кружочками» — зависимые слова.'},
    {type:'select', label:'Выдели', prompt:'В предложении нет запятых. Выделите весь деепричастный оборот.', words:['Бариста','выжимая','сок','из','спелого','лимона','приготовил','основу.'], selected:[1,2,3,4,5], explain:'Оборот: «выжимая сок из спелого лимона». В предложении он должен обособляться с двух сторон.'},
    {type:'input', label:'Выпиши', prompt:'В предложении нет запятых. Выпишите деепричастие: «Смешивая лимонад длинной ложкой бариста добавлял лёд».', answers:['смешивая'], placeholder:'Одно слово', explain:'Деепричастие «смешивая» называет добавочное действие.'},
    {type:'choice', label:'Найди', prompt:'В каком предложении основное и добавочное действия выполняет один и тот же человек?', options:['Подойдя к стойке, мне подали лимонад.','Подойдя к стойке, гость заказал лимонад.','Подойдя к стойке, заиграла музыка.'], answer:1, explain:'Гость и подошёл, и заказал. В других вариантах исполнитель добавочного действия не назван верно.'},
    {type:'select', label:'Выдели', prompt:'В предложении нет запятых. Выделите деепричастный оборот.', words:['Девочка','пила','коктейль','помешивая','его','трубочкой.'], selected:[3,4,5], explain:'Оборот: «помешивая его трубочкой». Он стоит после основной части предложения.'}
  ],
  [
    {type:'choice', label:'Найди', prompt:'Найдите предложение с верно поставленными запятыми.', options:['Добавив мяту бариста перемешал лимонад.','Добавив мяту, бариста перемешал лимонад.','Добавив, мяту бариста перемешал лимонад.'], answer:1, explain:'Оборот в начале предложения отделяется запятой целиком.'},
    {type:'commas', label:'Расставь', prompt:'Нажмите на места, где нужны запятые.', words:['Компот','остывая','под','крышкой','становился','ароматнее'], commas:[0,3], explain:'Оборот «остывая под крышкой» стоит внутри предложения и обособляется с двух сторон.'},
    {type:'input', label:'Выпиши', prompt:'В предложении нет запятых. Выпишите оборот: «Мы подали компот добавив в него кубики льда».', answers:['добавив в него кубики льда'], placeholder:'Оборот без запятых', explain:'Оборот: «добавив в него кубики льда». Перед ним нужна запятая.'},
    {type:'select', label:'Выдели', prompt:'В предложении нет запятых. Выделите часть, которую нужно обособить.', words:['Процедив','яблочно-вишнёвый','компот','мы','перелили','его','в','кувшин.'], selected:[0,1,2], explain:'В начале предложения находится оборот «процедив яблочно-вишнёвый компот».'},
    {type:'commas', label:'Расставь', prompt:'Расставьте запятые в предложении.', words:['Повар','проверил','вкус','добавив','немного','сахара'], commas:[2], explain:'Оборот стоит после основной части: «проверил вкус, добавив немного сахара».'}
  ],
  [
    {type:'choice', label:'Найди', prompt:'Где запятая не нужна?', options:['Взбив ягоды мы добавили банан.','Бариста работал не покладая рук.','Нарезая банан повар включил блендер.'], answer:1, explain:'«Не покладая рук» — фразеологизм со значением «усердно».'},
    {type:'select', label:'Выдели', prompt:'Выделите устойчивое выражение.', words:['Перед','праздником','команда','работала','не','покладая','рук.'], selected:[4,5,6], explain:'Устойчивое сочетание: «не покладая рук».'},
    {type:'input', label:'Выпиши', prompt:'Замените одним наречием выражение «работать спустя рукава».', answers:['небрежно','плохо'], placeholder:'Одно наречие', explain:'«Спустя рукава» значит «небрежно, плохо».'},
    {type:'choice', label:'Сравни', prompt:'Где сочетание «засучив рукава» имеет буквальное значение и требует запятой?', options:['Бариста работал засучив рукава.','Засучив рукава рубашки бариста вымыл ягоды.','Команда принялась за дело засучив рукава.'], answer:1, explain:'Названы настоящие рукава рубашки и реальное действие, поэтому оборот обособляется.'},
    {type:'commas', label:'Расставь', prompt:'Поставьте запятые только там, где они нужны.', words:['Повар','трудился','не','покладая','рук','и','закончив','смену','угостил','всех','смузи'], commas:[5,7], explain:'Фразеологизм не обособляется. Союз «и» соединяет сказуемые «трудился» и «угостил», а оборот «закончив смену» стоит после союза и выделяется с двух сторон.'}
  ],
  [
    {type:'choice', label:'Найди', prompt:'Найдите верное оформление однородных оборотов.', options:['Выжав сок, и добавив воду, мы получили морс.','Выжав сок и добавив воду, мы получили морс.','Выжав, сок и добавив воду мы получили морс.'], answer:1, explain:'Перед одиночным «и», соединяющим однородные обороты, запятая не ставится.'},
    {type:'select', label:'Выдели', prompt:'В предложении нет запятых. Выделите оба оборота, не захватывая союз.', words:['Размяв','ягоды','и','залив','их','водой','мы','приготовили','основу.'], selected:[0,1,3,4,5], explain:'Обороты: «размяв ягоды» и «залив их водой». Союз «и» связывает их, но не входит в границы ни одного оборота.'},
    {type:'input', label:'Выпиши', prompt:'В предложении нет запятых. Выпишите только деепричастия: «Процедив морс и добавив мёд мы охладили напиток».', answers:['процедив добавив','процедив, добавив'], placeholder:'Два слова', explain:'Деепричастия — «процедив», «добавив». Союз «и» связывает обороты, но не входит в их границы.'},
    {type:'commas', label:'Расставь', prompt:'Расставьте запятые между однородными оборотами и основной частью.', words:['Перебрав','ягоды','промыв','их','и','удалив','листочки','мы','приступили','к','рецепту'], commas:[1,6], explain:'Первый оборот отделён бессоюзно, второй и третий соединены одиночным «и».'},
    {type:'select', label:'Выдели', prompt:'В предложении нет запятых. Выделите оба оборота, не захватывая повторяющийся союз.', words:['И','разминая','ягоды','и','добавляя','воду','повар','следил','за','цветом','морса.'], selected:[1,2,4,5], explain:'Обороты: «разминая ягоды», «добавляя воду». Повторяющийся союз «и… и» связывает конструкции, но не входит в границы ни одной из них.'}
  ]
];

const tasks = [
 {mode:'comma', words:['Смешав','воду','с','лимонным','соком','бариста','добавил','мёд'], commas:[4], fact:'Классическая основа лимонада — вода и цитрусовый сок.', explain:'Оборот «смешав воду с лимонным соком» стоит в начале.'},
 {mode:'comma', words:['Нарезав','клубнику','и','добавив','листья','мяты','мы','получили','яркий','лимонад'], commas:[5], fact:'Клубника хорошо сочетается с мятой и лимоном.', explain:'Однородные обороты соединены одиночным «и»; запятая нужна после всей группы.'},
 {mode:'comma', words:['Компот','остывая','под','крышкой','становится','насыщеннее'], commas:[0,3], fact:'Компоту часто дают настояться после приготовления.', explain:'Оборот «остывая под крышкой» стоит внутри предложения.'},
 {mode:'comma', words:['Мы','охладили','напиток','положив','в','кувшин','кубики','льда'], commas:[2], fact:'Лёд лучше добавлять непосредственно перед подачей.', explain:'Оборот «положив в кувшин кубики льда» стоит после сказуемого.'},
 {mode:'comma', words:['Бариста','работал','не','покладая','рук'], commas:[], fact:'«Не покладая рук» означает «усердно».', explain:'Это фразеологизм, поэтому запятые не нужны.'},
 {mode:'comma', words:['Засучив','рукава','рубашки','повар','вымыл','ягоды'], commas:[2], fact:'Ягоды для напитка перебирают и аккуратно промывают.', explain:'Здесь рукава действительно засучили: оборот имеет буквальное значение.'},
 {mode:'comma', words:['Повар','смешал','соки','улыбаясь','гостям','и','напевая','летнюю','мелодию'], commas:[2], fact:'В одном напитке можно соединять сладкие и кислые соки.', explain:'Однородные обороты соединены одиночным «и» и вместе отделены от сказуемого.'},
 {mode:'comma', words:['Настаивая','ягоды','несколько','часов','мы','получаем','морс','без','кипячения'], commas:[3], fact:'Морс можно приготовить холодным настаиванием ягод.', explain:'Оборот стоит перед грамматической основой «мы получаем».'},
 {mode:'comma', words:['Кубики','льда','постепенно','тая','разбавляют','напиток'], commas:[1,3], fact:'Крупные кубики льда тают медленнее мелких.', explain:'Оборот «постепенно тая» стоит внутри предложения и обособляется с двух сторон.'},
 {mode:'comma', words:['Добавив','апельсин','нарезав','яблоко','и','положив','корицу','мы','сварили','компот'], commas:[1,6], fact:'В яблочный компот часто добавляют цитрус и корицу.', explain:'Первые два оборота разделяются запятой, второй и третий соединены одиночным «и».'},
 {mode:'select', words:['Взбив','банан','с','молоком','мы','получили','густой','коктейль.'], selected:[0,1,2,3], fact:'Банан делает молочный коктейль густым без загустителей.', explain:'Оборот: «взбив банан с молоком». После него нужна запятая.'},
 {mode:'select', words:['Мы','украсили','стакан','положив','сверху','дольку','лайма.'], selected:[3,4,5,6], fact:'Долька лайма одновременно украшает напиток и добавляет аромат.', explain:'Оборот: «положив сверху дольку лайма». Перед ним нужна запятая.'},
 {mode:'select', words:['Перемешивая','лимонад','длинной','ложкой','бариста','сохранил','пузырьки.'], selected:[0,1,2,3], fact:'Газированные напитки перемешивают осторожно.', explain:'Оборот: «перемешивая лимонад длинной ложкой». После него нужна запятая.'},
 {mode:'select', words:['Посетители','бежали','к','стойке','сломя','голову.'], selected:[], fact:'«Сломя голову» означает «очень быстро».', explain:'Деепричастного оборота нет: «сломя голову» — цельное фразеологическое сочетание.'},
 {mode:'select', words:['Сняв','цедру','и','выжав','сок','мы','использовали','весь','лимон.'], selected:[0,1,3,4], fact:'Цедра содержит ароматические масла, а сок даёт кислоту.', explain:'Обороты: «сняв цедру», «выжав сок». Союз «и» связывает их, но не входит в границы.'},
 {mode:'select', words:['Напиток','охлаждаясь','в','стеклянном','кувшине','сохранял','аромат','мяты.'], selected:[1,2,3,4], fact:'Прозрачный кувшин красиво показывает цвет морса.', explain:'Оборот: «охлаждаясь в стеклянном кувшине». Он обособляется с двух сторон.'},
 {mode:'select', words:['Повар','подал','компот','остудив','его','до','комнатной','температуры.'], selected:[3,4,5,6,7], fact:'Компот можно подавать и тёплым, и охлаждённым.', explain:'Оборот: «остудив его до комнатной температуры». Перед ним нужна запятая.'},
 {mode:'select', words:['Добавляя','мёд','небольшими','порциями','и','постоянно','пробуя','напиток','бариста','регулировал','сладость.'], selected:[0,1,2,3,5,6,7], fact:'Сладость напитка удобно регулировать небольшими порциями.', explain:'Обороты: «добавляя мёд небольшими порциями», «постоянно пробуя напиток». Союз «и» не входит в их границы.'},
 {mode:'select', words:['Процедив','ягодную','основу','мы','получили','однородный','морс.'], selected:[0,1,2], fact:'Процеживание отделяет ягодные косточки и кожицу.', explain:'Оборот: «процедив ягодную основу». После него нужна запятая.'},
 {mode:'select', words:['Дети','пили','лимонад','сидя','в','тени','сада','и','обсуждая','рецепт.'], selected:[3,4,5,6,8,9], fact:'Домашний лимонад можно собрать как конструктор из воды, сока, ягод и трав.', explain:'Обороты: «сидя в тени сада», «обсуждая рецепт». Союз «и» связывает их, но не входит в границы.'}
];

function save(){ localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); updateProgress(); }
function updateProgress(){
  const done = state.completed.length;
  $('#progressText').textContent = `${done} / 5`;
  $('#progressBar').style.width = `${done * 20}%`;
}
function toast(text){ const t=$('#toast'); t.textContent=text; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),1800); }
function renderStart(){
  app.innerHTML=`<section class="panel hero"><div><span class="eyebrow">Летняя экспедиция • 40 заданий</span><h1>Бар <span>добавочных</span> действий</h1><p>Изучите рецепты лимонадов, морсов и компотов — и заодно разберитесь, как устроен деепричастный оборот. В первых четырёх локациях Вас ждут по 5 заданий разных форматов, а в финале — большая тренировка из 20 предложений.</p><div class="buttons"><button class="primary" id="startBtn">Открыть летний бар →</button><button class="secondary" id="continueBtn">Продолжить с карты</button></div></div><div class="hero-art"><img class="fruit" src="assets/summer-tasting.png" alt="Поднос летних напитков"><img class="lemonade" src="assets/lemon-lemonade.png" alt="Лимонно-мятный лимонад"></div></section>`;
  $('#startBtn').onclick=renderMap; $('#continueBtn').onclick=renderMap;
}
function renderMap(){
  const cards=[...lessons,{title:'Большая дегустация',short:'20 заданий: запятые и границы оборота',art:'assets/summer-tasting.png'}];
  app.innerHTML=`<section class="panel map-panel"><h1 class="section-title">Карта летнего бара</h1><p class="subtitle">У каждого напитка — собственная локация и пять заданий. Следующая карточка открывается после прохождения предыдущей.</p><div class="route">${cards.map((x,i)=>{const locked=i>state.unlocked; const done=state.completed.includes(i); const count=i<4?`${Math.min(state.lessonSteps[i]||0,5)}/5`:(done?'20/20':'20 заданий'); return `<button class="station ${done?'done':''}" data-i="${i}" ${locked?'disabled':''}><span class="number">${i+1}</span><span class="state">${done?'готово ✓':locked?'закрыто 🔒':count}</span><span class="station-image"><img src="${x.art}" alt="${x.title}"></span><h3>${x.title}</h3><p>${x.short}</p></button>`}).join('')}</div></section>`;
  document.querySelectorAll('.station:not(:disabled)').forEach(b=>b.onclick=()=>{const i=+b.dataset.i; i<4?renderLesson(i):renderTraining();});
}
function renderLesson(i){
  activeLesson=i; const l=lessons[i];
  if((state.lessonSteps[i]||0)>=5){renderLessonComplete(i);return;}
  const step=state.lessonSteps[i]||0; const t=lessonTasks[i][step];
  app.innerHTML=`<section class="panel lesson"><div><div class="lesson-top"><span class="eyebrow">Локация ${i+1} • задание ${step+1} из 5</span><div class="mini-progress"><b style="width:${(step+1)*20}%"></b></div></div><h1>${l.title}</h1><p>${l.intro}</p><details class="theory-box"><summary>Правило и примеры</summary><div class="formula">${l.formula}</div><div class="rule-card">${l.rules.map(r=>`<div>• ${r}</div>`).join('<br>')}</div><div class="examples">${l.examples.map(e=>`<div class="example">${e}</div>`).join('')}</div></details>${renderLessonTask(t)}</div><div class="art"><img src="${l.art}" alt="${l.title}"><div class="recipe-box"><strong>Рецепт напитка</strong><span>${l.recipe}</span></div><div class="lesson-score">Верных ответов: <b>${state.lessonScores[i]||0}</b></div></div></section>`;
  bindLessonTask(i,t);
}
function renderLessonComplete(i){const l=lessons[i];app.innerHTML=`<section class="panel finish"><img src="${l.art}" alt="${l.title}" style="height:240px;max-width:80%;object-fit:contain;filter:drop-shadow(0 18px 16px rgba(5,70,76,.25))"><span class="eyebrow">Локация пройдена • ${state.lessonScores[i]||0}/5</span><h1>${l.title} готов!</h1><p>Все пять заданий выполнены. Можно вернуться на карту или пройти эту локацию ещё раз.</p><div class="buttons" style="justify-content:center"><button class="primary" id="completeMap">На карту →</button><button class="secondary" id="replayLesson">Повторить задания</button></div></section>`;$('#completeMap').onclick=renderMap;$('#replayLesson').onclick=()=>{state.lessonSteps[i]=0;state.lessonScores[i]=0;save();renderLesson(i)}}
function renderLessonTask(t){
  let body='';
  if(t.type==='choice') body=`<div class="options">${t.options.map((o,n)=>`<button class="option" data-n="${n}">${o}</button>`).join('')}</div>`;
  if(t.type==='select') body=`<div class="sentence-box compact">${t.words.map((w,n)=>`<span class="word selectable" data-i="${n}">${w}</span>`).join(' ')}</div><button class="primary lesson-check" id="lessonCheck">Проверить</button>`;
  if(t.type==='commas') body=`<div class="sentence-box compact">${renderCommaWords(t)}</div><button class="primary lesson-check" id="lessonCheck">Проверить</button>`;
  if(t.type==='input') body=`<div class="write-row"><input id="lessonInput" type="text" autocomplete="off" placeholder="${t.placeholder||'Введите ответ'}"><button class="primary" id="lessonCheck">Проверить</button></div>`;
  return `<div class="lesson-task"><span class="mode-badge">${t.label}</span><h3>${t.prompt}</h3>${body}<div class="feedback lesson-result" id="lessonFeedback" role="status" aria-live="polite"></div></div>`;
}
function bindLessonTask(i,t){
  if(t.type==='choice') document.querySelectorAll('.option').forEach(btn=>btn.onclick=()=>checkLessonTask(i,t,+btn.dataset.n));
  if(t.type==='select') document.querySelectorAll('.selectable').forEach(w=>w.onclick=()=>w.classList.toggle('selected'));
  if(t.type==='commas') document.querySelectorAll('.comma-gap').forEach(g=>g.onclick=()=>g.classList.toggle('on'));
  if($('#lessonCheck')) $('#lessonCheck').onclick=()=>checkLessonTask(i,t);
  if($('#lessonInput')) $('#lessonInput').onkeydown=e=>{if(e.key==='Enter')checkLessonTask(i,t)};
}
function normalizeAnswer(s){return String(s||'').toLowerCase().replace(/[«»"'.,!?;:]/g,'').replace(/ё/g,'е').replace(/\s+/g,' ').trim()}
function checkLessonTask(i,t,choice){
  let got,expected,ok=false;
  if(t.type==='choice'){got=choice;expected=t.answer;ok=got===expected;}
  if(t.type==='select'){got=[...document.querySelectorAll('.lesson-task .selectable.selected')].map(x=>+x.dataset.i);expected=t.selected;ok=sameIndices(got,expected);}
  if(t.type==='commas'){got=[...document.querySelectorAll('.lesson-task .comma-gap.on')].map(x=>+x.dataset.i);expected=t.commas;ok=sameIndices(got,expected);}
  if(t.type==='input'){got=normalizeAnswer($('#lessonInput').value);ok=t.answers.map(normalizeAnswer).includes(got);}
  document.querySelectorAll('.option,.selectable,.comma-gap,#lessonCheck,#lessonInput').forEach(x=>{x.disabled=true;x.style.pointerEvents='none'});
  if(t.type==='choice'){document.querySelector(`.option[data-n="${t.answer}"]`).classList.add('correct');if(!ok)document.querySelector(`.option[data-n="${choice}"]`)?.classList.add('wrong');}
  if(t.type==='select')document.querySelectorAll('.selectable').forEach(w=>w.classList.toggle('selected',t.selected.includes(+w.dataset.i)));
  if(t.type==='commas')document.querySelectorAll('.comma-gap').forEach(g=>g.classList.toggle('on',t.commas.includes(+g.dataset.i)));
  if(t.type==='input'&&!ok)$('#lessonInput').value=t.answers[0];
  if(ok)state.lessonScores[i]=(state.lessonScores[i]||0)+1;
  document.querySelector('.theory-box')?.removeAttribute('open');
  const final=(state.lessonSteps[i]||0)>=4; const fb=$('#lessonFeedback'); fb.className=`feedback lesson-result show ${ok?'good':'bad'}`; fb.innerHTML=`<strong>${ok?'Верно!':'Разберём ответ.'}</strong><span class="explain">${t.explain}</span><div class="buttons"><button class="${final?'primary':'secondary'}" id="nextLessonTask">${final?'Завершить локацию →':'Следующее задание →'}</button></div>`;
  save(); $('#nextLessonTask').onclick=()=>advanceLesson(i); requestAnimationFrame(fitCurrentPanel);
}
function advanceLesson(i){
  const next=(state.lessonSteps[i]||0)+1; state.lessonSteps[i]=next;
  if(next>=5){if(!state.completed.includes(i))state.completed.push(i);state.unlocked=Math.max(state.unlocked,i+1);save();renderMap();}
  else{save();renderLesson(i);}
}
function renderTraining(){
  if(state.trainingIndex>=tasks.length){renderFinish();return} const t=tasks[state.trainingIndex]; const comma=t.mode==='comma';
  app.innerHTML=`<section class="panel training"><div class="training-head"><span class="mode-badge">${comma?'Расставьте запятые':'Выделите оборот'}</span><h2>Большая дегустация</h2><span class="task-counter">${state.trainingIndex+1} / 20</span></div><p class="instruction">${comma?'Нажмите на промежутки, где должны стоять запятые. Если запятые не нужны, сразу проверяйте.':'В предложении запятые не расставлены. Выделите только слова оборота — без союзов. Если оборота нет, ничего не выделяйте.'}</p><div class="sentence-box" id="sentence">${comma?renderCommaWords(t):renderSelectWords(t)}</div><div class="recipe-chip">🥄 ${t.fact}</div><div class="feedback" id="taskFeedback"></div><div class="task-actions"><button class="secondary" id="hintBtn">Подсказка</button><button class="primary" id="checkBtn">Проверить</button></div><div class="hint-box" id="hintBox" hidden>${comma?'Найдите сказуемое, затем добавочное действие и его зависимые слова.':'Задайте от сказуемого вопрос «что делая?» или «что сделав?». Союз может связывать обороты, но не входит в их границы.'}</div></section>`;
  if(!comma)document.querySelectorAll('.selectable').forEach(w=>w.onclick=()=>w.classList.toggle('selected'));
  else document.querySelectorAll('.comma-gap').forEach(g=>g.onclick=()=>g.classList.toggle('on'));
  $('#hintBtn').onclick=()=>$('#hintBox').hidden=!$('#hintBox').hidden; $('#checkBtn').onclick=checkTask;
}
function renderCommaWords(t){return t.words.map((w,i)=>`<span class="word">${w}</span>${i<t.words.length-1?`<button class="comma-gap" data-i="${i}" aria-label="Поставить запятую после слова ${w}"></button>`:''}`).join('')}
function renderSelectWords(t){return t.words.map((w,i)=>`<span class="word selectable" data-i="${i}">${w}</span>`).join(' ')}
function sameIndices(a,b){const left=[...new Set(a)].sort((x,y)=>x-y),right=[...new Set(b)].sort((x,y)=>x-y);return left.length===right.length&&left.every((x,i)=>x===right[i])}
function checkTask(){const t=tasks[state.trainingIndex]; const sentence=$('#sentence'); const got=t.mode==='comma'?[...sentence.querySelectorAll('.comma-gap.on')].map(x=>Number(x.dataset.i)):[...sentence.querySelectorAll('.selectable.selected')].map(x=>Number(x.dataset.i)); const accepted=t.mode==='comma'?(t.commaAnswers||[t.commas]):[t.selected]; const ok=accepted.some(answer=>sameIndices(got,answer)); const fb=$('#taskFeedback'); fb.className=`feedback show ${ok?'good':'bad'}`;
  if(ok){state.score++; fb.innerHTML=`Точно! <span class="explain">${t.explain}</span>`;}else{fb.innerHTML=`Есть неточность. <span class="explain">${t.explain}</span>`; showCorrect(t);} state.answers.push(ok); state.trainingIndex++; save(); $('#checkBtn').textContent=state.trainingIndex===tasks.length?'Узнать результат →':'Следующий рецепт →'; $('#checkBtn').onclick=()=>state.trainingIndex===tasks.length?finishTraining():renderTraining(); document.querySelectorAll('.comma-gap,.selectable').forEach(x=>x.disabled=true); }
function showCorrect(t){if(t.mode==='comma')document.querySelectorAll('.comma-gap').forEach(g=>{g.classList.toggle('on',t.commas.includes(+g.dataset.i))});else document.querySelectorAll('.selectable').forEach(w=>w.classList.toggle('selected',t.selected.includes(+w.dataset.i)))}
function finishTraining(){if(!state.completed.includes(4))state.completed.push(4);state.unlocked=4;save();renderFinish()}
function renderFinish(){const pct=Math.round(state.score/20*100),stars=state.score>=18?'★★★':state.score>=14?'★★☆':'★☆☆';app.innerHTML=`<section class="panel finish"><span class="eyebrow">Квест завершён</span><h1>Бар открыт!</h1><div class="stars">${stars}</div><div class="score-ring" style="--score:${pct}%"><b>${state.score}/20</b></div><p>${state.score>=18?'Вы безошибочно чувствуете границы оборотов и союзы между ними.':state.score>=14?'Правила уже работают. Осталось внимательнее проверять границы оборота.':'Рецепты освоены — теперь стоит ещё раз пройти дегустацию и закрепить запятые.'}</p><div class="buttons" style="justify-content:center"><button class="primary" id="againTraining">Повторить 20 заданий</button><button class="secondary" id="resetAll">Начать квест заново</button></div></section>`;$('#againTraining').onclick=()=>{state.trainingIndex=0;state.score=0;state.answers=[];save();renderTraining()};$('#resetAll').onclick=()=>{localStorage.removeItem(STORAGE_KEY);state={unlocked:0,completed:[],trainingIndex:0,score:0,answers:[],lessonSteps:{},lessonScores:{}};save();renderStart()}}

$('#homeBtn').onclick=renderMap;
$('#resetProgressBtn').onclick=()=>{if(!confirm('Сбросить весь прогресс и начать квест заново?'))return;localStorage.removeItem(STORAGE_KEY);state={unlocked:0,completed:[],trainingIndex:0,score:0,answers:[],lessonSteps:{},lessonScores:{}};save();if(drawMode){drawCtx.clearRect(0,0,drawCanvas.width,drawCanvas.height);setDrawMode(false)}renderStart();toast('Прогресс сброшен')};
$('#soundBtn').onclick=async()=>{const a=$('#melody');try{if(soundOn){a.pause();soundOn=false}else{await a.play();soundOn=true}$('#soundBtn').classList.toggle('active',soundOn);$('#soundBtn').textContent=soundOn?'♫':'♪'}catch(e){toast('Добавьте файл assets/melody.mp3 — и музыка заработает')}};

const drawCanvas=$('#drawCanvas'), drawCtx=drawCanvas.getContext('2d');
let drawing=false, drawMode=false, drawColor='#e63362', lastPoint=null;
function resizeCanvas(){const dpr=Math.max(1,window.devicePixelRatio||1),rect=drawCanvas.getBoundingClientRect();drawCanvas.width=Math.round(rect.width*dpr);drawCanvas.height=Math.round(rect.height*dpr);drawCtx.setTransform(dpr,0,0,dpr,0,0);drawCtx.lineCap='round';drawCtx.lineJoin='round';}
function setDrawMode(on){drawMode=on;drawCanvas.classList.toggle('active',on);$('#drawBtn').classList.toggle('active',on);$('#drawTools').hidden=!on;if(on){resizeCanvas();toast('Рисуйте поверх задания. «Готово» вернёт кнопки игры.')}}
function drawPoint(e){if(!drawing)return;const r=drawCanvas.getBoundingClientRect(),p={x:e.clientX-r.left,y:e.clientY-r.top};drawCtx.strokeStyle=drawColor;drawCtx.lineWidth=+$('#drawSize').value;drawCtx.beginPath();drawCtx.moveTo(lastPoint.x,lastPoint.y);drawCtx.lineTo(p.x,p.y);drawCtx.stroke();lastPoint=p;}
drawCanvas.addEventListener('pointerdown',e=>{if(!drawMode)return;drawing=true;const r=drawCanvas.getBoundingClientRect();lastPoint={x:e.clientX-r.left,y:e.clientY-r.top};drawCanvas.setPointerCapture(e.pointerId)});
drawCanvas.addEventListener('pointermove',drawPoint);drawCanvas.addEventListener('pointerup',()=>{drawing=false;lastPoint=null});drawCanvas.addEventListener('pointercancel',()=>{drawing=false;lastPoint=null});
$('#drawBtn').onclick=()=>setDrawMode(!drawMode);$('#closeDraw').onclick=()=>setDrawMode(false);$('#clearDraw').onclick=()=>drawCtx.clearRect(0,0,drawCanvas.width,drawCanvas.height);
document.querySelectorAll('.color-dot').forEach(b=>b.onclick=()=>{drawColor=b.dataset.color;document.querySelectorAll('.color-dot').forEach(x=>x.classList.toggle('active',x===b))});
function fitCurrentPanel(){const panel=app.querySelector('.panel');if(!panel||innerWidth<=900)return;panel.classList.remove('ultra-compact','micro-compact');const over=()=>{const mainColumn=panel.matches('.lesson')?panel.firstElementChild:null;return panel.scrollHeight>panel.clientHeight+2||(mainColumn&&mainColumn.scrollHeight>mainColumn.clientHeight+2)||panel.getBoundingClientRect().bottom>innerHeight-4};requestAnimationFrame(()=>{if(!over())return;panel.classList.add('ultra-compact');requestAnimationFrame(()=>{if(over())panel.classList.add('micro-compact')})})}
const fitObserver=new MutationObserver(()=>requestAnimationFrame(fitCurrentPanel));fitObserver.observe(app,{childList:true});
window.addEventListener('resize',()=>{if(drawMode)resizeCanvas();fitCurrentPanel()});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&drawMode)setDrawMode(false)});
updateProgress();renderStart();
