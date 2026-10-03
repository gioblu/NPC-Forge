import json
import re
import os
import urllib.request

from pathlib import Path
from typing import Optional
from providers.base import BaseProvider 

class OllamaProvider(BaseProvider):

    def __init__(self, config: object):
        """Initializes a new independent instance of the LLMConnector."""
        self.api_url = config.get("api_url", "127.0.0.1:5000").rstrip("/")
        self.model = config.get("model", "")
        
    def request(self, prompt: str) -> str:
        """Sends HTTP POST request to NPC-Forge API /api/chat endpoint."""
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False, 
            "options": {
                "temperature": 0.7, 
                "repeat_penalty": 1.2
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

    def craft_intent(self, user_query: str) -> Optional[dict]:
        """
        Framework-agnostic tool: Asks the LLM for a script, detects the
        language, and formats it into a safe NDF container.
        """
        # 1. Prompt Engineering 
        prompt = (
            "Provide a complete, reusable script or code block for the "
            f"following request: '{user_query}'\n\n"
            "YOUR RESPONSE MUST FOLLOW THIS EXACT LAYOUT:\n"
            "Provide a short, precise text description explaining the"
            "logic.\n Put the complete functional code inside a standard" 
            "Markdown code fence explicitly stating the language "
            "(e.g., ```python, ```bash, ```go, ```javascript).\n\n"
            "CONSTRAINTS:\n- Do not output any JSON markdown formatting."
        )
        
        raw_response = self.request(prompt)
        if not raw_response: return None

        # Parse Response and detect the code-fence and language
        codefence_pattern = re.compile(
            r'```(\w+)?\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE
        )
        
        match = codefence_pattern.search(raw_response)
        if not match: return None
            
        detected_lang = (match.group(1) or "txt").lower().strip()
        extracted_code = match.group(2).strip()
        explanation_clean = codefence_pattern.sub("", raw_response).strip()
        explanation_clean = re.sub(r'\n{3,}', '\n\n', explanation_clean)
        
        static_explanation = "Generated code ready to be executed."
        static_goal = "Automated execution framework block."

        shell_languages = {"bash", "sh", "zsh", "shell", "command"}
        
        if detected_lang in shell_languages:
            command_shell = extracted_code
        else:
            extension_map = {
                "python": "py", "javascript": "js", "typescript": "ts", 
                "golang": "go", "ruby": "rb", "markdown": "md"
            }
            file_ext = extension_map.get(detected_lang, detected_lang)
            
            command_shell = (
                f"TMP_FILE=$(mktemp /tmp/termy_script_XXXXXX.{file_ext}) &&\n"
                "cat << 'EOF' > \"$TMP_FILE\"\n\n"
                f"{extracted_code}\n\n"
                "EOF\n"
                "termy_set_context 'active_file' \"$TMP_FILE\" &&\n"
                "termy_set_context 'active_content' \"$(cat \"$TMP_FILE\")\""
            )
        
        # Build NDF Payload Object Structure
        ndf_object = {
            "category": "user_generated", 
            "input": [user_query],
            "output": f"{explanation_clean if explanation_clean else static_explanation}",
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