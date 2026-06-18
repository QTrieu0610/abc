import json
import os
import random
import re
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

    def __init__(self, source: str, use_ai_fallback: bool = True, profile_name: str = "default"):
        self.source = source.lower()
        self.use_ai_fallback = use_ai_fallback
        self.profile_name = profile_name

        if self.source in ["sjc", "webgia"]:
            self.target_url = "https://webgia.com/gia-vang/sjc/"
            self.headers = DEFAULT_HEADERS.copy()
            self.ollama_url = "http://localhost:11434/api/generate"
            self.ai_model = "gemma4:e2b"
            os.makedirs("sessions", exist_ok=True)
            self.session_file = f"sessions/crawler_session_{self.profile_name}.json"
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
        elif self.source == "pnj":
            self.headers = {
                **DEFAULT_HEADERS,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.pnj.com.vn",
                "Referer": self.PAGE_URL_PNJ,
            }
            self.max_retries = 2
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
        print("[!] WebGia static parse failed. Trying local AI fallback...")
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
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.ai_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=120,
            )
            if response.status_code == 200:
                return json.loads(response.json()["response"])
            print(f"[-] Ollama error: {response.text}")
            return None
        except Exception as e:
            print(f"[-] Ollama unavailable: {e}")
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
                print(f"[*] Phát hiện từ khóa nghi ngờ chặn Bot: '{signal}'")
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
                print("[!] Yêu cầu đăng nhập. Đang tự động điền thông tin bảo mật...")
                page.locator("input[type='text'], input[name='username'], input[type='email']").first.fill(
                    self.credentials["username"]
                )
                page.wait_for_timeout(random.randint(300, 800))
                page.locator("input[type='password']").fill(self.credentials["password"])
                page.keyboard.press("Enter")
                print("[*] Đã ấn Đăng nhập, đang chờ trang phản hồi...")
                page.wait_for_timeout(5000) # Đợi bắt buộc 5s để sang hẳn trang sau
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except:
                    pass
                
                # Check for MFA / OTP after login
                if page.locator("input[name*='otp'], input[name*='code'], input[id*='otp'], text='MFA', text='OTP', input[placeholder*='OTP']").is_visible(timeout=3000):
                    print("[-] Phát hiện yêu cầu xác thực 2 bước (MFA/OTP)! Hãy tự nhập trên trình duyệt...")
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
                    print("[*] Đang mở trình duyệt mới (có giao diện) để bạn quan sát bot gõ phím...")
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
                        print("[*] Đang đợi trang tải hoàn tất...")
                        page.wait_for_load_state("networkidle", timeout=10000)
                        html = page.content()
                    else:
                        raise e

                # Đợi con người giải quyết Captcha/MFA
                while self._detect_blocking_signals_sjc(html):
                    print("[-] BỊ CHẶN (MFA/Captcha)! Bot đang tạm dừng...")
                    print("[*] Vui lòng thao tác trên cửa sổ trình duyệt (Nhập OTP/Giải Captcha). Bot sẽ tự động kiểm tra lại sau mỗi 5s...")
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
                    print(f"[!!!] CẦN CON NGƯỜI DUYỆT (HITL). Dừng thử lại! Lỗi: {e}")
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

    def _execute_crawling_doji(self):
        print(f"[*] Crawling DOJI: {self.target_url}")

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.target_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                records = self._parse_doji(response.text)

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

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent=DEFAULT_HEADERS["User-Agent"],
                    viewport={"width": 1440, "height": 1000},
                )
                page.goto(self.PAGE_URL_PNJ, wait_until="networkidle", timeout=45000)

                for zone, location in self.ZONES_PNJ.items():
                    page.locator("select").first.select_option(zone)
                    page.wait_for_timeout(1200)
                    text = page.locator("body").inner_text(timeout=10000)
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

                browser.close()
        except Exception as e:
            print(f"[-] PNJ Playwright fallback failed: {e}")

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
    def __init__(self, use_ai_fallback: bool = True, profile_name: str = "default"):
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
    def __init__(self):
        super().__init__(source="doji")

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
    def __init__(self):
        super().__init__(source="pnj")

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


class MultiSourceGoldCrawler:
    """Run SJC/WebGia, DOJI, and PNJ crawlers in parallel."""

    def __init__(self, use_ai_fallback: bool = True, profile_name: str = "default"):
        self.crawlers = {
            "sjc": SjcWebGiaCrawler(use_ai_fallback=use_ai_fallback, profile_name=profile_name),
            "doji": DojiCrawler(),
            "pnj": PnjCrawler(),
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
    print(json.dumps(result, indent=2, ensure_ascii=False))
