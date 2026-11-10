"""Teacher-owned games assigned to named pupils, with checked access per request."""
import secrets
from contextlib import closing
from urllib.parse import urlparse, urlencode
import learning_module as learning


class GameAssignmentError(PermissionError):
    code='game_assignment_unavailable'


def ensure_schema(con):
    con.executescript('''
      CREATE TABLE IF NOT EXISTS assigned_games (
        id TEXT PRIMARY KEY, teacher_id TEXT NOT NULL, slug TEXT NOT NULL, product_slug TEXT,
        public_id TEXT, title TEXT NOT NULL, kind TEXT NOT NULL, target_count INTEGER NOT NULL,
        created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS assigned_game_students (
        game_id TEXT NOT NULL, student_id TEXT NOT NULL, seen_at TEXT, started_at TEXT,
        completed_at TEXT, revoked_at TEXT, due_at TEXT, PRIMARY KEY(game_id,student_id));
      CREATE TABLE IF NOT EXISTS assigned_game_answers (
        game_id TEXT NOT NULL, student_id TEXT NOT NULL, event_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
        PRIMARY KEY(student_id,event_id));
      CREATE INDEX IF NOT EXISTS idx_assigned_game_teacher ON assigned_games(teacher_id);
      CREATE INDEX IF NOT EXISTS idx_assigned_game_student ON assigned_game_students(student_id);
    ''')


def local_slug(s,game):
    path=urlparse(game.get('online_url') or game.get('url') or '').path.strip('/').split('/')
    slug = s.PROTECTED_FULL_GAME_ROUTES.get(path[0]) if path else None
    if not slug and len(path)>1 and path[0]=='full-games':
        slug=path[1]
    return slug if slug in s.HTML_GAMES else None


def create(s,user,payload):
    s.require_teacher(user)
    public_id=str(payload.get('public_id') or '')
    product_slug=str(payload.get('slug') or '')
    due=learning.parse_due(payload.get('due_at'))
    try: target=int(payload.get('target_count',0))
    except (ValueError,TypeError): raise ValueError('Укажите количество ответов от 0 до 500.') from None
    if not 0<=target<=500: raise ValueError('Укажите количество ответов от 0 до 500.')
    cabinet=s.teacher_games(user)
    if public_id:
        game=next((g for g in cabinet['created'] if g['public_id']==public_id and g['is_active']),None)
        if not game: raise PermissionError('Можно назначить только свою активную игру.')
        slug=game['mechanic'];kind='created';product_slug=None
        if slug not in s.PUBLIC_GAMES and slug not in s.HTML_GAMES:
            raise ValueError('Онлайн-игра недоступна.')
    else:
        game=next((g for g in cabinet['purchased'] if g['slug']==product_slug),None)
        slug=local_slug(s,game) if game else None
        if not game or not slug or not s.user_can_access_full_game(user,product_slug):
            raise PermissionError('Для назначения нужна полная онлайн-версия игры в вашем кабинете.')
        kind='full'
    with learning.connection(s) as con:
        ids=list(payload.get('student_ids') or [])
        if payload.get('all_students'):
            ids += [r[0] for r in con.execute("SELECT user_id FROM users WHERE teacher_id=? AND role='student'",(user['user_id'],))]
        for group_id in payload.get('group_ids') or []:
            if not con.execute('SELECT 1 FROM student_groups WHERE id=? AND teacher_id=?',(str(group_id),user['user_id'])).fetchone():
                raise PermissionError('Можно выбирать только свои группы.')
            ids += [r[0] for r in con.execute('SELECT student_id FROM student_group_members WHERE group_id=?',(str(group_id),))]
        ids=learning.own_students(s,con,user,ids)
        game_id=secrets.token_hex(12)
        con.execute('INSERT INTO assigned_games VALUES(?,?,?,?,?,?,?,?,?)',
            (game_id,user['user_id'],slug,product_slug,public_id,game['title'],kind,target,s.now_iso()))
        con.executemany('INSERT INTO assigned_game_students(game_id,student_id,due_at) VALUES(?,?,?)',[(game_id,i,due) for i in ids])
    return {'id':game_id,'recipients':len(ids)}


def check_access(s,con,user,game_id):
    game=con.execute('SELECT * FROM assigned_games WHERE id=?',(game_id,)).fetchone()
    if not game: raise GameAssignmentError('Назначенная игра не найдена.')
    game=dict(game)
    teacher=con.execute("SELECT * FROM users WHERE user_id=? AND role='teacher'",(game['teacher_id'],)).fetchone()
    if not teacher: raise GameAssignmentError('Назначение игры недоступно.')
    if user['role']=='teacher' and user['user_id']==game['teacher_id']:
        pass
    elif user['role']=='student':
        pupil=con.execute('''SELECT a.* FROM assigned_game_students a JOIN users u ON u.user_id=a.student_id
            WHERE a.game_id=? AND a.student_id=? AND u.teacher_id=? AND u.role='student' ''',
                          (game_id,user['user_id'],game['teacher_id'])).fetchone()
        if not pupil or pupil['revoked_at']: raise GameAssignmentError('Игра не назначена вам или доступ отозван.')
    else: raise GameAssignmentError('Эта игра назначена другому ученику.')
    if game['kind']=='full':
        if not s.user_can_access_full_game(dict(teacher),game['product_slug']):
            raise GameAssignmentError('У учителя больше нет доступа к полной версии игры.')
    else:
        active=con.execute('''SELECT 1 FROM game_sets WHERE public_id=? AND teacher_id=? AND mechanic=?
            AND is_active=1 AND is_deleted=0''',(game['public_id'],game['teacher_id'],game['slug'])).fetchone()
        if not active: raise GameAssignmentError('Учитель отключил эту игру.')
    return game


def open_game(s,user,payload):
    game_id=str(payload.get('game_id') or '')
    with learning.connection(s) as con:
        game=check_access(s,con,user,game_id)
        if user['role']=='student':
            con.execute('''UPDATE assigned_game_students SET seen_at=COALESCE(seen_at,?),
                started_at=COALESCE(started_at,?) WHERE game_id=? AND student_id=?''',
                (s.now_iso(),s.now_iso(),game_id,user['user_id']))
    query={'assignment_id':game_id}
    if game['public_id']:query['set']=game['public_id']
    return {'url':'/assigned-games/'+game_id+'/index.html?'+urlencode(query)}


def overview(s,user,student_id=''):
    with closing(s.db()) as con:
        if user['role']=='teacher':
            where,args='g.teacher_id=?',[user['user_id']]
            if student_id:
                learning.own_students(s,con,user,[student_id]);where+=' AND a.student_id=?';args.append(student_id)
        elif user['role']=='student':
            if student_id and student_id!=user['user_id']:raise PermissionError('Доступна только ваша статистика.')
            where,args="a.student_id=? AND u.teacher_id=g.teacher_id",[user['user_id']]
        else:raise PermissionError('Назначенные игры доступны учителю и ученику.')
        rows=[dict(r) for r in con.execute(f'''SELECT g.*,a.student_id,u.display_name,a.seen_at,a.started_at,
            a.completed_at,a.revoked_at,a.due_at,
            (SELECT COUNT(*) FROM assigned_game_answers x WHERE x.game_id=g.id AND x.student_id=a.student_id) checked,
            (SELECT COALESCE(SUM(t.is_correct),0) FROM assigned_game_answers x JOIN attempts t ON t.attempt_id=x.attempt_id
                WHERE x.game_id=g.id AND x.student_id=a.student_id) correct
            FROM assigned_games g JOIN assigned_game_students a ON a.game_id=g.id
            JOIN users u ON u.user_id=a.student_id WHERE {where} ORDER BY g.created_at DESC''',args)]
        for row in rows:
            row['assignment_kind']='game';row['total']=row['target_count']
            row['outline']=[{'title':'Игра','count':row['target_count']}]
            learning.deadline_status(row)
        return rows


def update(s,user,payload):
    s.require_teacher(user)
    game_id=str(payload.get('game_id') or '')
    with learning.connection(s) as con:
        if not con.execute('SELECT 1 FROM assigned_games WHERE id=? AND teacher_id=?',(game_id,user['user_id'])).fetchone():
            raise PermissionError('Это назначение другого учителя.')
        where,args='game_id=?',[game_id]
        if payload.get('student_id'):
            where+=' AND student_id=?';args.append(str(payload['student_id']))
        if not con.execute('SELECT 1 FROM assigned_game_students WHERE '+where,args).fetchone():raise PermissionError('Назначение не найдено.')
        if payload.get('revoke') is True:
            con.execute('UPDATE assigned_game_students SET revoked_at=COALESCE(revoked_at,?) WHERE '+where,[s.now_iso(),*args])
        elif 'due_at' in payload:
            con.execute('UPDATE assigned_game_students SET due_at=? WHERE '+where,[learning.parse_due(payload['due_at']),*args])
        else:raise ValueError('Укажите срок или отзыв игры.')
    return {'ok':True}


def record_answer(s,con,user,game,payload,attempt_id):
    con.execute('INSERT INTO assigned_game_answers VALUES(?,?,?,?)',
                (game['id'],user['user_id'],payload['event_id'],attempt_id))
    count=con.execute('SELECT COUNT(*) FROM assigned_game_answers WHERE game_id=? AND student_id=?',
                     (game['id'],user['user_id'])).fetchone()[0]
    con.execute('''UPDATE assigned_game_students SET seen_at=COALESCE(seen_at,?),started_at=COALESCE(started_at,?),
        completed_at=CASE WHEN ?>0 AND ?>=? THEN COALESCE(completed_at,?) ELSE completed_at END
        WHERE game_id=? AND student_id=?''',(s.now_iso(),s.now_iso(),game['target_count'],count,
        game['target_count'],s.now_iso(),game['id'],user['user_id']))
