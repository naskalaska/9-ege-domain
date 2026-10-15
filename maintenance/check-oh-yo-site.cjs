const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const chrome=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=9225','--remote-allow-origins=*','--user-data-dir='+path.join(root,'maintenance/oh-yo-browser'),'about:blank'],{stdio:['ignore','ignore','pipe']});
chrome.stderr.on('data',d=>console.error(String(d)));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{try{
let tabs;for(let i=0;i<60;i++){try{tabs=await(await fetch('http://127.0.0.1:9225/json')).json();break}catch{await delay(200)}}
const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);let id=0;const pending=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){pending.get(m.id)(m);pending.delete(m.id)}};
const send=(method,params={})=>new Promise(r=>{pending.set(++id,r);ws.send(JSON.stringify({id,method,params}))});
const ev=async expression=>{let r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.result.exceptionDetails)throw Error(JSON.stringify(r.result.exceptionDetails));return r.result.result.value};
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:process.env.OH_YO_URL||'file:///'+path.join(root,'app/HTML/Ох, ё! Сказание о шипящих/Ох_ё_сказание о шипящих.html').replaceAll('\\','/')});await delay(1500);
const results=[];
for(const [width,height] of [[320,568],[390,844],[768,1024],[1440,900]]){
 await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
 for(const url of ['/games','/shop','/shop/oh-yo']){
  await send('Page.navigate',{url:'http://127.0.0.1:8096'+url});await delay(1000);
  const data=await ev(`(()=>({url:location.pathname,width:innerWidth,scroll:document.documentElement.scrollWidth,text:document.body.innerText.includes('Ох, ё!'),price:document.body.innerText.includes('400 ₽'),gallery:document.querySelectorAll('[data-gallery-index]').length,badImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)}))()`);
  if(!data.text||data.scroll>width||data.badImages.length)throw Error(JSON.stringify(data));
  if(url==='/shop/oh-yo'){
   if(!await ev("document.querySelector('.product-detail-summary .eyebrow').textContent==='ИГРА'")||!data.price||data.gallery!==5)throw Error('Missing price/gallery');
   await ev("document.querySelector('[data-gallery-next]').click()");await delay(200);
   if(await ev("document.querySelector('[data-gallery-current]').textContent")!=='2')throw Error('Carousel failed');
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(root,`maintenance/oh-yo-shop-${width}.png`),Buffer.from(shot.result.data,'base64'));
  }
  results.push(data);
 }
}
await send('Page.navigate',{url:'http://127.0.0.1:8096/games/oh-yo/index.html'});await delay(800);
for(const mode of [0,1,2]){
 await ev(`state.level=4;state.mode=${mode};start()`);await delay(1600);
 const data=await ev("(()=>{const expected=current().answer;answer(expected);return {mode:state.mode,correct:state.session.correct,answered:state.session.answered}})()");
 if(data.correct!==1||!data.answered)throw Error(JSON.stringify(data));results.push(data);
 await delay(1700);
 if(await ev('state.session.index')!==1)throw Error('Auto next failed');
 await delay(1500);
 await ev("answer(['о','е','ё'].find(a=>a!==current().answer))");
 if(!await ev('state.session.answered && !state.session.lastCorrect'))throw Error('Wrong answer failed');
 await ev('next()');await delay(1000);
 if(await ev('state.session.index')!==2)throw Error('Continue failed');
}
console.log(JSON.stringify(results,null,2));fs.writeFileSync(path.join(root,'maintenance/oh-yo-site-check.json'),JSON.stringify(results,null,2));ws.close();
}finally{chrome.kill()}})().catch(e=>{console.error(e);process.exitCode=1});



