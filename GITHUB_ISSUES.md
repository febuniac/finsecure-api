# ISSUES TO CREATE ON GITHUB
# Copy each block below as a separate GitHub Issue

---

## ISSUE 1
Title: [BUG] Expired JWT tokens are still accepted as valid

Labels: bug, security, priority:high

Body:
## Description
The `validate_token()` function in `src/auth.py` disables expiration verification entirely.
This means a token issued months ago is still accepted as valid, allowing stale or stolen
tokens to authenticate indefinitely.

## Steps to reproduce
1. Generate a token with `create_token()`
2. Wait for it to expire (1 hour)
3. Call `validate_token()` with the expired token
4. Observe it returns a valid payload instead of `None`

## Expected behavior
Expired tokens should return `None` and the request should be rejected with 401.

## File
`src/auth.py` — line 17, `options={"verify_exp": False}`

---

## ISSUE 2
Title: [BUG] Payment history ignores the `limit` parameter — always returns all 100 records

Labels: bug, performance, priority:medium

Body:
## Description
`get_payment_history()` in `src/payments.py` accepts a `limit` parameter but never applies it.
It always returns all records from the simulated database. In production, this causes heavy
queries and timeouts for users with large transaction histories.

## Steps to reproduce
1. Call `get_payment_history(user_id="user_1", limit=5)`
2. Observe that 100 records are returned instead of 5

## Expected behavior
Should return at most `limit` records.

## File
`src/payments.py` — line 33, `return all_records` should be `return all_records[:limit]`

---

## ISSUE 3
Title: [BUG] Fraud score can exceed 1.0 — breaks risk percentage display on dashboard

Labels: bug, priority:medium

Body:
## Description
`calculate_risk_score()` in `src/fraud.py` accumulates score components without capping the result.
A transaction from a high-risk country, over $10k, by a new user scores 1.0 + overflow.
The frontend dashboard interprets this as a percentage and displays ">100% risk", breaking the UI.

## Steps to reproduce
```python
score = calculate_risk_score(amount=15000, country="XX", is_new_user=True)
print(score)  # returns 1.0, but other combinations can return values above 1.0
```

## Expected behavior
Score should be capped at 1.0: `return min(score, 1.0)`

## File
`src/fraud.py` — `calculate_risk_score()` return value

---

## ISSUE 4 — SECURITY (CodeQL equivalent)
Title: [SECURITY] SQL Injection in `get_transaction()` — user input concatenated into query

Labels: security, codeql, priority:critical

Body:
## Description
`get_transaction()` in `src/payments.py` builds a SQL query by directly concatenating
the `transaction_id` parameter. An attacker can pass a crafted string to extract
or destroy database records.

## Vulnerable code
```python
query = f"SELECT * FROM transactions WHERE id = '{transaction_id}'"
```

## Attack example
```
transaction_id = "' OR '1'='1"
# Results in: SELECT * FROM transactions WHERE id = '' OR '1'='1'
```

## Fix
Use parameterized queries:
```python
query = "SELECT * FROM transactions WHERE id = %s"
cursor.execute(query, (transaction_id,))
```

## File
`src/payments.py` — `get_transaction()`, line 38

## CodeQL Rule
`python/sql-injection`

---

## ISSUE 5 — SECURITY (CodeQL equivalent)
Title: [SECURITY] Command injection in `run_fraud_report()` — shell=True with unsanitized input

Labels: security, codeql, priority:critical

Body:
## Description
`run_fraud_report()` in `src/fraud.py` passes user-controlled `report_name` directly
to a shell command using `subprocess.run(..., shell=True)`. This allows arbitrary
command execution on the server.

## Vulnerable code
```python
result = subprocess.run(
    f"cat /reports/{report_name}.txt",
    shell=True,
    ...
)
```

## Attack example
```
report_name = "x; rm -rf /reports"
# Executes: cat /reports/x; rm -rf /reports.txt
```

## Fix
Sanitize input and avoid `shell=True`:
```python
import shlex
safe_name = shlex.quote(report_name)
result = subprocess.run(["cat", f"/reports/{safe_name}.txt"], capture_output=True)
```

## File
`src/fraud.py` — `run_fraud_report()`, line 23

## CodeQL Rule
`python/command-injection`

---

## ISSUE 6 — SECURITY (CodeQL equivalent)
Title: [SECURITY] Passwords hashed with MD5 — must migrate to bcrypt

Labels: security, codeql, priority:high

Body:
## Description
`hash_password()` in `src/auth.py` uses MD5 to hash passwords. MD5 is cryptographically
broken and trivially reversible using rainbow tables. This puts all user credentials at
risk in the event of a database breach.

## Vulnerable code
```python
def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()
```

## Fix
Replace with bcrypt:
```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

## File
`src/auth.py` — `hash_password()`, line 22

## CodeQL Rule
`python/weak-cryptographic-algorithm`
