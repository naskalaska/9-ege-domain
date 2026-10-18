/* Online games call one common recorder at their actual answer checks. */
(() => {
  const slug = document.currentScript?.dataset.game;
  if (!slug || window.recordLearningGameAnswer) return;
  const started = Date.now();
  let owner = null;
  let authenticating = false;
  let awaitingAuthentication = true;
  let pendingAnswers = [];
  let busy = false;
  let queue = [];
  const key = () => `ege_game_results:${owner}`;
  const save = () => { try { localStorage.setItem(key(), JSON.stringify(queue)); } catch {} };
  const normalize = value => value instanceof Set ? [...value].map(normalize)
    : value instanceof Map ? Object.fromEntries([...value].map(([k,v])=>[k,normalize(v)]))
    : Array.isArray(value) ? value.map(normalize)
    : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([k,v])=>[k,normalize(v)])) : value;
  const asText = value => value == null ? '' : typeof value === 'string' ? value : JSON.stringify(normalize(value));
  async function flush() {
    if (!owner || busy || !queue.length) return;
    busy = true;
    try {
      const meResponse = await fetch('/api/auth/me', {credentials:'same-origin'});
      if (!meResponse.ok) return;
      const me = await meResponse.json();
      if (me.user?.user_id !== owner) { owner = null; queue = []; return; }
      while (queue.length) {
        const response = await fetch('/api/games/result', {method:'POST',credentials:'same-origin',keepalive:true,
          headers:{'Content-Type':'application/json'},body:JSON.stringify(queue[0])});
        if (!response.ok && response.status !== 400) break;
        queue.shift(); save();
      }
    } catch {} finally { busy = false; }
  }
  window.recordLearningGameAnswer = (ok, prompt = '', given = '', correct = '') => {
    const event = {slug, event_id:crypto.randomUUID(), public_id:new URLSearchParams(location.search).get('set') || '',
      is_correct:Boolean(ok),prompt:asText(prompt).slice(0,20000),given_answer:asText(given).slice(0,12000),
      correct_answer:asText(correct).slice(0,12000),time_spent_sec:Math.round((Date.now()-started)/1000)};
    if (!owner) { if (awaitingAuthentication) pendingAnswers.push(event);return; }
    queue.push(event);
    save(); flush();
  };
  async function authenticate() {
    if (authenticating || !awaitingAuthentication) return;
    authenticating = true;
    try {
      const response = await fetch('/api/auth/me', {credentials:'same-origin'});
      if (!response.ok) return;
      const data = await response.json();
      awaitingAuthentication = false;
      if (!data.user?.has_required_consents) { pendingAnswers=[];return; }
      owner = data.user.user_id;
      try { queue = JSON.parse(localStorage.getItem(key()) || '[]'); if (!Array.isArray(queue)) queue = []; } catch { queue = []; }
      queue.push(...pendingAnswers);pendingAnswers=[];save();flush();
    } catch {} finally { authenticating = false; }
  }
  const resume = () => awaitingAuthentication ? authenticate() : flush();
  authenticate();
  window.addEventListener('online',resume);
  setInterval(resume,15000);
})();
