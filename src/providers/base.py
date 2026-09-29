from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """Abstract base class for NPC-Forge connectors."""

    @abstractmethod
    def request(self, npc_name: str, query: str) -> dict | None:
        """Sends a request to the NPC engine and returns the response."""
        pass

    