from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

DEVIN_API_KEY = os.environ.get("DEVIN_API_KEY", "")
DEVIN_ORG_ID  = os.environ.get("DEVIN_ORG_ID", "")
DEVIN_BASE    = f"https://api.devin.ai/v3/organizations/{DEVIN_ORG_ID}"

def headers():
    return {"Authorization": f"Bearer {DEVIN_API_KEY}", "Content-Type": "application/json"}

@app.route("/health")
def health():
    return jsonify({"status": "ok", "org": DEVIN_ORG_ID})

@app.route("/sessions", methods=["POST"])
def create_session():
    body = request.json or {}
    prompt = body.get("prompt", "")
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    res = requests.post(f"{DEVIN_BASE}/sessions", headers=headers(), json={"prompt": prompt}, timeout=15)
    return jsonify(res.json()), res.status_code

@app.route("/sessions", methods=["GET"])
def list_sessions():
    res = requests.get(f"{DEVIN_BASE}/sessions", headers=headers(), timeout=15)
    return jsonify(res.json()), res.status_code

@app.route("/sessions/<sid>", methods=["GET"])
def get_session(sid):
    res = requests.get(f"{DEVIN_BASE}/sessions/{sid}", headers=headers(), timeout=15)
    return jsonify(res.json()), res.status_code
