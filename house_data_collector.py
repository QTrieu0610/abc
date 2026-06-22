import csv
import os
from datetime import datetime
from typing import Dict, List, Optional

from data_collector import csv_lock


class HousePriceDataCollector:
    """Persist current house-price crawler records to CSV."""

    DATA_DIR = "house_price_data"
    DEFAULT_FILENAME = "house_price_listings.csv"
    FIELDNAMES = [
        "timestamp",
        "source",
        "property_type",
        "title",
        "price",
        "price_text",
        "area_m2",
        "area_text",
        "price_per_m2",
        "location",
        "url",
    ]

    def __init__(self, data_dir: Optional[str] = None):
        self.DATA_DIR = data_dir or self.DATA_DIR
        os.makedirs(self.DATA_DIR, exist_ok=True)

    def default_path(self) -> str:
        return os.path.join(self.DATA_DIR, self.DEFAULT_FILENAME)

    def append_to_csv(self, data: Dict[str, Dict], filename: Optional[str] = None) -> int:
        filename = filename or self.default_path()
        rows = self._payload_to_rows(data)
        if not rows:
            print("[-] No house price data to save")
            return 0

        with csv_lock:
            existing = self.load_csv_data(filename)
            existing_keys = {self._dedupe_key(row) for row in existing}
            new_rows = [
                row
                for row in rows
                if self._dedupe_key(row) not in existing_keys
            ]

            if not new_rows:
                print("[*] House price CSV already has the latest listings")
                return 0

            all_rows = existing + new_rows
            all_rows.sort(key=lambda row: row.get("timestamp", ""), reverse=True)

            os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(all_rows)

        print(f"[+] Saved {len(new_rows)} house price records to {filename}")
        return len(new_rows)

    def load_csv_data(self, filename: Optional[str] = None) -> List[Dict]:
        filename = filename or self.default_path()
        if not os.path.exists(filename):
            return []

        with csv_lock:
            with open(filename, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                return list(reader)

    def _payload_to_rows(self, data: Dict[str, Dict]) -> List[Dict]:
        rows = []
        for source_key, payload in (data or {}).items():
            if not isinstance(payload, dict) or payload.get("status") != "ok":
                continue
            records = payload.get("results") if isinstance(payload.get("results"), list) else []
            for record in records:
                if not isinstance(record, dict):
                    continue
                rows.append(self._record_to_row(source_key, record))
        return rows

    def _record_to_row(self, source_key: str, record: Dict) -> Dict:
        timestamp = record.get("datetime")
        try:
            timestamp = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OSError):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "timestamp": timestamp,
            "source": record.get("source") or source_key.upper(),
            "property_type": record.get("property_type") or "Real Estate",
            "title": record.get("title"),
            "price": record.get("price"),
            "price_text": record.get("price_text"),
            "area_m2": record.get("area_m2"),
            "area_text": record.get("area_text"),
            "price_per_m2": record.get("price_per_m2"),
            "location": record.get("location"),
            "url": record.get("url"),
        }

    @staticmethod
    def _dedupe_key(row: Dict) -> tuple:
        return (
            row.get("source"),
            row.get("title"),
            row.get("price_text"),
            row.get("area_text"),
            row.get("url"),
        )
