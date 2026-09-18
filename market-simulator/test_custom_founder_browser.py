from playwright.sync_api import sync_playwright, expect


URL = "http://127.0.0.1:8790"


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=True,
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL + "/founder")
    page.locator("#buildOwn").click()
    expect(page.locator("#customSection")).to_be_visible(timeout=30000)
    expect(page.locator('[data-section="graph"]')).to_be_hidden()
    expect(page.locator("#buildOwnExisting")).not_to_have_class("secondary")

    profile = page.locator("#customProfileForm")
    profile.locator('[name="name"]').fill("远航科技")
    profile.locator('[name="industry"]').fill("企业服务")
    profile.locator('[name="region"]').fill("上海")
    profile.locator('button[type="submit"]').click()
    expect(page.locator("#customProfileStatus")).to_have_text("已保存")

    event = page.locator("#customEventForm")
    event.locator('[name="date"]').fill("2025-01-10")
    event.locator('button[type="submit"]').click()
    expect(page.locator("#customTimeline .timeline-fact")).to_have_count(1)

    page.locator('[data-section="actions"]').click()
    expect(page.locator("#customActionsSection")).to_be_visible()
    expect(page.locator("#customActionContext h2")).to_have_text("行动工作台")
    assert page.locator("#customActionsSection h2", has_text="行动工作台").count() == 1

    finance = page.locator("#customFinanceForm")
    finance.locator('[name="target"]').fill("3000000")
    finance.locator('[name="cash"]').fill("600000")
    finance.locator('[name="burn"]').fill("100000")
    finance.locator('[name="purpose"]').fill("产品研发与团队招聘")
    finance.locator('button[type="submit"]').click()
    expect(page.locator("#customFinanceStatus")).to_have_text("融资准备已保存")
    expect(page.locator("#customRunway")).to_contain_text("6.0 个月")

    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    browser.close()
    print("Custom company path, mode switching, action workspace and financing plan passed.")
