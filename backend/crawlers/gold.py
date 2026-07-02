from typing import List, Dict, Optional
import requests
from datetime import datetime

from crawlers.base import BaseCrawler
from crawlers.base_table import BaseTableCrawler

class SjcWebGiaCrawler(BaseTableCrawler):
    """
    SJC Gold Price crawler using WebGia table.
    Outputs SJC-specific flat dictionary mapping key-value.
    """
    def __init__(self, profile_name="default"):
        gold_type_mapping = {
            "1l": "1l", "miếng": "1l", "mieng": "1l",
            "nhẫn": "nhan1c", "nhan": "nhan1c",
            "nữ trang 99,99": "nutrang_9999", "nữ trang 9999": "nutrang_9999", "99,99": "nutrang_9999",
            "99": "nutrang_99",
            "75": "nutrang_75", "18k": "nutrang_75"
        }
        super().__init__(
            url="https://webgia.com/gia-vang/sjc/",
            table_selector="table.table-gia-vang",
            gold_type_mapping=gold_type_mapping,
            output_format="flat",
            company_name="SJC",
            profile_name=profile_name
        )


class DojiCrawler(BaseTableCrawler):
    """
    DOJI Gold Price crawler.
    Parses geographic region tables and outputs standard normalized record lists.
    """
    def __init__(self, profile_name="default"):
        gold_type_mapping = {
            "sjc": "SJC - Bán Lẻ",
            "avpl": "AVPL / Kim TT", "kim tt": "AVPL / Kim TT", "kim": "AVPL / Kim TT",
            "nhan tron": "Nhẫn Tròn 9999", "nhẫn tròn": "Nhẫn Tròn 9999", 
            "hung thinh": "Nhẫn Tròn 9999", "hưng thịnh": "Nhẫn Tròn 9999"
        }
        area_map = {
            "ha noi": "Hanoi", "hà nội": "Hanoi",
            "da nang": "Da Nang", "đà nẵng": "Da Nang",
            "ho chi minh": "Ho Chi Minh City", "hồ chí minh": "Ho Chi Minh City",
        }
        super().__init__(
            url="https://giavang.doji.vn/",
            table_selector="table",
            gold_type_mapping=gold_type_mapping,
            output_format="normalized",
            default_location="Hanoi",
            location_mapping=area_map,
            company_name="DOJI",
            profile_name=profile_name
        )


class PnjCrawler(BaseCrawler):
    """
    PNJ Gold Price crawler.
    Uses Direct API requests since PNJ loads data dynamically via client-side endpoints.
    """
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
                    if not gold_type: 
                        continue
                    
                    try:
                        buy = int(float(str(item.get("giamua") or "0").replace(',', ''))) * 1000
                        sell = int(float(str(item.get("giaban") or "0").replace(',', ''))) * 1000
                    except ValueError:
                        continue
                        
                    if buy == 0 and sell == 0: 
                        continue
                        
                    records.append({
                        "datetime": timestamp, 
                        "company": "PNJ", 
                        "gold_type": gold_type,
                        "buy_price": buy, 
                        "sell_price": sell,
                        "location": location, 
                        "source": self.url
                    })
            except Exception as e: 
                print(f"[-] PNJ API error for zone {zone_id}: {e}")
        from crawlers.utils import source_result
        return source_result("success", records) if records else source_result("error", error="PNJ API failed")
