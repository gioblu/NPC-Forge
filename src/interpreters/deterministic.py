import json
import os
import subprocess
import sys
import shlex
from pathlib import Path
import time
from rich.markdown import Markdown
from providers.api import ApiProvider
from providers.local import LocalProvider
from tools import TOOLS
from .base import Interpreter, ExecutionResult, ExecutionContext

class DeterministicInterpreter(Interpreter):
    
    def compute_response_time(self, start_time):
        end_time = time.perf_counter()
        return end_time - start_time
    
    def format_response_time(self, start_time):
        return (
            f"[color(240)]Response time:[/color(240)] "
            f"[color(247)]{self.compute_response_time(start_time):.2f}s[/]"
        )
        
    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        result = ExecutionResult()
        start_time = time.perf_counter()
        client = ApiProvider(url="http://127.0.0.1:5000", timeout=10.0)
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
            result.ndf_objects.append(res) # Capture the NDF trace
            
            response_text = res.get("response", "")
            result.responses.append(response_text)
            
            command = ""
            actions_taken = [] # We will collect explanations to inject into context["summary"]
            
            tools = res.get("tools", [])
            if tools:
                for tool_group in tools:
                    if isinstance(tool_group, dict): tool_group = [tool_group]
                    for tool_data in tool_group:
                        if not isinstance(tool_data, dict): continue
                        
                        tool_args = tool_data.get("arguments", {})
                        
                        # 1. Extract command
                        if "command" in tool_args:
                            command += (f" && {tool_args['command']}" if command else tool_args["command"])
                        
                        # 2. Extract the VSCode-Pilot style explanation from arguments
                        explanation = tool_args.get("explanation", "").strip()
                        if explanation and explanation not in actions_taken:
                            actions_taken.append(explanation)

            TOOLS["tts"].execute({"text": response_text}, True, context, exec_ctx.config)
            print()
            exec_ctx.tui.render_action(
                thinking=res.get("thinking", ""),
                response=Markdown(str(response_text).strip()),
                command=command,
                description=" ".join(actions_taken).strip(),
                title=f"[bold green]{res.get('npc', 'NPC')}[/] {res.get('emoji', '')} {meta}"
            )
            print()
            
            if command:
                scripts_dir = Path(exec_ctx.current_bot_dir) / "scripts"
                sources = []
                if scripts_dir.is_dir():
                    sources = [f"source {shlex.quote(str(f))}" for f in sorted(scripts_dir.iterdir()) if f.suffix == ".sh"]
                if sources: command = f"{' && '.join(sources)} && {command}"

                permission = res.get("permission", "ask")
                perm_execute = permission in ("yolo", "auto") or exec_ctx.cli_args.yes or exec_ctx.cli_args.force_yes

                if perm_execute or exec_ctx.tui.confirm("\nShould I run it?"):
                    try:
                        if not perm_execute: print("\n")
                        res_proc = subprocess.run(command, shell=True, executable="/bin/bash", check=False)
                        if not perm_execute: print()
                        result.exit_code = res_proc.returncode
                        
                        if Path(exec_ctx.context_path).exists():
                            try:
                                # 1. Reload from disk to get 'termy_set_context' updates from the bash script
                                with open(exec_ctx.context_path, "r", encoding="utf-8") as f:
                                    disk_context = json.load(f)
                                
                                # 2. Safely merge disk state into in-memory context
                                for key, value in disk_context.items():
                                    if key == "summary" and isinstance(value, list) and isinstance(context.get("summary"), list):
                                        # Preserve existing summaries, add any new ones from disk
                                        for item in value:
                                            if item not in context["summary"]:
                                                context["summary"].append(item)
                                    else:
                                        context[key] = value
                                
                                # 3. NOW inject the deterministic explanations into the freshly synced summary
                                if "summary" not in context:
                                    context["summary"] = []
                                for action in actions_taken:
                                    summary_entry = f"[Deterministic] {action}"
                                    if summary_entry not in context["summary"]:
                                        context["summary"].append(summary_entry)
                                        
                                # 4. Save the fully synced context back to disk immediately
                                with open(exec_ctx.context_path, "w", encoding="utf-8") as f:
                                    json.dump(context, f, indent=4, ensure_ascii=False)
                                    
                            except Exception as e:
                                exec_ctx.console.print(f"[yellow]Warning: Failed to sync context from disk: {e}[/yellow]")
                                
                    except Exception as exc:
                        exec_ctx.console.print(f"[red]Failed to execute command: {exc}[/red]")
                        result.exit_code = 1
                else:
                    exec_ctx.console.print("\n[yellow]Execution aborted by user.[/yellow]")
                    
        else:
            # Handle rejected status with related intents multi-choice menu
            related = res.get("related", [])
            
            if related:
                related_intents = [
                    intent["input"][0] if isinstance(intent.get("input"), list) else str(intent.get("input", ""))
                    for intent in related
                ]
                
                menu_text = f"Type [bold green]1-{len(related)}[/] or [bold green]q[/] to quit\n"
                exec_ctx.console.print()
                choice = exec_ctx.tui.multi_choice(
                    f"[bold green]{res.get('npc', 'NPC')}[/] {res.get('emoji', '')} {meta}", 
                    related_intents, 
                    menu_text, 
                    'g'
                )
                
                if isinstance(choice, int) and 0 < choice <= len(related):
                    try:
                        script_path = os.path.abspath(sys.argv[0])
                        res_proc = subprocess.run([script_path, related_intents[choice - 1]], env=os.environ)
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
                exec_ctx.console.print(f"[yellow]Intent not understood.[/yellow]")
                result.exit_code = 0
                return result

        return result