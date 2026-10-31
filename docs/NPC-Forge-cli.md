## `npc-forge` CLI

The NPC-Forge CLI provides an interface to administer, install, and run your NPCs. This tool serves NPCs, streams logs, manages datasets, and executes framework tests. Run it using the `npc-forge` command. 

```bash
npc-forge <command> [options]
```

### Service Management

| Command | Aliases | Description |
| :--- | :--- | :--- |
| `serve` | `start` | Starts the background `npc-forge.service` systemd user daemon. |
| `stop` | - | Stops the background registry service. |
| `restart` | `reboot` | Restarts the background registry service. |

```bash
npc-forge start
npc-forge stop
npc-forge restart
```

### NPC Management

#### `create <name>`
Scaffolds a new NPC profile from the built-in example template. Creates a new directory at `~/.local/share/npc-forge/npcs/<name>` and populates it with the standard dataset, vocabulary, and configuration files. The `name` property in `config.json` is automatically updated to match the provided name.

```bash
npc-forge create my_new_npc
```

It is possible to test the newly created NPC by executing `npc-forge serve` and then visiting [127.0.0.1:5000/my_new_npc/chat](http://127.0.0.1:5000/my_new_npc/chat).

#### `install <path> [--dev]`
Installs an NPC profile from a local directory into the `npc-forge` registry. Copies the entire source directory (datasets, scripts, entry points) to `~/.local/share/npc-forge/npcs/<name>` and executes `setup.sh` if it exists in the source directory. Use `--dev` to pass the developer flag to the setup hook.

```bash
# Standard installation
npc-forge install ./npcs/termy

# Developer/Editable installation
npc-forge install ./npcs/termy --dev
```

#### `list`
Prints a formatted table of all installed NPCs including their name, template count, intent count, vocabulary size, total dataset size, and last modified date.

```text
Name       Templates  Intents  Vocabulary  Total size  Last modified         
termy      5          42       150         1.20 MB     31-10-2026 14:30:00   
guard_bot  2          12       45          340.5 KB    30-10-2026 09:15:00   
```

#### `dataset <npc>`
Manages optional datasets for a specific installed NPC. Opens an interactive TUI menu to view, download, or remove configured datasets for the target NPC.

```bash
npc-forge dataset termy
```

### Diagnostics & Testing

#### `logs` / `watch`
Streams live logs from the systemd server daemon using the native Linux `tail` utility. Displays the last 20 lines of the log file and follows new entries. Press `Ctrl+C` to exit the stream.

```bash
npc-forge logs
```

#### `test` / `tests`
Executes the test suite using the Python interpreter located in the local `venv` directory. Looks for a custom runner at `tests/run_tests.py`. If not found, falls back to standard `unittest discover`.

```bash
npc-forge test
```

### Development Mode

When developing a new NPC, you can use the `--dev` flag during installation:

```bash
npc-forge install ./path/to/my_npc --dev
```

This passes the `--dev` argument to the NPC's `setup.sh` hook (if one exists), allowing the NPC's custom installer to set up symlinks, editable installs, or dev-specific dependencies. If the target directory is already symlinked/installed in dev mode, the tool will detect the path match and skip the file copy process to preserve your local working directory.

### Help

To view the built-in help screen and quick reference directly from the terminal, run:

```bash
npc-forge --help
# or
npc-forge -h
```