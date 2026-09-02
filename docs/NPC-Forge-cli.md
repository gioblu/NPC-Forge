## `npc-forge` CLI

The NPC-Forge CLI provides an interface to administer, install, and run your NPCs. This tool serves NPCs, streams logs and executes framework tests. Run it using the `npc-forge` command. 

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

#### `install <path> [--dev]`
Installs an NPC profile from a local directory into the `npc-forge` registry. Copies the entire source directory (datasets, scripts, entry points) to `~/.local/share/npc-forge/npcs/<name>` and executes `setup.sh` if it exists in the source directory. Use `--dev` to pass the developer flag to the setup hook.

```bash
# Standard installation
npc-forge install ./npcs/termy

# Developer/Editable installation
npc-forge install ./npcs/termy --dev
```

#### `list`
Prints a list of all installed NPCs including the creator's name, intent count, vocabulary size, dataset size and tool availability.

```text
Installed NPCs:

termy (intents: 42, vocabulary: 150, dataset: 1.2MB, tools: yes) by Alice
guard_bot (intents: 12, vocabulary: 45, dataset: 340.5KB, tools: no) by Bob
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

It passes the `--dev` argument to the NPC's `setup.sh` hook (if one exists), allowing the NPC's custom installer to set up symlinks, editable installs, or dev-specific dependencies. If the target directory is already symlinked/installed in dev mode, the tool will detect the path match and skip the file copy process to preserve your local working directory.


### Help

To view the built-in help screen and quick reference directly from the terminal, run:

```bash
npc-forge --help
# or
npc-forge -h
```
