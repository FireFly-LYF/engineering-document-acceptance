import io
import json
import urllib.error
import pytest
from app.agnes import AgnesClient


class Response:
    def __init__(self,content):
        self.content = content
    def __enter__(self):
        return io.BytesIO(json.dumps({'choices':[{'message':{'content':self.content},'finish_reason':'stop'}],
            'usage':{'total_tokens':12}}).encode())
    def __exit__(self,*args):
        return False


def test_invalid_json_is_logged_as_rejected(monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen',lambda *a,**k:Response('这不是JSON'))
    client = AgnesClient(api_key='local-test-secret')
    with pytest.raises(ValueError):
        client.json('system',{'field':'value'})
    assert client.stats()['calls'][0]['status']=='rejected'
    assert 'local-test-secret' not in json.dumps(client.stats())


def test_http_failure_does_not_echo_provider_body_or_key(monkeypatch):
    def fail(*args,**kwargs):
        raise urllib.error.HTTPError('https://example.invalid',401,'SECRET_REMOTE_DETAIL',{},io.BytesIO(b'SECRET_BODY'))
    monkeypatch.setattr('urllib.request.urlopen',fail)
    client = AgnesClient(api_key='local-test-secret')
    with pytest.raises(RuntimeError) as error:
        client.chat('system','input')
    assert 'SECRET' not in str(error.value)
    assert client.stats()['calls'][0]['error_code']=='http_401'
    assert 'local-test-secret' not in json.dumps(client.stats())


def test_model_does_not_receive_credentials_as_user_content(monkeypatch):
    requests = []
    def respond(request,**kwargs):
        requests.append(json.loads(request.data))
        return Response('{"ok": true}')
    monkeypatch.setattr('urllib.request.urlopen',respond)
    client = AgnesClient(api_key='local-test-secret')
    assert client.json('system',{'ok':True})=={'ok':True}
    assert 'local-test-secret' not in json.dumps(requests)


def test_invalid_json_retry_keeps_rejection_and_usage(monkeypatch):
    responses = iter(['invalid','{"ok": true}'])
    monkeypatch.setattr('urllib.request.urlopen',lambda *a,**k:Response(next(responses)))
    client = AgnesClient(api_key='local-test-secret')
    assert client.json('system',{'ok':True})=={'ok':True}
    assert [call['status'] for call in client.stats()['calls']]==['rejected','succeeded']
    assert client.stats()['total_tokens']==24
