from decomposers import Decomposer
from .base import Interpreter, ExecutionResult, ExecutionContext
from .deterministic import DeterministicInterpreter
from .probabilistic import ProbabilisticInterpreter
from tui.tools import TuiTools

class HybridInterpreter(Interpreter):
    def __init__(self, decomposer: Decomposer):
        self.decomposer = decomposer
        self.det_interpreter = DeterministicInterpreter()
        self.prob_interpreter = ProbabilisticInterpreter()
        self.tui = TuiTools()

    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        final_result = ExecutionResult()
        subprompts = self.decomposer.decompose(user_input)
        context["plan"] = subprompts
        if len(subprompts) > 1:
            exec_ctx.console.print(f"\n[bold cyan]Decomposed into {len(subprompts)} subprompts.[/bold cyan]")

        for idx, subprompt in enumerate(subprompts):
            
            if len(subprompts) > 1:
                self.tui.render_status(f"[bold green]Subprompt {idx + 1}/{len(subprompts)}[/bold green]", subprompt)
            else: 
                self.tui.render_status(f"[bold green]Prompt[/bold green]", subprompt)
            exec_ctx.console.print()
            
            # Step A: Try Deterministic First
            det_result = self.det_interpreter.interpret(subprompt, context, exec_ctx)
            
            if det_result.status != "rejected": final_result.merge(det_result)
            else:
                # Loop until the LLM actually finishes the subtask or hits a hard limit
                max_llm_attempts = 10 
                for attempt in range(max_llm_attempts):
                    prob_result = self.prob_interpreter.interpret(subprompt, context, exec_ctx)
                    final_result.merge(prob_result)
                    
                    # Check if the LLM explicitly finished the subtask
                    if prob_result.is_complete:
                        self.tui.render_status(f"[green]Step complete.[/green]", subprompt)
                        break
                    else: 
                        self.tui.render_status(f"[green]Executing step {attempt + 1}.[/green]", subprompt)
                        exec_ctx.console.print()
                else:
                    exec_ctx.console.print(f"\n[red]ProbabilisticInterpreter failed to resolve subprompt after {max_llm_attempts} attempts.[/red]\n")

        # Final summary for decomposed prompts
        if len(subprompts) > 1:
            if final_result.status == "success":
                self.tui.render_status(f"[bold green]Task execution completed[/bold green]", f"All {len(subprompts)} subprompts completed successfully.")
            elif final_result.status == "partial":
                self.tui.render_status(f"[bold yellow]Task execution partially completed[/bold yellow]", f"Completed {len(final_result.responses)} of {len(subprompts)} subprompts.")
            else:
                self.tui.render_status(f"[bold red]Task execution failed[/bold red]", f"Failed to complete the task.")

        exec_ctx.console.print()
        return final_result