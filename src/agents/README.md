
## NPC-Forge Agent Abstraction Layer

Every agent in this directory must inherit from `BaseAgent`. 

### `BaseAgent`
This abstract base class defines the interface that all agents must implement. It ensures interoperability with the NPC-Forge framework.

```python
from abc import ABC, abstractmethod
from providers.base import BaseProvider

class BaseAgent(ABC):
    def __init__(self, provider: BaseProvider, tools: list):
        self.provider = provider  # The LLM backend (Ollama, llama.cpp, etc.)
        self.tools = tools        # List of JSON schemas for available tools

    @abstractmethod
    def run_step(self, user_query: str, context: dict, ctx: int = 4096, i: int = 0) -> tuple:
        """
        Executes a single reasoning step.
        Must return a tuple: (output_text: str, ndf_object: dict)
        """
        pass
```

- `provider`: Injected dynamically. Allows the agent to be agnostic of whether it's talking to Ollama, a local llama.cpp server, or a cloud API.
- `tools`: The filtered list of tool schemas (from `src/tools/`) that the agent is allowed to use for this specific task.
- `context`: The persistent state dictionary. The agent reads from it to understand the current environment and mutates it (via tool outputs) to track progress.

### `SelfReflectingAgent`

This is the default agent. Unlike many harnesses, such as pi or VScode copilot, this agent does not receive the whole conversation every time, it implements a self-reflecting agent loop. The agent receives only the actual state and a summary of the previous steps. This approach is optimized for local models and consumer hardware.

To avoid small models easily lose track of state, a prompt that forces the model to acknowledge its current state before acting is being used.

It injects the following state variables from `context`:
- `Plan`: The high-level plan devised to accomplish the task.
- `Active file` / `Active content`: What the agent is currently looking at.
- `Last execution output`: The result of the previous tool.
- `Your past actions`: A bulleted list of the `summary` logs from previous steps.

Once the LLM responds, the agent parses the raw JSON response into TERMy's internal NDF object. Currently, it extracts the **first** tool call requested by the LLM and formats it for the CLI executor:

```python
ndf_object = {
    "category": tool_name,
    "output": output,
    "thinking": response.get("thinking", ""),
    "tools": [
        {
            "name": tool_name,
            "explanation": explanation,
            "goal": goal,
            "mode": raw_args.get("mode", "sync"),
            "arguments": raw_args
        }
    ],
    "status": "done" if tool_name == "finish" else "busy",
    "permission": "ask"
} 
```

### How to create a new agent

Thanks to the dynamic resolver in `run_cli.py`, adding a new agent requires no changes to the main CLI code.

#### Create the file
Create a new file in `src/agents/`, for example, `react_agent.py`.

#### Implement the class
Inherit from `BaseAgent` and implement `run_step`.

```python
from agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, provider, tools):
        super().__init__(provider, tools)
        # Custom initialization here

    def run_step(self, user_query: str, context: dict, ctx: int = 4096, i: int = 0) -> tuple:
        # Build your custom prompt
        messages = self._build_react_prompt(user_query, context, i)
        
        # Call the LLM
        response = self.provider.request(messages, self.tools, ctx)
        
        # Parse into the standard ndf_object format
        # ... parsing logic ...
        
        return output_text, ndf_object
```

#### Update `config.json`
Change the agent type in your configuration file to match your new file/class name (following the kebab-case to PascalCase convention).

```json
{
  "agent": {
    "type": "react", 
    "tools": ["finish", "plan", "read_file", "run_command"]
  }
}
```
The resolver will automatically look for `agents.react_agent.MyAgent` and load it!
