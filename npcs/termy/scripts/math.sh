
compute_area() {
    local shape="$1"
    local p1="$2"
    local p2="$3"
    local res=""
    local user_unit=""
    local out_unit=""
    local raw_unit=""
    local spoken_unit=""

    # Check presence of minimum required parameters
    if [ -z "$shape" ] || [ -z "$p1" ]; then
        echo "Usage: compute_area <shape> <parameter1> [parameter2]"
        echo "Supported shapes: square, circle, circle_diameter, rectangle, triangle"
        return 1
    fi

    # Compute area according to the $shape parameter
    case "$shape" in
        square)
            res=$(echo "scale=4; $p1 * $p1" | bc -l)
            ;;
        circle)
            res=$(echo "scale=4; 4*a(1) * ($p1 ^ 2)" | bc -l)
            ;;
        circle_diameter)
            res=$(echo "scale=4; 4*a(1) * (($p1 / 2) ^ 2)" | bc -l)
            ;;
        rectangle)
            if [ -z "$p2" ]; then
                echo "⛔ Error: Rectangle are computation requires 2 sides."
                return 1
            fi
            res=$(echo "scale=4; $p1 * $p2" | bc -l)
            ;;
        triangle)
            if [ -z "$p2" ]; then
                echo "⛔ Error: Triangle are computation requires 2 sides."
                return 1
            fi
            res=$(echo "scale=4; ($p1 * $p2) / 2" | bc -l)
            ;;
        *)
            echo "Forma non supportata: $shape"
            return 1
            ;;
    esac

    # Prompt interactively to determine the unit of measure
    read -p "Which is the unit of measure? (mm, cm, m, km): " user_unit

    # Convert short abbreviation to full spoken word for termy_say
    case "$user_unit" in
        mm) spoken_unit="millimeters" ;;
        cm) spoken_unit="centimeters" ;;
        m)  spoken_unit="meters" ;;
        km) spoken_unit="kilometers" ;;
        *)  spoken_unit="unknown units" ;;
    esac

    # Format unit of measure
    if [ -z "$user_unit" ]; then
        out_unit=" ?^2"
        raw_unit="?"
        termy_speech="Result: $res squared"
    else
        out_unit=" ${user_unit}^2"
        raw_unit="$user_unit"
        termy_speech="Result: $res $spoken_unit squared"
    fi

    echo -e "\nResult: $res$out_unit"
    termy_say -s "$termy_speech"
    termy_set_context last_math_result "$res"
    termy_set_context last_math_result_unit "$raw_unit"
}

plot_function() {
    local raw_equation="$1"
    local gnuplot_equation=""
    local half_range=10

    if [ -z "$raw_equation" ]; then
        echo "Usage: plot_function \"<equation>\""
        echo "Example: plot_function \"x**2 - 4\""
        return 1
    fi

    # Check if equation contains any spaces or tabs
    if [[ "$raw_equation" =~ [[:space:]] ]]; then
        echo -e "\n⛔ Error: Equation contains spaces."
        echo "Please provide the equation without spaces."
        echo ""
        echo "Examples:"
        echo "  sin(x)*x"
        echo "  x**2-4"
        echo "  exp(x)/2+cos(x)"
        echo ""
        echo "Incorrect:"
        echo "  sin(x) * x"
        echo "  x ** 2 - 4"
        return 1
    fi


    if ! command -v gnuplot &> /dev/null; then
        echo -e "\n⚠️ Gnuplot is not installed on this system."
        termy_say -s "Gnuplot is missing. I need to install it to draw the function."
        echo "Attempting automatic installation (requires sudo privileges)..."
        sudo apt update && sudo apt install -y gnuplot
        
        if ! command -v gnuplot &> /dev/null; then
            echo "⛔ Error: Unable to install gnuplot automatically. Please run: sudo apt install gnuplot"
            termy_say -s "Installation failed. Please install gnuplot manually."
            return 1
        fi
        echo -e "✅ Gnuplot successfully installed!\n"
    fi

    if [[ "$raw_equation" == *=* ]]; then
        gnuplot_equation=$(echo "$raw_equation" | cut -d'=' -f2-)
    else
        gnuplot_equation="$raw_equation"
    fi
    gnuplot_equation=$(echo "$gnuplot_equation" | tr -d ' ' | sed 's/\*\*/\^/g')

    termy_say -s "Interactive plot initialized. Use arrow keys to zoom."
    
    while true; do
        clear
        echo -e "--- Live Plot for f(x) = $gnuplot_equation --- (Current Range: -$half_range to $half_range)"
        echo -e "\nResult:"

        gnuplot << EOF 2>/tmp/termy_plot_err.txt
        set terminal dumb size 70 20 unicode ansi aspect 3;
        set xrange [-$half_range:$half_range];
        set autoscale y;
        set grid;
        unset key;
        plot $gnuplot_equation notitle with lines lc rgb "green";
EOF

        if [ $? -ne 0 ]; then
            echo "⛔ Error while plotting the function."
            cat /tmp/termy_plot_err.txt
            return 1
        fi

        echo -e "\n[Controls]  ▲ : Zoom In  |  ▼ : Zoom Out  |  q : Quit Plotter"

        read -s -n 1 key
        if [[ $key == $'\e' ]]; then
            read -s -n 2 -t 0.1 next_chars
            key+="$next_chars"
        fi

        case "$key" in
            $'\e[A')
                if [ $half_range -gt 1 ]; then
                    half_range=$(( half_range - 2 ))
                fi
                ;;
            $'\e[B')
                half_range=$(( half_range + 2 ))
                ;;
            q|Q)
                echo -e "\nExiting plotter..."
                break
                ;;
        esac
    done

    termy_say -s "Plotter closed."
    termy_set_context last_math_result "Term-Plot: $gnuplot_equation"
    termy_set_context last_math_result_unit "text-mode-interactive"
}

termy_is_prime() {
    # TCSS Rule 1: Isolate arbitrary user input inside a local variable
    local target_num
    target_num=$(printf '%s' "${1:-}" | xargs)

    if [ -z "$target_num" ] && command -v termy_get_context >/dev/null 2>&1; then
        target_num=$(termy_get_context 'last_math_result' 2>/dev/null | xargs)
        if [ -n "$target_num" ] && [ "$target_num" != "null" ]; then
            printf 'ℹ No argument provided. Using last math result from context: %s\n' "$target_num"
        else
            target_num=""
        fi
    fi

    if [ -z "$target_num" ]; then
        printf >&2 '\033[1;31m✗ Error:\033[0m No number provided or found in context.\n'
        printf >&2 'Usage: termy_is_prime <positive_integer>\n'
        
        if command -v termy_say >/dev/null 2>&1; then
            termy_say '⛔ Error: No number provided.' > /dev/null 2>&1 &
        fi
        return 1
    fi

    if [[ ! "$target_num" =~ ^[0-9]+$ ]]; then
        # TCSS Rule 2: Parameterized printf wrapping the unsafe input in literal single-quotes
        printf >&2 '\033[1;31m✗ Error:\033[0m %s is not a valid positive integer.\n' "'$target_num'"
        
        if command -v termy_say >/dev/null 2>&1; then
            local safe_voice="${target_num//\'/}"
            termy_say "⛔ Error: ${safe_voice} is not a valid integer." > /dev/null 2>&1 &
        fi
        return 1
    fi

    local is_prime=true

    if [ "$target_num" -lt 2 ]; then
        is_prime=false
    else
        for ((i=2; i*i<=target_num; i++)); do
            if [ $((target_num % i)) -eq 0 ]; then
                is_prime=false
                break
            fi
        done
    fi

    if [ "$is_prime" = true ]; then
        printf '\033[1;32m✓ %s is a PRIME number.\033[0m\n' "$target_num"
        
        if command -v termy_say >/dev/null 2>&1; then
            termy_say "${target_num} is a prime number." > /dev/null 2>&1 &
        fi
    else
        printf '\033[1;31m✗ %s is NOT a prime number.\033[0m\n' "$target_num"
        
        if command -v termy_say >/dev/null 2>&1; then
            termy_say "${target_num} is not a prime number." > /dev/null 2>&1 &
        fi
    fi

    if command -v termy_set_context >/dev/null 2>&1; then
        termy_set_context last_math_result "$target_num"
        termy_set_context last_math_result_unit "text-mode-interactive"
    fi
}





