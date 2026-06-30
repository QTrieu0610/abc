import os
import json
import time
import requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from crawlers.config import DEFAULT_HEADERS
from crawlers.utils import source_result

class BaseCrawler:
    """
    Base crawler implementing the 3-Tier Fallback architecture:
    Tier 1: Fast HTTP Requests (with Warmed-up Identity) + Static Parser
    Tier 2: Cloak Browser (Playwright) + Static Parser
    Tier 3: Cloak Browser (Playwright) + AI LLM Parser
    """
    def __init__(self, url: str, profile_name: str = "default"):
        self.url = url
        self.profile_name = profile_name
        self.session_file = f"sessions/crawler_session_{self.profile_name}.json"
        
        # Load identity for Tier 1
        self.cookies_dict = self._load_session_cookies()
        self.headers = DEFAULT_HEADERS.copy()

    def _load_session_cookies(self) -> Dict[str, str]:
        cookies_dict = {}
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    state = json.load(f)
                    for cookie in state.get("cookies", []):
                        cookies_dict[cookie["name"]] = cookie["value"]
            except Exception as e:
                print(f"[-] Cannot read session file: {e}")
        return cookies_dict

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        """Override this method to implement static DOM parsing (BeautifulSoup)"""
        raise NotImplementedError()

    def _tier_3_ai_parse(self, html: str) -> Optional[List[Dict]]:
        """Override this method to implement AI LLM parsing"""
        raise NotImplementedError()

    def _detect_blocking_signals(self, html: str, status_code: int = 200) -> bool:
        """Override this method to detect Cloudflare/Captcha blocks"""
        if status_code in [403, 503, 429]:
            return True
        if not html:
            return True
        lower_html = html.lower()
        if "cloudflare" in lower_html or "captcha" in lower_html or "just a moment" in lower_html:
            return True
        return False

    def _fetch_tier_1_http(self) -> Optional[str]:
        """Tier 1: Fast HTTP Request using warmed-up cookies"""
        try:
            print(f"[*] Tier 1: Fetching via HTTP Request (Identity: {self.profile_name}) -> {self.url}")
            session = requests.Session()
            session.cookies.update(self.cookies_dict)
            response = session.get(self.url, headers=self.headers, timeout=10)
            html = response.text
            if self._detect_blocking_signals(html, response.status_code):
                print("[-] Tier 1 Blocked (Cloudflare/Captcha detected).")
                return None
            return html
        except Exception as e:
            print(f"[-] Tier 1 Request failed: {e}")
            return None

    def _fetch_tier_2_and_3_browser(self) -> Optional[str]:
        """Tier 2 & 3: Playwright Cloak Browser Fetch"""
        from .browser import fetch_html_with_playwright
        print(f"[*] Tier 2/3: Fetching via Cloak Browser -> {self.url}")
        return fetch_html_with_playwright(self.url, self.profile_name)

    def execute(self) -> Dict:
        """Executes the 3-Tier Fallback Strategy"""
        # Tier 1
        html = self._fetch_tier_1_http()
        if html:
            print("[+] Tier 1 HTTP success. Applying Static Parser...")
            try:
                results = self._tier_1_static_parse(html)
                if results:
                    return source_result("success", results=results)
            except Exception as e:
                print(f"[-] Tier 1 Static Parse failed: {e}")

        # Tier 2
        html = self._fetch_tier_2_and_3_browser()
        if not html:
            return source_result("error", error="All tiers failed to fetch HTML")

        print("[+] Tier 2 Browser fetch success. Applying Static Parser...")
        try:
            results = self._tier_1_static_parse(html)
            if results:
                return source_result("success", results=results)
        except Exception as e:
            print(f"[-] Tier 2 Static Parse failed: {e}")

        # Tier 3
        print("[-] Static Parser failed. Falling back to Tier 3 AI Parser...")
        try:
            results = self._tier_3_ai_parse(html)
            if results:
                return source_result("success", results=results)
            return source_result("error", error="AI parsing returned empty data")
        except Exception as e:
            return source_result("error", error=f"AI Parse failed: {e}")
