import os
import pkgutil
import importlib

TOOLS = {}
TOOLS_CONFIG = {}

package_dir = os.path.dirname(__file__)

_tools_map = {}

# Default fallback for tools that don't define a config
DEFAULT_RENDER_CONFIG = {
    "title_color": "green",
    "command_key": None,
    "description": None,  # Will fallback to 'output' in the renderer
    "response_key": None  # Will fallback to 'output' in the renderer
}

for _, module_name, _ in pkgutil.iter_modules([package_dir]):
    module = importlib.import_module(f"tools.{module_name}")
    
    if hasattr(module, "schema"):
        tool_schema = getattr(module, "schema")
        try:
            tool_name = tool_schema["function"]["name"]
            
            TOOLS[tool_name] = module
            _tools_map[tool_name] = tool_schema
            
            TOOLS_CONFIG[tool_name] = getattr(
                module, "config", DEFAULT_RENDER_CONFIG.copy()
            )
            
        except (KeyError, TypeError):
            print(f"Error: Malformed tool schema in: '{module_name}.py'.")

def get_tools_by_name(names_list: list) -> list:
    """Returns an array of only the tools specified in 'names_list'."""
    return [_tools_map[name] for name in names_list if name in _tools_map]


def render_tool_action(tui, tool_name, tool_args, output, llm_model, status, iteration, response_time):
    """Renders the tool action using centralized, templated metadata."""
    
    meta = (
        f"[color(240)]Status:[/color(240)] [color(247)]{status} [/]"
        f"[color(240)]Iteration:[/color(240)] [color(247)]{iteration}[/] "
        f"{response_time}"
    )
    
    # 1. Fetch config
    cfg = TOOLS_CONFIG.get(tool_name, {
        "title_color": "green", "command_key": None, "description": None, "response_key": None
    })
    
    # 2. Safe Dictionary for templating (prevents KeyError if a variable is missing)
    class SafeDict(dict):
        def __missing__(self, key):
            return ''
    safe_args = SafeDict(tool_args)
    
    # 3. Resolve Command (Template OR Key OR Empty)
    if cfg.get("command_template"):
        command = cfg["command_template"].format_map(safe_args)
    elif cfg.get("command_key"):
        command = tool_args.get(cfg["command_key"], "")
    else:
        command = ""
        
    # 4. Resolve Description (Template OR Static OR Fallback to output)
    if cfg.get("description_template"):
        description = cfg["description_template"].format_map(safe_args)
    else:
        description = cfg.get("description") or output
        
    # 5. Resolve Response (Key OR Fallback to output)
    response = tool_args.get(cfg["response_key"], "") if cfg.get("response_key") else output

    # 6. Render
    tui.render_action(
        thinking="",
        response=response,
        command=command,
        description=description,
        title=f"[bold {cfg.get('title_color', 'green')}]{llm_model}[/]  {meta}"
    )

__all__ = ["TOOLS", "get_tools_by_name", "render_tool_action", "TOOLS_CONFIG"]