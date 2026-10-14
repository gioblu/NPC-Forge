from abc import ABC, abstractmethod
from typing import List

class Decomposer(ABC):
    """Abstract base class for prompt decomposition strategies."""
    
    @abstractmethod
    def decompose(self, prompt: str) -> List[str]:
        """Decompose a prompt into a list of sequential subprompts."""
        pass