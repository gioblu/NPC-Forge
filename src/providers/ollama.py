import json
import math
import urllib.request

from pathlib import Path
from typing import Optional
from providers.base import BaseProvider 

class OllamaProvider(BaseProvider):

    def __init__(self, config: object):
        """Initializes a new independent instance of the LLMConnector."""
        self.api_url = config.get("api_url", "127.0.0.1:5000").rstrip("/")
        self.model = config.get("model", "")

    def estimate_context_needed(self, prompt: str, num_ctx: int) -> int:
        # Dynamic context memory estimation
        tokens = math.ceil(len(prompt) * 0.28)
        total = tokens + num_ctx # num_ctx is the context for the response
        # Round to ollama VRAM optimized binary power
        if total <= 8192: context_window = 8192
        elif total <= 16384: context_window = 16384
        elif total <= 32768: context_window = 32768
        else: context_window = 65536
        return context_window
        
    def request(self, prompt: str, num_ctx: int) -> str:
        """Sends HTTP POST request to NPC-Forge API /api/chat endpoint."""
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False, 
            "options": {
                "temperature": 0, 
                "num_ctx": self.estimate_context_needed(prompt, num_ctx)
            },
            "format": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "content": {"type": "string"},
                    "extension": {"type": "string"}
                },
                "required": ["code", "content", "extension"]
            }
        }

        binary_data = json.dumps(data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(binary_data))
        }
        
        req = urllib.request.Request(
            self.api_url, data=binary_data, headers=headers, method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("message", {}).get("content", "")
        except Exception as e:
            print(f"NPC-Forge OllamaClient error: {e}")
            return False

    def craft_intent(self, user_query: str, num_ctx: int) -> Optional[dict]:
        """
        Framework-agnostic tool: Asks the LLM for a script, detects the
        language, and formats it into a safe NDF container.
        """
        # 1. Prompt Engineering 
        prompt = (
            "Follows a question from a human, be sincere and very terse (you are running in a limited machine).\n"
            "In \"code\" add a complete, terse, elegant and reusable solution (it will executed in a terminal).\n"
            "In \"content\" add a direct, concise, and technical explanation in markdown format.\n"
            "In \"extension\" add the appropriate extension for the solution (py, css, js, html, ecc.)."
            f"{user_query}"
        )
        
        raw_response = json.loads(self.request(prompt, num_ctx))
        if not raw_response: return None

        cmd = raw_response.get("code", "")    
        exp = raw_response.get("content", "")
        ext = raw_response.get("extension", "")
        
        static_explanation = "Generated code ready to be executed."
        static_goal = "Automated execution framework block."
        
        command_shell = (
            f"TMP_FILE=$(mktemp /tmp/termy_script_XXXXXX.{ext}) &&\n"
            "cat << 'EOF' > \"$TMP_FILE\"\n\n"
            f"{cmd}\n\n"
            "EOF\n"
            "termy_set_context 'active_file' \"$TMP_FILE\" &&\n"
            "termy_set_context 'active_content' \"$(cat \"$TMP_FILE\")\""
        )
        
        # Build NDF Payload Object Structure
        ndf_object = {
            "category": "user_generated", 
            "input": [user_query],
            "output": f"{exp if exp else static_explanation}",
            "tools": [
                {
                    "name": "run_in_terminal",
                    "arguments": {
                        "command": command_shell,
                        "explanation": static_explanation,
                        "goal": static_goal, 
                        "mode": "sync"
                    }
                }
            ],
            "permission": "ask"
        }
        
        # Just return the object, let the caller decide when/where to save
        return ndf_object