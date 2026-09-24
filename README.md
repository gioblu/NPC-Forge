
[![NPC-Forge Discord](https://img.shields.io/badge/Join-Discord-%235865F2.svg)](https://discord.gg/84zTNDzjD)
## NPC-Forge

NPC-Forge is a framework for building conversational agents with distinct personalities, multi-turn context, sentiment analysis, and tool-call support. NPCs run on the CPU (web browser or OS) even on embedded systems and obsolete hardware without relying on machine learning or LLMs.

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

### TERMy terminal assistant

[TERMy](npcs/termy/README.md) is the first NPC baked into the NPC-Forge framework. It is a cynical but very knowledgeable Linux terminal assistant that translates your natural language into shell commands without a single artificial neuron. 

Termy is **Turing-complete** and supports conditional branching, arbitrary loops, and arbitrary state manipulation; all expressed in plain English. Just type `termy` followed by your prompt:

[![Terminal demonstration](/npcs/termy/showcase.gif)](https://www.youtube.com/watch?v=qeIp0xePLBg)

You can also write a script in plain english, create a file `test.termy` with the following content:
```
search on wiki the programma 101
append it to p101.txt
open it in the browser 
```
Then digit `termy -y < test.termy` and watch TERMy transpile it to a Shell script and execute it. 

> [!TIP]
> If you want to expand the capabilities of TERMy check out the [dataset](npcs/termy/dataset) directory and the [TERMy](npcs/termy/README.md) documentation

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
> First experimental release of [NPC-Forge](https://github.com/gioblu/NPC-Forge) distributed "AS IS" without any warranty, use it at your own risk.

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
