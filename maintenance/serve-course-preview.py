"""Local course preview using the real application and a separate database."""
import argparse
import json
import os
import secrets
import socket
import sys
import threading
import webbrowser
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
# These settings apply to this preview process only.
os.environ['APP_ENV'] = 'development'
os.environ['SEED_DEMO_USERS'] = '1'
os.environ['ADMIN_LOGIN'] = 'course-preview-admin'
os.environ['ADMIN_PASSWORD'] = secrets.token_urlsafe(24)
import server
import courses


def prepare(data_dir=None):
    directory = Path(data_dir).resolve() if data_dir else ROOT / 'data' / 'course-preview'
    if not directory.is_relative_to(ROOT):
        raise ValueError('The preview database must stay inside the project directory.')
    path = directory / 'ege_app.db'
    first_start=not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    for name in ['server', 'ege1_3_module', 'ege5_module', 'ege10_module', 'ege11_module',
                 'ege12_module', 'ege13_module', 'ege14_module', 'ege15_module', 'ege_speech_engine']:
        module = sys.modules.get(name)
        if module is not None:
            module.DB_PATH = path
    server.DATA_DIR = path.parent
    server.ensure_app_db()
    with closing(server.db()) as con, con:
        for row in con.execute("SELECT user_id FROM users WHERE username IN ('student','course-preview-admin')").fetchall():
            server.insert_user_consent(con, row['user_id'], '127.0.0.1', 'Course preview')
        if first_start:
            for row in con.execute('SELECT * FROM course_lessons').fetchall():
                data = json.loads(row['data'])
                data['opens_at'] = ''
                con.execute('UPDATE course_lessons SET data=? WHERE id=?', (json.dumps(data, ensure_ascii=False), row['id']))
        con.execute('''INSERT OR IGNORE INTO shop_orders
            (order_uid,product_id,product_title,amount,currency,buyer_email,status,created_at)
            VALUES ('local-course-preview',?,?,'5000.00','RUB','student','paid',?)''',
            (courses.PRODUCT, courses.TITLE, server.now_iso()))


class PreviewHandler(server.Handler):
    def do_GET(self):
        path=urlparse(self.path).path
        if path in {'/api/courses','/api/courses/admin'}:
            try:
                result=courses.overview(server,self.require_user_with_consents(),path.endswith('/admin'))
                result['preview']=True
                self.send_json(result)
            except PermissionError as error:
                self.send_json({'error':str(error)},401)
        elif path == '/course-preview':
            body = (ROOT / 'Превью_курса_Нейровизуал.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/course-preview/session':
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size > 1000:
                    raise ValueError('Некорректный запрос.')
                data = json.loads(self.rfile.read(size))
                role = data.get('role', 'student')
                if role not in {'student', 'admin'}:
                    raise ValueError('Неизвестный режим просмотра.')
                with closing(server.db()) as con:
                    row = con.execute('SELECT * FROM users WHERE username=?',
                                      ('student' if role == 'student' else 'course-preview-admin',)).fetchone()
                user = server.public_user(row)
                token = secrets.token_urlsafe(32)
                server.SESSIONS[token] = {'user': user}
                self.send_json({'token': token, 'user': user}, headers={'Set-Cookie': self.session_cookie(token)})
            except Exception as error:
                self.send_json({'error': str(error)}, 400)
        elif path == '/api/courses/action':
            super().do_POST()
        else:
            # Keep the preview entirely local: no payments, mail or webhooks.
            self.send_json({'error': 'В превью доступны курс и его админка. Реальные оплаты и отправка писем отключены.'}, 403)


class PreviewServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8098)
    parser.add_argument('--open-browser', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    prepare(args.data_dir)
    url = f'http://localhost:{args.port}/course-preview'
    try:
        httpd = PreviewServer(('127.0.0.1', args.port), PreviewHandler)
    except OSError:
        print(f'Cannot start preview: port {args.port} is busy. Close the previous preview window or use --port 8099.', flush=True)
        raise SystemExit(1)
    if args.open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f'Course preview: {url}\nAll seven lessons are initially open; saved group schedules are preserved. Keep this window open. Press Ctrl+C to stop.', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    main()
