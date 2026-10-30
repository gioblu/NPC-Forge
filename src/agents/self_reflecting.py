from agents.base import BaseAgent

class SelfReflectingAgent(BaseAgent):
    
    def _build_content(self, user_input: str, context: dict, i: int = 0) -> list:
        system_prompt = (
            "You are a sincere, talented, helpful and ironic terminal expert.\n"
            "You are running on consumer hardware; be terse, write elegant code.\n"
            "The human assigned to you a task, please complete it step-by-step using the provided tools.\n"
            "Thank you.\n"
        )
        
        task_journal = context.get('summary', None)
        if task_journal is None: task_journal_list = "None"
        elif len(task_journal) == 0:
            task_journal_list = "None (List is empty, no actions appended yet)"
        else: task_journal_list = "\n".join(f"- {item}" for item in task_journal)

        # Format plan as a numbered list if it's an array
        plan = context.get('plan', None)
        if plan is None:
            plan_str = "None"
        elif isinstance(plan, list):
            plan_str = "\n".join(f"{idx+1}. {item}" for idx, item in enumerate(plan))
        else: plan_str = str(plan)

        state_msg = (
            f"Plan: {plan_str}\n"
            f"Iteration: {i}\n"
            f"Active file: {context.get('active_file', 'None')}\n"
            f"Active content: {context.get('active_content', 'None')}\n"
            f"Last execution output: {context.get('output', 'None')}\n"
            f"Your past actions in this session:\n{task_journal_list}"
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_input}\n\nState:\n{state_msg}"}
        ]

    def run_step(self, user_input: str, details: str, context: dict, ctx: int = 4096, i: int = 0) -> tuple:
        prompt = f"\n\nTask: {user_input}\n"
        if details: prompt += f"Details: {details}\n\n"
        content = self._build_content(prompt, context, i)
        response = self.provider.request(content, self.tools, ctx)
        if not response: return None
            
        content = response.get("content", "").strip()
        tool_calls = response.get("tool_calls", [])
        
        if tool_calls:
            call = tool_calls[0]
            func = call.get("function", {})
            tool_name = func.get("name")
            raw_args = func.get("arguments", {})            
            explanation = raw_args.get("explanation", "")
            goal = raw_args.get("goal", explanation)
            output = content if content else explanation
            ndf_object = {
                "category": tool_name,
                "input": [user_input],
                "output": output,
                "thinking": response.get("thinking", ""),
                "tools": [
                    {
                        "name": tool_name,
                        "arguments": raw_args
                    }
                ],
                "permission": "ask"
            }
            
            return output, "done" if tool_name == "finish" else "busy", ndf_object