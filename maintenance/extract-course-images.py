"""Extract embedded course images losslessly into deployable protected assets.

Run from any directory. Original HTML is backed up under ignored tmp/.
Re-running is safe: filenames are SHA-256 hashes and unchanged files are skipped.
"""
import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'app'/'Нейровизуал для учителя'
DEST = ROOT/'app'/'course-media'
BACKUP = ROOT/'tmp'/'course-before-image-extraction'
PATTERN = re.compile(r'data:image/(png|jpeg|gif|webp|svg\+xml|avif);base64,([A-Za-z0-9+/=\r\n]+)')


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    report = []
    for path in SOURCE.glob('*.html'):
        source = path.read_text('utf-8')
        before = path.stat().st_size
        count = 0

        def extract(match):
            nonlocal count
            payload = base64.b64decode(match[2], validate=False)
            ext = {'jpeg': 'jpg', 'svg+xml': 'svg'}.get(match[1], match[1])
            name = hashlib.sha256(payload).hexdigest()+'.'+ext
            asset = DEST/name
            if asset.exists():
                if asset.read_bytes() != payload:
                    raise RuntimeError('Existing image does not match its hash: '+name)
            else:
                if len(payload) >= 100*1024*1024:
                    raise RuntimeError('Image itself exceeds the GitHub limit: '+name)
                asset.write_bytes(payload)
            count += 1
            return '/api/courses/asset?id='+name

        updated = PATTERN.sub(extract, source)
        if count:
            backup = BACKUP/path.name
            if not backup.exists(): backup.write_bytes(path.read_bytes())
            path.write_text(updated, 'utf-8')
            report.append({'file': path.name, 'before': before, 'after': path.stat().st_size, 'images': count})
    (ROOT/'tmp'/'course-image-extraction.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
