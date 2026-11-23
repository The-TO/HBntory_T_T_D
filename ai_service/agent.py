"""The AI agent: a question goes in, a grounded answer comes out."""
import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import settings
from prompts import build_system_prompt

log = logging.getLogger("ai_service.agent")

FALLBACK_ANSWER = (
    "Sorry, I could not complete this request. Please try a simpler question."
)
MODEL_UNAVAILABLE = "The AI model is unavailable right now."


class AgentError(Exception):
    """The question cannot be answered."""

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail


@dataclass
class ToolCallRecord:
    """One tool call made by the agent."""

    name: str
    arguments: dict
    result: str
    is_error: bool
    duration_ms: int


@dataclass
class AgentResult:
    """The answer, plus everything needed to debug how it was produced."""

    answer: str
    tool_calls: list = field(default_factory=list)  # list of ToolCallRecord
    model_calls: int = 0


# --------------------------------------------------------------------------
# MCP side
# --------------------------------------------------------------------------

@asynccontextmanager
async def mcp_session():
    """Start the MCP server (stdio) and yield an initialized client session."""
    server = StdioServerParameters(
        command=sys.executable,       # the Python of the current virtual env
        args=[settings.MCP_SERVER_SCRIPT],
        cwd=settings.MCP_SERVER_DIR,
        env=dict(os.environ),         # PRODUCT_API_URL, HBNTORY_DB, ...
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _to_model_tools(mcp_tools):
    """Convert the MCP tool definitions to Ollama's tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools.tools
    ]


def _result_text(mcp_result):
    return "\n".join(
        block.text
        for block in mcp_result.content
        if getattr(block, "type", None) == "text"
    )


def _parse_arguments(raw):
    """Tool arguments should be an object; some models send a JSON string."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


async def _call_tool(session, name, arguments):
    """Call one MCP tool and record it. Never raises: errors go to the model."""
    start = time.monotonic()
    try:
        raw = await session.call_tool(name, arguments)
        text, is_error = _result_text(raw), bool(raw.isError)
    except Exception as exc:  # the MCP server itself failed (crash, closed pipe...)
        log.error("tool %s could not be called: %r", name, exc)
        text = json.dumps({
            "ok": False,
            "error": "tool_call_failed",
            "message": "The tool could not be called. Information is unavailable right now.",
        })
        is_error = True
    duration_ms = int((time.monotonic() - start) * 1000)

    log.info(
        "tool_call name=%s args=%s error=%s duration=%dms",
        name, json.dumps(arguments, ensure_ascii=False), is_error, duration_ms,
    )
    log.debug("tool_result name=%s result=%s", name, text)
    return ToolCallRecord(name, dict(arguments), text, is_error, duration_ms)


def _unknown_tool(name, arguments, known_names):
    """The model asked for a tool that does not exist: tell it, call nothing."""
    log.warning("model asked for unknown tool %r", name)
    text = json.dumps({
        "ok": False,
        "error": "unknown_tool",
        "message": "No tool named '%s'. Available tools: %s."
                   % (name, ", ".join(sorted(known_names))),
    })
    return ToolCallRecord(str(name), dict(arguments), text, True, 0)


def _for_model(text):
    """Cut a very long tool result so it fits in the model's context."""
    limit = settings.MAX_TOOL_RESULT_CHARS
    if len(text) <= limit:
        return text
    return text[:limit] + (
        "\n[RESULT TRUNCATED: too long. Search more precisely to see the rest.]"
    )


# --------------------------------------------------------------------------
# Model side (Ollama)
# --------------------------------------------------------------------------

def _post_to_ollama(payload):
    url = settings.OLLAMA_URL.rstrip("/") + "/api/chat"
    try:
        response = requests.post(url, json=payload, timeout=settings.MODEL_TIMEOUT)
    except requests.Timeout as exc:
        log.error("Ollama timeout: %r", exc)
        raise AgentError(MODEL_UNAVAILABLE, detail=(
            "Ollama did not answer within %d seconds. Use a smaller model, "
            "or raise MODEL_TIMEOUT." % settings.MODEL_TIMEOUT)) from exc
    except requests.RequestException as exc:
        log.error("Ollama unreachable: %r", exc)
        raise AgentError(MODEL_UNAVAILABLE, detail=(
            "Cannot reach Ollama at %s. Start it with: ollama serve"
            % settings.OLLAMA_URL)) from exc

    if response.status_code != 200:
        try:
            reason = response.json().get("error", "")
        except ValueError:
            reason = response.text[:200]
        log.error("Ollama HTTP %d: %s", response.status_code, reason)
        raise AgentError(MODEL_UNAVAILABLE, detail=(
            "Ollama answered HTTP %d: %s. Check that the model is downloaded "
            "(ollama pull %s) and supports tool calling."
            % (response.status_code, reason, settings.AI_MODEL)))
    try:
        return response.json()["message"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AgentError(MODEL_UNAVAILABLE, detail="Unexpected answer from Ollama.") from exc


async def ollama_chat(messages, tools):
    """Send the conversation to the local model. Returns its reply message (dict)."""
    payload = {
        "model": settings.AI_MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
        # temperature 0: the most consistent answers, best for facts
        "options": {"temperature": 0, "num_ctx": settings.NUM_CTX},
    }
    return await asyncio.to_thread(_post_to_ollama, payload)


# --------------------------------------------------------------------------
# The agent loop
# --------------------------------------------------------------------------

def _check_question(question):
    if not isinstance(question, str) or not question.strip():
        raise AgentError("Please ask a question.")
    question = question.strip()
    if len(question) > settings.MAX_QUESTION_LENGTH:
        raise AgentError(
            "The question is too long (maximum %d characters)."
            % settings.MAX_QUESTION_LENGTH
        )
    return question


async def ask(session, question, chat=None):
    """Answer one question. Each question is independent (no history)."""
    question = _check_question(question)
    chat = chat or ollama_chat

    tools = _to_model_tools(await session.list_tools())
    known_names = {tool["function"]["name"] for tool in tools}
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": question},
    ]
    result = AgentResult(answer="")

    for round_number in range(settings.MAX_TOOL_ROUNDS + 1):
        reply = await chat(messages, tools)
        result.model_calls += 1

        requested = reply.get("tool_calls") or []
        if not requested:
            result.answer = (reply.get("content") or "").strip() or FALLBACK_ANSWER
            return result

        if round_number == settings.MAX_TOOL_ROUNDS:
            break  # too many tool rounds: stop here

        # The model asked for one or more tools: run them, send the results back.
        messages.append(reply)
        for call in requested:
            function = call.get("function") or {}
            name = function.get("name")
            arguments = _parse_arguments(function.get("arguments"))
            if name in known_names:
                record = await _call_tool(session, name, arguments)
            else:
                record = _unknown_tool(name, arguments, known_names)
            result.tool_calls.append(record)
            messages.append({
                "role": "tool",
                "tool_name": record.name,
                "content": _for_model(record.result),
            })

    log.warning("agent stopped after %d tool rounds", settings.MAX_TOOL_ROUNDS)
    result.answer = FALLBACK_ANSWER
    return result
