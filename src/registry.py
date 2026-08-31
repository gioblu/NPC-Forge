import os
from pathlib import Path

# Force isolation mapping onto the central deployment directory
REGISTRY_DIR = Path.home() / ".local" / "share" / "npc-forge"

# GLOBAL CACHE REGISTRY: Keeps NPC Engine instances alive in memory
NPC_REGISTRY = {}

def get_npc_engine(npc_name):
    """
    Ensures that each NPC Engine is instantiated and baked ONCE 
    on startup, avoiding reload latencies.
    """
    npc_path = REGISTRY_DIR / "npcs" / npc_name
    if not os.path.exists(npc_path):
        return None
        
    # If the NPC instance does not exist in the memory, initialize it
    if npc_name not in NPC_REGISTRY:
        from FlintNPC import FlintNPC
        try:
            
            old_cwd = os.getcwd()
            
            os.chdir(str(REGISTRY_DIR))
            
            NPC_REGISTRY[npc_name] = FlintNPC(npc_name)
            
            os.chdir(old_cwd)
            
        except Exception as init_error:
            if 'old_cwd' in locals():
                os.chdir(old_cwd)
                
            print(f"[SERVER] CRITICAL: Failed to initialize NPC Engine '{npc_name}': {str(init_error)}")
            import traceback
            traceback.print_exc()
            return None

    # Return the cached fast in-memory instance
    return NPC_REGISTRY[npc_name]