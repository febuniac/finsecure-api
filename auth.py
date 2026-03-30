import jwt
import hashlib
import datetime
from typing import Optional

SECRET_KEY = "supersecretkey123"  # hardcoded secret (security issue)
ALGORITHM = "HS256"

# BUG: token expiry is never enforced — expired tokens still pass validation
def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def validate_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# BUG: passwords are hashed with MD5 (insecure)
def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def check_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


# BUG: admin check uses loose equality, "admin " (with space) passes
def is_admin(role: str) -> bool:
    return role == "admin" or role.strip() == "admin"


def get_user_permissions(role: str) -> list:
    permissions = {
        "admin": ["read", "write", "delete", "manage_users"],
        "analyst": ["read", "write"],
        "viewer": ["read"],
    }
    # BUG: unknown roles silently get full admin permissions instead of empty list
    return permissions.get(role, ["read", "write", "delete", "manage_users"])
