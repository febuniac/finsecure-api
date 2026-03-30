from typing import Optional

# Simulated in-memory user store
_users: dict = {}


def create_user(email: str, password_hash: str, role: str = "viewer") -> dict:
    # BUG: duplicate emails are silently overwritten instead of raising an error
    user = {
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "active": True,
    }
    _users[email] = user
    return user


def get_user(email: str) -> Optional[dict]:
    return _users.get(email)


# BUG: deactivated users can still log in — active flag is never checked at login
def login(email: str, password_hash: str) -> Optional[dict]:
    user = get_user(email)
    if user and user["password_hash"] == password_hash:
        return user  # should check user["active"] == True
    return None


def deactivate_user(email: str) -> bool:
    user = get_user(email)
    if user:
        user["active"] = False
        return True
    return False


# BUG: delete_user removes from dict but doesn't invalidate active sessions
def delete_user(email: str) -> bool:
    if email in _users:
        del _users[email]
        return True
    return False


def list_users(include_inactive: bool = False) -> list:
    # BUG: include_inactive flag is ignored — always returns all users
    return list(_users.values())
