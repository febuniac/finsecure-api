import pytest
from src.auth import validate_token, create_token, hash_password, get_user_permissions
from src.payments import calculate_fee, process_payment, get_payment_history
from src.fraud import calculate_risk_score, is_fraudulent, flag_transaction
from src.users import create_user, login, deactivate_user, list_users


# --- auth tests ---

def test_expired_token_should_be_rejected():
    token = create_token("user_1", "viewer")
    # This test FAILS because verify_exp is disabled
    import jwt, datetime
    expired_payload = {"user_id": "user_1", "role": "viewer", "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=2)}
    expired_token = jwt.encode(expired_payload, "supersecretkey123", algorithm="HS256")
    result = validate_token(expired_token)
    assert result is None, "Expired token should not be valid"


def test_unknown_role_should_have_no_permissions():
    perms = get_user_permissions("hacker")
    assert perms == [], "Unknown roles should get empty permissions"


# --- payments tests ---

def test_payment_limit_is_applied():
    history = get_payment_history("user_1", limit=5)
    assert len(history) == 5, f"Expected 5 records, got {len(history)}"


def test_negative_payment_should_be_rejected():
    result = process_payment(-100.0, "USD", "user_1")
    assert result["status"] == "error", "Negative amounts should be rejected"


def test_fee_calculation_large_amount():
    fee = calculate_fee(1000.0, "standard")
    assert fee == 29.0, f"Expected 29.0, got {fee}"


# --- fraud tests ---

def test_fraud_score_capped_at_one():
    score = calculate_risk_score(15000, "XX", True)
    assert score <= 1.0, f"Score should be capped at 1.0, got {score}"


def test_threshold_score_is_flagged():
    assert is_fraudulent(0.75) == True, "Score of exactly 0.75 should be flagged"


# --- users tests ---

def test_inactive_user_cannot_login():
    create_user("test@example.com", "hashedpw", "viewer")
    deactivate_user("test@example.com")
    result = login("test@example.com", "hashedpw")
    assert result is None, "Deactivated users should not be able to login"


def test_list_users_respects_include_inactive():
    create_user("active@example.com", "hash1", "viewer")
    create_user("inactive@example.com", "hash2", "viewer")
    deactivate_user("inactive@example.com")
    active_only = list_users(include_inactive=False)
    assert all(u["active"] for u in active_only), "Should only return active users"
