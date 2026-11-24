"""L'agent IA de HBntory : une question entre, une réponse sort.

Le modèle (Ollama) ne connaît ni les produits ni le stock. Il demande des
tools, ce fichier les exécute sur le serveur MCP et lui renvoie les
résultats, jusqu'à ce que le modèle donne sa réponse finale.
"""
import asyncio
import json
import os
import sys

import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import settings
from prompts import build_system_prompt

FALLBACK_ANSWER = ("Sorry, I could not find the answer with the available "
                   "information.")


class AgentError(Exception):
    """La question ne peut pas être traitée (question invalide, modèle
    injoignable...). Le message peut être montré à l'utilisateur."""


def check_question(question):
    """Vérifie la question et la renvoie sans espaces autour."""
    question = (question or "").strip()
    if not question:
        raise AgentError("Please ask a question.")
    if len(question) > settings.MAX_QUESTION_LENGTH:
        raise AgentError("The question is too long (%d characters maximum)."
                         % settings.MAX_QUESTION_LENGTH)
    return question


def call_ollama(messages, tools):
    """Envoie la conversation au modèle. Renvoie son message (un dict)."""
    payload = {
        "model": settings.AI_MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,  # la réponse complète en une seule fois
        "options": {
            "temperature": 0,  # le moins d'invention possible
            "num_ctx": settings.NUM_CTX,  # taille de la mémoire du modèle
        },
    }
    try:
        response = requests.post(settings.OLLAMA_URL + "/api/chat",
                                 json=payload, timeout=settings.MODEL_TIMEOUT)
    except requests.RequestException as error:
        # Le détail technique va dans le terminal, pas à l'utilisateur.
        print("OLLAMA ERROR", repr(error))
        raise AgentError("The AI model is unavailable right now. "
                         "Is Ollama running?")
    if response.status_code != 200:
        # Ollama explique son erreur dans le corps de la réponse,
        # par exemple : model "qwen3:8b" not found, try pulling it first.
        print("OLLAMA ERROR", response.status_code, response.text[:300])
        raise AgentError("The AI model returned an error (HTTP %d). "
                         "Is the model downloaded?" % response.status_code)
    return response.json()["message"]


def tools_for_ollama(mcp_tools):
    """Décrit les tools MCP au modèle, dans le format qu'Ollama attend."""
    tools = []
    for tool in mcp_tools.tools:
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        })
    return tools


def read_arguments(arguments):
    """Les arguments d'un tool doivent être un dict. Certains modèles les
    envoient sous forme de texte JSON : on le transforme en dict."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return {}
    if isinstance(arguments, dict):
        return arguments
    return {}


def tool_error(code, message):
    """Une erreur au même format que celles du serveur MCP, en texte."""
    return json.dumps({"ok": False, "error": code, "message": message})


async def run_tool(session, name, arguments, tool_names):
    """Exécute un tool sur le serveur MCP. Renvoie toujours un texte : en
    cas de problème, une erreur que le modèle pourra expliquer."""
    print("TOOL CALL", name, arguments)  # pour voir ce que fait l'agent
    if name not in tool_names:
        print("UNKNOWN TOOL asked by the model:", name)
        text = tool_error("unknown_tool", "No tool named '%s'." % name)
    else:
        try:
            result = await session.call_tool(name, arguments)
            text = result.content[0].text
        except Exception:
            text = tool_error("tool_call_failed",
                              "The tool could not be called. Information "
                              "is unavailable right now.")
    print("TOOL RESULT", text[:200])
    return text


async def talk_to_model(session, question):
    """La boucle de l'agent. Renvoie (réponse, noms des tools appelés)."""
    tools = tools_for_ollama(await session.list_tools())
    tool_names = [tool["function"]["name"] for tool in tools]
    tools_used = []

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": question},
    ]

    # On redonne la main au modèle tant qu'il demande des tools,
    # sans dépasser MAX_TOOL_ROUNDS tours.
    for round_number in range(settings.MAX_TOOL_ROUNDS):
        message = call_ollama(messages, tools)
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:  # pas de tool demandé : c'est la réponse finale
            answer = (message.get("content") or "").strip()
            answer = answer.replace("**", "")  # enlève le gras Markdown
            return answer or FALLBACK_ANSWER, tools_used

        for call in tool_calls:
            name = call["function"]["name"]
            arguments = read_arguments(call["function"].get("arguments"))
            text = await run_tool(session, name, arguments, tool_names)
            tools_used.append(name)
            messages.append({
                "role": "tool",
                "tool_name": name,
                # on coupe les résultats trop longs pour le modèle
                "content": text[:settings.MAX_TOOL_RESULT_CHARS],
            })

    print("AGENT STOPPED after %d rounds" % settings.MAX_TOOL_ROUNDS)
    return FALLBACK_ANSWER, tools_used  # trop de tours : on s'arrête


async def run_agent(question):
    """Lance le serveur MCP, puis répond à UNE question.

    Renvoie (réponse, noms des tools appelés).
    """
    question = check_question(question)
    server = StdioServerParameters(
        command=sys.executable,  # le Python de l'environnement virtuel
        args=[settings.MCP_SERVER_SCRIPT],
        cwd=settings.MCP_SERVER_DIR,  # le serveur se lance dans son dossier
        env=dict(os.environ),  # transmet PRODUCT_API_URL, HBNTORY_DB...
    )
    problem = None

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            try:
                return await talk_to_model(session, question)
            except AgentError as error:
                # Une erreur qui sortirait d'ici serait "emballée" par la
                # librairie MCP dans une ExceptionGroup, et ne serait plus
                # reconnue comme une AgentError. On la garde de côté...
                problem = error

    raise problem  # ... et on la relance une fois la connexion fermée


def answer_question(question):
    """Version normale (pas async) de run_agent, pour Flask et ask.py."""
    return asyncio.run(run_agent(question))