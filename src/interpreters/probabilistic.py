import time
from agents import resolve_agent_class
from providers import resolve_provider_class
from tools import TOOLS, get_tools_by_name
from .base import Interpreter, ExecutionResult, ExecutionContext, execute_and_sync_tools

class ProbabilisticInterpreter(Interpreter):
    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        result = ExecutionResult()
        result.status = "busy"
        
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

        max_iterations = 50 if getattr(exec_ctx.cli_args, "agent", False) else 1
        llm_model = llm_config.get("model", "unknown")
        
        for iteration in range(max_iterations):
            details = getattr(exec_ctx.cli_args, 'llm_detail', "")
            
            with exec_ctx.console.status(f"[bold green]Agent loop ({llm_model}) step {iteration + 1}[/]", spinner="dots"):
                agent_result = agent.run_step(
                    user_input, details, context, 
                    getattr(exec_ctx.cli_args, "context", None) or llm_config.get("num_ctx", 4096), 
                    iteration + 1
                )
            
            if not agent_result:
                exec_ctx.console.print(f"[red]Failed to get response from {llm_model}.[/red]")
                result.status = "rejected"
                break
                
            output, step_status, ndf_object = agent_result
            ndf_object = {"input": [user_input]} | ndf_object
            result.ndf_objects.append(ndf_object)
            
            tools_list = ndf_object.get("tools", [])
            
            # Check for finish tool first
            should_break = False
            for tool_info in tools_list:
                if tool_info.get("name") == "finish":
                    result.status = "success"
                    if output and output not in result.responses:
                        result.responses.append(output)
                    should_break = True
                    break
            
            if should_break:
                break
            
            exec_ctx.tui.render_action(
                thinking=ndf_object.get("thinking", ""),
                response=ndf_object.get("output", ""),
                command="",
                description="",
                title=f"[bold green]{llm_model}[/]"
            )

            
            TOOLS["tts"].execute(
                {"text": ndf_object.get("output", "")}, True, context, exec_ctx.console, exec_ctx.config
            )  
            
            # Execute all other standard tools using the shared helper
            execute_and_sync_tools(
                tools_data=tools_list,
                context=context,
                exec_ctx=exec_ctx,
                result=result,
                thinking="",
                global_permission=ndf_object.get("permission", "ask"),
                skip_tool_names=["finish"]
            )

            if step_status == "done":
                result.status = "success"
                if output and output not in result.responses:
                    result.responses.append(output)
                break
        else:
            result.status = "partial"

        return result