#!/usr/bin/env python3
import glob
import sys
import os    
import subprocess
from pathlib import Path

from FlintNPC import load_json

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# Standard XDG Directory per l'utente locale
FORGE_DATA_DIR = Path.home() / ".local" / "share" / "npc-forge"
LOG_FILE_PATH = FORGE_DATA_DIR / "npc_forge.log"
SERVICE_NAME = "npc-forge.service"

def run_systemctl_user(action: str):
    """Executes systemctl commands as user with no root privileges"""
    try:
        subprocess.run(["systemctl", "--user", action, SERVICE_NAME], check=True)
        print(f"{GREEN}[NPC-FORGE]{RESET} Systemd user daemon '{action}' triggered successfully.")
    except subprocess.CalledProcessError:
        print(f"{RED}[NPC-FORGE]{RESET} Error executing systemctl --user {action}.")
        sys.exit(1)

def is_service_active() -> bool:
    """Verifies if the user's Systemd service is active."""
    try:
        res = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return res.stdout.strip() == "active"
    except Exception:
        return False

def stream_logs():
    """Streams logs using the native Linux tail utility. Starts the service if it is offline."""
    if not is_service_active():
        print(f"{YELLOW}[NPC-FORGE]{RESET} Service is offline. Bootstrapping gateway in background...")
        run_systemctl_user("start")

    if not LOG_FILE_PATH.exists():
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE_PATH.touch()

    print(f"{YELLOW}[NPC-FORGE]{RESET} Streaming live logs from {GREEN}{LOG_FILE_PATH}{RESET}... (Press Ctrl+C to exit)\n")
    
    try:
        subprocess.run(["tail", "-f", "-n", "20", str(LOG_FILE_PATH)], check=True)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[NPC-FORGE]{RESET} Log streaming stopped by user.")
    except subprocess.CalledProcessError:
        print(f"{RED}[NPC-FORGE]{RESET} Error reading log file at '{LOG_FILE_PATH}'")

def run_framework_tests():
    """Executes the compact color-coded test runner within the proper production User Space environment context."""
    venv_python = FORGE_DATA_DIR / "venv" / "bin" / "python3"
    test_dir = FORGE_DATA_DIR / "tests"
    runner_script = test_dir / "run_tests.py"
        
    print(f"{YELLOW}[NPC-FORGE]{RESET} Initializing testing pipeline engine from: {GREEN}{test_dir}{RESET}...\n")
    
    # Prepariamo l'ambiente forzando la root di produzione nel PYTHONPATH di sistema
    current_env = os.environ.copy()
    current_env["PYTHONPATH"] = f"{FORGE_DATA_DIR}:{str(FORGE_DATA_DIR / 'src')}:{current_env.get('PYTHONPATH', '')}"
    
    if runner_script.exists():
        cmd = [str(venv_python), str(runner_script)]
        sub_cwd = str(FORGE_DATA_DIR)
    else: 
        cmd = [
            str(venv_python), "-m", "unittest", "discover", 
            "-s", ".", 
            "-v"
        ]
        sub_cwd = str(test_dir)
    
    try:
        res = subprocess.run(cmd, cwd=sub_cwd, env=current_env, check=False)
        sys.exit(res.returncode)
    except Exception as e:
        print(f"{RED}[NPC-FORGE]{RESET} Critical failure attempting to invoke testing subprocess: {e}")
        sys.exit(1)


def install_npc(source_path: str, dev: bool = False):
    """Installs NPC in user space: moves files and executes setup."""
    src = Path(source_path).resolve()
    if not src.exists() or not src.is_dir():
        print(f"{RED}[NPC-FORGE]{RESET} Error: Provided path is not a valid directory: '{source_path}'")
        sys.exit(1)
        
    npc_name = src.name.lower().strip()
    if npc_name == "." or npc_name == "":
        npc_name = src.parent.name.lower().strip()

    target_npc_dir = FORGE_DATA_DIR / "npcs" / npc_name
    print(f"\n{YELLOW}[NPC-FORGE]{RESET} Installing NPC {GREEN}{npc_name}{RESET}...")
    
    # Check if source and destination are the same (symlinked in dev mode)
    src_resolved = src.resolve()
    target_resolved = target_npc_dir.resolve() if target_npc_dir.exists() else None
    
    if target_resolved and src_resolved == target_resolved:
        print(f"{YELLOW}[NPC-FORGE]{RESET} NPC {GREEN}{npc_name}{RESET} already installed in dev mode (symlinked). Skipping copy.")
    else:
        if target_npc_dir.exists():
            subprocess.run(["rm", "-rf", str(target_npc_dir)], check=True)
        subprocess.run(["mkdir", "-p", str(target_npc_dir)], check=True)

        # Copy the entire NPC source directory (dataset, scripts, entry point,
        # setup.sh, etc.) so nothing is silently left out of the install.
        subprocess.run(["cp", "-r", f"{src}/.", str(target_npc_dir)], check=True)
    bot_setup_hook = src / "setup.sh"
    if bot_setup_hook.exists():
        print(f"{YELLOW}[NPC-FORGE]{RESET} Dedicated installer discovered for {GREEN}{npc_name}{RESET}. Launching setup...\n")
        try:
            subprocess.run(["chmod", "+x", str(bot_setup_hook)], check=True)
            
            # Dynamically build the command array to include --dev if requested
            setup_cmd = ["bash", str(bot_setup_hook)]
            if dev:
                setup_cmd.append("--dev")
                
            subprocess.run(setup_cmd, cwd=str(src), check=True)
        except subprocess.CalledProcessError as err:
            print(f"{RED}[NPC-FORGE]{RESET} Bot installer hook exited with an error: {err}")
    else:
        print(f"{YELLOW}[NPC-FORGE]{RESET} No local execution hook found. {GREEN}{npc_name}{RESET} will be served purely via API context.")

    print(f"{GREEN}[NPC-FORGE]{RESET} Success: NPC {GREEN}{npc_name}{RESET} registered.\n")

def print_help():
    """Prints the comprehensive standard help screen."""
    help_text = f"""
{GREEN}npc-forge{RESET} - The Deterministic NPC Automation Engine

{YELLOW}Usage:{RESET}
    npc-forge <command> [options]

{YELLOW}Commands:{RESET}
    {GREEN}serve, start{RESET}   Start the background NPC registry gateway service (systemd)
    {GREEN}stop{RESET}           Stop the background registry service
    {GREEN}restart, reboot{RESET} Restart the background registry service
    {GREEN}logs, watch{RESET}    Stream live logs from the systemd server daemon
    {GREEN}list{RESET}           List all locally installed NPCs and their capabilities
    {GREEN}install <path>{RESET} Install an NPC profile from a local directory
    {GREEN}test, tests{RESET}    Run the internal framework test suite

{YELLOW}Options:{RESET}
    {GREEN}-h, --help{RESET}     Show this help message and exit
    {GREEN}--dev{RESET}          Install NPC in editable developer mode (used with 'install')

{YELLOW}Examples:{RESET}
    npc-forge install ./npcs/termy --dev
    npc-forge logs
    npc-forge list
"""
    print(help_text)

def list_installed_npcs():
    """Reads the registry folder and aggregates metrics about installed NPCs"""
    npc_base_dir = FORGE_DATA_DIR / "npcs"
    if not npc_base_dir.exists() or not npc_base_dir.is_dir():
        print(f"No NPCs installed yet.")
        return

    npc_dirs = [d for d in npc_base_dir.iterdir() 
                if d.is_dir() and d.name != "__pycache__"]
    if not npc_dirs:
        print(f"No NPCs installed yet.")
        return

    print(f"\nInstalled NPCs:\n")

    for npc_dir in sorted(npc_dirs):
        npc_name = npc_dir.name
        dataset_dir = npc_dir / "dataset"  
        
        # Extract creator from config
        creator = "Unknown"
        

        config = load_json(npc_dir, "config.json")
        creator = config.get("creator", "Unknown")
                
        personality = load_json(dataset_dir, "personality.json")

        dataset = []
        for f in glob.glob(os.path.join(dataset_dir, "dataset_*.json")):
            dataset.extend(
                load_json(dataset_dir, os.path.basename(f))
            )

        templates = []
        for f in glob.glob(os.path.join(dataset_dir, "templates_*.json")):
            templates.extend(
                load_json(dataset_dir, os.path.basename(f))
            )

        merge = personality + dataset + templates
        intent_count = len(merge)

        vocab_size = 0
        vocab_dir = npc_dir / "dataset" / "vocabulary"
        
        vc = load_json(vocab_dir, "vocabulary.json")
        vocab_size += len(vc) if isinstance(vc, (list, dict)) else 0
        
        vt = load_json(vocab_dir, "templates.json")
        vocab_size += len(vt) if isinstance(vt, (list, dict)) else 0
        
        # Calculate dataset directory size
        dataset_dir = npc_dir / "dataset"
        data_size_bytes = 0
        if dataset_dir.exists():
            for file in dataset_dir.rglob("*"):
                if file.is_file():
                    data_size_bytes += file.stat().st_size
        
        if data_size_bytes < 1000000:
            size_str = f"{data_size_bytes/1024:.1f}KB"
        else:
            size_str = f"{data_size_bytes/1024/1024:.2f}MB"
        
        has_tools = "no"
        if isinstance(merge, list):
            if any(
                "tools" in item for item in merge if isinstance(
                    item, dict
                )
            ):
                has_tools = "yes"
    
        print(f"{GREEN}{npc_name}{RESET} (intents: {intent_count}, vocabulary: {vocab_size}, dataset: {size_str}, tools: {has_tools}) by {creator}")
    print()

def main():
    if len(sys.argv) < 2 or sys.argv[1].lower() in ["-h", "--help"]:
        print_help()
        sys.exit(0 if len(sys.argv) > 1 else 1)
        
    cmd = sys.argv[1].lower().strip()
    
    if cmd in ["serve", "start"]: run_systemctl_user("start")
    elif cmd == "stop": run_systemctl_user("stop")
    elif cmd in ["reboot", "restart"]: run_systemctl_user("restart")
    elif cmd in ["logs", "watch"]: stream_logs()
    elif cmd in ["test", "tests"]: run_framework_tests()
    elif cmd == "list": list_installed_npcs()
    elif cmd == "install":
        if len(sys.argv) < 3:
            print(f"{RED}Error: Missing target package directory path. Usage: npc-forge install <path> [--dev]{RESET}")
            sys.exit(1)
            
        is_dev = "--dev" in sys.argv
        args_without_dev = [arg for arg in sys.argv if arg != "--dev"]
        
        if len(args_without_dev) < 3:
            print(f"{RED}Error: Missing target package directory path. Usage: npc-forge install <path> [--dev]{RESET}")
            sys.exit(1)
            
        target_path = args_without_dev[2]
        install_npc(target_path, dev=is_dev)
    else:
        print(f"{RED}Unknown: '{cmd}'. Supported: serve, start, stop, restart, watch, logs, tests, install{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
