import re
from typing import Optional, Dict, List

def clean_price(price_str: Optional[str]) -> Optional[int]:
    """Normalize Vietnamese gold prices to VND per chi."""
    if not price_str:
        return None

    cleaned = re.sub(r"[^\d]", "", str(price_str))
    if not cleaned:
        return None

    value = int(cleaned)
    if value < 100000:
        value *= 1000
    return value

def clean_real_estate_price(price_str: Optional[str]) -> Optional[int]:
    """Normalize Vietnamese real-estate prices to VND."""
    if not price_str:
        return None

    value = str(price_str).lower().strip()
    value = value.replace(",", ".")
    if any(token in value for token in ["thỏa thuận", "thoả thuận", "liên hệ", "lien he"]):
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", value)
    if not match:
        return None

    amount = float(match.group(1))
    if "tỷ" in value or "ty" in value:
        amount *= 1_000_000_000
    elif "triệu" in value or "trieu" in value:
        amount *= 1_000_000
    elif "nghìn" in value or "ngan" in value or "ngàn" in value:
        amount *= 1_000

    return int(amount)

def clean_area_m2(area_str: Optional[str]) -> Optional[float]:
    """Extract a square-meter value from Vietnamese real-estate text."""
    if not area_str:
        return None

    value = str(area_str).lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m2|m²|m\s*2)", value)
    if not match:
        return None
    return float(match.group(1))

def source_result(status: str, results: Optional[List[Dict]] = None, error: Optional[str] = None) -> Dict:
    return {
        "status": status,
        "results": results or [],
        "error": error,
    }
