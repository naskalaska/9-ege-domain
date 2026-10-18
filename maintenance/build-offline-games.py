"""Build full file:// game editions: one HTML plus external theory handouts."""
from __future__ import annotations
import base64
import hashlib
import html
import json
import mimetypes
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'HTML-игры — полные офлайн-версии'
QA = ROOT / 'maintenance' / 'offline-qa'
sys.path.insert(0, str(ROOT / 'app'))
import server

IMAGE = re.compile(r'data:image/([\w.+-]+);base64,([A-Za-z0-9+/=]+)')
RUNTIME = (Path(__file__).parent / 'offline-runtime.js').read_text(encoding='utf-8')
BASE_STYLE = 'body{max-width:1100px;margin:32px auto;padding:0 22px 50px;font:18px/1.6 Arial,sans-serif;color:#172844;background:#f4f7fb}h1,h2,h3{line-height:1.25}section,figure{margin:24px 0;padding:24px;border:1px solid #d9e0ed;border-radius:16px;background:white}img{max-width:100%;height:auto}figure img{display:block;margin:auto}a{color:#194e9b}table{border-collapse:collapse}td,th{border:1px solid #ccd4e0;padding:8px}button{display:none}.help-grid,.guide-grid,.theory-grid,.rule-grid{display:grid;gap:18px}li{margin:8px 0}@media print{body{background:#fff;font-size:12pt}section,figure{break-inside:avoid;border:0}nav{display:none}}'


def safe_name(value):
    return re.sub(r'[<>:"/\\|?*]', ' ', value).strip(' .')


def expression_span(source, name, start=0):
    found = re.search(r'\b(?:const|let|var)\s+' + re.escape(name) + r'\s*=\s*', source[start:])
    if not found:
        return None
    begin = start + found.end()
    return begin, expression_end(source, begin)


def expression_end(source, begin):
    stack = []
    string = None
    escaped = False
    line_comment = block_comment = False
    i = begin
    while i < len(source):
        c = source[i]
        nxt = source[i:i+2]
        if line_comment:
            if c == '\n': line_comment = False
        elif block_comment:
            if nxt == '*/': block_comment = False; i += 1
        elif string:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == string: string = None
        elif nxt == '//': line_comment = True; i += 1
        elif nxt == '/*': block_comment = True; i += 1
        elif c in "\"'`": string = c
        elif c in '{[(': stack.append(c)
        elif c in '}])':
            if not stack: return i
            stack.pop()
            if not stack and source[begin] in '{[(': return i+1
        elif not stack and c in ';\n': return i
        i += 1
    raise ValueError('Unterminated expression')


def expression(source, name):
    span = expression_span(source, name)
    return source[span[0]:span[1]] if span else None


def js_value(expr, setup=''):
    if not expr: return None
    runner = "const vm=require('node:vm'),fs=require('node:fs');const d=JSON.parse(fs.readFileSync(0,'utf8'));const c=vm.createContext({window:{}});vm.runInContext(d.setup,c);const v=vm.runInContext('('+d.expr+')',c,{timeout:5000});process.stdout.write(JSON.stringify(v));"
    result = subprocess.run(['node','-e',runner],input=json.dumps({'expr':expr,'setup':setup},ensure_ascii=False).encode(),capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace')[:500])
    return json.loads(result.stdout)


def book_document(title, body):
    return f'<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{BASE_STYLE}</style><nav><a href="../Игра.html">← К игре</a></nav><h1>{html.escape(title)}</h1>{body}</html>'


def render_text(value):
    if value is None: return ''
    if isinstance(value, str):
        if value.startswith(('data:','assets/','Памятки теории/')): return ''
        if re.search(r'</?(?:p|b|strong|div|ol|ul|li|span|em|section|h[1-6])\b',value):
            return '<div>'+value+'</div>'
        return '<p>'+html.escape(value)+'</p>'
    if isinstance(value, list):
        if value and all(isinstance(v,list) for v in value):
            return '<table>'+''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in value)+'</table>'
        return ''.join(render_text(v) for v in value)
    if isinstance(value, dict):
        title = value.get('theoryTitle') or value.get('title') or value.get('label') or value.get('short')
        body = '<h2>'+html.escape(str(title))+'</h2>' if title else ''
        selected = ['body','rule','rules','memo','intro','formula','principle','note','steps','example','examples','tips','lines','tags']
        for key in selected:
            if key in value: body += render_text(value[key])
        if not body:
            body = ''.join(render_text(v) for k,v in value.items() if k not in {'art','asset','assets','image','img','recipe','questions','tasks','options','answer','correct'})
        return '<section>'+body+'</section>' if body else ''
    return ''


class GameBuilder:
    def __init__(self, slug, folder, output):
        self.slug, self.folder, self.output = slug, folder, output
        self.title = server.HTML_GAME_TITLES.get(slug, 'Пушинки — свои наборы')
        self.assets = {}
        self.theory = []
        self.theory_hashes = {}
        self.embedded_count = 0
        self.source_files = []
        self.text_theory = []
        self.warnings = []

    def save_theory(self, data, name, title=None):
        digest = hashlib.sha256(data).hexdigest()
        if digest in self.theory_hashes: return self.theory_hashes[digest]
        name = safe_name(name)
        target = self.output/'Памятки теории'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        relative = 'Памятки теории/'+name
        self.theory.append({'file':relative,'title':title or Path(name).stem,'sha256':digest})
        self.theory_hashes[digest] = relative
        return relative

    def externalize_data(self, source):
        ranges = []
        if self.slug == 'oh-yo':
            assets = json.loads(expression(source,'ASSETS'))
            for key,title in [('memo-root','О, Е, Ё в корне'),('memo-suffix','О, Е, Ё в суффиксах и окончаниях')]:
                value=assets[key];match=IMAGE.fullmatch(value)
                path=self.save_theory(base64.b64decode(match[2]),title+'.'+match[1],title)
                source=source.replace(value,path)
        elif self.slug == 'word-architecture':
            for name in ['memoImages','memoNewImages']:
                span=expression_span(source,name)
                if span:ranges.append(span)
        elif self.slug == 'participle-map':
            # The source replaces two early posters with corrected full posters.
            # Export only the currently used artwork, rather than the superseded copies.
            initial=expression_span(source,'theoryCards')
            initial_value=js_value(source[initial[0]:initial[1]])
            for match in list(re.finditer(r'theoryCards\.(\w+)\s*=\s*\{',source)):
                begin=source.index('{',match.start());end=expression_end(source,begin)
                updated=js_value(source[begin:end])
                key=match[1]
                old=initial_value.get(key,{}).get('asset')
                if old and updated.get('asset'):source=source.replace(old,updated['asset'])
            span=expression_span(source,'theoryCards')
            if span:ranges.append(span)
            for match in re.finditer(r'theoryCards\.\w+\s*=\s*\{',source):
                begin=source.index('{',match.start());ranges.append((begin,expression_end(source,begin)))
        replacements={}
        for begin,end in ranges:
            for match in IMAGE.finditer(source,begin,end):
                uri=match[0]
                if uri not in replacements:
                    extension={'jpeg':'jpg','svg+xml':'svg'}.get(match[1],match[1])
                    index=len(self.theory)+1
                    replacements[uri]=self.save_theory(base64.b64decode(match[2]),f'Памятка {index:02d}.{extension}',f'Памятка {index:02d}')
        for uri,path in replacements.items():source=source.replace(uri,path)
        return source

    def theory_paths(self):
        found=set()
        if self.slug=='paronyms':
            source=(self.folder/'cards-manifest.js').read_text(encoding='utf-8-sig')
            cards=json.loads(source[source.index('['):].rstrip().removesuffix(';'))
            for index,card in enumerate(cards,1):
                path=self.folder/'assets'/card['folder']/card['explanationImage']
                self.assets[path.relative_to(self.folder).as_posix()]=self.save_theory(path.read_bytes(),f'{index:03d} {card["title"]}{path.suffix}',card['title'])
                found.add(path)
        for p in self.folder.rglob('*'):
            if not p.is_file():continue
            is_theory = (
                self.slug=='numerals-hit-parade' and p.name.lower().startswith('памятка') or
                self.slug=='karaoke-numerals' and (p.name.startswith('memo-') or 'drawn-memos' in p.parts) or
                self.slug=='verb-conjugation-quest' and p.name=='Алгоритм полный.png' or
                self.slug=='grammar-zoo' and p.name.lower().startswith('теория ') or
                self.slug=='parts-of-speech-kingdom' and p.name.lower().startswith('памятка')
            )
            if is_theory:
                self.assets[p.relative_to(self.folder).as_posix()]=self.save_theory(p.read_bytes(),p.name)
                found.add(p)
        return found

    def load_assets(self):
        handouts=self.theory_paths()
        reference_text='\n'.join(p.read_text(encoding='utf-8-sig',errors='replace') for p in self.folder.rglob('*')
                                  if p.is_file() and p.suffix in {'.html','.js','.css','.json'}).lower()
        reference_text=unquote(reference_text)
        suffixes={'.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.mp3','.wav','.ogg','.mp4','.woff','.woff2','.ttf'}
        for p in sorted(self.folder.rglob('*')):
            if not p.is_file() or p.suffix.lower() not in suffixes or p in handouts:continue
            if p.name.lower() not in reference_text:
                # Product gallery screenshots are stored beside some self-contained games.
                # They are not part of the offline game's resource graph.
                continue
            mime=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
            self.assets[p.relative_to(self.folder).as_posix()]='data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode('ascii')
            self.embedded_count+=1

    def resolve(self, value):
        key=unquote(html.unescape(value)).split('?')[0].removeprefix('./')
        return self.assets.get(key,next((v for k,v in self.assets.items() if k.lower()==key.lower()),value))

    def css(self, source):
        return re.sub(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^)]*))\s*\)',
                      lambda m:'url("'+self.resolve(next(g for g in m.groups() if g is not None).strip())+'")',source,flags=re.I)

    def script(self, source):
        source=re.sub(r'(\b(?:const|let|var)\s+DEMO_MODE\s*=)[^;]+;',r'\1 false;window.__OFFLINE_FULL_CHECKS.push(["DEMO_MODE",DEMO_MODE]);',source)
        source=source.replace('Number(window.KARAOKE_DEMO_LIMIT || 0)','0').replace('Number(window.ORTHOSHOOTING_DEMO_LIMIT||0)','0')
        # Round lengths are game mechanics; only explicit demo flags are disabled.
        source=re.sub(r'function\s+goToGamesMenu\s*\([^)]*\)\s*\{',lambda m:m[0],source)
        marker=re.search(r'function\s+goToGamesMenu\s*\([^)]*\)\s*\{',source)
        if marker:
            begin=source.index('{',marker.start());end=expression_end(source,begin)
            source=source[:begin]+"{window.location.href='../Открыть игры.html';}"+source[end:]
        if self.slug=='fluffs':
            marker=re.search(r'async\s+function\s+loadGameData\s*\(\)\s*\{',source)
            if marker:
                begin=source.index('{',marker.start());end=expression_end(source,begin)
                body="""{const bank=window.__OFFLINE_FLUFFS_BANK;const size=document.querySelector('#offlineRoundSize')?.value||'20';return {...bank,description:'Начать игру',items:shuffleArray(bank.items).slice(0,size==='all'?bank.items.length:Number(size))};}"""
                source=source[:begin]+body+source[end:]
        return source.replace('</script','<\\/script')

    def collect_text_theory(self, source):
        names={
            'oh-yo':['ROOT_TEXT','SUFFIX_TEXT','JUNIOR_ROOT_TEXT','JUNIOR_SUFFIX_TEXT'],
            'autumn-herbarium':['prefixRules'],
            'numerals-hit-parade':['STAGES'],
            'summer-gerund-bar':['lessons'],
            'parts-of-speech-kingdom':['CAT'],
            'expedition-memory-isolated-members':['SKILLS'],
            'participle-map':['theoryGuides','theoryCards'],
            'word-architecture':['memo'],
        }.get(self.slug,[])
        for name in names:
            try:
                value=js_value(expression(source,name))
                if self.slug=='participle-map' and name=='theoryCards':
                    for match in re.finditer(r'theoryCards\.(\w+)\s*=\s*\{',source):
                        begin=source.index('{',match.start())
                        value[match[1]]=js_value(source[begin:expression_end(source,begin)])
                if value is not None:self.text_theory.append(render_text(value))
            except Exception as error:self.warnings.append('Текст памятки '+name+': '+str(error)[:180])
        if self.slug=='autumn-leaves':
            match=re.search(r'<details>\s*<summary>Вспомнить правило</summary>(.*?)</details>',source,re.S)
            if match:self.text_theory.append(match[1])
        if self.slug=='autumn-herbarium':
            match=re.search(r'<script[^>]+id="gameData"[^>]*>(.*?)</script>',source,re.S)
            data=json.loads(match[1])
            for topic in data['topics']:
                if topic.get('rules'):self.text_theory.append(render_text({'title':topic['title'],'rules':topic['rules']}))
        if self.slug=='karaoke-numerals':
            p=self.folder/'theory-v10.js';raw=p.read_text(encoding='utf-8-sig')
            self.text_theory.append(render_text(js_value('window.KARAOKE_THEORY',raw)))
        if self.slug=='syntactic-soup':
            match=re.search(r'<dialog[^>]+id="rulesDialog"[^>]*>(.*?)</dialog>',source,re.S)
            if match:self.text_theory.append(match[1])
        if self.slug=='foxwarts-syntax':
            try:
                role_meta=expression(source,'ROLE_META');role_order=expression(source,'ROLE_ORDER')
                begin=source.index('function renderHelpLegend()');end=source.index('function openCharacteristic()',begin)
                setup=f'const ROLE_META={role_meta};const ROLE_ORDER={role_order};'+source[begin:end]
                value=js_value(expression(source,'help'),setup)
                self.text_theory.append(render_text(value))
            except Exception as error:self.warnings.append('Памятки Фоксвартса: '+str(error)[:180])

    def build(self):
        self.output.mkdir(parents=True,exist_ok=True)
        self.load_assets()
        entry=self.folder/server.game_entry_file(self.slug,'index.html')
        source=entry.read_text(encoding='utf-8-sig')
        self.source_files.append(entry.relative_to(ROOT).as_posix())
        source=self.externalize_data(source)
        combined=source+'\n'+'\n'.join(p.read_text(encoding='utf-8-sig') for p in self.folder.glob('*.js'))
        self.collect_text_theory(combined)
        def stylesheet(match):
            attrs=match[0]
            href=re.search(r'\bhref=["\']([^"\']+)["\']',attrs,re.I)
            if not href:return attrs
            path=self.folder/unquote(href[1].split('?')[0])
            if not path.is_file():raise FileNotFoundError(path)
            self.source_files.append(path.relative_to(ROOT).as_posix())
            return '<style data-offline-source="'+html.escape(path.name)+'">'+self.css(path.read_text(encoding='utf-8-sig'))+'</style>'
        source=re.sub(r'<link\b(?=[^>]*\brel=["\']stylesheet["\'])[^>]*>',stylesheet,source,flags=re.I)
        def scripts(match):
            attrs,code=match[1],match[2]
            src=re.search(r'\bsrc=["\']([^"\']+)["\']',attrs,re.I)
            if src:
                path=self.folder/unquote(src[1].split('?')[0])
                if not path.is_file():raise FileNotFoundError(path)
                self.source_files.append(path.relative_to(ROOT).as_posix())
                code=path.read_text(encoding='utf-8-sig')
                attrs=re.sub(r'\bsrc=["\'][^"\']+["\']','data-offline-source="'+html.escape(path.name)+'"',attrs,flags=re.I)
            if not re.search(r'type=["\']application/(?:json|ld\+json)["\']',attrs,re.I):code=self.script(code)
            return '<script'+attrs+'>'+code+'</script>'
        source=re.sub(r'<script\b([^>]*)>(.*?)</script>',scripts,source,flags=re.S|re.I)
        # Rewrite static markup and CSS without duplicating the resource dictionary into JS.
        chunks=re.split(r'(<script\b[^>]*>.*?</script>)',source,flags=re.S|re.I)
        for i,chunk in enumerate(chunks):
            if chunk.lower().startswith('<script'):continue
            chunk=re.sub(r'\b(src|poster)\s*=\s*(["\'])(.*?)\2',lambda m:m[1]+'='+m[2]+self.resolve(m[3])+m[2],chunk,flags=re.I)
            chunks[i]=self.css(chunk)
        source=''.join(chunks)
        asset_json=json.dumps(self.assets,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
        # The encoding declaration must precede the large inline resource dictionary.
        boot='<meta charset="utf-8"><meta name="offline-edition" content="full"><meta http-equiv="Content-Security-Policy" content="connect-src data: blob:; object-src \'none\'; frame-src \'none\'">'
        extra=''
        if self.slug=='fluffs':
            words=server.ege11_module.WORDS
            bank={'title':'Пушинки — суффиксы. Полная база задания 11','items':[
                {'id':word['id'],'variant':word['variant'],'answer':word['correct_letter'],
                 'options':server.ege11_module.letter_choices(word),'correct_spelling':word['correct_spelling'],
                 'explanation':word['explanation']} for word in words]}
            extra='window.__OFFLINE_FLUFFS_BANK='+json.dumps(bank,ensure_ascii=False).replace('</','<\\/')+';'
        boot+='<script>window.__OFFLINE_ASSETS='+asset_json+';window.__OFFLINE_BUNDLE_INFO='+json.dumps({'slug':self.slug,'full':True,'theory':self.theory,'embedded_files':self.embedded_count},ensure_ascii=False)+';'+extra+RUNTIME+'</script>'
        source=re.sub(r'(<head\b[^>]*>)',lambda m:m[0]+boot,source,count=1,flags=re.I)
        if self.slug=='fluffs':
            controls='''<section style="position:relative;z-index:10;max-width:520px;margin:16px auto;background:#fffffff0;padding:14px;border-radius:14px;font:16px Arial;color:#24364d"><label>Слов за игру <select id="offlineRoundSize"><option>20</option><option>40</option><option value="all">Вся база</option></select></label><p id="offlineBankCount"></p><label>Открыть свой набор заданий <input id="offlineBankFile" type="file" accept=".json,application/json"></label><p id="offlineBankError" role="status"></p></section>'''
            source=source.replace('<div class="start-btn" id="startBtn">',controls+'<div class="start-btn" id="startBtn">')
            initializer='''<script>(()=>{const count=()=>document.querySelector('#offlineBankCount').textContent='В базе: '+window.__OFFLINE_FLUFFS_BANK.items.length+' слов. Без ограничения повторов.';count();document.querySelector('#offlineRoundSize').onchange=()=>prepareGame().then(startGame);document.querySelector('#offlineBankFile').onchange=async(event)=>{try{let data=JSON.parse(await event.target.files[0].text());if(Array.isArray(data))data={title:'Мой набор',items:data};if(!Array.isArray(data.items)||!data.items.length||data.items.some(item=>!item.variant||!(item.answer||item.correct_letter)))throw Error('В наборе нужны задания с полями variant и answer.');data.items=data.items.map(item=>({...item,answer:item.answer||item.correct_letter}));window.__OFFLINE_FLUFFS_BANK=data;count();await prepareGame();startGame();document.querySelector('#offlineBankError').textContent='Набор открыт.'}catch(error){document.querySelector('#offlineBankError').textContent=error.message}}})();</script>'''
            source=source.replace('</body>',initializer+'</body>')
        # An unobtrusive local catalogue link also works in games without navigation.
        source=source.replace('</body>','<a href="../Открыть игры.html" style="position:fixed;bottom:8px;left:8px;z-index:2147483000;background:#fffef4;color:#24364d;border:1px solid #bdc8d4;border-radius:8px;padding:5px 9px;font:12px Arial;text-decoration:none">← Все офлайн-игры</a><script>window.__OFFLINE_READY=true;</script></body>')
        path=self.output/'Игра.html';path.write_text(source,encoding='utf-8')
        if self.theory or any(self.text_theory):
            theory_dir=self.output/'Памятки теории';theory_dir.mkdir(exist_ok=True)
            figures=''.join('<figure><figcaption>'+html.escape(t['title'])+'</figcaption><a href="'+quote(Path(t['file']).name)+'"><img loading="lazy" src="'+quote(Path(t['file']).name)+'" alt="'+html.escape(t['title'])+'"></a></figure>' for t in self.theory)
            (theory_dir/'Памятки.html').write_text(book_document(self.title+' — теория',''.join(self.text_theory)+figures),encoding='utf-8')
        return {'slug':self.slug,'title':self.title,'folder':self.output.name,'html':path.relative_to(OUT).as_posix(),'html_bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'theory_files':len(self.theory),'theory':self.theory,'has_theory':(self.output/'Памятки теории').exists(),'embedded_files':self.embedded_count,'sources':self.source_files,'warnings':self.warnings}


def main():
    OUT.mkdir(exist_ok=True);QA.mkdir(exist_ok=True)
    selected=set(sys.argv[1:])
    previous=json.loads((QA/'manifest.json').read_text(encoding='utf-8')) if selected and (QA/'manifest.json').exists() else []
    by_slug={entry['slug']:entry for entry in previous}
    seen=set();unique=[]
    for slug,folder in {**server.HTML_GAMES,**server.PUBLIC_GAMES}.items():
        if folder in seen:continue
        seen.add(folder)
        unique.append((slug,folder))
    if selected-set(slug for slug,_ in unique):raise ValueError('Unknown game selection')
    for index,(slug,folder) in enumerate(unique,1):
        if selected and slug not in selected:continue
        title=server.HTML_GAME_TITLES.get(slug,'Пушинки — свои наборы')
        target=OUT/f'{index:02d} {safe_name(title)}'
        built=GameBuilder(slug,folder,target).build();by_slug[slug]=built
        print(slug,round(built['html_bytes']/1048576,1),'MiB','handouts',built['theory_files'],'warnings',len(built['warnings']),flush=True)
    results=[by_slug[slug] for slug,_ in unique if slug in by_slug]
    (QA/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    cards=''.join(f'<section><h2>{i}. {html.escape(r["title"])}</h2><a href="{quote(r["html"])}">Открыть полную игру →</a>'+ (f' · <a href="{quote(r["folder"]+"/Памятки теории/Памятки.html")}">Памятки с теорией</a>' if r['has_theory'] else '')+'</section>' for i,r in enumerate(results,1))
    catalogue=book_document('HTML-игры — полные офлайн-версии','<p>Открывайте игры двойным щелчком. Интернет, сервер и вход в аккаунт не требуются. Внутри каждой папки — «Игра.html» и памятки с теорией, если они предусмотрены в игре.</p>'+cards).replace('<nav><a href="../Игра.html">← К игре</a></nav>','')
    (OUT/'Открыть игры.html').write_text(catalogue,encoding='utf-8')
    print('Built',len(results),'games',OUT)


if __name__=='__main__':main()
