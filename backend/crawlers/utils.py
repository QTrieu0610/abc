import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup, Comment

def html_to_clean_markdown(html_content: str) -> str:
    """
    Convert HTML content to clean, structured Markdown.
    Strips scripts, styles, navs, headers, footers, forms and returns
    headings, tables, lists, and bold/italic elements as Markdown.
    """
    if not html_content:
        return ""
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove unwanted elements
    for tag in soup(["script", "style", "header", "footer", "nav", "svg", "img", "iframe", "noscript", "form"]):
        tag.decompose()
        
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        
    # Helper to convert elements to markdown recursively
    def convert_element(element) -> str:
        if element.name is None:
            # Text node
            return element.string or ""
            
        name = element.name.lower()
        
        # Process children
        children_text = "".join(convert_element(child) for child in element.children)
        
        if name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(name[1])
            return f"\n\n{'#' * level} {children_text.strip()}\n\n"
        elif name == "p":
            return f"\n\n{children_text.strip()}\n\n"
        elif name == "br":
            return "\n"
        elif name in ["ul", "ol"]:
            return f"\n{children_text}\n"
        elif name == "li":
            return f"* {children_text.strip()}\n"
        elif name == "table":
            rows = []
            for tr in element.find_all("tr", recursive=True):
                cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"], recursive=False)]
                if cells:
                    rows.append("| " + " | ".join(cells) + " |")
            if not rows:
                return ""
            # Add separator after header row
            if len(rows) > 0:
                header_cells_count = len(rows[0].split("|")) - 2
                if header_cells_count > 0:
                    separator = "| " + " | ".join(["---"] * header_cells_count) + " |"
                    rows.insert(1, separator)
            return "\n\n" + "\n".join(rows) + "\n\n"
        elif name in ["div", "section", "article"]:
            return f"\n{children_text}\n"
        elif name in ["strong", "b"]:
            return f"**{children_text.strip()}**"
        elif name in ["em", "i"]:
            return f"*{children_text.strip()}*"
        else:
            return children_text

    markdown = convert_element(soup.body or soup)
    # Clean up multiple newlines and spaces
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = re.sub(r' {2,}', ' ', markdown)
    return markdown.strip()

def clean_price(price_str: Optional[str]) -> Optional[int]:
    """Normalize Vietnamese gold prices to VND per chi/luong."""
    if not price_str:
        return None

    value_str = str(price_str).lower().strip()
    
    # Check if price is in million VND format (e.g., "80.50 triệu" or "80.50 tr")
    if "triệu" in value_str or "tr" in value_str or "trieu" in value_str:
        match = re.search(r"(\d+(?:[.,]\d+)?)", value_str)
        if match:
            val = float(match.group(1).replace(",", "."))
            value = int(val * 1_000_000)
            if value > 100_000_000:
                value //= 10
            return value

    # Split by whitespace and take the first token to ignore any change indicators (e.g. "145,400 2000")
    parts = value_str.split()
    if parts:
        if any(c.isdigit() for c in parts[0]):
            value_str = parts[0]

    # Clean non-digit characters except dots/commas
    value_str = re.sub(r"[^\d.,]", "", value_str)
    value_str = value_str.strip(".,")
    if not value_str:
        return None
        
    # Standardize commas to dots
    value_str = value_str.replace(",", ".")
    
    # If there are multiple dots, it's just thousands separators (e.g. 80.500.000)
    if value_str.count(".") > 1:
        value_str = value_str.replace(".", "")
        
    # If there's exactly one dot
    elif value_str.count(".") == 1:
        parts = value_str.split(".")
        if len(parts[1]) == 3: # e.g. 80.500
            val = float(value_str)
            if val < 1000:
                value_str = str(int(val * 1_000_000))
            else:
                value_str = value_str.replace(".", "")
        else:
            val = float(value_str)
            if val < 1000:
                value_str = str(int(val * 1_000_000))
            else:
                value_str = value_str.replace(".", "")

    try:
        value = int(float(value_str))
        # If it's something like 80500 (PNJ format, representing 80,500,000 VND / lượng)
        if value < 100000:
            value *= 1000
            
        # Normalize gold prices to VND per chi (around 14 million VND)
        # If the price is per luong (e.g. > 100 million VND), divide by 10 to get price per chi
        if value > 100_000_000:
            value //= 10
            
        return value
    except ValueError:
        return None

def clean_real_estate_price(price_str: Optional[str]) -> Optional[int]:
    """Normalize Vietnamese real-estate prices to VND."""
    if not price_str:
        return None

    value = str(price_str).lower().strip()
    
    if any(token in value for token in ["thỏa thuận", "thoả thuận", "liên hệ", "lien he"]):
        return None

    tỷ_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:tỷ|ty|tỉ)", value)
    tr_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)", value)
    
    total_vnd = 0.0
    found = False
    
    if tỷ_match:
        tỷ_val = float(tỷ_match.group(1).replace(",", "."))
        total_vnd += tỷ_val * 1_000_000_000
        found = True
        
        # Look for a trailing million part, e.g. "1 tỷ 200 triệu"
        billion_end = tỷ_match.end()
        post_value = value[billion_end:]
        tr_submatch = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr)", post_value)
        if tr_submatch:
            tr_val = float(tr_submatch.group(1).replace(",", "."))
            total_vnd += tr_val * 1_000_000
    elif tr_match:
        tr_val = float(tr_match.group(1).replace(",", "."))
        total_vnd += tr_val * 1_000_000
        found = True
    else:
        # Standard pure number format
        cleaned = re.sub(r"[^\d]", "", value)
        if cleaned:
            total_vnd = float(cleaned)
            found = True
            
    if not found:
        return None
        
    return int(total_vnd)

def clean_area_m2(area_str: Optional[str]) -> Optional[float]:
    """Extract a square-meter value from Vietnamese real-estate text."""
    if not area_str:
        return None

    value = str(area_str).lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m2|m²|mét vuông|met vuong|m\s*2)", value)
    if not match:
        # Try to fallback to any number if no unit matches
        match_any = re.search(r"(\d+(?:\.\d+)?)", value)
        if match_any:
            return float(match_any.group(1))
        return None
    return float(match.group(1))

def source_result(status: str, results: Optional[List[Dict]] = None, error: Optional[str] = None) -> Dict:
    return {
        "status": status,
        "results": results or [],
        "error": error,
    }
