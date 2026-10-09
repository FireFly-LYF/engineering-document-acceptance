"""Small Agnes chat-completions adapter. Credentials never enter artifacts."""
from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from app.common import digest

ROOT = Path(__file__).resolve().parents[1]


def load_env(path=None):
    path = Path(path or ROOT / '.env')
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def parse_json(content):
    text = content.strip()
    if text.startswith('```'):
        text = '\n'.join(text.splitlines()[1:])
        text = text.rsplit('```', 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # No eval, and no acceptance of arbitrary trailing model prose.
        start = min([i for i in (text.find('{'), text.find('[')) if i >= 0], default=-1)
        if start >= 0:
            obj, end = json.JSONDecoder().raw_decode(text[start:])
            if not text[start + end:].strip():
                return obj
        raise ValueError('Agnes 返回的 JSON 无效') from None


class AgnesClient:
    def __init__(self, *, base_url=None, model=None, api_key=None, timeout=None):
        load_env()
        self.base_url = (base_url or os.getenv('AGNES_BASE_URL', 'https://api.agnes-ai.cn/v1')).rstrip('/')
        self.model = model or os.getenv('AGNES_MODEL', 'agnes-3.0-flash')
        self.api_key = api_key or os.getenv('AGNES_API_KEY', '')
        self.timeout = float(timeout or os.getenv('AGNES_TIMEOUT', '120'))
        self._lock = threading.Lock()
        self.calls = []

    def _record(self,system,user,image,purpose,started,attempt,*,status,usage=None,error=None):
        with self._lock:
            self.calls.append({'purpose':purpose,'model':self.model,
                'elapsed_seconds':round(time.perf_counter()-started,3),
                'usage':usage or {},'attempts':attempt+1,'status':status,'error_code':error,
                'prompt_sha256':digest(system),'input_sha256':digest(user+(digest(image) if image else '')),
                '_thread':threading.get_ident()})

    def chat(self, system, payload, *, purpose='extraction', image=None, max_tokens=4096):
        if not self.api_key:
            raise RuntimeError('缺少 AGNES_API_KEY，请配置项目 .env 或环境变量')
        user = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        content = user
        if image:
            content = [{'type': 'text', 'text': user}, {'type': 'image_url', 'image_url': {
                'url': 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')}}]
        body = {'model': self.model, 'messages': [
            {'role': 'system', 'content': system}, {'role': 'user', 'content': content}],
            'stream': False, 'temperature': 0, 'max_tokens': max_tokens}
        req = urllib.request.Request(self.base_url + '/chat/completions',
            data=json.dumps(body).encode('utf-8'), method='POST',
            headers={'Authorization': 'Bearer ' + self.api_key, 'Content-Type': 'application/json'})
        started = time.perf_counter()
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    result = json.load(response)
                choice = result['choices'][0]
                if choice.get('finish_reason') == 'length':
                    raise RuntimeError('Agnes 响应被截断，请减少单次输入或增加输出预算')
                text = choice['message']['content']
                if isinstance(text, list):
                    text = ''.join(part.get('text', '') for part in text if isinstance(part, dict))
                if not isinstance(text, str):
                    raise RuntimeError('Agnes 未返回可读内容')
                self._record(system,user,image,purpose,started,attempt,status='succeeded',usage=result.get('usage'))
                return text
            except urllib.error.HTTPError as exc:
                # Do not log provider bodies, request headers or credentials.
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    self._record(system,user,image,purpose,started,attempt,status='failed',error=f'http_{exc.code}')
                    raise RuntimeError(f'Agnes HTTP {exc.code}（{purpose}）') from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    self._record(system,user,image,purpose,started,attempt,status='failed',error='network_error')
                    raise RuntimeError(f'Agnes 网络连接失败（{purpose}）') from None
            except (KeyError,IndexError,ValueError,TypeError,RuntimeError):
                self._record(system,user,image,purpose,started,attempt,status='rejected',error='invalid_response')
                raise RuntimeError(f'Agnes 返回无效或截断内容（{purpose}）') from None
            time.sleep(0.8 * (attempt + 1))

    def json(self, system, payload, **kwargs):
        retries = max(0,min(1,int(os.getenv('AGNES_JSON_RETRIES','1'))))
        for attempt in range(retries+1):
            text = self.chat(system + '\n仅输出 JSON，不使用代码块。', payload, **kwargs)
            try:
                return parse_json(text)
            except ValueError:
                with self._lock:
                    for call in reversed(self.calls):
                        if call['_thread']==threading.get_ident():
                            call.update(status='rejected',error_code='invalid_json')
                            break
                if attempt==retries:
                    raise
                time.sleep(.5)

    def stats(self):
        with self._lock:
            calls = [{k:v for k,v in call.items() if k!='_thread'} for call in self.calls]
        return {'model': self.model, 'calls': calls, 'total_calls': len(calls),
            'total_tokens': sum(int(x['usage'].get('total_tokens', 0)) for x in calls)}
