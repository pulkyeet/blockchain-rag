from typing import Any
import time
import psycopg
from openai import OpenAI
from shared.contracts import Tool, ToolName, ToolResult
from services.tools.schema_context import ONCHAIN_SCHEMA
from services.tools.sql_validator import validate_and_cap, SQLValidationError
from config import settings

SYSTEM_PROMPT = f"""You convert questions about on-chain Ethereum data into a single PostgreSQL SELECT query.

Schema: {ONCHAIN_SCHEMA}

Rules:
- Output ONLY the SQL query, no explanation, no markdown fences.
- Use only the tables/columns listed above.
- Always include a LIMIT clause.
- Do not invent, guess, or hardcode any address. Only use addresses that appear literally in the user's question.
- If the question requires information not present in the schema (e.g. resolving a name to an address, price data, off-chain identity), respond with exactly: NO_QUERY_POSSIBLE
"""


class TextToSQLTool(Tool):
    name = ToolName.TEXT_TO_SQL

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url
        )

    def _generate_sql(self, question: str) -> str:
        response = self.client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            max_tokens=420,
        )
        return response.choices[0].message.content.strip()

    def run(self, input: dict[str, Any]) -> ToolResult:
        start = time.time()
        question = input["query"]

        try:
            raw_sql = self._generate_sql(question)
            if raw_sql.strip() == "NO_QUERY_POSSIBLE":
                return ToolResult(
                    tool=self.name,
                    output=None,
                    error="question not answerable from on-chain schema",
                    latency_ms=(time.time() - start) * 1000,
                )
            safe_sql = validate_and_cap(raw_sql)

            with psycopg.connect(settings.postgres_readonly_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(safe_sql)
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    result = [dict(zip(columns, row)) for row in rows]

            return ToolResult(
                tool=self.name,
                output={"sql": safe_sql, "rows": result},
                latency_ms=(time.time() - start) * 1000,
            )
        except SQLValidationError as e:
            return ToolResult(
                tool=self.name,
                output=None,
                error=f"unsafe SQL rejected: {e}",
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(
                tool=self.name,
                output=None,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )
