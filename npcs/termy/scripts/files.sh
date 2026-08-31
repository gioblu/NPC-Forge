#!/bin/bash

# Find a particular function in source.
# supports Python, Rust, Go, Javascript, Typescript, C, C++, PHP
# Uses grep by default (available everywhere), ripgrep as optional speedup
# Usage: find_function_in_source <function_name> [search_dir]

find_function_in_source() {
    local target_name="$1"
    local search_dir="${2:-.}"
    
    # Validate inputs
    if [ -z "$target_name" ]; then
        printf "⛔ Error: Function name required\n" >&2
        return 1
    fi
    
    if [ ! -d "$search_dir" ]; then
        printf "⛔ Error: Directory not found: %s\n" "$search_dir" >&2
        return 1
    fi
    
    # Use ripgrep if available (faster), otherwise use grep (slower but always available)
    if command -v rg > /dev/null 2>&1; then
        # Ripgrep path: faster with type filtering
        rg -n -C 2 -t py -t go -t php -t c -t cpp -t js -t ts -t rust \
           "\b(def|func|function|fn)\s+${target_name}\b|^[a-zA-Z0-9_*]+\s+${target_name}\s*\(" \
           "$search_dir" 2>/dev/null || {
            printf "⚠️  No matches found for function: %s\n" "$target_name"
            return 0
        }
    else
        # Grep fallback: search all source files
        find "$search_dir" \( -name "*.py" -o -name "*.go" -o -name "*.php" -o -name "*.c" -o -name "*.cpp" -o -name "*.js" -o -name "*.ts" -o -name "*.rs" \) 2>/dev/null | \
        xargs grep -n -B 2 -A 2 -E "\b(def|func|function|fn)\s+${target_name}\b|^[a-zA-Z0-9_*]+\s+${target_name}\s*\(" 2>/dev/null || {
            printf "⚠️  No matches found for function: %s\n" "$target_name"
            return 0
        }
    fi
}

# Monitor system, auth, or web server logs in real-time
monitor_logs() {
    local target="${1:-system}"
    local log_title=""
    local log_cmd=""

    case "$target" in
        "auth")
            log_title="🔒 Monitoring Authentication & Security Logs"
            # Fallback for Ubuntu/Debian (auth.log) or CentOS/RHEL (secure)
            if [ -f /var/log/auth.log ]; then
                log_cmd="tail -n 20 -f /var/log/auth.log"
            else
                log_cmd="tail -n 20 -f /var/log/secure"
            fi
            ;;
        "nginx")
            log_title="🌐 Monitoring Nginx Error Logs"
            log_cmd="tail -n 20 -f /var/log/nginx/error.log"
            ;;
        "kernel")
            log_title="💻 Monitoring Kernel Logs"
            log_cmd="journalctl -k -n 20 -f"
            ;;
        "system"|*)
            log_title="🛑 Monitoring System Error Logs"
            log_cmd="journalctl -p 3 -n 20 -f"
            ;;
    esac

    # 1. Output the styled header
    echo -e "${log_title} \n\033[1m(Ctrl+C to exit):\033[22m\n"

    # 2. Voice announcement
    termy_say -s "Starting ${target} log monitoring."

    # 3. Execute the selected log stream safely
    eval "$log_cmd" 2>/dev/null || {
        termy_say "⛔ Error: Unable to access the requested log file or service."
        return 1
    }
}

# Read and display the current user's command history from the history file
show_history() {
    printf "📜 Command history:\n\n"
    termy_say -s "Retrieving your command history."
    local history_file="${HISTFILE:-$HOME/.bash_history}"

    if [ -f "$history_file" ]; then
        nl -w 5 -s "  " "$history_file" | tail -n 50
    else
        termy_say "⛔ Error: Unable to locate your bash history file."
        return 1
    fi
}

# Search for virtual environments in subdirectories, prompt for verification, and activate upon confirmation
locate_and_activate_venv() {
    local config_file="$HOME/.termy_config.json"
    local found_venv=""

    termy_say -s "Scanning local subdirectories for Python virtual environments."

    # It safely targets directories containing a valid bin/activate script
    if ! found_venv=$(find . -type d -name "node_modules" -prune -o -path "*/bin/activate" -print -quit 2>/dev/null); then
        printf "\n⛔ \033[1mSearch Failed\033[22m\n\n"
        printf "An error occurred during the filesystem traversal.\n"
        termy_say -s "Error occurred while searching the directory tree."
        return 1
    fi

    if [ -z "$found_venv" ]; then
        printf "\n⛔ \033[1mNo Environment Found\033[22m\n\n"
        printf "Could not locate a Python virtual environment in this path or its subdirectories.\n"
        termy_say -s "No virtual environment detected in the local subdirectories."
        return 1
    fi

    local venv_root
    venv_root=$(dirname "$(dirname "$found_venv")")
    
    local absolute_venv_path
    absolute_venv_path=$(cd "$venv_root" && pwd)

    printf "\n🔍 \033[1mVirtual Environment Located\033[22m\n\n"
    printf "Relative Path : %s\n" "$venv_root"
    printf "Absolute Path : %s\n\n" "$absolute_venv_path"

    termy_say -s "I found a virtual environment at $venv_root. Is this the correct one?"
    
    local user_confirmation
    
    read -r -p "Is this the correct environment? (y/N): " user_confirmation </dev/tty
    user_confirmation=$(echo "$user_confirmation" | tr '[:upper:]' '[:lower:]' | xargs)

    if [[ "$user_confirmation" == "y" || "$user_confirmation" == "yes" ]]; then
        if [ ! -f "$config_file" ]; then
            echo "{}" > "$config_file"
        fi

        local temp_json
        if temp_json=$(jq --arg path "$absolute_venv_path" \
                         '.python_venv_path = $path' \
                         "$config_file" 2>/dev/null); then
            echo "$temp_json" > "$config_file"
            
            printf "\n🚀 \033[1mEnvironment Verified and Activated\033[22m\n\n"
            termy_say -s "Configuration saved. Activating the virtual environment now."
            
            source "${absolute_venv_path}/bin/activate"
        else
            termy_say "⛔ Error: Failed to record the environment path inside the configuration file."
            return 1
        fi
    else
        printf "\n⚠️  Environment activation cancelled by user request.\n\n"
        termy_say -s "Activation canceled."
        return 0
    fi
}

create_env_file() {
    local env_file=".env"
    local config_file="$HOME/.termy_config.json"

    termy_say -s "Initializing environment configuration sequence."

    if [ -f "$env_file" ]; then
        termy_say -s "An environment file already exists. Do you want to overwrite it?"
        local confirm
        read -r -p "A .env file already exists. Overwrite and clear it? (y/N): " confirm </dev/tty
        confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]' | xargs)
        if [[ "$confirm" != "y" && "$confirm" != "yes" ]]; then
            printf "⚠️  \033[1mOperation Aborted\033[22m\nFile preservation maintained.\n\n"
            termy_say "Operation cancelled."
            return 0
        fi
    fi

    echo "# Environment Configuration Generated by TERMy" > "$env_file"
    printf "📝 \033[1mSuccess\033[22m environment file initialized successfully at './%s'.\n\n" "$env_file"
    termy_say -s "Environment file initialized successfully."
}

add_env_entry() {
    local env_file=".env"

    if [ ! -f "$env_file" ]; then
        printf "⛔ \033[1mMissing File\033[22m\nNo .env file found. Please initialize one first.\n\n"
        termy_say "Error. No environment file detected."
        return 1
    fi

    termy_say -s "Please enter the configuration key name."
    local env_key
    read -r -p "Enter Key Name (e.g., API_KEY): " env_key </dev/tty
    env_key=$(echo "$env_key" | tr -d '[:space:]' | tr '[:lower:]' '[:upper:]')

    if [ -z "$env_key" ]; then
        termy_say "Key name cannot be empty. Entry setup aborted."
        return 1
    fi

    termy_say -s "Please enter the value for $env_key."
    local env_val
    read -r -p "Enter Value for $env_key: " env_val </dev/tty
    env_val=$(echo "$env_val" | xargs)

    grep -v "^${env_key}=" "$env_file" > "${env_file}.tmp" && mv "${env_file}.tmp" "$env_file"

    echo "${env_key}=\"${env_val}\"" >> "$env_file"

    printf "✅ \033[1mEntry Updated\033[22m key '%s' has been recorded successfully.\n\n" "$env_key"
    termy_say -s "Entry added successfully for $env_key."
}

remove_env_entry() {
    local env_file=".env"

    if [ ! -f "$env_file" ]; then
        printf "⛔ \033[1mMissing File\033[22m\nNo .env file found in the active workspace.\n\n"
        termy_say "Error. No environment file detected."
        return 1
    fi

    local keys=()
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^# && -n "$line" && "$line" == *=* ]]; then
            keys+=("${line%%=*}")
        fi
    done < "$env_file"

    if [ ${#keys[@]} -eq 0 ]; then
        printf "⚠️  \033[1mEmpty File\033[22m\nNo configurable entries found inside the .env file.\n\n"
        termy_say "The environment file contains no keys to remove."
        return 0
    fi

    printf "🗑️  \033[1mSelect Key to Remove\033[22m\n"
    termy_say -s "Please choose the numeric index of the key you wish to remove."

    PS3="Select an entry number (or type cancel): "
    select choice in "${keys[@]}"; do
        if [ -n "$choice" ]; then
            grep -v "^${choice}=" "$env_file" > "${env_file}.tmp" && mv "${env_file}.tmp" "$env_file"
            
            printf "\n🔥 \033[1mKey Purged\033[22m\nSuccessfully removed '%s' from the configuration.\n\n" "$choice"
            termy_say -s "Successfully removed $choice."
            break
        elif [ "$REPLY" = "cancel" ]; then
            printf "\n⚠️  \033[1mSelection Cancelled\033[22m\nNo adjustments were executed.\n\n"
            termy_say "Operation aborted."
            break
        else
            printf "\033[31mInvalid index. Please select a valid number from the menu.\033[0m\n"
        fi
    done
}

termy_execute() {
    local target_file="$1"

    if [[ -z "$target_file" ]]; then
        termy_say "⛔ Error: Target file path parameter is missing." >&2
        return 1
    fi

    if [[ ! -f "$target_file" ]]; then
        termy_say "⛔ Error: File does not exist or is invalid: '${target_file}'" >&2
        return 1
    fi

    local file_name
    file_name=$(basename -- "$target_file")
    
    local file_ext=""
    if [[ "$file_name" == *.* ]]; then
        file_ext="${file_name##*.}"
        file_ext="${file_ext,,}" # Force lowercase for safe matching
    fi

    case "$file_ext" in
        py)
            python3 "$target_file"
            ;;
        js)
            node "$target_file"
            ;;
        sh|bash)
            bash "$target_file"
            ;;
        rb)
            ruby "$target_file"
            ;;
        go)
            go run "$target_file"
            ;;
        "")
            # Extensionless assets require explicit executable privileges
            if [[ -x "$target_file" ]]; then
                "$target_file"
            else
                termy_say "⛔ Error: Extensionless file is not executable. Run 'chmod +x'" >&2
                return 1
            fi
            ;;
        *)
            termy_say "⛔ Error: Unsupported runtime extension (.${file_ext})." >&2
            return 1
            ;;
    esac

    local run_status=$?
    if [[ $run_status -eq 0 ]]; then
        termy_say "Execution completed."
        return 0
    else
        termy_say "⛔ Error: Runtime returned exit code ${run_status}." >&2
        return $run_status
    fi
}

# ================================================================
#  termy_shell_algorithm — config-driven algorithm compiler
#
#  Usage:  termy_shell_algorithm [algorithm] [language]
#    algorithm   optional (name or config keyword) — else menu
#    language    optional (bash/python/javascript/c/go/rust,
#                aliases: sh py js node rs) — else menu of what's
#                installed for that algorithm
#
#  Each config declares its own parameters; the function prompts for
#  them, validates by kind, and injects the answers into src/<algo>.<lang>
#  via {{PARAM}} / {{PARAM_LEN}} placeholders.
#
#  algorithm_templates/
#  ├── config/<algo>.conf   NAME, KEYWORDS, DESCRIPTION,
#  │                        PARAMS="a b", PARAM_a="prompt|default|kind"
#  └── src/<algo>.<lang>    template with {{…}} placeholders
#
#  Output: ./<algo>.<ext> in the current directory (dataset dir),
#  compiled to ./<algo> for c/go/rust when the toolchain is present.
# ================================================================
termy_shell_algorithm() {
    local TPL_ROOT="$HOME/.local/share/npc-forge/npcs/termy/dataset/algorithm_templates"

    # ---- terminal ui --------------------------------------------------
    local RST=$'\033[0m' CYA=$'\033[1;36m' GRN=$'\033[1;32m' YLW=$'\033[1;33m'
    local BLU=$'\033[1;34m' DIM=$'\033[2m'   RED=$'\033[1;31m'
    log_step() { printf '%s[•]%s %s\n' "$BLU" "$RST" "$1"; }
    log_ok()   { printf '%s[✓]%s %s\n' "$GRN" "$RST" "$1"; }
    log_warn() { printf '%s[!]%s %s\n' "$YLW" "$RST" "$1"; }
    log_err()  { printf '%s[✗]%s %s\n' "$RED" "$RST" "$1" >&2; }
    log_dim()  { printf '%s    ↳ %s%s\n' "$DIM" "$1" "$RST"; }

    # ask VARNAME "prompt" ["default"] — ↵ takes the default;
    # with no TTY the default is taken silently (unattended builds).
    ask() {
        local __var="$1" __prompt="$2" __default="${3-}" __val=""
        if [[ -t 0 ]]; then
            read -r -p "$(printf '%s[?]%s %s %s[↵ %s]%s: ' \
                "$CYA" "$RST" "$__prompt" "$DIM" "${__default:-skip}" "$RST")" __val
        fi
        printf -v "$__var" '%s' "${__val:-$__default}"
    }

    # sed_escape: protect \ & | so values survive sed substitution
    sed_escape() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }

    # _valid VALUE KIND — parameter validation
    _valid() {
        local t
        case "$2" in
            number) [[ "$1" =~ ^-?[0-9]+$ ]] ;;
            list)   [[ -n "$1" ]] || return 1
                    for t in $1; do [[ "$t" =~ ^-?[0-9]+$ ]] || return 1; done ;;
            *)      [[ -n "$1" ]] ;;
        esac
    }

    # _lang_meta LANG → sets L_EXT (file ext), L_RUN (interpreter),
    # L_BUILD (compiler prefix; empty when interpreted)
    _lang_meta() {
        case "$1" in
            bash)       L_EXT="sh"  L_RUN="bash"    L_BUILD="" ;;
            python)     L_EXT="py"  L_RUN="python3" L_BUILD="" ;;
            javascript) L_EXT="js"  L_RUN="node"    L_BUILD="" ;;
            c)          L_EXT="c"   L_RUN=""        L_BUILD="cc -O2 -o" ;;
            go)         L_EXT="go"  L_RUN=""        L_BUILD="go build -o" ;;
            rust)       L_EXT="rs"  L_RUN=""        L_BUILD="rustc -O -o" ;;
            *)          L_EXT="$1"  L_RUN=""        L_BUILD="" ;;
        esac
    }

    # _lang_available LANG — is the interpreter/compiler on PATH?
    _lang_available() {
        _lang_meta "$1"
        local tool=""
        [[ -n "$L_RUN" ]] && tool="${L_RUN%% *}"
        [[ -z "$tool" && -n "$L_BUILD" ]] && tool="${L_BUILD%% *}"
        [[ -z "$tool" ]] && return 0
        command -v "$tool" >/dev/null 2>&1
    }

    # _algo_langs ALGO → prints lang tokens whose toolchain exists
    # (skip notes go to stderr so command substitution stays clean)
    _algo_langs() {
        local f lang out=""
        for f in "$TPL_ROOT/src/$1".*; do
            [[ -f "$f" ]] || continue
            lang="${f##*.}"
            if _lang_available "$lang"; then out+="$lang "
            else printf '%s[!]%s %s: no %s toolchain — skipped\n' "$YLW" "$RST" "$1" "$lang" >&2; fi
        done
        printf '%s' "$out"
    }

    printf '\n%s╔══════════════════════════════════════════╗%s\n' "$CYA" "$RST"
    printf '%s║%s  TERMy ALGORITHM COMPILER · multi-lang   %s║%s\n' "$CYA" "$RST" "$CYA" "$RST"
    printf '%s╚══════════════════════════════════════════╝%s\n\n' "$CYA" "$RST"
    [[ -d "$TPL_ROOT/src" ]] || { log_err "No src/ in '$TPL_ROOT' — nothing to compile."; return 1; }
    (( $# > 2 )) && log_warn "Two parameters max — ignoring extras: '${*:3}'"

    # ---- 1 · discover algorithms (unique src basenames) -----------------
    local -a algos=()
    local f base
    for f in "$TPL_ROOT"/src/*.*; do
        [[ -f "$f" ]] || continue
        base=$(basename "$f"); base="${base%.*}"
        printf ' %s ' "${algos[*]:-}" | grep -q " $base " || algos+=("$base")
    done
    (( ${#algos[@]} > 0 )) || { log_err "No sources in '$TPL_ROOT/src/'."; return 1; }
    log_step "Discovered ${#algos[@]} algorithm(s) in ${DIM}$TPL_ROOT/src/${RST}"

    # ---- 2 · resolver: name → config keywords ----------------------------
    _resolve_algo() { # sets REPLY_ALGO / REPLY_NOTE · rc 1 = no match
        local q="$1" a w conf kw
        local -a kws=()
        REPLY_ALGO="" REPLY_NOTE=""
        [[ -z "$q" ]] && return 1
        for a in "${algos[@]}"; do
            if [[ "$q" == *"$a"* ]] || { (( ${#q} >= 3 )) && [[ "$a" == *"$q"* ]]; }; then
                REPLY_ALGO="$a"; REPLY_NOTE="name"; return 0
            fi
        done
        for conf in "$TPL_ROOT"/config/*.conf; do
            [[ -f "$conf" ]] || continue
            a=$(basename "$conf" .conf)
            printf ' %s ' "${algos[*]}" | grep -q " $a " || continue
            kw=$(sed -n -e 's/^KEYWORDS=//p' -- "$conf" | tr -d '"' | tr '[:upper:]' '[:lower:]')
            read -ra kws <<< "$kw"
            for w in "${kws[@]}"; do
                [[ -z "$w" ]] && continue
                if [[ "$q" == *"$w"* ]] || { (( ${#q} >= 3 )) && [[ "$w" == *"$q"* ]]; }; then
                    REPLY_ALGO="$a"; REPLY_NOTE="keyword '$w'"; return 0
                fi
            done
        done
        return 1
    }

    local default_algo="fibonacci"
    printf ' %s ' "${algos[*]}" | grep -q " $default_algo " || default_algo="${algos[0]}"

    # ---- 3 · algorithm: parameter first, otherwise ask -------------------
    local algo="" match_note="" input_algo="${1:-}" q
    if [[ -n "$input_algo" ]]; then
        q=$(printf '%s' "$input_algo" | tr '[:upper:]' '[:lower:]')
        if [[ "$q" =~ ^[0-9]+$ ]] && (( q >= 1 && q <= ${#algos[@]} )); then
            algo="${algos[$((q-1))]}"; match_note="index, from argument"
        elif _resolve_algo "$q"; then
            algo="$REPLY_ALGO"; match_note="$REPLY_NOTE, from argument"
        else
            log_warn "Unknown algorithm '$input_algo' — pick from the menu"
        fi
    fi

    if [[ -z "$algo" ]]; then
        local conf desc langs a i
        printf '\n'
        for i in "${!algos[@]}"; do
            a="${algos[$i]}"
            conf="$TPL_ROOT/config/$a.conf"
            desc=""
            [[ -f "$conf" ]] && desc=$(sed -n -e 's/^DESCRIPTION=//p' -- "$conf" | head -1 | sed 's/^"//; s/"$//')
            langs=$(_algo_langs "$a")
            printf '    %s%2d)%s %-16s %s[%s]%s %s%s%s\n' \
                "$YLW" "$((i+1))" "$RST" "$a" "$DIM" "${langs% }" "$RST" "$DIM" "${desc:0:42}" "$RST"
        done
        printf '\n'
        local choice=""
        if [[ -t 0 ]]; then
            read -r -p "$(printf '%s[?]%s Algorithm %s[1-%d · name · keyword · ↵ %s]%s: ' \
                "$CYA" "$RST" "$DIM" "${#algos[@]}" "$default_algo" "$RST")" choice
        else
            log_warn "No TTY on stdin — running unattended with defaults"
        fi
        choice="${choice#"${choice%%[![:space:]]*}"}"
        choice="${choice%"${choice##*[![:space:]]}"}"
        choice=$(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]')
        if [[ -z "$choice" ]]; then
            algo="$default_algo"; match_note="default"
        elif [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#algos[@]} )); then
            algo="${algos[$((choice-1))]}"; match_note="menu pick"
        elif _resolve_algo "$choice"; then
            algo="$REPLY_ALGO"; match_note="$REPLY_NOTE"
        else
            algo="$default_algo"; match_note="fallback"
            log_warn "Nothing matches '$choice' — using '$default_algo'"
        fi
    fi
    log_ok "Algorithm resolved: ${YLW}${algo}${RST} ${DIM}(${match_note})${RST}"

    # ---- 4 · language: parameter first, otherwise ask --------------------
    local lang_arg="${2:-}" lang="" l
    local -a avail=()
    read -ra avail <<< "$(_algo_langs "$algo")"
    (( ${#avail[@]} > 0 )) || { log_err "No usable toolchain for '$algo'."; return 1; }

    if [[ -n "$lang_arg" ]]; then
        lang_arg=$(printf '%s' "$lang_arg" | tr '[:upper:]' '[:lower:]')
        case "$lang_arg" in          # friendly aliases
            py) lang_arg="python" ;; js|node) lang_arg="javascript" ;;
            sh|shell) lang_arg="bash" ;; rs) lang_arg="rust" ;;
        esac
        for l in "${avail[@]}"; do [[ "$l" == "$lang_arg" ]] && { lang="$l"; break; }; done
        [[ -z "$lang" ]] && log_warn "Language '$lang_arg' unavailable for '$algo' — pick from the menu"
    fi

    if [[ -z "$lang" ]]; then
        printf '\n'
        for i in "${!avail[@]}"; do
            printf '    %s%2d)%s %s\n' "$YLW" "$((i+1))" "$RST" "${avail[$i]}"
        done
        local lchoice=""
        if [[ -t 0 ]]; then
            read -r -p "$(printf '%s[?]%s Language %s[1-%d · ↵ %s]%s: ' \
                "$CYA" "$RST" "$DIM" "${#avail[@]}" "${avail[0]}" "$RST")" lchoice
        fi
        lchoice=$(printf '%s' "$lchoice" | tr '[:upper:]' '[:lower:]')
        if [[ "$lchoice" =~ ^[0-9]+$ ]] && (( lchoice >= 1 && lchoice <= ${#avail[@]} )); then
            lang="${avail[$((lchoice-1))]}"
        else
            for l in "${avail[@]}"; do [[ "$l" == "$lchoice" ]] && { lang="$l"; break; }; done
        fi
        if [[ -z "$lang" ]]; then
            lang="${avail[0]}"
            [[ -n "$lchoice" ]] && log_warn "Unknown language '$lchoice' — using '$lang'"
        fi
    fi
    log_ok "Language: ${YLW}${lang}${RST}"

    # ---- 5 · parameters declared by the config ----------------------------
    local conf_file="$TPL_ROOT/config/$algo.conf"
    local algo_name="$algo" params_raw=""
    [[ -f "$conf_file" ]] && {
        algo_name=$(sed -n -e 's/^NAME=//p' -- "$conf_file" | head -1 | sed 's/^"//; s/"$//')
        params_raw=$(sed -n -e 's/^PARAMS=//p' -- "$conf_file" | head -1 | sed 's/^"//; s/"$//')
    }
    algo_name="${algo_name:-$algo}"

    local -a params=() p_vals=() p_kinds=()
    read -ra params <<< "$params_raw"
    if (( ${#params[@]} > 0 )); then
        printf '\n%s    parameters%s\n' "$DIM" "$RST"
        local p spec prompt default kind val
        for p in "${params[@]}"; do
            spec=""
            if [[ -f "$conf_file" ]]; then
                spec=$(sed -n -e "s/^PARAM_${p}=//p" -- "$conf_file" | head -1 | sed 's/^"//; s/"$//')
            fi
            IFS='|' read -r prompt default kind <<< "$spec"
            prompt="${prompt:-$p}"; default="${default:-}"; kind="${kind:-text}"
            while :; do
                ask val "$prompt" "$default"
                _valid "$val" "$kind" && break
                log_warn "Expected ${kind} — try again (e.g. ${default:-...})"
                if [[ ! -t 0 ]]; then val="$default"; break; fi   # never loop unattended
            done
            p_vals+=("$val"); p_kinds+=("$kind")
        done
    fi

    # ---- 6 · render src/<algo>.<lang> → ./<algo>.<ext> ---------------------
    _lang_meta "$lang"
    local src_file="$TPL_ROOT/src/$algo.$lang"
    local out_file="./${algo}.${L_EXT}"
    [[ -e "$out_file" ]] && log_warn "Overwriting existing $out_file"

    local s_name; s_name=$(sed_escape "$algo_name")
    local -a sed_args=(
        -e "s|{{NAME}}|$s_name|g"
        -e "s|{{ALGO}}|$algo|g"
        -e "s|{{LANG}}|$lang|g"
        -e "s|{{YEAR}}|$(date +%Y)|g"
    )
    local idx=0 PH val kind joined count tok
    for p in "${params[@]}"; do
        val="${p_vals[$idx]}"; kind="${p_kinds[$idx]}"; idx=$((idx+1))
        PH=$(printf '%s' "$p" | tr '[:lower:]' '[:upper:]')
        if [[ "$kind" == "list" ]]; then
            count=$(printf '%s' "$val" | wc -w | tr -d '[:space:]')
            if [[ "$lang" == "bash" ]]; then
                # per-element isolation: 1 2 3 → '1' '2' '3'
                joined=""
                for tok in $val; do joined+="$(sh_quote "$tok") "; done
                joined="${joined% }"
            else
                joined=$(printf '%s' "$val" | sed 's/  */ /g; s/ /, /g')
            fi
            sed_args+=(-e "s|{{$PH}}|$(sed_escape "$joined")|g" \
                       -e "s|{{$PH}_LEN}|$count|g")
        elif [[ "$lang" == "bash" ]]; then
            sed_args+=(-e "s|{{$PH}}|$(sed_escape "$(sh_quote "$val")")|g")
        else
            sed_args+=(-e "s|{{$PH}}|$(sed_escape "$val")|g")
        fi
    done

    log_step "Rendering $out_file ${DIM}← src/$algo.$lang${RST}"
    sed "${sed_args[@]}" -- "$src_file" > "$out_file"
    [[ "$lang" == "bash" ]] && chmod +x -- "$out_file"

    # ---- 7 · compile / run ---------------------------------------------------
    local do_build="" do_run="" lc
    if [[ -n "$L_BUILD" ]]; then
        local bin="./$algo"
        ask do_build "Compile with ${L_BUILD%% *}? (y/n)" "y"
        lc=$(printf '%s' "$do_build" | tr '[:upper:]' '[:lower:]')
        if [[ "$lc" == y* ]]; then
            if $L_BUILD "$bin" "$out_file" 2>/dev/null; then
                log_ok "Compiled → $bin"
                ask do_run "Run it now? (y/n)" "y"
                lc=$(printf '%s' "$do_run" | tr '[:upper:]' '[:lower:]')
                [[ "$lc" == y* ]] && { log_step "Output:"; "$bin"; }
            else
                log_warn "Compilation failed — source is in $out_file"
            fi
        fi
    else
        ask do_run "Run ${L_RUN} $out_file now? (y/n)" "y"
        lc=$(printf '%s' "$do_run" | tr '[:upper:]' '[:lower:]')
        [[ "$lc" == y* ]] && { log_step "Output:"; "$L_RUN" -- "$out_file"; }
    fi

    # ---- 8 · report + context + voice ------------------------------------------
    local summary="" j
    for j in "${!params[@]}"; do summary+="${params[$j]}=${p_vals[$j]} "; done
    printf '\n'
    log_ok "Algorithm ${YLW}${algo}${RST} (${lang}) → ${out_file}"
    [[ -n "$summary" ]] && log_dim "params: ${summary% }"

    if command -v termy_set_context >/dev/null 2>&1; then
        termy_set_context active_file "$out_file"
        termy_set_context active_algorithm "$algo"
        termy_set_context active_language "$lang"
    fi
    export TERMY_LAST_ALGO_FILE="$out_file"

    if command -v termy_say >/dev/null 2>&1; then
        termy_say "Implemented ${algo_name} in ${lang}." >/dev/null 2>&1 &
    fi
    return 0
}

# ================================================================
#  termy_generate_web_page — interactive, config-driven site compiler
#
#  Usage:  termy_generate_web_page [type]
#    type   optional website type (theme name or config keyword) —
#           resolved silently; missing or unknown → interactive menu.
#
#  Prompts (↵ accepts the shown default; no TTY → all defaults):
#    theme · project name · title · description · color scheme
#    (with palette previews) · address · email · socials ·
#    copyright · git init
#
#  Output: ./<project-slug>/index.html + styles.css + app.js
#
#  web_templates/
#  ├── config/<theme>.conf     KEYWORDS, FALLBACK_TITLE, FALLBACK_DESCRIPTION
#  ├── config/schemes.conf     scheme presets (name|bg|surface|ink|…)
#  ├── html/<theme>.html       {{TITLE}} {{DESCRIPTION}} {{COPYRIGHT}} {{ADDRESS}}
#  │                           {{EMAIL}} {{SOCIALS}} {{STYLES}} {{SCRIPTS}} {{YEAR}} {{THEME}}
#  ├── css/_base.css           reset · token contract · shared footer
#  ├── css/<theme>.css         optional · unified tokens --c-* / --f-*
#  ├── js/_core.js             shared interaction engine
#  └── js/<theme>.js           optional per-theme extras
# ================================================================
termy_generate_web_page() {
    local TPL_ROOT="$HOME/.local/share/npc-forge/npcs/termy/dataset/web_templates"

    # ---- terminal ui --------------------------------------------------
    local RST=$'\033[0m' CYA=$'\033[1;36m' GRN=$'\033[1;32m' YLW=$'\033[1;33m'
    local BLU=$'\033[1;34m' DIM=$'\033[2m'   RED=$'\033[1;31m'
    log_step() { printf '📄 %s\n' "$1"; }
    log_ok()   { printf '✅ %s\n' "$1"; }
    log_warn() { printf '💣 %s\n' "$1"; }
    log_err()  { printf '💥 %s\n' "$1" >&2; }
    log_dim()  { printf '%s  ↳ %s%s\n' "$DIM" "$1" "$RST"; }

    # ask VARNAME "prompt" ["default"] — ↵ takes the default;
    # with no TTY the default is taken silently (unattended builds).
    ask() {
        local __var="$1" __prompt="$2" __default="${3-}" __val=""
        if [[ -t 0 ]]; then
            read -r -p "$(printf '%s❔%s %s %s[↵ %s]%s: ' \
                "$CYA" "$RST" "$__prompt" "$DIM" "${__default:-skip}" "$RST")" __val
        fi
        printf -v "$__var" '%s' "${__val:-$__default}"
    }

    # html_escape: user text → safe inside markup.
    # sed_escape:  protect \ & | so text survives sed substitution.
    html_escape() { printf '%s' "$1" | sed -e 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g'; }
    sed_escape()  { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
    
    # sh_quote: single-quote isolation (TCSS Rule 1).
    # Wraps arbitrary input in '…' and escapes every embedded ' as '\''
    # so the kernel treats the whole value as a literal string.
    sh_quote() {
        local q=${1//\'/\'\\\'\'}
        printf "'%s'" "$q"
    }

    # color_to_rgb "any css color" → "R;G;B" (rc 1 if unparsable)
    color_to_rgb() {
        local c="$1" re_rgba='^rgba?\(([0-9]+)[, ]+([0-9]+)[, ]+([0-9]+)'
        if [[ "$c" =~ ^#([0-9a-fA-F]{6})$ ]]; then
            local h="${BASH_REMATCH[1]}"
            printf '%d;%d;%d' "$((16#${h:0:2}))" "$((16#${h:2:2}))" "$((16#${h:4:2}))"
        elif [[ "$c" =~ ^#([0-9a-fA-F]{3})$ ]]; then
            local h="${BASH_REMATCH[1]}"
            printf '%d;%d;%d' "$((16#${h:0:1}${h:0:1}))" "$((16#${h:1:1}${h:1:1}))" "$((16#${h:2:1}${h:2:1}))"
        elif [[ "$c" =~ $re_rgba ]]; then
            printf '%d;%d;%d' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
        else
            return 1
        fi
    }

    # swatch: a SQUARE color chip.
    # Heads-up: ██ is a glyph — it paints with the FOREGROUND color.
    # A background-only code hides behind it (that's the white-swatch bug),
    # so we set fg AND bg to the same rgb for a solid chip in every terminal.
    swatch() {
        local rgb
        if rgb=$(color_to_rgb "$1"); then
            printf '\033[38;2;%sm\033[48;2;%sm██\033[0m' "$rgb" "$rgb"
        else
            printf '%s▒▒%s' "$DIM" "$RST"
        fi
    }

    # color math for the custom scheme (plain 6-digit hex in/out)
    _mix()  { local a="$1" b="$2" p="$3"
        printf '%02x%02x%02x' \
            $(( (16#${a:0:2}*(100-p) + 16#${b:0:2}*p)/100 )) \
            $(( (16#${a:2:2}*(100-p) + 16#${b:2:2}*p)/100 )) \
            $(( (16#${a:4:2}*(100-p) + 16#${b:4:2}*p)/100 ))
    }
    _luma() { printf '%d' $(( (16#${1:0:2}*299 + 16#${1:2:2}*587 + 16#${1:4:2}*114) / 1000 )); }

    printf '%s╔═════════════════════════╗%s\n' "$GRN" "$RST"
    printf '%s║%s TERMy website generator %s║%s\n' "$GRN" "$RST" "$GRN" "$RST"
    printf '%s╚═════════════════════════╝%s\n\n' "$GRN" "$RST"
    (( $# > 1 )) && log_warn "Single parameter expected — ignoring extras: '${*:2}'"

    # ---- 1 · discover themes -------------------------------------------
    local -a themes=()
    local f
    for f in "$TPL_ROOT"/html/*.html; do
        [[ -f "$f" ]] && themes+=("$(basename "$f" .html)")
    done
    (( ${#themes[@]} > 0 )) || { log_err "No templates in '$TPL_ROOT/html/' — nothing to compile."; return 1; }
    log_step "Discovered ${#themes[@]} theme(s) in ${DIM}$TPL_ROOT/html/${RST}"

    # ---- 2 · resolver: theme name → config keywords ---------------------
    _termy_resolve_theme() { # sets REPLY_THEME / REPLY_NOTE · rc 1 = no match
        local q="$1" t w conf kw
        local -a kws=()
        REPLY_THEME="" REPLY_NOTE=""
        [[ -z "$q" ]] && return 1
        for t in "${themes[@]}"; do
            if [[ "$q" == *"$t"* ]] || { (( ${#q} >= 3 )) && [[ "$t" == *"$q"* ]]; }; then
                REPLY_THEME="$t"; REPLY_NOTE="name"; return 0
            fi
        done
        for conf in "$TPL_ROOT"/config/*.conf; do
            [[ -f "$conf" ]] || continue
            t=$(basename "$conf" .conf)
            printf ' %s ' "${themes[*]}" | grep -q " $t " || continue
            kw=$(sed -n -e 's/^KEYWORDS=//p' -- "$conf" | tr -d '"' | tr '[:upper:]' '[:lower:]')
            read -ra kws <<< "$kw"
            for w in "${kws[@]}"; do
                [[ -z "$w" ]] && continue
                if [[ "$q" == *"$w"* ]] || { (( ${#q} >= 3 )) && [[ "$w" == *"$q"* ]]; }; then
                    REPLY_THEME="$t"; REPLY_NOTE="keyword '$w'"; return 0
                fi
            done
        done
        return 1
    }

    local default_theme="" t i conf kw
    for t in landing index default; do
        printf ' %s ' "${themes[*]}" | grep -q " $t " && { default_theme="$t"; break; }
    done
    default_theme="${default_theme:-${themes[0]}}"

    # ---- 3 · theme: parameter first, otherwise ask -----------------------
    local theme="" match_note="" input_type="${1:-}" q
    if [[ -n "$input_type" ]]; then
        q=$(printf '%s' "$input_type" | tr '[:upper:]' '[:lower:]')
        if [[ "$q" =~ ^[0-9]+$ ]] && (( q >= 1 && q <= ${#themes[@]} )); then
            theme="${themes[$((q-1))]}"; match_note="index, from argument"
        elif _termy_resolve_theme "$q"; then
            theme="$REPLY_THEME"; match_note="$REPLY_NOTE, from argument"
        else
            log_warn "Unknown website type '$input_type' — pick from the menu"
        fi
    fi

    if [[ -z "$theme" ]]; then
        printf '\n'
        for i in "${!themes[@]}"; do
            t="${themes[$i]}"
            conf="$TPL_ROOT/config/$t.conf"
            kw=""
            [[ -f "$conf" ]] && kw=$(sed -n -e 's/^KEYWORDS=//p' -- "$conf" | tr -d '"')
            printf '    %s%2d)%s %-13s %s%s%s\n' \
                "$YLW" "$((i+1))" "$RST" "$t" "$DIM" "${kw:+· ${kw:0:54}}" "$RST"
        done
        printf '\n'
        local choice=""
        if [[ -t 0 ]]; then
            read -r -p "$(printf '%s❔%s Theme %s[1-%d · name · keyword · ↵ %s]%s: ' \
                "$CYA" "$RST" "$DIM" "${#themes[@]}" "$default_theme" "$RST")" choice
        else
            log_warn "No TTY on stdin — running unattended with defaults"
        fi
        choice="${choice#"${choice%%[![:space:]]*}"}"
        choice="${choice%"${choice##*[![:space:]]}"}"
        choice=$(printf '%s' "$choice" | tr '[:upper:]' '[:lower:]')
        if [[ -z "$choice" ]]; then
            theme="$default_theme"; match_note="default"
        elif [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#themes[@]} )); then
            theme="${themes[$((choice-1))]}"; match_note="menu pick"
        elif _termy_resolve_theme "$choice"; then
            theme="$REPLY_THEME"; match_note="$REPLY_NOTE"
        else
            theme="$default_theme"; match_note="fallback"
            log_warn "Nothing matches '$choice' — using '$default_theme'"
        fi
    fi
    log_ok "Theme resolved: ${YLW}${theme}${RST} ${DIM}(${match_note})${RST}"

    # ---- 4 · project name → its own directory ----------------------------
    local project="" slug proj_dir
    ask project "Project name" "$theme"
    slug=$(printf '%s' "$project" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')
    [[ -z "$slug" ]] && slug="termy-site"
    proj_dir="./$slug"
    if [[ -d "$proj_dir" ]]; then
        log_warn "Project '$slug' exists — rebuilding in place"
    else
        mkdir -p -- "$proj_dir" || { log_err "Cannot create '$proj_dir'"; return 1; }
    fi
    log_step "Building into ${YLW}$proj_dir/${RST}"

    local OUT_HTML="$proj_dir/index.html" OUT_CSS="$proj_dir/styles.css" OUT_JS="$proj_dir/app.js"

    # ---- 5 · title & description ------------------------------------------
    local conf_file="$TPL_ROOT/config/$theme.conf"
    local fallback_title="" fallback_desc=""
    [[ -f "$conf_file" ]] && {
        fallback_title=$(sed -n -e 's/^FALLBACK_TITLE=//p' -- "$conf_file" | head -1 | sed 's/^"//; s/"$//')
        fallback_desc=$(sed -n -e 's/^FALLBACK_DESCRIPTION=//p' -- "$conf_file" | head -1 | sed 's/^"//; s/"$//')
    }
    fallback_title="${fallback_title:-$project}"
    fallback_desc="${fallback_desc:-A website generated with the TERMy template engine.}"

    local page_title="" description=""
    ask page_title  "Page title"  "$fallback_title"
    ask description "Description" "$fallback_desc"
    log_ok "Title: \"${page_title}\""

    # ---- 6 · color scheme (menu with palette previews + custom) -----------
    local -a sc_names=() sc_defs=()
    local sc_conf="$TPL_ROOT/config/schemes.conf" name rest
    if [[ -f "$sc_conf" ]]; then
        while IFS='|' read -r name rest; do
            [[ -z "$name" || "$name" == \#* ]] && continue
            sc_names+=("$name"); sc_defs+=("$rest")
        done < "$sc_conf"
    fi

    local custom_idx=$(( ${#sc_names[@]} + 2 ))
    printf '\n     %spreview: bg · ink · accent · accent-2%s\n\n' "$DIM" "$RST"
    printf '     %s 1)%s theme default palette\n\n' "$YLW" "$RST"
    for i in "${!sc_names[@]}"; do
        local -a cols=()
        IFS='|' read -ra cols <<< "${sc_defs[$i]}"
        printf '     %s%2d)%s %-9s %s %s %s %s\n\n' "$YLW" "$((i+2))" "$RST" "${sc_names[$i]}" \
            "$(swatch "${cols[0]}")" "$(swatch "${cols[2]}")" "$(swatch "${cols[4]}")" "$(swatch "${cols[5]}")"
    done
    printf '     %s%2d)%s custom — pick your own colors\n\n' "$YLW" "$custom_idx" "$RST"

    local scheme_choice="1" scheme_name="theme default" scheme_block=""
    ask scheme_choice "Color scheme" "1"

    if [[ "$scheme_choice" =~ ^[0-9]+$ ]] && (( scheme_choice == 1 )); then
        # Theme default — no override needed, base css has the colors
        scheme_name="theme default"
        scheme_block=""
    elif [[ "$scheme_choice" =~ ^[0-9]+$ ]] && (( scheme_choice >= 2 && scheme_choice <= custom_idx - 1 )); then
        local idx=$(( scheme_choice - 2 )) b s ink m a a2 a3 l
        scheme_name="${sc_names[$idx]}"
        IFS='|' read -r b s ink m a a2 a3 l <<< "${sc_defs[$idx]}"
        scheme_block=$(printf '/* scheme: %s — injected by TERMy (overrides theme tokens) */\n:root {\n    --color-background: %s;\n    --color-surface: %s;\n    --color-text-primary: %s;\n    --color-text-secondary: %s;\n    --color-accent-primary: %s;\n    --color-accent-secondary: %s;\n    --color-accent-tertiary: %s;\n    --color-border: %s;\n}' \
            "$scheme_name" "$b" "$s" "$ink" "$m" "$a" "$a2" "$a3" "$l")
    elif [[ "$scheme_choice" =~ ^[0-9]+$ ]] && (( scheme_choice == custom_idx )); then
        # defaults = the theme's own tokens (1st/3rd/5th/6th hex in its css)
        local css_file="$TPL_ROOT/css/$theme.css"
        local -a th=()
        [[ -f "$css_file" ]] && th=($(grep -oE '#[0-9a-fA-F]{6}' -- "$css_file" | head -6))
        local d_bg="${th[0]:-#0d2137}" d_ink="${th[2]:-#e9f2f8}" d_acc="${th[4]:-#ff6a2b}" d_acc2="${th[5]:-#53c8ff}"
        printf '\n%s    custom scheme — 6-digit hex, ↵ keeps the theme value%s\n' "$DIM" "$RST"
        local c_bg c_ink c_acc c_acc2
        ask c_bg   "Background" "${d_bg#\#}"
        ask c_ink  "Text"       "${d_ink#\#}"
        ask c_acc  "Accent"     "${d_acc#\#}"
        ask c_acc2 "Accent 2"   "${d_acc2#\#}"
        local ok_re='^[0-9a-fA-F]{6}$'
        [[ "$c_bg"   =~ $ok_re ]] || c_bg="${d_bg#\#}"
        [[ "$c_ink"  =~ $ok_re ]] || c_ink="${d_ink#\#}"
        [[ "$c_acc"  =~ $ok_re ]] || c_acc="${d_acc#\#}"
        [[ "$c_acc2" =~ $ok_re ]] || c_acc2="${d_acc2#\#}"
        # derive secondary tokens so the page stays coherent
        local c_surface c_muted c_line
        if (( $(_luma "$c_bg") > 140 )); then c_surface=$(_mix "$c_bg" "ffffff" 70)
        else                                   c_surface=$(_mix "$c_bg" "ffffff" 7); fi
        c_muted=$(_mix "$c_ink" "$c_bg" 45)
        c_line="${c_ink}26"                    # 8-digit hex: ink at ~15% alpha
        scheme_name="custom"
        scheme_block=$(printf '/* scheme: custom — injected by TERMy (overrides theme tokens) */\n:root {\n    --color-background: #%s;\n    --color-surface: #%s;\n    --color-text-primary: #%s;\n    --color-text-secondary: #%s;\n    --color-accent-primary: #%s;\n    --color-accent-secondary: #%s;\n    --color-border: #%s;\n}' \
            "$c_bg" "$c_surface" "$c_ink" "$c_muted" "$c_acc" "$c_acc2" "$c_line")
    else
        # Invalid choice — fallback to theme default
        log_warn "Invalid scheme choice '$scheme_choice' — using theme default"
        scheme_name="theme default"
        scheme_block=""
    fi
    log_ok "Scheme: ${YLW}${scheme_name}${RST}"

    # ---- 7 · footer: address / email / socials / copyright ----------------
    printf '\n%s❔ footer & contact%s (all optional)\n' "$DIM" "$RST"
    local address="" email="" socials_raw="" copyright=""
    ask address     "Address" ""
    ask email       "Email" ""
    ask socials_raw "Socials (comma-separated URLs)" ""
    ask copyright   "Copyright" "© $(date +%Y) ${page_title}"

    local email_html=""
    [[ -n "$email" ]] && email_html="<a href=\"mailto:$(html_escape "$email")\">$(html_escape "$email")</a>"

    local socials_html="" s label
    if [[ -n "$socials_raw" ]]; then
        local -a slist=()
        IFS=',' read -ra slist <<< "$socials_raw"
        for s in "${slist[@]}"; do
            s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"
            [[ -z "$s" ]] && continue
            [[ "$s" != *://* ]] && s="https://$s"
            label=$(printf '%s' "$s" | sed -E 's#^[a-z]+://##; s#^www\.##; s#/.*$##')
            case "$label" in
                github.com)        label="GitHub" ;;
                x.com|twitter.com) label="X" ;;
                linkedin.com)      label="LinkedIn" ;;
                instagram.com)     label="Instagram" ;;
                youtube.com)       label="YouTube" ;;
                *) label="$(printf '%s' "${label%%.*}" | sed 's/^\(.\)/\U\1/')" ;;
            esac
            socials_html+="<a href=\"$(html_escape "$s")\" target=\"_blank\" rel=\"noopener\">$(html_escape "$label") ↗</a>"
        done
    fi

    local s_title s_desc s_addr s_copy s_email s_socials
    s_title=$(sed_escape "$(html_escape "$page_title")")
    s_desc=$(sed_escape "$(html_escape "$description")")
    s_addr=$(sed_escape "$(html_escape "$address")")
    s_copy=$(sed_escape "$(html_escape "$copyright")")
    s_email=$(sed_escape "$email_html")
    s_socials=$(sed_escape "$socials_html")

    # ---- 8 · assemble css (optional) ---------------------------------------
    local tpl="$TPL_ROOT/html/$theme.html"
    local base_css="$TPL_ROOT/css/_base.css" css="$TPL_ROOT/css/$theme.css"
    local core_js="$TPL_ROOT/js/_core.js"   js="$TPL_ROOT/js/$theme.js"
    local styles_tag="" scripts_tag=""
    local -a parts=()
    local t0; t0=$(date +%s%N 2>/dev/null)

    if [[ -f "$css" ]]; then
        [[ -f "$base_css" ]] && parts+=("$base_css")
        parts+=("$css")
        cat -- "${parts[@]}" > "$OUT_CSS"
        # scheme overrides go LAST — later :root wins the cascade
        [[ -n "$scheme_block" ]] && printf '\n\n%s\n' "$scheme_block" >> "$OUT_CSS"
        styles_tag="<link rel=\"stylesheet\" href=\"${OUT_CSS##*/}\">"
    else
        log_warn "No css/$theme.css — emitting unstyled markup"
    fi

    # ---- 9 · assemble js (optional) ------------------------------------------
    parts=()
    [[ -f "$core_js" ]] && parts+=("$core_js")
    [[ -f "$js"      ]] && parts+=("$js")
    if (( ${#parts[@]} > 0 )); then
        cat -- "${parts[@]}" > "$OUT_JS"
        scripts_tag="<script src=\"${OUT_JS##*/}\" defer></script>"
    else
        log_warn "No js for '$theme' — static page, no interactions"
    fi

    # ---- 10 · render html (placeholder injection) -------------------------------
    log_step "Rendering $OUT_HTML ${DIM}← html/$theme.html${RST}"
    sed -e "s|{{TITLE}}|$s_title|g" \
        -e "s|{{DESCRIPTION}}|$s_desc|g" \
        -e "s|{{COPYRIGHT}}|$s_copy|g" \
        -e "s|{{ADDRESS}}|$s_addr|g" \
        -e "s|{{EMAIL}}|$s_email|g" \
        -e "s|{{SOCIALS}}|$s_socials|g" \
        -e "s|{{STYLES}}|$styles_tag|g" \
        -e "s|{{SCRIPTS}}|$scripts_tag|g" \
        -e "s|{{YEAR}}|$(date +%Y)|g" \
        -e "s|{{THEME}}|$theme|g" \
        -- "$tpl" > "$OUT_HTML"

    # ---- 11 · report -------------------------------------------------------------
    local elapsed="n/a" t1
    [[ "$t0" =~ ^[0-9]+$ ]] && { t1=$(date +%s%N); elapsed="$(( (t1 - t0) / 1000000 )) ms"; }

    local swatches="" hex
    for hex in $( { [[ -n "$scheme_block" ]] && grep -oE '#[0-9a-fA-F]{6}' -- <<< "$scheme_block" || grep -oE '#[0-9a-fA-F]{6}' -- "$OUT_CSS"; } | head -3 ); do
        swatches+=" $(swatch "$hex")"
    done

    printf '\n'
    log_ok "Compiled ${YLW}${theme}${RST} in ${CYA}${elapsed}${RST} · scheme: ${scheme_name} · title: \"${page_title}\""
    printf '\n'
    [[ -n "$swatches" ]] && log_dim "palette:${swatches}"
    log_dim "$OUT_HTML · $(du -h -- "$OUT_HTML" | cut -f1)"
    [[ -f "$OUT_CSS" ]] && log_dim "$OUT_CSS · $(du -h -- "$OUT_CSS" | cut -f1)"
    [[ -f "$OUT_JS"  ]] && log_dim "$OUT_JS · $(du -h -- "$OUT_JS" | cut -f1)"
    printf '\n'
    log_ok "Preview: ${YLW}python3 -m http.server${RST} ${DIM}→ http://localhost:8000/$slug/${RST}"

    # ---- 12 · optional git init ----------------------------------------------------
    local git_choice="n"
    if command -v git >/dev/null 2>&1; then
        if [[ -d "$proj_dir/.git" ]]; then
            log_dim "git repo already present in $proj_dir/ — commit when ready"
        else
            printf '\n'
            ask git_choice "Init a git repo in $proj_dir/? (y/n)" "n"
            case "$(printf '%s' "$git_choice" | tr '[:upper:]' '[:lower:]')" in
                y*)
                    if git -C "$proj_dir" init -q && git -C "$proj_dir" add -A && \
                       git -C "$proj_dir" -c user.name="TERMy" -c user.email="termy@termy.local" \
                           commit -qm "termy: initial $theme build"; then
                        log_ok "Git repo initialized — first commit created"
                    else
                        log_warn "git init failed — skipping"
                    fi ;;
            esac
        fi
    fi
    printf '\n'

    # ---- 13 · persist context & voice ------------------------------------------------
    # Resolve absolute paths for context persistence
    local abs_html abs_css abs_js
    abs_html=$(cd "$(dirname "$OUT_HTML")" 2>/dev/null && pwd)/$(basename "$OUT_HTML")
    abs_css=$(cd "$(dirname "$OUT_CSS")" 2>/dev/null && pwd)/$(basename "$OUT_CSS")
    abs_js=$(cd "$(dirname "$OUT_JS")" 2>/dev/null && pwd)/$(basename "$OUT_JS")
    
    if command -v termy_set_context >/dev/null 2>&1; then
        termy_set_context active_project "$slug"
        termy_set_context active_file "$abs_html"
        termy_set_context active_css "$abs_css"
        termy_set_context active_js "$abs_js"
        termy_set_context active_theme "$theme"
        termy_set_context active_title "$page_title"
        termy_set_context active_scheme "$scheme_name"
    fi
    if command -v termy_say >/dev/null 2>&1; then
        termy_say "Compiled the $theme project." >/dev/null 2>&1 &
    fi
    return 0
}