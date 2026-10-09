"""Perform a minimal authenticated probe without displaying credentials."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agnes import AgnesClient

if __name__ == '__main__':
    client = AgnesClient()
    response = client.json('连接测试，请原样返回输入对象。', {'ok': True}, purpose='connection_test', max_tokens=256)
    if response != {'ok': True}:
        raise SystemExit('连接成功但 JSON 响应未通过验证')
    print('Agnes connection OK; model=' + client.model)
