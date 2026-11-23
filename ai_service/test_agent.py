"""Tests of the agent logic with a fake model and a fake MCP session.

No Ollama, no MCP server and no network needed.
Run from ai_service/:   pytest -v
"""
import asyncio
import json
from types import SimpleNamespace

import pytest
import requests

import agent
import prompts
import settings


# --- fakes --------------------------------------------------------------------

def text_reply(text):
    return {"role": "assistant", "content": text}


def tool_reply(name, arguments):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": name, "arguments": arguments}}],
    }


class FakeModel:
    """Replies with the scripted answers, in order, and records each request."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []  # (messages, tools) seen at each call

    async def __call__(self, messages, tools):
        self.requests.append((list(messages), tools))
        return self.replies.pop(0)


def mcp_result(text, is_error=False):
    return SimpleNamespace(isError=is_error, content=[SimpleNamespace(type="text", text=text)])


class FakeSession:
    """Fake MCP client session exposing one tool, get_product."""

    def __init__(self, results):
        self.results = results  # tool name -> result object, or an Exception
        self.calls = []

    async def list_tools(self):
        schema = {"type": "object", "properties": {"sku": {"type": "string"}}}
        return SimpleNamespace(
            tools=[SimpleNamespace(name="get_product", description="Get one product", inputSchema=schema)]
        )

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        outcome = self.results[name]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def run(coro):
    return asyncio.run(coro)


# --- the agent loop -----------------------------------------------------------

def test_question_without_tool_is_answered_directly():
    model = FakeModel([text_reply("I can only help with products and stock.")])
    session = FakeSession({})
    result = run(agent.ask(session, "What is the weather?", chat=model))
    assert result.answer == "I can only help with products and stock."
    assert result.tool_calls == []
    assert session.calls == []


def test_model_receives_system_prompt_and_mcp_tools():
    model = FakeModel([text_reply("ok")])
    run(agent.ask(FakeSession({}), "Hello", chat=model))
    messages, tools = model.requests[0]
    assert messages[0] == {"role": "system", "content": prompts.build_system_prompt()}
    assert messages[1] == {"role": "user", "content": "Hello"}
    assert tools == [{
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get one product",
            "parameters": {"type": "object", "properties": {"sku": {"type": "string"}}},
        },
    }]


def test_tool_call_is_executed_recorded_and_result_sent_back():
    model = FakeModel([
        tool_reply("get_product", {"sku": "HB-LAP-1001"}),
        text_reply("It is a laptop."),
    ])
    session = FakeSession({"get_product": mcp_result('{"ok": true, "product": {"sku": "HB-LAP-1001"}}')})
    result = run(agent.ask(session, "Details of HB-LAP-1001", chat=model))

    assert result.answer == "It is a laptop."
    assert session.calls == [("get_product", {"sku": "HB-LAP-1001"})]
    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert (call.name, call.arguments, call.is_error) == ("get_product", {"sku": "HB-LAP-1001"}, False)
    assert json.loads(call.result)["ok"] is True
    assert result.model_calls == 2

    # The second request carries the tool result, as a "tool" message.
    messages, _ = model.requests[1]
    assert messages[-1] == {
        "role": "tool",
        "tool_name": "get_product",
        "content": '{"ok": true, "product": {"sku": "HB-LAP-1001"}}',
    }
    assert messages[-2]["tool_calls"][0]["function"]["name"] == "get_product"


def test_tool_error_is_passed_to_the_model():
    model = FakeModel([tool_reply("get_product", {"sku": "X"}), text_reply("Unavailable.")])
    error_text = '{"ok": false, "error": "product_api_unavailable", "message": "down"}'
    session = FakeSession({"get_product": mcp_result(error_text, is_error=True)})
    result = run(agent.ask(session, "Details of X", chat=model))
    assert result.tool_calls[0].is_error is True
    assert model.requests[1][0][-1]["content"] == error_text
    assert result.answer == "Unavailable."


def test_crash_of_the_mcp_server_does_not_crash_the_agent():
    model = FakeModel([tool_reply("get_product", {"sku": "X"}), text_reply("Unavailable.")])
    session = FakeSession({"get_product": RuntimeError("pipe closed")})
    result = run(agent.ask(session, "Details of X", chat=model))
    assert result.tool_calls[0].is_error is True
    assert "tool_call_failed" in result.tool_calls[0].result
    assert result.answer == "Unavailable."


def test_unknown_tool_is_refused_without_calling_the_mcp_server():
    model = FakeModel([tool_reply("delete_everything", {}), text_reply("Sorry.")])
    session = FakeSession({})
    result = run(agent.ask(session, "Do something", chat=model))
    assert session.calls == []
    assert result.tool_calls[0].is_error is True
    assert "unknown_tool" in result.tool_calls[0].result
    assert "get_product" in model.requests[1][0][-1]["content"]  # the model is told what exists


def test_arguments_sent_as_a_json_string_are_understood():
    model = FakeModel([tool_reply("get_product", '{"sku": "A1"}'), text_reply("ok")])
    session = FakeSession({"get_product": mcp_result('{"ok": true}')})
    run(agent.ask(session, "Details of A1", chat=model))
    assert session.calls == [("get_product", {"sku": "A1"})]


def test_long_tool_result_is_cut_for_the_model_but_kept_in_the_trace():
    big = "x" * (settings.MAX_TOOL_RESULT_CHARS + 500)
    model = FakeModel([tool_reply("get_product", {"sku": "A1"}), text_reply("ok")])
    session = FakeSession({"get_product": mcp_result(big)})
    result = run(agent.ask(session, "Details of A1", chat=model))
    assert result.tool_calls[0].result == big
    sent = model.requests[1][0][-1]["content"]
    assert len(sent) < len(big) and "TRUNCATED" in sent


def test_agent_stops_after_too_many_tool_rounds():
    model = FakeModel([tool_reply("get_product", {"sku": "X"}) for _ in range(settings.MAX_TOOL_ROUNDS + 1)])
    session = FakeSession({"get_product": mcp_result('{"ok": true}')})
    result = run(agent.ask(session, "Loop forever", chat=model))
    assert result.answer == agent.FALLBACK_ANSWER
    assert len(result.tool_calls) == settings.MAX_TOOL_ROUNDS


def test_empty_model_answer_gives_the_fallback():
    result = run(agent.ask(FakeSession({}), "Hello", chat=FakeModel([text_reply("  ")])))
    assert result.answer == agent.FALLBACK_ANSWER


def test_bad_questions_are_rejected_before_calling_the_model():
    model = FakeModel([])
    for bad in ["", "   ", None, "x" * (settings.MAX_QUESTION_LENGTH + 1)]:
        with pytest.raises(agent.AgentError):
            run(agent.ask(FakeSession({}), bad, chat=model))
    assert model.requests == []


def test_system_prompt_lists_every_supported_question_type():
    prompt = prompts.build_system_prompt()
    assert len(prompts.SUPPORTED_QUESTIONS) >= 4
    for question in prompts.SUPPORTED_QUESTIONS:
        assert question["description"] in prompt
        assert question["examples"], question["id"]


# --- communication with Ollama -------------------------------------------------

def fake_response(status, body):
    return SimpleNamespace(status_code=status, json=lambda: body, text=str(body))


def test_ollama_request_has_the_expected_shape(monkeypatch):
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen.update(url=url, payload=json, timeout=timeout)
        return fake_response(200, {"message": {"role": "assistant", "content": "hi"}})

    monkeypatch.setattr(agent.requests, "post", fake_post)
    reply = run(agent.ollama_chat([{"role": "user", "content": "x"}], []))
    assert reply == {"role": "assistant", "content": "hi"}
    assert seen["url"].endswith("/api/chat")
    assert seen["payload"]["model"] == settings.AI_MODEL
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["options"]["temperature"] == 0


def test_ollama_not_running_gives_a_clear_error(monkeypatch):
    def refuse(url, json=None, timeout=None):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(agent.requests, "post", refuse)
    with pytest.raises(agent.AgentError) as error:
        run(agent.ollama_chat([], []))
    assert str(error.value) == agent.MODEL_UNAVAILABLE
    assert "ollama serve" in error.value.detail


def test_missing_model_gives_a_clear_error(monkeypatch):
    monkeypatch.setattr(
        agent.requests, "post",
        lambda url, json=None, timeout=None: fake_response(404, {"error": "model not found"}),
    )
    with pytest.raises(agent.AgentError) as error:
        run(agent.ollama_chat([], []))
    assert "ollama pull" in error.value.detail
    assert "model not found" in error.value.detail


def test_ollama_timeout_gives_a_clear_error(monkeypatch):
    def slow(url, json=None, timeout=None):
        raise requests.Timeout("too slow")

    monkeypatch.setattr(agent.requests, "post", slow)
    with pytest.raises(agent.AgentError) as error:
        run(agent.ollama_chat([], []))
    assert "MODEL_TIMEOUT" in error.value.detail
