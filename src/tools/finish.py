schema = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Call 'finish' only when the entire task is complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Final summary of the completed task."}
            },
            "required": ["summary"]
        }
    }
}