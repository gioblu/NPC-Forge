
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
