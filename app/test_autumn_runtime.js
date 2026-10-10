// Exercise the actual mini-game script with a minimal DOM, without a browser dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function element() {
  return {
    children: [], childNodes: [{}, {}, {}], dataset: {}, style: {}, hidden: false,
    textContent: '', disabled: false, offsetWidth: 80, offsetHeight: 90,
    classList: {add() {}, remove() {}},
    setAttribute() {}, addEventListener() {}, focus() {}, remove() {},
    append(...items) {this.children.push(...items);},
    replaceChildren(...items) {this.children = items;},
    getBoundingClientRect() {return {width: 900, height: 600};},
  };
}

async function run(items, fail = false) {
  const nodes = new Map();
  const get = key => {if (!nodes.has(key)) nodes.set(key, element()); return nodes.get(key);};
  const defaults = ['и', 'ы'].map(letter => Object.assign(element(), {dataset: {letter}}));
  const context = vm.createContext({
    document: {
      getElementById: get, querySelector: get,
      querySelectorAll: () => defaults,
      createElement: element, createTextNode: text => ({textContent: text}),
      addEventListener() {},
    },
    window: {matchMedia: () => ({matches: false})},
    location: {search: items ? '?set=test' : ''}, URLSearchParams,
    requestAnimationFrame() {},
    fetch: async () => ({ok: !fail, json: async () => ({mechanic: 'autumn-leaves', title: 'Моя осень', items})}),
  });
  const html = fs.readFileSync(path.join(__dirname, 'HTML/Осень. И-Ы/autumn.html'), 'utf8');
  const code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  vm.runInContext(code, context);
  await new Promise(resolve => setImmediate(resolve));
  if (fail) {
    assert.equal(get('start').disabled, true);
    assert.match(get('#intro .subtitle').textContent, /Не удалось загрузить/);
    return;
  }
  vm.runInContext('startGame()', context);
  const total = vm.runInContext('ROUND_SIZE', context);
  assert.equal(total, items ? items.length : 15);
  if (items) {
    assert.equal(get('.counter').childNodes[1].textContent, ` / ${total} листьев`);
    assert.equal(get('.counter').childNodes[2].textContent, undefined);
  }
  vm.runInContext(`
    for (const leaf of leaves) {
      openQuestion(leaf);
      if (teacherTitle && answers.length !== leaf.q.options.length) throw Error('Wrong answer buttons');
      checkAnswer(leaf.q.answer);
      closeQuestion();
    }
    if (score !== ROUND_SIZE || running || $('finish').hidden) throw Error('Round did not finish');
  `, context);
  assert.equal(Number(get('score').textContent), total);
}

(async () => {
  await run(null);
  const items = [
    {variant: 'з..ря', answer: 'а', options: ['а', 'о'], correct_spelling: 'заря'},
    {variant: 'дли..ый', answer: 'нн', options: ['н', 'нн'], correct_spelling: 'длинный'},
    {variant: 'об..ём', answer: 'ъ', options: ['ь', 'ъ', '-'], correct_spelling: 'объём'},
  ];
  await run(items);
  await run(items, true);
  console.log('Autumn runtime: built-in round, custom answers, small set, unavailable set passed');
})();
