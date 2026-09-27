"""Exercise the deployed frontend, cookie session and revision protection."""
import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--attempts', type=int, default=30)
    parser.add_argument('--storage', choices=['sqlite','durable-object'])
    parser.add_argument('--read-only', action='store_true')
    args = parser.parse_args()
    base = args.url.rstrip('/')
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(path, data=None):
        headers = {'Origin':base}
        body = json.dumps(data).encode() if data is not None else None
        if body is not None: headers['Content-Type']='application/json'
        req = urllib.request.Request(base+path, body, headers)
        with client.open(req, timeout=90) as response:
            return response.status, response.read()
    for attempt in range(args.attempts):
        try:
            _, raw = request('/api/health')
            health = json.loads(raw)
            assert health['ok']
            if args.storage: assert health.get('storage') == args.storage, health
            break
        except (urllib.error.URLError, TimeoutError, AssertionError) as error:
            if attempt == args.attempts-1: raise
            print(f'Waiting for container provisioning ({attempt+1}/{args.attempts}): {type(error).__name__}', flush=True)
            time.sleep(10)
    for path in ('/', '/founder', '/app.js', '/founder.js'):
        status, body = request(path)
        assert status == 200 and len(body)>100, path
    _, raw = request('/api/game')
    assert json.loads(raw)['game'] is None
    if not args.read_only:
        # One test save per deployment, identified by name; no investment action.
        _, raw = request('/api/new', {'name':'Deployment smoke test','currency':'CNY'})
        game = json.loads(raw)['game']
        revision = game['revision']
        _, raw = request('/api/action', {'type':'advance','revision':revision})
        assert json.loads(raw)['game']['revision'] == revision+1
        try:
            request('/api/action', {'type':'advance','revision':revision})
            raise AssertionError('Stale write was accepted')
        except urllib.error.HTTPError as error:
            assert error.code == 409, error.code
        _, raw = request('/api/game')
        assert json.loads(raw)['game']['revision'] == revision+1
    print('PASS: current frontend, API, session persistence and revision checks', flush=True)


if __name__ == '__main__': main()
