from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # Increase timeout
    page.set_default_timeout(120000)

    # Use x.com instead of twitter.com
    page.goto("https://x.com/login", wait_until="domcontentloaded")

    print("Login manually in the browser...")
    input("After login press ENTER here...")

    context.storage_state(path="twitter_session.json")
    browser.close()

print("Session saved.")