from playwright.sync_api import sync_playwright,expect
url='http://127.0.0.1:8790'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url+'/founder');page.locator('#start').click();expect(page.locator('.result').first).to_be_visible(timeout=30000)
    state=page.request.get(url+'/api/game').json()['game']
    for c in state['companies']:
        if c['closed'] or c['industry'] in ('未披露','',None):continue
        detail=page.request.get(url+'/api/company?id='+c['id']).json()['company']
        if detail['institutions']:break
    page.locator('#search').fill(c['id']);page.locator('.result').first.click()
    page.locator('#institutionScope').select_option('industry');expect(page.locator('[data-add]').first).to_be_visible(timeout=30000)
    page.locator('[data-add]').first.click();expect(page.locator('[data-add]').first).to_have_text('已加入名单',timeout=30000)
    page.locator('[data-tab=contacts]').click();page.locator('[data-ticket]').fill('100');page.locator('[data-finance=submit]').click()
    expect(page.locator('.finance-error')).to_contain_text('融资目标')
    expect(page.locator('[data-ticket]')).to_have_value('100')
    expect(page.locator('#financingWeek')).to_be_disabled()
    page.locator('[data-complete-plan]').click()
    page.locator('[data-tab=plan]').click()
    for k,v in {'cash':'50','target':'100','pre_money':'400','purpose':'研发'}.items():page.locator('[name='+k+']').fill(v)
    page.locator('[name=budget_research]').fill('100')
    page.locator('[name=burn]').fill('10')
    page.locator('#save').click();expect(page.locator('#saveStatus')).to_have_text('计划已保存',timeout=30000)
    page.locator('[data-tab=contacts]').click();page.locator('[data-ticket]').fill('101');page.locator('[data-finance=submit]').click()
    expect(page.locator('.finance-error')).to_contain_text('超过',timeout=30000)
    expect(page.locator('[data-ticket]')).to_have_value('101')
    page.locator('[data-ticket]').fill('100');page.locator('[data-finance=submit]').click()
    expect(page.locator('#contacts')).to_contain_text('评审中',timeout=30000)
    page.locator('#financingWeek').click();expect(page.locator('[data-finance=accept]')).to_be_visible(timeout=30000)
    page.locator('[data-finance=accept]').click();expect(page.locator('#contacts')).to_contain_text('待交割',timeout=30000)
    page.locator('#financingWeek').click();expect(page.locator('#financingSummary')).to_contain_text('企业现金 ¥150',timeout=30000)
    expect(page.locator('#contacts')).to_contain_text('20.00%')
    page.reload();page.locator('[data-tab=contacts]').click();expect(page.locator('#financingSummary')).to_contain_text('企业现金 ¥150',timeout=30000)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    b.close();print('Submit, weekly review, terms, settlement, persistence and mobile passed.')
