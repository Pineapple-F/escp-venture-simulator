from playwright.sync_api import sync_playwright,expect

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
    page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8790/founder');page.locator('#start').click()
    expect(page.locator('.result').first).to_be_visible(timeout=30000)
    page.locator('.result').first.click();page.locator('[data-section=past]').click()
    expect(page.locator('#pastFunding')).not_to_be_empty()
    rows=[dict(id=str(i),date=f'202{i}-01-01',available=f'202{i}-01-01',stage='A轮',amount=a,currency=c) for i,(a,c) in enumerate([(10,'CNY'),(None,'CNY'),(20,'CNY'),(30,'USD')])]
    page.evaluate('(rows)=>document.querySelector("#pastFunding").innerHTML=fundingVisual(rows)',rows)
    assert page.locator('.funding-timeline li').count()==4
    assert page.locator('.funding-amount-chart').count()==1
    assert page.locator('.funding-bar').count()==2
    expect(page.locator('.funding-timeline')).to_contain_text('金额未披露')
    assert page.locator('.funding-bar').first.get_attribute('style')=='width:50.0000%'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate('(rows)=>document.querySelector("#pastFunding").innerHTML=fundingVisual(rows)',rows[:1])
    assert page.locator('.funding-amount-chart').count()==0
    assert page.locator('.funding-timeline li').count()==1
    assert not errors,errors
    b.close();print('Funding timeline, currency separation, missing values, scale and mobile passed.')
