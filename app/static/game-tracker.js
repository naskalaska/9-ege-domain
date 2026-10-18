/* Online games call one common recorder at their actual answer checks. */
(() => {
  const slug = document.currentScript?.dataset.game;
  if (!slug || window.recordLearningGameAnswer) return;
  const started = Date.now();
  let owner = null;
  let busy = false;
  let queue = [];
  const key = () => `ege_game_results:${owner}`;
  const save = () => { try { localStorage.setItem(key(), JSON.stringify(queue)); } catch {} };
  const asText = value => typeof value === 'string' ? value : JSON.stringify(value ?? '');
  async function flush() {
    if (!owner || busy || !queue.length) return;
    busy = true;
    try {
      const me = await fetch('/api/auth/me', {credentials:'same-origin'}).then(r=>r.json());
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
    if (!owner) return;
    queue.push({slug, event_id:crypto.randomUUID(), public_id:new URLSearchParams(location.search).get('set') || '',
      is_correct:Boolean(ok),prompt:asText(prompt).slice(0,2000),given_answer:asText(given).slice(0,2000),
      correct_answer:asText(correct).slice(0,2000),time_spent_sec:Math.round((Date.now()-started)/1000)});
    save(); flush();
  };
  fetch('/api/auth/me', {credentials:'same-origin'}).then(r=>r.json()).then(data=>{
    if (!data.user?.has_required_consents) return;
    owner = data.user.user_id;
    try { queue = JSON.parse(localStorage.getItem(key()) || '[]'); if (!Array.isArray(queue)) queue = []; } catch { queue = []; }
    flush();
  }).catch(()=>{});
  window.addEventListener('online',flush);
  setInterval(flush,15000);
})();
