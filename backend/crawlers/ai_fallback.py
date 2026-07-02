import os
import json
import re
import requests
from typing import List, Dict, Optional
from bs4 import Comment, BeautifulSoup
from datetime import datetime

from crawlers.base import BaseCrawler
from crawlers.utils import clean_price, clean_real_estate_price, clean_area_m2, html_to_clean_markdown

class GenericLLMCrawler(BaseCrawler):
    def __init__(self, url: str, profile_name="generic"):
        super().__init__(url, profile_name)
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        self.ai_model = os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_FALLBACK_MODEL") or "gemma4:e2b"
        self.openai_verify_ssl = os.environ.get("OPENAI_VERIFY_SSL", "true").lower() not in ["0", "false", "no"]

    def _tier_1_static_parse(self, html: str) -> Optional[List[Dict]]:
        return None # Generic crawlers never parse statically

    def _clean_html(self, html: str) -> str:
        return html_to_clean_markdown(html)

    def _call_llm(self, prompt: str, content: str, response_schema: Optional[Dict] = None) -> Optional[Dict]:
        clean_text = self._clean_html(content)[:12000]
        full_prompt = f"{prompt}\n\nContext:\n{clean_text}"
        
        use_ollama = not bool(self.openai_api_key) or "gemma" in self.ai_model.lower() or "llama" in self.ai_model.lower()
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": self.ai_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a data extraction assistant. Always respond with raw valid JSON matching the requested schema. Do not output markdown fences or any conversational text."
                },
                {"role": "user", "content": full_prompt}
            ],
            "temperature": 0.1
        }
        
        if use_ollama:
            actual_model = self.ai_model
            print(f"[*] Calling Local LLM ({actual_model}) via Ollama...")
            endpoint = self.ollama_url
            if "api/generate" in endpoint:
                endpoint = endpoint.replace("api/generate", "v1/chat/completions")
            elif not endpoint.endswith("/v1/chat/completions"):
                endpoint = endpoint.rstrip('/') + "/v1/chat/completions"
        else:
            print(f"[*] Calling Cloud LLM ({self.ai_model}) via OpenAI-compatible endpoint...")
            endpoint = "https://api.openai.com/v1/chat/completions"
            if "deepseek" in self.ai_model.lower() or "deepseek" in (os.environ.get("DEEPSEEK_API_KEY") or ""):
                endpoint = "https://api.deepseek.com/chat/completions"
            headers["Authorization"] = f"Bearer {self.openai_api_key}"

        if response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "extracted_data",
                    "strict": True,
                    "schema": response_schema
                }
            }
        else:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, verify=self.openai_verify_ssl, timeout=120)
            if resp.status_code == 400 and response_schema:
                # Schema fallback if API returns error
                print("[-] JSON Schema format rejected by provider. Retrying with basic JSON mode...")
                payload["response_format"] = {"type": "json_object"}
                resp = requests.post(endpoint, headers=headers, json=payload, verify=self.openai_verify_ssl, timeout=120)
                
            resp.raise_for_status()
            result_text = resp.json()["choices"][0]["message"]["content"].strip()
            
            # Clean possible markdown block markers
            if result_text.startswith("```"):
                result_text = re.sub(r"^```(?:json)?\s*", "", result_text)
                result_text = re.sub(r"\s*```$", "", result_text)
                result_text = result_text.strip()
                
            return json.loads(result_text)
        except Exception as e:
            print(f"[-] LLM Call failed: {e}")
            return None

class GenericGoldCrawler(GenericLLMCrawler):
    def _tier_3_ai_parse(self, html: str) -> Optional[List[Dict]]:
        prompt = (
            "Extract all gold buy and sell prices from the text. Look for companies like SJC, DOJI, PNJ, or others. "
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
            
            # Perform additional sanitization on LLM output
            buy = clean_price(str(buy_raw)) if buy_raw is not None else None
            sell = clean_price(str(sell_raw)) if sell_raw is not None else None
            
            company = item.get("company") or "Generic"
            if company.lower() == "generic":
                # Fallback to the domain of the URL if generic
                from urllib.parse import urlparse
                domain = urlparse(self.url).netloc.replace("www.", "")
                company = domain.split(".")[0].upper()
            
            records.append({
                "datetime": timestamp,
                "company": company,
                "gold_type": item.get("gold_type", "Unknown"),
                "buy_price": buy,
                "sell_price": sell,
                "location": item.get("location") or "National",
                "source": self.url
            })
        return records

class GenericRealEstateCrawler(GenericLLMCrawler):
    def _tier_3_ai_parse(self, html: str) -> Optional[List[Dict]]:
        prompt = (
            "Extract real estate listings from the text. "
            "Identify the title, price details, area in m2, and location. "
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
                            "title": {"type": "string"},
                            "price": {"type": ["integer", "string", "null"]},
                            "price_text": {"type": ["string", "null"]},
                            "area_m2": {"type": ["number", "string", "null"]},
                            "location": {"type": ["string", "null"]}
                        },
                        "required": ["title", "price", "price_text", "area_m2", "location"],
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
            price_raw = item.get("price")
            area_raw = item.get("area_m2")
            
            # Post-process LLM values using cleaning utilities
            price = clean_real_estate_price(str(price_raw)) if price_raw is not None else None
            area = clean_area_m2(str(area_raw)) if area_raw is not None else None
            
            # Calculate price per m2
            price_per_m2 = None
            if price and area:
                price_per_m2 = int(price / area)
                
            records.append({
                "datetime": timestamp,
                "title": item.get("title", "Unknown"),
                "price": price,
                "price_text": item.get("price_text") or str(price_raw or "Thỏa thuận"),
                "area_m2": area,
                "price_per_m2": price_per_m2,
                "location": item.get("location") or "Unknown",
                "source": self.url
            })
        return records
