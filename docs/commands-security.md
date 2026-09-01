
## NPC-Forge TCS 0.0 (Terminal Commands Security)

TCS 0.0 (Terminal Commands Security) defines the requirements for parsing, matching, and executing system commands securely within `npc-forge`. 

To eliminate **Command Injection** vulnerabilities and nasty bugs the framework enforces the following sacred requirements that must never be violated:

1. Commands **must** use single-quote isolation where there is arbitrary input (user prompt, http responses, ecc.) and the implementation must escape `'` in arbitrary input
2. Commands concatenating multiple variables **must** use `printf`
3. Commands that invoke native binaries must use the Double-Dash (`--`) separator before passing arbitrary input.

### Single-quote isolation

All shell execution configurations located in datasets **must** encapsulate tags using single quotes (`'...'`). This structure tells the Linux kernel to treat everything inside the tag bounds as a literal string, deactivating inline command evaluation.

#### Vulnerable
```json
"command": "echo \"<||string||>\" > <||file||>"
```

#### Secure
```json
"command": "echo '<||string||>' > <||file||>"
```

### `printf` Parameterization
When a sequence requires injecting multiple structural fields (e.g., user account profiles, system contextual parameters) inside a continuous text block, the pipeline **must** utilize `printf` over `echo`. This maps textual layouts into clear, separate, isolated parameters, eliminating the maintenance hell of nested quote concatenation.

```json
"command": "printf 'Welcome %s, payload: %s\n' '<||username||>' '<||string||>' > <||file||>"
```

### Flag Injection Mitigation
When user-controlled input (like `<||file||>` or `<||string||>`) is passed as an argument to POSIX utilities (e.g., `touch`, `rm`, `mkdir`, `cat`, `grep`), a malicious or accidental input starting with a hyphen (e.g., `-rf /` or `--help`) will be interpreted by the utility as a system flag rather than text.

To neutralize this, all template commands invoking native binaries **must** use the Double-Dash (`--`) separator immediately before passing user variables. The `--` syntax signals to the utility that command-line option parsing has ended, forcing it to treat everything that follows as literal filenames or arguments.

#### Vulnerable
```json
"command": "touch <||file||>"
```
*If `<||file||>` evaluates to `-rf`, the system interprets it as a malformed option or executes unintended binary flags.*

#### Secure
```json
"command": "touch -- <||file||>"
```
*If `<||file||>` evaluates to `-rf`, the utility safely creates a file literally named `"-rf"` without executing system flags.*

