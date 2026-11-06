import json
import sys
from pathlib import Path
from storage.dataset import DatasetStorage

REGISTRY_DIR = Path.home() / ".local" / "share" / "npc-forge"
SRC_DIR = Path(__file__).parent.resolve()

storage = DatasetStorage()

def load_and_merge_json_files(base_path, pattern, fallback_filename):
    merged_data = []
    files = sorted(base_path.glob(pattern))
    
    if not files:
        fallback_path = base_path / fallback_filename
        if fallback_path.exists():
            files = [fallback_path]
        else:
            print(f"[WARNING] No files found for pattern '{pattern}' or fallback '{fallback_filename}' in {base_path}")
            return []

    for full_path in files:
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    merged_data.extend(data)
                else:
                    print(f"[ERROR] File {full_path.name} is not a JSON Array (List). Skipping content.")
        except json.JSONDecodeError as syntax_err:
            print(f"[CRITICAL] Syntax error in JSON {full_path.name}: {syntax_err}")
            raise syntax_err
        except Exception as general_err:
            print(f"[ERROR] Failed to load {full_path.name}: {general_err}")
            
    return merged_data

def npc_to_html(npc_name):
    base_npc_path = REGISTRY_DIR / "npcs" / npc_name
    dataset_dir = base_npc_path / "dataset"
    vocab_dir = dataset_dir / "vocabulary"
    
    with open(SRC_DIR / "web" / "js" / "FlintParser.js", "r", encoding="utf-8") as f:
        parser_js = f.read()
    with open(SRC_DIR / "web" / "js" / "FlintNPC.js", "r", encoding="utf-8") as f:
        npc_js = f.read()
    with open(SRC_DIR / "web" / "js" / "Captain.js", "r", encoding="utf-8") as f:
        captain_js = f.read()
    with open(SRC_DIR / "web" / "chat" / "css" / "chat-style.css", "r", encoding="utf-8") as f:
        chat_style = f.read()
        
    dataset_bundle = load_and_merge_json_files(dataset_dir, "dataset_*.json", "dataset.json")
    templates_bundle = load_and_merge_json_files(dataset_dir, "templates_*.json", "templates.json")
    
    config_data = storage.load_json(base_npc_path, "config.json") or {}
        
    bundle = {
        "config": config_data,
        "types": storage.load_json(dataset_dir, "types.json") or {},
        "templates_vocabulary": storage.load_json(vocab_dir, "templates.json") or {},
        "vocabulary": storage.load_json(vocab_dir, "vocabulary.json") or {},
        "dataset": dataset_bundle,
        "personality": storage.load_json(dataset_dir, "personality.json") or [],
        "templates": templates_bundle
    }
    bundle_json_str = json.dumps(bundle, ensure_ascii=False)

    # 1. Load the dataset registry from the source directory
    registry_path = SRC_DIR / "storage" / "registry.json"
    registry_data = {"datasets": []}
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not parse registry.json: {e}")
            
    registry_json_str = json.dumps(registry_data, ensure_ascii=False)

    with open(SRC_DIR / "web" / "chat" / "html" / "template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    html_compiled = html_template.replace("/*{{STYLE_SOURCE}}*/", chat_style)
    html_compiled = html_compiled.replace("{{NPC_NAME}}", npc_name)
    
    html_compiled = html_compiled.replace("// {{CAPTAIN_SOURCE}}", captain_js)
    html_compiled = html_compiled.replace("// {{FLINT_PARSER_SOURCE}}", parser_js)
    html_compiled = html_compiled.replace("// {{FLINT_NPC_SOURCE}}", npc_js)
    html_compiled = html_compiled.replace("// {{NPC_BUNDLE_DATA}}", "const npcBundleData = " + bundle_json_str + ";")
    
    # 2. Inject the registry directly into the HTML as a JS constant
    html_compiled = html_compiled.replace("// {{DATASET_REGISTRY}}", "const INJECTED_DATASET_REGISTRY = " + registry_json_str + ";")

    return html_compiled

def compile_standalone_npc(npc_name):
    base_npc_path = REGISTRY_DIR / "npcs" / npc_name
    
    if not base_npc_path.exists():
        print(f"Error: NPC '{npc_name}' not found on disk.")
        return

    print(f"[COMPILER] Compiling assets for profile: '{npc_name}'...")
    
    html_compiled = npc_to_html(npc_name)

    output_dir = base_npc_path / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{npc_name}_standalone.html"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_compiled)

    print(f"[COMPILER] Standalone compiled successfully: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compile_npc.py <npc_name>")
    else:
        compile_standalone_npc(sys.argv[1])