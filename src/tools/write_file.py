
from pathlib import Path

config = {
    "title_color": "green",
    "command_key": "file_content",
    "description_template": "Creating file {file_path}",
    "response_key": "summary"
}

schema = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Create or update a file with raw text content. NO bash escaping needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to the file."},
                "file_content": {"type": "string", "description": "The exact raw content of the file."},
                "summary": {"type": "string", "description": "Write what you accomplished in this step in the past tense and if to call 'finish' to help your future self."}
            },
            "required": ["file_path", "file_content", "summary"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console = None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    file_path = args.get("file_path")
    try:    
        if execute and file_path:
            file_content = args.get("file_content")
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            Path(file_path).write_text(file_content, encoding="utf-8")
            context["active_file"] = str(Path(file_path).absolute())
            context["active_content"] = file_content
            context["output"] = f"Successfully wrote {file_path}"
            context["summary"].append(args.get("summary"))
            if console: console.print(f"\n[green]Wrote file: {file_path}[/green]")
            return True
    except Exception as e:
        context["output"] = f"Error writing file: {e}"
        context["summary"].append("Attempted to write the file {file_path} but failed because of {e}")
        if console: console.print(f"[red]❌ Failed to write file: {e}[/red]")
        return -1