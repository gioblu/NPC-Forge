
open_browser() {
    # Isolate arbitrary user input inside a local variable
    local target_url
    target_url=$(printf '%s' "${1:-}" | xargs)

    # Interactive Input: fallback if no argument was passed directly
    if [ -z "$target_url" ]; then
        if command -v termy_say >/dev/null 2>&1; then
            termy_say "Please enter or paste the complete website URL or local file path you want to open." >/dev/null 2>&1 &
        fi
        printf "🌐 \033[1mLinux Web Browser Dispatcher\033[22m\n"
        read -r -p "Enter URL or Filepath (e.g., ./index.html): " target_url </dev/tty
        target_url=$(printf '%s' "$target_url" | xargs)
    fi

    # Exit if input is empty
    if [ -z "$target_url" ]; then
        printf >&2 "⛔ \033[1mError:\033[22m No target link or filepath provided.\n"
        return 1
    fi

    # Handle local paths and convert them to absolute file:// URLs
    if [ -f "$target_url" ] || [ -d "$target_url" ]; then
        # Resolve the absolute system path (e.g., convert ./index.html to /home/user/.../index.html)
        local abs_path
        abs_path=$(readlink -f -- "$target_url")
        # Format as a standard URL
        target_url="file://${abs_path}"
        printf "📄 \033[1mURL:\033[22m %s\n\n" "$target_url"
    else
        # If it is a remote link and lacks explicit web protocols, prepend https://
        if [[ ! "$target_url" =~ ^https?:// ]] && [[ ! "$target_url" =~ ^file:// ]]; then
            target_url="https://${target_url}"
        fi
    fi

    # Initialization (TCSS Rule 2: Strictly Parameterized printf)
    printf "⚓ \033[1mLaunching Default Linux Browser\033[22m\n"
    
    if command -v termy_say >/dev/null 2>&1; then
        local clean_speak
        clean_speak=$(printf "Opening your default browser to access %s" "$(basename -- "$target_url")" | sed "s/'//g")
        termy_say "$clean_speak" >/dev/null 2>&1 &
    fi

    # Subshell Execution Dispatch (TCSS Rule 3: Double-Dash '--')
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$target_url" >/dev/null 2>&1 &
    elif command -v open >/dev/null 2>&1; then
        open -- "$target_url" >/dev/null 2>&1 &
    else
        printf >&2 "⛔ \033[1mEnvironment Failure\033[22m\nNo suitable browser launcher utility found (xdg-open/open missing).\n\n"
        if command -v termy_say >/dev/null 2>&1; then
            termy_say "Error. Could not find desktop open utilities on this machine." >/dev/null 2>&1 &
        fi
        return 1
    fi
    return 0
}
