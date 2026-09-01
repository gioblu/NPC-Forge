## FlintNPC

FlintNPC is the conversational agent framework built on top of FlintParser. It orchestrates the deterministic NLU engine into a full-featured, multi-turn conversational system with tool-call support, sentiment tracking, thinking mode, and context memory.

FlintNPC is available in identical, cross-compliant implementations for both [Python](src/flint_npc.py), for local OS environments, and [JavaScript](src/flint_npc.js), running client-side inside any browser tab or Node.js instance.

### The Engineering Philosophy

FlintNPC relies on **subtraction engineering**: instead of adding probabilistic models, it subtracts noise until only deterministic, auditable behavior remains. The framework implements a four-stage intent resolution pipeline that degrades gracefully from fast exact matching to fuzzy probabilistic fallback:

```
User Prompt

1. Sanitize & Strip (remove noise)
2. Exact Match (O(1) hash lookup)
3. Template Match (semantic structure parsing)
4. Probabilistic Match (IDF-weighted Levenshtein)
5. Response or rejection (with related intent suggestions)
```

### Features

- **Four-Stage Intent Resolution** Exact match, template match, probabilitstic match, rejection
- **Multi-Turn Context Memory** Persistent conversational state with overwrite semantics
- **Sentiment Analysis** Tracks expletives, thanking words, encouraging or discouraging words
- **Tool-Call Support** Extracts slots and triggers tool execution with permission gating
- **Thinking Mode** Inner monologue that explains the agent's reasoning
- **Composite Prompt Splitting** Handles multi-command inputs (`cmd1; cmd2`)
- **Metadata Rendering** Macro substitution for dynamic responses (`<||username||>`, `<||npc_name||>`)
- **Related Intent Suggestions** Generates suggestions based on rarest word matching
- **Threshold Tuning** Adaptive error tolerance based on prompt length
- **Permission Gating** Controls which actions require user confirmation

### Performance comparison

This table compares FlintNPC with [ChatScript](https://github.com/ChatScript/ChatScript), [NLP.js](https://github.com/axa-group/nlp.js/), and [Rasa](https://github.com/rasahq/rasa) across performance, resource usage, linguistic robustness and conversational features:

| Feature | FlintNPC | ChatScript | NLP.js | Rasa |
|---|---|---|---|---|
| **Hardware required** | 🟢 Pi Zero, ESP32 | 🟢 Pi 1 | 🟢 Browser | 🔴 Server |
| **Memory required** | 🟢 < 10 MB | 🟢 < 50 MB | 🟡 30–80 MB | 🔴 500MB–2GB+ |
| **GPU required** | 🟢 No | 🟢 No | 🟢 No | 🟡 Optional |
| **Training required** | 🟢 No | 🟢 No | 🔴 Yes | 🔴 Yes |
| **Speed** | 🟢 Microseconds | 🟢 Microseconds | 🟡 Milliseconds | 🔴 100ms+ |
| **Dependencies** | 🟢 Minimal | 🟢 Minimal | 🟡 npm packages | 🔴 Heavy (TensorFlow, NumPy) |
| **Typo tolerance** | 🟢 Strong | 🟢 Strong | 🟡 Weak | 🟢 Strong |
| **Filler words tolerance** | 🟢 Built-in | 🟡 Wildcards | 🔴 None | 🟡 Via training data |
| **Word inversions** | 🟢 Handled | 🟡 Partial | 🟡 Partial | 🟢 Handled |
| **Synonyms** | 🟢 Templates | 🟢 Concepts | 🟡 Basic | 🟢 Synonyms + lookup |
| **Templates** | 🟢 Semantic structure | 🟢 Pattern language | 🔴 None | 🟡 Forms only |
| **Sentiment** | 🟢 Built-in | 🟡 Manual | 🔴 None | 🟡 Custom |
| **Memory/context** | 🟢 Built-in | 🟢 Facts system | 🔴 Stateless | 🟢 Tracker |
| **Tool calls** | 🟢 Built-in | 🟢 Actions | 🟡 Handlers | 🟢 Actions |
| **Permission gating** | 🟢 Built-in | 🟡 Manual rule logic | 🔴 None | 🟡 Custom code |
| **Composite prompts** | 🟢 Built-in | 🟡 Manual | 🔴 None | 🔴 None |
| **Determinism** | 🟢 Guaranteed | 🟢 Guaranteed | 🟡 Varies | 🔴 Probabilistic |

[FlintNPC](docs/FlintNPC.md) stands out as the fastest, lightest, and feature-rich option, with built-in sentiment, context, permissions, and composite-prompt handling, [ChatScript](https://github.com/ChatScript/ChatScript) is a strong rule-based alternative while [NLP.js](https://github.com/axa-group/nlp.js/) and [Rasa](https://github.com/rasahq/rasa) trade determinism and low resource usage for greater statistical flexibility.

### How It Works

FlintNPC processes input through a four-stage pipeline, each stage more permissive than the last:

#### Stage 1: Sanitization & Sentiment Extraction

```python
stripped, sentiment = parser.strip_and_sentiment(
    "darn, can you show me the red tie?",
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
structure, slots = parser.parse_structure("show red tie", threshold=0.8)
# structure: ["<||vocab_show||>", "<||color||>", "<||vocab_tie||>"]
# slots: {"color": "red"}

match = parser.match_structure(templates, structure)
# Returns the intent block whose structure matches
```

The parser converts the prompt into an ordered sequence of semantic tags, then walks each template's structure paths to find a match. Variables (like `<||color||>`) are extracted via regex and stored in slots.

#### Stage 4: Probabilistic Match (IDF-Weighted Levenshtein)

```python
score = parser.sentence_similarity("show me a red tie", "show red tie", threshold=0.66)
# Returns: 0.85 (high confidence match)
```

If no exact or template match is found, the parser computes an asymmetric, order-independent similarity score against all intent variants:
- **Anchor tokens** (from the intent phrase) are weighted by their IDF specificity
- **Query tokens** (from the user prompt) are fuzzy-matched against anchors via Levenshtein distance
- **OOV penalty** tokens absent from the vocabulary reduce the score

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
  "npc_name": "TERMy",
  "creator": "Giovanni Blu Mitolo",
  "creation_date": "2026-07-12",
  "sentence_threshold": 0.75,
  "word_threshold": 0.75,
  "suggestions": 5
}
```

- **sentence_threshold** minimum similarity score for probabilistic match on prompts >3 words
- **word_threshold** stricter threshold for short prompts (1-3 words)
- **suggestions** max number of related intent suggestions on rejection

### Dataset Structure

FlintNPC uses the NDF (NPC-Forge Dataset Format). A dataset directory contains:

```
npcs/<name>/
├── config.json
├── dataset/
│   ├── types.json              # Variable type regex definitions
│   ├── vocabulary/
│   │   ├── vocabulary.json     # Sentiment word lists
│   │   └── templates.json      # Vocabulary tag synonyms
│   ├── personality.json        # Static intents (greetings, etc.)
│   ├── dataset_*.json          # Dynamic intents (split across files)
│   └── templates_*.json        # Template-based intents
```

See the [NDF specification](docs/dataset.md) for full details.

### Performance Characteristics

- **Zero Dependencies** Only Python standard library + FlintParser
- **CPU-Only** No GPU, no CUDA, no PyTorch. Runs on a Raspberry Pi Zero.
- **Deterministic** Same input always produces the same output. Testable in CI.
- **Microsecond Latency** Exact match: <10μs. Template match: <1ms. Probabilistic: <10ms.
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

#### Why Four Stages?

Most NLU frameworks use a single neural classifier. FlintNPC uses a cascade:
1. **Exact match** is O(1) and covers 60-80% of queries (people repeat common phrases)
2. **Template match** is O(n) and covers structured queries with variables
3. **Probabilistic match** is O(n*m) and covers typos and paraphrases
4. **Rejection** is the fallback when nothing matches

Each stage is 10-100x slower than the previous, so we short-circuit as early as possible.

#### Why Context Override?

Multi-turn conversations require state. Instead of a complex dialogue manager, FlintNPC uses a simple hash map:
- Active context entries override the global dataset on key collision
- Context persists until explicitly overwritten
- Rejection clears the context

This allows flows like "create dir" → "move it" → "delete it" without re-specifying the directory each time.

#### Why Composite Prompt Splitting?

Users often issue multiple commands at once (`list files; show red tie`). Instead of rejecting the input, FlintNPC splits on separators and processes each sub-prompt sequentially. Responses are concatenated.

#### Why Adaptive Thresholds?

Short prompts (1-3 words) are highly sensitive to typos. A single character change can flip the meaning (`who` vs `how`). Long prompts are more tolerant of errors because the rarest word still anchors the match.

FlintNPC uses:
- **word_threshold** (default 0.75) for prompts ≤3 words
- **sentence_threshold** (default 0.75) for prompts >3 words

### Limitations

FlintNPC is not a replacement for LLMs. It's a **deterministic conversational framework** for structured, predictable interactions. It cannot:
- Understand open-ended, creative language
- Perform reasoning or inference beyond pattern matching
- Handle multi-language without per-language datasets
- Generate novel responses beyond what's in the dataset

For open-ended chit-chat, the NPC-Forge framework can **escalate** to an LLM when FlintNPC returns a "rejected" status. This hybrid approach gives you the best of both worlds: deterministic speed for 80% of queries, probabilistic flexibility for the rest.

### License

Licensed under the [AGPL-3.0](../LICENSE). Commercial licensing available.
