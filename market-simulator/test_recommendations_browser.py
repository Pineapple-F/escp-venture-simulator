"""Real-page search/preview/confirm gate, automatic recommendations and own graph.

Run: python test_recommendations_browser.py --channel msedge --output <directory>
Uses temporary accounts and mocks only expensive event forecasting.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', default='msedge' if sys.platform == 'win32' else None)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='escp-identity-browser-') as temporary:
        os.environ.update(MODEL_WARM_ON_START='0', COOKIE_SECURE='0',
                          SAVE_DB_PATH=str(Path(temporary) / 'saves.sqlite3'))
        os.environ.pop('SAVE_STORE_URL', None)
        import server
        assert not server.RECOMMENDER.model_error, server.RECOMMENDER.model_error
        known = max((row for row in server.RECOMMENDER.investor_rows if row['trained']), key=lambda row: row['company_count'])
        unseen = next(row for row in server.RECOMMENDER.investor_rows if not row['trained'])
        expected = {row['id']: server.RECOMMENDER.recommend(row['id']) for row in (known, unseen)}
        previews = {row['id']: server.RECOMMENDER.preview(row['id']) for row in (known, unseen)}

        class Quiet(server.Handler):
            def log_message(self, *args):
                pass

        httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(httpd.server_address[1])
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel=args.channel, headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                page.set_default_timeout(15000)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/api/model-forecast?**', lambda route: route.fulfill(
                    content_type='application/json', body=json.dumps({'available': False, 'reason': '界面测试不运行事件预测'})))

                def screenshot(name):
                    if args.output:
                        # Full-page capture can resize the viewport; finish any resulting transitions.
                        page.screenshot(path=str(args.output / name), full_page=True, animations='disabled')

                def choose(subject, switching=False):
                    prefix = 'switchInvestor' if switching else 'identity'
                    page.locator('#' + prefix + 'Search').fill(subject['id'])
                    button = page.locator('#' + prefix + 'Results [data-investor-choice="' + subject['id'] + '"]')
                    expect(button).to_be_visible()
                    button.click()

                def assert_results(subject, label):
                    expect(page.locator('#game')).to_be_visible()
                    expect(page.locator('#welcome')).to_be_hidden()
                    expect(page.locator('#currentInvestorName')).to_have_text(subject['name'])
                    expect(page.locator('#recommendationsView')).to_be_visible()
                    expect(page.locator('#recommendationRail')).to_be_visible()
                    expect(page.locator('#recommendationSummary, #recommendationTitle, .recommendation-method')).to_have_count(0)
                    expect(page.locator('.inbox')).to_be_hidden()
                    if page.viewport_size['width'] > 900:
                        graph_box = page.locator('#recommendationsView').bounding_box()
                        rail_box = page.locator('#recommendationRail').bounding_box()
                        assert rail_box['x'] >= graph_box['x'] + graph_box['width']
                    expect(page.locator('#recommendationRows > li')).to_have_count(10)
                    ids = page.locator('[data-recommendation-company]').evaluate_all(
                        '(rows) => rows.map(row => row.dataset.recommendationCompany)')
                    assert ids == [row['id'] for row in expected[subject['id']]['items']]
                    expect(page.locator('#ownInvestorGraph [data-own-graph-node="institution:' + subject['id'] + '"]')).to_be_visible()
                    expect(page.locator('#recommendationLoad')).to_have_count(0)
                    expect(page.locator('#advance')).to_be_enabled()

                def switch(subject):
                    page.locator('#changeInvestor').click()
                    expect(page.locator('#investorSwitchDialog')).to_be_visible()
                    choose(subject, switching=True)
                    page.locator('#confirmInvestorSwitch').click()
                    expect(page.locator('#investorSwitchDialog')).to_be_hidden()

                def assert_preview(subject):
                    expect(page.locator('#identityPreview')).to_have_attribute('data-state', 'ready')
                    expect(page.locator('#identityPreviewTitle')).to_have_text(subject['name'])
                    expect(page.locator('#identityPreviewGraph [data-ipg-node="institution:' + subject['id'] + '"]')).to_have_count(1)
                    expect(page.locator('#identityPreviewProfile')).to_contain_text(str(subject['company_count']))
                    expect(page.locator('#enterInvestor')).to_have_text('确认投资方')
                    expect(page.locator('#enterInvestor')).to_be_enabled()
                    # Measure and capture the expanded layout after its real transitions.
                    page.evaluate('''async () => {
                        const frame = () => new Promise(requestAnimationFrame);
                        await frame(); await frame();
                        await Promise.allSettled(document.getAnimations().filter(animation =>
                            animation.effect.getComputedTiming().iterations !== Infinity
                        ).map(animation => animation.finished));
                        await frame(); await frame();
                    }''')

                page.goto(base)
                expect(page.locator('#welcome')).to_be_visible()
                expect(page.locator('#game')).to_be_hidden()
                for removed_text in ('先找到你的投资方。', '投资方工作台',
                                     '从数据库中选择投资方，进入后自动查看企业推荐和自己的知识图谱。',
                                     '直接浏览投资方列表，或像搜索引擎一样输入关键词查找。必须选中一条真实记录才能进入。'):
                    expect(page.locator('body')).not_to_contain_text(removed_text)
                expect(page.locator('#identityPreview')).to_have_attribute('aria-hidden', 'true')
                expect(page.locator('#identityResults [data-investor-choice]').first).to_be_visible()
                expect(page.locator('#enterInvestor')).to_be_disabled()
                screenshot('search-only-desktop.png')
                page.locator('#identitySearch').fill('__unknown_subject__')
                expect(page.locator('#identityResults [data-investor-choice]')).to_have_count(0)
                expect(page.locator('#enterInvestor')).to_be_disabled()
                assert not context.request.post(base + '/api/new', data={'name': 'visitor'}).ok
                page.locator('#identitySearch').fill(known['id'])
                expect(page.locator('#identityResults [data-investor-choice]').first).to_be_visible()
                expect(page.locator('#enterInvestor')).to_be_disabled()
                # A failed preview never confirms an identity or exposes stale details.
                page.route('**/api/investor-preview?**', lambda route: route.fulfill(
                    status=503, content_type='application/json', body=json.dumps({'error': '测试资料暂不可用'})))
                choose(known)
                expect(page.locator('#identityPreviewStatus')).to_contain_text('测试资料暂不可用')
                expect(page.locator('#enterInvestor')).to_be_disabled()
                assert context.request.get(base + '/api/game').json()['game'] is None
                page.unroute('**/api/investor-preview?**')
                page.locator('#identityPreviewRetry').click()
                assert_preview(known)

                # Selection previews are read-only; delayed investor A cannot replace B.
                pending_previews = []
                page.route('**/api/investor-preview?**', lambda route: pending_previews.append(route))
                choose(unseen)
                expect(page.locator('#enterInvestor')).to_be_disabled()
                page.unroute('**/api/investor-preview?**')
                choose(known)
                assert_preview(known)
                for route in pending_previews:
                    route.fulfill(content_type='application/json', body=json.dumps(previews[unseen['id']]))
                assert_preview(known)
                assert context.request.get(base + '/api/game').json()['game'] is None
                left = page.locator('#identityResults').bounding_box()
                right = page.locator('#identityPreview').bounding_box()
                assert right['x'] >= left['x'] + left['width'] - 1, (left, right)
                layout = page.locator('#newForm').evaluate('''form => {
                    const style = getComputedStyle(form);
                    return {width: form.getBoundingClientRect().width, maxWidth: style.maxWidth,
                        grid: style.gridTemplateColumns, gap: style.columnGap};
                }''')
                assert layout['width'] > 1000 and layout['gap'] == '28px', layout
                print('Settled desktop preview:', layout, flush=True)
                confirm = page.locator('#enterInvestor').bounding_box()
                assert confirm['x'] >= right['x'] and confirm['y'] > right['y']
                page.locator('#identityPreviewGraph [data-ipg-action="zoom-in"]').click()
                page.locator('#identityPreviewGraph [data-ipg-action="zoom-out"]').click()
                page.locator('#identityPreviewGraph [data-ipg-action="fit"]').click()
                canvas = page.locator('#identityPreviewGraph svg.ipg-svg')
                canvas.scroll_into_view_if_needed()
                canvas_box = canvas.bounding_box()
                previous_transform = canvas.locator(':scope > g').get_attribute('transform')
                page.mouse.move(canvas_box['x'] + 8, canvas_box['y'] + 8)
                page.mouse.down()
                page.mouse.move(canvas_box['x'] + 34, canvas_box['y'] + 27, steps=3)
                page.mouse.up()
                assert canvas.locator(':scope > g').get_attribute('transform') != previous_transform
                page.locator('#identityPreviewGraph [data-ipg-action="fit"]').click()
                page.locator('#identityPreviewGraph [data-ipg-node^="round:"]').first.click()
                expect(page.locator('#identityPreviewGraph .ipg-detail')).to_contain_text('来源记录')
                screenshot('investor-preview-desktop.png')
                page.locator('#enterInvestor').click()
                assert_results(known, 'SGL 个性化推荐')
                screenshot('automatic-sgl-and-own-graph.png')
                before = context.request.get(base + '/api/legacy-export').json()
                page.locator('#recommendationRows .recommendation-open').first.click()
                expect(page.locator('#companyDialog')).to_be_visible()
                expect(page.locator('#companyBody')).to_contain_text(expected[known['id']]['items'][0]['name'])
                page.locator('#companyDialog [data-close]').first.click()
                page.reload()
                assert_results(known, 'SGL 个性化推荐')
                assert context.request.get(base + '/api/legacy-export').json() == before

                page.locator('#changeInvestor').click()
                choose(unseen, switching=True)
                page.keyboard.press('Escape')
                assert_results(known, 'SGL 个性化推荐')
                switch(unseen)
                assert_results(unseen, '热门推荐')
                after = context.request.get(base + '/api/legacy-export').json()
                for key in ('cash', 'positions', 'curve', 'log', 'month'):
                    assert before[key] == after[key], key
                assert after['investor_id'] == unseen['id']
                page.reload()
                assert_results(unseen, '热门推荐')
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                screenshot('automatic-mostpop-mobile.png')
                page.set_viewport_size({'width': 1440, 'height': 1000})

                page.route('**/api/recommendations', lambda route: route.fulfill(
                    status=503, content_type='application/json', body=json.dumps({'error': '测试推荐暂不可用'})))
                switch(known)
                expect(page.locator('#recommendationStatus')).to_contain_text('测试推荐暂不可用')
                expect(page.locator('#recommendationRows > li')).to_have_count(0)
                page.unroute('**/api/recommendations')
                page.locator('#recommendationRetry').click()
                assert_results(known, 'SGL 个性化推荐')

                # A delayed old identity response must not overwrite the new one.
                pending = []
                page.route('**/api/recommendations', lambda route: pending.append(route))
                switch(unseen)
                expect(page.locator('#recommendationRows > li')).to_have_count(0)
                page.unroute('**/api/recommendations')
                switch(known)
                assert_results(known, 'SGL 个性化推荐')
                for route in pending:
                    route.fulfill(content_type='application/json', body=json.dumps(expected[unseen['id']]))
                assert_results(known, 'SGL 个性化推荐')
                page.goto(base + '/founder')
                expect(page.locator('#workspace')).to_be_visible()
                expect(page.locator('#recommendationsView')).to_have_count(0)

                # Existing unbound account must choose identity without resetting funds.
                legacy = server.new_game(server.UNIVERSE, 'Existing account', initial=123456)
                sid = secrets.token_urlsafe(32)
                server.saves().create(sid, legacy)
                old_context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
                old_context.add_cookies([{'name': 'market_save', 'value': sid, 'url': base, 'httpOnly': True, 'sameSite': 'Strict'}])
                old_page = old_context.new_page()
                old_page.goto(base)
                expect(old_page.locator('#welcome')).to_be_visible()
                expect(old_page.locator('#game')).to_be_hidden()
                expect(old_page.locator('#enterInvestor')).to_be_disabled()
                assert old_page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                if args.output:
                    old_page.screenshot(path=str(args.output / 'identity-selection-mobile.png'), full_page=True, animations='disabled')
                old_page.locator('#identitySearch').fill(known['id'])
                # Existing accounts do not validate hidden new-account amount fields.
                old_page.locator('#newForm [name=initial]').evaluate('(input) => { input.value = ""; }')
                old_page.locator('#identityResults [data-investor-choice="' + known['id'] + '"]').click()
                expect(old_page.locator('#identityPreview')).to_have_attribute('data-state', 'ready')
                expect(old_page.locator('#identityPreviewTitle')).to_have_text(known['name'])
                assert old_page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                assert old_page.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches')
                assert old_context.request.get(base + '/api/legacy-export').json()['cash'] == 123456
                assert not old_context.request.get(base + '/api/game').json()['game'].get('investor_id')
                if args.output:
                    old_page.screenshot(path=str(args.output / 'investor-preview-mobile.png'), full_page=True, animations='disabled')
                old_page.locator('#enterInvestor').click()
                expect(old_page.locator('#game')).to_be_visible()
                saved = old_context.request.get(base + '/api/legacy-export').json()
                assert saved['investor_id'] == known['id'] and saved['cash'] == 123456
                assert not errors, errors
                old_context.close()
                browser.close()
                print('PASS: minimal search entry, right profile/interactive graph preview, explicit confirmation, '
                      'read-only preview/retry/stale isolation, reduced-motion/mobile, required DB identity, '
                      'automatic SGL/MostPop and own graph, '
                      'switch/cancel/reload, preserved saves, company details, mobile, retry/stale response, founder access, legacy binding.')
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()


if __name__ == '__main__':
    main()
