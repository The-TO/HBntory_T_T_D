"""Tests de l'agent, sans Ollama.

On remplace le vrai modèle par un faux, qui donne des réponses écrites à
l'avance. Le serveur MCP, lui, est le vrai.
Lancement, depuis le dossier ai_service/ :  python3 -m pytest test_agent.py -v
"""
import json

import pytest

import agent
import settings


def use_fake_model(monkeypatch, replies):
    """Remplace call_ollama par un faux modèle qui renvoie les réponses de
    la liste `replies`, une par appel, dans l'ordre."""
    seen = []

    def fake_call_ollama(messages, tools):
        seen.append(list(messages))
        return replies.pop(0)

    monkeypatch.setattr(agent, "call_ollama", fake_call_ollama)
    return seen  # pour regarder ensuite ce que le modèle a reçu


def ask_tool(name, arguments):
    """Une réponse du modèle qui demande un tool."""
    return {"role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": name,
                                         "arguments": arguments}}]}


def answer(text):
    """Une réponse finale du modèle."""
    return {"role": "assistant", "content": text}


def test_answer_without_tool(monkeypatch):
    use_fake_model(monkeypatch, [answer("I can only help with products.")])
    text, tools_used = agent.answer_question("What is the weather?")
    assert text == "I can only help with products."
    assert tools_used == []


def test_tool_result_is_sent_back_to_the_model(monkeypatch):
    seen = use_fake_model(monkeypatch, [ask_tool("get_product", {"sku": ""}),
                                        answer("No product given.")])
    text, tools_used = agent.answer_question("Details about a product?")
    assert tools_used == ["get_product"]
    tool_message = seen[1][-1]  # le dernier message du 2e appel au modèle
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["error"] == "invalid_input"


def test_arguments_sent_as_text_are_understood(monkeypatch):
    seen = use_fake_model(monkeypatch, [ask_tool("get_product", '{"sku": ""}'),
                                        answer("ok")])
    agent.answer_question("Details?")
    result = json.loads(seen[1][-1]["content"])
    assert result["error"] == "invalid_input"  # le tool a bien reçu sku=""


def test_unknown_tool_is_refused(monkeypatch):
    seen = use_fake_model(monkeypatch, [ask_tool("delete_everything", {}),
                                        answer("Sorry.")])
    agent.answer_question("Delete the stock")
    assert json.loads(seen[1][-1]["content"])["error"] == "unknown_tool"


def test_agent_stops_after_too_many_rounds(monkeypatch):
    replies = [ask_tool("get_product", {"sku": ""})] * 20
    use_fake_model(monkeypatch, replies)
    text, tools_used = agent.answer_question("Loop forever")
    assert text == agent.FALLBACK_ANSWER
    assert len(tools_used) == settings.MAX_TOOL_ROUNDS


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_invalid_question_is_refused(question):
    with pytest.raises(agent.AgentError):
        agent.answer_question(question)


def test_ollama_down_gives_a_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_URL", "http://localhost:1")
    with pytest.raises(agent.AgentError) as error:
        agent.answer_question("Where is the mouse?")
    assert "unavailable" in str(error.value)