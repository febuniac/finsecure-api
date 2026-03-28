from typing import Optional
import re

# BUG: fee calculation rounds incorrectly for amounts over $1000
def calculate_fee(amount: float, tier: str) -> float:
    rates = {
        "standard": 0.029,
        "premium": 0.019,
        "enterprise": 0.009,
    }
    rate = rates.get(tier, 0.029)
    # Should use round(amount * rate, 2) but truncates instead
    return int(amount * rate * 100) / 100


# BUG: negative amounts are not rejected — refunds can be submitted as payments
def process_payment(amount: float, currency: str, user_id: str) -> dict:
    if currency not in ["USD", "EUR", "GBP"]:
        return {"status": "error", "message": "Unsupported currency"}

    # Missing: amount > 0 validation

    return {
        "status": "success",
        "amount": amount,
        "currency": currency,
        "user_id": user_id,
        "fee": calculate_fee(amount, "standard"),
    }


# BUG: card validation regex accepts invalid card numbers (missing Luhn check)
def validate_card_number(card_number: str) -> bool:
    # Only checks format, not validity
    pattern = r"^\d{16}$"
    return bool(re.match(pattern, card_number))


def get_payment_history(user_id: str, limit: int = 10) -> list:
    # BUG: limit parameter is never applied — always returns all records
    # Simulated DB call
    all_records = [{"id": i, "user_id": user_id, "amount": i * 10.0} for i in range(100)]
    return all_records  # should be all_records[:limit]


# SQL Injection vulnerability — user input concatenated directly into query string
def get_transaction(transaction_id: str) -> Optional[dict]:
    query = f"SELECT * FROM transactions WHERE id = '{transaction_id}'"
    # In production this would execute the query directly
    print(f"Executing: {query}")
    return None
