import argparse
import os
import subprocess
import time
from typing import Optional

import requests


TARGETS = {
    "batdongsan": "https://batdongsan.com.vn/nha-dat-ban",
    "alonhadat": "https://alonhadat.com.vn/nha-dat/can-ban.html",
}


def cdp_endpoint_url(cli_value: Optional[str] = None) -> Optional[str]:
    if cli_value:
        return cli_value
    for env_name in [
        "CLOAKBROWSER_CDP_URL",
        "CLOAK_BROWSER_CDP_URL",
        "REAL_ESTATE_CDP_URL",
        "PLAYWRIGHT_CDP_URL",
    ]:
        value = os.environ.get(env_name)
        if value:
            print(f"[*] Using CDP endpoint from {env_name}: {value}")
            return value
    return os.environ.get("CLOAKBROWSER_DEFAULT_CDP_URL", "http://127.0.0.1:9222")


def is_cloakbrowser_cdp(endpoint_url: Optional[str]) -> bool:
    return bool(endpoint_url and (
        os.environ.get("CLOAKBROWSER_CDP_URL")
        or os.environ.get("CLOAK_BROWSER_CDP_URL")
        or "127.0.0.1:9222" in endpoint_url.lower()
        or "localhost:9222" in endpoint_url.lower()
        or "cloak" in endpoint_url.lower()
    ))


def cdp_version_url(endpoint_url: Optional[str]) -> Optional[str]:
    if not endpoint_url:
        return None
    endpoint = endpoint_url.strip()
    if endpoint.startswith("ws://"):
        endpoint = "http://" + endpoint[len("ws://"):]
    elif endpoint.startswith("wss://"):
        endpoint = "https://" + endpoint[len("wss://"):]
    if not endpoint.startswith(("http://", "https://")):
        return None
    base = endpoint.split("?", 1)[0]
    if "/devtools/" in base:
        base = base.split("/devtools/", 1)[0]
    return base.rstrip("/") + "/json/version"


def check_cdp_endpoint(endpoint_url: Optional[str]) -> Optional[str]:
    version_url = cdp_version_url(endpoint_url)
    if not version_url:
        return None
    try:
        response = requests.get(version_url, timeout=3)
        response.raise_for_status()
        payload = response.json()
        if payload.get("webSocketDebuggerUrl") or payload.get("Browser"):
            return None
        return f"CDP endpoint responded but did not expose a browser debugger at {version_url}"
    except Exception as e:
        return (
            f"Cloak Browser CDP is not reachable at {endpoint_url}.\n"
            f"Open Cloak Browser with remote debugging port 9222, then verify:\n"
            f"  curl {version_url}\n"
            f"Details: {e}"
        )


def local_cdp_browser_exe() -> Optional[str]:
    configured = os.environ.get("CLOAKBROWSER_EXE") or os.environ.get("REAL_ESTATE_BROWSER_EXE")
    candidates = [
        configured,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def local_cdp_profile_dir() -> str:
    return os.environ.get(
        "REAL_ESTATE_CDP_PROFILE_DIR",
        os.path.join(os.path.dirname(__file__), "cdp_browser_profile"),
    )


def start_local_cdp_browser(endpoint_url: Optional[str], start_url: str) -> bool:
    endpoint = (endpoint_url or "").lower()
    if "127.0.0.1:9222" not in endpoint and "localhost:9222" not in endpoint:
        return False

    browser_exe = local_cdp_browser_exe()
    if not browser_exe:
        print(
            "[-] Cannot auto-start CDP browser because Chrome/Cloak executable was not found. "
            "Set CLOAKBROWSER_EXE or REAL_ESTATE_BROWSER_EXE to the browser path."
        )
        return False

    profile_dir = local_cdp_profile_dir()
    os.makedirs(profile_dir, exist_ok=True)
    args = [
        browser_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--new-window",
        start_url,
    ]
    try:
        print(f"[*] Starting local CDP browser on 127.0.0.1:9222: {browser_exe}")
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
        for _ in range(10):
            time.sleep(1)
            if not check_cdp_endpoint(endpoint_url):
                print("[+] Local CDP browser is ready at http://127.0.0.1:9222")
                return True
    except Exception as e:
        print(f"[-] Could not auto-start local CDP browser: {e}")
        return False

    print("[-] Local CDP browser was started but 127.0.0.1:9222 did not become ready.")
    return False


def ensure_cdp_endpoint(endpoint_url: Optional[str], start_url: str) -> Optional[str]:
    cdp_error = check_cdp_endpoint(endpoint_url)
    if not cdp_error:
        return None
    print(f"[-] {cdp_error}")
    if start_local_cdp_browser(endpoint_url, start_url):
        return check_cdp_endpoint(endpoint_url)
    return cdp_error


def refresh_session(source: str, cdp_url: Optional[str] = None) -> None:
    source_key = source.lower()
    if source_key not in TARGETS:
        raise ValueError(f"Unknown source '{source}'. Use one of: {', '.join(TARGETS)}")

    os.makedirs("sessions", exist_ok=True)
    session_file = f"sessions/crawler_session_{source_key}.json"
    url = TARGETS[source_key]

    context_args = {
        "viewport": {"width": 1920, "height": 1080},
        "locale": "vi-VN",
        "timezone_id": "Asia/Ho_Chi_Minh",
    }
    if os.path.exists(session_file):
        context_args["storage_state"] = session_file

    endpoint_url = cdp_endpoint_url(cdp_url)
    connected_browser = bool(endpoint_url)
    cdp_error = ensure_cdp_endpoint(endpoint_url, url) if connected_browser else None
    if cdp_error and is_cloakbrowser_cdp(endpoint_url):
        raise RuntimeError(cdp_error)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        if connected_browser:
            print(f"[*] Connecting to Cloak/remote browser over CDP: {endpoint_url}")
            browser = p.chromium.connect_over_cdp(endpoint_url)
            if is_cloakbrowser_cdp(endpoint_url) and browser.contexts:
                print("[*] Using existing Cloak Browser profile context")
                context = browser.contexts[0]
            else:
                context = browser.new_context(**context_args)
        else:
            browser = p.chromium.launch(headless=False, slow_mo=50)
            context = browser.new_context(**context_args)

        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("=" * 72)
        print(f"Opened {url}")
        print("Complete Cloudflare/captcha/login in the browser window if it appears.")
        print("When the listing page is visible, return here and press Enter.")
        print("=" * 72)
        input()

        context.storage_state(path=session_file)
        print(f"[+] Saved refreshed session to {session_file}")

        if not (connected_browser and is_cloakbrowser_cdp(endpoint_url)):
            context.close()
        if not connected_browser:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Playwright session for real-estate crawlers.")
    parser.add_argument(
        "source",
        nargs="?",
        default="batdongsan",
        choices=sorted(TARGETS),
        help="Real-estate source to refresh",
    )
    parser.add_argument(
        "--cdp-url",
        help="Cloak Browser CDP endpoint, for example http://127.0.0.1:9222 or ws://127.0.0.1:9222/devtools/browser/...",
    )
    args = parser.parse_args()
    refresh_session(args.source, args.cdp_url)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[-] {e}")
        raise SystemExit(1)
