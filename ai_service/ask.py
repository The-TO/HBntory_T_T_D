"""Pose une question à l'agent depuis le terminal.

Lancement, depuis le dossier ai_service/ :
    python3 ask.py "Where can I find a wireless mouse?"
        -> affiche seulement la réponse

    python3 ask.py --debug "Where can I find a wireless mouse?"
        -> affiche aussi chaque appel de tool (TOOL CALL / TOOL RESULT)
           et la liste des tools utilisés
"""
import contextlib
import io
import sys

import agent

# On sépare l'option --debug du reste : le reste, c'est la question.
args = sys.argv[1:]
debug = "--debug" in args
args = [word for word in args if word != "--debug"]

if not args:
    print('Usage: python3 ask.py [--debug] "your question"')
    sys.exit(1)

question = " ".join(args)

try:
    if debug:
        # Mode debug : tout ce que l'agent affiche (TOOL CALL...) reste visible.
        answer, tools_used = agent.answer_question(question)
    else:
        # Mode normal : on cache ce que l'agent affiche pendant son travail.
        with contextlib.redirect_stdout(io.StringIO()):
            answer, tools_used = agent.answer_question(question)
except agent.AgentError as error:
    print("Error:", error)
    sys.exit(1)

print("\nANSWER:", answer)
if debug:
    print("TOOLS USED:", tools_used)
