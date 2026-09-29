
import sys
import traceback

from pathlib import Path
from registry import load_npc
from providers.base import BaseProvider 

class LocalProvider(BaseProvider):

    def __init__(self, forge_root_dir: str, npc_dataset_dir: str):
        """Initializes the local in-memory NPC-Forge client"""
        self.forge_root_dir = str(Path(forge_root_dir).resolve())
        self.npc_dataset_dir = str(Path(npc_dataset_dir).resolve())

    def request(self, npc_name: str, query: str) -> dict:
        """
            Processes an query locally without contacting the server.
            The server itself uses this function to respond to requests.  
        """
        try:
            engine = load_npc(npc_name)
            if engine is None:
                raise RuntimeError(
                    f"NPC Engine Profile '{npc_name}' not found."
                )

            result = engine.process_messages(query)
            return result

        except Exception as e:
            sys.stderr.write(
                f"NPC-Forge local runtime error for NPC '{npc_name}': {e}\n"
            )
            traceback.print_exc(file=sys.stderr)

            return {
                "response": f"Error: Local engine execution failed -> {e}",
                "status": "rejected",
                "error": str(e),
            }

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
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
            
        return True