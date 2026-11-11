import os
import shlex
import subprocess


config = {
    "title_color": "green",
    "command": "{command}",
    "description": "Executing terminal command.",
    "response": "{explanation}"
}

schema = {
    "type": "function",
    "function": {
        "name": "run_in_terminal",
        "description": "Execute a terminal/bash command (e.g., mkdir, ls, xdg-open); consider that each call is executed in an isolated subshell, 'cd' does not persist.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute."},
                "explanation": {"type": "string", "description": "Write what you accomplished in this step in the past tense and if to call 'finish' to help your future self."}
            },
            "required": ["command", "explanation"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console=None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    if execute:
        sources = []
        complete_command = ""
        bash_command = args.get("command")
        scripts_dir = args.get("scripts_dir")
        if scripts_dir and scripts_dir.is_dir():
            for file in sorted(scripts_dir.iterdir()):
                if file.suffix == ".sh":
                    sources.append(f"source {shlex.quote(str(file))}")
        if sources: 
            complete_command = f"{' && '.join(sources)} && {bash_command}"
        else:
            complete_command = bash_command
        
        try:
            console.print()
            # Run WITHOUT capture_output to inherit stdio (allows ANSI + interactive input)
            res = subprocess.run(
                complete_command, 
                shell=True, 
                executable="/bin/bash",
                check=False
            )
            
            # Update context with summary (output won't be captured, but that's OK)
            context["output"] = f"\n'run_in_terminal': {bash_command} executed with exit code {res.returncode}"
            context["summary"].append(f"Executed terminal command: {bash_command}")
            os.environ["TERMY_YES"] = ""    
            
            return res.returncode
        except Exception as e:
            context["output"] = f"Error: {e}"
            context["summary"].append(f"Attempted to execute terminal command: {bash_command} but failed because of {e}")
            if hasattr(console, 'print'):
                console.print(f"[red]❌ Failed to execute command: {e}[/red]")
            return -1