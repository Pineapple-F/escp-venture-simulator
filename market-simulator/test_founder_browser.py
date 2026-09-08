import os
from playwright.sync_api import sync_playwright,expect

url=os.environ.get('TEST_URL','http://127.0.0.1:8790')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url+'/founder');page.locator('#start').click()
    expect(page.locator('.result').first).to_be_visible(timeout=30000)
    page.locator('.result').first.click()
    page.locator('[data-section=overview]').click()
    expect(page.locator('.profile-grid')).to_be_visible(timeout=30000)
    expect(page.locator('#profileNote')).to_contain_text('数据快照')
    page.locator('[data-section=past]').click()
    expect(page.locator('#pastFunding')).not_to_be_empty()
    page.locator('[data-section=finance]').click()
    page.locator('[data-tab=plan]').click()
    expect(page.locator('#planForm')).to_be_visible(timeout=30000)
    page.locator('[name=cash]').fill('600000');page.locator('[name=burn]').fill('100000')
    page.locator('[name=target]').fill('3000000');page.locator('[name=purpose]').fill('产品研发')
    page.locator('[name=budget_research]').fill('3000000')
    expect(page.locator('#runway')).to_contain_text('6.0 个月')
    page.locator('[name=burn]').fill('33')
    expect(page.locator('#runway')).to_have_text('资金可用期异常')
    page.locator('[name=burn]').fill('100000')
    page.locator('#save').click();expect(page.locator('#saveStatus')).to_have_text('计划已保存',timeout=30000)
    state=page.request.get(url+'/api/game').json()['game']
    assert state['cash']==state['initial'] and not state['positions']
    page.reload();expect(page.locator('[name=cash]')).to_have_value('600000',timeout=30000)
    page.locator('[data-tab=plan]').click()
    with page.expect_download() as dl:page.locator('#export').click()
    assert dl.value.suggested_filename=='融资准备清单.txt'
    page.locator('[name=burn]').fill('0');expect(page.locator('#runway')).to_have_text('暂无净现金消耗')
    page.locator('#save').click();expect(page.locator('#saveStatus')).to_have_text('计划已保存',timeout=30000)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.goto(url+'/');expect(page.locator('#game')).to_be_visible(timeout=30000)
    expect(page.locator('#cash')).to_have_text('¥100,000,000')
    assert not errors,errors
    browser.close();print('Founder plan, persistence, export, zero burn, mobile and investor isolation passed.')
