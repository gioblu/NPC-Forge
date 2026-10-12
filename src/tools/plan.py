
config = {
"title_color": "green",
    "command_key": None,
    "description_template": "{output}",
    "response_key": "text"
}

schema = {
    "type": "function",
    "function": {
        "name": "plan",
        "description": "If the user asks for a complex solution, plan it with this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "If the user's request is complex or vague, use this tool to enrich it and devise a plan."},
            },
            "required": ["text"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console = None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    context["plan"] = args.get("text", "")
    context["summary"].append("I have created a detailed plan to accomplish the task.")
    return True