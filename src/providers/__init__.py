import importlib

def resolve_provider_class(provider_type: str):
    """
    Dynamically resolves a provider class based on a naming convention.
    Example: "llama-cpp" -> module: "providers.llama_cpp", class: "LlamaCppProvider"
    """
    # Convert kebab-case to snake_case for the module name
    module_name = provider_type.replace("-", "_")
    
    # Convert kebab-case to PascalCase and append "Provider"
    class_name = "".join(word.capitalize() for word in provider_type.split("-")) + "Provider"
    
    try:
        # Dynamically import the module (e.g., providers.llama_cpp)
        module = importlib.import_module(f"providers.{module_name}")        
        
        # Extract the class from the module
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(
            f"Could not load provider type '{provider_type}'. "
            f"Expected to find class '{class_name}' in 'providers.{module_name}'. "
            f"Original error: {e}"
        )

__all__ = ["resolve_provider_class"]