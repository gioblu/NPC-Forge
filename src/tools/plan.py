import subprocess
from pathlib import Path

config = {
    "title_color": "green",
    "command_key": "file_path",
    "description_template": "Linting and formatting {file_path}",
    "response_key": "summary"
}

schema = {
    "type": "function",
    "function": {
        "name": "lint",
        "description": "Lint and format a source code file. Supports Python, JS, TS, HTML, CSS, C, C++, Go, Rust, and PHP.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string", 
                    "description": "The relative or absolute path to the file to lint and format."
                },
                "summary": {
                    "type": "string", 
                    "description": "Write what you accomplished in this step in the past tense to help your future self."
                }
            },
            "required": ["file_path", "summary"]
        }
    }
}

# Map file extensions to their standard formatter/linter commands
FORMATTERS = {
    ".py": ["ruff", "format"],
    ".js": ["prettier", "--write"],
    ".ts": ["prettier", "--write"],
    ".html": ["prettier", "--write"],
    ".css": ["prettier", "--write"],
    ".c": ["clang-format", "-i"],
    ".cpp": ["clang-format", "-i"],
    ".go": ["gofmt", "-w"],
    ".rs": ["rustfmt"],
    ".php": ["php-cs-fixer", "fix", "--using-cache=no"],
}

def execute(args: dict, execute: bool, context: dict, console = None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    
    file_path = args.get("file_path")
    summary = args.get("summary", "Linted and formatted file.")
    
    # Ensure summary list exists to prevent context loss
    if "summary" not in context:
        context["summary"] = []
        
    if not file_path:
        context["output"] = "Error: No file_path provided."
        return -1
        
    path = Path(file_path)
    cmd = FORMATTERS.get(path.suffix)
    
    if not cmd:
        msg = f"No linter/formatter configured for {path.suffix}."
        context["output"] = msg
        context["summary"].append(msg)
        if console: console.print(f"[yellow]⚠️ {msg}[/yellow]")
        return True # Return True so the agent loop doesn't crash, just logs the skip
        
    if execute:
        try:
            # Run the native formatter
            res = subprocess.run(
                cmd + [str(path)], 
                check=True, 
                capture_output=True, 
                text=True
            )
            msg = f"Successfully linted and formatted {file_path}"
            context["output"] = msg
            context["summary"].append(summary)
            if console: console.print(f"[green]{msg}[/green]")
            return True
            
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() if e.stderr else "Unknown formatting error"
            context["output"] = f"Failed to lint {file_path}: {err_msg}"
            context["summary"].append(f"Failed to lint {file_path}")
            if console: console.print(f"[red]❌ {context['output']}[/red]")
            return -1
            
        except FileNotFoundError:
            msg = f"Formatter not found: '{cmd[0]}'. Please install it and ensure it's in your PATH."
            context["output"] = msg
            context["summary"].append(msg)
            if console: console.print(f"[red]❌ {msg}[/red]")
            return -1
            
    return True