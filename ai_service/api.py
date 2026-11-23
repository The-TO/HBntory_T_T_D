"""AI Query Service : l'endpoint HTTP utilisé par la page cliente.

Lancement, depuis le dossier ai_service/ :  python3 api.py  (port 5003)

    POST /api/ai/query
    Corps JSON :   {"question": "Where can I find a wireless mouse?"}
    Réponse 200 :  {"answer": "...", "tools_used": [...]}
    Erreurs :      400 (question invalide), 503 (modèle ou tools en panne)
"""
from flask import Flask, jsonify, request

import agent

app = Flask(__name__)


@app.after_request
def allow_client_page(response):
    """CORS : autorise la page cliente (sur un autre port) à appeler ici.

    "*" veut dire : n'importe quelle page. C'est acceptable ici, parce que
    le service est public et anonyme : il ne lit aucun cookie et ne
    renvoie rien de privé.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


@app.route("/api/ai/query", methods=["POST", "OPTIONS"])
def ai_query():
    """Reçoit une question en JSON et renvoie la réponse de l'agent."""
    # Avant un POST en JSON, le navigateur envoie tout seul une requête
    # OPTIONS pour vérifier qu'il a le droit d'appeler ce service.
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON body is required."}), 400

    # 1. On vérifie la question AVANT d'appeler l'agent.
    #    Une erreur ici est la faute de la requête : 400.
    question = data.get("question")
    if not isinstance(question, str):
        return jsonify({"error": "A 'question' text is required."}), 400
    try:
        question = agent.check_question(question)
    except agent.AgentError as error:
        return jsonify({"error": str(error)}), 400

    # 2. La question est valide : toute erreur à partir d'ici vient du
    #    service lui-même (Ollama éteint, serveur MCP en panne...) : 503.
    try:
        answer, tools_used = agent.answer_question(question)
    except agent.AgentError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:
        print("AI SERVICE ERROR", repr(error))  # détail pour nous seulement
        return jsonify({"error": "The AI service is unavailable right "
                                 "now."}), 503

    return jsonify({"answer": answer, "tools_used": tools_used})


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed."}), 405


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003, debug=True)