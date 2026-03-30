from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import threading
import time

app = Flask(__name__)
CORS(app)

DEVIN_API_KEY = os.environ.get("DEVIN_API_KEY", "")
DEVIN_ORG_ID  = os.environ.get("DEVIN_ORG_ID", "")
DEVIN_BASE    = f"https://api.devin.ai/v3/organizations/{DEVIN_ORG_ID}"

# In-memory store: { session_id: { issue_number, title, status, pr_url, session_url, created_at } }
sessions_store = {}

def devin_headers():
    return {
        "Authorization": f"Bearer {DEVIN_API_KEY}",
        "Content-Type": "application/json"
    }

def poll_session(session_id):
    """Background thread: polls Devin every 30s until session is done."""
    max_polls = 60  # 30 minutes max
    polls = 0
    while polls < max_polls:
        time.sleep(30)
        polls += 1
        try:
            res = requests.get(
                f"{DEVIN_BASE}/sessions/{session_id}",
                headers=devin_headers(),
                timeout=15
            )
            if not res.ok:
                continue
            data = res.json()
            status = data.get("status", data.get("state", "running"))
            session_url = data.get("url", f"https://app.devin.ai/sessions/{session_id}")

            # Try to find PR url in structured output
            pr_url = None
            structured = data.get("structured_output") or data.get("output") or {}
            if isinstance(structured, dict):
                pr_url = structured.get("pr_url") or structured.get("pull_request_url")
            # Also scan messages for github PR links
            if not pr_url:
                messages = data.get("messages") or []
                for msg in messages:
                    content = str(msg.get("content", ""))
                    if "github.com" in content and "/pull/" in content:
                        import re
                        match = re.search(r'https://github\.com/[^\s\)\"]+/pull/\d+', content)
                        if match:
                            pr_url = match.group(0)
                            break

            if session_id in sessions_store:
                sessions_store[session_id]["status"] = status
                sessions_store[session_id]["session_url"] = session_url
                if pr_url:
                    sessions_store[session_id]["pr_url"] = pr_url

            # Stop polling when terminal state
            if status in ["completed", "stopped", "blocked", "error", "failed"]:
                break
        except Exception as e:
            print(f"Poll error for {session_id}: {e}")
            continue

@app.route("/health")
def health():
    return jsonify({"status": "ok", "org": DEVIN_ORG_ID})

@app.route("/sessions", methods=["POST"])
def create_session():
    body = request.json or {}
    prompt = body.get("prompt", "")
    issue_number = body.get("issue_number")
    issue_title = body.get("issue_title", "")

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        res = requests.post(
            f"{DEVIN_BASE}/sessions",
            headers=devin_headers(),
            json={"prompt": prompt},
            timeout=15
        )
        data = res.json()
        if not res.ok:
            return jsonify(data), res.status_code

        session_id = data.get("session_id") or data.get("id")
        session_url = data.get("url") or (f"https://app.devin.ai/sessions/{session_id}" if session_id else None)

        if session_id:
            sessions_store[session_id] = {
                "session_id": session_id,
                "issue_number": issue_number,
                "issue_title": issue_title,
                "status": "running",
                "pr_url": None,
                "session_url": session_url,
                "created_at": time.time()
            }
            # Start background polling
            t = threading.Thread(target=poll_session, args=(session_id,), daemon=True)
            t.start()

        return jsonify({**data, "session_url": session_url}), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions", methods=["GET"])
def list_sessions():
    """Returns our enriched store merged with Devin API data."""
    try:
        res = requests.get(
            f"{DEVIN_BASE}/sessions",
            headers=devin_headers(),
            timeout=15
        )
        if not res.ok:
            return jsonify(res.json()), res.status_code

        devin_sessions = res.json()
        items = devin_sessions if isinstance(devin_sessions, list) else devin_sessions.get("sessions") or devin_sessions.get("items") or []

        # Merge with our local store for extra metadata
        enriched = []
        for s in items:
            sid = s.get("session_id") or s.get("id")
            local = sessions_store.get(sid, {})
            enriched.append({
                **s,
                "issue_number": local.get("issue_number"),
                "issue_title": local.get("issue_title") or s.get("title") or s.get("prompt", "")[:80],
                "pr_url": local.get("pr_url"),
                "session_url": local.get("session_url") or s.get("url") or (f"https://app.devin.ai/sessions/{sid}" if sid else None),
            })

        return jsonify({"sessions": enriched})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Returns live status for one session."""
    try:
        res = requests.get(
            f"{DEVIN_BASE}/sessions/{session_id}",
            headers=devin_headers(),
            timeout=15
        )
        data = res.json()
        local = sessions_store.get(session_id, {})

        # Scan for PR url if not already found
        pr_url = local.get("pr_url")
        if not pr_url:
            messages = data.get("messages") or []
            for msg in messages:
                content = str(msg.get("content", ""))
                if "github.com" in content and "/pull/" in content:
                    import re
                    match = re.search(r'https://github\.com/[^\s\)\"]+/pull/\d+', content)
                    if match:
                        pr_url = match.group(0)
                        if session_id in sessions_store:
                            sessions_store[session_id]["pr_url"] = pr_url
                        break

        return jsonify({
            **data,
            "issue_number": local.get("issue_number"),
            "issue_title": local.get("issue_title"),
            "pr_url": pr_url,
            "session_url": local.get("session_url") or data.get("url") or f"https://app.devin.ai/sessions/{session_id}",
        }), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
