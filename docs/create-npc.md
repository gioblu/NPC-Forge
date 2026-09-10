## NPC creation guide
Using `npc-forge` you can create a new NPC very quickly and customize it for your own needs. There are 2 types of NPC:
1. Web
2. OS

### Web NPC
A web NPC runs in the webpage and can execute tool calls using [Captain.js](https://github.com/gioblu/NPC-Forge/blob/main/src/js/Captain.js). 

### OS NPC
An OS NPCs may implement some glue-code to work within an application or a terminal and some scripts used by the NPC to operate. 
If you are creating an OS NPC feel free to drop your glue-code in its directory, although it is suggested to store in the directory `scripts` all the scripts part of its dataset.

### How to create NPCs
1. Be sure you installed `npc-forge` in development mode (`./setup.sh --dev`)
2. Execute `npc-forge create my_new_npc`

This command will scaffold the directory `npcs/my_new_npc` structure and example dataset files. 

After that you can start working on your dataset!

> [!TIP]
> If you are running the NPC-Forge server, remember to execute `npc-forge reboot` to reload the dataset.

### How to test new NPCs
All NPCs are served and accessible at [127.0.0.1:5000/my_new_npc/chat](http://127.0.0.1:5000/my_new_npc/chat) and can be tested in a web chat interface.
