#!/bin/bash

# Fetch and announce weather information using saved JSON coordinates

get_weather() {
    local lat lng city
    lat=$(termy_get_context "latitude")
    lng=$(termy_get_context "longitude")
    city=$(termy_get_context "city")

    if [ -z "$lat" ] || [ -z "$lng" ]; then
        termy_say "Location data missing. Initializing configuration setup."
        get_city || { termy_say "Configuration failed."; return 1; }    
        lat=$(termy_get_context "latitude")
        lng=$(termy_get_context "longitude")
        city=$(termy_get_context "city")
    fi

    if [ -z "$lat" ] || [ -z "$lng" ]; then
        termy_say "⛔ Error: Missing required GPS coordinates."
        return 1
    fi

    local weather
    weather=$(curl -s --max-time 5 "https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current_weather=true&temperature_unit=celsius&timezone=auto")
    
    if [ -z "$weather" ] || [ "$weather" = "null" ]; then
        termy_say "⛔ Error: Unable to reach the weather service provider."
        return 1
    fi

    local temp code
    temp=$(echo "$weather" | jq -r '.current_weather.temperature // empty')
    code=$(echo "$weather" | jq -r '.current_weather.weathercode // empty')

    local icon condition
    case $code in
        0) icon="☀️" ; condition="Clear sky" ;;
        1|2|3) icon="🌤️" ; condition="Mainly clear or partly cloudy" ;;
        45|48) icon="🌫️" ; condition="Fog and depositing rime fog" ;;
        51|53|55) icon="🌦️" ; condition="Drizzle light or dense intensity" ;;
        61|63|65) icon="☔" ; condition="Rain slight or heavy intensity" ;;
        71|73|75) icon="❄️" ; condition="Snow fall slight or heavy weight" ;;
        80|81|82) icon="🌧️" ; condition="Rain showers continuous" ;;
        95|96|99) icon="⚡" ; condition="Thunderstorm with slight or heavy hail" ;;
        *) icon="❓" ; condition="Unknown condition pattern" ;;
    esac

    echo -e "\n🌐 City: $city | 🌡️ Temp: ${temp}°C | $icon  Weather: $condition ($code)"
    echo -e "\n📊 Forecasts:"
    
    local encoded_city
    encoded_city=$(xxd -plain <<< "$city" | tr -d '\n' | sed 's/\(..\)/%\1/g' | sed 's/%0a//g')
    
    curl -s --max-time 5 "https://wttr.in/${encoded_city}"
    termy_say -s "In $city the temperature is ${temp} degrees celsius, with $condition."
}

# Fetch and announce the current moon phase using saved city or fallback

get_moon_phase() {
    local city
    city=$(termy_get_context "city")
    
    if [ -z "$city" ]; then
        city="London"
    fi

    local encoded_city
    encoded_city=$(xxd -plain <<< "$city" | tr -d '\n' | sed 's/\(..\)/%\1/g' | sed 's/%0a//g')

    local moon_icon
    moon_icon=$(curl -s --max-time 5 "https://wttr.in/${encoded_city}?format=%m" | xargs)

    if [ -z "$moon_icon" ] || [ "$moon_icon" = "null" ]; then
        termy_say "⛔ Error: Unable to reach the moon phase service provider."
        return 1
    fi

    local condition
    case "$moon_icon" in
        "🌑") condition="New Moon" ;;
        "🌒") condition="Waxing Crescent" ;;
        "🌓") condition="First Quarter" ;;
        "🌔") condition="Waxing Gibbous" ;;
        "🌕") condition="Full Moon" ;;
        "🌖") condition="Waning Gibbous" ;;
        "🌗") condition="Last Quarter" ;;
        "🌘") condition="Waning Crescent" ;;
        *)    condition="Current Phase" ;;
    esac

    echo -e "\n🌙 City: $city | Phase: $moon_icon ($condition)"
    termy_say -s "The current moon phase in $city is $condition."
}
