import os
import json
from pathlib import Path

REGISTRY_DIR = Path.home() / ".local" / "share" / "npc-forge"
SRC_DIR = Path(__file__).parent.resolve()

def load_json_file(base_path, filename):
    full_path = base_path / filename
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Forza la validazione del tipo oggetto richiesto da FlintNPC
            if filename == "config.json" and not isinstance(data, dict):
                raise ValueError("config.json MUST be a JSON Object ({...})")
            return data
    except FileNotFoundError:
        print(f"[ERROR] Missing file path: {full_path}")
        return [] if filename in [
            "dataset.json", "personality.json", "templates.json"
        ] else {}
    except json.JSONDecodeError as syntax_err:
        print(f"[CRITICAL] Syntax error in JSON {filename}: {syntax_err}")
        # Interrompe l'esecuzione per evitare di generare file corrotti
        raise syntax_err
    except Exception as general_err:
        print(f"[ERROR] Failed to load {filename}: {general_err}")
        return [] if filename in [
            "dataset.json", "personality.json", "templates.json"
        ] else {}

def load_and_merge_json_files(base_path, pattern, fallback_filename):
    """
    Cerca tutti i file che corrispondono al pattern (es. 'dataset_*.json'),
    li ordina, carica il loro contenuto (che deve essere una lista JSON) 
    e li unisce in un unico array. Se non trova nulla, usa il file di fallback.
    """
    merged_data = []
    # Cerca i file corrispondenti al pattern e li ordina alfabeticamente
    files = sorted(base_path.glob(pattern))
    
    # Fallback: se non trova file multi-parte, controlla se esiste il file singolo originale
    if not files:
        fallback_path = base_path / fallback_filename
        if fallback_path.exists():
            files = [fallback_path]
        else:
            print(f"[ERROR] No files found for pattern '{pattern}' or fallback '{fallback_filename}' in {base_path}")
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

def compile_npc_html(npc_name):
    base_npc_path = REGISTRY_DIR / "npcs" / npc_name
    dataset_dir = base_npc_path / "dataset"
    vocab_dir = dataset_dir / "vocabulary"
    
    with open(SRC_DIR / "js" / "FlintParser.js", "r", encoding="utf-8") as f:
        parser_js = f.read()
    with open(SRC_DIR / "js" / "FlintNPC.js", "r", encoding="utf-8") as f:
        npc_js = f.read()
    with open(SRC_DIR / "js" / "Captain.js", "r", encoding="utf-8") as f:
        captain_js = f.read()
    with open(SRC_DIR / "css" / "chat-style.css", "r", encoding="utf-8") as f:
        chat_style = f.read()
        
    # Carica e accorpa i file multipli per dataset e templates
    dataset_bundle = load_and_merge_json_files(dataset_dir, "dataset_*.json", "dataset.json")
    templates_bundle = load_and_merge_json_files(dataset_dir, "templates_*.json", "templates.json")
        
    bundle = {
        "config": load_json_file(base_npc_path, "config.json"),
        "types": load_json_file(dataset_dir, "types.json"),
        "templates_vocabulary": load_json_file(vocab_dir, "templates.json"),
        "vocabulary": load_json_file(vocab_dir, "vocabulary.json"),
        "dataset": dataset_bundle,
        "personality": load_json_file(dataset_dir, "personality.json"),
        "templates": templates_bundle
    }
    bundle_json_str = json.dumps(bundle, ensure_ascii=False)

    with open(SRC_DIR / "html" / "chat" / "template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    html_compiled = html_template.replace("/*{{STYLE_SOURCE}}*/", chat_style)
    html_compiled = html_compiled.replace("{{NPC_NAME}}", npc_name)
    
    html_compiled = html_compiled.replace(
        "// {{CAPTAIN_SOURCE}}", captain_js
    )
    html_compiled = html_compiled.replace(
        "// {{FLINT_PARSER_SOURCE}}", parser_js
    )
    html_compiled = html_compiled.replace("// {{FLINT_NPC_SOURCE}}", npc_js)
    html_compiled = html_compiled.replace(
        "// {{NPC_BUNDLE_DATA}}", "const npcBundleData = " + bundle_json_str + ";"
    )

    return html_compiled

def compile_standalone_npc(npc_name):
    base_npc_path = REGISTRY_DIR / "npcs" / npc_name
    
    if not base_npc_path.exists():
        print(f"Error: NPC '{npc_name}' not found on disk.")
        return

    print(f"[COMPILER] Compiling assets for profile: '{npc_name}'...")
    
    html_compiled = compile_npc_html(npc_name)

    output_dir = base_npc_path / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{npc_name}_standalone.html"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_compiled)

    print(f"[COMPILER] Standalone compiled successfully: {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python compile_npc.py <npc_name>")
    else:
        compile_standalone_npc(sys.argv[1])
