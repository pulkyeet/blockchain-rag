# A defense layer for neo4j as it has no read-only DB role like postgres

import re

FORBIDDEN_KEYWORDS = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bDETACH\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bDROP\b",
    r"\bLOAD CSV\b",
    r"\bCALL\s*\{",
    r"apoc\.",
    r"\bGRANT\b",
    r"\bREVOKE\b",
]

ALLOWED_START = re.compile(
    r"^\s*(MATCH|OPTIONAL MATCH|WITH|UNWIND|RETURN)\b", re.IGNORECASE
)


class CypherValidationError(Exception):
    pass


def validate_cypher(query: str, default_limit: int = 100) -> str:
    """
    Returns a safe-to-run query (LIMIT appended if missing) or raises CypherValidationError.
    """
    stripped = query.strip().rstrip(";")

    if ";" in stripped:
        raise CypherValidationError("Multi-statement queries are not allowed.")

    if not ALLOWED_START.match(stripped):
        raise CypherValidationError(
            "Query must start with MATCH, OPTIONAL MATCH, WITH, or UNWIND (read-only)."
        )

    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, stripped, re.IGNORECASE):
            raise CypherValidationError(f"Forbidden keyword/pattern matched: {pattern}")

    if not re.search(r"\bLIMIT\s+\d+\b", stripped, re.IGNORECASE):
        stripped = f"{stripped}\nLIMIT {default_limit}"

    return stripped
