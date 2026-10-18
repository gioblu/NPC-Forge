import json
import urllib.request
from providers.base import BaseProvider 

class OllamaProvider(BaseProvider):
    def __init__(self, config: dict):
        self.api_url = config.get("api_url", "127.0.0.1:11434/api/chat")
        self.model = config.get("model", "")
        self.num_ctx = config.get("num_ctx", 4096)
    
    def request(self, messages: list, tools: list = [], ctx: int = 0) -> dict:
        data = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": { "num_ctx": ctx or self.num_ctx, "num_predict": -1 }
        }
        binary_data = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(self.api_url, data=binary_data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("message", {})
        except Exception as e:
            print(f"NPC-Forge OllamaClient error: {e}")
            return {}