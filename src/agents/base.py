from abc import ABC, abstractmethod
from providers.base import BaseProvider

class BaseAgent(ABC):
    def __init__(self, provider: BaseProvider, tools: list):
        self.provider = provider
        self.tools = tools

    @abstractmethod
    def run_step(self, user_query: str, details: str, context: dict) -> tuple:
        pass
