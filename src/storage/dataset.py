#!/usr/bin/env python3
from __future__ import annotations

import glob
import os
import json
import logger

from pathlib import Path

class DatasetStorage:
    """
    Handles direct file-based persistence for the NPC-Forge datasets.
    Bypasses natural language processing to read and write raw NDF structures.
    """
    
    def __init__(self) -> None:
        pass

    def save_entry(
        self, 
        ndf_object: dict, 
        dataset_dir: str, 
        dataset_file: str = "dataset_generated_by_user.json"
    ) -> bool:
        """Appends the generated NDF object securely to the target dataset."""
        dataset_path = Path(dataset_dir) / dataset_file
        os.makedirs(dataset_path.parent, exist_ok=True)
        
        existing_data = []
        if dataset_path.exists():
            try:
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = []
            except Exception:
                existing_data = []
                
        existing_data.append(ndf_object)
        
        try:
            with open(dataset_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def load_json(self, path, name):
        try:
            with open(os.path.join(path, name), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON file load error. Path: {os.path.join(path, name)} Error: {e}")
            return None

    def load_json_recursive(self, path, name):
        templates = []
        for f in glob.glob(os.path.join(path, "**", name), recursive=True):
            data = self.load_json(os.path.dirname(f), os.path.basename(f))
            if isinstance(data, list): templates.extend(data)
            elif isinstance(data, dict): templates.append(data)
        return templates