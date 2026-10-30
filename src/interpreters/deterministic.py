import os
import subprocess
import sys
import time
from rich.markdown import Markdown
from providers.api import ApiProvider
from providers.local import LocalProvider
from tools import TOOLS
from .base import Interpreter, ExecutionResult, ExecutionContext, execute_and_sync_tools

class DeterministicInterpreter(Interpreter):
    
    def compute_response_time(self, start_time):
        return time.perf_counter() - start_time
    
    def format_response_time(self, start_time):
        return (
            f"[color(240)]Response time:[/color(240)] "
            f"[color(247)]{self.compute_response_time(start_time):.2f}s[/]"
        )
        
    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        result = ExecutionResult()
        start_time = time.perf_counter()
        client = ApiProvider(url="http://127.0.0.1:5000", timeout=30.0)
        res = client.request(exec_ctx.cli_args.npc, user_input)    
        
        if res is None:
            exec_ctx.console.print("NPC-Forge server offline, starting local...")
            client = LocalProvider(exec_ctx.forge_root_dir, exec_ctx.current_bot_dir)
            res = client.request(exec_ctx.cli_args.npc, user_input)
            
        if res is None:
            result.status = "rejected"
            return result

        status = str(res.get("status", "rejected")).lower()
        result.status = status
        
        meta = (
            f"[color(240)]Status:[/color(240)] [color(247)]{status} [/]"
            f"[color(240)]Interpreter:[/color(240)] [color(247)]deterministic [/]"
            f"[color(240)]Confidence:[/color(240)] [color(247)]{res.get('confidence', 0.0) * 100:.2f}%[/] "
            f"{self.format_response_time(start_time)}"        
        )
        
        if status != "rejected":
            result.ndf_objects.append(res)
            response_text = res.get("response", "")
            result.responses.append(response_text)
            
            command = ""
            actions_taken = []
            standard_tools = []
            
            # 1. Separate custom terminal commands from standard tools
            tools = res.get("tools", [])
            if tools and any(tools):
                for tool_group in tools:
                    if isinstance(tool_group, dict): 
                        tool_group = [tool_group]
                    for tool_data in tool_group:
                        if not isinstance(tool_data, dict): continue
                        
                        tool_args = tool_data.get("arguments", {})
                        
                        explanation = tool_args.get("explanation", "").strip()
                        if explanation and explanation not in actions_taken:
                            actions_taken.append(explanation)
                        
                        standard_tools.append(tool_data)

            print()            
            exec_ctx.tui.render_action(
                thinking=res.get("thinking", ""),
                response=Markdown(str(response_text).strip()),
                command=command,
                description="",
                title=f"[bold green]{res.get('npc', 'NPC')}[/] {res.get('emoji', '')} {meta}"
            )
            
            TOOLS["tts"].execute(
                {"text": response_text}, True, context, exec_ctx.console, exec_ctx.config
            )            
            
            if len(standard_tools):
                # 2. Execute all standard tools using the shared helper
                actions_taken.extend(execute_and_sync_tools(
                    tools_data=standard_tools,
                    context=context,
                    exec_ctx=exec_ctx,
                    result=result,
                    thinking="",
                    global_permission=res.get("permission", "ask")
                ))
            
            print()            
        else:
            # Handle rejected status (multi-choice menu logic remains identical to your original)
            related = res.get("related", [])
            if related and exec_ctx.fallback:
                related_intents = [
                    intent["input"][0] if isinstance(intent.get("input"), list) else str(intent.get("input", ""))
                    for intent in related
                ]
                menu_text = f"Type [bold green]1-{len(related)}[/] or [bold green]q[/] to quit\n"
                exec_ctx.console.print()
                choice = exec_ctx.tui.multi_choice(f"[bold green]{res.get('npc', 'NPC')}[/] {res.get('emoji', '')} {meta}", related_intents, menu_text, 'g')
                
                if isinstance(choice, int) and 0 < choice <= len(related):
                    try:
                        res_proc = subprocess.run([os.path.abspath(sys.argv[0]), related_intents[choice - 1]], env=os.environ)
                        result.exit_code = res_proc.returncode
                        return result
                    except KeyboardInterrupt:
                        exec_ctx.console.print("\n[yellow]Execution cancelled.[/yellow]\n")
                        result.exit_code = 130
                        return result
                    except Exception as exc:
                        exec_ctx.console.print(f"\n[red]Failed to execute recursive call: {exc}[/red]\n")
                        result.exit_code = 1
                        return result
                elif not choice or str(choice).lower() == 'q':
                    result.exit_code = 0
                    return result
                else:
                    result.meta["generate"] = True
                    return result
            else:
                if exec_ctx.fallback: 
                    exec_ctx.console.print(f"[yellow]Intent not understood.[/yellow]")
                result.exit_code = 0
                return result

        return result