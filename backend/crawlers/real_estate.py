import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from crawlers.base import BaseCrawler
from crawlers.utils import clean_real_estate_price, clean_area_m2

class RealEstateBaseCrawler(BaseCrawler):
    """Common parsing logic for real estate sites"""
    LISTING_SELECTORS = [
        "[class*='js__card']", "[class*='product-item']", "[class*='re__card']",
        "[class*='listing']", "[class*='property']", "article",
    ]
    TITLE_SELECTORS = ["h1", "h2", "h3", "[class*='title']", "[class*='name']", "a[title]"]
    PRICE_PATTERNS = [
        r"(?:giá|gia)\s*:?\s*([\d,.]+\s*(?:tỷ|ty|triệu|trieu|nghìn|ngàn|ngan))",
        r"([\d,.]+\s*(?:tỷ|ty|triệu|trieu|nghìn|ngàn|ngan)(?:\s*/\s*m2)?)",
        r"(thỏa thuận|thoả thuận|liên hệ|lien he)",
    ]

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        soup = BeautifulSoup(html or "", "html.parser")
        records = []
        timestamp = int(datetime.now().timestamp())

        for selector in self.LISTING_SELECTORS:
            elements = soup.select(selector)
            if not elements: continue
            
            for el in elements:
                text = el.get_text(" ", strip=True).lower()
                
                # Title
                title = ""
                for t_sel in self.TITLE_SELECTORS:
                    t_el = el.select_one(t_sel)
                    if t_el:
                        title = t_el.get_text(" ", strip=True)
                        break
                if not title: title = "Real Estate Listing"
                
                # Price
                price = None
                for pattern in self.PRICE_PATTERNS:
                    match = re.search(pattern, text)
                    if match:
                        price = clean_real_estate_price(match.group(1))
                        if price: break

                # Area
                area = clean_area_m2(text)
                
                if price or area:
                    records.append({
                        "datetime": timestamp,
                        "title": title,
                        "price": price,
                        "area_m2": area,
                        "location": "Unknown",
                        "source": self.url
                    })
            if records: break

        return records if records else None

class BatdongsanCrawler(RealEstateBaseCrawler):
    def __init__(self, profile_name="default"):
        super().__init__("https://batdongsan.com.vn/nha-dat-ban", profile_name)

class AloNhaDatCrawler(RealEstateBaseCrawler):
    def __init__(self, profile_name="default"):
        super().__init__("https://alonhadat.com.vn/nha-dat/can-ban.html", profile_name)
