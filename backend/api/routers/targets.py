from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

from typing import Optional
from urllib.parse import urlparse
import re

router = APIRouter()

CONFIG_DIR = 'config'
GOLD_TARGETS_FILE = os.path.join(CONFIG_DIR, 'gold_targets.json')
REAL_ESTATE_TARGETS_FILE = os.path.join(CONFIG_DIR, 'real_estate_targets.json')

class TargetRequest(BaseModel):
    id: Optional[str] = None
    url: str

def generate_id_from_url(url: str, existing_ids: list) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        host = host.split(':')[0]  # Remove port
        parts = host.split('.')
        if len(parts) > 1:
            if parts[0] == 'web' or parts[0] == 'www':
                domain = parts[1]
            else:
                domain = parts[0]
        else:
            domain = host
        slug = re.sub(r'[^a-zA-Z0-9]', '', domain).lower()
        if not slug:
            slug = "target"
    except Exception:
        slug = "target"

    base_slug = slug
    counter = 1
    while slug in existing_ids:
        slug = f"{base_slug}_{counter}"
        counter += 1
    return slug

def get_file_path(target_type: str):
    if target_type == 'gold':
        return GOLD_TARGETS_FILE
    elif target_type == 'real_estate':
        return REAL_ESTATE_TARGETS_FILE
    else:
        raise HTTPException(status_code=400, detail="Invalid target type. Use 'gold' or 'real_estate'")

def read_targets(target_type: str):
    file_path = get_file_path(target_type)
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_targets(target_type: str, targets: list):
    file_path = get_file_path(target_type)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(targets, f, indent=4)

@router.get("/api/targets/{target_type}")
async def get_targets(target_type: str):
    return read_targets(target_type)

@router.post("/api/targets/{target_type}")
async def add_target(target_type: str, target: TargetRequest):
    targets = read_targets(target_type)
    existing_ids = [t['id'] for t in targets]
    
    target_id = target.id
    if not target_id or not target_id.strip():
        target_id = generate_id_from_url(target.url, existing_ids)
    else:
        target_id = re.sub(r'[^a-zA-Z0-9_-]', '', target_id).lower()
        if target_id in existing_ids:
            raise HTTPException(status_code=400, detail="ID already exists")
            
    targets.append({'id': target_id, 'url': target.url, 'label': target_type})
    write_targets(target_type, targets)
    return {"status": "success", "message": "Target added successfully"}

@router.delete("/api/targets/{target_type}/{target_id}")
async def delete_target(target_type: str, target_id: str):
    targets = read_targets(target_type)
    original_len = len(targets)
    targets = [t for t in targets if t['id'] != target_id]
    if len(targets) == original_len:
        raise HTTPException(status_code=404, detail="Target not found")
    write_targets(target_type, targets)
    return {"status": "success", "message": "Target deleted successfully"}
