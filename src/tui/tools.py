import sys
import termios
import tty

from rich.console import Console
from rich.panel import Panel
from rich.padding import Padding
from rich.text import Text
from rich.console import Group

from rich import box

# ANSI Color Codes & UI Elements

RED        = "\033[31m"
GREEN      = "\033[32m"
LIGHT_GRAY = "\033[37m"
GRAY       = "\033[90m"
YELLOW     = "\033[33m"
CYAN       = "\033[36m"
RESET      = "\033[0m"

BOLD       = "\033[1m"
UNDERLINE  = "\033[4m"
CLEAR_LINE = "\033[2K\r"

console = Console()

class TuiTools:

    def keypress(self) -> str:
        """Reads a single keypress instantly without waiting for Enter."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b": 
                ch += sys.stdin.read(2)
        except (KeyboardInterrupt, EOFError):
            return "\x03"
        finally: 
            # 🌟 FIX 1: Usa TCSANOW per ripristinare IMMEDIATAMENTE lo stato originale del terminale
            termios.tcsetattr(fd, termios.TCSANOW, old_settings)
            sys.stdout.flush()
            sys.stdin.flush()
        return ch

    def confirm(self, prompt_text: str = "Execute?") -> bool:
        """A clean, fast confirmation prompt styled with Rich."""
        console.print(
            f"{prompt_text}"
            f" [bold](y/n)[bold]", 
            end=" "
        )
        while True:
            key = self.keypress().lower()
            if key in {"y", "e", "\r", "\n"}: 
                return True
            if key in {"n", "q", "\x03"}: 
                return False

    def multi_choice(self, prompt: str, choices: list, menu: str, additional: str) -> int:
        """
        Renders a stunning terminal menu inspired by Lip Gloss/Charm architecture.
        Instant single-key response with native vertical and horizontal padding.
        """
        if not choices:
            return 0

        max_range = len(choices)
        
        # --- COSTRIAMO IL CONTENUTO (STILE LIP GLOSS) ---
        menu_content = Text()
        
        # 1. Special actions
        menu_content.append("  [q] ", style="bold green")
        menu_content.append("Quit\n", style="bold white")
        
        menu_content.append(f"  [{additional.lower()}] ", style="bold green")
        menu_content.append("Ask model\n", style="bold white")
        
        # Divider line
        menu_content.append("  " + "─" * 30 + "\n", style="dim green")

        # 2. Numbered choices
        for i, choice_text in enumerate(choices, 1):
            menu_content.append(f"  [{i}] ", style="bold green")
            menu_content.append(f"{choice_text}\n", style="white")

        inner_padding = Padding(menu_content, (1, 2, 0, 0))


        panel = Panel(
            inner_padding,
            title=f"[bold green] {prompt} [/bold green]",
            title_align="left",
            border_style="green",
            box=box.SQUARE
        )

        console.print(panel)

        
        # CORREZIONE: Rimosso flush=True che causava il crash di Rich
        console.print(f"  [bold green]➔[/bold green] [dim]Press a key... [/dim]", end="")
        console.print()

        # --- CICLO DI ASCOLTO ISTANTANEO ---
        try:
            while True:
                raw_key = self.keypress()
                key = raw_key.lower().strip()

                # Pulisce la riga di input corrente per un feedback visivo immediato
                print("\r", end="", flush=True)

                if key == 'q' or raw_key == '\x03':
                    return 0
                if key == additional.lower():
                    return max_range + 1
                
                if key.isdigit():
                    numeric_choice = int(key)
                    if 1 <= numeric_choice <= max_range:
                        return numeric_choice
                
                continue

        except (KeyboardInterrupt, EOFError):
            print()
            return 0

    def render_action(
        self, 
        thinking: str = "", 
        response = "",  # Changed type hint so it accepts the Markdown object
        command: str = "", 
        description: str = "", 
        emoji: str = "", 
        title: str = "TERMy Output"
    ):
        """
        Renders thinking, response, command, and description in a unified Rich Panel
        matching the multi_choice Lip Gloss/Charm style.
        """
        # FIX 1: Use a list to collect both Text and Markdown elements
        content_elements = []
        
        if thinking:
            thinking_text = Text()
            thinking_text.append("Thinking: ", style="dim italic #9f9f9f")
            thinking_text.append(f"{thinking}\n", style="dim italic #9f9f9f")
            content_elements.append(thinking_text)
            
        if response:
            content_elements.append(response)
            if emoji:
                content_elements.append(Text(f" {emoji}\n"))
            
        if command:
            command_text = Text()
            command_text.append(f"\n{command}\n", style="bold green")
            content_elements.append(command_text)
            
        if description:
            desc_text = Text()
            desc_text.append(f"{description.strip()}", style="dim #9f9f9f")
            content_elements.append(desc_text)

        # Rimuovi: unified_content = Text("").join(content_elements)
        
        # 🌟 FIX: Usa Group per combinare in sicurezza Text e Markdown insieme
        unified_content = Group(*content_elements)

        # Metti il Group dentro al Padding
        inner_padding = Padding(unified_content, (1, 1, 1, 1))

        panel = Panel(
            inner_padding,
            title=f"[bold green] {title} [/bold green]",
            title_align="left",
            border_style="green",
            box=box.SQUARE
        )

        console.print(panel)

