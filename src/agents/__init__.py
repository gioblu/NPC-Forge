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

__all__ = ["AGENT_REGISTRY"]
