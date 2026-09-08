from playwright.sync_api import sync_playwright,expect

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    page=b.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8790');page.locator('#newForm button[type=submit]').click()
    expect(page.locator('#game')).to_be_visible(timeout=30000)
    state=page.request.get('http://127.0.0.1:8790/api/game').json()['game']
    assert isinstance(state['companies'][0]['history'],dict)
    c=next(c for c in state['companies'] if not c['closed'])
    page.locator('#search').fill(c['name'])
    page.locator('#marketRows [data-company="'+c['id']+'"]').first.click()
    expect(page.locator('#offerAmount')).to_be_visible(timeout=30000)
    page.locator('#offerAmount').fill('12345');page.locator('#offerForm button').click()
    expect(page.locator('.investment-result')).to_contain_text('12,345',timeout=30000)
    expect(page.locator('#cash')).to_have_text('¥99,987,655')
    page.locator('[data-result-portfolio]').click()
    expect(page.locator('#positions')).to_contain_text('12,345')
    page.locator('[data-view=journal]').click()
    assert page.locator('.capital-column').count()==2
    page.locator('.capital-column').first.click()
    expect(page.locator('#capitalReading')).to_contain_text('开户')
    page.reload();expect(page.locator('#cash')).to_have_text('¥99,987,655',timeout=30000)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    b.close();print('Lazy details, allocation result, opening baseline, persistence and mobile passed.')
