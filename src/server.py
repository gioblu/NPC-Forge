import os
from pathlib import Path
import signal
import traceback
from flask import Flask, json, request, jsonify, make_response
from registry import get_npc_engine
from compile_npc import compile_npc_html
from server_openai import openai_blueprint
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.register_blueprint(openai_blueprint)

@app.route("/<npc_name>/chat/", methods=["GET"])
def chat_html(npc_name):
    try:
        html_content = compile_npc_html(npc_name)
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response
    except Exception as server_crash:
        print("\n" + "="*50)
        print("!!! CRITICAL SERVER SIDE ERROR DETECTED !!!")
        print(f"Target NPC Profile HTML Compile: {npc_name}")
        print("="*50)
        traceback.print_exc()
        print("="*50 + "\n")
        return f"Error compiling chat: {str(server_crash)}", 500

@app.route("/api/chat/<npc_name>", methods=["POST"])
def chat(npc_name):
    try:
        engine = get_npc_engine(npc_name)
        if not engine:
            return jsonify({"error": f"NPC profile '{npc_name}' not found on disk"}), 404
        
        data = request.get_json() or {}
        message = data.get("message", "")
        if not message:
            return jsonify(
                {"error": "The field 'message' is mandatory"}
            ), 400
        
        result = engine.process_messages(message)
        return jsonify(result)
        
    except Exception as server_crash:
        print("\n" + "="*50)
        print("!!! CRITICAL SERVER SIDE ERROR DETECTED !!!")
        print(f"Target NPC Profile: {npc_name}")
        print("="*50)
        traceback.print_exc()
        print("="*50 + "\n")
        
        return jsonify({
            "error": "Internal Server Error Context Exception",
            "details": str(server_crash)
        }), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)


