import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import re

import os
import random
import time

class HybridGoldCrawler:
    """
    Hệ thống Crawler 3 Lớp (Hybrid) áp dụng cho giá vàng SJC.
    Tier 1: Request thuần + Static Parsing (BeautifulSoup)
    Tier 2: Gọi AI (Ollama Local) khi giao diện web thay đổi
    """
    
    def __init__(self, use_ai_fallback=True, profile_name="default"):
        self.target_url = "https://webgia.com/gia-vang/sjc/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.use_ai_fallback = use_ai_fallback
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ai_model = "qwen2.5:7b" # Bạn có thể đổi sang llama3.1
        
        # 1. Multi-identity / Profile-based Crawling
        self.profile_name = profile_name
        os.makedirs("sessions", exist_ok=True)
        self.session_file = f"sessions/crawler_session_{self.profile_name}.json"
        
        # 2. Dynamic Retry Strategy & Proxy Rotation
        self.max_retries = 3
        self.proxies = [None] # Nơi gắn Proxy List nếu cần
        
        # 3. Secure Credentials Vault
        self.credentials = {
            "username": os.environ.get("GOLD_SITE_USER", "default_user"),
            "password": os.environ.get("GOLD_SITE_PASS", "default_pass")
        }
        
    def _get_cookies_from_session(self):
        """Đọc file state của Playwright và trích xuất Cookies để dùng cho requests"""
        import os
        cookies_dict = {}
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    for cookie in state.get('cookies', []):
                        cookies_dict[cookie['name']] = cookie['value']
            except Exception as e:
                print(f"[-] Không thể đọc session file: {e}")
        return cookies_dict
    def _clean_price(self, price_str):
        """Làm sạch chuỗi giá: '82.500.000' -> 82500000"""
        if not price_str: return None
        cleaned = re.sub(r'[^\d]', '', price_str)
        if not cleaned: return None
        
        # Thường giá trên webgia ghi là 82.500 (nghìn đồng/chỉ) -> Cần nhân thêm 1000
        val = int(cleaned)
        if val < 100000:  
            val *= 1000
        return val

    def _tier_1_static_parse(self, html):
        """
        Trích xuất Ưu tiên (Tĩnh & Nhanh). Tốc độ: ~10ms
        Sử dụng BeautifulSoup để quét thẻ HTML tĩnh.
        """
        print("[*] Áp dụng Static Parser (Tier 1)...")
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {}
        # Mô phỏng việc cào bảng giá từ webgia.com
        # Thẻ HTML thực tế có thể khác, đây là Rule dự kiến
        table = soup.find('table', class_='table-gia-vang')
        
        if not table:
            # Giao diện đã đổi, hoặc webgia chống bot -> Trả về None để kích hoạt Fallback
            return None
            
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                name = cols[0].text.strip().lower()
                buy = self._clean_price(cols[1].text.strip())
                sell = self._clean_price(cols[2].text.strip())
                
                # Mapping tên
                if '1l' in name or 'miếng' in name:
                    result['buy_1l'] = buy; result['sell_1l'] = sell
                elif 'nhẫn' in name and '1c' in name:
                    result['buy_nhan1c'] = buy; result['sell_nhan1c'] = sell
                elif 'nữ trang' in name and '99,99' in name:
                    result['buy_nutrang_9999'] = buy; result['sell_nutrang_9999'] = sell
                elif 'nữ trang' in name and '99%' in name:
                    result['buy_nutrang_99'] = buy; result['sell_nutrang_99'] = sell
                elif 'nữ trang' in name and '75%' in name:
                    result['buy_nutrang_75'] = buy; result['sell_nutrang_75'] = sell
                    
        # Kiểm tra xem có quét được dữ liệu SJC 1L quan trọng nhất không
        if 'buy_1l' not in result:
            return None # Thất bại, sang Fallback
            
        print("[+] Static Parser chạy thành công!")
        return result

    def _tier_2_ai_fallback(self, html):
        """
        AI Fallback (Chậm & Thông minh). Tốc độ: ~2-5s
        Chỉ gọi khi Tier 1 gãy do giao diện thay đổi.
        """
        print("[!] Giao diện thay đổi hoặc Selector gãy. Kích hoạt AI Fallback (Tier 2)...")
        
        # 1. Sanitization: Chuyển HTML thành Text siêu gọn để tiết kiệm Token
        from bs4 import Comment
        soup = BeautifulSoup(html, 'html.parser')
        
        # Xóa rác
        for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
            tag.decompose()
        for comment in soup.findAll(text=lambda text:isinstance(text, Comment)):
            comment.extract()
            
        clean_text = " ".join(soup.stripped_strings)
        
        # Lấy 2000 ký tự quan trọng nhất chứa cụm từ 'sjc'
        sjc_idx = clean_text.lower().find('sjc')
        if sjc_idx != -1:
            start = max(0, sjc_idx - 500)
            end = min(len(clean_text), sjc_idx + 1500)
            clean_text = clean_text[start:end]
        else:
            clean_text = clean_text[:2000]

        # 2. Gọi Local LLM (Ollama)
        prompt = f"""Bạn là AI phân tích dữ liệu. Đọc văn bản sau và lấy ra giá mua/bán của vàng SJC hôm nay.
Chú ý: Quy đổi giá về VND/chỉ (Ví dụ 8,200,000). Trả về JSON, KHÔNG CÓ BẤT KỲ CHỮ NÀO KHÁC.

Format JSON cần thiết:
{{
  "buy_1l": 0, "sell_1l": 0,
  "buy_nhan1c": 0, "sell_nhan1c": 0,
  "buy_nutrang_9999": 0, "sell_nutrang_9999": 0,
  "buy_nutrang_99": 0, "sell_nutrang_99": 0,
  "buy_nutrang_75": 0, "sell_nutrang_75": 0
}}

Text:
{clean_text}"""

        print(f"[*] Đang gửi {len(clean_text)} ký tự cho mô hình {self.ai_model} phân tích...")
        try:
            response = requests.post(self.ollama_url, json={
                "model": self.ai_model,
                "prompt": prompt,
                "stream": False,
                "format": "json" # Bắt buộc model trả về JSON chuẩn
            }, timeout=120)  # Tăng timeout lên 120s vì chạy local có thể mất thời gian
            
            if response.status_code == 200:
                result = json.loads(response.json()['response'])
                print("[+] AI Trích xuất dữ liệu thành công!")
                return result
            else:
                print(f"[-] Lỗi gọi Ollama: {response.text}")
                return None
        except Exception as e:
            print(f"[-] Ollama Server không phản hồi. Hãy chắc chắn bạn đã chạy 'ollama run {self.ai_model}'. Lỗi: {e}")
            return None

    def _detect_blocking_signals(self, html, status_code=200):
        """4. Detect blocking signals: Captcha, Rate Limits, Empty results"""
        if status_code in [403, 429, 503]: return True
        if not html: return True
        html_lower = html.lower()
        signals = ["please verify you are a human", "cloudflare", "access denied", "captcha", "security check"]
        for signal in signals:
            if signal in html_lower:
                return True
        return False

    def _simulate_human_behavior(self, page):
        """5. Simulate human-like behavior: typing delay, mouse movement, scrolling"""
        print("[*] Đang mô phỏng hành vi người thật (Mouse movement & Scrolling)...")
        # Di chuột ngẫu nhiên
        page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        page.wait_for_timeout(random.randint(500, 1500))
        # Cuộn trang ngẫu nhiên
        page.mouse.wheel(0, random.randint(300, 800))
        page.wait_for_timeout(random.randint(1000, 2000))

    def _handle_login(self, page):
        """6. Support login using credentials stored securely"""
        try:
            if page.locator("input[type='password']").is_visible(timeout=2000):
                print("[!] Yêu cầu đăng nhập. Đang tự động điền thông tin bảo mật...")
                # Gõ chậm như người thật (delay)
                page.locator("input[type='text'], input[name='username'], input[type='email']").first.fill(self.credentials['username'])
                page.wait_for_timeout(random.randint(300, 800))
                page.locator("input[type='password']").fill(self.credentials['password'])
                page.wait_for_timeout(random.randint(300, 800))
                page.keyboard.press("Enter")
                page.wait_for_load_state('networkidle')
                print("[+] Đăng nhập thành công!")
        except Exception:
            pass # Không có form login thì bỏ qua

    def _browser_fetch(self):
        """
        Tier 2 (Browser Automation): Headful/Headless kết hợp MCP.
        """
        print("[!] Kích hoạt Browser Automation (Playwright)...")
        try:
            from playwright.sync_api import sync_playwright
            import os
            
            # Cấu hình Token MCP (Nếu có)
            mcp_token = os.environ.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN", "ke6HO9i2bxggIzXIH2fjqJGirgsp_WzLrBGFw04UzNs")
            
            with sync_playwright() as p:
                browser = None
                context = None
                
                # 1. THỬ KẾT NỐI VÀO BROWSER CÁ NHÂN QUA MCP EXTENSION (Không mở cửa sổ mới)
                try:
                    # Mặc định Playwright Extension mở cổng 9222 hoặc 9223
                    endpoint_url = f"ws://localhost:9222?token={mcp_token}"
                    print("[*] Đang thử kết nối vào Browser cá nhân (Extension) qua MCP Token...")
                    browser = p.chromium.connect_over_cdp(endpoint_url)
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    print("[+] Đã gắn thành công vào Browser của bạn!")
                except Exception as cdp_err:
                    print(f"[*] Không tìm thấy Extension/CDP (Lỗi: {cdp_err}). Chuyển sang chế độ Headless truyền thống...")
                    # 2. FALLBACK: TẠO HEADLESS BROWSER MỚI (Chạy ngầm hoàn toàn)
                    browser = p.chromium.launch(headless=True)
                    
                    context_args = {
                        'user_agent': self.headers['User-Agent'],
                        'viewport': {'width': 1920, 'height': 1080}
                    }
                    if os.path.exists(self.session_file):
                        context_args['storage_state'] = self.session_file
                        print("[*] Đã nạp Session/Cookies cũ vào Headless Browser.")
                    context = browser.new_context(**context_args)
                
                page = context.new_page()
                
                # Đi tới trang, cho phép chờ đến 30s để vượt qua màn hình Cloudflare
                page.goto(self.target_url, wait_until='networkidle', timeout=30000)
                
                # Hành vi giống người (Tránh bị phát hiện là Bot)
                self._simulate_human_behavior(page)
                
                # Xử lý Login nếu web yêu cầu
                self._handle_login(page)
                
                html = page.content()
                
                # Kiểm tra chặn (Captcha/Challenge)
                if self._detect_blocking_signals(html):
                    print("[-] Bị chặn bởi Captcha/Challenge. Yêu cầu HITL (Human-in-the-loop)!")
                    # 7. HITL Escalation: Ở đây ta có thể gửi cảnh báo qua Slack/Telegram
                    # hoặc đẩy trạng thái về Frontend React để con người vào giải quyết
                    raise Exception("HITL_REQUIRED")
                    
                print("[+] Lấy mã nguồn thành công qua Playwright!")
                
                # Lưu lại Session/Cookies mới nhất
                context.storage_state(path=self.session_file)
                print(f"[+] Đã cập nhật Session mới tại {self.session_file}")
                
                # Chỉ đóng tab vừa tạo để không làm tắt trình duyệt chính của bạn
                page.close()
                
                # Nếu tự khởi tạo Headless thì mới đóng browser
                if not browser.contexts: 
                    browser.close()
                    
                return html
        except ImportError:
            print("[-] Chưa cài đặt Playwright! Vui lòng chạy: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            print(f"[-] Lỗi Browser Automation: {e}")
            return None

    def execute_crawling(self):
        """Hàm chính điều phối việc cào dữ liệu với Retry Strategy"""
        print(f"[*] Đang kết nối tới {self.target_url} (Profile: {self.profile_name})...")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Lấy Proxy (nếu có cấu hình Rotation)
                proxy = random.choice(self.proxies)
                proxies_dict = {"http": proxy, "https": proxy} if proxy else None
                
                cookies = self._get_cookies_from_session()
                
                # Lớp 1: Request thuần
                response = requests.get(self.target_url, headers=self.headers, cookies=cookies, proxies=proxies_dict, timeout=10)
                
                if self._detect_blocking_signals(response.text, response.status_code):
                    print(f"[-] Lần {attempt}: Bị Anti-bot chặn (HTTP {response.status_code}). Kích hoạt Playwright Fallback...")
                    html = self._browser_fetch()
                else:
                    html = response.text
                
                # Parse tĩnh
                data = self._tier_1_static_parse(html)
                
                # AI Fallback
                if data is None and self.use_ai_fallback:
                    data = self._tier_2_ai_fallback(html)
                    
                if data:
                    current_timestamp = int(datetime.now().timestamp())
                    data['datetime'] = current_timestamp
                    return {'sjc': [data]}
                    
                raise Exception("Lấy dữ liệu thất bại sau khi Parse.")
                
            except Exception as e:
                if str(e) == "HITL_REQUIRED":
                    print("[!!!] CẦN SỰ CAN THIỆP CỦA CON NGƯỜI (HITL). DỪNG RETRY.")
                    return None
                    
                print(f"[-] Lỗi ở lần thử {attempt}/{self.max_retries}: {e}")
                if attempt < self.max_retries:
                    # 8. Dynamic Retry Delay: Chờ ngẫu nhiên trước khi thử lại
                    delay = attempt * random.randint(3, 7)
                    print(f"[*] Đang áp dụng Dynamic Delay. Đợi {delay}s trước khi thử lại...")
                    time.sleep(delay)
                else:
                    print("[-] Vượt quá số lần thử nghiệm. Cào thất bại.")
                    return None

# Chạy thử nghiệm độc lập
if __name__ == "__main__":
    crawler = HybridGoldCrawler(use_ai_fallback=True)
    result = crawler.execute_crawling()
    if result:
        print("\n[KIẾT QUẢ CUỐI CÙNG]")
        print(json.dumps(result, indent=2, ensure_ascii=False))
