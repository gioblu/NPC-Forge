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

    def estimate_context_needed(self, prompt: str, ctx_cap: int) -> int:
        # We estimate that:
        # input tokens = output tokens required to answer
        tokens = math.ceil(len(prompt) * 0.28) * 2
        # Round to ollama VRAM optimized binary power
        if tokens <= 8192: context_window = 8192
        elif tokens <= 16384: context_window = 16384
        elif tokens <= 32768: context_window = 32768
        else: context_window = 65536
        if tokens > ctx_cap: return ctx_cap
        return context_window
        
    def request(self, prompt: str, ctx_cap: int) -> str:
        """Sends HTTP POST request to NPC-Forge API /api/chat endpoint."""
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False, 
            "options": { 
                "num_ctx": self.estimate_context_needed(prompt, ctx_cap)
            },
            "format": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "content": {"type": "string"},
                    "extension": {"type": "string"},
                    "summary": {"type": "string"}
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

    def craft_intent(self, user_query: str, ctx_cap: int) -> Optional[dict]:
        """
        Framework-agnostic tool: Asks the LLM for a script
        and formats it into a safe NDF container.
        """
        
        prompt = (
            "You are a terminal expert, solve the task requested by the human.\n"
            "Be sincere and terse (you are running in a limited machine).\n"
            "\nIn \"code\" add a solution adhering to the following requirements:\n\n"
            "1. Do not use code fences, write only code that is complete, functional, elegant and reusable.\n"
            "2. Use external dependencies or third party libraries only when asked to.\n"
            "\nIn \"content\" add a direct, concise, and technical explanation in markdown format.\n\n"
            "In \"extension\" add the appropriate extension for the solution (py, css, js, html, ecc.).\n\n"
            "In \"summary\" add a 40 characters description of what you did in this step and why."
            f"{user_query}"
        )
        raw_response = json.loads(self.request(prompt, ctx_cap))
        if not raw_response: return None

        cmd = raw_response.get("code", "")    
        exp = raw_response.get("content", "")
        ext = raw_response.get("extension", "")
        summary = raw_response.get("summary", "")
        
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
        return prompt, summary, ndf_object