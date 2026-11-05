"""Start the local site, reuse an existing instance, and open it when ready."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8790'
CLIENT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def ready():
    try:
        with CLIENT.open(URL + '/api/health', timeout=1) as response:
            data = json.load(response)
            return data.get('ok') is True and data.get('service') == 'venture-simulator'
    except (OSError, ValueError, urllib.error.URLError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if ready():
        print('ESCP 已在运行：' + URL, flush=True)
        if not args.no_browser:
            webbrowser.open(URL)
        return
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', 8790))
        except OSError:
            raise SystemExit('8790 端口已被其他程序占用，请先关闭占用该端口的程序。')
    missing = [name for name in ('duckdb', 'numpy') if importlib.util.find_spec(name) is None]
    if missing:
        print('当前 Python 缺少运行依赖：' + ', '.join(missing))
        raise SystemExit('请使用已配置的 Python，或运行 python -m pip install -r market-simulator/requirements.txt')
    # Local accounts use the existing local database. A copied cloud setting
    # must not route a local preview to a remote account store or require HTTPS.
    os.environ.pop('SAVE_STORE_URL', None)
    os.environ.update(MARKET_HOST='127.0.0.1', MARKET_PORT='8790', COOKIE_SECURE='0',
                      MODEL_WARM_ON_START='0', MODEL_DEVICE='cpu', MODEL_CPU_THREADS='1',
                      PYTHONUNBUFFERED='1', PYTHONUTF8='1')
    print('正在启动 ESCP：' + URL, flush=True)
    print('推荐使用 CPU；企业事件预测在需要时加载。按 Ctrl+C 停止。', flush=True)
    done = threading.Event()

    def announce():
        for _ in range(60):
            if done.wait(.5):
                return
            if ready():
                print('ESCP 已就绪：' + URL, flush=True)
                if not args.no_browser:
                    webbrowser.open(URL)
                return

    threading.Thread(target=announce, daemon=True).start()
    sys.path.insert(0, str(ROOT / 'market-simulator'))
    os.chdir(ROOT / 'market-simulator')
    try:
        runpy.run_path(str(ROOT / 'market-simulator/server.py'), run_name='__main__')
    except KeyboardInterrupt:
        print('\nESCP 已停止。', flush=True)
    finally:
        done.set()


if __name__ == '__main__':
    main()
