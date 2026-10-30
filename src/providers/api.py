
import json
import sys
import urllib.request

from providers.base import BaseProvider 

class ApiProvider(BaseProvider):

    def __init__(
        self, 
        url: str = "http://127.0.0.1:5000", 
        timeout: float = 30.0
    ):
        """Initializes a new instance of the ApiProvider."""
        self.base_url = url.rstrip("/")
        self.timeout = timeout

    def set_url(self, url: str):
        """Sets the target API URL"""
        if url is not None: 
            self.base_url = url.rstrip("/")
        
    def set_timeout(self, timeout: float):
        """Sets the request timeout"""
        if timeout is not None: 
            self.timeout = timeout

    def request(self, npc_name: str, query: str) -> dict | None:
        """Sends an HTTP POST request towards the NPC-Forge API server."""
        try:
            payload = {"message": query}
            data = json.dumps(payload).encode("utf-8")
            url = f"{self.base_url}/api/chat/{npc_name}"
            
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode("utf-8"))
                    return result
                else:
                    sys.stderr.write(
                        f"NPC-Forge returned HTTP {response.status}"
                        f"for query '{query}'\n"
                    )
                    return None
                    
        except Exception as e:
            sys.stderr.write(f"NPC-Forge returned an unexpected error: {e}\n")
            return None
