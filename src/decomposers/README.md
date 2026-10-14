
## Decomposers: Prompt Breakdown Strategies

Complex user prompts often contain multiple distinct tasks. The Decomposer abstraction is responsible for analyzing a raw user prompt and breaking it down into a sequential list of subprompts. 

This allows the `DeterministicInterpreter`, `ProbabilisticInterpreter` and `HybridInterpreter` to process, execute, and track multi-step requests efficiently.

### Architecture

The module is built on a simple, Abstract Base Class (ABC) pattern, allowing TERMy to switch between deterministic, probabilistic, or hybrid parsing.

```python
@abstractmethod
def decompose(self, prompt: str) -> List[str]:
    """Decompose a prompt into a list of sequential subprompts."""
    pass
```

### `DeterministicDecomposer` (Rule-Based)
**File:** `decomposers/deterministic.py`

This strategy uses regular expressions to split the prompt. It is the default choice for speed and predictability.

* **Mechanism:** Splits text based on a configurable regex pattern.
* **Default Pattern:** `r"\n+|\d+\)|[;!?]"`
  * Newlines (`\n+`)
  * Numbered list items (`1)`, `2)`, etc.)
  * Standard sentence terminators (`;`, `!`, `?`)
* **Pros:** Instant execution, zero latency, no external dependencies.
* **Cons:** Rigid. It doesn't understand context, so it might incorrectly split a sentence if it contains a semicolon or question mark in the middle of a thought.

### `ProbabilisticDecomposer` (LLM-Powered)
**File:** `decomposers/probabilistic.py`

This strategy leverages an LLM (via `OllamaProvider`) to process the prompt and devise a step-by-step execution plan.

* **Mechanism:** Sends the prompt to the LLM with a strict system prompt demanding a valid JSON array of subtasks. It includes robust cleanup for markdown code blocks and a safe fallback to the original prompt if JSON parsing fails.
* **Pros:** Understands context, handles complex natural language gracefully, and creates logical step-by-step plans.
* **Cons:** Slower (requires LLM inference time), requires a running Ollama instance, and is subject to LLM hallucination (mitigated by the JSON fallback).

### Comparison

| Feature | Deterministic | Probabilistic |
| :--- | :--- | :--- |
| **Speed** | Instant (< 1ms) | Slow (Seconds, depends on LLM) |
| **Accuracy** | Literal (Regex based) | Semantic (Context aware) |
| **Dependencies** | None (Pure Python) | Requires Ollama / LLM running |
| **Best For** | Simple, clearly delimited commands | Complex, multi-step natural language workflows |

### Extending the Module

To create a custom decomposition strategy (e.g., a graph-based decomposer or an AST-based parser for code), simply inherit from the base class:

```python
from typing import List
from .base import Decomposer

class CustomDecomposer(Decomposer):
    def decompose(self, prompt: str) -> List[str]:
        # Your custom logic here
        return ["step 1", "step 2"]
```