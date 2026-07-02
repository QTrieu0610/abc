import os
import random
import time
import threading
from crawlers.config import DEFAULT_HEADERS

# Lock to prevent multiple concurrent Playwright instances from crashing on the same profile
browser_lock = threading.Lock()

def auto_solve_challenge(page):
    print("[*] Attempting auto-solve Cloudflare/Captcha...")
    try:
        iframes = page.locator('iframe').all()
        for iframe in iframes:
            if iframe.is_visible(timeout=1000):
                box = iframe.bounding_box()
                if box and box['width'] > 0 and box['height'] > 0:
                    x = box['x'] + 30
                    y = box['y'] + box['height'] / 2
                    print(f"[*] Found iframe. Moving mouse to ({x}, {y})")
                    page.mouse.move(x, y, steps=10)
                    page.wait_for_timeout(500)
                    page.mouse.click(x, y)
                    print("[+] Clicked inside iframe via coordinates!")
                    return
    except Exception:
        pass
        
    try:
        page.frame_locator('iframe').locator('input[type="checkbox"], .cb-c, body').first.click(timeout=3000)
        print("[+] Clicked Turnstile via frame_locator!")
        return
    except Exception:
        pass

    try:
        page.locator('.ctp-checkbox-label, #challenge-stage, input[type="checkbox"]').first.click(timeout=3000)
        print("[+] Clicked Turnstile via page locator!")
        return
    except Exception:
        pass

def fetch_html_with_playwright(url: str, profile_name: str = "default") -> str:
    """Thread-safe wrapper to fetch HTML."""
    with browser_lock:
        return _fetch_html_with_playwright_locked(url, profile_name)

def _fetch_html_with_playwright_locked(url: str, profile_name: str = "default") -> str:
    """Fetch HTML using CloakBrowser with humanize and specific profile."""
    profile_dir = os.path.abspath(f"browser_profiles/{profile_name}")
    os.makedirs(profile_dir, exist_ok=True)
    
    try:
        from cloakbrowser import launch_persistent_context
    except ImportError:
        print("[-] CloakBrowser not found. Please install it first.")
        return ""

    context = launch_persistent_context(
        user_data_dir=profile_dir,
        headless=True,
        humanize=True,
        stealth_args=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ],
        user_agent=DEFAULT_HEADERS["User-Agent"],
        viewport={"width": 1280, "height": 720},
        color_scheme="dark"
    )

    try:
        page = context.pages[0] if context.pages else context.new_page()
        
        # Enhanced anti-detect to bypass shadow blocks
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {},
            };
            Object.defineProperty(navigator, 'languages', {
                get: () => ['vi-VN', 'vi', 'en-US', 'en'],
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        # Navigate
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        # Check for Cloudflare / Captchas
        html = page.content()
        lower_html = html.lower()
        if "cloudflare" in lower_html or "just a moment" in lower_html or "captcha" in lower_html:
            print("[-] Detected protection! Engaging auto-solver...")
            page.wait_for_timeout(2000)
            auto_solve_challenge(page)
            page.wait_for_timeout(random.randint(3000, 5000))
            
        # Scroll to trigger lazy rendering
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(500)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Wait for table selector (up to 5s) to resolve CSR delays
        try:
            page.wait_for_selector("table", timeout=5000)
            print("[+] Found table selector in DOM!")
            page.wait_for_timeout(1000)  # Extra second to render dynamic content
        except Exception:
            print("[-] No table found in DOM within 5s, returning current content.")

        return page.content()
    finally:
        context.close()
