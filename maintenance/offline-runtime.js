/* Local resource resolver. The binary resources themselves are inside this HTML. */
(() => {
  'use strict';
  const assets = window.__OFFLINE_ASSETS;
  const assetNames = new Map(Object.keys(assets).map(key=>[key.toLowerCase(),key]));
  window.__OFFLINE_FULL_CHECKS = [];
  const misses = new Set();
  window.__OFFLINE_MISSING_RESOURCES = misses;
  const decode = value => { try { return decodeURIComponent(value); } catch { return value; } };
  function resolve(value) {
    if (typeof value !== 'string' || !value || /^(?:data:|blob:|#)/i.test(value)) return value;
    let key = decode(value).replaceAll('\\','/').replace(/^\.\//,'').split('?')[0];
    if (assets[key] || assetNames.has(key.toLowerCase())) return assets[key] || assets[assetNames.get(key.toLowerCase())];
    if (key.startsWith('file:')) {
      try {
        const absolute=decode(new URL(value).pathname),base=decode(new URL('.',location.href).pathname);
        if (absolute.startsWith(base)) key=absolute.slice(base.length);
      } catch {}
      if (assets[key]) return assets[key];
    }
    if (/^Памятки теории\//.test(key)) return value;
    if (/\.(?:png|jpe?g|webp|svg|gif|mp3|wav|ogg|woff2?)(?:$|[?#])/i.test(key) && !/^https?:/i.test(key)) misses.add(key);
    return value;
  }
  window.__OFFLINE_RESOLVE = resolve;
  const css = value => typeof value === 'string' ? value.replace(/url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)/gi, (_,double,single,bare) => `url("${resolve(double ?? single ?? bare.trim())}")`) : value;
  function markup(value) {
    if (typeof value !== 'string') return value;
    return css(value.replace(/\b(src|poster)\s*=\s*(["'])(.*?)\2/gi, (_,name,quote,url)=>`${name}=${quote}${resolve(url)}${quote}`));
  }
  const setAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function(name,value) {
    if (/^(src|poster)$/i.test(name)) value = resolve(String(value));
    else if (name.toLowerCase()==='style') value = css(String(value));
    return setAttribute.call(this,name,value);
  };
  for (const [proto,name] of [[HTMLImageElement.prototype,'src'],[HTMLMediaElement.prototype,'src'],[HTMLSourceElement.prototype,'src'],[HTMLVideoElement.prototype,'poster']]) {
    const original = Object.getOwnPropertyDescriptor(proto,name);
    if (original?.set) Object.defineProperty(proto,name,{...original,set(value){return original.set.call(this,resolve(value));}});
  }
  for (const name of ['innerHTML','outerHTML']) {
    const original = Object.getOwnPropertyDescriptor(Element.prototype,name);
    if (original?.set) Object.defineProperty(Element.prototype,name,{...original,set(value){return original.set.call(this,markup(value));}});
  }
  const insert = Element.prototype.insertAdjacentHTML;
  Element.prototype.insertAdjacentHTML = function(position,value){return insert.call(this,position,markup(value));};
  const originalSet = CSSStyleDeclaration.prototype.setProperty;
  CSSStyleDeclaration.prototype.setProperty = function(name,value,priority){return originalSet.call(this,name,css(value),priority);};
  const originalCssText = Object.getOwnPropertyDescriptor(CSSStyleDeclaration.prototype,'cssText');
  if (originalCssText?.set) Object.defineProperty(CSSStyleDeclaration.prototype,'cssText',{...originalCssText,set(value){originalCssText.set.call(this,css(value));}});
  for (const name of ['background','backgroundImage','borderImage','borderImageSource','listStyleImage','maskImage','webkitMaskImage','cursor']) {
    const property = name.replace(/[A-Z]/g,c=>'-'+c.toLowerCase());
    Object.defineProperty(CSSStyleDeclaration.prototype,name,{configurable:true,enumerable:true,
      get(){return this.getPropertyValue(property);},set(value){originalSet.call(this,property,css(value));}});
  }
  const AudioOriginal = window.Audio;
  window.Audio = function(src){return src == null ? new AudioOriginal() : new AudioOriginal(resolve(src));};
  window.Audio.prototype = AudioOriginal.prototype;
  const fetchOriginal = window.fetch.bind(window);
  window.fetch = function(input,options) {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (/^(?:https?:|\/api\/)/i.test(url)) return Promise.reject(new Error('Для офлайн-игры сервер не требуется. Используйте встроенный набор или загрузите локальный файл.'));
    return fetchOriginal(typeof input === 'string' ? resolve(input) : input,options);
  };
  window.KARAOKE_DEMO_LIMIT = 0;
  window.ORTHOSHOOTING_DEMO_LIMIT = 0;
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[href]');
    if (!link) return;
    const href=link.getAttribute('href');
    if (/^\/(?:games|apps|html-games)(?:\/|$)/.test(href)) {event.preventDefault();location.href='../Открыть игры.html';}
  });
})();
