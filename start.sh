#!/usr/bin/env bash
set -euo pipefail

# Dossier du script : projets/HBntory_T_T_D
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Virtualenv à la racine de HBntory_T_T_D
VENV="$ROOT/venv/bin/activate"

if [[ ! -f "$VENV" ]]; then
    echo "Virtualenv introuvable : $VENV"
    echo "Crée-le avec : python3 -m venv venv"
    exit 1
fi

# 1. Initialisation de la base de données du backoffice (bloquant)
#    Si init_db.py échoue, set -e arrête le script avant de lancer quoi que ce soit.
echo "Initialisation de la base de données..."
(cd "$ROOT/backoffice" && source "$VENV" && python3 init_db.py)
echo "Base de données initialisée."

# 2. API produits via Docker Compose
(cd "$ROOT/../hbntory-products-api" && docker compose up) &
DOCKER_PID=$!

# 3. API IA : port 5003
(cd "$ROOT/ai_service" && source "$VENV" && python3 api.py) &
AI_PID=$!

# 4. Client web : port 8080
(cd "$ROOT/web_client" && source "$VENV" && python3 -m http.server 8080) &
WEB_PID=$!

# 5. Backoffice : port 5002
(cd "$ROOT/backoffice" && source "$VENV" && python3 app.py) &
BACKOFFICE_PID=$!

trap 'kill $DOCKER_PID $AI_PID $WEB_PID $BACKOFFICE_PID 2>/dev/null; wait' EXIT INT TERM

echo "Tous les services sont lancés en parallèle."
echo "Docker Compose : démarré"
echo "AI service : http://127.0.0.1:5003"
echo "Web client : http://127.0.0.1:8080"
echo "Backoffice : http://127.0.0.1:5002"
echo "Ctrl+C pour arrêter les quatre services."

wait
