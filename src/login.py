import time
from playwright.sync_api import sync_playwright
from src.config import (
    SESSION_FILE,
    X_USERNAME,
    X_PASSWORD,
    X_EMAIL
)

def verify_logged_in(page):
    """Checks if the browser is logged in to X."""
    try:
        # AppTabBar_Home_Link is the testid for X Home link in the sidebar
        page.wait_for_selector('a[href="/home"], [data-testid="AppTabBar_Home_Link"]', timeout=8000)
        return True
    except:
        return False

def run_login_manual():
    """Manual login flow where the user enters credentials in the browser."""
    print("\n--- Manual Login Flow ---")
    print("Opening browser. Please log in manually...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(120000)
        
        page.goto("https://x.com/login", wait_until="domcontentloaded")
        
        while True:
            input("\nAfter you have successfully logged in and can see your Home timeline, press ENTER here...")
            if verify_logged_in(page):
                SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(SESSION_FILE))
                print(f"Success! Session saved to: {SESSION_FILE}")
                break
            else:
                print("Could not verify login. Please make sure you are logged in to X and can see your home timeline.")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    print("Login aborted.")
                    break
        
        browser.close()

def run_login_auto():
    """Automated login flow using credentials from .env."""
    print("\n--- Automated Login Flow ---")
    if not X_USERNAME or not X_PASSWORD:
        print("Error: X_USERNAME and X_PASSWORD must be configured in .env file for automated login.")
        print("Please check your .env file or run with --manual.")
        return

    print(f"Logging in as username: {X_USERNAME}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Must be visible in case of CAPTCHA/email check
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(45000)
        
        try:
            page.goto("https://x.com/login", wait_until="domcontentloaded")
            time.sleep(3)
            
            # 1. Fill Username/Phone/Email field
            username_field = page.locator('input[autocomplete="username"], input[name="text"]')
            username_field.wait_for(state="visible", timeout=15000)
            username_field.fill(X_USERNAME)
            
            # Click Next
            next_button = page.locator('button:has-text("Next"), div[role="button"]:has-text("Next")')
            next_button.click()
            time.sleep(3)
            
            # 2. Check for secondary verification check (email or phone prompt)
            # Sometimes X asks "Enter your phone number or email address"
            if page.locator('text="Enter your phone number or email address"').count() > 0 or \
               page.locator('input[name="text"]').count() > 0 and not page.locator('input[name="password"]').count():
                print("X requested email/phone verification check. Filling email...")
                if not X_EMAIL:
                    print("Error: X_EMAIL is required in .env for verification prompt.")
                    input("Please fill it in manually in the browser, click Next, then press ENTER here to continue...")
                else:
                    verify_field = page.locator('input[name="text"]')
                    verify_field.fill(X_EMAIL)
                    next_button = page.locator('button:has-text("Next"), div[role="button"]:has-text("Next")')
                    next_button.click()
                    time.sleep(3)
            
            # 3. Fill Password
            password_field = page.locator('input[name="password"]')
            password_field.wait_for(state="visible", timeout=10000)
            password_field.fill(X_PASSWORD)
            
            # Click Log In
            login_button = page.locator('button:has-text("Log in"), div[role="button"]:has-text("Log in")')
            login_button.click()
            time.sleep(5)
            
            # 4. CAPTCHA detection
            # If we are not logged in and there's a captcha iframe or wait element
            if not verify_logged_in(page):
                print("\nVerification check required (CAPTCHA, rate limit, or security challenge).")
                print("Please complete any challenges/CAPTCHAs directly in the opened browser window.")
                input("Once you see your Home timeline, press ENTER here in the terminal to save your session...")
            
            # 5. Save session
            if verify_logged_in(page):
                SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(SESSION_FILE))
                print(f"Success! Session saved to: {SESSION_FILE}")
            else:
                print("Could not verify login. Session was not saved.")
                
        except Exception as e:
            print(f"An error occurred during automated login: {e}")
            print("Falling back to manual check...")
            input("If you managed to log in, press ENTER here to save the session...")
            if verify_logged_in(page):
                SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(SESSION_FILE))
                print(f"Success! Session saved to: {SESSION_FILE}")
            else:
                print("Could not verify login. Session was not saved.")
                
        finally:
            browser.close()
