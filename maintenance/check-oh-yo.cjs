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
for(const [width,height] of [[320,568],[360,800],[390,844],[580,800],[768,1024],[1024,768],[1440,900],[844,390]]){
await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
for(const [name,expression] of [['home',"home('level')"],['stories',"home('story')"],['well',"state.level=4;state.mode=0;start()"],['apples',"state.mode=1;start()"],['forest',"state.mode=2;start()"],['rules','bayunRules()'],['memos','openMemos()'],['stats','stats()'],['errors','errorsPage()'],['dialog',"home();showMemo('root')"]]){
await ev("document.querySelector('#modal').close();"+expression);await delay(100);
const check=await ev(`(()=>{const w=innerWidth;return {width:w,scroll:document.documentElement.scrollWidth,over:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().width&&getComputedStyle(e).position!=='absolute'&&e.getBoundingClientRect().right>w+1).slice(0,10).map(e=>e.tagName+'.'+e.className)}})()`);
results.push({screen:[width,height],page:name,...check});
if((width===390&&['home','stories','apples','dialog'].includes(name))||(width===1440&&name==='well')){const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(root,`maintenance/oh-yo-${width}-${name}.png`),Buffer.from(shot.result.data,'base64'));}
}
}
fs.writeFileSync(path.join(root,'maintenance/oh-yo-responsive.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results.filter(r=>r.scroll>r.width||r.over.length),null,2));console.log('Checked',results.length,'screens/states');ws.close();
}finally{chrome.kill()}})().catch(e=>{console.error(e);process.exitCode=1});

