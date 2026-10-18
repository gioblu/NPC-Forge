import os
import shlex
import subprocess


config = {
    "title_color": "green",
    "command": "{command}",
    "description": "Executing terminal command.",
    "response": "{summary}"
}

schema = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "Execute a terminal/bash command (e.g., mkdir, ls, xdg-open); consider that each call is executed in an isolated subshell, 'cd' does not persist.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute."},
                "summary": {"type": "string", "description": "Write what you accomplished in this step in the past tense and if to call 'finish' to help your future self."}
            },
            "required": ["command", "summary"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console = None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    if execute:
        sources = []
        complete_command = ""
        bash_command = args.get("command")
        scripts_dir = args.get("scripts_dir")
        if scripts_dir.is_dir():
            for file in sorted(scripts_dir.iterdir()):
                if file.suffix == ".sh":
                    sources.append(f"source {shlex.quote(str(file))}")
        if sources: complete_command = f"{' && '.join(sources)} && {bash_command}"
        
        try:
            res = subprocess.run(
                complete_command, shell=True, executable="/bin/bash",
                capture_output=True, text=True, check=False
            )
            context["output"] = (
                f"\n'run_command': {bash_command} "
                f"output: {res.stdout}\n{res.stderr.strip() or 'Success.'}"
            )
            context["summary"].append(f"Executed terminal command: {bash_command}")
            os.environ["TERMY_YES"] = ""    
            if res.stdout: console.print(res.stdout)
            if res.stderr: console.print(f"[red]❌ Failed to write file: {res.stderr}[/red]")
            return res
        except Exception as e:
            context["output"] = f"Error: {e}"
            context["summary"].append(f"Attempted to execute terminal command: {bash_command} but failed because of {e}")
            console.print(f"[red]❌ Failed to write file: {e.stderr}[/red]")
            return -1