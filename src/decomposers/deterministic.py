import re
from typing import List
from .base import Decomposer

class DeterministicDecomposer(Decomposer):
    """Decomposes prompts using the exact regex delimiter approach from FlintNPC."""
    
    def __init__(self, separator_pattern: str = r"\n+|\d+\)|[;!?]"):
        self.separator_pattern = separator_pattern

    def decompose(self, prompt: str) -> List[str]:
        raw_segments = re.split(self.separator_pattern, prompt)
        return [seg.strip() for seg in raw_segments if seg.strip()]