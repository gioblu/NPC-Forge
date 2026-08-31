## NPC-Forge

NPC-Forge is a framework for building conversational agents with distinct personalities, multi-turn context, sentiment analysis, and tool-call support. NPCs run on the CPU (web browser or OS) without relying on machine learning or LLMs even on obsolete hardware.

Instead of praying for a model to do the right thing, you can now use NPC-Forge to quickly build a deterministic agent and hook it up to your favourite workflow, API or harness.

#### Why NPC-Forge? 

Many problems you encounter can be solved without machine-learning or LLMs. NPC-Forge gives you a way to solve those problems more efficiently:

* **Deterministic**:  can't hallucinate; no slop, no safety alignment filters.
* **No training**: no time wasted, update the dataset, execute `npc-forge reboot`, done
* **Very fast**: runs on the CPU, responds in milliseconds even on embedded systems and obsolete machines.
* **Plug-and-play**: implements an OpenAI-compatible API that connects your NPCs to your preferred LLM harness in seconds. Connect the NPC-Forge API endpoint to tools like Open WebUI or Copilot, and see your NPCs responding and executing tool calls at lightspeed.
* **Easily manage datasets**: specifies [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md) designed to help you organize and expand the capabilities of your NPCs  

#### NPC-Forge CLI

Administer, install, and run your NPCs with the following terminal commands:

```
npc-forge list           # Lists the installed NPCs
npc-forge test           # Run NPC-Forge test suite
npc-forge serve          # Starts OpenAi/Copilot compatible API server
npc-forge stop           # Stops server
npc-forge reboot         # Reboots server
npc-forge watch          # Starts server and watch logs in real-time
npc-forge install <path> # Installs a new NPC
```

### TERMy terminal assistant

[TERMy](npcs/termy/README.md) is the first NPC baked into the NPC-Forge framework. It is a cynical but very knowledgeable Linux terminal assistant that translates your natural language into shell commands without a single artificial neuron. Just type `termy` followed by your prompt:

[![Terminal demonstration](/npcs/termy/showcase.gif)](https://www.youtube.com/watch?v=qeIp0xePLBg)

> [!TIP]
> If you are interested to explore or expand the dataset of TERMy check out the [dataset](npcs/termy/dataset) directory!

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
> This is the first experimental release of [NPC-Forge](https://github.com/gioblu/NPC-Forge) and it is distributed "AS IS" without any warranty, use it at your own risk.

### Documentation

- [TERMy](npcs/termy/README.md)
- [FlintParser](docs/FlintParser.md)
- [FlintNPC](docs/FlintParser.md)
- [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md)
- [TCSS (Terminal Commands Security Standard)](docs/command-security.md)

### Contributing to the forge
I am developing NPC-Forge with the conviction that democratic and sustainable use of Artificial Intelligence can be achieved with **deterministic designs** driven by curated and tested datasets crafted by the community; if you can, help me out. NPC-Forge thrives on your contributions, the community grows stronger when you:
- Extend the dataset of existing NPCs
- Craft new NPCs
- Optimize or extend the framework

This is a battleground where to prove what is possible, or are you just going to sit there watching massive data centers drain entire rivers just to generate corporate emails?

### License

Licensed under the [AGPL-3.0](LICENSE), feel free to contact me directly for commercial licensing options. Let's see if your corporate checkbook can purchase an exemption.
