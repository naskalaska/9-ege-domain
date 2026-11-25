"""Serve the unchanged game with shared media URLs instead of embedded base64."""
import base64
import hashlib
import re
import threading
from functools import lru_cache
from pathlib import Path

MEDIA = re.compile(r'data:(image/(?:png|gif)|audio/mpeg);base64,([A-Za-z0-9+/=]+)')
ASSET_NAME = re.compile(r'[a-f0-9]{64}\.(?:png|gif|mp3)\Z')
LOCK = threading.RLock()


def web_body(source: Path, media_dir: Path) -> bytes:
    stat = source.stat()
    with LOCK:
        return _prepare(str(source), stat.st_mtime_ns, stat.st_size, str(media_dir))


@lru_cache(maxsize=2)
def _prepare(source, modified, size, media_dir):
    root = Path(media_dir)
    root.mkdir(parents=True, exist_ok=True)

    def externalize(match):
        mime, encoded = match.groups()
        extension = {'image/png': 'png', 'image/gif': 'gif', 'audio/mpeg': 'mp3'}[mime]
        name = hashlib.sha256(encoded.encode('ascii')).hexdigest() + '.' + extension
        target = root / name
        if not target.is_file():
            temporary = target.with_suffix('.tmp')
            temporary.write_bytes(base64.b64decode(encoded, validate=True))
            temporary.replace(target)
        return '/espresso-media/' + name

    return MEDIA.sub(externalize, Path(source).read_text(encoding='utf-8-sig')).encode('utf-8')
