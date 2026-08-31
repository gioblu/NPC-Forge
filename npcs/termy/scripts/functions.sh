

# Fetch a random inspirational quote and announce it via text and voice
get_quote() {
    # 1. Fetch the raw quote JSON payload from the API
    local response
    response=$(curl -s "https://zenquotes.io/api/random")

    if [ -z "$response" ] || [ "$response" = "null" ]; then
        termy_say "⛔ Error: Unable to reach the quote service provider."
        return 1
    fi

    # Extract text for the speech synthesis engine
    local quote_text
    local author_name
    quote_text=$(echo "$response" | jq -r '.[0].q')
    author_name=$(echo "$response" | jq -r '.[0].a')

    # Output the textual version to screen
    echo "$response" | jq -r '.[0] | "🎓 \"\(.q)\" - \u001b[4m\(.a)\u001b[24m"'

    # TTS speech
    termy_say "Here is the quote you required. $quote_text. By $author_name." >/dev/null
}

# Fetch the top headlines and announce them via text and voice
get_news() {
    # Fetch world news headlines from GitHub
    local response
    response=$(curl -s "https://github.io")

    if [ -z "$response" ] || [ "$response" = "null" ] || ! echo "$response" | jq -e . >/dev/null 2>&1; then
        termy_say "⛔ Error: Unable to parse news data. Network feed is currently unavailable."
        return 1
    fi

    # Extract and format the top 3 articles for the terminal display
    echo -e "\n📰  \u001b[1mTODAY'S TOP HEADLINES:\u001b[0m\n"
    echo "$response" | jq -r '.articles[:3][] | "\u001b[1m\(.title)\u001b[0m\nURL: \(.url)\n"'

    # Extract separate strings for the text-to-speech engine
    local headline_1
    local headline_2
    local headline_3
    headline_1=$(echo "$response" | jq -r '.articles[0].title // "No headline available"')
    headline_2=$(echo "$response" | jq -r '.articles[1].title // "No headline available"')
    headline_3=$(echo "$response" | jq -r '.articles[2].title // "No headline available"')

    # Speak the headlines continuously with clean natural pauses
    termy_say -s "Here are the top three news headlines for today."
    sleep 0.5
    termy_say -s "First. $headline_1"
    sleep 0.5
    termy_say -s "Second. $headline_2"
    sleep 0.5
    termy_say -s "Third. $headline_3"
}

# Fetch random joke and announce it via text and voice
get_joke() {
    # Fetch the joke JSON payload from the API
    # Using the native single-object endpoint '/random_joke' 
    # and forcing curl to handle potential cloud redirects (-L)
    local response
    response=$(curl -sL "https://official-joke-api.appspot.com/random_joke")

    if [ -z "$response" ] || [ "$response" = "null" ] || ! echo "$response" | jq empty 2>/dev/null; then
        termy_say "⛔ Error: Unable to reach the joke service provider or invalid data received."
        return 1
    fi

    local joke_setup
    local joke_punchline
    joke_setup=$(echo "$response" | jq -r '.setup')
    joke_punchline=$(echo "$response" | jq -r '.punchline')
    echo "$response" | jq -r '"\"\(.setup)\" - \u001b[4m\(.punchline)\u001b[24m"'
    termy_say -s "Here is the joke you required. $joke_setup... $joke_punchline"
}

# Detect available system text editors and open the target file using the selected program
open_file_with_editor() {
    local target_file="$1"

    if [ -z "$target_file" ]; then
        if command -v termy_get_context >/dev/null 2>&1; then
            target_file=$(termy_get_context 'active_file' 2>/dev/null)
        fi
        
        if [ -z "$target_file" ]; then
            termy_say -s -- "Please enter the path or name of the file you want to open."
            printf "📝 \033[1mSystem File Opener\033[22m\n\n"
            read -r -p "Enter filename/path: " target_file </dev/tty
            target_file=$(echo "$target_file" | xargs)
        fi
    fi

    if [ -z "$target_file" ]; then
        termy_say -s -- "Filename cannot be empty. Operation aborted."
        return 1
    fi

    # Strip paths using basename to lock the execution scope to the current folder.
    # Strip wildcards (*, ?) to prevent unintended shell globbing expansions.
    target_file=$(basename "$target_file" | tr -d '*?')
    
    if [ ! -f "$target_file" ]; then
        termy_say -s -- "The requested file does not exist. Do you want to create a new one?"
        local create_confirm
        read -r -p "File '$target_file' does not exist. Create it? (y/N): " create_confirm </dev/tty
        create_confirm=$(echo "$create_confirm" | tr '[:upper:]' '[:lower:]' | xargs)
        
        if [[ "$create_confirm" == "y" || "$create_confirm" == "yes" ]]; then
            touch -- "$target_file" || {
                termy_say -s -- "Error. Unable to create the file due to permission constraints."
                return 1
            }
        else
            printf "⚠️  \033[1mOperation Aborted\033[22m\nFile access cancelled.\n\n"
            termy_say -s -- "Opening cancelled."
            return 0
        fi
    fi

    local editor_matrix=(
        "Micro Text Editor|micro"
        "GNU Nano|nano"
        "Vim|vim"
        "Vi|vi"
        "Visual Studio Code|code"
        "VSCodium|codium"
        "Sublime Text|subl"
        "Atom Editor|atom"
        "Gedit (GNOME)|gedit"
        "Kate (KDE)|kate"
    )

    local available_names=()
    local available_cmds=()

    for item in "${editor_matrix[@]}"; do
        local name="${item%%|*}"
        local cmd="${item#*|}"
        if command -v "$cmd" >/dev/null 2>&1; then
            available_names+=("$name")
            available_cmds+=("$cmd")
        fi
    done

    if [ ${#available_names[@]} -eq 0 ]; then
        printf "⚠️  \033[1mNo Matrix Editors Detected\033[22m\nFalling back to system standard EDITOR variable.\n\n"
        
        local fallback_editor
        fallback_editor=$(echo "${EDITOR:-nano}" | awk '{print $1}')
        
        if ! command -v "$fallback_editor" >/dev/null 2>&1; then
            fallback_editor="nano"
        fi

        termy_say -s -- "Launching your system default editor."
        "$fallback_editor" -- "$target_file"
        return $?
    fi

    printf "\n\033[1mSelect Text Editor\033[22m\n\n"
    termy_say -s -- "Please select the numeric index of the editor you wish to use."
    PS3="Choose an editor number (or type cancel): "
    select choice in "${available_names[@]}"; do
        if [ -n "$choice" ]; then
            for i in "${!available_names[@]}"; do
                if [ "${available_names[$i]}" = "$choice" ]; then
                    local selected_cmd="${available_cmds[$i]}"
                    
                    printf "\n\033[1mLaunching %s\033[22m...\n\n" "$choice"
                    termy_say -s -- "Opening file with $choice."
                    
                    # Protected execution using double dash boundary marker
                    "$selected_cmd" -- "$target_file"
                    break 2
                fi
            done
        elif [ "$REPLY" = "cancel" ]; then
            printf "\n⚠️  \033[1mSelection Cancelled\033[22m\nNo file adjustments were executed.\n\n"
            termy_say -s -- "Operation aborted."
            break
        else
            printf "\033[31mInvalid index. Please select a valid number from the menu.\033[0m\n"
        fi
    done

    return 0
}


