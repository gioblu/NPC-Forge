
[![NPC-Forge Discord](https://img.shields.io/badge/Join-Discord-%235865F2.svg)](https://discord.gg/84zTNDzjD)
## NPC-Forge

NPC-Forge is an experimental framework for building hybrid AI agents with distinct personalities, multi-turn context memory, sentiment analysis, and tool-call support. NPCs run on the CPU (web browser or OS) even on embedded systems and obsolete hardware without relying on machine learning or LLMs.

Instead of praying for a model to do the right thing, you can now use NPC-Forge to quickly build a deterministic agent and hook it up to your favourite workflow, API or harness.

#### Why NPC-Forge? 

Many problems you encounter can be solved without machine-learning or LLMs. NPC-Forge gives you a way to solve those problems more efficiently:

* **Deterministic**:  can't hallucinate or generate slop; has no safety alignment filters.
* **Fast**: runs on the CPU and responds in milliseconds.
* **Reliable**: tolerates typos, expletives, interjections and word inversions much better than NLP.js
* **Extensible**: datasets can be developed with ease thanks to [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md).
* **No training**: update the dataset, execute `npc-forge reboot`, and you are done.
* **Plug-and-play**: implements an OpenAI-compatible API that connects your NPCs to your preferred LLM harness in seconds. Connect the NPC-Forge API endpoint to tools like Open WebUI or Copilot, and see your NPCs responding and executing tool calls at lightspeed.

#### NPC-Forge CLI

Administer, install, and run your NPCs with the following terminal commands:

```
npc-forge list           # Lists the installed NPCs
npc-forge test           # Run NPC-Forge test suite
npc-forge serve          # Starts OpenAi/Copilot compatible API server
npc-forge stop           # Stops server
npc-forge reboot         # Reboots server
npc-forge watch          # Starts server and watch logs in real-time
npc-forge create         # Creates new NPC using the example profile
npc-forge install <path> # Installs a new NPC
```
Additional information can be found in the [NPC-Forge CLI](docs/NPC-Forge-cli.md) documentation.

### TERMy-24k terminal assistant
[TERMy-24k](/npcs/termy/README.md) is a hybrid AI terminal assistant that includes a deterministic engine capable of translating natural language to terminal commands. It is implemented upon the [NPC-Forge](README.md) framework which provides all the infrastructure required for users to work efficiently with deterministic agents and local LLMs. This is not yet another terminal harness that just routes prompts. It provides hybrid agentic capabilities, access to a local knowledgebase of responses, while still being capable of consulting LLMs when perplexed and save the newly generated answers locally for future use. It implements a novel and very efficient approach to multi-turn context memory that enable both the deterministic engine and the LLM to cooperate to accomplish the task. 

<a href="https://www.youtube.com/watch?v=mIoUCLJDJ1U"><img src="/npcs/termy/showcase.gif" style="width: 650px"></a>

The local dataset weights 47.35MB, is composed of 102 templates, 24,274 intents and arguably makes [TERMy-24k](/npcs/termy/README.md) the **world's most powerful, open-source, deterministic agent**.

Until yesterday deterministic chatbots capped out at a few hundred intents. Thanks to [NPC-Forge](README.md), its revolutionary semantic parser [FlintParser](/docs/FlintParser.md), and its intent recognition pipeline implemented in [FlintNPC](/docs/FlintNPC.md), today, anyone can build a chatbot with over 50,000 dataset entries that responds in less than 100 milliseconds, even on a Raspberry Pi.

You can also write a script in plain english, create a file `test.termy` with the following content:
```
search on wiki the programma 101
append it to p101.txt
open it in the browser 
```
Then digit `termy -y < test.termy` and watch TERMy transpile it to a Shell script and execute it. 

> [!TIP]
> If you want to expand the capabilities of TERMy check out the [dataset](npcs/termy/dataset) directory and the [TERMy](npcs/termy/README.md) documentation

#### Advanced features and hybrid mode

While TERMy is fundamentally deterministic, it is also a very powerful **hybrid harness** that can be used for agentic coding. You can use TERMy and go straight to your local LLM if you need while retaining its revolutionary context memory and instantaneous deterministic responses. This is a practical example of how it can be used:


<a href="https://www.youtube.com/watch?v=1WQBMnXlCiM"><img src="/npcs/termy/showcase-llm.gif" style="width: 650px"></a>

When the LLM generates a new valid dataset entry, TERMy will ask if to save it to the local dataset. Once saved, future similar requests will execute deterministically in milliseconds without invoking the LLM, making TERMy smarter and faster over time.

<a href="https://www.youtube.com/watch?v=xgzD2akCj3k"><img src="/npcs/termy/showcase-continuous-learning.gif" style="width: 650px"></a>

### Quick start to redemption
Reclaim control on your workflow in less than sixty seconds:

```bash
# Clone the forge from the cloud
git clone https://github.com/gioblu/NPC-Forge.git

# Step into the forge and install it
cd NPC-Forge && chmod +x setup.sh && ./setup.sh

# Install TERMy
npc-forge install npcs/termy

# Chat with TERMy
termy how are you
```
Consider that this experimental release of `npc-forge` works only on Linux and WSL.

> [!WARNING]
> This is the second experimental release of [NPC-Forge](https://github.com/gioblu/NPC-Forge) distributed "AS IS" without any warranty, use it at your own risk.

### Documentation
- [TERMy](npcs/termy/README.md)
- [FlintParser](docs/FlintParser.md)
- [FlintNPC](docs/FlintNPC.md)
- [NPC-Forge CLI](docs/NPC-Forge-cli.md)
- [NPC-Forge API](docs/NPC-Forge-API.md)
- [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md)
- [TCS 0.0 (Terminal Commands Security)](docs/commands-security.md)
- [NPC creation guide](docs/create-npc.md)

### Contributing to the forge
I am developing NPC-Forge with the conviction that democratic and sustainable use of Artificial Intelligence can be achieved with **deterministic designs** driven by curated and tested datasets crafted by the community; if you can, help me out. NPC-Forge thrives on your contributions, the community grows stronger when you:
- Extend the dataset of existing NPCs
- Craft new NPCs
- Optimize or extend the framework

Or are you just going to sit there waiting for the water to reach the boiling point?

The following list contains the contributors; with their support, expertise, kindness and talent NPC-Forge and TERMy are getting better by the day:
[Fred Larsen](https://github.com/fredilarsen), [Kevin Mathis](https://github.com/KMathisGit), [Cristiano Pizzarelli](https://github.com/LordEnd13), [David Starkweather](https://github.com/starkdg), [SyN-droMe](https://github.com/SyN-droMe), [AnonymousMonkeyNo12](https://github.com/AnonymousMonkeyNo12)

### License

Licensed under the [AGPL-3.0](LICENSE), feel free to contact me directly for commercial licensing options. Let's see if your corporate checkbook can purchase an exemption.
