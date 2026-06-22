import json
import os
import random
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _load_env_file():
    """Load .env from this project without requiring python-dotenv."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
            return
        except Exception as e:
            print(f"[-] Cannot load .env file {path}: {e}")


_load_env_file()


def clean_price(price_str: Optional[str]) -> Optional[int]:
    """Normalize Vietnamese gold prices to VND per chi."""
    if not price_str:
        return None

    cleaned = re.sub(r"[^\d]", "", str(price_str))
    if not cleaned:
        return None

    value = int(cleaned)
    if value < 100000:
        value *= 1000
    return value


def clean_real_estate_price(price_str: Optional[str]) -> Optional[int]:
    """Normalize Vietnamese real-estate prices to VND."""
    if not price_str:
        return None

    value = str(price_str).lower().strip()
    value = value.replace(",", ".")
    if any(token in value for token in ["thỏa thuận", "thoả thuận", "liên hệ", "lien he"]):
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", value)
    if not match:
        return None

    amount = float(match.group(1))
    if "tỷ" in value or "ty" in value:
        amount *= 1_000_000_000
    elif "triệu" in value or "trieu" in value:
        amount *= 1_000_000
    elif "nghìn" in value or "ngan" in value or "ngàn" in value:
        amount *= 1_000

    return int(amount)


def clean_area_m2(area_str: Optional[str]) -> Optional[float]:
    """Extract a square-meter value from Vietnamese real-estate text."""
    if not area_str:
        return None

    value = str(area_str).lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m2|m²|m\s*2)", value)
    if not match:
        return None
    return float(match.group(1))


def source_result(status: str, results: Optional[List[Dict]] = None, error: Optional[str] = None) -> Dict:
    return {
        "status": status,
        "results": results or [],
        "error": error,
    }


class GoldCrawler:
    """
    Unified crawler for Gold prices from multiple sources: SJC (WebGia), DOJI, and PNJ.
    """

    # DOJI static constants
    AREA_MAP_DOJI = {
        "ha noi": "Hanoi",
        "hà nội": "Hanoi",
        "da nang": "Da Nang",
        "đà nẵng": "Da Nang",
        "ho chi minh": "Ho Chi Minh City",
        "hồ chí minh": "Ho Chi Minh City",
    }

    GOLD_TYPE_PATTERNS_DOJI = [
        ("SJC - Bán Lẻ", ["sjc"]),
        ("AVPL / Kim TT", ["avpl", "kim tt", "kim"]),
        ("Nhẫn Tròn 9999", ["nhan tron", "nhẫn tròn", "hung thinh", "hưng thịnh"]),
        ("Nữ trang 99.99", ["99.99", "9999"]),
        ("Nữ trang 99.9", ["99.9", "999"]),
        ("Nữ trang 99", ["99 -", " 99 "]),
    ]

    # PNJ static constants
    PRIMARY_API_PNJ = "https://edge-cf-api.pnj.io"
    FALLBACK_API_PNJ = "https://edge-api.pnj.io"
    ENDPOINT_PNJ = "/ecom-frontend/v1/get-gold-price?zone={zone}"
    PAGE_URL_PNJ = "https://www.pnj.com.vn/site/gia-vang"

    ZONES_PNJ = {
        "00": "Ho Chi Minh City",
        "07": "Can Tho",
        "11": "Hanoi",
        "13": "Da Nang",
        "14": "Tay Nguyen",
        "21": "Dong Nam Bo",
    }

    def __init__(self, source: str, use_ai_fallback: bool = True, profile_name: str = "gold"):
        self.source = source.lower()
        self.use_ai_fallback = use_ai_fallback
        self.profile_name = profile_name

        os.makedirs("sessions", exist_ok=True)
        self.session_file = f"sessions/crawler_session_{self.profile_name}.json"

        if self.source in ["sjc", "webgia"]:
            self.target_url = "https://webgia.com/gia-vang/sjc/"
            self.headers = DEFAULT_HEADERS.copy()
            self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
            self.openai_api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
            self.ai_model = os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_FALLBACK_MODEL") or "gemma4:e2b"
            self.openai_verify_ssl = os.environ.get("OPENAI_VERIFY_SSL", "true").lower() not in ["0", "false", "no"]
            self.max_retries = 3
            self.proxies = [None]
            self.credentials = {
                "username": os.environ.get("GOLD_SITE_USER", "default_user"),
                "password": os.environ.get("GOLD_SITE_PASS", "default_pass"),
            }
        elif self.source == "doji":
            self.target_url = "https://giavang.doji.vn/"
            self.headers = DEFAULT_HEADERS.copy()
            self.max_retries = 2
            self.credentials = {
                "username": os.environ.get("DOJI_SITE_USER", "default_user"),
                "password": os.environ.get("DOJI_SITE_PASS", "default_pass"),
            }
        elif self.source == "pnj":
            self.headers = {
                **DEFAULT_HEADERS,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.pnj.com.vn",
                "Referer": self.PAGE_URL_PNJ,
            }
            self.max_retries = 2
            self.credentials = {
                "username": os.environ.get("PNJ_SITE_USER", "default_user"),
                "password": os.environ.get("PNJ_SITE_PASS", "default_pass"),
            }
        else:
            raise ValueError(f"Unknown source: {self.source}")

    # === SJC (WebGia) Helpers ===
    def _get_cookies_from_session_sjc(self):
        cookies_dict = {}
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    for cookie in state.get("cookies", []):
                        cookies_dict[cookie["name"]] = cookie["value"]
            except Exception as e:
                print(f"[-] Cannot read session file: {e}")
        return cookies_dict

    def _clean_price_sjc(self, price_str):
        return clean_price(price_str)

    def _tier_1_static_parse_sjc(self, html):
        print("[*] Applying WebGia static parser...")
        soup = BeautifulSoup(html or "", "html.parser")
        result = {}

        table = soup.find("table", class_="table-gia-vang")
        if not table:
            for candidate in soup.find_all("table"):
                header_text = candidate.get_text(" ", strip=True).lower()
                if "loại vàng" in header_text and "mua vào" in header_text and "bán ra" in header_text:
                    table = candidate
                    break
        if not table:
            return None

        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            if len(cols) >= 4:
                name_index, buy_index, sell_index = 1, 2, 3
            else:
                name_index, buy_index, sell_index = 0, 1, 2

            name = cols[name_index].get_text(" ", strip=True).lower()
            buy = self._clean_price_sjc(cols[buy_index].get_text(" ", strip=True))
            sell = self._clean_price_sjc(cols[sell_index].get_text(" ", strip=True))

            if buy is None and sell is None:
                continue

            if "1l" in name or "mieng" in name or "miếng" in name:
                if "buy_1l" not in result:
                    result["buy_1l"] = buy
                    result["sell_1l"] = sell
            elif "nhan" in name or "nhẫn" in name:
                if "buy_nhan1c" not in result:
                    result["buy_nhan1c"] = buy
                    result["sell_nhan1c"] = sell
            elif ("nu trang" in name or "nữ trang" in name) and ("99,99" in name or "9999" in name):
                result["buy_nutrang_9999"] = buy
                result["sell_nutrang_9999"] = sell
            elif ("nu trang" in name or "nữ trang" in name) and "99" in name:
                result["buy_nutrang_99"] = buy
                result["sell_nutrang_99"] = sell
            elif ("nu trang" in name or "nữ trang" in name) and ("75" in name or "18k" in name):
                result["buy_nutrang_75"] = buy
                result["sell_nutrang_75"] = sell

        if "buy_1l" not in result:
            return None

        print("[+] WebGia static parser succeeded")
        return result

    def _tier_2_ai_fallback_sjc(self, html):
        print("[!] WebGia static parse failed. Trying LLM API fallback...")
        from bs4 import Comment

        soup = BeautifulSoup(html or "", "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        clean_text = " ".join(soup.stripped_strings)
        sjc_idx = clean_text.lower().find("sjc")
        if sjc_idx != -1:
            clean_text = clean_text[max(0, sjc_idx - 500): min(len(clean_text), sjc_idx + 1500)]
        else:
            clean_text = clean_text[:2000]

        prompt = f"""Extract today's SJC gold buy/sell prices from this Vietnamese text.
Return JSON only. Normalize all values to VND per chi.

Expected keys:
{{
  "buy_1l": 0, "sell_1l": 0,
  "buy_nhan1c": 0, "sell_nhan1c": 0,
  "buy_nutrang_9999": 0, "sell_nutrang_9999": 0,
  "buy_nutrang_99": 0, "sell_nutrang_99": 0,
  "buy_nutrang_75": 0, "sell_nutrang_75": 0
}}

Text:
{clean_text}"""

        try:
            headers = {
                "Content-Type": "application/json",
            }
            if self.openai_api_key:
                headers["Authorization"] = f"Bearer {self.openai_api_key}"
            payload = {
                "model": self.ai_model,
                "prompt": prompt,
                "system": "Return valid JSON only. Do not include markdown fences.",
                "format": "json",
                "stream": False,
            }
            response = requests.post(
                self.ollama_url,
                headers=headers,
                json=payload,
                verify=self.openai_verify_ssl,
                timeout=120,
            )
            if response.status_code == 200:
                content = response.json().get("response", "")
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content)
                return json.loads(content)
            print(f"[-] Ollama API error: {response.status_code} {response.text}")
            return None
        except Exception as e:
            print(f"[-] LLM API unavailable: {e}")
            return None

    def _detect_blocking_signals_sjc(self, html, status_code=200):
        if status_code in [403, 429, 503]:
            return True
        if not html:
            return True
        html_lower = html.lower()
        signals = [
            "please verify you are a human", "checking your browser before accessing", "access denied", 
            "please complete the captcha", "security check", 
            "2-step verification", "enter the otp", "two-factor authentication", "device verification"
        ]
        
        for signal in signals:
            if signal in html_lower:
                print(f"[*] Suspected blocking signal detected: '{signal}'")
                return True
                
        return False

    def _simulate_human_behavior_sjc(self, page):
        page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        page.wait_for_timeout(random.randint(500, 1500))
        page.mouse.wheel(0, random.randint(300, 800))
        page.wait_for_timeout(random.randint(1000, 2000))

    def _handle_login_sjc(self, page):
        try:
            if page.locator("input[type='password']").is_visible(timeout=2000):
                print("[!] Login requested. Filling security credentials...")
                page.locator("input[type='text'], input[name='username'], input[type='email']").first.fill(
                    self.credentials["username"]
                )
                page.wait_for_timeout(random.randint(300, 800))
                page.locator("input[type='password']").fill(self.credentials["password"])
                page.keyboard.press("Enter")
                print("[*] Clicked Login, waiting for response...")
                page.wait_for_timeout(5000) # Wait 5s for page transition
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except:
                    pass
                
                # Check for MFA / OTP after login
                if page.locator("input[name*='otp'], input[name*='code'], input[id*='otp'], text='MFA', text='OTP', input[placeholder*='OTP']").is_visible(timeout=3000):
                    print("[-] MFA/OTP verification required! Please complete in browser...")
        except Exception as e:
            pass

    def _browser_fetch_sjc(self):
        print("[!] Starting Playwright fallback for WebGia...")
        try:
            from playwright.sync_api import sync_playwright

            mcp_token = os.environ.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN", "")

            with sync_playwright() as p:
                browser = None
                context = None
                launched_browser = False

                try:
                    endpoint_url = f"ws://localhost:9222?token={mcp_token}" if mcp_token else "ws://localhost:9222"
                    browser = p.chromium.connect_over_cdp(endpoint_url)
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                except Exception:
                    print("[*] Opening new headful browser for observation...")
                    browser = p.chromium.launch(headless=False, slow_mo=50)
                    launched_browser = True
                    context_args = {
                        "user_agent": self.headers["User-Agent"],
                        "viewport": {"width": 1920, "height": 1080},
                    }
                    if os.path.exists(self.session_file):
                        context_args["storage_state"] = self.session_file
                    context = browser.new_context(**context_args)

                page = context.new_page()
                page.goto(self.target_url, wait_until="domcontentloaded", timeout=30000)
                self._simulate_human_behavior_sjc(page)
                self._handle_login_sjc(page)
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                try:
                    html = page.content()
                except Exception as e:
                    if "navigating" in str(e).lower():
                        print("[*] Waiting for page load completion...")
                        page.wait_for_load_state("networkidle", timeout=10000)
                        html = page.content()
                    else:
                        raise e

                # Đợi con người giải quyết Captcha/MFA
                while self._detect_blocking_signals_sjc(html):
                    print("[-] BLOCKED (MFA/Captcha)! Bot paused...")
                    print("[*] Solve Captcha/MFA in browser window. Bot will retry in 5s...")
                    page.wait_for_timeout(5000)
                    try:
                        html = page.content()
                    except:
                        pass

                context.storage_state(path=self.session_file)
                page.close()
                if launched_browser:
                    browser.close()
                return html
        except ImportError:
            print("[-] Playwright is not installed")
            return None
        except Exception as e:
            print(f"[-] Playwright fallback failed: {e}")
            return None

    def _browser_fetch_doji(self):
        print("[!] Starting Playwright fallback for DOJI...")
        try:
            from playwright.sync_api import sync_playwright

            mcp_token = os.environ.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN", "")

            with sync_playwright() as p:
                browser = None
                context = None
                launched_browser = False

                try:
                    endpoint_url = f"ws://localhost:9222?token={mcp_token}" if mcp_token else "ws://localhost:9222"
                    browser = p.chromium.connect_over_cdp(endpoint_url)
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                except Exception:
                    print("[*] Opening new headful browser for observation...")
                    browser = p.chromium.launch(headless=False, slow_mo=50)
                    launched_browser = True
                    context_args = {
                        "user_agent": self.headers["User-Agent"],
                        "viewport": {"width": 1920, "height": 1080},
                    }
                    if os.path.exists(self.session_file):
                        context_args["storage_state"] = self.session_file
                    context = browser.new_context(**context_args)

                page = context.new_page()
                page.goto(self.target_url, wait_until="domcontentloaded", timeout=30000)
                self._simulate_human_behavior_sjc(page)
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                try:
                    html = page.content()
                except Exception as e:
                    if "navigating" in str(e).lower():
                        print("[*] Waiting for page load completion...")
                        page.wait_for_load_state("networkidle", timeout=10000)
                        html = page.content()
                    else:
                        raise e

                # Đợi con người giải quyết Captcha/MFA
                while self._detect_blocking_signals_doji(html):
                    print("[-] BLOCKED (MFA/Captcha)! Bot paused...")
                    print("[*] Solve Captcha/MFA in browser window. Bot will retry in 5s...")
                    page.wait_for_timeout(5000)
                    try:
                        html = page.content()
                    except:
                        pass

                context.storage_state(path=self.session_file)
                page.close()
                if launched_browser:
                    browser.close()
                return html
        except ImportError:
            print("[-] Playwright is not installed")
            return None
        except Exception as e:
            print(f"[-] Playwright fallback failed for DOJI: {e}")
            return None

    def _execute_crawling_sjc(self):
        print(f"[*] Crawling WebGia SJC: {self.target_url}")

        for attempt in range(1, self.max_retries + 1):
            try:
                proxy = random.choice(self.proxies)
                proxies_dict = {"http": proxy, "https": proxy} if proxy else None
                cookies = self._get_cookies_from_session_sjc()

                response = requests.get(
                    self.target_url,
                    headers=self.headers,
                    cookies=cookies,
                    proxies=proxies_dict,
                    timeout=10,
                )

                if self._detect_blocking_signals_sjc(response.text, response.status_code):
                    html = self._browser_fetch_sjc()
                else:
                    html = response.text

                data = self._tier_1_static_parse_sjc(html)
                if data is None and self.use_ai_fallback:
                    data = self._tier_2_ai_fallback_sjc(html)

                if data:
                    data["datetime"] = int(datetime.now().timestamp())
                    return {"sjc": source_result("ok", [data])}

                raise Exception("Could not parse WebGia SJC prices")
            except Exception as e:
                print(f"[-] WebGia SJC attempt {attempt}/{self.max_retries} failed: {e}")
                if "HITL_REQUIRED" in str(e):
                    print(f"[!!!] Human review (HITL) required. Stopping retries! Error: {e}")
                    return {"sjc": source_result("failed", [], str(e))}
                    
                if attempt < self.max_retries:
                    time.sleep(attempt * random.randint(3, 7))
                else:
                    return {"sjc": source_result("failed", [], str(e))}

    # === DOJI Helpers ===
    def _normalize_text_doji(self, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip().lower()

    def _map_gold_type_doji(self, raw_name: str) -> Optional[str]:
        normalized = self._normalize_text_doji(raw_name)
        for gold_type, patterns in self.GOLD_TYPE_PATTERNS_DOJI:
            if any(pattern in normalized for pattern in patterns):
                return gold_type
        return None

    def _looks_like_price_doji(self, value: str) -> bool:
        return clean_price(value) is not None

    def _parse_rows_from_text_doji(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html or "", "html.parser")
        text = soup.get_text("\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        records = []
        current_location = None
        timestamp = int(datetime.now().timestamp())

        for line in lines:
            lower = self._normalize_text_doji(line)
            if "bang gia tai" in lower or "bảng giá tại" in lower:
                current_location = None
                for marker, location in self.AREA_MAP_DOJI.items():
                    if marker in lower:
                        current_location = location
                        break
                continue

            if current_location is None:
                continue

            match = re.match(r"(.+?)\s+([\d,.]+)\s+([\d,.]+)$", line)
            if not match:
                continue

            raw_name, raw_buy, raw_sell = match.groups()
            gold_type = self._map_gold_type_doji(raw_name)
            buy = clean_price(raw_buy)
            sell = clean_price(raw_sell)

            if not gold_type or buy is None or sell is None:
                continue

            records.append({
                "datetime": timestamp,
                "company": "DOJI",
                "gold_type": gold_type,
                "buy_price": buy,
                "sell_price": sell,
                "location": current_location,
                "source": self.target_url,
            })

        return records

    def _parse_rows_from_tables_doji(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html or "", "html.parser")
        records = []
        timestamp = int(datetime.now().timestamp())

        for table in soup.find_all("table"):
            location = None
            heading_text = ""
            previous = table.find_previous(["h1", "h2", "h3", "h4", "strong", "div"])
            if previous:
                heading_text = previous.get_text(" ", strip=True).lower()

            for marker, mapped in self.AREA_MAP_DOJI.items():
                if marker in heading_text:
                    location = mapped
                    break

            if not location:
                continue

            for row in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                if len(cells) < 3:
                    continue

                raw_name, raw_buy, raw_sell = cells[0], cells[1], cells[2]
                gold_type = self._map_gold_type_doji(raw_name)
                buy = clean_price(raw_buy)
                sell = clean_price(raw_sell)

                if not gold_type or buy is None or sell is None:
                    continue

                records.append({
                    "datetime": timestamp,
                    "company": "DOJI",
                    "gold_type": gold_type,
                    "buy_price": buy,
                    "sell_price": sell,
                    "location": location,
                    "source": self.target_url,
                })

        return records

    def _parse_doji(self, html: str) -> List[Dict]:
        records = self._parse_rows_from_tables_doji(html)
        if not records:
            records = self._parse_rows_from_text_doji(html)

        unique = {}
        for record in records:
            key = (record["location"], record["gold_type"])
            unique[key] = record
        return list(unique.values())

    def _detect_blocking_signals_doji(self, html, status_code=200):
        if status_code in [403, 429, 503]:
            return True
        if not html:
            return True
        html_lower = html.lower()
        signals = [
            "please verify you are a human", "checking your browser before accessing", "access denied", 
            "please complete the captcha", "security check", 
            "2-step verification", "enter the otp", "two-factor authentication", "device verification"
        ]
        for signal in signals:
            if signal in html_lower:
                return True
        return False

    def _execute_crawling_doji(self):
        print(f"[*] Crawling DOJI: {self.target_url}")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.target_url, headers=self.headers, timeout=15)
                
                if response.status_code != 200 or self._detect_blocking_signals_doji(response.text, response.status_code):
                    html = self._browser_fetch_doji()
                else:
                    html = response.text

                records = self._parse_doji(html)

                if not records:
                    raise Exception("Could not parse DOJI prices")

                print(f"[+] DOJI parser collected {len(records)} rows")
                return {"doji": source_result("ok", records)}
            except Exception as e:
                print(f"[-] DOJI attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    return {"doji": source_result("failed", [], str(e))}

    # === PNJ Helpers ===
    def _normalize_api_price_pnj(self, value) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return clean_price(str(value))
        if numeric <= 0:
            return None
        if numeric < 100000:
            numeric *= 1000
        return int(numeric)

    def _fetch_zone_from_domain_pnj(self, domain: str, zone: str) -> Dict:
        url = domain + self.ENDPOINT_PNJ.format(zone=zone)
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def _fetch_zone_pnj(self, zone: str) -> Dict:
        last_error = None
        for domain in [self.PRIMARY_API_PNJ, self.FALLBACK_API_PNJ]:
            try:
                return self._fetch_zone_from_domain_pnj(domain, zone)
            except Exception as e:
                last_error = e
                print(f"[-] PNJ API failed for zone {zone} on {domain}: {e}")
        raise last_error or Exception(f"PNJ API failed for zone {zone}")

    def _parse_api_data_pnj(self, zone: str, payload: Dict) -> List[Dict]:
        records = []
        timestamp = int(datetime.now().timestamp())
        location = self.ZONES_PNJ.get(zone, zone)

        for item in payload.get("data") or []:
            gold_type = item.get("tensp") or item.get("name") or item.get("masp")
            buy = self._normalize_api_price_pnj(item.get("giamua"))
            sell = self._normalize_api_price_pnj(item.get("giaban"))

            if not gold_type or (buy is None and sell is None):
                continue

            records.append({
                "datetime": timestamp,
                "company": "PNJ",
                "gold_type": gold_type,
                "buy_price": buy,
                "sell_price": sell,
                "location": location,
                "source": self.PAGE_URL_PNJ,
            })

        return records

    def _browser_fetch_pnj(self) -> List[Dict]:
        """Fallback for cases where the PNJ API domains reject direct requests."""
        print("[!] Starting Playwright fallback for PNJ...")
        records = []
        try:
            from playwright.sync_api import sync_playwright

            mcp_token = os.environ.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN", "")

            with sync_playwright() as p:
                browser = None
                context = None
                launched_browser = False

                try:
                    endpoint_url = f"ws://localhost:9222?token={mcp_token}" if mcp_token else "ws://localhost:9222"
                    browser = p.chromium.connect_over_cdp(endpoint_url)
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                except Exception:
                    print("[*] Opening new headful browser for observation...")
                    browser = p.chromium.launch(headless=False, slow_mo=50)
                    launched_browser = True
                    context_args = {
                        "user_agent": self.headers["User-Agent"],
                        "viewport": {"width": 1440, "height": 1000},
                    }
                    if os.path.exists(self.session_file):
                        context_args["storage_state"] = self.session_file
                    context = browser.new_context(**context_args)

                page = context.new_page()
                page.goto(self.PAGE_URL_PNJ, wait_until="networkidle", timeout=45000)

                for zone, location in self.ZONES_PNJ.items():
                    try:
                        page.locator("#demo-simple-select-helper").click(timeout=5000)
                        page.wait_for_selector('li[role="option"]', timeout=5000)
                        page.locator(f'li[role="option"][data-value="{zone}"]').click(timeout=5000)
                    except Exception as select_err:
                        print(f"[-] Failed to select zone {zone} via MUI select: {select_err}")
                        try:
                            page.locator("select").first.select_option(zone, timeout=2000)
                        except:
                            continue
                    page.wait_for_timeout(1200)
                    text = page.locator("body").first.inner_text(timeout=10000)
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    timestamp = int(datetime.now().timestamp())

                    for index, line in enumerate(lines):
                        if not line.lower().startswith("vàng"):
                            continue
                        window = " ".join(lines[index:index + 6])
                        numbers = re.findall(r"\d{1,3}(?:[,.]\d{3})+|\d{4,6}", window)
                        if len(numbers) < 2:
                            continue
                        buy = self._normalize_api_price_pnj(numbers[0])
                        sell = self._normalize_api_price_pnj(numbers[1])
                        records.append({
                            "datetime": timestamp,
                            "company": "PNJ",
                            "gold_type": line,
                            "buy_price": buy,
                            "sell_price": sell,
                            "location": location,
                            "source": self.PAGE_URL_PNJ,
                        })

                context.storage_state(path=self.session_file)
                page.close()
                if launched_browser:
                    browser.close()
        except Exception as e:
            try:
                print(f"[-] PNJ Playwright fallback failed: {e}")
            except UnicodeEncodeError:
                print(f"[-] PNJ Playwright fallback failed: {repr(e)}")

        unique = {}
        for record in records:
            unique[(record["location"], record["gold_type"])] = record
        return list(unique.values())

    def _execute_crawling_pnj(self):
        print(f"[*] Crawling PNJ: {self.PAGE_URL_PNJ}")

        for attempt in range(1, self.max_retries + 1):
            try:
                records = []
                for zone in self.ZONES_PNJ:
                    payload = self._fetch_zone_pnj(zone)
                    records.extend(self._parse_api_data_pnj(zone, payload))

                if not records:
                    raise Exception("Could not parse PNJ prices")

                print(f"[+] PNJ parser collected {len(records)} rows")
                return {"pnj": source_result("ok", records)}
            except Exception as e:
                print(f"[-] PNJ attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(2)
                else:
                    records = self._browser_fetch_pnj()
                    if records:
                        print(f"[+] PNJ Playwright fallback collected {len(records)} rows")
                        return {"pnj": source_result("ok", records)}
                    return {"pnj": source_result("failed", [], str(e))}

    def execute_crawling(self):
        if self.source in ["sjc", "webgia"]:
            return self._execute_crawling_sjc()
        elif self.source == "doji":
            return self._execute_crawling_doji()
        elif self.source == "pnj":
            return self._execute_crawling_pnj()
        else:
            raise ValueError(f"Unknown source: {self.source}")


class SjcWebGiaCrawler(GoldCrawler):
    """
    Backward-compatible SjcWebGiaCrawler.
    """
    def __init__(self, use_ai_fallback: bool = True, profile_name: str = "gold"):
        super().__init__(source="sjc", use_ai_fallback=use_ai_fallback, profile_name=profile_name)

    def _get_cookies_from_session(self):
        return self._get_cookies_from_session_sjc()

    def _clean_price(self, price_str):
        return self._clean_price_sjc(price_str)

    def _tier_1_static_parse(self, html):
        return self._tier_1_static_parse_sjc(html)

    def _tier_2_ai_fallback(self, html):
        return self._tier_2_ai_fallback_sjc(html)

    def _detect_blocking_signals(self, html, status_code=200):
        return self._detect_blocking_signals_sjc(html, status_code)

    def _simulate_human_behavior(self, page):
        return self._simulate_human_behavior_sjc(page)

    def _handle_login(self, page):
        return self._handle_login_sjc(page)

    def _browser_fetch(self):
        return self._browser_fetch_sjc()


class DojiCrawler(GoldCrawler):
    """
    Backward-compatible DojiCrawler.
    """
    def __init__(self, profile_name: str = "doji"):
        super().__init__(source="doji", profile_name=profile_name)

    # DOJI static constants mapping
    AREA_MAP = GoldCrawler.AREA_MAP_DOJI
    GOLD_TYPE_PATTERNS = GoldCrawler.GOLD_TYPE_PATTERNS_DOJI

    def _normalize_text(self, value: str) -> str:
        return self._normalize_text_doji(value)

    def _map_gold_type(self, raw_name: str) -> Optional[str]:
        return self._map_gold_type_doji(raw_name)

    def _looks_like_price(self, value: str) -> bool:
        return self._looks_like_price_doji(value)

    def _parse_rows_from_text(self, html: str) -> List[Dict]:
        return self._parse_rows_from_text_doji(html)

    def _parse_rows_from_tables(self, html: str) -> List[Dict]:
        return self._parse_rows_from_tables_doji(html)

    def _parse(self, html: str) -> List[Dict]:
        return self._parse_doji(html)


class PnjCrawler(GoldCrawler):
    """
    Backward-compatible PnjCrawler.
    """
    def __init__(self, profile_name: str = "pnj"):
        super().__init__(source="pnj", profile_name=profile_name)

    # PNJ static constants mapping
    PRIMARY_API = GoldCrawler.PRIMARY_API_PNJ
    FALLBACK_API = GoldCrawler.FALLBACK_API_PNJ
    ENDPOINT = GoldCrawler.ENDPOINT_PNJ
    PAGE_URL = GoldCrawler.PAGE_URL_PNJ
    ZONES = GoldCrawler.ZONES_PNJ

    def _normalize_api_price(self, value) -> Optional[int]:
        return self._normalize_api_price_pnj(value)

    def _fetch_zone_from_domain(self, domain: str, zone: str) -> Dict:
        return self._fetch_zone_from_domain_pnj(domain, zone)

    def _fetch_zone(self, zone: str) -> Dict:
        return self._fetch_zone_pnj(zone)

    def _parse_api_data(self, zone: str, payload: Dict) -> List[Dict]:
        return self._parse_api_data_pnj(zone, payload)

    def _browser_fetch(self) -> List[Dict]:
        return self._browser_fetch_pnj()


class RealEstateCrawler:
    """
    Crawl Vietnamese real-estate listing pages and normalize listing data.

    The output mirrors the gold crawler contract:
    {source_name: {"status": "ok|failed", "results": [...], "error": None}}
    """

    DEFAULT_SOURCES = {
        "batdongsan": {
            "label": "Batdongsan",
            "url": "https://batdongsan.com.vn/nha-dat-ban",
        },
        "alonhadat": {
            "label": "AloNhaDat",
            "url": "https://alonhadat.com.vn/nha-dat/can-ban.html",
        },
    }

    LISTING_SELECTORS = [
        "[class*='js__card']",
        "[class*='product-item']",
        "[class*='re__card']",
        "[class*='listing']",
        "[class*='property']",
        "article",
    ]

    TITLE_SELECTORS = [
        "h1", "h2", "h3",
        "[class*='title']",
        "[class*='name']",
        "a[title]",
    ]

    PRICE_PATTERNS = [
        r"(?:giá|gia)\s*:?\s*([\d,.]+\s*(?:tỷ|ty|triệu|trieu|nghìn|ngàn|ngan))",
        r"([\d,.]+\s*(?:tỷ|ty|triệu|trieu|nghìn|ngàn|ngan)(?:\s*/\s*m2)?)",
        r"(thỏa thuận|thoả thuận|liên hệ|lien he)",
    ]

    LOCATION_HINTS = ["quận", "huyện", "thành phố", "tp.", "tỉnh", "phường", "xã", "đường"]

    def __init__(
        self,
        source: str = "batdongsan",
        target_url: Optional[str] = None,
        max_pages: int = 1,
        use_browser_fallback: bool = True,
    ):
        self.source = (source or "batdongsan").lower()
        self.max_pages = max(1, int(max_pages or 1))
        self.use_browser_fallback = use_browser_fallback
        source_config = self.DEFAULT_SOURCES.get(self.source, {})
        self.source_label = source_config.get("label", self.source.title())
        self.target_url = target_url or source_config.get("url")
        if not self.target_url:
            raise ValueError("Real-estate target URL is required for custom sources")
        self.headers = DEFAULT_HEADERS.copy()
        self.last_browser_error = None
        self.auto_started_cdp_browser = False
        self.auto_started_cdp_process = None
        
        # Save session file in the sessions directory
        os.makedirs("sessions", exist_ok=True)
        self.session_file = f"sessions/crawler_session_{self.source}.json"

    def _should_use_browser_first(self) -> bool:
        return self.source == "batdongsan" and self.use_browser_fallback

    def _browser_context_args(self) -> Dict:
        context_args = {
            "user_agent": self.headers["User-Agent"],
            "viewport": {"width": 1920, "height": 1080},
            "locale": "vi-VN",
            "timezone_id": "Asia/Ho_Chi_Minh",
        }
        if os.path.exists(self.session_file):
            print(f"[*] Loading real-estate session: {self.session_file}")
            context_args["storage_state"] = self.session_file
        else:
            print(f"[*] No stored session found for {self.source_label}; starting clean context")
        return context_args

    def _cdp_endpoint_url(self) -> Optional[str]:
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

        mcp_token = os.environ.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN", "")
        if mcp_token:
            return f"ws://localhost:9222?token={mcp_token}"

        return os.environ.get("CLOAKBROWSER_DEFAULT_CDP_URL", "http://127.0.0.1:9222")

    def _is_cloakbrowser_cdp(self, endpoint_url: Optional[str] = None) -> bool:
        if os.environ.get("CLOAKBROWSER_CDP_URL") or os.environ.get("CLOAK_BROWSER_CDP_URL"):
            return True
        endpoint = (endpoint_url or "").lower()
        return "127.0.0.1:9222" in endpoint or "localhost:9222" in endpoint or "cloak" in endpoint

    def _cdp_version_url(self, endpoint_url: Optional[str]) -> Optional[str]:
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

    def _check_cdp_endpoint(self, endpoint_url: Optional[str]) -> Optional[str]:
        version_url = self._cdp_version_url(endpoint_url)
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
                f"Cloak Browser CDP is not reachable at {endpoint_url}. "
                f"Open Cloak Browser with remote debugging port 9222, then verify {version_url}. "
                f"Details: {e}"
            )

    def _local_cdp_browser_exe(self) -> Optional[str]:
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

    def _local_cdp_profile_dir(self) -> str:
        return os.environ.get(
            "REAL_ESTATE_CDP_PROFILE_DIR",
            os.path.join(os.path.dirname(__file__), "cdp_browser_profile"),
        )

    def _start_local_cdp_browser(self, endpoint_url: Optional[str], start_url: str) -> bool:
        self.auto_started_cdp_browser = False
        self.auto_started_cdp_process = None
        endpoint = (endpoint_url or "").lower()
        if "127.0.0.1:9222" not in endpoint and "localhost:9222" not in endpoint:
            return False

        browser_exe = self._local_cdp_browser_exe()
        if not browser_exe:
            self.last_browser_error = (
                "Cannot auto-start CDP browser because Chrome/Cloak executable was not found. "
                "Set CLOAKBROWSER_EXE or REAL_ESTATE_BROWSER_EXE to the browser path."
            )
            print(f"[-] {self.last_browser_error}")
            return False

        profile_dir = self._local_cdp_profile_dir()
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
            self.auto_started_cdp_process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            for _ in range(10):
                time.sleep(1)
                if not self._check_cdp_endpoint(endpoint_url):
                    self.auto_started_cdp_browser = True
                    print("[+] Local CDP browser is ready at http://127.0.0.1:9222")
                    return True
        except Exception as e:
            self.last_browser_error = f"Could not auto-start local CDP browser: {e}"
            print(f"[-] {self.last_browser_error}")
            return False

        self.last_browser_error = "Local CDP browser was started but 127.0.0.1:9222 did not become ready."
        print(f"[-] {self.last_browser_error}")
        return False

    def _stop_auto_started_cdp_browser(self, browser=None) -> None:
        print("[*] Closing auto-started CDP browser after crawl")
        try:
            if browser:
                browser.close()
        except Exception:
            pass

        process = self.auto_started_cdp_process
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

        self.auto_started_cdp_process = None
        self.auto_started_cdp_browser = False

    def _ensure_cdp_endpoint(self, endpoint_url: Optional[str], start_url: str) -> Optional[str]:
        cdp_error = self._check_cdp_endpoint(endpoint_url)
        if not cdp_error:
            return None
        print(f"[-] {cdp_error}")
        if self._start_local_cdp_browser(endpoint_url, start_url):
            return self._check_cdp_endpoint(endpoint_url)
        return self.last_browser_error or cdp_error

    def _challenge_wait_seconds(self) -> int:
        try:
            return max(0, int(os.environ.get("CLOAKBROWSER_CHALLENGE_WAIT_SECONDS", "120")))
        except ValueError:
            return 120

    def _wait_for_challenge_clearance(self, page, endpoint_url: Optional[str]) -> str:
        html = page.content()
        blocking_reason = self._blocking_reason(html)
        if not blocking_reason or not self._is_cloakbrowser_cdp(endpoint_url):
            return html

        wait_seconds = self._challenge_wait_seconds()
        if wait_seconds <= 0:
            return html

        print(
            f"[!] {self.source_label} is blocked by {blocking_reason}. "
            f"Waiting up to {wait_seconds}s for Cloak Browser/manual challenge clearance..."
        )
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            html = page.content()
            if not self._detect_blocking_signals(html):
                print(f"[+] {self.source_label} challenge cleared; continuing crawl")
                return html

        return html

    def _pick_existing_page(self, context, target_url: str):
        target_host = re.match(r"^https?://([^/]+)", target_url)
        target_host = target_host.group(1).lower() if target_host else ""
        for page in context.pages:
            try:
                if target_host and target_host in (page.url or "").lower():
                    print(f"[*] Reusing existing Cloak Browser tab: {page.url}")
                    return page
            except Exception:
                continue
        return None

    def _page_url(self, page_number: int) -> str:
        if page_number <= 1:
            return self.target_url
        separator = "&" if "?" in self.target_url else "?"
        return f"{self.target_url}{separator}p={page_number}"

    def _fetch_static_page(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return response.text

    def _browser_fetch_page(self, url: str) -> Optional[str]:
        print(f"[!] Starting Playwright fallback for real-estate page: {url}")
        self.last_browser_error = None
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = None
                context = None
                launched_browser = False

                try:
                    endpoint_url = self._cdp_endpoint_url()
                    if not endpoint_url:
                        raise RuntimeError("No CDP endpoint configured")
                    cdp_error = self._ensure_cdp_endpoint(endpoint_url, url)
                    if cdp_error and self._is_cloakbrowser_cdp(endpoint_url):
                        self.last_browser_error = cdp_error
                        return None
                    browser = p.chromium.connect_over_cdp(endpoint_url)
                    if self._is_cloakbrowser_cdp(endpoint_url) and browser.contexts:
                        print("[*] Using Cloak Browser existing profile context")
                        context = browser.contexts[0]
                    else:
                        context = browser.new_context(**self._browser_context_args())
                except Exception as e:
                    print(f"[-] Could not connect to Cloak/CDP browser: {e}")
                    if self.source == "batdongsan":
                        self.last_browser_error = (
                            "Batdongsan requires Cloak Browser CDP for Cloudflare. "
                            "Start Cloak with --remote-debugging-port=9222 or set CLOAKBROWSER_CDP_URL."
                        )
                        print(f"[-] {self.last_browser_error}")
                        return None
                    print("[*] Opening new browser for real-estate crawl...")
                    headless = os.environ.get("REAL_ESTATE_HEADLESS", "true").lower() not in ["0", "false", "no"]
                    browser = p.chromium.launch(headless=headless, slow_mo=50)
                    launched_browser = True
                    context = browser.new_context(**self._browser_context_args())

                using_cloak_cdp = self._is_cloakbrowser_cdp(endpoint_url if 'endpoint_url' in locals() else None)
                page = self._pick_existing_page(context, url) if using_cloak_cdp else None
                if page:
                    page.bring_to_front()
                    current_url = (page.url or "").lower()
                    target_url = url.lower()
                    if target_url not in current_url:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    else:
                        print("[*] Existing Cloak tab is already on target URL; reading current page state")
                else:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Give client-side listings and automatic security checks time to settle.
                for _ in range(5):
                    page.wait_for_timeout(3000)
                    current_html = page.content()
                    if not self._detect_blocking_signals(current_html):
                        break
                html = page.content()
                html = self._wait_for_challenge_clearance(page, endpoint_url if 'endpoint_url' in locals() else None)

                blocking_reason = self._blocking_reason(html)
                if blocking_reason:
                    print(f"[-] Not saving blocked session for {self.source_label}: {blocking_reason}")
                else:
                    context.storage_state(path=self.session_file)
                    print(f"[+] Saved real-estate session: {self.session_file}")
                if self.auto_started_cdp_browser:
                    self._stop_auto_started_cdp_browser(browser)
                elif not self._is_cloakbrowser_cdp(endpoint_url if 'endpoint_url' in locals() else None):
                    page.close()
                    context.close()
                if launched_browser and browser:
                    browser.close()
                return html
        except Exception as e:
            print(f"[-] Real-estate Playwright fallback failed: {e}")
            self.last_browser_error = str(e)
            return None

    def _blocking_reason(self, html: Optional[str], status_code: int = 200) -> Optional[str]:
        if status_code in [403, 429, 503] or not html:
            return f"HTTP {status_code} or empty response"
        html_lower = html.lower()

        if "access denied" in html_lower:
            return "access denied"

        cloudflare_block_markers = [
            "<title>just a moment",
            "just a moment...",
            "checking your browser",
            "challenge-platform",
            "cf-chl-",
            "cf_chl_",
            "/cdn-cgi/challenge-platform/",
            "cf-browser-verification",
        ]
        if any(marker in html_lower for marker in cloudflare_block_markers):
            return "Cloudflare challenge"

        human_verification_markers = [
            "verify you are a human",
            "verify that you are human",
            "security check",
            "complete the security check",
        ]
        if any(marker in html_lower for marker in human_verification_markers):
            return "human verification challenge"

        captcha_markers = [
            "g-recaptcha",
            "hcaptcha",
            "captcha-container",
            "captcha__",
        ]
        if any(marker in html_lower for marker in captcha_markers):
            return "captcha challenge"

        return None

    def _detect_blocking_signals(self, html: Optional[str], status_code: int = 200) -> bool:
        return self._blocking_reason(html, status_code) is not None

    def _extract_title(self, element) -> Optional[str]:
        for selector in self.TITLE_SELECTORS:
            node = element.select_one(selector)
            if not node:
                continue
            title = node.get("title") or node.get_text(" ", strip=True)
            if title and len(title) > 10:
                return title
        text = element.get_text(" ", strip=True)
        return text[:160] if len(text) > 10 else None

    def _extract_url(self, element) -> Optional[str]:
        link = element.select_one("a[href]")
        if not link:
            return None
        href = link.get("href")
        if not href:
            return None
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("/"):
            root_match = re.match(r"^(https?://[^/]+)", self.target_url)
            return f"{root_match.group(1)}{href}" if root_match else href
        return href

    def _extract_price_text(self, text: str) -> Optional[str]:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        for pattern in self.PRICE_PATTERNS:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        parts = [part.strip() for part in re.split(r"[|\n•]", text or "") if part.strip()]
        for part in parts:
            lower = part.lower()
            if any(hint in lower for hint in self.LOCATION_HINTS):
                return part[:160]
        return None

    def _parse_json_ld_listings(self, soup: BeautifulSoup) -> List[Dict]:
        records = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                payload = json.loads(script.string or "{}")
            except Exception:
                continue

            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                graph = item.get("@graph") if isinstance(item.get("@graph"), list) else [item]
                for node in graph:
                    if not isinstance(node, dict):
                        continue
                    node_type = str(node.get("@type", "")).lower()
                    if "product" not in node_type and "offer" not in node_type and "residence" not in node_type:
                        continue
                    title = node.get("name") or node.get("headline")
                    offers = node.get("offers") if isinstance(node.get("offers"), dict) else {}
                    price_text = str(offers.get("price") or node.get("price") or "")
                    url = node.get("url")
                    if title:
                        records.append(self._build_record(title, price_text, "", url))
        return records

    def _build_record(
        self,
        title: str,
        price_text: Optional[str],
        body_text: str,
        url: Optional[str],
    ) -> Dict:
        area_text = None
        area_match = re.search(r"\d+(?:[,.]\d+)?\s*(?:m2|m²|m\s*2)", body_text or "", flags=re.IGNORECASE)
        if area_match:
            area_text = area_match.group(0)

        price_vnd = clean_real_estate_price(price_text)
        area_m2 = clean_area_m2(area_text)
        price_per_m2 = int(price_vnd / area_m2) if price_vnd and area_m2 else None

        return {
            "datetime": int(datetime.now().timestamp()),
            "source": self.source_label,
            "property_type": "Real Estate",
            "title": title,
            "price": price_vnd,
            "price_text": price_text,
            "area_m2": area_m2,
            "area_text": area_text,
            "price_per_m2": price_per_m2,
            "location": self._extract_location(body_text),
            "url": url,
        }

    def _parse_listings(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html or "", "html.parser")
        records = self._parse_json_ld_listings(soup)

        for selector in self.LISTING_SELECTORS:
            for element in soup.select(selector):
                text = element.get_text(" ", strip=True)
                if len(text) < 30:
                    continue

                title = self._extract_title(element)
                price_text = self._extract_price_text(text)
                if not title or not price_text:
                    continue

                records.append(self._build_record(title, price_text, text, self._extract_url(element)))

        unique = {}
        for record in records:
            key = (record.get("title"), record.get("price_text"), record.get("url"))
            unique[key] = record
        return list(unique.values())

    def execute_crawling(self) -> Dict[str, Dict]:
        print(f"[*] Crawling real-estate source {self.source_label}: {self.target_url}")
        records = []
        last_error = None

        for page_number in range(1, self.max_pages + 1):
            url = self._page_url(page_number)
            html = None
            if self._should_use_browser_first():
                html = self._browser_fetch_page(url)
                if not html:
                    last_error = self.last_browser_error or "Browser-first real-estate fetch returned no HTML"
            else:
                try:
                    html = self._fetch_static_page(url)
                    if self._detect_blocking_signals(html):
                        raise Exception("Blocked or empty static response")
                except Exception as e:
                    last_error = e
                    print(f"[-] Static real-estate fetch failed for page {page_number}: {e}")
                    if self.use_browser_fallback:
                        html = self._browser_fetch_page(url)

            if not html:
                continue

            blocking_reason = self._blocking_reason(html)
            if blocking_reason:
                last_error = (
                    f"{self.source_label} page {page_number} blocked by {blocking_reason}. "
                    "Refresh the stored session or complete the challenge manually before crawling."
                )
                print(f"[-] {last_error}")
                continue

            page_records = self._parse_listings(html)
            print(f"[+] {self.source_label} page {page_number}: {len(page_records)} listings")
            records.extend(page_records)

        if records:
            return {self.source: source_result("ok", records)}
        return {self.source: source_result("failed", [], str(last_error or "No listings parsed"))}


class BatdongsanCrawler(RealEstateCrawler):
    def __init__(self, max_pages: int = 1, use_browser_fallback: bool = True):
        super().__init__("batdongsan", max_pages=max_pages, use_browser_fallback=use_browser_fallback)


class AloNhaDatCrawler(RealEstateCrawler):
    def __init__(self, max_pages: int = 1, use_browser_fallback: bool = True):
        super().__init__("alonhadat", max_pages=max_pages, use_browser_fallback=use_browser_fallback)


class MultiSourceRealEstateCrawler:
    """Run real-estate crawlers and return the same source_result envelope as gold crawlers."""

    def __init__(self, max_pages: int = 1, use_browser_fallback: bool = True):
        self.crawlers = {
            "batdongsan": BatdongsanCrawler(max_pages=max_pages, use_browser_fallback=use_browser_fallback),
            "alonhadat": AloNhaDatCrawler(max_pages=max_pages, use_browser_fallback=use_browser_fallback),
        }

    def execute_crawling(self) -> Dict[str, Dict]:
        results = {
            source_name: source_result("failed", [], "Not started")
            for source_name in self.crawlers
        }

        with ThreadPoolExecutor(max_workers=len(self.crawlers)) as executor:
            future_map = {
                executor.submit(crawler.execute_crawling): source_name
                for source_name, crawler in self.crawlers.items()
            }

            for future in as_completed(future_map):
                source_name = future_map[future]
                try:
                    source_payload = future.result()
                    if source_payload and source_name in source_payload:
                        results[source_name] = source_payload[source_name]
                except Exception as e:
                    results[source_name] = source_result("failed", [], str(e))

        return results


class MultiSourceGoldCrawler:
    """Run SJC/WebGia, DOJI, and PNJ crawlers in parallel."""

    def __init__(self, use_ai_fallback: bool = True, profile_name: Optional[str] = None):
        self.crawlers = {
            "sjc": SjcWebGiaCrawler(use_ai_fallback=use_ai_fallback, profile_name="sjc"),
            "doji": DojiCrawler(profile_name="doji"),
            "pnj": PnjCrawler(profile_name="pnj"),
        }

    def execute_crawling(self) -> Dict[str, Dict]:
        results = {
            "sjc": source_result("failed", [], "Not started"),
            "doji": source_result("failed", [], "Not started"),
            "pnj": source_result("failed", [], "Not started"),
        }

        with ThreadPoolExecutor(max_workers=len(self.crawlers)) as executor:
            future_map = {
                executor.submit(crawler.execute_crawling): source_name
                for source_name, crawler in self.crawlers.items()
            }

            for future in as_completed(future_map):
                source_name = future_map[future]
                try:
                    source_payload = future.result()
                    if source_payload and source_name in source_payload:
                        results[source_name] = source_payload[source_name]
                except Exception as e:
                    results[source_name] = source_result("failed", [], str(e))

        return results


class HybridGoldCrawler(MultiSourceGoldCrawler):
    """Backward-compatible name for existing imports."""


if __name__ == "__main__":
    crawler = MultiSourceGoldCrawler(use_ai_fallback=True)
    result = crawler.execute_crawling()
    try:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(result, indent=2, ensure_ascii=True))
