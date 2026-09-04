# NPC-Forge development
The scope of this document is to describe what led me to develop NPC-Forge and TERMy, the research I have done and the development decision I have taken.

### Backstory
I love research and development, you may have heard of me because of [PJON (Padded Jittering Operative Network)](https://github.com/gioblu/PJON). It is a network protocol I started developing in 2010, which was recently [implemented in silicon](http://asic.ethz.ch/2025/Pjononcroc.html) by the ETH Zurich university thanks to the research of [Pius Sieber](https://github.com/piussieber/).

I had a chance to focus for 2 months on my personal projects since early July, during the strange times of AI price hikes and the end of subsidized tokenmaxing. I was curious to see if I could develop from scratch a terminal assistant capable of handling simple natural language requests. I have a bad memory and got used to ask to copilot "activate the virtual environment" or similar trivial operations spending a non negligible sum every month. I started thinking, maybe I can do something to make my workflow more efficient? Do I really need trillions of parameters to accomplish those tasks?

### Transformers at home

I started an open-ended research on the feasibility of implementing a generative model at home and training it from scratch on the computer I used to play Kerbal Space Program in the early 2010s "upgraded" with 16GB of RAM, NVIDIA GTX 1050 Ti (4GB VRAM) and a i7-4790K (4.0GHz 8 cores) CPU. In my experiments I tend to look for minimalism, so I imposed myself a constrained environment to be forced to work towards an elegant and efficient solution. 

I first developed a framework to train and evaluate transformers, which I implemented from scratch in Python. I have started with something very similar to [NanoGPT](https://github.com/karpathy/nanogpt) with 100-200M parameters, then I added flash attention, and all the expected optimizations, I even tried novel architectures like Mamba. The results were generally unsatisfactory, creepy if not outright scary, like the following:

```
Enter your prompt (or leave blank for empty start):

What is an alien?

Generating...

Using tokenizer: /ollm/checkpoints/gpt/tinyostrich/tokenizer.model

=== Generated Text ===

He's not a member of the world. He can't believe anything anymore.
All of those animals are looking like excrements, but every mouth is not a bad one.
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
(the word `excrements` was used instead of an expletive composed of 4 letters that I am not willing to publish in here)

All my tests produced models that were prone to enter in loops repeating the same sentence, and even if trained on QA they were rarely able to consistently answer questions, specially if technical. I trained models on a collection of royalty free books from the [Project Gutemberg](https://www.gutenberg.org/), a lot of open-source software, and various datasets available on [Huggingface](https://huggingface.co/).

I quickly understood that this approach was not feasible; a proper run would have required at least a month of training non-stop. I was amazed by how my models looked alive and magical, but I was also ashamed because they were incredibly wasteful and effectively useless. 

### Local models

I pivoted to ollama and open-weight models and developed [howto](https://github.com/gioblu/howto), yet another terminal harness that uses a pre-prompt to force the model to answer only with terminal commands. Results were generally unsatisfactory because of the time required to get a response. Models like [ornith:9b](https://ollama.com/library/ornith:9b), [mistral:7b](https://ollama.com/library/mistral:7b) or [cogito:14b](https://ollama.com/library/cogito:14b) can get the job done sometimes, but they are not fast and reliable enough for general use, specially if you have only 4GB of VRAM. 

### Going deterministic

Then I remembered about the blockchain craze, when everyone wanted to fit a blockchain somewhere and sell it as the next big thing.  I didn't want to waste my time and money like all those people did in the previous hype cycle, so I started building a terminal assistant from scratch with a new set of constraints:
1. No embeddings
2. No machine-learning
3. No LLMs

### Dataset format

My intention was to implement NLU (Natural Language Understanding) from scratch without focusing too much on how others did it before me. The first things I needed was a set of conventions to rely on, so I drafted the [NDF 0.0 (NPC-Forge Dataset Format](https://github.com/gioblu/NPC-Forge/blob/main/docs/dataset.md) which specifies the dataset format of NPC-Forge. The following object contains category, input sentences, textual response, thinking traces, permission gating and tool calls to be executed in a format compatible with VS code. 
  
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
}
```
I am really in love with this, it is a self-contained atom of knowledge that can be easily edited and shared. It is very simple to expand the knowledge of conversational agents if you adhere to this convention; let's say I want my terminal assistant to learn about docker commands, I can just write down a list of objects, reload the dataset, and the NPC will instantly learn them as Neo learnt Jujitsu in The Matrix. 

The next problem to solve was, how to handle questions like "create file .gitignore"? I needed to parse the "variable" in there and understand the true meaning of the request, so I came up with this:
```json
{
    "intent": "file_creation",
    "category": "linux_files",
    "type": "template",
    "structure": [
        [
            {
                "tag": "<||vocab_create||>",
                "type": "vocab",
                "required": true
            },
            {
                "tag": "<||vocab_file||>",
                "type": "vocab",
                "required": false
            },
            {
                "tag": "<||file||>",
                "type": "filename",
                "required": true
            }
        ]
    ],
    "message": "<||completion||>",
    "tools": [
        {
            "name": "run_in_terminal",
            "arguments": {
                "command": "echo '' > '<||file||>' && termy_set_context 'active_file' '<||file||>'",
                "explanation": "Writes <||string||> in file <||file||>.",
                "goal": "Directory Allocation",
                "mode": "sync"
            }
        }
    ],
    "permission": "ask",
    "thinking": [
        "Ok, I am asked to create the file <||file||>."
    ]
},
```
Each tag like `<||vocab_create||>` represents a concept, in this case the action of creation, which is represented by multiple sinonyms:
```json
{
  "<||vocab_create||>": ["create", "make", "generate", "craft", "forge"]
}
```
One or more tags can be expected at the same position and each tag can be required or optional. The "variables" or named entities are extracted according to their `type` and a related regular expression:

```json
{
  "<||filename||>": "[\\w\\-]+\\.[a-zA-Z0-9]{2,4}",
}
```



I must thank my great friend [Kevin](https://github.com/KMathisGit) to help me thinking this out.

### Meditations on safety

Looking at the `permission` key I concluded that, enforcing the use of `"permission": "ask"` for all potentially destructive commands, the tool became inherently safe to use, obviously, potential for human error remained (bug in the implementation or in the dataset), but risks were strongly mitigated.

### The implementation

I wrote [FlintParser](https://github.com/gioblu/NPC-Forge/blob/main/docs/FlintNPC.md) and [FlintNPC](https://github.com/gioblu/NPC-Forge/blob/main/docs/FlintParser.md) classes to make use of the dataset described above, implement a NLU (Natural Language Understanding) pipeline, and all the required features for the terminal assistant to work. I wrote those classes in identical, cross-compliant implementations for both Python, for local OS environments, and JavaScript, running client-side inside any browser tab or Node.js instance.

The most difficult part was to determine what to do and in which order. I have worked a lot on a compiler for my own programming language [BIPLAN](https://github.com/gioblu/BIPLAN) and while developing that I had the honour to learn that the first thing you need to do when translating code is to remove noise and then work your way out trying the least expensive paths first.

So that's the pipeline I implemented:
1. Strip expletives, interjections, encouraging, discouraging and thanking words (remove noise)
2. Sentiment analysis
3. Exact Match (very fast)
4. Template Match (slower)
5. Probabilistic Match (even slower)
6. Response or rejection (with related intent suggestions)

While implementing step 1 I had the revelation that while stripping those words I could have stored their frequency and generate a sentiment analysis and so I implemented step 2 killing 2 birds with one stone. Once I had step 4 working I could start testing it. 

For the first time after almost 2 months throwing spaghetti at the wall and hope they stuck, I felt again the joy of working on something sane, predictable, almost something a serious engineer would work on:

```
$ termy create file test.txt and write Hello I am TERMy

TERMy | template match | Confidence: 100.00%
Thinking: WTF... when the human will learn this very simple command?

echo 'Hello I am TERMy' > 'test.txt' && termy_set_context 'active_file' 'test.txt'

Description: Writes Hello I am TERMy in file test.txt.

Response: No problemo

Execute:  ▶ Yes     No
```






