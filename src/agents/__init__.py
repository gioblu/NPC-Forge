import os
import pkgutil
import importlib
from agents.base import BaseAgent

AGENT_REGISTRY = {}

package_dir = os.path.dirname(__file__)

for _, module_name, _ in pkgutil.iter_modules([package_dir]):
    if module_name == "base": continue    
    module = importlib.import_module(f"agents.{module_name}")
    
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        
        if (
            isinstance(attribute, type) 
            and issubclass(attribute, BaseAgent) 
            and attribute is not BaseAgent
        ):
            if hasattr(attribute, "name") and attribute.name:
                AGENT_REGISTRY[attribute.name] = attribute
      
def resolve_agent_class(agent_type: str):
    """
    Dynamically resolves an agent class based on a naming convention.
    Example: "self-reflecting" -> module: "agents.self_reflecting", class: "SelfReflectingAgent"
    """
    # Convert kebab-case to snake_case for the module name
    module_name = agent_type.replace("-", "_")
    # Convert kebab-case to PascalCase and append "Agent"
    class_name = "".join(word.capitalize() for word in agent_type.split("-")) + "Agent"
    try:
        # Dynamically import the module (e.g., agents.self_reflecting)
        module = importlib.import_module(f"agents.{module_name}")        
        # Extract the class from the module
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(
            f"Could not load agent type '{agent_type}'. "
            f"Expected to find class '{class_name}' in 'agents.{module_name}'. "
            f"Original error: {e}"
        )

__all__ = ["AGENT_REGISTRY", resolve_agent_class]
