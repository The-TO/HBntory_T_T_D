"""Pose une question à l'agent depuis le terminal.

Lancement, depuis le dossier ai_service/ :
    python3 ask.py "Where can I find a wireless mouse?"
Chaque appel de tool s'affiche (TOOL CALL / TOOL RESULT), puis la réponse.
"""
import sys

import agent

if len(sys.argv) < 2:
    print('Usage: python3 ask.py "your question"')
    sys.exit(1)

question = " ".join(sys.argv[1:])

try:
    answer, tools_used = agent.answer_question(question)
except agent.AgentError as error:
    print("Error:", error)
    sys.exit(1)

print("\nANSWER:", answer)
print("TOOLS USED:", tools_used)