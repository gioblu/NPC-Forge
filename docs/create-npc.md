## NPC creation guide
The NPC-Forge framework can scaffold a new NPC in seconds and it is then very easy to customize it for any need. 

### How to create NPCs
1. Be sure you installed `npc-forge` in development mode (`./setup.sh --dev`)
2. Execute `npc-forge create my_new_npc`

This command will scaffold the directory `npcs/my_new_npc` structure and example dataset files, that is where your NPC's dataset lives.

Read the [NDF 0.0 (NPC-Forge Dataset Format)](docs/dataset.md), this document will help you understand the dataset format.

After that you are ready to work on your NPC!

> [!TIP]
> If you are running the NPC-Forge server, remember to execute `npc-forge reboot` to reload the dataset.

### How to test new NPCs
All NPCs are served and accessible at [127.0.0.1:5000/my_new_npc/chat](http://127.0.0.1:5000/my_new_npc/chat) and can be tested in a web chat interface.
