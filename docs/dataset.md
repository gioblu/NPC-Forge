# NDF 0.0 (NPC-Forge Dataset Format)
```
Invented by Giovanni Blu Mitolo
Originally published: 15/11/2026
Latest revision: 15/11/2026
Related work: https://github.com/gioblu/NPC-Forge/
Compliant implementations: NPC-Forge 0.0 and following
Released into the public domain

15/11/2026 0.0 - First draft
```

This document describes the dataset conventions specified by **NDF 0.0 (NPC-Forge Dataset Format)**. which enable efficient organization, curation and categorization of deterministic agents behavior:
- [Data organization](#data-organization)
- [Static](#static-questions) questions and [conversational](#conversational-questions) questions
- [Context](#context) 
- [Tool calls](#tool-calls) (Copilot, OpenAi)
- [System tags](#system-tags)
- [Entity types](#types)
- [Templates](#templates)
- [Templates vocabulary](#templates-vocabulary)
- [Vocabulary](#vocabulary)

The NPC-Forge framework operates using a **Data-Driven Finite State Machine (DDFSM)**, for this reason semantic analysis, intent processing, named entity extraction, and tool-call execution are governed entirely by static JSON files stored within each NPC profile.

I have specified NDF 0.0 while being strongly convinced that democractic, efficient and sustainable use of Artificial Intelligence can be achieved with deterministic designs, driven by a set of highly curated and tested open-source datesets that can be easily integrated in any workflow. 

---

### <a id="data-organization"></a>Data organization
NPC-Forge installs NPCs in the `npcs` directory. Each NPC is stored in a dedicated directory, for example `termy`, along with its own `dataset` directory structured as following:
```text
dataset/
    dataset_*.json      # Static questions with no named entities 
    personality.json    # Conversational, greetings, fallback
    templates_*.json    # Semantic maps
    types.json          # Named entity types and related regular expressions
    vocabulary/         
        templates.json  # Tag definitions used by templates.json
        vocabulary.json # Categorized vocabulary for semantic analysis
```

---

### <a id="static-questions"></a>Static questions
Any file named `dataset_*.json` in the `dataset` directory is parsed and its content is used for exact-match questions, or the ones that don't need NER (Named Entity Recognition). Each file is just an array of entries mapping a user prompt to a hardcoded response and, optionally, a tool call. The `input`, `message` and `thinking` keys can be a string or an array of strings; when an array of strings is provided one of its entries is selected randomly. The `tools` key contains an array of [tool calls](#tool-calls) to be executed. The `category` key is used to list and group multiple intents together.

```json
{
    "category": "http_weather",
    "input": [
        "check weather",
        "will it snow today",
        "is it raining today"
    ],
    "message": [
        "Sure I will fetch the weather forecast for you."
    ],
    "thinking": [
        "I am not sure if I want to do any work today...",
        "Let's solve this..."
    ]
    "permission": "yolo"
}
```

---

### <a id="tool-calls"></a>Tool Calls
Each entry, whether in `dataset_*.json` or `templates_*.json`, can contain one or more tool calls in the optional `tools` array. Each entry represents one call. The object contents can be structured arbitrarily. If a terminal command is inserted in a tool call it must adhere to the [TCSS](docs/commands-security.md) (Terminal Commands Security Standard).

---

### <a id="conversational-questions"></a>Conversational questions
Small talk, greetings, identity, and fallback responses must be stored in `personality.json`:

```json
{
    "input": [
        "I love LLMs bruh"
    ],
    "message": [
        "Are you aware that complexity is generally admired by idiots?"
    ]
},
```

In this case `<||username||>` will be substitute at render time. That's one of many system tags covered next.


---

### <a id="context"></a>Context
Follow up questions related to an entry can be added in `context` as shown below:

```json
{
    "input": [
        "I love LLMs bruh"
    ],
    "message": [
        "Are you aware that complexity is generally admired by idiots?"
    ],
    "context": [
        {
            "input": [
                "why"
            ],
            "message": [
                "Because complexity is not a good thing!"
            ]
        }
    ]
},
```

After the `I love LLMs bruh` question is received, `why` will output the content of its related `message` key. Every time an entry is triggered, it overwrites existing context entries with the same keys. Each context entry can contain itself a `context` key, for this reason entries can be recursively nested.

---

### <a id="system-tags"></a>System tags
Wherever you write a `message`, `thinking`, `description`, or a tool's `command`/`explanation`/`arguments` string, `<||tag||>` placeholders get substituted at render time. Here's the resolution order.

1. **Entities** from `templates_*.json` structure like `<||string||>` or `<||n||>` which `type` is contained in `types.json`.
2. **Vocabulary** from `dataset/vocabulary/vocabulary.json` help add variation to phrases, for example using the tag `<||encouraging||>` to add a random encouraging word like `good` or `awesome`, or `<||interjection||>` to add an interjection like `uhmm` or `practically`.
3. **System values** (computed once at load time), for example `<||username||>` (OS user), `<||npc_name||>`, `<||creation_date||>`, `<||creator||>` (from `config.json`), `<||computer_name||>` (hostname), `<||response_classes||>` (total loaded entries).
4. **Custom tags** can be defined just adding an object with an arbitrary key, then use that key as tag name where required, for example the `<||completions||>` tag is populated by the contents of the `completions` key.  

Unresolved tags silently become empty strings.

---

### <a id="templates"></a>Templates
Any file named `templates_*.json` contains semantic maps, this is a custom data forma the DDFSM uses to scan phrases, implement NER (Named Entity Recognition), and route the matched phrase to a response with optional tool calls. Unlike `dataset_*.json`, these entries match a *structure* of tags instead of an exact phrase, which is what lets them capture free-form input like a search query, a filename, or a number.

```json
{
    "category": "creative_writing",
    "type": "template",
    "structure": [[
        {
            "tag": ["<||vocab_write||>", "<||vocab_create||>"],
            "type": "vocab",
            "required": true
        },
        {
            "tag": "<||vocab_poem||>",
            "type": "vocab",
            "required": true
        },
        {
            "tag": "<||vocab_about||>",
            "type": "vocab",
            "required": false
        },
        {
            "tag": "<||string||>",
            "type": "string",
            "required": true
        }
    ]],
    "message": [
        "A poem about <||string||>? Fine..."
    ],
    "thinking": [
        "A poem about <||string||>? The human wants art..."
    ],
    "permission": "yolo"
}
```

`structure` is an array of semantic maps. Each map is an array of objects describing the question. Each entry in the semantic map must contain:
- The key `tag` containing a string, or an array of strings where any one satisfies the entry
- The key `type` containing a string, `vocab_*` resolves the tag against the synonyms in `vocabulary/templates.json`, anything else has to match a key declared in `types.json`, like `string`, `word` or `number`, to capture and validate user's input via regular expressions
- The key `required`, when `false`, the parser can skip that node if it's missing from the phrase, so optional words like `about` can be dropped from natural phrasing.

---

### <a id="templates-vocabulary"></a>Templates vocabulary
This maps the vocabulary tags used inside `templates_*.json` to lists of synonims:

```json
{
    "<||vocab_check||>": ["check", "verify"],
    "<||vocab_create||>": ["create", "make", "generate", "craft", "forge"],
    "<||vocab_search||>": ["search", "find", "locate", "query"]
}
```

It's what makes a single `structure` array match thousands of prompts without bloating the template or needing multiple entries.

---

### <a id="types"></a>Entity types
This is the validation layer behind the NER pipeline. Every uncatalogued entity is checked against these regular expressions to discover its type:

```json
{
    "<||email||>": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
    "<||ip_address||>": "(?:[0-9]{1,3}\\.){3}[0-9]{1,3}",
    "<||filename||>": "[\\w\\-]+\\.[a-zA-Z0-9]{2,4}",
    "<||letter||>": "^[a-zA-Z]$",
    "<||number||>": "\\d+(?:\\.\\d+)?",
    "<||word||>": "^[a-zA-Z]+",
    "<||string||>": "^\"(.*)\"$|^(.*)$"
}
```

Each key here is a tag that a `structure` node's `type` can reference in `templates_*.json`. Whatever gets captured is bound to that tag and injected. Types can be arbitrarily defined in here as needed.

---

### <a id="vocabulary"></a>Vocabulary
This file handles conversational building blocks and the data used to sanitize input during the pre-processing stage. Most of these lists do double duty: they're stripped from and detected in the incoming prompt, but they're also the randomly selected source for the [system tags](#system-tags) section above (so `thanking_words` backs both the incoming "thanks" detection and the outgoing `<||thanking_words||>` tag).

```json
{
    "thanking_words": ["thanks", "thank you"],
    "interjection": ["hmm", "well", "actually"],
    "encouraging_words": ["great", "excellent"],
    "discouraging_words": ["bad", "terrible"],
    "greetings": ["hello", "hi there"],
    "expletives": [],
    "stop_words": ["a", "the", "to"]
}
```
