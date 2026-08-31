#!/bin/bash

# Prompt for city, resolve geolocation coordinates, and save both into the config JSON

get_city() {
    local config_file="$HOME/.termy_config.json"
    termy_say -s "Where are you located? Please tell me your city name:"
    local user_city
    read -r -p "Where are you located? Please tell me your city name: " user_city
    user_city=$(echo "$user_city" | xargs)
    
    if [ -z "$user_city" ]; then
        termy_say "Location cannot be empty. Setup aborted."
        return 1
    fi

    local encoded_city
    encoded_city=$(echo -n "$user_city" | jq -sRj @uri)

    local geo_response
    geo_response=$(curl -s "https://geocoding-api.open-meteo.com/v1/search?name=${encoded_city}&count=1&language=en&format=json")
    
    local lat
    local lng
    lat=$(echo "$geo_response" | jq -r '.results[0].latitude')
    lng=$(echo "$geo_response" | jq -r '.results[0].longitude')

    if [ "$lat" = "null" ] || [ "$lng" = "null" ] || [ -z "$lat" ]; then
        termy_say "⛔ Error: Could not resolve coordinates for '$user_city'. Please check the spelling."
        return 1
    fi

    if termy_set_context "city" "$user_city" && \
       termy_set_context "latitude" "$lat" && \
       termy_set_context "longitude" "$lng"; then
        
        termy_say "Location configured! City set to $user_city (Latitude: $lat, Longitude: $lng)."
    else
        termy_say "⛔ Error: Failed to record geographic entries inside the configuration file."
        return 1
    fi
}

# Retrieve the current country based on public IP, save it to config, and announce it
get_country() {
    local config_file="$HOME/.termy_config.json"

    termy_say -s "Detecting your current country location based on your public IP address."

    local country_code
    country_code=$(curl -s "https://ipinfo.io/country" | xargs)

    if [ -z "$country_code" ] || [ "${#country_code}" -ne 2 ]; then
        termy_say "⛔ Error: Unable to resolve your location from the public IP address."
        return 1
    fi

    local country_name
    case "$country_code" in
        "US") country_name="United States" ;;
        "IT") country_name="Italy" ;;
        "GB") country_name="United Kingdom" ;;
        "DE") country_name="Germany" ;;
        "FR") country_name="France" ;;
        "ES") country_name="Spain" ;;
        "CA") country_name="Canada" ;;
        "AU") country_name="Australia" ;;
        *) country_name="$country_code" ;; # Fallback to code if name mapping is omitted
    esac

    if termy_set_context "country_code" "$country_code" && \
       termy_set_context "country_name" "$country_name"; then
        
        printf "🌍 \033[1mLocation Verified\033[22m\n"
        printf "Country Name : %s\n" "$country_name"
        printf "Country Code : %s\n\n" "$country_code"

        termy_say -s "Location configured. Country detected as $country_name."
    else
        termy_say "⛔ Error: Failed to record geographic country entries inside the configuration file."
        return 1
    fi
}


# Resolve geographic location details using a target postal zip code
lookup_zip_code() {
    local config_file="$HOME/.termy_config.json"
    local target_zip="$1"

    if [ -z "$target_zip" ]; then
        termy_say -s "Please enter the postal zip code you want to locate."
        printf "📦 \033[1mPostal Zip Code Lookup\033[22m\n"
        read -r -p "Enter Zip/Postal Code: " target_zip </dev/tty
        target_zip=$(echo "$target_zip" | xargs)
    fi

    if [ -z "$target_zip" ]; then
        termy_say "Zip code cannot be empty. Operation aborted."
        return 1
    fi

    local ISO_country="US"
    if [ -f "$config_file" ]; then
        local read_country
        read_country=$(jq -r '.country_code // empty' "$config_file" 2>/dev/null)
        if [ -n "$read_country" ]; then
            ISO_country="$read_country"
        fi
    fi

    local clean_country
    clean_country=$(echo "$ISO_country" | tr '[:upper:]' '[:lower:]')

    termy_say -s "Resolving postal data parameters for zip code $target_zip."

    local api_response
    api_response=$(curl -s "https://zippopotam.us{clean_country}/${target_zip}")

    if [ -z "$api_response" ] || [ "$api_response" = "{}" ] || ! echo "$api_response" | jq empty 2>/dev/null; then
        printf "⛔ \033[1mLookup Failure\033[22m\nNo location records found for Zip Code '%s' within Country Code '%s'.\n\n" "$target_zip" "$ISO_country"
        termy_say "⛔ Error. Unable to resolve location details for that postal code."
        return 1
    fi

    local place_name
    local state_name
    local state_short
    place_name=$(echo "$api_response" | jq -r '.places[0]."place name"')
    state_name=$(echo "$api_response" | jq -r '.places[0].state')
    state_short=$(echo "$api_response" | jq -r '.places[0]."state abbreviation"')

    if termy_set_context "last_zip" "$target_zip" \
                          "last_zip_city" "$place_name" \
                          "last_zip_state" "$state_name"; then
        
        printf "📍 \033[1mLocation Resolved Successfully\033[22m\n"
        printf "Zip Code      : %s (%s)\n" "$target_zip" "$ISO_country"
        printf "City/Place    : %s\n" "$place_name"
        printf "State/Region  : %s (%s)\n\n" "$state_name" "$state_short"

        termy_say -s "Postal code resolved. Location identified as $place_name, region $state_name."
    else
        termy_say "⛔ Error: Failed to record postal tracking elements inside configuration."
        return 1
    fi

}
