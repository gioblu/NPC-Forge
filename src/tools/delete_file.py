
from pathlib import Path

config = {
    "title_color": "red",
    "command_template": "rm {file_path}",
    "description_template": "Deleting file {file_path}",
    "response_key": "summary"
}

schema = {
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a file (be careful, with the wrong tool call you may even delete yourself).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to the file."},
                "summary": {"type": "string", "description": "Write what you accomplished in this step in the past tense and if to call 'finish' to help your future self."}
            },
            "required": ["file_path", "summary"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console = None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    try:
        file_path = args.get("file_path", "")
        target_path = Path(file_path).resolve() 
        if target_path.is_dir():
            context["output"] = f"Error: the target {file_path} is a directory."
        if execute and file_path:
            if target_path.exists():
                target_path.unlink()
                
                if context.get("active_file") == str(target_path):
                    context["active_file"] = ""
                    context["active_content"] = ""
                    
                context["output"] = f"Successfully deleted {file_path}"
                context["summary"].append(args.get("summary", ""))
                console.print(f"\n[red]Deleted file: {file_path}[/red]")
                return True
            else: context["output"] = f"File {file_path} does not exist, nothing to delete."
        return False
    except Exception as e:
        context["output"] = f"Error deleting file: {e}"        
        context["summary"].append(f"Attempted to delete the file {file_path} but failed because of {e}")
        console.print(f"[red]❌ Failed to delete file:[/red]")
        return -1