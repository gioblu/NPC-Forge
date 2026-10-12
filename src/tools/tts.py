import shlex
import subprocess

config = {
    "title_color": "green",
    "command_key": None,
    "description": "{output}",
    "response_key": "text"
}

schema = {
    "type": "function",
    "function": {
        "name": "tts",
        "description": "Text-to-speech syntesys to be used wisely and when you really need to.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "text to be read aloud."}
            },
            "required": ["text"]
        }
    }
}

def execute(args: dict, execute: bool, context: dict, console = None, config: dict = None):
    if console is None: console = {}
    if config is None: config = {}
    tts_engine = config.get("tts")
    response = args.get("text", "")
    if response and context.get("tts", "") == "on" and tts_engine:
        try:
            subprocess.run(
                f"pkill -9 -x {shlex.quote(tts_engine)}", 
                shell=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            subprocess.Popen(
                [tts_engine, response],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            context['output'] = "'tts' used successfully"    
            context['summary'].append(f"'tts' used successfully to output '{response}'.")
        except Exception as e:
            return -1
    context['output'] = "'tts' used successfully"
    context['summary'].append(f"'tts' successfully called to output '{response}' but was muted by config.")
            