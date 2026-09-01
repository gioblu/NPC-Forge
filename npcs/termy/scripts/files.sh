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
