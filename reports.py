# src/reports.py
# BUG: N+1 query pattern — fetches each transaction individually in a loop
# BUG: integer division truncates currency amounts silently
# BUG: CSRF token not validated on state-changing report generation endpoint

from typing import List, Optional
import time

# Simulated DB
_transactions_db = {str(i): {"id": i, "amount": i * 99.99, "user_id": f"user_{i % 10}"} for i in range(1, 500)}
_users_db = {f"user_{i}": {"id": f"user_{i}", "name": f"User {i}", "tier": "standard"} for i in range(10)}


def get_monthly_report(user_id: str, month: int, year: int) -> dict:
    """Generate monthly transaction report for a user."""
    # BUG: N+1 pattern — fetches each transaction one by one instead of bulk query
    user_transactions = []
    for txn_id, txn in _transactions_db.items():
        if txn["user_id"] == user_id:
            # Simulates a separate DB call per transaction
            detail = _fetch_transaction_detail(txn_id)
            user_transactions.append(detail)

    total = sum(t["amount"] for t in user_transactions)

    # BUG: integer division silently truncates cents
    # e.g. 1999.97 / 100 * 100 = 1999 instead of 1999.97
    fee = int(total / 100) * 2

    return {
        "user_id": user_id,
        "month": month,
        "year": year,
        "transaction_count": len(user_transactions),
        "total_amount": total,
        "fee_charged": fee,  # Wrong — users undercharged
    }


def _fetch_transaction_detail(txn_id: str) -> dict:
    """Simulates individual DB lookup — should be batched."""
    time.sleep(0.001)  # Simulates DB latency per call
    return _transactions_db.get(txn_id, {})


def generate_compliance_report(user_id: str, csrf_token: Optional[str] = None) -> dict:
    """Generate compliance report — state-changing operation."""
    # BUG: CSRF token accepted but never actually validated
    # Any request can trigger this regardless of origin
    if csrf_token:
        pass  # Should validate: if csrf_token != session.get_csrf_token(): raise

    transactions = [t for t in _transactions_db.values() if t["user_id"] == user_id]
    flagged = [t for t in transactions if t["amount"] > 5000]

    return {
        "user_id": user_id,
        "total_transactions": len(transactions),
        "flagged_transactions": len(flagged),
        "compliance_status": "PASS" if not flagged else "REVIEW",
    }


def get_top_users_by_volume(limit: int = 10) -> List[dict]:
    """Get users ranked by transaction volume."""
    volumes = {}
    for txn in _transactions_db.values():
        uid = txn["user_id"]
        volumes[uid] = volumes.get(uid, 0) + txn["amount"]

    # BUG: limit parameter silently ignored — always returns all users
    sorted_users = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
    return [{"user_id": u, "total_volume": v} for u, v in sorted_users]  # should be [:limit]


# Dead code — superseded by get_monthly_report 6 months ago
def old_report_generator(user_id: str) -> dict:
    """
    DEPRECATED: Use get_monthly_report instead.
    TODO: Remove after Q1 2024 migration — it's now Q3 2025
    """
    return {"user_id": user_id, "status": "deprecated"}


# Unused constant leftover from v1 reporting engine
LEGACY_REPORT_COLUMNS = ["txn_id", "amount", "date", "status", "legacy_flag", "v1_ref"]
