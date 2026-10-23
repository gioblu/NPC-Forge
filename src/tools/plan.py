
config = {
    "title_color": "green",
    "command": None,
    "description": "Devise a plan to accomplish the task assigned by the human."
}

schema = {
    "type": "function",
    "function": {
        "name": "plan",
        "description": "If the user's request is complex or vague, use this tool to devise a plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text of a your well devised plan."},
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
    context["output"] = "Plan created successfully."
    return True