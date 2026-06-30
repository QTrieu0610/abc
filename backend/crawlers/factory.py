from typing import Type
from crawlers.base import BaseCrawler
from crawlers.gold import SjcWebGiaCrawler, DojiCrawler, PnjCrawler
from crawlers.real_estate import BatdongsanCrawler, AloNhaDatCrawler
from crawlers.ai_fallback import GenericGoldCrawler, GenericRealEstateCrawler

class CrawlerFactory:
    """
    Smart Router for allocating the correct crawler based on URL and requested label.
    It performs validation, mismatch detection, and routing.
    """
    
    @staticmethod
    def get_crawler(url: str, label: str) -> BaseCrawler:
        label = label.lower().strip()
        url_lower = url.lower()
        
        # 1. Known Gold Sites
        if "webgia.com" in url_lower:
            if label != "gold": raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return SjcWebGiaCrawler()
        if "doji.vn" in url_lower:
            if label != "gold": raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return DojiCrawler()
        if "pnj.com.vn" in url_lower or "pnj.io" in url_lower:
            if label != "gold": raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return PnjCrawler()
            
        # 2. Known Real Estate Sites
        if "batdongsan.com.vn" in url_lower:
            if label != "real_estate": raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return BatdongsanCrawler()
        if "alonhadat.com.vn" in url_lower:
            if label != "real_estate": raise ValueError("Hình như bạn chọn nhầm loại dữ liệu")
            return AloNhaDatCrawler()

        # 3. Unknown Sites - Fallback to AI
        # We don't reject unknown domains completely; we pass them to AI.
        # If the domain is totally unrelated (e.g., youtube.com), the AI prompt will 
        # naturally fail to extract data and return an empty result securely.
        if label == "gold":
            return GenericGoldCrawler(url=url)
        elif label == "real_estate":
            return GenericRealEstateCrawler(url=url)
        else:
            raise ValueError(f"Label không hợp lệ: {label}. Chỉ hỗ trợ 'gold' hoặc 'real_estate'.")
