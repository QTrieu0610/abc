import os
import json
import requests
from typing import List, Dict, Optional
from bs4 import Comment, BeautifulSoup
from datetime import datetime

from crawlers.base import BaseCrawler
from crawlers.utils import clean_price

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
        soup = BeautifulSoup(html or "", "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav", "svg", "img"]):
            tag.decompose()
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        return " ".join(soup.get_text(" ", strip=True).split())

    def _call_llm(self, prompt: str, content: str) -> Optional[Dict]:
        clean_text = self._clean_html(content)[:12000]
        full_prompt = f"{prompt}\n\nContext:\n{clean_text}"
        
        use_ollama = not bool(self.openai_api_key) or "gemma" in self.ai_model.lower() or "llama" in self.ai_model.lower()
        
        if use_ollama:
            actual_model = self.ai_model
            print(f"[*] Calling Local LLM ({actual_model}) via Ollama...")
            endpoint = self.ollama_url
            if "api/generate" in endpoint:
                endpoint = endpoint.replace("api/generate", "v1/chat/completions")
            elif not endpoint.endswith("/v1/chat/completions"):
                endpoint = endpoint.rstrip('/') + "/v1/chat/completions"
                
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": actual_model,
                "messages": [
                    {"role": "system", "content": "You are a data extraction assistant. Always respond with raw valid JSON only, no markdown formatting like ```json."},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": 0.1
            }
        else:
            print(f"[*] Calling Cloud LLM ({self.ai_model}) via OpenAI-compatible endpoint...")
            endpoint = "https://api.openai.com/v1/chat/completions"
            if "deepseek" in self.ai_model.lower() or "deepseek" in (os.environ.get("DEEPSEEK_API_KEY") or ""):
                endpoint = "https://api.deepseek.com/chat/completions"

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.ai_model,
                "messages": [
                    {"role": "system", "content": "You are a data extraction assistant. Always respond with raw valid JSON only, no markdown formatting like ```json."},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": 0.1
            }

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, verify=self.openai_verify_ssl, timeout=120)
            resp.raise_for_status()
            result_text = resp.json()["choices"][0]["message"]["content"]
            
            # Clean JSON formatting
            if result_text.startswith("```json"):
                result_text = result_text.strip("```json").strip("```").strip()
            return json.loads(result_text)
        except Exception as e:
            print(f"[-] LLM Call failed: {e}")
            return None

class GenericGoldCrawler(GenericLLMCrawler):
    def _tier_3_ai_parse(self, html: str) -> Optional[List[Dict]]:
        prompt = (
            "Extract gold prices from the provided text. Look for SJC, DOJI, PNJ, or 9999 gold types. "
            "Return a JSON array of objects, each containing: 'gold_type', 'buy_price' (integer), 'sell_price' (integer), 'location'. "
            "If no gold prices are found, return an empty array []."
        )
        data = self._call_llm(prompt, html)
        if not data: return None
        
        timestamp = int(datetime.now().timestamp())
        records = []
        for item in data:
            records.append({
                "datetime": timestamp,
                "company": "Generic",
                "gold_type": item.get("gold_type", "Unknown"),
                "buy_price": item.get("buy_price", 0),
                "sell_price": item.get("sell_price", 0),
                "location": item.get("location", "National"),
                "source": self.url
            })
        return records

class GenericRealEstateCrawler(GenericLLMCrawler):
    def _tier_3_ai_parse(self, html: str) -> Optional[List[Dict]]:
        prompt = (
            "Extract real estate listings from the text. "
            "Return a JSON array of objects, each containing: 'title', 'price' (integer VND), 'area_m2' (float), 'location'. "
            "If no real estate listings are found, return an empty array []."
        )
        data = self._call_llm(prompt, html)
        if not data: return None
        
        timestamp = int(datetime.now().timestamp())
        records = []
        for item in data:
            records.append({
                "datetime": timestamp,
                "title": item.get("title", "Unknown"),
                "price": item.get("price", 0),
                "area_m2": item.get("area_m2", 0),
                "location": item.get("location", "Unknown"),
                "source": self.url
            })
        return records
