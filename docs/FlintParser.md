# FlintParser

FlintParser is a lightweight, zero-dependency, deterministic Natural Language Understanding (NLU) semantic parser. Converts user's questions into semantic structures while implementing Named Entity Recognition (NER).

FlintParser is available in identical, cross-compliant implementations for both [Python](src/flint_parser.py), for local OS environments, and [JavaScript](src/flint_parser.js), running client-side inside any browser tab or Node.js instance.

### The Engineering Philosophy

FlintParser relies on **subtraction engineering** and can be described as, not only a parser, but also a transpiler, because it is capable of translating plain English into semantic paths with the following format:

```json
"structure": [[
    {
        "tag": "<||vocab_prefer||>",
        "type": "vocab",
        "required": true
    },
    {
        "tag": "<||a||>",
        "type": "word",
        "required": true
    },
    {
        "tag": "<||vocab_or||>",
        "type": "vocab",
        "required": true
    },
    {
        "tag": "<||b||>",
        "type": "word",
        "required": true
    }
]]
```

The semantic path above represents the prompt `Do you prefer <||a||> or <||b||>`, where `<||a||>` and `<||b||>` can be substituted with any word, for example `do you prefer complexity or simplicity`.

#### Why Subtraction?

Most NLU frameworks **add** complexity: they train neural networks, they build embedding spaces, they maintain massive vocabularies. FlintParser does the opposite. It **subtracts** noise until only the semantic skeleton remains:

1. **Strips the noise** removing insults, interjections, emojis, filler words
2. **Extracts the structure** converting words to semantic tags (`<||vocab_show||>`, `<||color||>`)
3. **Matches patterns** comparing the structure against known templates
4. **Confidence ranking** using IDF-weighted similarity to rank matches

### Features

- **Text Sanitization** Strips insults, emojis, interjections while tracking sentiment
- **Template Semantic Parsing** Converts text into ordered semantic tag sequences
- **Sentence Similarity** Asymmetric, order-independent BOW IDF + Levenshtein scoring
- **Subject Identification** Extracts the rarest (most specific) word via IDF
- **Sentiment Analysis** Counts expletives, thanking words, encouraging/discouraging tokens
- **Emoji Generation** Generates a cynical emoji based on sentiment density
- **Typo Tolerance** Fuzzy-matches vocabulary tags with configurable threshold
- **Variable Extraction** Regex-based slot extraction with string literal support
- **Candidate Prediction** Predicts next expected tags for autocomplete/debugging

### How It Works

FlintParser processes input through a five-stage pipeline:

#### 1. Sanitization & Sentiment Extraction

```python
parser.strip_and_sentiment(
    "darn, can you show me the red tie?",
    sentiment_json,
    current_sentiment={"expletives": 0, "thanking_words": 0, ...}
)
# Returns: ("can you show me the red tie?", {"expletives": 1, ...})
```

The parser strips noise while counting occurrences. This feeds the sentiment system and cleans the prompt for parsing.

#### 2. Tokenization & Filtering

```python
# Input: "can you show me the red tie?"
# After stop-word filtering: ["show", "red", "tie"]
```

Stop words, expletives, and interjections are removed. What remains are the semantically meaningful tokens.

#### 3. Structure Parsing (The Transpiler)

```python
structure, slots = parser.parse_structure("show red tie", threshold=0.8)
# structure: ["<||vocab_show||>", "<||color||>", "<||vocab_tie||>"]
# slots: {"color": "red"}
```

Each token is either:
- **Matched to a vocabulary tag** via fuzzy Levenshtein similarity (handles typos like `"shwo"` → `<||vocab_show||>`)
- **Extracted as a variable** via regex (e.g., `<||color||>` matches `"red"`, `"blue"`, `"burgundy"`)
- **Ignored** if it doesn't match any candidate

#### 4. Template Matching

```python
match = parser.match_structure(templates, structure)
# Returns the intent block whose structure matches the parsed structure
```

The parser walks each template's structure paths, checking if the parsed tags align. Optional nodes are skipped if not present.

#### 5. Confidence Scoring

```python
score = parser.sentence_similarity("show me a red tie", "show red tie", threshold=0.66)
# Returns: 0.85 (high confidence match)
```

For probabilistic fallback (when no exact template matches), the parser computes an asymmetric, order-independent similarity score:
- **Anchor tokens** (from the intent phrase) are weighted by their IDF specificity
- **Query tokens** (from the user prompt) are fuzzy-matched against anchors
- **OOV penalty** tokens absent from the vocabulary reduce the score

### Code Examples

#### Auto-Weighted IDF

FlintParser automatically computes word rarity across your intent corpus:

```python
# After initialization, parser.weights contains IDF scores:
# {"tie": 1.0, "show": 0.8, "the": 0.05, "a": 0.03}

rarest = parser.get_rarest_word("show me a red tie")
# Returns: "tie" (highest IDF weight)
```

Rare words get high weight (they're specific to this intent). Common words get low weight (they appear everywhere).

#### Sentiment-Driven Emoji

```python
sentiment = {
    "expletives": 2,
    "thanking_words": 0,
    "encouraging_words": 0,
    "discouraging_words": 0,
    "interjections": 0
}
emoji = parser.sentiment_emoji(sentiment)
# Returns: "😔" (two expletives, no thanks = sad/frustrated)
```

The emoji system is cynical and nerdy it doesn't fake enthusiasm. One expletive = `😒`, five expletives = `😱`.

#### Typo-Tolerant Vocabulary Matching

```python
tag = parser.find_template("shwo", threshold=0.8)
# Returns: "<||vocab_show||>" (fuzzy match on typo)
```

Levenshtein similarity with early-exit pruning makes this fast even on large vocabularies.

#### String Literal Extraction

```python
structure, slots = parser.parse_structure('search for "red silk tie"', threshold=0.8)
# slots: {"query": "red silk tie"}
```

Quoted strings are captured as a single slot, preserving spaces and punctuation.

### Performance Characteristics

- **Zero Dependencies** Only `re`, `string`, `math` from the Python standard library
- **CPU-Only** No GPU, no CUDA, no PyTorch. Runs on a Raspberry Pi Zero.
- **Deterministic** Same input always produces the same output. Testable in CI.
- **Microsecond Latency** Parsing 1,000 intents takes <10ms on a modern CPU.
- **Memory Efficient** The entire parser + dataset fits in <5MB RAM.

### Integration with NPC-Forge

FlintParser is the NLU engine that powers NPC-Forge agents. It's instantiated once per NPC with the dataset:

```python
from flint_parser import FlintParser

parser = FlintParser(
    name="TERMy",
    vocabulary=load_json("dataset/vocabulary/words.json"),
    templates=load_json("dataset/templates.json"),
    templates_vocabulary=load_json("dataset/vocabulary/templates.json"),
    variable_types=load_json("dataset/types.json"),
    intents=load_json("dataset/dataset.json")
)

# Parse a user prompt
structure, slots = parser.parse_structure("show me a red tie", threshold=0.8)

# Find the matching intent
match = parser.match_structure(parser.templates, structure)
```

The parser is stateless and thread-safe. It can be called from multiple concurrent requests without locks.

### Algorithmic Choices

#### Why Levenshtein?

Neural embeddings are overkill for small vocabularies. Levenshtein distance is:
- **Deterministic** Same input, same output
- **Explainable** You can see exactly which characters differ
- **Fast** O(n*m) with early-exit pruning
- **Zero-dependency** No pre-trained models to download

#### Why IDF Weighting?

TF-IDF (Term Frequency-Inverse Document Frequency) is the gold standard for keyword extraction. By weighting rare words heavily, the parser:
- Prevents "the", "a", "is" from dominating similarity scores
- Makes short identifiers (like programming language names "c", "r") detectable
- Allows the threshold to be tuned for the specific dataset

#### Why Asymmetric Similarity?

The parser treats the intent phrase as the "anchor" and the user prompt as the "query". This means:
- Missing anchor words heavily penalize the score (the user didn't say something important)
- Extra query words are tolerated (the user added filler)
- Word order doesn't matter (the parser is order-independent)

This matches how humans actually communicate: we add noise, we skip words, but we rarely omit the core subject.

### Limitations

FlintParser is not a replacement for LLMs. It's a **deterministic front-end** for structured, predictable conversations. It cannot:
- Understand open-ended, creative language
- Perform reasoning or inference beyond pattern matching
- Handle multi-language without per-language vocabularies
- Extract entities that aren't in the variable type regexes

For open-ended chit-chat, the NPC-Forge framework can **escalate** to an LLM when FlintParser returns a "rejected" status. This hybrid approach gives you the best of both worlds: deterministic speed for 80% of queries, probabilistic flexibility for the rest.

### License

Licensed under the [AGPL-3.0](../LICENSE). Commercial licensing available.