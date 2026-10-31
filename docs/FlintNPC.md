## FlintNPC

FlintNPC is the conversational agent framework built on top of FlintParser. It orchestrates the deterministic NLU engine into a full-featured, multi-turn conversational system with tool-call support, sentiment tracking, thinking mode, and context memory.

FlintNPC is available in identical, cross-compliant implementations for both Python, for local OS environments, and JavaScript, running client-side inside any browser tab or Node.js instance.

### The Engineering Philosophy

FlintNPC relies on **subtraction engineering**: instead of adding probabilistic models, it subtracts noise until only deterministic, auditable behavior remains. The framework implements the following pipeline:

```
User Prompt

1. Sanitize & Strip (insults, interjections, thanking words)
2. Exact Match (O(1) hash lookup)
3. Template Match (semantic structure parsing)
4. Probabilistic Match (Precomputed signatures & rarest-word pruning)
5. Response, rejection or entry generation via ollama
```

### Features

- **Four-Stage Intent Resolution** Exact match, template match, probabilistic match, rejection
- **Multi-Turn Context Memory** Persistent conversational state with overwrite semantics
- **Sentiment Analysis** Tracks expletives, thanking words, encouraging or discouraging words
- **Tool-Call Support** Extracts slots and triggers tool execution with permission gating
- **Thinking Mode** Inner monologue that explains the agent's response
- **Composite Prompt Splitting** Handles multi-command inputs (`cmd1; cmd2`)
- **Metadata Rendering** Macro substitution for dynamic responses (`<||username||>`, `<||npc_name||>`)
- **Related Intent Suggestions** Generates suggestions based on rarest word matching
- **Permission Gating** Controls which actions require user confirmation

### How It Works

FlintNPC processes input through a four-stage pipeline, each stage more permissive than the last:

#### Stage 1: Sanitization & Sentiment Extraction

```python
stripped, sentiment = parser.strip_and_sentiment(
    "darn what is the temperature of the cpu?",
    vocabulary,
    current_sentiment
)
# Returns: ("can you show me the red tie?", {"expletives": 1, ...})
```

The parser strips noise (insults, interjections, emojis) while counting occurrences. This feeds the sentiment system and cleans the prompt for matching.

#### Stage 2: Exact Match (O(1) Hash Lookup)

```python
if stripped in exact_match_map:
    matched_block = exact_match_map[stripped]
    return generate_response(matched_block, confidence=1.0, status="exact match")
```

Every intent variant in the dataset is indexed in a hash map. If the sanitized prompt matches exactly, we return immediately with 100% confidence. This is the fastest path.

**Context Override**: Active context entries (from multi-turn conversations) override the global dataset on key collision. This allows follow-up intents like "move it" to take priority over unrelated global intents.

#### Stage 3: Template Match (Semantic Structure Parsing)

```python
structure, slots = parser.parse_structure("search on wiki programma 101", threshold=0.8)
# structure: ["<||vocab_search||>", "<||vocab_wiki||>", "<||string||>"]
# slots: {"string": "programma 101"}

match = parser.match_structure(templates, structure)
# Returns the intent block whose structure matches
```

The parser converts the prompt into an ordered sequence of semantic tags, then walks each template's structure paths to find a match. Variables (like `<||color||>`) are extracted via regex and stored in slots.

#### Stage 4: Probabilistic Match (Precomputed Signatures & Rarest-Word Pruning)

```python
# Checks active context first, then global dataset
score = nlp.fast_score_calculation(query_tokens, precomputed, threshold)
```

If no exact or template match is found, the parser computes a similarity score against intent variants. To ensure ultra-low latency, it uses aggressive pruning:
- **Active Context Priority**: Checks against the current conversational context before falling back to the global dataset.
- **Rarest-Word Pruning**: The rarest word in the query is identified. If it (or its synonym tag) is not in the target intent's precomputed `token_set` or `tag_set`, the candidate is skipped immediately.
- **Early Exit**: Uses precomputed `max_weight_sums` and `token_count` to discard candidates that cannot possibly meet the `threshold` before running the final score calculation.

The highest-scoring intent above the threshold is returned.

#### Stage 5: Rejection (With Suggestions)

```python
if best_score < threshold:
    related_intents = generate_suggestions(rarest_word, dataset)
    return generate_response(rejection, confidence=0.0, status="rejected", related=related_intents)
```

If no match clears the threshold, the agent returns a rejection with up to 5 related intent suggestions based on the rarest (most specific) word in the prompt.

### Code Examples

#### Basic Usage

```python
from flint_npc import FlintNPC

# Initialize an NPC from a dataset directory
npc = FlintNPC("TERMy", log_level="INFO")

# Process a user prompt
response = npc.process_message("show me a red tie")

print(response["response"])      # "Certainly. A selection from the tie atelier..."
print(response["status"])        # "template match"
print(response["confidence"])    # 1.0
print(response["slots"])         # {"color": "red"}
print(response["tools"])         # [{"name": "ShowProducts", "arguments": {...}}]
```

#### Multi-Turn Context Memory

FlintNPC maintains conversational state across multiple turns. Context entries persist until explicitly overwritten:

```python
# Turn 1: User says "create a directory"
res1 = npc.process_message("create a directory")
# Context is now: ["move it", "delete it"]

# Turn 2: User says "move it"
res2 = npc.process_message("move it")
# Context persists, "delete it" still active

# Turn 3: User says "delete it"
res3 = npc.process_message("delete it")
# Both follow-ups worked without re-specifying the directory
```

Context semantics:
- `"context": [...]` → overwrites active context with new entries
- `"context": []` → explicitly clears the context
- No `"context"` key → context persists unchanged

#### Composite Prompt Splitting

FlintNPC can handle multi-command inputs by splitting on separators:

```python
response = npc.process_messages("list files; show cpu temperature; goodbye")
# Splits into 3 sub-prompts, processes each sequentially
# Returns aggregated response with concatenated output
```

Separators: newlines, numbered lists (`1)`), semicolons, exclamation marks, question marks.

#### Tool-Call Execution

FlintNPC extracts tool calls from matched intents:

```python
response = npc.process_message("show me a red tie")
# response["tools"] = [
#   {
#     "name": "ShowProducts",
#     "arguments": {"category": "ties", "color": "red"},
#     "goal": "Product discovery"
#   }
# ]

# Your harness executes the tool:
for tool in response["tools"]:
    result = execute_tool(tool["name"], tool["arguments"])
    # result: HTML cards with red ties
```

#### Thinking Mode

FlintNPC can emit an inner monologue that explains its reasoning:

```python
response = npc.process_message("show me a red tie")
print(response["thinking"])
# "A tie request. The only honest piece of clothing left. Opening the catalogue..."
```

Thinking is defined in the dataset and can include slot substitution (`<||color||>`).

#### Metadata Rendering

FlintNPC substitutes macros in responses with runtime values:

```python
# In dataset: "Hello <||username||>, I am <||npc_name||>"
response = npc.process_message("hello")
# response["response"]: "Hello nonar, I am TERMy"
```

Available metadata:
- `<||username||>` current user (from `$USER` env var)
- `<||npc_name||>` NPC name (from config)
- `<||computer_name||>` hostname
- `<||creation_date||>` dataset creation date
- `<||creator||>` dataset author
- `<||response_classes||>` total number of loaded response blocks
- `<||completion||>` random completion phrase
- `<||unknown||>` random "unknown" response
- `<||related||>` related intent suggestions

#### Sentiment Tracking

FlintNPC tracks sentiment across the conversation:

```python
response = npc.process_message("thanks for the help, you're great!")
print(response["sentiment"])
# {"expletives": 0, "thanking_words": 1, "encouraging_words": 1, ...}

print(response["emoji"])
# "😃" (thanking + encouraging = happy)
```

Sentiment is aggregated across composite prompts and persists across turns.

### Configuration

FlintNPC reads configuration from `npcs/<name>/config.json`:

```json
{
  "name": "TERMy",
  "creator": "Giovanni Blu Mitolo",
  "creation_date": "2026-07-12",
  "threshold": 0.75,
  "synonym_contribution": 0.0,
  "suggestions": 5
}
```

- **threshold** (default `0.75`): Minimum similarity score required for probabilistic matches.
- **synonym_contribution** (default `0.0`): Weight given to synonym matches during precomputation.
- **suggestions** (default `5`): Maximum number of related intent suggestions to return on rejection.

### Performance Characteristics

- **Zero Dependencies** Only Python standard library + FlintParser
- **CPU-Only** No GPU, no CUDA, no PyTorch. Runs on a Raspberry Pi Zero.
- **Deterministic** Same input always produces the same output. Testable in CI.
- **Fast response time** Answers in less 100 milliseconds in most cases.
- **Memory Efficient** The entire agent + dataset fits in <10MB RAM.

### Integration with NPC-Forge

FlintNPC is the conversational layer that powers NPC-Forge agents. It wraps FlintParser and provides:
- Multi-turn context management
- Tool-call orchestration
- Sentiment aggregation
- Metadata rendering
- Composite prompt handling

The NPC-Forge CLI uses FlintNPC to serve agents:

```bash
npc-forge serve              # Start OpenAI-compatible API server
npc-forge install npcs/termy # Install TERMy
termy show me a red tie      # Chat with TERMy via CLI
```

### Algorithmic Choices

#### Why three stages?

Most NLU frameworks rely on heavy neural classifiers. FlintNPC uses a highly optimized, deterministic pipeline with aggressive pre-compilation at startup to ensure ultra-low latency:

1. **Exact match: O(1)** Direct hash-map lookup covers the vast majority of queries instantly.
2. **Template match: O(1) average case** Structures are pre-compiled and sorted by specificity at startup, allowing for immediate early-exit matching without on-the-fly parsing.
3. **Probabilistic match: O(1) pruning + O(K) scoring** Uses pre-computed intent signatures and "rarest-word" hash-set filtering to eliminate 99% of candidates in O(1) time. Expensive scoring is only applied to the remaining `K` candidates (typically 0 or 1), avoiding naive O(N×M) full dataset scans.

#### Why Context Override?

Multi-turn conversations require state. Instead of a complex dialogue manager, FlintNPC uses a simple hash map:
- Active context entries override the global dataset on key collision
- Context persists until explicitly overwritten
- Rejection clears the context

This allows flows like "create dir" > "move it" > "delete it" without re-specifying the directory each time.

#### Why Composite Prompt Splitting?

Users often issue multiple commands at once (`list files; show red tie`). Instead of rejecting the input, FlintNPC splits on separators and processes each sub-prompt sequentially. Responses are concatenated.

### Limitations

FlintNPC is not a replacement for LLMs. It's a **deterministic conversational framework** for structured, predictable interactions. It cannot:
- Understand open-ended, creative language
- Perform reasoning or inference beyond pattern matching
- Handle multi-language without per-language datasets
- Generate novel responses beyond what's in the dataset

For open-ended chit-chat, the NPC-Forge framework can **escalate** to an LLM when FlintNPC returns a "rejected" status. This hybrid approach gives you the best of both worlds: deterministic speed for 80% of queries, probabilistic flexibility for the rest.

### License

Licensed under the AGPL-3.0. Commercial licensing available.