from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

router = APIRouter()

CONFIG_DIR = 'config'
GOLD_TARGETS_FILE = os.path.join(CONFIG_DIR, 'gold_targets.json')
REAL_ESTATE_TARGETS_FILE = os.path.join(CONFIG_DIR, 'real_estate_targets.json')

class TargetRequest(BaseModel):
    id: str
    url: str

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
    for t in targets:
        if t['id'] == target.id:
            raise HTTPException(status_code=400, detail="ID already exists")
    targets.append({'id': target.id, 'url': target.url, 'label': target_type})
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
