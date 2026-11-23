"""All AI service settings."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

MCP_SERVER_DIR = os.environ.get(
    "MCP_SERVER_DIR", os.path.join(HERE, "..", "product_mcp_server")
)
MCP_SERVER_SCRIPT = os.environ.get("MCP_SERVER_SCRIPT", "server.py")


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
AI_MODEL = os.environ.get("AI_MODEL", "qwen3:8b")
NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
MODEL_TIMEOUT = int(os.environ.get("MODEL_TIMEOUT", "180"))

# limits
MAX_TOOL_ROUNDS = 6           
MAX_QUESTION_LENGTH = 500      
MAX_TOOL_RESULT_CHARS = 8000   