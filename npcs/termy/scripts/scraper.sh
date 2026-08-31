#!/usr/bin/env bash
#
# Web scraping utility with lazy trafilatura installation in npc-forge venv
# Installs trafilatura only when user requests scraping
#

# Colors for output
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

# Default timeout
DEFAULT_TIMEOUT=10

# Path to npc-forge virtual environment
FORGE_VENV="$HOME/.local/share/npc-forge/venv"
FORGE_PYTHON="$FORGE_VENV/bin/python3"
FORGE_PIP="$FORGE_VENV/bin/pip"

# Check if trafilatura is installed in the npc-forge venv
check_trafilatura() {
    "$FORGE_PYTHON" -c "import trafilatura" 2>/dev/null && return 0 || return 1
}

# Install trafilatura in the npc-forge venv
install_trafilatura() {
    echo -e "${YELLOW}📦 Installing trafilatura in npc-forge environment...${RESET}"
    
    if [ ! -d "$FORGE_VENV" ]; then
        echo -e "${RED}⛔ npc-forge virtual environment not found at $FORGE_VENV${RESET}"
        echo -e "${YELLOW}Please run: ./setup.sh${RESET}"
        return 1
    fi
    
    if [ ! -x "$FORGE_PIP" ]; then
        echo -e "${RED}⛔ pip not found in $FORGE_VENV/bin${RESET}"
        return 1
    fi
    
    if "$FORGE_PIP" install trafilatura --quiet 2>/dev/null; then
        echo -e "${GREEN}✅ trafilatura installed successfully${RESET}"
        return 0
    else
        echo -e "${RED}⛔ Failed to install trafilatura${RESET}"
        return 1
    fi
}

# Scrape URL and extract main content
scrape_url() {
    local url="$1"
    local output_format="${2:-txt}"  # txt, html, json, markdown, csv, xml, xmltei
    
    # Map user-friendly names to trafilatura formats
    case "$output_format" in
        text) output_format="txt" ;;
        plain) output_format="txt" ;;
    esac
    
    # Validate format against supported formats
    case "$output_format" in
        txt|html|json|markdown|csv|xml|xmltei) ;;
        *)
            echo -e "${RED}⛔ Invalid format: $output_format${RESET}" >&2
            echo -e "${YELLOW}Valid formats: txt, html, json, markdown, csv, xml, xmltei${RESET}" >&2
            return 1
            ;;
    esac
    
    if ! check_trafilatura; then
        install_trafilatura || return 1
    fi
    
    "$FORGE_PYTHON" << PYEOF
import trafilatura
import sys
import json

url = "$url"

try:
    # Fetch URL with trafilatura (no timeout param - use defaults)
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        print("${RED}⛔ Failed to fetch URL${RESET}", file=sys.stderr)
        sys.exit(1)
    
    # Extract main content
    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        output_format="$output_format"
    )
    
    if result:
        if "$output_format" == "json":
            data = json.loads(result)
            print(json.dumps(data, indent=2))
        else:
            print(result)
    else:
        print("${YELLOW}⚠  No content extracted from URL${RESET}", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"${RED}⛔ Error: {e}${RESET}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# Extract specific metadata from URL
scrape_metadata() {
    local url="$1"
    
    if ! check_trafilatura; then
        install_trafilatura || return 1
    fi
    
    "$FORGE_PYTHON" << PYEOF
import trafilatura
import sys
import json

url = "$url"

try:
    # Fetch URL with trafilatura (no timeout param - use defaults)
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        print("${RED}⛔ Failed to fetch URL${RESET}", file=sys.stderr)
        sys.exit(1)
    
    # Extract with metadata
    result = trafilatura.extract(
        downloaded,
        output_format="json",
        include_comments=False
    )
    
    if result:
        data = json.loads(result)
        metadata = {
            "url": "$url",
            "title": data.get("title", "N/A"),
            "author": data.get("author", "N/A"),
            "date": data.get("date", "N/A"),
            "length": len(data.get("text", "")),
            "content_preview": (data.get("text", "")[:200] + "...") if data.get("text") else "N/A"
        }
        print(json.dumps(metadata, indent=2))
    else:
        print("${YELLOW}⚠  No content extracted from URL${RESET}", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"${RED}⛔ Error: {e}${RESET}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# Main CLI function (can be sourced or called directly)
scraper_main() {
    case "${1:-help}" in
        scrape)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}Usage: scraper_main scrape <url> [format]${RESET}"
                echo "Formats: txt (default), html, json, markdown, csv, xml, xmltei"
                return 1
            fi
            scrape_url "$2" "${3:-txt}"
            ;;
        metadata)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}Usage: scraper_main metadata <url>${RESET}"
                return 1
            fi
            scrape_metadata "$2"
            ;;
        check)
            if check_trafilatura; then
                echo -e "${GREEN}✅ trafilatura is installed${RESET}"
            else
                echo -e "${RED}⛔ trafilatura is not installed${RESET}"
                return 1
            fi
            ;;
        install)
            install_trafilatura
            ;;
        *)
            echo -e "${CYAN}Web Scraping Utility${RESET}"
            echo "Usage: scraper_main <command> [args]"
            echo ""
            echo "Commands:"
            echo "  scrape <url> [format]  - Extract main content from URL"
            echo "                           Formats: text (default), html, json"
            echo "  metadata <url>         - Extract metadata from URL"
            echo "  check                  - Check if trafilatura is installed"
            echo "  install                - Install trafilatura"
            echo ""
            echo "Examples:"
            echo "  scraper_main scrape https://example.com"
            echo "  scraper_main scrape https://example.com json"
            echo "  scraper_main metadata https://example.com"
            ;;
    esac
}

# If called directly (not sourced), execute main
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    scraper_main "$@"
fi

