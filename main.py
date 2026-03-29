from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

DEVIN_API_KEY = os.environ.get("DEVIN_API_KEY", "")
DEVIN_ORG_ID  = os.environ.get("DEVIN_ORG_ID", "")
DEVIN_BASE    = f"https://api.devin.ai/v3/organizations/{DEVIN_ORG_ID}"

def devin_headers():
    return {
        "Authorization": f"Bearer {DEVIN_API_KEY}",
        "Content-Type": "application/json"
    }

@app.route("/health")
def health():
    return jsonify({"status": "ok", "org": DEVIN_ORG_ID})

@app.route("/sessions", methods=["POST"])
def create_session():
    body = request.json or {}
    prompt = body.get("prompt", "")
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    try:
        res = requests.post(
            f"{DEVIN_BASE}/sessions",
            headers=devin_headers(),
            json={"prompt": prompt},
            timeout=15
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions", methods=["GET"])
def list_sessions():
    try:
        res = requests.get(
            f"{DEVIN_BASE}/sessions",
            headers=devin_headers(),
            timeout=15
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    try:
        res = requests.get(
            f"{DEVIN_BASE}/sessions/{session_id}",
            headers=devin_headers(),
            timeout=15
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
