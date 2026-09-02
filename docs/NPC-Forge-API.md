# NPC-Forge API Documentation

The NPC-Forge API is a Flask-based HTTP server (defaulting to `http://127.0.0.1:5000`) that provides interfaces for interacting with installed NPCs. It exposes both **Native Endpoints** for direct application integration and **OpenAI-Compatible Endpoints** to allow integration with third-party tools, IDE extensions like VS Code, and LLM harnesses.


### Native Endpoints

These endpoints are designed for direct, straightforward interaction with a specific NPC.

#### NPC Chat Interface
Returns a compiled, standalone HTML chat interface for the specified NPC.

- **Endpoint**: `GET /<npc_name>/chat/`
- **Response Type**: `text/html`

**Success Response** (`200 OK`):
```html
<!-- Compiled HTML chat interface for the requested NPC -->
```

**Error Response** (`500 Internal Server Error`):
```json
{
  "error": "Internal Server Error: Failed to compile chat interface."
}
```
*(Note: Internal stack traces are intentionally suppressed in the response and only logged server-side.)*

---

#### Chat Request
Sends a text message directly to an NPC's engine and returns the raw processed result.

- **Endpoint**: `POST /api/chat/<npc_name>`
- **Request Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "message": "Hello, what can you do?"
}
```

**Success Response** (`200 OK`):
```json
{
  "response": "I can help you with various tasks...",
  "status": "exact match",
  "thinking": "Analyzing user intent...",
  "tools": []
}
```

**Error Responses**:
- `400 Bad Request`: `{"error": "The field 'message' is mandatory"}`
- `404 Not Found`: `{"error": "NPC profile '<npc_name>' not found on disk"}`
- `500 Internal Server Error`: `{"error": "Internal Server Error", "details": "An unexpected error occurred..."}`

---

### OpenAI-Compatible Endpoints

These endpoints mimic the OpenAI API specification, allowing NPC-Forge to act as a drop-in replacement for LLM providers in compatible clients.

#### List Available NPCs
Returns a list of all installed NPC profiles, formatted as OpenAI "models".

- **Endpoint**: `GET /api/v1/models`

**Success Response** (`200 OK`):
```json
{
  "object": "list",
  "data": [
    {
      "id": "termy",
      "object": "model",
      "created": 1690000000,
      "owned_by": "user"
    },
    {
      "id": "guard_bot",
      "object": "model",
      "created": 1690000500,
      "owned_by": "user"
    }
  ]
}
```

**Error Response** (`500 Internal Server Error`):
```json
{
  "error": "Failed to list available models",
  "details": "<error details>"
}
```

---

#### Chat Completions
Processes a chat completion request. This endpoint includes custom parsing logic to handle tool execution results and specific XML tagging.

- **Endpoint**: `POST /api/v1/chat/completions`
- **Request Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "model": "termy",
  "messages": [
    {
      "role": "user",
      "content": "<userRequest> List the files in the current directory </userRequest>"
    }
  ]
}
```

**Success Response** (`200 OK` - Standard Reply):
```json
{
  "id": "npc-forge-1690000000000",
  "object": "chat.completion",
  "created": 1690000000000,
  "model": "termy-0",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Here are the files in the directory...",
        "reasoning_content": "The user wants to list files. I will use the ls tool.",
        "refusal": null,
        "annotations": []
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 19,
    "completion_tokens": 10,
    "total_tokens": 29
  },
  "service_tier": "default"
}
```

**Success Response** (`200 OK` - Tool Call Reply):
*If the NPC engine determines that tools should be executed, the response includes a `tool_calls` array.*
```json
{
  "id": "npc-forge-1690000000000",
  "object": "chat.completion",
  "created": 1690000000000,
  "model": "termy-0",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "reasoning_content": "Executing directory listing.",
        "refusal": null,
        "annotations": [],
        "tool_calls": [
          {
            "id": "call_1690000000000_0",
            "type": "function",
            "function": {
              "name": "run_in_terminal",
              "arguments": "{\"command\": \"ls -la\"}"
            }
          }
        ]
      },
      "logprobs": null,
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 19,
    "completion_tokens": 10,
    "total_tokens": 29
  },
  "service_tier": "default"
}
```

**Success Response** (`200 OK` - Tool Result Interception):
*When the client sends back the result of a tool execution.*
```json
{
  "id": "npc-forge-1690000000000",
  "object": "chat.completion",
  "created": 1690000000000,
  "model": "gpt-5.4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "total 8\ndrwxr-xr-x 2 user user 4096 Sep  2 10:00 .\ndrwxr-xr-x 5 user user 4096 Sep  2 09:00 ..",
        "refusal": null,
        "annotations": []
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  },
  "service_tier": "default"
}
```

**Error Responses**:
- `400 Bad Request`: `{"error": "Empty messages stack"}` (if `messages` array is missing or empty).
- `404 Not Found`: `{"error": "NPC profile 'termy' not found on disk"}` (only if the fallback 'termy' engine fails to initialize).
- `500 Internal Server Error`: Generic server failure during directory scanning or request processing.

---

### Notes for Developers
- **CORS**: Cross-Origin Resource Sharing (CORS) is enabled by default on the Flask app, allowing web-based frontends to interact with the API.
- **Logging**: All requests, extracted prompts, tool calls, and errors are logged via the internal `logger` module. Full tracebacks for `500` errors are written to the rotating log file but are never exposed to the client.
- **Production Deployment**: The built-in Flask development server is used by default. For production, it is highly recommended to serve the app via a WSGI server (e.g., `gunicorn -w 4 -b 127.0.0.1:5000 server:app`).
