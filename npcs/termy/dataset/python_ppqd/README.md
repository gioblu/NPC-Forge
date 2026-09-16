## python_ppqd (Python Programming Questions Dataset)

The [Python Programming Questions Dataset](https://www.kaggle.com/datasets/bhaveshmittal/python-programming-questions-dataset) is an exceptional dataset meticulously crafted for training state-of-the-art language models such as Gemma, Llama 2, Orca, and more.

The [dataset_python_ppqd.json](npcs/termy/dataset/python_ppqd/dataset_python_ppqd.json) file contains a cleaned, enhanced and reformatted version of the Python Programming Language Dataset designed to be used by NPCs to handle prompts related to Python. 

The idea is to use this dataset, originally developed to train LLMs, to provide Python programming abilities to deterministic NPCs. The sheer amount of intents (>10k) and their paraphrases (~4 per intent) makes NPCs surprisingly capable of answering Python related questions.

A lot of work has been done on the original dataset using scripts and local language models:

1. The dataset has been converted to [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md) using [json_to_ndf.py](npcs/termy/dataset/dataset_python_ppqd/scripts/json_to_ndf.py).
2. Removed all duplicated inputs.
3. Pruned inputs to a single line.
4. Removed non-ASCII characters.
5. Lowercased inputs.
6. Added input paraphrases.
7. Removed questions that require code editing (optimize this code, rewrite this code).
8. Moved source code output to `tools` to enable context usage (save it, append it, ecc.).
9. Manual curation, cleanup and enhancement.

The resulting [dataset_python_ppqd.json](npcs/termy/dataset/python_ppqd/dataset_python_ppqd.json) contains **11456 intents and weights around 13.5MB**. 

The paraphrases generation was done using [granite-4.1 3B](https://www.ibm.com/granite/docs/models/granite4-1) and required around 24 hours of compute on an obsolete machine with 16GB of RAM, Intel i7-4790K CPU and NVIDIA GeForce GTX 1050 Ti.

### License 

The [dataset_python_ppqd.json](npcs/termy/dataset/python_ppqd/dataset_python_ppqd.json) file is licensed under [AGPL-3.0](LICENSE).

The [Python Programming Questions Dataset](https://www.kaggle.com/datasets/bhaveshmittal/python-programming-questions-dataset) is licensed under CC0: Public Domain and it was published by Bhavesh Mittal on [Kaggle](https://www.kaggle.com/datasets/bhaveshmittal/python-programming-questions-dataset).

