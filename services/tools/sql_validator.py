import re

ALLOWED_START = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE)\b",
    re.IGNORECASE,
)
DEFAULT_LIMIT = 100

class SQLValidationError(Exception):
    pass

def validate_and_cap(sql: str) -> str:
    sql = sql.strip().rstrip(";")

    if ";" in sql:
        raise SQLValidationError("Multiple statements not allowed.")
    if not ALLOWED_START.match(sql):
        raise SQLValidationError("Only SELECT statements allowed.")
    if FORBIDDEN.search(sql):
        raise SQLValidationError("Forbidden keyword detected. Only SELECT statements allowed")
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {DEFAULT_LIMIT}"
    
    return sql