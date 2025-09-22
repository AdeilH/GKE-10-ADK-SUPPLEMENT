import os
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# --- Configure and create the ADK-provided application ---
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- DATABASE PATH (FIXED) ---
# The session database will now be written to the persistent volume mounted at /data.
# This prevents the application from crashing and ensures session data persists.
SESSION_SERVICE_URI = "sqlite:///./data/sessions.db"
ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True

# Call the function to get the ADK FastAPI app instance.
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

# --- HEALTH CHECK ---
# This endpoint lives at /_healthz to satisfy the GKE Load Balancer (via BackendConfig)
# and the Kubernetes probes (readinessProbe/livenessProbe).
@app.get("/_healthz")
def health_check():
    """Health check for Kubernetes probes and the GKE Ingress."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

