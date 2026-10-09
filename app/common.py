from __future__ import annotations
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def uid(prefix, *parts):
    return prefix + '_' + hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:24]


def digest(data):
    if isinstance(data, Path):
        return hashlib.sha256(data.read_bytes()).hexdigest()
    if not isinstance(data, bytes):
        data = str(data).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def normalized(text):
    # Format normalization only: never replace O with 0 or drop identifier characters.
    return ''.join(unicodedata.normalize('NFKC', str(text)).split()).casefold()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()
