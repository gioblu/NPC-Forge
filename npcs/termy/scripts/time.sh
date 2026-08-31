#!/bin/bash

# Retrieve the current timezone, save it to config, and announce it
get_timezone() {
    termy_say -s "Detecting your current system timezone configuration."

    local tz_name
    local tz_offset
    tz_name=$(date +%Z)
    tz_offset=$(date +%z | sed -E 's/([+-][0-9]{2})([0-9]{2})/UTC\1:\2/')

    if [ -z "$tz_name" ] || [ -z "$tz_offset" ]; then
        termy_say "⛔ Error: Unable to resolve the system timezone."
        return 1
    fi

    if termy_set_context "timezone_name" "$tz_name" "timezone_offset" "$tz_offset"; then    
        printf "🕒 \033[1mTimezone Verified\033[22m\n"
        printf "Timezone Name   : %s\n" "$tz_name"
        printf "Timezone Offset : %s\n\n" "$tz_offset"
        termy_say -s "Timezone configured to $tz_name with offset $tz_offset."
    else
        termy_say "⛔ Error: Failed to record timezone entries inside the configuration file."
        return 1
    fi
}
