import json
from typing import List
from .base import Decomposer
from providers.ollama import OllamaProvider

class ProbabilisticDecomposer(Decomposer):
    """Decomposes prompts by asking an LLM (via OllamaProvider) to devise a step-by-step plan."""
    
    def __init__(self, config: dict):
        # Reuse the existing provider instead of writing custom urllib logic
        self.provider = OllamaProvider(config)
        print(f"[ProbabilisticDecomposer] Initialized with model: {self.provider.model}")

    def decompose(self, prompt: str) -> List[str]:
        print(f"[ProbabilisticDecomposer] Requesting decomposition from {self.provider.model}... (this may take a moment if the model is loading)")
        
        system_prompt = (
            "You are an expert request analyst. Your task is to analyze the user's prompt, "
            "devise a step-by-step plan to address it, and output ONLY a valid JSON array "
            "of subtasks. Each subtask should be a self-contained instruction or query "
            "that can be executed sequentially. Do not include any markdown formatting or "
            "explanations outside the JSON array, if you need delimeters use double quotes. Example:\n\n"
            "create the new abstraction Decomposers in the decomposers directory and then implement the abstract class and ProbabilisticDecomposer classes with stubs.\n\n"
            "Expected output: [\"create directory decomposers\", \"implement the Decomposer base class in decomposers/base.py\", \"implement ProbabilisticDecomposer extending Decomposer base class in decomposers/probabilistic.py\"]"
        )
        user_prompt = f"Decompose the following prompt into an array of subprompts: {prompt}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Delegate the HTTP request to the provider
            response_msg = self.provider.request(messages)
            content = response_msg.get("content", "[]")
            print(f"[ProbabilisticDecomposer] Raw LLM output: {content}")
            
            # Clean up markdown code blocks if the LLM adds them
            cleaned = content.strip()
            if cleaned.startswith("```json"): cleaned = cleaned[7:]
            if cleaned.startswith("```"): cleaned = cleaned[3:]
            if cleaned.endswith("```"): cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            subprompts = json.loads(cleaned)
            if isinstance(subprompts, list):
                result = [str(p).strip() for p in subprompts if str(p).strip()]
                print(f"[ProbabilisticDecomposer] Successfully decomposed into {len(result)} subprompts.")
                return result
                
        except json.JSONDecodeError as e:
            print(f"[ProbabilisticDecomposer] Failed to parse JSON from LLM: {e}")
        except Exception as e:
            print(f"[ProbabilisticDecomposer] Provider error: {e}")
            
        # Safe fallback: return the original prompt as a single-item array
        print("[ProbabilisticDecomposer] Falling back to original prompt.")
        return [prompt]