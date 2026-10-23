#!/usr/bin/env python3
from __future__ import annotations

import glob
import os
import json
import urllib.request

from pathlib import Path
from logger import logger

class DatasetStorage:
    """
    Handles direct file-based persistence for the NPC-Forge datasets.
    Automatically supports both legacy .json and high-performance .jsonl formats,
    even when wildcard patterns are used.
    """
    
    def __init__(self) -> None:
        pass

    def save_entry(
        self, 
        ndf_object: dict, 
        dataset_dir: str, 
        dataset_file: str = "dataset_generated_by_user.jsonl" 
    ) -> bool:
        """Appends the generated NDF object securely to the target dataset."""
        dataset_path = Path(dataset_dir) / dataset_file
        os.makedirs(dataset_path.parent, exist_ok=True)
        
        ext = dataset_path.suffix.lower()
        
        try:
            if ext == ".jsonl":
                # High-performance O(1) append for JSONL
                with open(dataset_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ndf_object, ensure_ascii=False) + "\n")
            else:
                # Legacy fallback for .json (reads, appends, rewrites)
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
                
                with open(dataset_path, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save entry to {dataset_path}: {e}")
            return False

    def load_file(self, file_path: str | Path):
        """
        Core loader. 
        Returns a list for .jsonl files.
        Returns the RAW parsed object (dict or list) for .json files.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return None
            
        ext = file_path.suffix.lower()
        
        try:
            if ext == ".jsonl":
                data = []
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(json.loads(line))
                return data
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"File load error. Path: {file_path} Error: {e}")
            return None

    def load_json(self, path, name):
        """
        Loads a specific file. Automatically falls back to .jsonl 
        if the requested .json file does not exist.
        """
        file_path = os.path.join(path, name)
        
        # If the requested .json file doesn't exist, but the .jsonl version does, try that
        if not os.path.exists(file_path) and name.endswith(".json"):
            jsonl_path = file_path[:-5] + ".jsonl"
            if os.path.exists(jsonl_path):
                return self.load_file(jsonl_path)
                
        return self.load_file(file_path)

    def load_json_recursive(self, path, name="*"):
        """
        Recursively finds and loads all matching .json and .jsonl files into a flat list.
        """
        templates = []
        
        # Glob finds everything matching the pattern (e.g., "dataset_*")
        for f in glob.glob(os.path.join(path, "**", name), recursive=True):
            # Only process valid dataset file extensions
            if f.endswith(('.json', '.jsonl')):
                data = self.load_file(f)
                
                # Safely handle both dict and list returns
                if isinstance(data, list): 
                    templates.extend(data)
                elif isinstance(data, dict): 
                    templates.append(data)
                    
        return templates

class DatasetManager:
    """Generic manager for downloading and removing optional remote datasets for any NPC."""
    
    def __init__(self, forge_data_dir: Path, npc_name: str):
        self.npc_name = npc_name
        self.npc_dir = Path(forge_data_dir) / "npcs" / npc_name
        self.config_path = self.npc_dir / "config.json"
        self.dataset_dir = self.npc_dir / "dataset"
        
        # Dynamically resolve the path to src/storage/registry.json
        # __file__ is the path to this current file (dataset.py)
        self.registry_path = Path(__file__).resolve().parent / "registry.json"

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_registry(self) -> list:
        """Loads the global dataset registry."""
        if not self.registry_path.exists():
            logger.warning(f"Dataset registry not found at {self.registry_path}")
            return []
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("datasets", [])
        except Exception as e:
            logger.error(f"Failed to load dataset registry: {e}")
            return []

    def get_available_datasets(self) -> list:
        """Returns the catalog of datasets from the GLOBAL registry."""
        return self._load_registry()

    def get_active_datasets(self) -> list:
        """Returns the list of datasets currently active for THIS SPECIFIC NPC."""
        return self._load_config().get("active_datasets", [])

    def toggle_dataset(self, dataset_id: str) -> dict:
        available = self.get_available_datasets()
        ds_info = next((d for d in available if d["id"] == dataset_id), None)
        
        if not ds_info:
            return {"success": False, "message": f"Unknown dataset: {dataset_id}"}
            
        file_path = self.dataset_dir / ds_info["file"]
        active_datasets = self.get_active_datasets()
        
        if dataset_id in active_datasets:
            # Remove dataset
            if file_path.exists():
                file_path.unlink()
            active_datasets.remove(dataset_id)
            self._update_config(active_datasets)
            return {"success": True, "message": f"Removed {ds_info['file']}"}
        else:
            # Download dataset
            try:
                self.dataset_dir.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(ds_info["url"], headers={'User-Agent': 'NPC-Forge'})
                with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
                    out_file.write(response.read())
                
                active_datasets.append(dataset_id)
                self._update_config(active_datasets)
                return {"success": True, "message": f"Downloaded {ds_info['file']}"}
            except Exception as e:
                return {"success": False, "message": f"Download failed: {e}"}

    def _update_config(self, active_datasets: list):
        config = self._load_config()
        config["active_datasets"] = active_datasets
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)