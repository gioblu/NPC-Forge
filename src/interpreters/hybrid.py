from decomposers import Decomposer
from .base import Interpreter, ExecutionResult, ExecutionContext
from .deterministic import DeterministicInterpreter
from .probabilistic import ProbabilisticInterpreter

class HybridInterpreter(Interpreter):
    def __init__(self, decomposer: Decomposer):
        self.decomposer = decomposer
        self.det_interpreter = DeterministicInterpreter()
        self.prob_interpreter = ProbabilisticInterpreter()

    def interpret(self, user_input: str, context: dict, exec_ctx: ExecutionContext) -> ExecutionResult:
        final_result = ExecutionResult()
        subprompts = self.decomposer.decompose(user_input)
        
        if len(subprompts) > 1:
            exec_ctx.console.print(f"\n[bold cyan]Decomposed into {len(subprompts)} subprompts.[/bold cyan]")

        for idx, subprompt in enumerate(subprompts):
            if len(subprompts) > 1:
                exec_ctx.console.print(f"\n[bold cyan]--- Subprompt {idx + 1}/{len(subprompts)} ---[/bold cyan]")
                exec_ctx.console.print(f"[italic]{subprompt}[/italic]\n")

            # Step A: Try Deterministic First
            det_result = self.det_interpreter.interpret(subprompt, context, exec_ctx)
            
            if det_result.status != "rejected":
                final_result.merge(det_result)
            else:
                # Step B: Fallback to Probabilistic (LLM)
                exec_ctx.console.print(f"[yellow]Deterministic rejected. Falling back to LLM...[/yellow]")
                
                # Loop until the LLM actually finishes the subtask or hits a hard limit
                max_llm_attempts = 10 
                for attempt in range(max_llm_attempts):
                    prob_result = self.prob_interpreter.interpret(subprompt, context, exec_ctx)
                    final_result.merge(prob_result)
                    
                    # Check if the LLM explicitly finished the subtask
                    if prob_result.is_complete:
                        exec_ctx.console.print(f"[bold green]Subprompt resolved by LLM.[/bold green]")
                        break
                    else:
                        exec_ctx.console.print(f"[yellow]LLM needs more steps to resolve subprompt. Attempt {attempt + 1}/{max_llm_attempts}...[/yellow]")
                else:
                    exec_ctx.console.print(f"[red]LLM failed to resolve subprompt after {max_llm_attempts} attempts.[/red]")

        # Final summary for decomposed prompts
        if len(subprompts) > 1:
            exec_ctx.console.print("\n" + "="*40)
            if final_result.status == "success":
                exec_ctx.console.print(f"[bold green]✓ All {len(subprompts)} subprompts resolved successfully.[/bold green]")
            elif final_result.status == "partial":
                exec_ctx.console.print(f"[bold yellow]⚠ Partially resolved: {len(final_result.responses)}/{len(subprompts)} subprompts succeeded.[/bold yellow]")
            else:
                exec_ctx.console.print(f"[bold red]✗ Failed to resolve any subprompts.[/bold red]")
            exec_ctx.console.print("="*40 + "\n")

        return final_result