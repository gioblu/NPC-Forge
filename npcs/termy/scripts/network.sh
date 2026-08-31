#!/bin/bash

# Check internet connectivity status

check_internet_status() {
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        termy_say "🌐 Yes, you are connected to the internet."
    else
        termy_say "⛔ No, you are currently offline."
    fi
}

# Retrieve public IP address

get_public_ip() {
    termy_say -s "Detecting your current public IP address."

    local current_ip
    current_ip=$(curl -s "https://ifconfig.me" | xargs)

    if [ -z "$current_ip" ]; then
        termy_say "⛔ Error: Unable to resolve your public IP address from the network."
        return 1
    fi

    if termy_set_context "public_ip" "$current_ip"; then
        printf "🌐 \033[1mNetwork Status Verified\033[22m\n"
        printf "Public IP Address : %s\n\n" "$current_ip"
        termy_say -s "Network configuration updated. Your public IP is $current_ip."
    else
        termy_say "⛔ Error: Failed to record network entries inside the configuration file."
        return 1
    fi
}

# Check if a local port is open or free

check_local_port() {
    local target_port="$1"

    if [ -z "$target_port" ]; then
        termy_say -s "Please enter the port number you want to verify."
        printf "🔌 \033[1mPort Availability Checker\033[22m\n"
        read -r -p "Enter Port Number (e.g., 8080): " target_port </dev/tty
        target_port=$(echo "$target_port" | xargs)
    fi

    if [[ ! "$target_port" =~ ^[0-9]+$ ]] || [ "$target_port" -lt 1 ] || [ "$target_port" -gt 65535 ]; then
        printf "⛔ \033[1mInvalid Port\033[22m\nPort must be a valid integer between 1 and 65535.\n\n"
        termy_say "Error. Invalid port number specified."
        return 1
    fi

    termy_say -s "Scanning system network sockets for port $target_port."

    local socket_info
    socket_info=$(ss -lntup | grep -E ":${target_port}\s" | head -n 1)

    local is_free="true"
    local process_name="none"

    if [ -n "$socket_info" ]; then
        is_free="false"
        process_name=$(echo "$socket_info" | grep -oE 'users:\(\("[^"]+"' | cut -d'"' -f2)
        if [ -z "$process_name" ]; then
            process_name="unknown process"
        fi
    fi

    if termy_set_context "last_checked_port" "$target_port" \
                          "last_checked_port_free" "$is_free" \
                          "last_checked_port_proc" "$process_name"; then
        
        printf "🔍 \033[1mPort Scan Results\033[22m\n"
        printf "Port Number  : %s\n" "$target_port"
        
        if [ "$is_free" = "true" ]; then
            printf "Status       : \033[32mFREE (Available)\033[0m\n\n"
            termy_say -s "Port $target_port is free and ready for allocation."
        else
            printf "Status       : \033[31mOCCUPIED (In Use)\033[0m\n"
            printf "Process Name : %s\n\n" "$process_name"
            termy_say -s "Port $target_port is currently occupied by $process_name."
        fi
    else
        termy_say "Error: Failed to record network port telemetry inside the configuration file."
        return 1
    fi

    return 0
}

termy_request() {
    local base_url="$1"
    local query_string="$2"
    local jq_filter="$3"
    local clean_term
    clean_term=$(printf '%s' "$query_string" | jq -sRr @uri)
    local final_url
    final_url=$(printf '%s/%s' "$base_url" "$clean_term")
    local res
    res=$(curl -s -- "$final_url" | jq -r "$jq_filter" 2>/dev/null)
    res=${res:-Definition not found.}
    printf '%s' "$res"
}