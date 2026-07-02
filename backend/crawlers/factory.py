import os
import json
from typing import Optional

from crawlers.base import BaseCrawler
from crawlers.gold import PnjCrawler
from crawlers.real_estate import BatdongsanCrawler, AloNhaDatCrawler
from crawlers.ai_fallback import GenericRealEstateCrawler
from crawlers.base_table import BaseTableCrawler

def load_target_config(url: str, label: str) -> Optional[dict]:
    filename = "gold_targets.json" if label == "gold" else "real_estate_targets.json"
    candidates = [
        os.path.join("config", filename),
        os.path.join("backend", "config", filename),
        os.path.join("..", "config", filename),
    ]
    url_normalized = url.rstrip("/").lower()
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    targets = json.load(f)
                    for t in targets:
                        target_url = t.get("url", "").rstrip("/").lower()
                        # Match exact normalized URL or if target URL is inside requested URL
                        if target_url == url_normalized or (target_url and target_url in url_normalized):
                            return t
            except Exception as e:
                print(f"[-] Error reading target config {path}: {e}")
    return None

class CrawlerFactory:
    """
    Smart Router for allocating the correct crawler based on URL and requested label.
    Supports dynamic JSON configuration loading and fallback to Autopilot Table crawler.
    """
    
    @staticmethod
    def get_crawler(url: str, label: str) -> BaseCrawler:
        label = label.lower().strip()
        url_lower = url.lower()
        
        # 1. Try loading configuration dynamically from JSON first
        config = load_target_config(url, label)
        
        if config:
            crawler_type = config.get("crawler_type", "table")
            if crawler_type == "table" and label == "gold":
                return BaseTableCrawler(
                    url=url,
                    table_selector=config.get("table_selector"),
                    gold_type_mapping=config.get("gold_type_mapping"),
                    output_format=config.get("output_format", "normalized"),
                    default_location=config.get("default_location", "National"),
                    location_mapping=config.get("location_mapping"),
                    company_name=config.get("company_name", "Generic"),
                    profile_name=config.get("id", "default")
                )
            elif crawler_type == "api" and config.get("id") == "pnj":
                return PnjCrawler()

        # 2. Hardcoded fallback routing (for backward compatibility of known domains)
        if "webgia.com" in url_lower and label == "gold":
            gold_type_mapping = {
                "1l": "1l", "miếng": "1l", "mieng": "1l",
                "nhẫn": "nhan1c", "nhan": "nhan1c",
                "nữ trang 99,99": "nutrang_9999", "99,99": "nutrang_9999",
                "99": "nutrang_99",
                "75": "nutrang_75", "18k": "nutrang_75"
            }
            return BaseTableCrawler(
                url=url,
                table_selector="table.table-gia-vang",
                gold_type_mapping=gold_type_mapping,
                output_format="flat",
                company_name="SJC",
                profile_name="sjc"
            )
            
        if "doji.vn" in url_lower and label == "gold":
            gold_type_mapping = {
                "sjc": "SJC - Bán Lẻ",
                "avpl": "AVPL / Kim TT", "kim tt": "AVPL / Kim TT",
                "nhan tron": "Nhẫn Tròn 9999", "nhẫn tròn": "Nhẫn Tròn 9999", "hung thinh": "Nhẫn Tròn 9999"
            }
            area_map = {
                "ha noi": "Hanoi", "hà nội": "Hanoi",
                "da nang": "Da Nang", "đà nẵng": "Da Nang",
                "ho chi minh": "Ho Chi Minh City", "hồ chí minh": "Ho Chi Minh City"
            }
            return BaseTableCrawler(
                url=url,
                table_selector="table",
                gold_type_mapping=gold_type_mapping,
                output_format="normalized",
                default_location="Hanoi",
                location_mapping=area_map,
                company_name="DOJI",
                profile_name="doji"
            )
            
        if ("pnj.com.vn" in url_lower or "pnj.io" in url_lower) and label == "gold":
            return PnjCrawler()
            
        # 3. Known Real Estate Sites
        if "batdongsan.com.vn" in url_lower:
            if label != "real_estate": 
                raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return BatdongsanCrawler()
        if "alonhadat.com.vn" in url_lower:
            if label != "real_estate": 
                raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return AloNhaDatCrawler()

        # 4. Unknown Sites - Autopilot Mode Fallback
        if label == "gold":
            # Autopilot Table Crawler: attempts static parsing and automatically falls back to LLM Tier 3
            return BaseTableCrawler(url=url, profile_name="autopilot")
        elif label == "real_estate":
            return GenericRealEstateCrawler(url=url)
        else:
            raise ValueError(f"Label không hợp lệ: {label}. Chỉ hỗ trợ 'gold' hoặc 'real_estate'.")
