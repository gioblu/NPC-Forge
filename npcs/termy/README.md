## TERMy
TERMy is an experimental, deterministic terminal assistant implemented using [FlintParser](/src/FlintParser.py) and [FlintNPC](/src/FlintNPC.py) Python implementations. It is incredibly lightweight and can run on very small targets such as RPI or ESP32, just type `termy` followed by your prompt:

[![Terminal demonstration](/npcs/termy/showcase.gif)](https://www.youtube.com/watch?v=qeIp0xePLBg)

### How to install TERMy
Open the terminal inside the npc-forge repository main directory and digit:
```bash
npc-forge install npcs/termy
```
If you plan to work with the dataset install both `npc-forge` and TERMY in development mode:
```bash
# Clone the forge from the cloud
git clone https://github.com/gioblu/NPC-Forge.git

# Step into the temple of clean code
cd NPC-Forge

# Run the installation script in development mode
chmod +x setup.sh && ./setup.sh --dev

# Install TERMy
npc-forge install npcs/termy
```

### How to add entries to the dataset

Be sure to read carefully the [NDF 0.0 (NPC-Forge Dataset Format)](/docs/dataset.md). In the `npcs/termy/dataset` directory there are `dataset_*.json` and `templates_*.json` files which contain dataset entries organized in categories, such as `dataset_files.json` or `templates_directories.json`.

Once you added an entry remember to restart the server:
```bash
npc-forge reboot
```

### Intent lookup

If you want to explore the abilities of termy you can just write `termy` followed by a keyword:

```
termy files

TERMy | rejected | Confidence: 0.00%

Response: Your request was not specific enough, please choose between the options below! 

Related intents:

1) list files - Lists the files in the current directory.
2) create a file - Creates a new file.
3) encrypt a file - Encrypts or decrypts a file using GPG.
4) manage archives - Compresses or decompresses directories.
5) print json file - Prints JSON file with proper indentation.

```

As you can see TERMy, when is not confident enough on an answer, will output a list of intents related to your prompt.


