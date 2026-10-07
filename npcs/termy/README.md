## TERMy
TERMy is an experimental neuro-symbolic AI terminal assistant implemented using [FlintParser](/src/FlintParser.py) and [FlintNPC](/src/FlintNPC.py) that translates your plain English requests in shell scripts in milliseconds. It is incredibly lightweight and can run on very small targets such as the Raspberry Pi, just type `termy` followed by your prompt:

<img src="/npcs/termy/showcase.gif" style="width: 650px">


> [!WARNING]
> This is the second experimental release of [NPC-Forge](https://github.com/gioblu/NPC-Forge) distributed "AS IS" without any warranty, use it at your own risk.

### How to install TERMy
Open the terminal inside the npc-forge repository main directory and digit:
```bash
npc-forge install npcs/termy
```
If you plan to work with the dataset install both `npc-forge` and TERMY in development mode:
```bash
# Clone the forge from the cloud
git clone https://github.com/gioblu/NPC-Forge.git

# Step into the temple of clean code
cd NPC-Forge

# Run the installation script in development mode
chmod +x setup.sh && ./setup.sh --dev

# Install TERMy
npc-forge install npcs/termy
```

### How to use it

Just digit `termy` followed by your request:
```
termy hello
```

You can also write a script in plain english and pass it to termy, create a file `test.termy` with the following content:
```
search on wiki the programma 101
append it to p101.txt
open it in the browser 
```
Then digit:
```
termy -y < test.termy
```
Watch TERMy transpile it to a Shell script and execute it.

Then digit `termy -y < test.termy` and watch TERMy transpile it to a Shell script and execute it. 

### Flags

- `-y, --yes`: Automatically answer "yes" to prompts, skipping execution confirmation (ideal for scripted `.termy` files).
- `-g, --generate`: Force the request to be processed by the configured LLM to generate a new script/intent.
- `-c, --context`: Set the response buffer size in tokens (default: 4096). TERMy dynamically estimates the total context window needed, rounding to VRAM-optimized boundaries (e.g., 8192, 16384) to prevent out-of-memory errors and ensure efficient inference.
- `-a, --agent`: Include session context (active file, active content, last output) for agentic workflows and multi-step debugging.
- `-d, --delete-context`: Include session context (active file, active content, last output) for agentic workflows and multi-step debugging.

### Configuration

TERMy's behavior is controlled by the `config.json` file located in the `npcs/termy/` directory. You can customize its thresholds, LLM fallback, and system integrations by editing this file.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | The display name of the NPC instance. |
| `threshold` | float | The minimum confidence score (0.0 to 1.0) required for TERMy to execute a deterministic intent without asking for clarification. |
| `synonym_contribution` | float | Weight given to synonym matching. Higher values make TERMy more tolerant of varied phrasing. |
| `suggestions` | int | Maximum number of related intents to show when a request is rejected or has low confidence. |
| `tts` | string | The system Text-to-Speech engine to use (e.g., `espeak-ng`, `say` on macOS, `festival`). Set to `null` or `""` to disable. |
| `llm` | object | Contains the LLM fallback configuration |

### LLM Fallback Configuration (`llm` object)
Controls the hybrid generation mode when triggered via the `-g` flag or low-confidence fallback.

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Master switch for LLM fallback capabilities. |
| `model` | string | The specific Ollama model to use for code generation and reasoning. |
| `api_url` | string | The endpoint for the Ollama API. Change this if your Ollama instance runs on a different port or host. |
| `ctx_cap` | int | The default response buffer size (in tokens) for LLM generation. TERMy dynamically estimates total context needs and rounds up to the nearest power of 2 (e.g., 8192, 16384) to optimize VRAM usage. |

### Advanced features and hybrid mode

While TERMy is fundamentally deterministic, it is a powerful **hybrid harness** powered by local LLMs (like Ollama) that implements prompt semantic caching and continuous learning.

If TERMy encounters an error or an unknown request, you can iteratively refine it using natural language:
```bash
# 1. Generate a script for a new task
termy -g "create a python script that draws 200 random green triangles"

# 2. If it fails, just ask it to fix the error using the saved context
termy -a -g "fix it"

# 3. Refine the output
termy -a -g "yes, but make each triangle a random shade of green"
```
When the LLM generates a valid new intent, TERMy will prompt you to save it to the local dataset. Once saved, future identical requests will execute deterministically in milliseconds without invoking the LLM, making TERMy smarter and faster over time.

> [!TIP]
> TERMy's dynamic context estimation ensures that even when falling back to an LLM, it uses the minimum necessary VRAM, making it highly efficient on consumer hardware.

### Conditions
You can pass standard conditional structures to TERMy. The `if` statement evaluates a command string or expression, mapping it to standard exit codes: it returns `true` on `exit 0` (success) and `false` on `exit 1` (failure).

Syntax example:
```bash
termy 'if "you are a llm" then "goodbye" else "nice to meet you"'
```

<img src="/npcs/termy/showcase-turing-complete.gif" style="width: 650px">

### Loops

TERMy implements loops over a specified number of iterations; inside the loop block, you can chain multiple requests together by separating them with a comma `,`. 

Single-prompt loop:
```bash
termy execute 3 times tell me a joke
```

Multi-statement loop (separated by commas):
```bash
termy execute 3 times tell me a joke, inspire me
```
In the examle above TERMy will loop 3 times, generating a joke and a famous quote at each iteration.

### How to add entries to the dataset
When TERMy does not know how to answer a question asks to the user if should generate the missing dataset entry using the configured LLM model. After the answer is generated the user is asked if the entry should be saved or not:

<img src="/npcs/termy/showcase-continuous-learning.gif" style="width: 650px">

You can also add entries manually, be sure to read carefully the [NDF 0.0 (NPC-Forge Dataset Format)](/docs/dataset.md). In the `npcs/termy/dataset` directory there are `dataset_*.json` and `templates_*.json` files which contain dataset entries organized in categories, such as `dataset_files.json` or `templates_directories.json`.

Once you added an entry remember to restart the server:
```bash
npc-forge reboot
```

### Intent lookup

If you want to explore the abilities of termy you can just write `termy` followed by a keyword:

```
termy files

TERMy | rejected | Confidence: 0.00%

Response: Your request was not specific enough, please choose between the options below! 

Related intents:

1) list files - Lists the files in the current directory.
2) create a file - Creates a new file.
3) encrypt a file - Encrypts or decrypts a file using GPG.
4) manage archives - Compresses or decompresses directories.
5) print json file - Prints JSON file with proper indentation.

```

As you can see TERMy, when is not confident enough on an answer, will output a list of intents related to your prompt.

### Acknowledgements

The dataset of TERMy was expanded thanks to these source datasets:
- [Tested-143k-Python-Alpaca](https://huggingface.co/datasets/Vezora/Tested-143k-Python-Alpaca) dataset licensed under Apache license 2.0 published by Vezora on Huggingface.
- [python_functions_reasoning](https://huggingface.co/notbadai) dataset licensed under Apache license 2.0 published by on [Huggingface](https://huggingface.co/datasets/notbadai/python_functions_reasoning).
-  [python-glaive-100](https://www.kaggle.com/datasets/thedevastator/glaive-python-code-qa-dataset) dataset licensed under [CC0 1.0 Universal (CC0 1.0)](https://creativecommons.org/publicdomain/zero/1.0/) - Public Domain Dedication by The Devastator on [kaggle](https://www.kaggle.com/datasets/thedevastator/glaive-python-code-qa-dataset).
- [Python Programming Questions Dataset](https://www.kaggle.com/datasets/bhaveshmittal/python-programming-questions-dataset) dataset licensed under CC0: Public Domain published by Bhavesh Mittal on [Kaggle](https://www.kaggle.com/datasets/bhaveshmittal/python-programming-questions-dataset).
- [nl2bash](https://github.com/TellinaTool/nl2bash/tree/master/data) dataset licensed under MIT license published by TellinaTool on [github](https://github.com/TellinaTool/nl2bash/).

