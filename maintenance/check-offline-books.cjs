const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..'),qa=path.join(__dirname,'offline-qa'),out=path.join(root,'HTML-игры — полные офлайн-версии');
const manifest=JSON.parse(fs.readFileSync(path.join(qa,'manifest.json'),'utf8'));
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',['--headless=new','--disable-gpu','--no-first-run','--remote-debugging-port=9236','--user-data-dir='+path.join(qa,'browser'),'about:blank'],{windowsHide:true,stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let ws;
 try{
  let tabs;
  for(let i=0;i<60;i++){try{tabs=await(await fetch('http://127.0.0.1:9236/json')).json();break}catch{await delay(200)}}
  assert(tabs,'Chrome did not start');
  ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
  let seq=0;const pending=new Map(),requests=[];
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))});
  ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}else if(m.method==='Fetch.requestPaused'){requests.push(m.params.request.url);send('Fetch.failRequest',{requestId:m.params.requestId,errorReason:'InternetDisconnected'})}};
  await send('Page.enable');await send('Runtime.enable');await send('Fetch.enable',{patterns:[{urlPattern:'http://*'},{urlPattern:'https://*'}]});
  const pages=['Открыть игры.html',...manifest.filter(g=>g.has_theory).map(g=>g.folder+'/Памятки теории/Памятки.html')],results=[];
  for(const file of pages){
   await send('Page.navigate',{url:pathToFileURL(path.join(out,file)).href});await delay(300);
   const r=await send('Runtime.evaluate',{expression:`(async()=>{await Promise.all([...document.images].map(i=>{i.loading="eager";return i.decode()}));return{charset:document.characterSet,text:document.body.innerText.length,images:document.images.length,links:[...document.querySelectorAll('a[href]')].map(a=>a.href)}})()`,awaitPromise:true,returnByValue:true});
   assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));const v=r.result.value;assert.equal(v.charset,'UTF-8');assert(v.text>80||v.images>0);assert(v.links.every(l=>l.startsWith('file:')));if(file===pages[0])assert.equal(v.links.filter(l=>l.endsWith('/%D0%98%D0%B3%D1%80%D0%B0.html')).length,25);
   results.push({file,...v,pass:true});console.log('PASS',file);
  }
  assert.equal(requests.length,0);fs.writeFileSync(path.join(qa,'books-check.json'),JSON.stringify({pages:results,networkRequests:requests},null,2));
 }finally{ws?.close();chrome.kill()}
})().catch(e=>{console.error(e);process.exitCode=1});
