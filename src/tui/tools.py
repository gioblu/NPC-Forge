import sys
import termios
import tty

from rich.console import Console
from rich.panel import Panel
from rich.padding import Padding
from rich.text import Text
from rich.prompt import Prompt
from rich.console import Group
from rich.syntax import Syntax

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
                try:
                    ch += sys.stdin.read(2)
                except (EOFError, OSError):
                    pass
        except (KeyboardInterrupt, EOFError):
            return "\x03"
        finally: 
            termios.tcsetattr(fd, termios.TCSANOW, old_settings)
            sys.stdout.flush()
            sys.stdin.flush()
        return ch

    def confirm(self, prompt_text: str = "Execute?") -> bool:
        """A clean, fast confirmation prompt styled with Rich."""
        console.print(
            f"{prompt_text} [bold](y/n)[/bold]", 
            end=" "
        )
        while True:
            key = self.keypress().lower()
            if key in {"y", "e", "\r", "\n"}: 
                return True
            if key in {"n", "q", "\x03"}: 
                console.print()
                return False
            
    def prompt(self, question: str):
        try:
            return Prompt.ask(question)
        except (KeyboardInterrupt, EOFError):
            console.print()
            return None

    def multi_choice(self, prompt: str, choices: list, menu: str, additional: str) -> int:
        """
        Renders a stunning terminal menu inspired by Lip Gloss/Charm architecture.
        Instant single-key response with native vertical and horizontal padding.
        """

        max_range = len(choices)
        
        menu_content = Text()
        
        menu_content.append("  [q] ", style="bold green")
        menu_content.append("Quit\n", style="bold white")
        
        menu_content.append(f"  [{additional.lower()}] ", style="bold green")
        menu_content.append("Ask model\n", style="bold white")
        if max_range:
            menu_content.append("  " + "─" * 30 + "\n", style="dim green")

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
        
        console.print(f"  [bold green]➔[/bold green] [dim]Press a key... [/dim]", end="")
        console.print()

        try:
            while True:
                raw_key = self.keypress()
                key = raw_key.lower().strip()

                print("\r", end="", flush=True)

                if key == 'q' or raw_key == '\x03': 
                    console.print()
                    return 0
                if key == additional.lower(): 
                    return max_range + 1
                
                if key.isdigit():
                    numeric_choice = int(key)
                    if 1 <= numeric_choice <= max_range:
                        return numeric_choice
                
                continue

        except (KeyboardInterrupt, EOFError):
            console.print() # Force a clean newline on exit
            return 0

    def render_action(
        self, 
        thinking: str = "", 
        response = "",  # Accepts the Markdown object
        command: str = "", 
        description: str = "",
        title: str = "TERMy Output"
    ):
        """
        Renders thinking, response, command, and description in a unified Rich Panel
        matching the multi_choice Lip Gloss/Charm style.
        """
        content_elements = []
        header = Text()
        header.append(Text.from_markup(f"{title}\n"))
        content_elements.append(header)
                        
        if thinking:
            thinking_text = Text()
            thinking_text.append("Thinking: ", style="dim italic color(240)")
            thinking_text.append(f"{thinking}\n", style="dim italic color(240)")
            content_elements.append(thinking_text)
            
        if response: content_elements.append(response)
            
        if command:
            # 1. Creiamo la sintassi Bash con il tema scelto
            command_syntax = Syntax(
                command.strip(), 
                "bash", 
                theme="one-dark", 
                line_numbers=False, 
                word_wrap=True,
            )
            
            command_box = Panel(
                command_syntax,
                box=box.SQUARE,
                padding=(0, 1, 0, 1),
                border_style="#282c34",
                style="on #282c34"
            )
            
            content_elements.append(Text(""))
            content_elements.append(command_box)
            content_elements.append(Text(""))

            
        if description:
            desc_text = Text()
            desc_text.append(f"{description.strip()}", style="color(240)")
            content_elements.append(desc_text)

        unified_content = Group(*content_elements)
        inner_padding = Padding(unified_content, (0, 0, 0, 0))

        panel = Panel(
            inner_padding,
            border_style="color(234)",
            style="on color(234)",
            box=box.SQUARE
        )

        console.print(panel)