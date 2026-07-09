import os
import logging
import uuid

from flask import Flask, request, jsonify, render_template

# Load a local .env file if present (only used for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hr-agent-webapp")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration - set these as environment variables in Azure App Service
# (see README.md). Defaults below match the sample code from AI Foundry.
# ---------------------------------------------------------------------------
ENDPOINT = os.environ.get(
    "AI_FOUNDRY_ENDPOINT",
    "https://thokebhushan13594-3522-resource.services.ai.azure.com/api/projects/thokebhushan13594-3522",
)
AGENT_NAME = os.environ.get("AI_FOUNDRY_AGENT_NAME", "HRAgent")
AGENT_VERSION = os.environ.get("AI_FOUNDRY_AGENT_VERSION", "3")

# Lazily-created clients (creating a credential/client per request is slow)
_project_client = None
_openai_client = None


def get_openai_client():
    """Create (once) and return the OpenAI-compatible client bound to the
    AI Foundry project. Uses DefaultAzureCredential, which will pick up:
      - your `az login` session when running locally
      - the App Service Managed Identity when deployed to Azure
    """
    global _project_client, _openai_client
    if _openai_client is None:
        logger.info("Initializing AIProjectClient for endpoint %s", ENDPOINT)
        credential = DefaultAzureCredential()
        _project_client = AIProjectClient(endpoint=ENDPOINT, credential=credential)
        _openai_client = _project_client.get_openai_client()
    return _openai_client


# In-memory chat history per browser session.
# NOTE: this resets whenever the app restarts/scales, and does not share
# state across multiple instances. That's fine for a small internal HR tool.
# For production-grade persistence, swap this for a database or Redis.
conversations = {}
MAX_HISTORY_MESSAGES = 20


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    session_id = data.get("session_id") or str(uuid.uuid4())

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    history = conversations.get(session_id, [])
    history.append({"role": "user", "content": user_message})

    try:
        client = get_openai_client()
        response = client.responses.create(
            input=history,
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME,
                    "version": AGENT_VERSION,
                    "type": "agent_reference",
                }
            },
        )
        reply_text = response.output_text
        history.append({"role": "assistant", "content": reply_text})
        conversations[session_id] = history[-MAX_HISTORY_MESSAGES:]

        return jsonify({"reply": reply_text, "session_id": session_id})

    except Exception as exc:  # noqa: BLE001
        logger.exception("Error calling AI Foundry agent")
        return jsonify({"error": f"Agent call failed: {exc}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
