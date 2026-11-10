"""Persistent authorization only for the isolated localhost demo server."""
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import server


def ensure_schema():
    with server.db() as con:
        con.execute('CREATE TABLE IF NOT EXISTS local_demo_sessions (token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,created_at TEXT NOT NULL)')


class DemoHandler(server.Handler):
    def demo_token(self):
        header=self.headers.get('Authorization','')
        if header.startswith('Bearer '):
            return header[7:].strip()
        for part in self.headers.get('Cookie','').split(';'):
            key,sep,value=part.strip().partition('=')
            if sep and key=='ege_session':
                return value
        return ''

    def current_user(self):
        user=super().current_user()
        if user:
            return user
        token=self.demo_token()
        if not token:
            return None
        digest=hashlib.sha256(token.encode()).hexdigest()
        with server.db() as con:
            row=con.execute("SELECT u.*,d.created_at AS demo_created_at FROM local_demo_sessions d JOIN users u ON u.user_id=d.user_id WHERE d.token_hash=? AND u.username IN ('student','teacher') AND u.role IN ('student','teacher')",(digest,)).fetchone()
        if not row:
            return None
        created=server.parse_iso(row['demo_created_at'])
        if not created or datetime.now(timezone.utc)-created>timedelta(days=7):
            return None
        server.SESSIONS[token]={'user':server.public_user(row),'created_at':row['demo_created_at']}
        return super().current_user()

    def send_json(self,data,status=200,headers=None):
        if status==200 and isinstance(data,dict) and data.get('token') and urlparse(self.path).path in {'/api/login','/api/auth/login'}:
            user=data.get('user') or {}
            if user.get('role') in {'student','teacher'}:
                with server.db() as con:
                    con.execute('INSERT OR REPLACE INTO local_demo_sessions VALUES(?,?,?)',(hashlib.sha256(data['token'].encode()).hexdigest(),user['user_id'],server.now_iso()))
        return super().send_json(data,status,headers)

    def do_POST(self):
        if urlparse(self.path).path in {'/api/logout','/api/auth/logout'}:
            token=self.demo_token()
            if token:
                with server.db() as con:
                    con.execute('DELETE FROM local_demo_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
        return super().do_POST()
