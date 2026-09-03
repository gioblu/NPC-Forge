# NPC-Forge development
The scope of this document is to describe what led me to develop NPC-Forge and TERMy, the research I have done and the development decision I have taken.

### Backstory
I love research and development, you may heard of me because of [PJON (Padded Jittering Operative Network)](https://github.com/gioblu/PJON). It is a network protocol I started developing in 2010, which was recently [implemented in silicon](http://asic.ethz.ch/2025/Pjononcroc.html) by the ETH Zurich university thanks to the research of [Pius Sieber](https://github.com/piussieber/).

I had the chance to focus for 2 months on my personal projects since early july, NPC-Forge is what I came up with. 

I started an open ended research on the feasibility of building a generative model at home, training it from scratch on the computer I used to play Kerbal Space Program in the early 2010s "upgraded" with 16GB of DDR3 RAM, a NVIDIA GeForce GTX 1050 Ti (4GB VRAM) and a i7-4790K (4.0GHz 8 cores) CPU. In my experiments I tend to look for minimalistic solutions, so I imposed myself a constrained set of tools to be forced to work towards an elegant and efficient solution. 

I first developed a framework to train and evaluate transformers, which I implemented from scratch in Python. I have started with something very similar to [NanoGPT](https://github.com/karpathy/nanogpt) then I added flash attention, and all the expected optimizations, I even tried more novel architectures like Mamba.
The results were generally unsatisfactory, creepy if not outright scary, like the following:

```
Enter your prompt (or leave blank for empty start):

  ▸ What is an alien?

◈ Generating…

Using tokenizer: /ollm/checkpoints/gpt/tinyostrich/tokenizer.model

=== Generated Text ===

He's not a member of the world. He can't believe anything anymore.
All of those animals are looking like dung, but every mouth is not a bad one.
They look alike, all of which are really terrible.
They get their own life, and each is a sign that they're not.
They're all right, they say.
They're just some different things they can make.
They've never seen them.
They were better not. Some of them've got their rights.
Some of them have to go.
But we're not looking for the future on how many.
The last two of them are all in the universe.
```
All my tests produced models that were prone to enter in loops often repeating the same sentence, and even if trained on QA they never were able to consistently answer to questions, specially if technical.
I trained models on a collection of royalty free books from the [Project Gutemberg](https://www.gutenberg.org/), and various datasets available on [Huggingface]().

### Going deterministic

I quickly understood that this approach was not feasible; a proper run would have required at least a month of training non-stop.  I was amazed by how my model looked alive and magical, but I was also ashamed because they were incredibly wasteful and effectively useless. 

Then I remembered about the blockchain craze, when everyone wanted to fit a blockchain somewhere and sell it as the next big thing.  I didn't want to waste my time and money like all those people did in the previous hype cycle, so I started building a conversational agent from scratch with a new set of constraints:
1. No embeddings
2. No machine-learning
3. No LLMs

### A terminal assistant

My intention was to implement NLU (Natural Language Understanding) from scratch without focusing too much on how others did it before me. I needed an idea for a technology demonstrator that could have shown the capabilities of the underlying algorithms, so I chose to develop a terminal assistant. The first things I needed was a set of conventions to rely on and a dataset format. 
I then drafted the [NDF 0.0 (NPC-Forge Dataset Format](https://github.com/gioblu/NPC-Forge/blob/main/docs/dataset.md) and specified the dataset format of NPC-Forge. The following object contains the category, the input sentences, the tool calls to be executed in a format compatible with VS code, the textual response, the thinking traces and the permission gating. 
  
```json
{
    "category": "linux_files",
    "input": [
        "list files",
        "list files and directories"
    ],
    "tools": [
        {
            "name": "run_in_terminal",
            "arguments": {
                "command": "ls -lah",
                "explanation": "Lists the files in the current directory.",
                "goal": "Display current directory contents",
                "mode": "sync"
            }
        }
    ],
    "message": "Done",
    "thinking": [
      "That is quite simple!",
      "This is boring..."
    ],
    "permission": "yolo"
},
```
I am really in love with this thing, it is very simple to expand the knowledge of NPCs with this, let's say I want my NPC to learn JuJitsu, I can just write down a list of objects, reload the dataset, and the NPC will instantly know Jujitsu as happened to Neo in The Matrix. I must thank my great friend [Kevin](https://github.com/KMathisGit) to help me thinking this out.

TBC...
