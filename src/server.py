import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from logger import logger
from registry import get_npc_engine
from compile_npc import compile_npc_html
from server_openai import openai_blueprint

app = Flask(__name__)
CORS(app)

app.register_blueprint(openai_blueprint)

@app.route("/<npc_name>/chat/", methods=["GET"])
def chat_html(npc_name):
    try:
        logger.info(f"[server.py][chat_html] Compiling HTML interface for NPC: '{npc_name}'")
        html_content = compile_npc_html(npc_name)
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response
        
    except Exception as server_crash:
        # exc_info=True automatically captures and formats the full traceback in the log file
        logger.error(
            f"[server.py][chat_html] CRITICAL ERROR compiling HTML for NPC '{npc_name}'. "
            f"Exception: {str(server_crash)}", 
            exc_info=True
        )
        # Return a generic error to the client to avoid leaking internal paths/stack traces
        return jsonify({"error": "Internal Server Error: Failed to compile chat interface."}), 500


@app.route("/api/chat/<npc_name>", methods=["POST"])
def chat(npc_name):
    try:
        logger.info(f"[server.py][chat] Incoming chat request for NPC: '{npc_name}'")
        
        engine = get_npc_engine(npc_name)
        if not engine:
            logger.warning(f"[server.py][chat] NPC profile '{npc_name}' not found on disk.")
            return jsonify({"error": f"NPC profile '{npc_name}' not found on disk"}), 404
        
        data = request.get_json() or {}
        message = data.get("message", "")
        
        if not message:
            logger.warning(f"[server.py][chat] Missing mandatory 'message' field in request.")
            return jsonify({"error": "The field 'message' is mandatory"}), 400
        
        # Log a snippet of the message to avoid flooding logs with massive payloads
        msg_preview = message[:100] + "..." if len(message) > 100 else message
        logger.info(f"[server.py][chat] Processing message: '{msg_preview}'")
        
        result = engine.process_messages(message)
        return jsonify(result)
        
    except Exception as server_crash:
        # exc_info=True ensures the traceback is written to the rotating log file
        logger.error(
            f"[server.py][chat] CRITICAL ERROR processing chat for NPC '{npc_name}'. "
            f"Exception: {str(server_crash)}",
            exc_info=True
        )
        return jsonify({
            "error": "Internal Server Error",
            "details": "An unexpected error occurred while processing the request."
        }), 500


if __name__ == "__main__":
    logger.info("[server.py][main] Starting NPC-Forge Flask Server on http://127.0.0.1:5000")
    
    # Note: For production deployment, it is highly recommended to use a WSGI 
    # server like Gunicorn or Waitress instead of the built-in Flask development server.
    # Example: gunicorn -w 4 -b 127.0.0.1:5000 server:app
    app.run(host="127.0.0.1", port=5000, debug=False)