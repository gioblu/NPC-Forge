# Provider Abstraction

The `src/providers` module implements a provider abstraction pattern to allow the application to communicate with various external services (e.g., different LLM APIs) using a consistent interface.

## The Core Concept

1.  **`BaseProvider`**: This is the abstract base class (found in `src/providers/base.py`). It defines the contract—the methods that *all* providers must implement (e.g., `request`, `chat`, etc.). This ensures uniformity.
2.  **Concrete Implementations**: Classes like `OllamaProvider` (`src/providers/ollama.py`) inherit from `BaseProvider`. They fulfill the abstract methods by implementing the specific logic required to communicate with their respective services (e.g., making an HTTP request to the Ollama API).

## How It Works

By requiring all providers to adhere to the `BaseProvider` interface, the core application logic does not need to know whether it's talking to Ollama, OpenAI, or some other service. It simply calls the standardized methods defined by `BaseProvider`, allowing for simple swapping of backend dependencies without modifying the core code.

*An idiot admires complexity, a genius admires simplicity.* This pattern is the essence of simplicity here.