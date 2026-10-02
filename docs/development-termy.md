# TERMy - The world's first deterministic, English to Bash compiler

For the past five years the tech industry has been misled by the following dogma: 

>Natural Language Understanding (NLU) requires vectors, embeddings, parameters, GPU clusters, and deep learning. 

Everyone still thinks "Attention is all you need". A transformer with an attention layer is the silver bullet capable of solving any problem. My take is, what you effectively need to answer most questions is just a parser capable of translating natural language to something the computer can understand. 

In many cases we use the transformer to let users interact with the computer in natural language; ask a question in English, get back English. Yes, the transformer has generative abilities, but I feel sure to assert that **those are side-effects of its core working principle**, and they are both a feature and a bug when applied to this use case.

What I am trying to say is, maybe, if the goal is to translate natural language to something the computer can understand, shouldn't we use a parser? Aren't we capable of compiling python to bytecode? Can't we compile English to Bash?

As you may know by now [TERMy](/npcs/termy/README.md) is a TUI that translates natural language in terminal commands, but can also answer questions and help with python programming. This is not yet another terminal harness that routes the question to a LLM. It is a novel deterministic agent with context and tool calling abilities. [TERMy](/npcs/termy/README.md) contains 101 templates, 30857 intents and a "dataset" of 58.82MB and it is arguably **the world's most powerful open-source deterministic agent**.

Until yesterday deterministic chatbots used to cap out at a few hundred intents. Thanks to NPC-Forge, its revolutionary semantic parser [FlintParser](/docs/FlintParser.md), and its efficient intent recognition pipeline implemented in [FlinNPC](/docs/FlintNPC.md), today everyone can create a chatbot with dozens of thousands intents capable of answering in milliseconds.

Just type `termy` followed by your prompt:

[![Terminal demonstration](/npcs/termy/showcase.gif)](https://www.youtube.com/watch?v=qeIp0xePLBg)

You can also write a script in plain english, create a file `test.termy` with the following content:
```
search on wiki the programma 101
append it to p101.txt
open it in the browser 
```
Then digit `termy -y < test.termy` and watch TERMy transpile it to a Shell script and execute it. 

### Datasets

I recently started pondering if I could have used datasets originally developed to train LLMs to teach Python to deterministic NPCs; with some trial and error I have developed software to curate and format them automatically.

Thanks to these scripts I was able to release:

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

With this data I had the chance to verify practically that NPC-forge and TERMy can handle "immense" datasets, remaining reliable, and still, answer in milliseconds. The sheer amount of intents and their paraphrases makes TERMy surprisingly capable of answering questions about Python.

### Turing completeness

In the last month I have made TERMy Turing-complete. I have added the `if` and `execute n times` intents that used along with `termy_get_context` and `termy_set_context` functions make [TERMy](/npcs/termy/README.md) capable of solving any problem, just like any other programming language, with the critical difference that the human-readable language here is plain English.

### Continuous learning and semantic caching

Yesterday a deterministic agent could just reject an unknown prompt with something like "Can you be more specific?". Today we can just ask ollama, can't we?

I added the ollama provider to TERMy and now when it rejects a query because it has no knowledge about it, the question can be routed to a local LLM instructing it to generate the missing dataset entry and save it in memory in the NDF format.

This introduces three architectural advantages:

1. **SPC (Semantic Prompt Caching)**: TERMy uses the LLM only once to generate the dataset entry, then when it is generated it is cached and the LLM will never be asked that question again.

2. **MSL (Manually Supervised Learning)**: The user reviews the model's output and commits each entry to the dataset with a single keystroke.

3. **CL (Continuous Learning)**: Every saved entry expands your local dataset. Over time, [TERMy](/npcs/termy/README.md) grows smarter through usage, while its dependency on LLMs reduces.

I am convinced we should all use systems like TERMy and that the future of AI will be hybrid designs that merge the best of both worlds (deterministic and probabilistic); insanely cheap, insanely fast, and with the same generative abilities of the most expensive model you can afford.

If you liked this read consider joining our discord channel and support the development of this project.
