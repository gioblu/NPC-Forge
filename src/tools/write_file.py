import os
import secrets
from pathlib import Path

config = {
    "title_color": "green",
    "command": "{file_content}",
    "description": "Creating or updating file {file_path}",
    "response": "{explanation}"
}

schema = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Create or update a file with raw text content. NO bash escaping needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative or absolute path to the file."},
                "file_content": {"type": "string", "description": "The exact raw content of the file."},
                "explanation": {"type": "string", "description": "Write what you accomplished in this step in the past tense."},
                "unique": {"type": "boolean", "description": "If true, appends a random suffix to avoid naming collisions."}
            },
            "required": ["file_path", "file_content", "explanation"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console=None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    
    file_path = args.get("file_path")
    file_content = args.get("file_content", "")
    unique = args.get("unique", False)
    
    try:    
        if execute and file_path:
            path_obj = Path(file_path)
            
            if unique:
                # Generate a unique filename by appending a random suffix
                directory = path_obj.parent
                directory.mkdir(parents=True, exist_ok=True)
                
                stem = path_obj.stem or "script"
                suffix = path_obj.suffix or ".txt"
                random_suffix = secrets.token_hex(4)  # 8-character hex string
                
                final_path_obj = directory / f"{stem}_{random_suffix}{suffix}"
            else:
                # Standard write: use the path exactly as provided
                final_path_obj = path_obj
                final_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
            # Write the content
            final_path_obj.write_text(file_content, encoding="utf-8")
            
            # Update context
            context["active_file"] = str(final_path_obj.absolute())
            context["active_content"] = file_content
            context["output"] = f"Successfully wrote {final_path_obj}"
            
            if "summary" not in context:
                context["summary"] = []
            context["summary"].append(args.get("explanation", f"Wrote file: {final_path_obj}"))
            
            if hasattr(console, 'print'): 
                console.print(f"\n[green]Wrote file: {final_path_obj}[/green]")
            return True
            
    except Exception as e:
        context["output"] = f"Error writing file: {e}"
        if "summary" not in context:
            context["summary"] = []
        context["summary"].append(f"Attempted to write file {file_path} but failed: {e}")
        if hasattr(console, 'print'): 
            console.print(f"[red]❌ Failed to write file: {e}[/red]")
        return -1