import re
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests
from datetime import datetime

from crawlers.base import BaseCrawler
from crawlers.utils import clean_price

class SjcWebGiaCrawler(BaseCrawler):
    def __init__(self, profile_name="default"):
        super().__init__("https://webgia.com/gia-vang/sjc/", profile_name)

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        print("[*] SjcWebGiaCrawler: Applying static parser...")
        soup = BeautifulSoup(html or "", "html.parser")
        result = {}
        
        table = soup.find("table", class_="table-gia-vang")
        if not table:
            for candidate in soup.find_all("table"):
                header_text = candidate.get_text(" ", strip=True).lower()
                if "loại vàng" in header_text and "mua vào" in header_text and "bán ra" in header_text:
                    table = candidate
                    break
        if not table: return None

        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 3: continue
            
            name_index, buy_index, sell_index = (1, 2, 3) if len(cols) >= 4 else (0, 1, 2)
            name = cols[name_index].get_text(" ", strip=True).lower()
            buy = clean_price(cols[buy_index].get_text(" ", strip=True))
            sell = clean_price(cols[sell_index].get_text(" ", strip=True))
            
            if buy is None and sell is None: continue
            
            if "1l" in name or "mieng" in name or "miếng" in name:
                if "buy_1l" not in result:
                    result["buy_1l"], result["sell_1l"] = buy, sell
            elif "nhan" in name or "nhẫn" in name:
                if "buy_nhan1c" not in result:
                    result["buy_nhan1c"], result["sell_nhan1c"] = buy, sell
            elif ("nu trang" in name or "nữ trang" in name) and ("99,99" in name or "9999" in name):
                result["buy_nutrang_9999"], result["sell_nutrang_9999"] = buy, sell
            elif ("nu trang" in name or "nữ trang" in name) and "99" in name:
                result["buy_nutrang_99"], result["sell_nutrang_99"] = buy, sell
            elif ("nu trang" in name or "nữ trang" in name) and ("75" in name or "18k" in name):
                result["buy_nutrang_75"], result["sell_nutrang_75"] = buy, sell

        if "buy_1l" not in result: return None
        result["datetime"] = int(datetime.now().timestamp())
        return [result]

class DojiCrawler(BaseCrawler):
    def __init__(self, profile_name="default"):
        super().__init__("https://giavang.doji.vn/", profile_name)
        self.AREA_MAP = {
            "ha noi": "Hanoi", "hà nội": "Hanoi", "da nang": "Da Nang", "đà nẵng": "Da Nang",
            "ho chi minh": "Ho Chi Minh City", "hồ chí minh": "Ho Chi Minh City",
        }
        self.GOLD_TYPE_PATTERNS = [
            ("SJC - Bán Lẻ", ["sjc"]), ("AVPL / Kim TT", ["avpl", "kim tt", "kim"]),
            ("Nhẫn Tròn 9999", ["nhan tron", "nhẫn tròn", "hung thinh", "hưng thịnh"]),
        ]

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip().lower()

    def _map_gold_type(self, raw_name: str) -> Optional[str]:
        normalized = self._normalize_text(raw_name)
        for gold_type, patterns in self.GOLD_TYPE_PATTERNS:
            if any(pattern in normalized for pattern in patterns):
                return gold_type
        return None

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        soup = BeautifulSoup(html or "", "html.parser")
        records = []
        timestamp = int(datetime.now().timestamp())
        for table in soup.find_all("table"):
            location = None
            heading_text = ""
            previous = table.find_previous(["h1", "h2", "h3", "h4", "strong", "div"])
            if previous:
                heading_text = self._normalize_text(previous.get_text())
                for marker, loc in self.AREA_MAP.items():
                    if marker in heading_text:
                        location = loc
                        break
            
            if not location: location = "Hanoi"

            for row in table.find_all("tr"):
                cols = row.find_all(["td", "th"])
                if len(cols) < 3: continue
                
                raw_name = cols[0].get_text(" ", strip=True)
                raw_buy = cols[1].get_text(" ", strip=True)
                raw_sell = cols[2].get_text(" ", strip=True)
                
                gold_type = self._map_gold_type(raw_name)
                buy = clean_price(raw_buy)
                sell = clean_price(raw_sell)
                
                if gold_type and (buy or sell):
                    records.append({
                        "datetime": timestamp, "company": "DOJI", "gold_type": gold_type,
                        "buy_price": buy, "sell_price": sell, "location": location,
                        "source": self.url
                    })
        return records if records else None

class PnjCrawler(BaseCrawler):
    def __init__(self, profile_name="default"):
        super().__init__("https://www.pnj.com.vn/site/gia-vang", profile_name)
        self.ZONES = {"00": "Ho Chi Minh City", "11": "Hanoi", "13": "Da Nang"}

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        # PNJ actually uses an API, not HTML parsing. Let's override execute!
        return None

    def execute(self) -> Dict:
        records = []
        timestamp = int(datetime.now().timestamp())
        for zone_id, location in self.ZONES.items():
            url = f"https://edge-cf-api.pnj.io/ecom-frontend/v1/get-gold-price?zone={zone_id}"
            try:
                resp = requests.get(url, headers=self.headers, timeout=5)
                data = resp.json().get("data") or []
                for item in data:
                    name = (item.get("tensp") or item.get("name") or item.get("masp") or "").lower()
                    gold_type = "SJC" if "sjc" in name else "PNJ" if "pnj" in name else "Nhẫn Trơn" if "nhẫn" in name else "9999" if "9999" in name else None
                    if not gold_type: continue
                    
                    try:
                        buy = int(float(str(item.get("giamua") or "0").replace(',', ''))) * 1000
                        sell = int(float(str(item.get("giaban") or "0").replace(',', ''))) * 1000
                    except ValueError:
                        continue
                        
                    if buy == 0 and sell == 0: continue
                        
                    records.append({
                        "datetime": timestamp, "company": "PNJ", "gold_type": gold_type,
                        "buy_price": buy, "sell_price": sell,
                        "location": location, "source": self.url
                    })
            except Exception as e: 
                print(f"[-] PNJ API error for zone {zone_id}: {e}")
        from crawlers.utils import source_result
        return source_result("success", records) if records else source_result("error", error="PNJ API failed")
