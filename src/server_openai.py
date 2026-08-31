import os
import re
import time
import json
from flask import Blueprint, request, jsonify
from registry import get_npc_engine
from logger import logger

openai_blueprint = Blueprint("openai_api", __name__)

@openai_blueprint.route("/api/v1/models", methods=["GET"])
def list_bots():
    """Returns the list of all available chatbots inside the npcs/ directory."""
    logger.info("[server_openai.py][list_bots] /api/v1/models - Scanning NPC profiles on disk...")
    npc_base = "npcs"
    
    try:
        models_data = list(
            map(lambda npc: {
                "id": npc, 
                "object": "model", 
                "created": int(os.path.getctime(os.path.join(npc_base, npc))), 
                "owned_by": os.environ.get("USER", "user")
            }, os.listdir(npc_base))
        )
        logger.info(f"[server_openai.py][list_bots] /api/v1/models - Successfully listed {len(models_data)} dynamic models.")
        
        response = {
            "object": "list",
            "data": models_data
        }
        return jsonify(response)
    except Exception as list_error:
        logger.error(f"[server_openai.py][list_bots] /api/v1/models - CRITICAL: Failed to scan directory structure: {str(list_error)}")
        return jsonify({"error": "Failed to list available models", "details": str(list_error)}), 500


@openai_blueprint.route("/api/v1/chat/completions", methods=["POST"])
def chat_completions():
    req = request.get_json() or {}
    messages = req.get("messages", [])
    requested_model =  str(req.get("model", "termy")).lower().strip()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    npc_base = os.path.join(base_dir, "npcs")
    
    logger.info("[server_openai.py][chat_completions] /api/v1/chat/completions")
    
    if not messages:
        logger.warning("[server_openai.py][chat_completions] /api/v1/chat/completions - FAILED: Payload missing 'messages' array.")
        return jsonify({"error": "Empty messages stack"}), 400
        
    last_message = messages[-1]
    role = last_message.get("role", "user")
    message_content = last_message.get("content", "")
    
    current_timestamp_ms = int(time.time() * 1000)

    if role == "tool" or "calling tool" in message_content or "Tool result" in message_content:
        terminal_output = message_content.replace("Tool result:", "").strip()
        logger.info(f"[server_openai.py][chat_completions] Intercepted tool execution response from VS Code terminal interface: '{terminal_output[:50]}...'")
        
        return jsonify({
            "id": f"npc-forge-{current_timestamp_ms}",
            "object": "chat.completion",
            "created": current_timestamp_ms,
            "model": "gpt-5.4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": terminal_output,
                        "refusal": None,
                        "annotations": []
                    },
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "service_tier": "default"
        })

    match = re.search(
        r'<userRequest>\s*(.*?)\s*</userRequest>',
        message_content, 
        re.IGNORECASE | re.DOTALL
    )
    user_prompt = match.group(1).strip() if match else message_content.strip()
    logger.info(f"[server_openai.py][chat_completions] Extracted text: '{user_prompt}'")
    
    if not requested_model or not os.path.exists(os.path.join(npc_base, requested_model)):
        logger.warning(f"[server_openai.py][chat_completions] Client requested '{requested_model}', which is not a valid NPC. Forcing 'termy'.")
        npc_name = "termy"
    else:
        npc_name = requested_model
    
    engine = get_npc_engine(npc_name)
    if not engine:
        logger.error("[server_openai.py][chat_completions] Error: 'termy' core engine profile not found or failed to initialize.")
        return jsonify({"error": "NPC profile 'termy' not found on disk"}), 404
        
    result = engine.process_messages(user_prompt)
    termy_output = result.get('response', '')
    status = result.get("status", "rejected")
    termy_thinking = result.get("thinking", "")
    tools_list = result.get("tools", [])
    
    is_matched = (status.lower().strip() in [
        "exact match", "template match", "probabilistic match"
    ])
    has_tools = is_matched and len(tools_list) > 0
    
    logger.info(f"[server_openai.py][chat_completions] Status: [{status.upper()}] | Tools: {has_tools}")

    message_payload = {
        "role": "assistant",
        "content": termy_output if termy_output else None,
        "reasoning_content": termy_thinking if termy_thinking else None, 
        "refusal": None,
        "annotations": []
    }
        
    if has_tools:
        logger.info(f"[server_openai.py][chat_completions] Packaging {len(tools_list)} bash command(s).")
        openai_tool_calls = []
        
        for i, tool in enumerate(tools_list):
            # if 'tool' is a list/tuple take first entry
            if isinstance(tool, (list, tuple)):
                logger.warning(f"[server_openai.py][chat_completions] Detected nested list in tools_list.")
                if len(tool) > 0:
                    tool_data = tool[0] if not isinstance(tool[0], (list, tuple)) else tool[0][0]
                else: continue
            else: tool_data = tool

            if isinstance(tool_data, dict):
                tool_name = tool_data.get("name", "run_in_terminal")
                tool_args = tool_data.get("arguments", {})
            else: logger.warning(f"[server_openai.py][chat_completions] Tool is raw scalar data ({type(tool_data).__name__}).")
                        
            openai_tool_calls.append({
                "id": f"call_{current_timestamp_ms}_{i}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args)
                }
            })
            
        message_payload["tool_calls"] = openai_tool_calls
        finish_reason = "tool_calls"

    else:
        logger.info(f"[server_openai.py][chat_completions] Packaging reply.")
        finish_reason = "stop"
    
    logger.info(f"[server_openai.py][chat_completions] Payload prepared. Target Action: '{termy_output[:60]}...' | Reason: '{finish_reason}'")
    
    return jsonify({
        "id": f"npc-forge-{current_timestamp_ms}",
        "object": "chat.completion",
        "created": current_timestamp_ms,
        "model": "termy-0",
        "choices": [
            {
                "index": 0,
                "message": message_payload,
                "logprobs": None,
                "finish_reason": finish_reason
            }
        ],
        "usage": {"prompt_tokens": 19, "completion_tokens": 10, "total_tokens": 29},
        "service_tier": "default"
    })
