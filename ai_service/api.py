"""Endpoint HTTP for Client web interface"""

#body exemple :
# POST /api/ai/query
# Body JSON : {"question": "Where can I find a wireless mouse?"}

# Réponse 200 :
# {
#     "answer": "...",
#     "tools_used": [...]
# }

from flask import Flask, jsonify, request
import agent

app = Flask(__name__)

@app.route("/api/ai/query", methods=["POST"])
def ai_query():
    """Get a json question and return the agent response"""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body is required."}), 400
    
    question = data.get("question")

    if not isinstance(question, str):
        return jsonify({"error": "A 'question' string is needed."}), 400

    try:
        answer, tools_used = agent.answer_question(question)
    except agent.AgentError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        return jsonify({
            "error": "The AI service is unavailable right now."
        }), 503

    return jsonify({
        "answer": answer,
        "tools_used": tools_used,
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not found"}), 405


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003, debug=True)
