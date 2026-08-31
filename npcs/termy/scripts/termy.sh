#!/bin/bash

# TERMy core functions
# Those are extracted and built as separate binaries.
# They are globally available on the system

# Copyright Giovanni Blu Mitolo 2026

TERMY_CONFIG_JSON="$HOME/.local/share/termy/config.json"

# This sets tts on and should force TERMy to use 
# the configured TTS (Text To Speech)

termy_voice_on() {
    termy_set_context "tts" "on"
    termy_say "Voice mode enabled."
}

# This sets tts off and should force TERMy to use 
# the configured TTS (Text To Speech)

termy_voice_off() {
    termy_set_context "tts" "off"
    echo "Voice mode disabled."
}

# This function is used by TERMy to synthetize speech

termy_say() {
    local silent=false

    if [ "$1" = "--silent" ] || [ "$1" = "-s" ]; then
        silent=true
        shift
    fi
    
    local raw_text="$1"
    local text="${raw_text//[\"\']}"

    # Try this instead of sed with hex escapes (more portable)
    text=$(printf '%s' "$text" | tr '\n' ' ' | grep -o '[[:print:]]*')
    
    text="${text//  / }"

    local current_mode=$(termy_get_context "tts")

    if [ "$current_mode" = "on" ] && command -v espeak-ng >/dev/null 2>&1; then
        pkill espeak-ng >/dev/null 2>&1
        espeak-ng "$text" >/dev/null 2>&1 &
    fi

    if [ "$silent" = false ]; then
        echo "$text"
    fi
}

# Prints config file

termy_print_config() {
    local config_file="$TERMY_CONFIG_JSON"

    termy_say -s "Reading configuration file."

    if [ ! -f "$config_file" ] || [ ! -s "$config_file" ]; then
        printf "⛔ \033[1mConfiguration Error\033[22m\nNo active profile found or the configuration file is empty.\n\n"
        termy_say "Error. Configuration file is missing or empty."
        return 1
    fi

    if ! jq empty "$config_file" 2>/dev/null; then
        printf "⛔ \033[1mParse Failure\033[22m\nThe configuration file contains invalid JSON data.\n\n"
        termy_say "Error. Critical syntax error detected inside your configuration file."
        return 1
    fi

    printf "⚙️  \033[1mTERMy configuration file\033[22m\n"
    printf "File Location: %s\n" "$config_file"
    printf "\n"

    jq . "$config_file"

    printf "\n\n"
    
    termy_say -s "Configuration file displayed successfully."
    return 0
}

termy_get_context() {
    local key="${1:-}"
    local config_file="$TERMY_CONFIG_JSON"

    if [ -z "$key" ] || [ ! -f "$config_file" ]; then
        return 1
    fi

    local value
    value=$(jq -r ".${key} // empty" "$config_file" 2>/dev/null)

    if [ -n "$value" ] && [ "$value" != "null" ]; then
        echo -n "$value"
        return 0
    else
        return 1
    fi
}

termy_set_context() {
    local key="${1:-}"
    local value="${2:-}"
    local config_file="$TERMY_CONFIG_JSON"
    local tmp_file="${config_file}.tmp"

    if [ -z "$key" ] || [ -z "$value" ]; then
        echo "⛔ Error: termy_set_context requires both a key and a value." >&2
        return 1
    fi

    if [ ! -f "$config_file" ]; then
        echo "{}" > "$config_file"
    fi

    if jq --arg k "$key" --arg v "$value" '.[$k] = $v' "$config_file" > "$tmp_file" 2>/dev/null; then
        mv "$tmp_file" "$config_file"
        return 0
    else
        echo "⛔ Error: Failed to update local context JSON configuration." >&2
        rm -f "$tmp_file"
        return 1
    fi
}
