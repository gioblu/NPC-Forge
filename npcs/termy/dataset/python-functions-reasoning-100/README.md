## `Tested-143k-Python-Alpaca` (Vezora's CodeTester Dataset)

The [python_functions_reasoning](https://huggingface.co/datasets/notbadai/python_functions_reasoning) is the Python (functions) coding reasoning dataset used to train Notbad v1.0 Mistral 24B reasoning model. The reasoning data were sampled from an RL-based self-improved Mistral-Small-24B-Instruct-2501 model. The Python functions and instructions were sourced from OpenCoder Dataset Stage1 and from open source projects on Github.

The [dataset_python-functions-reasoning-100.json](npcs/termy/dataset/python-functions-reasoning-100/dataset_python-functions-reasoning-100.json) file contains a subset of the original dataset featuring only the questions shorter than 100 characters, cleaned, enhanced and reformatted ready to be used by NPCs to handle prompts related to Python. 

The idea is to use this dataset, originally developed to train LLMs, to provide Python programming abilities to deterministic NPCs. The sheer amount of intents and their paraphrases makes NPCs surprisingly capable of answering Python related questions.

A lot of work has been done on the original dataset using scripts and local language models:

1. The dataset has been converted to [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md).
2. Removed all duplicated inputs.
3. Pruned inputs to a single line.
4. Removed non-ASCII characters.
5. Lowercased inputs.
6. Added input paraphrases.
7. Removed questions that require code editing (optimize this code, rewrite this code).
8. Moved source code output to `tools` to enable context usage (save it, append it, ecc.).
9. Manual curation, cleanup and enhancement.

The resulting [dataset_python-functions-reasoning-100.json](npcs/termy/dataset/python-functions-reasoning-100/dataset_python-functions-reasoning-100.json) contains **2747 intents and weights around 6.7MB**. 

The paraphrases generation was done using [granite-4.1 3B](https://www.ibm.com/granite/docs/models/granite4-1) and required around 12 hours of compute on an obsolete machine with 16GB of RAM, Intel i7-4790K CPU and NVIDIA GeForce GTX 1050 Ti.

### License 

The [dataset_python-functions-reasoning-100.json](npcs/termy/dataset/python-functions-reasoning-100/dataset_python-functions-reasoning-100.json) file is licensed under [AGPL-3.0](LICENSE).

Apache license 2.0 published by [notbadai](https://huggingface.co/notbadai) on [Huggingface](https://huggingface.co/datasets/notbadai/python_functions_reasoning).
