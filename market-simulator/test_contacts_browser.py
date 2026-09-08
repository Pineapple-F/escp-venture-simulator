import os
from playwright.sync_api import sync_playwright,expect
url=os.environ.get('TEST_URL','http://127.0.0.1:8790')
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url+'/founder');page.locator('#start').click()
    expect(page.locator('.result').first).to_be_visible(timeout=30000)
    state=page.request.get(url+'/api/game').json()['game']
    for c in state['companies']:
        if c['industry'] in ('未披露','',None):continue
        detail=page.request.get(url+'/api/company?id='+c['id']).json()['company']
        if detail['institutions']:break
    else:raise AssertionError('No institution matches')
    page.locator('#search').fill(c['id']);page.locator('.result').first.click()
    expect(page.locator('[data-add]').first).to_be_visible(timeout=30000)
    first_name=page.locator('.institution-card h3').first.inner_text()
    iid=page.locator('[data-investor]').first.get_attribute('data-investor')
    page.locator('[data-investor]').first.click()
    expect(page.locator('#investorTitle')).to_have_text(first_name,timeout=30000)
    detail=page.request.get(url+'/api/institution?id='+iid).json()
    assert page.locator('#investorCases .record').count()==len(detail['items'])
    if detail['pages']>1:
        page.locator('#investorNext').click()
        expect(page.locator('#investorPage')).to_have_text('2 / '+str(detail['pages']),timeout=30000)
    assert page.locator('.institution-card details').count()==0
    page.locator('#investorClose').click()
    page.locator('#institutionSearch').fill('不存在的机构_987xyz')
    expect(page.locator('#institutions')).to_contain_text('没有匹配结果',timeout=30000)
    page.locator('#institutionSearch').fill(first_name)
    expect(page.locator('.institution-card h3').first).to_have_text(first_name,timeout=30000)
    page.locator('#institutionSearch').fill('')
    expect(page.locator('[data-add]').first).to_be_visible(timeout=30000)
    assert page.locator('[data-goal]').count()==0
    page.locator('[data-tab=find]').click()
    page.locator('[data-add]').first.click()
    expect(page.locator('[data-add]').first).to_have_text('已加入名单',timeout=30000)
    page.locator('[data-tab=contacts]').click()
    expect(page.locator('.contact')).to_contain_text('未提交')
    page.reload();page.locator('[data-tab=contacts]').click()
    assert page.locator('#goals').count()==0
    expect(page.locator('[data-finance=submit]')).to_be_visible(timeout=30000)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    b.close();print('Historical candidates, shortlist, goal persistence and mobile passed.')
