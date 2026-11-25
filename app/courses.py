"""Paid course content, cohorts, schedules and private learner correspondence."""
import html
import json
import re
import secrets
import base64
import hashlib
import threading
import colorsys
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SLUG = 'neurovisual'
PRODUCT = 'course-neurovisual'
TITLE = 'Нейровизуал в работе учителя: от сотни попыток к предсказуемому результату'
SOURCE = Path(__file__).parent / 'Нейровизуал для учителя'
CONTACT = 'https://max.ru/u/f9LHodD0cOIeh46SDnpskQ5L0kGGxZgbDCU90obzbA4ArSzdFnpt-8Tq5pk'
CONSULTATION = 'Мы связываемся в мессенджере заранее, вы обозначаете проблемы, которые необходимо решить, я подбираю оптимальное решение. Мы связываемся для консультации: я показываю инструменты и помогаю с решением проблем.'
FILES = ['1_neurogzhel(2).html', '2_vizual_v_rabote_uchitelya_7.html', '3_referensy_final.html', '4_razvivaem_stil(1).html', '5_marshrut_uchastnika(1).html', '6_marshrut_final.html', '7_marshrut_final.html']
EXTRAS = ['kak_podklyuchit_chatgpt.html', 'Словарик — кнопки и настройки генерации.html', 'vizual_prompty_teacher_extended.html', 'Цветовой компас.html', 'Эксперименты — 8 задач визуала.html']
EXTRA_LABELS = ['Как подключить ChatGPT', 'Словарик: кнопки и настройки', 'Промпты для учителя', 'Цветовой компас', 'Эксперименты: 8 задач визуала']
BRANCHES = [[0, 1], [2, 4], [2], [3, 4], [3], [2, 3], [4]]
MEDIA = ['Урок 1. Инструменты.mp4']
INFOGRAPHICS = {
 'infographic-bratuha-overview.png': 'Братуха.ру: возможности',
 'infographic-chatgpt.png': 'Прямой доступ к ChatGPT',
 'infographic-bratuha.png': 'Братуха.ру: плюсы и минусы',
 'infographic-chataibot.png': 'ChatAIbot: плюсы и минусы',
 'infographic-syntx.png': 'Syntx.ai: обзор возможностей',
}
CACHE_LOCK = threading.Lock()


@contextmanager
def connection(s):
    with closing(s.db()) as con:
        with con:
            yield con


CHECKS = [
 ['Определена педагогическая задача', 'Выбраны инструменты и способ доступа', 'Выполнена пробная генерация'],
 ['Сформулировано учебное действие', 'Сравнены две версии промпта', 'Спланирован комплект из 3–5 материалов'],
 ['Выбран и разобран референс', 'Сохранена стилевая прибавка', 'Создан новый визуал по референсу'],
 ['Один сюжет проверен в разных стилях', 'Сохранены палитра и признаки героя', 'Выбран рабочий промпт'],
 ['Сравнены пять стилей', 'Зафиксированы палитра и правила серии', 'Промпты проверены на новых материалах'],
 ['Выбрано учебное действие', 'Проверены факты и формулировки', 'Материал готов к использованию'],
 ['Подготовлены 2–3 согласованных элемента', 'Элементы проверены в выбранной среде', 'Сохранены промпты и спецификации']]
HOMEWORKS = [
 'Составьте свой стартовый набор: опишите 2–3 педагогические задачи, выберите инструменты, способ доступа и бюджет. Выполните одну пробную генерацию. Отправьте список выбранных инструментов, результат пробы и план следующего шага.',
 'Выберите конкретное учебное действие и создайте для него две версии иллюстрации: по исходному и уточнённому промпту. Составьте план комплекта из 3–5 материалов и укажите, как ученики будут использовать каждый из них. Отправьте изображения, оба промпта и план комплекта.',
 'Создайте новый учебный визуал по выбранному референсу. Отправьте референс, результат, текстовую стилевую прибавку или промпт и короткое сравнение: что сохранили и что изменили. Если использовали готовый мудборд, приложите его название, ссылку или код.',
 'Проверьте один сюжет минимум в трёх стилях, выберите подходящий и измените в нём один элемент, сохранив палитру и признаки героя. Отправьте варианты, выбранный промпт и объяснение, где примените результат в своём учебном комплекте.',
 'Сравните пять стилей на мокапах и выберите один для своей серии. Составьте паспорт визуальной концепции: назначение, палитра, правила стиля, референсы и промпты. Проверьте концепцию на двух разных материалах и отправьте паспорт вместе с результатами проверки.',
 'Создайте один готовый учебный материал на выбор: рабочий лист, памятку, набор стикеров или плакат. Свяжите его с конкретным учебным действием, проверьте факты, формулировки и читаемость. Отправьте материал, промпты и короткое описание проверки.',
 'Подготовьте мини-комплект из 2–3 согласованных изображений для урока-истории, слайдов, интерактивной доски или игры. Проверьте их в выбранной среде. Отправьте комплект, промпты и результат проверки. При технических ограничениях подготовьте один готовый элемент и подробные спецификации остальных.'
]


def seed(con, s):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS course_settings(id TEXT PRIMARY KEY, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS course_lessons(id INTEGER PRIMARY KEY, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS course_groups(id TEXT PRIMARY KEY, title TEXT NOT NULL, schedule TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS course_members(user_id TEXT PRIMARY KEY, group_id TEXT, joined_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS course_order_groups(order_uid TEXT PRIMARY KEY, group_id TEXT, assigned_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS course_progress(user_id TEXT NOT NULL, lesson_id INTEGER NOT NULL,
      data TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(user_id,lesson_id));
    CREATE TABLE IF NOT EXISTS course_homework(user_id TEXT NOT NULL, lesson_id INTEGER NOT NULL,
      completed INTEGER NOT NULL DEFAULT 0, reviewed_at TEXT NOT NULL, reviewed_by TEXT NOT NULL,
      PRIMARY KEY(user_id,lesson_id));
    CREATE TABLE IF NOT EXISTS course_messages(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, lesson_id INTEGER NOT NULL,
      kind TEXT NOT NULL, body TEXT NOT NULL, reply TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, replied_at TEXT);
    ''')
    s.ensure_column(con,'course_groups','chat',"TEXT NOT NULL DEFAULT ''")
    con.execute('INSERT OR IGNORE INTO course_settings VALUES (?,?)', (SLUG, json.dumps({'chat':'https://max.ru/join/ysqNLQk5FQ8I9u_oOYX5Mztol5spN7r8dJASZhBFi_g','links':[], 'intro':'Добро пожаловать! Пройдите семь шагов от выбора инструмента до собственного комплекта учебного визуала.'}, ensure_ascii=False)))
    settings=json.loads(con.execute('SELECT data FROM course_settings WHERE id=?',(SLUG,)).fetchone()[0])
    if 'default_group' not in settings:
        settings['default_group']=''
        con.execute('UPDATE course_settings SET data=? WHERE id=?',(json.dumps(settings,ensure_ascii=False),SLUG))
        # Historical paid orders keep their existing group; the new default is prospective.
        for order in con.execute('''SELECT DISTINCT o.order_uid,o.buyer_email FROM shop_orders o
          LEFT JOIN shop_order_items i ON i.order_uid=o.order_uid
          WHERE o.status='paid' AND (o.product_id=? OR i.product_id=?)''',(PRODUCT,PRODUCT)).fetchall():
            member=con.execute('''SELECT m.group_id FROM course_members m JOIN users u ON u.user_id=m.user_id
              WHERE lower(COALESCE(NULLIF(u.email,''),u.username))=lower(?) LIMIT 1''',(order['buyer_email'],)).fetchone()
            con.execute('INSERT OR IGNORE INTO course_order_groups VALUES (?,?,?)',(order['order_uid'],member['group_id'] if member else None,s.now_iso()))
    text = (SOURCE / 'karta_kursa_vizual.html').read_text('utf-8')
    outline = json.loads(re.search(r'const lessons = (\[.*?\]);', text, re.S)[1])
    source_homework=json.loads((Path(__file__).parent/'course_homework_source.json').read_text('utf-8'))
    for i, row in enumerate(outline, 1):
        data = dict(title=row[0], summary=row[1], outcome=row[2], homework=HOMEWORKS[i-1], checklist=CHECKS[i-1], intro='', chat='', links=[], videos=[], opens_at='' if i==1 else 'manual', texts={})
        con.execute('INSERT OR IGNORE INTO course_lessons VALUES (?,?)', (i,json.dumps(data, ensure_ascii=False)))
    for row in con.execute('SELECT id,data FROM course_lessons').fetchall():
        saved=json.loads(row['data'])
        if str(row['id']) in source_homework and saved['homework']==HOMEWORKS[row['id']-1]:
            saved['homework']=source_homework[str(row['id'])]
            con.execute('UPDATE course_lessons SET data=? WHERE id=?',(json.dumps(saved,ensure_ascii=False),row['id']))
        video_limit=2 if row['id']==1 else 1
        if len(saved.get('videos',[]))>video_limit:
            saved['videos']=saved['videos'][:video_limit]
            con.execute('UPDATE course_lessons SET data=? WHERE id=?',(json.dumps(saved,ensure_ascii=False),row['id']))
    base = s.APP_BASE_URL.rstrip('/')
    for pid, slug, title, amount, url, desc in [
        (PRODUCT, SLUG, TITLE, '5000.00', base+'/courses/neurovisual', 'Семь практических занятий, дополнительные маршруты, домашние задания и обратная связь.'),
        ('personal-consultation', 'personal-consultation', 'Личная консультация', '2000.00', CONTACT, CONSULTATION)]:
        con.execute('''INSERT OR IGNORE INTO paid_entities(product_id,slug,title,type,amount,currency,delivery_url,online_url,description_json,is_active,created_at,updated_at)
          VALUES (?,?,?,'product',?,'RUB',?,?,?,1,?,?)''', (pid,slug,title,amount,url,url,json.dumps({'kindLabel':'Практический курс' if pid==PRODUCT else 'Личная консультация','shortDescription':desc,'fullDescription':desc,'format':'Обучение' if pid==PRODUCT else 'Личная консультация','delivery':'Доступ на платформе по почте покупки.' if pid==PRODUCT else 'Для согласования встречи напишите в MAX или на anastasia@dimitrieva-av.ru.'},ensure_ascii=False),s.now_iso(),s.now_iso()))
    catalog=json.loads((Path(__file__).parent/'course_catalog.json').read_text('utf-8'))
    catalog.pop('source',None)
    product=con.execute('SELECT cover_url,description_json FROM paid_entities WHERE product_id=?',(PRODUCT,)).fetchone()
    description=json.loads(product['description_json'] or '{}')
    if description.get('shortDescription','').startswith('Семь практических занятий, дополнительные маршруты'):
        con.execute('UPDATE paid_entities SET description_json=? WHERE product_id=?',(json.dumps(catalog,ensure_ascii=False),PRODUCT))
        description=dict(catalog)
    changed=False
    for key in ('refund','registration'):
        if key not in description:
            description[key]=catalog[key]
            changed=True
    if changed:
        con.execute('UPDATE paid_entities SET description_json=? WHERE product_id=?',(json.dumps(description,ensure_ascii=False),PRODUCT))
    if not product['cover_url'] or product['cover_url']=='/logo.jpg':
        con.execute('UPDATE paid_entities SET cover_url=? WHERE product_id=?',('/assets/course/neurovisual-cover.png',PRODUCT))


def paid(con, user):
    email = str(user.get('email') or user.get('username') or '').strip().lower()
    return user.get('role') == 'admin' or bool(con.execute('''SELECT 1 FROM shop_orders o LEFT JOIN shop_order_items i ON i.order_uid=o.order_uid
      WHERE o.status='paid' AND lower(o.buyer_email)=? AND (o.product_id=? OR i.product_id=?) LIMIT 1''',(email,PRODUCT,PRODUCT)).fetchone())


def enroll(con, user, s):
    if not paid(con,user):
        raise PermissionError('Курс доступен после оплаты. Войдите с почтой, указанной при покупке.')
    if user.get('role') != 'admin':
        email=str(user.get('email') or user.get('username') or '').strip().lower()
        orders=con.execute('''SELECT DISTINCT o.order_uid FROM shop_orders o LEFT JOIN shop_order_items i ON i.order_uid=o.order_uid
          WHERE o.status='paid' AND lower(o.buyer_email)=? AND (o.product_id=? OR i.product_id=?)
          ORDER BY o.paid_at,o.created_at''',(email,PRODUCT,PRODUCT)).fetchall()
        for order in orders: record_paid_order(con,order['order_uid'],s)


def record_paid_order(con,order_uid,s):
    """Snapshot the intake group on confirmed payment, before account creation if needed."""
    order=con.execute('''SELECT DISTINCT o.* FROM shop_orders o LEFT JOIN shop_order_items i ON i.order_uid=o.order_uid
      WHERE o.order_uid=? AND o.status='paid' AND (o.product_id=? OR i.product_id=?)''',(order_uid,PRODUCT,PRODUCT)).fetchone()
    if not order:return
    settings=json.loads(con.execute('SELECT data FROM course_settings WHERE id=?',(SLUG,)).fetchone()[0])
    gid=settings.get('default_group') or None
    con.execute('INSERT OR IGNORE INTO course_order_groups VALUES (?,?,?)',(order_uid,gid,s.now_iso()))
    assigned=con.execute('SELECT group_id FROM course_order_groups WHERE order_uid=?',(order_uid,)).fetchone()['group_id']
    for user in con.execute('''SELECT user_id FROM users WHERE role<>'admin'
      AND lower(COALESCE(NULLIF(email,''),username))=lower(?)''',(order['buyer_email'],)).fetchall():
        con.execute('INSERT OR IGNORE INTO course_members VALUES (?,?,?)',(user['user_id'],assigned,s.now_iso()))


def lessons(con):
    return [dict(id=r['id'], **json.loads(r['data'])) for r in con.execute('SELECT * FROM course_lessons ORDER BY id')]


def available(con, user, lesson):
    if user.get('role') == 'admin':
        return True
    member = con.execute('SELECT g.schedule FROM course_members m LEFT JOIN course_groups g ON m.group_id=g.id WHERE m.user_id=?',(user['user_id'],)).fetchone()
    overrides = json.loads(member['schedule']) if member and member['schedule'] else {}
    opens = overrides.get(str(lesson['id']), lesson['opens_at'])
    lesson['effective_opens_at']=opens
    return opens != 'manual' and (not opens or datetime.fromisoformat(opens) <= datetime.now(timezone.utc))


def overview(s, user, admin=False):
    with connection(s) as con:
        if admin:
            s.require_admin(user)
            # Enroll registered buyers even if they have not yet visited the course.
            for row in con.execute('SELECT * FROM users').fetchall():
                if row['role'] != 'admin' and paid(con,dict(row)):
                    enroll(con,dict(row),s)
        else:
            enroll(con,user,s)
        items=lessons(con)
        for lesson in items:
            lesson['available']=available(con,user,lesson)
            if not admin:
                for key in ('texts','videos','links','homework','checklist','intro','chat'):
                    if not lesson['available'] or key == 'texts': lesson.pop(key,None)
        settings=json.loads(con.execute('SELECT data FROM course_settings WHERE id=?',(SLUG,)).fetchone()[0])
        group=None
        if not admin:
            row=con.execute('''SELECT g.id,g.title,g.chat FROM course_members m JOIN course_groups g ON g.id=m.group_id
              WHERE m.user_id=?''',(user['user_id'],)).fetchone()
            if row:group=dict(row)
            if group and group['chat']:settings['chat']=group['chat']
            settings.pop('default_group',None)
        result=dict(title=TITLE,settings=settings,lessons=items,extras=[dict(id=i,title=t) for i,t in enumerate(EXTRA_LABELS)],branches=BRANCHES)
        result['group']=group
        homework=[dict(r) for r in con.execute('SELECT * FROM course_homework'+('' if admin else ' WHERE user_id=?'),() if admin else (user['user_id'],))]
        result['homework']=homework
        done=sum(bool(r['completed']) for r in homework if r['user_id']==user['user_id'])
        result['homework_progress']={'completed':done,'total':len(items),'percent':round(done/len(items)*100)}
        result['progress']=[dict(r, data=json.loads(r['data'])) for r in con.execute('SELECT * FROM course_progress'+('' if admin else ' WHERE user_id=?'), () if admin else (user['user_id'],))]
        result['messages']=[dict(r) for r in con.execute('SELECT * FROM course_messages'+('' if admin else ' WHERE user_id=?')+' ORDER BY created_at', () if admin else (user['user_id'],))]
        if admin:
            result['groups']=[dict(r,schedule=json.loads(r['schedule'])) for r in con.execute('SELECT * FROM course_groups')]
            result['members']=[dict(r) for r in con.execute('SELECT m.*,u.display_name,u.email,u.username FROM course_members m JOIN users u ON u.user_id=m.user_id')]
            product=con.execute('SELECT * FROM paid_entities WHERE product_id=?',(PRODUCT,)).fetchone()
            result['product']=dict(product,description=json.loads(product['description_json'] or '{}'))
        return result


def clean_url(value):
    value=str(value or '').strip()
    if value and (urlparse(value).scheme != 'https' or not urlparse(value).hostname):
        raise ValueError('Ссылки должны начинаться с https://')
    return value


def video_url(value):
    if '<iframe' in str(value).lower():
        match=re.search(r'\bsrc\s*=\s*[\"\x27]([^\"\x27]+)',str(value),re.I)
        if not match: raise ValueError('В коде встраивания нет адреса видео.')
        value=html.unescape(match[1])
    value=clean_url(value)
    p=urlparse(value)
    if p.hostname not in {'vk.com','www.vk.com','vkvideo.ru','www.vkvideo.ru','vk.ru','www.vk.ru'}:
        raise ValueError('Нужна ссылка на видео ВКонтакте.')
    if p.path == '/video_ext.php':
        q=parse_qs(p.query)
        if not re.fullmatch(r'-?\d+',q.get('oid',[''])[0]) or not re.fullmatch(r'\d+',q.get('id',[''])[0]):
            raise ValueError('Некорректная ссылка встраивания VK.')
        return value
    match=re.fullmatch(r'/video(-?\d+)_(\d+)',p.path)
    if not match:
        raise ValueError('Вставьте код встраивания VK или полный адрес video_ext.php из этого кода.')
    raise ValueError('Это ссылка для просмотра видео. Автоматически получить из неё надёжный адрес встраивания нельзя. Откройте видео в VK, выберите «Поделиться» → код для вставки и вставьте сюда весь iframe-код либо его полный src. Исходная ссылка не будет обрезана или сохранена вместо прежнего видео.')


def date(value):
    if value == 'manual': return 'manual'
    if not value: return ''
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if parsed.tzinfo is None: raise ValueError()
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError,TypeError):
        raise ValueError('Укажите дату открытия с часовым поясом.') from None


def action(s,user,p):
    kind=p.get('action')
    if kind=='catalog':
        s.require_admin(user)
        with connection(s) as con:
            row=dict(con.execute('SELECT * FROM paid_entities WHERE product_id=?',(PRODUCT,)).fetchone())
        update=p.get('data',{})
        payload={**row,**{key:update[key] for key in ('title','amount','sale_amount','sale_ends_at') if key in update}}
        result=s.update_paid_entity(user,payload)
        if any(key in update for key in ('shortDescription','fullDescription','refund','registration')):
            description=json.loads(row.get('description_json') or '{}')
            description.update(json.loads(s.safe_description_json({key:update[key] for key in ('shortDescription','fullDescription','refund','registration') if key in update})))
            with connection(s) as con: con.execute('UPDATE paid_entities SET description_json=? WHERE product_id=?',(json.dumps(description,ensure_ascii=False),PRODUCT))
        return result
    with connection(s) as con:
        if kind in {'settings','lesson','group','member','reply','homework'}:
            s.require_admin(user)
            if kind in {'settings','lesson'}:
                table='course_settings' if kind=='settings' else 'course_lessons'
                ident=SLUG if kind=='settings' else int(p['id'])
                row=con.execute(f'SELECT data FROM {table} WHERE id=?',(ident,)).fetchone()
                if not row: raise ValueError('Урок не найден.')
                data=json.loads(row[0]); update=p['data']
                for key in data:
                    if key in update: data[key]=update[key]
                data['chat']=clean_url(data.get('chat'))
                if kind=='settings':
                    gid=data.get('default_group') or ''
                    if gid and not con.execute('SELECT 1 FROM course_groups WHERE id=?',(gid,)).fetchone():
                        raise ValueError('Группа для новых оплат не найдена.')
                if not isinstance(data['links'],list) or len(data['links'])>50: raise ValueError('Слишком много ссылок.')
                data['links']=[dict(title=str(x['title'])[:200],url=clean_url(x['url'])) for x in data['links']]
                if kind=='lesson':
                    data['opens_at']=date(data['opens_at'])
                    video_limit=2 if ident==1 else 1
                    if not isinstance(data['videos'],list) or len(data['videos'])>video_limit:
                        raise ValueError('В первом уроке можно указать два видео, в остальных — одно.')
                    data['videos']=[video_url(v) if v else '' for v in data['videos']]
                    while data['videos'] and not data['videos'][-1]: data['videos'].pop()
                    if not data['title'].strip() or not data['homework'].strip() or not any(str(x).strip() for x in data['checklist']):
                        raise ValueError('Нужны название, домашнее задание и чек-лист.')
                con.execute(f'UPDATE {table} SET data=? WHERE id=?',(json.dumps(data,ensure_ascii=False),ident))
            elif kind=='group':
                gid=p.get('id') or secrets.token_hex(8)
                title=str(p.get('title','')).strip()[:200]
                if not title: raise ValueError('Укажите название группы.')
                schedule={str(int(k)):date(v) for k,v in p.get('schedule',{}).items()}
                if any(int(k) not in range(1,8) for k in schedule): raise ValueError('Неизвестный урок.')
                existing=con.execute('SELECT chat FROM course_groups WHERE id=?',(gid,)).fetchone()
                chat=clean_url(p.get('chat',existing['chat'] if existing else ''))
                con.execute('INSERT INTO course_groups(id,title,schedule,chat) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,schedule=excluded.schedule,chat=excluded.chat',(gid,title,json.dumps(schedule),chat))
            elif kind=='member':
                gid=p.get('group_id') or None
                if gid and not con.execute('SELECT 1 FROM course_groups WHERE id=?',(gid,)).fetchone(): raise ValueError('Группа не найдена.')
                con.execute('UPDATE course_members SET group_id=? WHERE user_id=?',(gid,p['user_id']))
            elif kind=='homework':
                lid=int(p.get('lesson_id',0))
                uid=str(p.get('user_id',''))
                if lid not in range(1,8):raise ValueError('Урок не найден.')
                if not isinstance(p.get('completed'),bool):raise ValueError('Укажите отметку выполнения задания.')
                if not con.execute('SELECT 1 FROM course_members WHERE user_id=?',(uid,)).fetchone():raise ValueError('Участник курса не найден.')
                con.execute('''INSERT INTO course_homework VALUES (?,?,?,?,?) ON CONFLICT(user_id,lesson_id) DO UPDATE SET
                  completed=excluded.completed,reviewed_at=excluded.reviewed_at,reviewed_by=excluded.reviewed_by''',
                  (uid,lid,int(p['completed']),s.now_iso(),user['user_id']))
            else:
                con.execute('UPDATE course_messages SET reply=?,replied_at=? WHERE id=?',(str(p.get('reply',''))[:20000],s.now_iso(),p['id']))
        else:
            enroll(con,user,s)
            lid=int(p.get('lesson_id',0))
            if lid:
                lesson=next((x for x in lessons(con) if x['id']==lid),None)
                if not lesson or not available(con,user,lesson): raise PermissionError('Урок ещё не открыт.')
            if kind=='progress':
                data=p.get('data',{})
                if not isinstance(data,dict) or len(json.dumps(data))>300000: raise ValueError('Слишком большой ответ.')
                con.execute('INSERT INTO course_progress VALUES (?,?,?,?) ON CONFLICT(user_id,lesson_id) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at',(user['user_id'],lid,json.dumps(data,ensure_ascii=False),s.now_iso()))
            elif kind=='message':
                body=str(p.get('body','')).strip()
                if not body or len(body)>20000: raise ValueError('Введите сообщение до 20 000 символов.')
                message_kind=p.get('kind','question')
                if message_kind not in {'question','feedback','homework'}: raise ValueError('Неизвестный тип сообщения.')
                con.execute('INSERT INTO course_messages(id,user_id,lesson_id,kind,body,created_at) VALUES (?,?,?,?,?,?)',(secrets.token_hex(12),user['user_id'],lid,message_kind,body,s.now_iso()))
            else: raise ValueError('Неизвестное действие.')
    return {'ok':True}


def text_blocks(source, overrides=None):
    """Edit visible text without permitting script/markup injection."""
    blocks=[]; skip=0; counter=0
    parts=re.split(r'(<[^>]*>)',source)
    for index,part in enumerate(parts):
        if part.startswith('<'):
            if re.match(r'<(script|style)\b',part,re.I): skip+=1
            elif re.match(r'</(script|style)\b',part,re.I): skip=max(0,skip-1)
        elif not skip and len(html.unescape(part).strip())>=8:
            key=str(counter); counter+=1
            blocks.append({'id':key,'text':str(overrides[key]) if overrides and key in overrides else html.unescape(part).strip()})
            if overrides and key in overrides: parts[index]=html.escape(str(overrides[key]))
    return ''.join(parts),blocks


def content(s,user,resource,editor=False):
    with connection(s) as con:
        enroll(con,user,s)
        item=None
        if resource=='map': filename='karta_kursa_vizual.html'
        elif resource.startswith('extra-'):
            idx=int(resource[6:])
            if idx not in range(len(EXTRAS)): raise LookupError('Материал не найден.')
            filename=EXTRAS[idx]
        else:
            lid=int(resource)
            item=next((x for x in lessons(con) if x['id']==lid),None)
            if not item or not available(con,user,item): raise PermissionError('Урок ещё не открыт.')
            filename=FILES[lid-1]
        source=optimized_source(s,filename)
        source,blocks=text_blocks(source,item.get('texts') if item else {})
        if editor:
            s.require_admin(user)
            return blocks
        source=re.sub(r'(<style\b[^>]*>)(.*?)(</style>)',lambda m:m[1]+cool_interface_css(m[2])+m[3],source,flags=re.S|re.I)
        # All course-local links resolve through the access-controlled resource endpoint.
        for i,f in enumerate(FILES,1):
            source=source.replace(f, f'/courses/neurovisual?lesson={i}')
        if resource=='map':
            source=re.sub(r'const lessons = \[.*?\];',lambda m: 'const lessons = '+json.dumps([[x['title'],x['summary'],x['outcome'],f'/courses/neurovisual?lesson={x["id"]}'] for x in lessons(con)],ensure_ascii=False)+';',source,flags=re.S)
            completion={r['lesson_id']:bool(r['completed']) for r in con.execute('SELECT * FROM course_homework WHERE user_id=?',(user['user_id'],))}
            source=source.replace('const completed = lessons.map((_, index) => saved[index] === true);','const completed = '+json.dumps([completion.get(i,False) for i in range(1,8)])+';')
            source=source.replace('<style>','<style>.mark{display:none!important}')
            source=source.replace('"Пройдено " + count + " из "','"Домашние задания: " + count + " из "')
        for i,f in enumerate(EXTRAS):
            source=source.replace('href="'+f+'"',f'href="/api/courses/content?resource=extra-{i}"')
        source=source.replace('<head>', '<head><meta name="referrer" content="no-referrer">')
        return source


def cool_interface_css(css):
    """Cool the document UI surfaces; leave image pixels and generated palettes intact."""
    def replace(match):
        raw=match[0][1:]
        if len(raw) in (3,4):raw=''.join(c*2 for c in raw)
        red,green,blue=(int(raw[i:i+2],16)/255 for i in (0,2,4))
        hue,light,saturation=colorsys.rgb_to_hls(red,green,blue)
        degrees=hue*360
        if saturation>.025 and (15<=degrees<=85 or light>.85 and (degrees<15 or degrees>345)):
            rgb=colorsys.hls_to_rgb(218/360,light,min(saturation,.6))
            return '#'+''.join(f'{round(c*255):02x}' for c in rgb)+raw[6:]
        return match[0]
    return re.sub(r'#(?:[a-f0-9]{8}|[a-f0-9]{6}|[a-f0-9]{4}|[a-f0-9]{3})\b',replace,css,flags=re.I)


def cache_dir(s):
    path=Path(s.DB_PATH).parent/'course-assets'
    path.mkdir(parents=True,exist_ok=True)
    return path


def optimized_source(s,filename):
    """Keep large embedded illustrations out of editable HTML and browser srcdoc."""
    original=SOURCE/filename
    version=hashlib.sha256((filename+str(original.stat().st_mtime_ns)).encode()).hexdigest()
    folder=cache_dir(s)
    cached=folder/(version+'.html')
    with CACHE_LOCK:
        if cached.exists(): return cached.read_text('utf-8')
        source=original.read_text('utf-8')
        def extract(m):
            payload=base64.b64decode(m[2])
            ext={'jpeg':'jpg','svg+xml':'svg'}.get(m[1],m[1])
            if ext not in {'png','jpg','gif','webp','svg','avif'}: return m[0]
            name=hashlib.sha256(payload).hexdigest()+'.'+ext
            asset=folder/name
            if not asset.exists(): asset.write_bytes(payload)
            return '/api/courses/asset?id='+name
        source=re.sub(r'data:image/(png|jpeg|gif|webp|svg\+xml|avif);base64,([A-Za-z0-9+/=\r\n]+)',extract,source)
        cached.write_text(source,'utf-8')
        return source


def media_file(s,user,ident,video=False):
    with connection(s) as con:
        enroll(con,user,s)
        if video:
            lesson=lessons(con)[0]
            if not available(con,user,lesson): raise PermissionError('Первый урок ещё не открыт.')
            idx=int(ident)
            if idx not in range(len(MEDIA)): raise LookupError('Видео не найдено.')
            path=SOURCE/MEDIA[idx]
            if not path.is_file(): raise LookupError('Видео не найдено.')
            return path
    if ident in INFOGRAPHICS:
        path=Path(__file__).parent/'course-media'/ident
        if not path.is_file(): raise LookupError('Инфографика не найдена.')
        return path
    if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|gif|webp|svg|avif)',ident): raise LookupError('Файл не найден.')
    path=cache_dir(s)/ident
    if not path.is_file(): path=Path(__file__).parent/'course-media'/ident
    if not path.is_file(): raise LookupError('Файл не найден.')
    return path
