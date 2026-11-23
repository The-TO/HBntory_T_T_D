"""Ask one question to the AI agent from the terminal."""
import argparse
import asyncio
import logging
import sys

import agent


async def run(question):
    async with agent.mcp_session() as session:
        return await agent.ask(session, question)


def print_trace(result):
    print("\n--- tool calls (%d), model calls: %d ---" % (len(result.tool_calls), result.model_calls))
    if not result.tool_calls:
        print("(no tool was called)")
    for number, call in enumerate(result.tool_calls, start=1):
        status = "ERROR" if call.is_error else "ok"
        print("[%d] %s %s -> %s (%d ms)" % (number, call.name, call.arguments, status, call.duration_ms))
        preview = call.result if len(call.result) <= 300 else call.result[:300] + "..."
        print("    result:", preview)


def main():
    parser = argparse.ArgumentParser(description="Ask the HBntory AI agent a question.")
    parser.add_argument("question", nargs="+", help="the question, in natural language")
    parser.add_argument("--debug", action="store_true", help="show every tool call")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        result = asyncio.run(run(" ".join(args.question)))
    except agent.AgentError as error:
        print("Error:", error)
        if error.detail:
            print("Detail:", error.detail)
        return 1
    except Exception as error:  # MCP server could not start, etc.
        print("Unexpected error: %r" % error)
        print("Check MCP_SERVER_DIR, that the MCP server runs (python3 test_client.py), "
              "and that the Product API is up.")
        return 1

    print(result.answer)
    if args.debug:
        print_trace(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
