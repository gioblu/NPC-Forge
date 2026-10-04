## The frontier of deterministic AI

For the past five years the tech industry has been misled by the following dogma: 

>Natural Language Understanding (NLU) requires vectors, embeddings, parameters, GPU clusters, and deep learning. 

Everyone still thinks "Attention is all you need". A transformer with an attention layer is the silver bullet capable of solving any problem. My take is, what you effectively need to answer most questions is just a parser capable of translating natural language to something the computer can understand. 

In many cases we use the transformer to let users interact with the computer in natural language; ask a question in English, get back English. Yes, the LLMs have generative abilities, but I feel sure to assert that those are side-effects of their core working principle, and they are both a feature and a bug when applied to this use case.

What I am trying to say is, maybe, if the goal is to translate natural language shouldn't we just use a parser? Aren't we capable of compiling python to bytecode? Can't we compile English to Bash?

### TERMy

[TERMy](/npcs/termy/README.md) is a deterministic terminal assistant that translates natural language to terminal commands. This is not yet another terminal harness that routes prompts to a LLM. It is a novel deterministic agent with multi-turn context memory and tool-call support. It includes 101 templates and 30857 intents; a "dataset" of 58.82MB that arguably makes it the **world's most powerful, open-source, deterministic agent**.

Until yesterday deterministic chatbots capped out at a few hundred intents. Thanks to [NPC-Forge](README.md), its revolutionary semantic parser [FlintParser](/docs/FlintParser.md), and its intent recognition pipeline implemented in [FlintNPC](/docs/FlintNPC.md), today, anyone can build a chatbot with over 50,000 dataset entries that responds in less than 100 milliseconds, even on a Raspberry Pi.

Just type `termy` followed by your prompt:

<img src="/npcs/termy/showcase.gif" style="width: 650px">

You can also write a script in plain english; create the file `test.termy` with the following content:
```
search on wiki the programma 101
append it to p101.txt
open it in the browser 
```
Then type `termy -y < test.termy` and watch TERMy compile it to Bash and execute it. 

### How it works
[TERMy](/npcs/termy/README.md) is implemented using the [FlintNPC](/docs/FlintNPC.md) and [FlintParser](/docs/FlintParser.md) classes provided by [NPC-Forge](README.md).

Both classes rely on subtraction engineering: instead of adding probabilistic models, after subtracting noise (insults, interjections, stop words), the request is parsed and compiled down to a natural language response and a list of tool calls. The framework implements the following pipeline:

1. Sanitize & Strip (insults, interjections, stop words)
2. Exact Match (O(1) hash lookup)
3. Template Match (semantic structure parsing)
4. Probabilistic Match (IDF-weighted Levenshtein)
5. Rejection with optional LLM dataset entry generation

This approach is more efficient and less brittle than many alternatives that implement much more complex machine-learning techniques. If you are interested in how I came up with this stuff, I wrote about it [here](/docs/development.md).

### Datasets
I recently started pondering if I could have used datasets originally developed to train LLMs to expand the knowledge of deterministic agents. I looked at the material available on [huggingface](https://huggingface.co/) and I found a lot of datasets composed of question and answer about python. With some trial and error I have developed software to curate and format datasets automatically in the [NDF](/docs/dataset.md) format used by [NPC-Forge](/README.md). Thanks to these scripts I was able to release:

1. [python_ppqd](/npcs/termy/dataset/python-functions-reasoning-100/README.md) 8777 intents around 10.8MB.

2. [python-functions-reasoning-100](/npcs/termy/dataset/python-functions-reasoning-100) 2747 intents around 6.7MB.

3. [Tested-143k-Python-Alpaca-80](/npcs/termy/dataset/Tested-143k-Python-Alpaca-80) 8027 intents around 16.1MB.

4. [python-glaive-100](/npcs/termy/dataset/python-glaive-100) 4042 intents around 9.7MB.

This is more or less the data curation pipeline I have implemented:

1. Selected only short questions (80 or 100 characters).
2. Removed code editing questions (optimize this code, rewrite this code).
3. Pruned special characters.
4. Pruned entries that contains broken code.
5. Pruned duplicates, kept higher quality entries.
6. Lowercased inputs.
7. Added input paraphrases.

The paraphrases generation was done using [granite-4.1 3B](https://www.ibm.com/granite/docs/models/granite4-1) and required more than 2 days of compute on an obsolete machine with 16GB of RAM, Intel i7-4790K CPU and NVIDIA GeForce GTX 1050 Ti.

With this data I had the chance to verify practically that [NPC-Forge](README.md) and TERMy can handle "immense" datasets, remaining reliable, and still, answer in milliseconds. The sheer amount of intents and their paraphrases makes TERMy surprisingly capable of answering questions about Python.

### Turing completeness

Recently TERMy became Turing-complete. I have added the `if` and `execute n times` intents that used along with `termy_get_context` and `termy_set_context` functions make [TERMy](/npcs/termy/README.md) capable of solving any problem, just like any other programming language, with the critical difference that the human-readable language here is plain English.

### Continuous learning and semantic caching

Yesterday, a deterministic agent could just reject an unknown prompt with something like "Can you be more specific?". Today we can just ask ollama, can't we?

I added the [ollama provider](/src/providers/ollama.py) to NPC-Forge and now when it rejects a query because it has no knowledge about it, the question can be routed to a local LLM instructing it to generate the missing dataset entry and save it in memory in the NDF format.

Introducing this simple feature enables:

1. **SPC (Semantic Prompt Caching)**: The LLM is used once to generate the answer and will never be asked that question again.

2. **MSL (Manually Supervised Learning)**: Users review the model's output and commit it with a single keystroke.

3. **CL (Continuous Learning)**: Over time [TERMy](/npcs/termy/README.md) grows smarter while its dependency on LLMs reduces.

I am convinced we should all use systems like TERMy and that the future of AI will be hybrid designs that merge the best of both worlds (deterministic and probabilistic); insanely cheap, insanely fast, and with the same generative abilities of the most expensive model you can afford.
