from agents.base import BaseAgent

class SelfReflectingAgent(BaseAgent):
    
    def _build_content(self, user_query: str, context: dict, i: int = 0) -> list:
        system_prompt = (
            "You are a sincere, talented, helpful and ironic terminal expert.\n"
            "You are running on consumer hardware; be terse, write elegant code.\n"
            "The human assigned to you a task, please complete it step-by-step using the provided tools.\n"
            f"This is iteration: {i}\n"
            "If you completed the task write it in the summary to let your future self know.\n"
            "Remember: \"An idiot admires complexity, a genious admires simplicity\" Terry A. Davis\n"
            "Thank you.\n"
        )
        
        task_journal = context.get('summary', None)
        if task_journal is None: task_journal_list = "None"
        elif len(task_journal) == 0:
            task_journal_list = "None (List is empty, no actions appended yet)"
        else: task_journal_list = "\n".join(f"- {item}" for item in task_journal)

        state_msg = (
            f"Plan: {context.get('plan', 'None')}\n"
            f"Active file: {context.get('active_file', 'None')}\n"
            f"Active content:\n{context.get('active_content', 'None')}\n"
            f"Last execution output:\n{context.get('output', 'None')}\n"
            f"Your past actions in this session:\n{task_journal_list}"
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_query}\n\nState:\n{state_msg}"}
        ]

    def run_step(self, user_query: str, context: dict, ctx: int = 4096, i: int = 0) -> tuple:
        content = self._build_content(user_query, context, i)
        response = self.provider.request(content, self.tools, ctx)
        if not response: return None
            
        content = response.get("content", "").strip()
        tool_calls = response.get("tool_calls", [])
        
        if tool_calls:
            call = tool_calls[0]
            func = call.get("function", {})
            tool_name = func.get("name")
            raw_args = func.get("arguments", {})
            
            # Extract NDF metadata (LLM may put these in arguments, we pull them out)
            explanation = raw_args.get("summary", "")
            goal = raw_args.get("goal", explanation)
            mode = raw_args.get("mode", "sync")
            
            output = content if content else explanation
            
            # raw_args now contains ONLY the execution payload
            ndf_object = {
                "category": tool_name,
                "output": output,
                "tools": [
                    {
                        "name": tool_name,
                        "explanation": explanation,
                        "goal": goal,
                        "mode": mode,
                        "arguments": raw_args
                    }
                ],
                "status": "done" if tool_name == "finish" else "busy",
                "permission": "yolo"
            }
            
            return output, ndf_object