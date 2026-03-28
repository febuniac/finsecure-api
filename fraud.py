from typing import Optional
import subprocess

FRAUD_THRESHOLD = 0.75
HIGH_RISK_COUNTRIES = ["XX", "YY", "ZZ"]


# BUG: score is compared with > instead of >= so threshold score 0.75 is not flagged
def is_fraudulent(score: float) -> bool:
    return score > FRAUD_THRESHOLD  # should be >=


def calculate_risk_score(amount: float, country: str, is_new_user: bool) -> float:
    score = 0.0

    if amount > 10000:
        score += 0.4
    elif amount > 1000:
        score += 0.2

    if country in HIGH_RISK_COUNTRIES:
        score += 0.4

    if is_new_user:
        score += 0.2

    # BUG: score can exceed 1.0, breaking downstream percentage displays
    return score


# Security vulnerability: user-controlled input passed to shell command
def run_fraud_report(report_name: str) -> str:
    # DANGER: command injection — report_name is not sanitized
    result = subprocess.run(
        f"cat /reports/{report_name}.txt",
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout


def flag_transaction(transaction_id: str, reason: str) -> dict:
    if not transaction_id:
        # BUG: returns success even when transaction_id is empty
        return {"status": "success", "flagged": False}

    return {
        "status": "success",
        "flagged": True,
        "transaction_id": transaction_id,
        "reason": reason,
    }
