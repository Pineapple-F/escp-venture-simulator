"""Exercise the deployed frontend, cookie session and revision protection."""
import argparse
import http.cookiejar
import http.client
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
        except (OSError, http.client.HTTPException, AssertionError) as error:
            if attempt == args.attempts-1: raise
            print(f'Waiting for container provisioning ({attempt+1}/{args.attempts}): {type(error).__name__}', flush=True)
            time.sleep(10)
    for path in ('/', '/founder', '/app.js', '/founder.js', '/recommendations.js', '/recommendations.css',
                 '/investor-preview-graph.js', '/investor-preview-graph.css'):
        status, body = request(path)
        assert status == 200 and len(body)>100, path
    _, raw = request('/api/game')
    assert json.loads(raw)['game'] is None
    if not args.read_only:
        # One isolated test save per deployment; no investment action.
        _, raw = request('/api/recommendation-investors')
        subjects = json.loads(raw)
        assert subjects['items'], 'No investment subjects loaded'
        subject = subjects['items'][0]
        _, raw = request('/api/investor-preview?investor_id=' + subject['id'])
        preview = json.loads(raw)
        assert preview['investor']['id'] == subject['id']
        assert preview['graph']['root_id'] == 'institution:' + subject['id']
        _, raw = request('/api/game')
        assert json.loads(raw)['game'] is None, 'Preview created an account'
        _, raw = request('/api/new', {'name':'Deployment smoke test','currency':'CNY', 'investor_id':subject['id']})
        game = json.loads(raw)['game']
        recommendation_started = time.monotonic()
        _, raw = request('/api/recommendations')
        recommendations = json.loads(raw)
        assert recommendations['method'] == ('sgl' if subject['trained'] else 'mostpop')
        assert recommendations['count'] == 10
        assert len({item['id'] for item in recommendations['items']}) == 10
        assert time.monotonic() - recommendation_started < 10, 'Recommendation took over 10 seconds'
        _, raw = request('/api/investor-graph')
        assert json.loads(raw)['root_id'] == 'institution:' + subject['id']
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
