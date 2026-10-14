import json
import os
from pathlib import Path
import time
from agents import resolve_agent_class
from providers import resolve_provider_class
from tools import TOOLS, get_tools_by_name, render_tool_action
from .base import Interpreter, ExecutionResult, ExecutionContext

class ProbabilisticInterpreter(Interpreter):
    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        start_time = time.perf_counter()
        result = ExecutionResult()
        result.status = "busy" # Initialize as busy/partial until proven successful
        
        config = exec_ctx.config
        llm_config = config.get("llm", {})
        agent_config = config.get("agent", {})
        
        if not llm_config.get("enabled", False):
            exec_ctx.console.print("[red]LLM is not enabled.[/red]")
            result.status = "rejected"
            return result

        try:
            agent = resolve_agent_class(agent_config.get("type", "self-reflecting"))(
                resolve_provider_class(llm_config.get("provider", "ollama"))(llm_config),
                get_tools_by_name(agent_config.get("tools", []))
            )
        except Exception as e:
            exec_ctx.console.print(f"[red]Failed to init LLM agent: {e}[/red]")
            result.status = "rejected"
            return result

        max_iterations = 50 if exec_ctx.cli_args.agent else 1
        llm_model = llm_config.get("model", "unknown")
        
        for iteration in range(max_iterations):
            prompt = f"\n\nTask: {user_input}\n"
            if hasattr(exec_ctx.cli_args, 'llm_detail') and exec_ctx.cli_args.llm_detail:
                prompt += f"Details: {exec_ctx.cli_args.llm_detail}\n\n"
            
            with exec_ctx.console.status(f"[bold green]Agent loop ({llm_model}) step {iteration + 1}[/]", spinner="dots"):
                agent_result = agent.run_step(prompt, context, exec_ctx.cli_args.context or llm_config.get("num_ctx", 4096), iteration + 1)
            
            if not agent_result:
                exec_ctx.console.print(f"[red]Failed to get response from {llm_model}.[/red]")
                result.status = "rejected"
                break
                
            output, ndf_object = agent_result
            result.ndf_objects.append(ndf_object)
            
            tools_list = ndf_object.get("tools", [])
            step_status = ndf_object.get("status", "busy")   
            tool_name = "unknown"
            
            for tool_info in tools_list:
                tool_name = tool_info.get("name", "unknown")
                tool_config = tool_info.get("arguments", {}) 
            
                if tool_name == "finish": 
                    result.status = "success"
                    if output and output not in result.responses:
                        result.responses.append(output)
                    break
                
                render_tool_action(
                    exec_ctx.tui, 
                    tool_name, 
                    tool_config, 
                    output, 
                    ndf_object.get("thinking", ""), 
                    llm_model, 
                    step_status, 
                    iteration, 
                    time.perf_counter() - start_time
                )

                tool_config["scripts_dir"] = Path(exec_ctx.current_bot_dir) / "scripts"
                exec_tool_name = tool_name if tool_name in TOOLS else "run_command"
                tool_module = TOOLS.get(exec_tool_name)
                
                if not tool_module:
                    exec_ctx.console.print(f"[red]Unknown tool: {tool_name}[/red]")
                    continue

                perm_prompt = f"\nShould I execute {tool_name}?"
                perm_execute = ndf_object.get("permission") in ("yolo", "auto") or exec_ctx.cli_args.yes or exec_ctx.cli_args.force_yes
                
                tool_call_result = tool_module.execute(
                    args=tool_config,
                    execute=perm_execute or exec_ctx.tui.confirm(perm_prompt),
                    context=context,
                    console=exec_ctx.console,
                    config=config
                )  
                
                if isinstance(tool_call_result, int):
                    result.exit_code = tool_call_result
                
                Path(exec_ctx.context_path).parent.mkdir(parents=True, exist_ok=True)
                with open(exec_ctx.context_path, "w", encoding="utf-8") as f:
                    json.dump(context, f, indent=4, ensure_ascii=False)

            if step_status == "done" or tool_name == "finish":
                result.status = "success"
                if output and output not in result.responses:
                    result.responses.append(output)
                break
        else:
            # This block executes if the loop finishes WITHOUT hitting a 'break'
            # Meaning the LLM ran out of iterations without finishing the task
            result.status = "partial"
                
        # Dataset saving logic using the last NDF object in the trace
        if result.status == "success" and result.ndf_objects:
            final_ndf = result.ndf_objects[-1] 
            perm_execute = final_ndf.get("permission") in ("yolo", "auto") or exec_ctx.cli_args.yes or exec_ctx.cli_args.force_yes
            
            if not perm_execute:
                save_intent = exec_ctx.tui.confirm("\nDo you want to save this final entry in the dataset?")
                if save_intent:
                    from storage.dataset import DatasetStorage
                    storage = DatasetStorage()
                    dataset_dir = Path(exec_ctx.current_bot_dir) / "dataset"
                    dataset_dir.mkdir(parents=True, exist_ok=True)           
                    save_filename = f"dataset_{os.environ.get('USER', 'user')}.json"
                    storage.save_entry(final_ndf, str(dataset_dir), save_filename)
                    exec_ctx.console.print("[green]Entry saved to dataset.[/green]")

        return result