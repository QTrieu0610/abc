import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse

from crawlers.ai_fallback import GenericLLMCrawler
from crawlers.utils import clean_price

class BaseTableCrawler(GenericLLMCrawler):
    """
    Highly reusable base crawler for parsing gold/pricing tables statically from HTML.
    Supports dynamic table discovery, dynamic column index detection, Custom keyword mapping,
    geographic location matching, and multiple output format rendering (flat vs normalized).
    Inherits from GenericLLMCrawler to automatically support Tier 3 fallback via LLMs.
    """
    def __init__(
        self, 
        url: str, 
        table_selector: Optional[str] = None,
        gold_type_mapping: Optional[Dict[str, str]] = None,
        output_format: str = "normalized",
        default_location: str = "National",
        location_mapping: Optional[Dict[str, str]] = None,
        company_name: str = "Generic",
        profile_name: str = "default"
    ):
        super().__init__(url, profile_name)
        self.table_selector = table_selector
        self.gold_type_mapping = gold_type_mapping or {}
        self.output_format = output_format.lower()
        self.default_location = default_location
        self.location_mapping = location_mapping or {}
        
        # Resolve dynamic company name for Autopilot
        if company_name == "Generic":
            domain = urlparse(url).netloc.replace("www.", "")
            if domain:
                company_name = domain.split(".")[0].upper()
            else:
                company_name = "GENERIC"
        self.company_name = company_name

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip().lower()

    def _map_gold_type(self, raw_name: str) -> Optional[str]:
        normalized = self._normalize_text(raw_name)
        for keyword, mapped_val in self.gold_type_mapping.items():
            if keyword in normalized:
                return mapped_val
        return None

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        soup = BeautifulSoup(html or "", "html.parser")
        
        # 1. Locate tables
        tables = []
        if self.table_selector:
            tables = soup.select(self.table_selector)
        else:
            # Fallback search heuristic: find tables with gold/price header words
            for candidate in soup.find_all("table"):
                header_text = candidate.get_text(" ", strip=True).lower()
                if any(kw in header_text for kw in ["loại", "vàng", "mua", "bán"]):
                    tables.append(candidate)
                    
        if not tables:
            return None

        records = []
        flat_result = {}
        timestamp = int(datetime.now().timestamp())

        for table in tables:
            # Determine location for DOJI-like regional tables
            location = self.default_location
            if self.location_mapping:
                previous = table.find_previous(["h1", "h2", "h3", "h4", "strong", "div"])
                if previous:
                    heading_text = self._normalize_text(previous.get_text())
                    for marker, loc in self.location_mapping.items():
                        if marker in heading_text:
                            location = loc
                            break

            # Dynamic column discovery
            header_row = table.find("tr")
            name_idx, buy_idx, sell_idx = None, None, None
            if header_row:
                headers = [h.get_text(" ", strip=True).lower() for h in header_row.find_all(["th", "td"])]
                for idx, h in enumerate(headers):
                    if any(kw in h for kw in ["loại", "nhóm", "tên", "sản phẩm"]):
                        name_idx = idx
                    elif "mua" in h:
                        buy_idx = idx
                    elif "bán" in h:
                        sell_idx = idx

            # Fallback column heuristics using content type scoring
            if name_idx is None or buy_idx is None or sell_idx is None:
                first_data_tr = None
                for row in table.find_all("tr"):
                    tds = row.find_all(["td", "th"])
                    if len(tds) >= 3:
                        # Skip header rows
                        text = tds[0].get_text(" ", strip=True).lower()
                        if any(kw in text for kw in ["loại vàng", "khu vực", "nhóm sản phẩm"]):
                            continue
                        first_data_tr = [c.get_text(" ", strip=True) for c in tds]
                        break
                        
                if first_data_tr:
                    # Find columns containing alphabetic text and those containing prices
                    text_indices = []
                    price_indices = []
                    for idx, val in enumerate(first_data_tr):
                        num_val = clean_price(val)
                        if num_val is not None and num_val > 10000:
                            price_indices.append(idx)
                        else:
                            if any(c.isalpha() for c in val):
                                text_indices.append(idx)
                                
                    if text_indices:
                        name_idx = text_indices[-1] # The last text column is usually the gold name
                    else:
                        name_idx = 0
                        
                    # Match buy/sell from the price columns
                    valid_prices = [idx for idx in price_indices if idx != name_idx]
                    if len(valid_prices) >= 2:
                        buy_idx = valid_prices[0]
                        sell_idx = valid_prices[1]
                    elif len(valid_prices) == 1:
                        buy_idx = valid_prices[0]
                        sell_idx = valid_prices[0]
                    else:
                        buy_idx, sell_idx = 1, 2
                else:
                    name_idx, buy_idx, sell_idx = 0, 1, 2

            # Parse table rows
            for row in table.find_all("tr"):
                cols = row.find_all(["td", "th"])
                if len(cols) < 3:
                    continue

                try:
                    raw_name = cols[name_idx].get_text(" ", strip=True)
                    raw_buy = cols[buy_idx].get_text(" ", strip=True)
                    raw_sell = cols[sell_idx].get_text(" ", strip=True)
                except IndexError:
                    continue

                # Skip header rows
                if "loại vàng" in raw_name.lower() or "mua vào" in raw_buy.lower() or "bán ra" in raw_sell.lower():
                    continue

                mapped_gold_type = self._map_gold_type(raw_name)
                
                # Autopilot mapping check
                if not mapped_gold_type:
                    if self.gold_type_mapping:
                        # If a mapping was defined but this item didn't match it, skip it
                        continue
                    else:
                        # Autopilot Mode: no mapping defined, keep the raw name as gold type
                        mapped_gold_type = raw_name

                buy = clean_price(raw_buy)
                sell = clean_price(raw_sell)

                if buy is None and sell is None:
                    continue

                if self.output_format == "flat":
                    # Flat dictionary format (SJC style)
                    flat_result[f"buy_{mapped_gold_type}"] = buy
                    flat_result[f"sell_{mapped_gold_type}"] = sell
                else:
                    # Normalized list format (DOJI/PNJ style)
                    records.append({
                        "datetime": timestamp,
                        "company": self.company_name,
                        "gold_type": mapped_gold_type,
                        "buy_price": buy,
                        "sell_price": sell,
                        "location": location,
                        "source": self.url
                    })

        if self.output_format == "flat":
            if not flat_result:
                return None
            flat_result["datetime"] = timestamp
            return [flat_result]
        else:
            return records if records else None

    def _tier_3_ai_parse(self, html: str) -> Optional[List[Dict]]:
        """
        Fallback Tier 3: LLM Data Extraction when static HTML parsing fails.
        Converts content to clean Markdown and requests strict structured JSON.
        """
        print(f"[*] BaseTableCrawler Falling back to Tier 3 LLM (Autopilot)...")
        prompt = (
            f"Extract all gold buy and sell prices from the text. Look for companies like {self.company_name} or others. "
            "Identify the gold products (types), buy prices, sell prices, and locations. "
            "Return a JSON object containing a 'records' list of objects."
        )
        schema = {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "company": {"type": ["string", "null"]},
                            "gold_type": {"type": "string"},
                            "buy_price": {"type": ["integer", "string", "null"]},
                            "sell_price": {"type": ["integer", "string", "null"]},
                            "location": {"type": ["string", "null"]}
                        },
                        "required": ["company", "gold_type", "buy_price", "sell_price", "location"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["records"],
            "additionalProperties": False
        }
        
        data = self._call_llm(prompt, html, response_schema=schema)
        if not data:
            return None
            
        records_list = []
        if isinstance(data, dict):
            records_list = data.get("records") or []
        elif isinstance(data, list):
            records_list = data
            
        timestamp = int(datetime.now().timestamp())
        records = []
        
        for item in records_list:
            buy_raw = item.get("buy_price")
            sell_raw = item.get("sell_price")
            buy = clean_price(str(buy_raw)) if buy_raw is not None else None
            sell = clean_price(str(sell_raw)) if sell_raw is not None else None
            
            gold_type = item.get("gold_type", "Unknown")
            mapped_gold_type = self._map_gold_type(gold_type) if self.gold_type_mapping else gold_type
            
            if self.gold_type_mapping and not mapped_gold_type:
                # If mapping is defined but the AI extracted type doesn't match, skip
                continue

            company = item.get("company") or self.company_name
            if company.lower() == "generic":
                company = self.company_name
            
            records.append({
                "datetime": timestamp,
                "company": company,
                "gold_type": mapped_gold_type,
                "buy_price": buy,
                "sell_price": sell,
                "location": item.get("location") or self.default_location,
                "source": self.url
            })
            
        # Format mapping back to SJC-style if needed
        if self.output_format == "flat" and records:
            flat_result = {}
            for r in records:
                flat_result[f"buy_{r['gold_type']}"] = r["buy_price"]
                flat_result[f"sell_{r['gold_type']}"] = r["sell_price"]
            flat_result["datetime"] = timestamp
            return [flat_result]
            
        return records if records else None
