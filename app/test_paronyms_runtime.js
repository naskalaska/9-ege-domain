const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, 'HTML', 'Паронимы');
const source = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
function load(protocol, pathname, memory = new Map()) {
  const nodes = new Map();
  const listeners = {};
  function node() {
    const classes = new Set();
    return {
      textContent: '', innerHTML: '', dataset: {},
      classList: {
        add: c => classes.add(c), remove: c => classes.delete(c),
        contains: c => classes.has(c),
        toggle(c, on) { if (on) classes.add(c); else classes.delete(c); },
      },
      addEventListener() {}, querySelectorAll: () => [],
      querySelector: () => ({focus() {}}), append() {},
    };
  }
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, node());
    return nodes.get(id);
  };
  get('#demoLimit').classList.add('hidden');
  const context = vm.createContext({
    window: {location: {protocol, pathname}, setTimeout: fn => fn()},
    localStorage: {
      getItem: key => memory.get(key), setItem: (key, value) => memory.set(key, value),
      removeItem: key => memory.delete(key),
    },
    document: {
      querySelector: get, querySelectorAll: () => [], createElement: node,
      addEventListener(type, handler, capture) {
        assert.equal(capture, true);
        listeners[type] = handler;
      },
    },
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'cards-manifest.js'), 'utf8'), context);
  vm.runInContext(source.replace(/\}\(\)\);\s*$/, `
    window.test = {DEMO_MODE, playableCards, state, el, startGame, checkAnswer,
      nextCard, resetCurrent, pickSet, renderGroupPicker};
  }());`), context);
  return {...context.window.test, listeners, memory, get};
}

const offline = load('file:', '/C:/Games/Паронимы/index.html');
const online = load('https:', '/full-games/paronyms/index.html');
const demo = load('https:', '/games/paronyms/index.html');
assert.equal(offline.DEMO_MODE, false);
assert.equal(online.DEMO_MODE, false);
assert.equal(demo.DEMO_MODE, true);
assert.equal(demo.playableCards.length, 140);
assert.ok(offline.playableCards.length > 20);
assert.equal(offline.playableCards.length, online.playableCards.length);
assert.equal(offline.listeners.click, undefined);
assert.equal(online.listeners.click, undefined);

function clickDemo(game, excluded = false, interactive = true) {
  let blocked = false;
  game.listeners.click({
    target: {closest(selector) {
      if (selector === '#demoLimit, #gameMenuLink, a') return excluded;
      if (selector === 'button, input, select, textarea') return interactive;
      throw Error(selector);
    }},
    preventDefault() {blocked = true;}, stopImmediatePropagation() {blocked = true;},
  });
  return blocked;
}
clickDemo(demo, true);
clickDemo(demo, false, false);
assert.equal(demo.memory.size, 0);
for (let i = 0; i < 39; i++) assert.equal(clickDemo(demo), false);
assert.equal(demo.get('#demoLimit').classList.contains('hidden'), true);
assert.equal(clickDemo(demo), false); // The 40th action is allowed.
assert.equal(demo.get('#demoLimit').classList.contains('hidden'), false);
assert.equal(clickDemo(demo), true); // Further actions are blocked.
assert.equal(demo.memory.get('paronyms-demo-actions-v1'), '40');
const reloaded = load('https:', '/games/paronyms/index.html', demo.memory);
assert.equal(reloaded.get('#demoLimit').classList.contains('hidden'), false);
assert.equal(clickDemo(reloaded), true);
const fullAfterDemo = load('https:', '/full-games/paronyms/index.html', demo.memory);
assert.equal(fullAfterDemo.listeners.click, undefined);
assert.equal(fullAfterDemo.get('#demoLimit').classList.contains('hidden'), true);
demo.state.search = 'почтенный';
demo.renderGroupPicker();
assert.match(demo.el.groupList.innerHTML, /почтенный/);
assert.doesNotMatch(demo.el.groupList.innerHTML, /абонент/);

let assets = 0;
for (const card of offline.playableCards) {
  for (const filename of [...card.words.map(word => card.images[word]), card.explanationImage]) {
    assert.ok(filename, `Missing filename in ${card.title}`);
    assert.ok(fs.statSync(path.join(root, 'assets', card.folder, filename)).size > 0);
    assets++;
  }
  assert.doesNotMatch(JSON.stringify(card), /постенный/i);
}
const target = offline.playableCards.find(card => card.words.includes('почтенный'));
assert.ok(target);
offline.state.customSelected.add(target.id);
offline.startGame('custom');
offline.checkAnswer();
assert.equal(offline.el.message.textContent, 'Подпиши все картинки.');
const words = offline.state.current.words;
words.forEach((word, i) => offline.state.assignments[word] = words[(i + 1) % words.length]);
offline.checkAnswer();
assert.equal(offline.state.errors, 1);
assert.equal(offline.state.queue.length, 1);
assert.equal(offline.el.explanationScreen.classList.contains('hidden'), false);
assert.ok(offline.el.explanationImage.src.includes(encodeURIComponent(target.explanationImage)));
offline.nextCard(false);
assert.equal(offline.state.current.id, target.id);
words.forEach(word => offline.state.assignments[word] = word);
offline.resetCurrent();
assert.equal(Object.keys(offline.state.assignments).length, 0);
words.forEach(word => offline.state.assignments[word] = word);
offline.checkAnswer();
offline.nextCard(false);
assert.equal(offline.el.finishScreen.classList.contains('hidden'), false);
assert.equal(offline.el.finishErrors.textContent, 'Ошибок: 1');

for (const mode of ['fresh', 'random']) {
  offline.startGame(mode);
  assert.equal(offline.state.totalGroups, 20);
  for (let i = 0; i < 20; i++) {
    offline.state.current.words.forEach(word => offline.state.assignments[word] = word);
    offline.checkAnswer();
    offline.nextCard(false);
  }
  assert.equal(offline.state.solved, 20);
  assert.equal(offline.state.errors, 0);
  assert.equal(offline.el.finishScreen.classList.contains('hidden'), false);
}
console.log(`Paronyms: ${offline.playableCards.length} groups in all modes, ${assets} assets; 40 demo actions, blocking/reload, unlimited full/offline, search, answers, retry, explanation, reset and rounds passed.`);
