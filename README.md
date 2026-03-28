# FinSecure API

Internal payment processing and fraud detection API for FinSecure Corp.

## Stack
- Python 3.11
- FastAPI
- PostgreSQL

## Modules
- `src/auth.py` — JWT authentication and session management
- `src/payments.py` — Payment processing and validation
- `src/fraud.py` — Fraud detection rules engine
- `src/users.py` — User management and permissions

## Setup
```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## Testing
```bash
pytest tests/
```

---

> ⚠️ This repo has an open backlog of bugs and security issues being triaged.
