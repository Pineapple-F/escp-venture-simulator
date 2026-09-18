"""Real-page graph regression checks using a temporary account database.

Run: python test_knowledge_graph_browser.py --channel msedge --output <directory>
Requires test-requirements.txt and an installed browser. No production saves change.
"""
import argparse
import json
import sqlite3
import sys
import tempfile
import threading
from contextlib import closing
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
import server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', default='msedge' if sys.platform == 'win32' else None)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    original_db = server.DB
    with tempfile.TemporaryDirectory(prefix='market-graph-test-') as temporary:
        server.DB = Path(temporary) / 'saves.sqlite3'
        with closing(sqlite3.connect(server.DB)) as connection, connection:
            connection.execute('CREATE TABLE saves (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
        class QuietHandler(server.Handler):
            def log_message(self, *args):
                pass
        class TestServer(server.ThreadingHTTPServer):
            daemon_threads = False
        httpd = TestServer(('127.0.0.1', 0), QuietHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(httpd.server_address[1])
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel=args.channel, headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                assert context.request.get(base + '/api/knowledge-graph?entity_type=company&entity_id=missing').status == 401
                created = context.request.post(base + '/api/new', data={'name': '图谱测试账户'})
                assert created.ok
                assert context.request.get(base + '/api/knowledge-graph?entity_type=company&entity_id=missing').status == 404
                assert context.request.get(base + '/api/knowledge-graph?entity_type=invalid&entity_id=x').status == 400
                assert context.request.get(base + '/api/knowledge-graph?entity_type=company').status == 400
                for path in ['/knowledge-graph.js', '/knowledge-graph.css']:
                    assert context.request.get(base + path).ok
                before = context.request.get(base + '/api/legacy-export').json()
                cid = next(cid for cid, rows in server.KNOWLEDGE_GRAPH.company_rounds.items()
                           if 3 <= len(rows) <= 6 and any(server.KNOWLEDGE_GRAPH.round_institutions[r['id']] for r in rows))
                name = server.KNOWLEDGE_GRAPH.companies[cid]['name']
                graph_data = context.request.get(base + '/api/knowledge-graph?entity_type=company&entity_id=' + cid).json()
                assert graph_data['root_id'] == 'company:' + cid
                page = context.new_page()
                def screenshot(filename):
                    if args.output:
                        page.evaluate('() => Promise.all(document.getAnimations().map(a => a.finished.catch(() => {})))')
                        page.screenshot(path=str(args.output / filename))
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base)
                page.locator('[data-discover=history]').click()
                page.locator('[data-filter=all]').click()
                page.locator('#search').fill(name)
                page.locator('#marketRows [data-company="' + cid + '"]').first.click()
                page.locator('#offerAmount').fill('12345')
                trigger = page.locator('#companyDialog [data-kg-type=company]')
                trigger.click()
                dialog = page.locator('#knowledgeGraphDialog')
                expect(dialog.locator('.kg-content')).to_be_visible()
                expect(dialog.locator('[data-kg-node]')).to_have_count(len(graph_data['nodes']))
                screenshot('investor-company-graph.png')
                institution = dialog.locator('[data-kg-node^="institution:"]').first
                institution_id = institution.get_attribute('data-kg-node')
                institution.click()
                dialog.locator('.kg-evidence summary').first.click()
                expect(dialog.locator('.kg-evidence[open]')).to_contain_text('机构')
                dialog.locator('[data-kg-explore]').click()
                expect(dialog.locator('[data-kg-node="' + institution_id + '"]')).to_have_attribute('aria-pressed', 'true')
                dialog.get_by_role('button', name='← 返回上一图谱').click()
                expect(dialog.locator('[data-kg-node="company:' + cid + '"]')).to_have_attribute('aria-pressed', 'true')
                dialog.locator('[data-kg-filter=institution]').uncheck()
                expect(dialog.locator('[data-kg-node^="institution:"]')).to_have_count(0)
                dialog.locator('[data-kg-filter=institution]').check()
                dialog.get_by_role('button', name='放大图谱', exact=True).click()
                dialog.get_by_role('button', name='适应视图', exact=True).click()
                page.keyboard.press('Escape')
                expect(trigger).to_be_focused()
                expect(page.locator('#offerAmount')).to_have_value('12345')
                page.locator('#companyDialog [data-close]').click()

                # Founder exploration must not switch the operating company or discard its draft.
                page.goto(base + '/founder')
                page.locator('#search').fill(cid)
                page.locator('#results [data-id="' + cid + '"]').click()
                expect(page.locator('#picker')).to_be_hidden()
                page.locator('[data-section=actions]').click()
                page.locator('[data-tab=plan]').click()
                page.locator('#planForm [name=purpose_categories][value=other]').check()
                page.locator('#planForm [name=purpose_detail]').fill('保留这份未保存的融资草稿')
                page.locator('[data-section=graph]').click()
                expect(page.locator('#graphSection')).to_be_visible()
                screenshot('founder-graph-workspace.png')
                other = page.locator('#graphCompanyResults [data-kg-id]').first
                other_id = other.get_attribute('data-kg-id')
                other.click()
                expect(dialog.locator('[data-kg-node="company:' + other_id + '"]')).to_be_visible()
                dialog.get_by_role('button', name='关闭知识图谱', exact=True).click()
                expect(page.locator('#sidebarCompany')).to_have_text(name)
                page.locator('#graphFindInvestors').click()
                page.locator('#institutions [data-investor]').first.click()
                page.locator('#investorDialog [data-kg-type=institution]').click()
                expect(dialog.locator('.kg-content')).to_be_visible()
                expect(dialog.locator('[data-kg-node^="institution:"]')).to_have_count(1)
                screenshot('founder-investor-graph.png')
                page.keyboard.press('Escape')
                expect(page.locator('#investorDialog')).to_be_visible()
                page.locator('#investorClose').click()
                page.locator('[data-section=actions]').click()
                page.locator('[data-tab=plan]').click()
                expect(page.locator('#planForm [name=purpose_detail]')).to_have_value('保留这份未保存的融资草稿')
                page.locator('[data-section=graph]').click()
                page.set_viewport_size({'width': 390, 'height': 844})
                page.locator('#ownCompanyGraph').click()
                expect(dialog.locator('.kg-content')).to_be_visible()
                assert dialog.evaluate('(d) => d.scrollWidth <= d.clientWidth + 1')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                screenshot('mobile-company-graph.png')
                dialog.get_by_role('button', name='关闭知识图谱', exact=True).click()

                # Failed reads can retry; a late response cannot overwrite a new root.
                page.route('**/api/knowledge-graph?**', lambda route: route.fulfill(status=500, content_type='application/json', body=json.dumps({'error': '测试读取失败'})))
                page.locator('#ownCompanyGraph').click()
                expect(dialog.locator('.kg-status')).to_contain_text('测试读取失败')
                page.unroute('**/api/knowledge-graph?**')
                dialog.get_by_role('button', name='重新加载', exact=True).click()
                expect(dialog.locator('.kg-content')).to_be_visible()
                page.evaluate('([a,b]) => { KnowledgeGraph.open("company",a); KnowledgeGraph.open("company",b); }', [cid, other_id])
                expect(dialog.locator('[data-kg-node="company:' + other_id + '"]')).to_have_attribute('aria-pressed', 'true')
                page.keyboard.press('Escape')
                after = context.request.get(base + '/api/legacy-export').json()
                assert after == before, 'Graph exploration changed saved account data'
                assert not errors, errors
                browser.close()
                print('PASS: API validation, investor/founder graphs, sources, navigation, filters, retry, race, draft retention, mobile layout, read-only saves; no JS errors.')
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()
            server.DB = original_db


if __name__ == '__main__':
    main()
