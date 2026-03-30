from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import threading
import time
import re

app = Flask(__name__)
CORS(app)

DEVIN_API_KEY    = os.environ.get("DEVIN_API_KEY", "")
DEVIN_ORG_ID     = os.environ.get("DEVIN_ORG_ID", "")
DEVIN_BASE       = f"https://api.devin.ai/v3/organizations/{DEVIN_ORG_ID}"
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
NOTIFY_EMAIL     = os.environ.get("NOTIFY_EMAIL", "")
FROM_EMAIL       = os.environ.get("FROM_EMAIL", "noreply@finsecure.app")

sessions_store = {}
# { "owner/repo": set of issue numbers already seen }
known_security_issues = {}

def devin_headers():
    return {"Authorization": f"Bearer {DEVIN_API_KEY}", "Content-Type": "application/json"}

# ── EMAIL ──────────────────────────────────────────────────────────────────────

def send_email(subject, html_body, to_email=None):
    to = to_email or NOTIFY_EMAIL
    if not SENDGRID_API_KEY or not to:
        print(f"[email skipped] {subject}")
        return
    try:
        res = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": FROM_EMAIL, "name": "Backlog Resolver"},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}]
            },
            timeout=10
        )
        print(f"[email] {res.status_code} → {subject}")
    except Exception as e:
        print(f"[email error] {e}")

def _wrap(content, accent_color="#4a9eff"):
    return f"""
<div style="font-family:'Helvetica Neue',Arial,sans-serif;max-width:580px;margin:0 auto;background:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb">
  <div style="background:#0e0f11;padding:20px 28px;display:flex;align-items:center;gap:10px">
    <span style="font-family:monospace;color:{accent_color};font-size:12px;letter-spacing:0.1em;text-transform:uppercase">✦ backlog resolver</span>
  </div>
  <div style="padding:28px">
    {content}
  </div>
  <div style="padding:14px 28px;background:#f9fafb;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;font-family:monospace">
    Sent by Backlog Resolver · powered by Devin
  </div>
</div>"""

def notify_pr_opened(issue_number, issue_title, pr_url, session_url, repo, to_email=None):
    content = f"""
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:12px 16px;margin-bottom:20px">
  <span style="color:#16a34a;font-size:13px;font-family:monospace;font-weight:500">✓ PR opened — ready for review</span>
</div>
<h2 style="color:#111827;font-size:18px;font-weight:600;margin:0 0 8px">Devin fixed issue #{issue_number}</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 20px">A pull request was automatically opened for the issue below.</p>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:14px 16px;margin-bottom:24px">
  <div style="font-size:11px;color:#9ca3af;font-family:monospace;margin-bottom:4px">{repo}</div>
  <div style="font-size:14px;color:#111827;font-weight:500">#{issue_number} {issue_title}</div>
</div>
<div style="display:flex;gap:12px;flex-wrap:wrap">
  <a href="{pr_url}" style="display:inline-block;background:#16a34a;color:#ffffff;padding:11px 22px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:500">Review PR →</a>
  <a href="{session_url}" style="display:inline-block;background:#f3f4f6;color:#374151;padding:11px 22px;border-radius:6px;text-decoration:none;font-size:14px">View Devin session</a>
</div>"""
    send_email(f"[Backlog Resolver] PR opened for issue #{issue_number} — {repo}", _wrap(content, "#16a34a"), to_email)

def notify_blocked(issue_number, issue_title, session_url, repo, to_email=None):
    content = f"""
<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:12px 16px;margin-bottom:20px">
  <span style="color:#d97706;font-size:13px;font-family:monospace;font-weight:500">⚠ Devin is blocked — action required</span>
</div>
<h2 style="color:#111827;font-size:18px;font-weight:600;margin:0 0 8px">Devin needs your input</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 20px">Devin ran into something it can't resolve on its own. Open the session to unblock it.</p>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:14px 16px;margin-bottom:24px">
  <div style="font-size:11px;color:#9ca3af;font-family:monospace;margin-bottom:4px">{repo}</div>
  <div style="font-size:14px;color:#111827;font-weight:500">#{issue_number} {issue_title}</div>
</div>
<a href="{session_url}" style="display:inline-block;background:#d97706;color:#ffffff;padding:11px 22px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:500">Open session and unblock →</a>"""
    send_email(f"[Backlog Resolver] Devin needs input on issue #{issue_number} — {repo}", _wrap(content, "#d97706"), to_email)

def notify_new_security_issue(issue_number, issue_title, issue_url, labels, repo, to_email=None):
    label_badges = "".join([
        f'<span style="display:inline-block;background:#fef2f2;color:#dc2626;border:1px solid #fecaca;border-radius:4px;font-size:11px;font-family:monospace;padding:2px 8px;margin-right:6px">{l}</span>'
        for l in labels
    ])
    content = f"""
<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:12px 16px;margin-bottom:20px">
  <span style="color:#dc2626;font-size:13px;font-family:monospace;font-weight:500">🔴 New security issue detected</span>
</div>
<h2 style="color:#111827;font-size:18px;font-weight:600;margin:0 0 8px">Security alert in {repo}</h2>
<p style="color:#6b7280;font-size:14px;margin:0 0 20px">A new issue with security labels was opened. Review it and decide whether to send it to Devin.</p>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:14px 16px;margin-bottom:16px">
  <div style="font-size:11px;color:#9ca3af;font-family:monospace;margin-bottom:6px">{repo} · #{issue_number}</div>
  <div style="font-size:14px;color:#111827;font-weight:500;margin-bottom:10px">{issue_title}</div>
  <div>{label_badges}</div>
</div>
<a href="{issue_url}" style="display:inline-block;background:#dc2626;color:#ffffff;padding:11px 22px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:500">View issue →</a>"""
    send_email(f"[Backlog Resolver] 🔴 New security issue #{issue_number} — {repo}", _wrap(content, "#dc2626"), to_email)

# ── POLLING ────────────────────────────────────────────────────────────────────

def poll_session(session_id, repo=None):
    max_polls = 60
    polls = 0
    notified_pr = False

    while polls < max_polls:
        time.sleep(30)
        polls += 1
        try:
            res = requests.get(f"{DEVIN_BASE}/sessions/{session_id}", headers=devin_headers(), timeout=15)
            if not res.ok:
                continue
            data = res.json()
            status = data.get("status", data.get("state", "running"))
            session_url = data.get("url", f"https://app.devin.ai/sessions/{session_id}")
            local = sessions_store.get(session_id, {})
            issue_number = local.get("issue_number", "?")
            issue_title = local.get("issue_title", "unknown issue")
            to_email = local.get("notify_email") or NOTIFY_EMAIL
            repo_name = repo or local.get("repo", "unknown/repo")

            # Find PR url
            pr_url = local.get("pr_url")
            if not pr_url:
                for msg in (data.get("messages") or []):
                    content = str(msg.get("content", ""))
                    if "github.com" in content and "/pull/" in content:
                        match = re.search(r'https://github\.com/[^\s\)\"]+/pull/\d+', content)
                        if match:
                            pr_url = match.group(0)
                            break
                structured = data.get("structured_output") or data.get("output") or {}
                if isinstance(structured, dict):
                    pr_url = pr_url or structured.get("pr_url") or structured.get("pull_request_url")

            if session_id in sessions_store:
                sessions_store[session_id]["status"] = status
                sessions_store[session_id]["session_url"] = session_url
                if pr_url:
                    sessions_store[session_id]["pr_url"] = pr_url

            if pr_url and not notified_pr:
                notify_pr_opened(issue_number, issue_title, pr_url, session_url, repo_name, to_email)
                notified_pr = True

            if status == "blocked":
                notify_blocked(issue_number, issue_title, session_url, repo_name, to_email)
                break
            if status in ["completed", "stopped", "error", "failed"]:
                break

        except Exception as e:
            print(f"[poll error] {session_id}: {e}")

# ── SECURITY MONITOR ───────────────────────────────────────────────────────────

SECURITY_LABELS = {"security", "codeql", "vulnerability", "CVE", "injection", "xss", "sqli"}

def check_new_security_issues(repo, to_email=None):
    """Fetch latest issues and notify if new security ones appear."""
    try:
        res = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            params={"state": "open", "per_page": 30, "sort": "created", "direction": "desc"},
            timeout=15
        )
        if not res.ok:
            return
        issues = res.json()
        seen = known_security_issues.get(repo, set())
        new_seen = set(seen)

        for issue in issues:
            num = issue["number"]
            if issue.get("pull_request"):
                continue
            labels = [l["name"].lower() for l in issue.get("labels", [])]
            is_security = any(sl in label for sl in SECURITY_LABELS for label in labels)
            if is_security and num not in seen:
                notify_new_security_issue(
                    num, issue["title"], issue["html_url"],
                    [l["name"] for l in issue.get("labels", [])],
                    repo, to_email
                )
                new_seen.add(num)

        known_security_issues[repo] = new_seen
    except Exception as e:
        print(f"[security monitor error] {repo}: {e}")

def security_monitor_loop():
    """Runs every hour, checks all watched repos."""
    while True:
        time.sleep(3600)
        repos = list(known_security_issues.keys())
        for repo in repos:
            print(f"[security monitor] checking {repo}")
            check_new_security_issues(repo)

# Start monitor thread
threading.Thread(target=security_monitor_loop, daemon=True).start()

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "org": DEVIN_ORG_ID, "monitored_repos": list(known_security_issues.keys())})

@app.route("/watch", methods=["POST"])
def watch_repo():
    """Register a repo for security monitoring."""
    body = request.json or {}
    repo = body.get("repo", "")
    to_email = body.get("notify_email", "")
    if not repo:
        return jsonify({"error": "repo is required"}), 400
    if repo not in known_security_issues:
        known_security_issues[repo] = set()
        # Do an initial scan to seed known issues (no notifications on first run)
        try:
            res = requests.get(f"https://api.github.com/repos/{repo}/issues", params={"state":"open","per_page":50}, timeout=15)
            if res.ok:
                issues = res.json()
                seen = set()
                for i in issues:
                    labels = [l["name"].lower() for l in i.get("labels", [])]
                    if any(sl in label for sl in SECURITY_LABELS for label in labels):
                        seen.add(i["number"])
                known_security_issues[repo] = seen
        except: pass
    return jsonify({"status": "watching", "repo": repo, "known_security_issues": len(known_security_issues.get(repo, set()))})

@app.route("/sessions", methods=["POST"])
def create_session():
    body = request.json or {}
    prompt = body.get("prompt", "")
    issue_number = body.get("issue_number")
    issue_title = body.get("issue_title", "")
    repo = body.get("repo", "")
    notify_email = body.get("notify_email", "")

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        res = requests.post(f"{DEVIN_BASE}/sessions", headers=devin_headers(), json={"prompt": prompt}, timeout=15)
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
                "repo": repo,
                "notify_email": notify_email,
                "status": "running",
                "pr_url": None,
                "session_url": session_url,
                "created_at": time.time()
            }
            threading.Thread(target=poll_session, args=(session_id, repo), daemon=True).start()

        return jsonify({**data, "session_url": session_url}), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions", methods=["GET"])
def list_sessions():
    try:
        res = requests.get(f"{DEVIN_BASE}/sessions", headers=devin_headers(), timeout=15)
        if not res.ok:
            return jsonify(res.json()), res.status_code
        raw = res.json()
        items = raw if isinstance(raw, list) else raw.get("sessions") or raw.get("items") or []
        enriched = []
        for s in items:
            sid = s.get("session_id") or s.get("id")
            local = sessions_store.get(sid, {})
            enriched.append({
                **s,
                "issue_number": local.get("issue_number"),
                "issue_title": local.get("issue_title") or s.get("title") or s.get("prompt","")[:80],
                "pr_url": local.get("pr_url"),
                "session_url": local.get("session_url") or s.get("url") or (f"https://app.devin.ai/sessions/{sid}" if sid else None),
                "repo": local.get("repo"),
            })
        return jsonify({"sessions": enriched})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    try:
        res = requests.get(f"{DEVIN_BASE}/sessions/{session_id}", headers=devin_headers(), timeout=15)
        data = res.json()
        local = sessions_store.get(session_id, {})
        pr_url = local.get("pr_url")
        if not pr_url:
            for msg in (data.get("messages") or []):
                content = str(msg.get("content", ""))
                if "github.com" in content and "/pull/" in content:
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
            "repo": local.get("repo"),
        }), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
