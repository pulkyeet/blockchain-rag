import time

from neo4j import GraphDatabase
from openai import OpenAI

from config import settings
from shared.contracts import Tool, ToolName, ToolResult
from services.tools.cypher_validator import validate_cypher, CypherValidationError
from services.tools.graph_schema_context import GRAPH_SCHEMA_CONTEXT

NO_QUERY_POSSIBLE = "NO QUERY POSSIBLE"

SYSTEM_PROMPT = f"""
You translate natural language questions into read-only Cypher queries against a neo4j graph of Ethereum on-chain data.

{GRAPH_SCHEMA_CONTEXT}
Rules:
- Output ONLY the Cypher query, no explanation, no markdown fences, nothing extra.
- Only MATCH/OPTIMAL MATCH/WITH/UNWIND/RETURN classes. Never  CREATE/MERGE/DELETE/SET.
- If the question references a specific address, contract name or token that you cannot confirm exists in the schema context above or if the question cannot be answered with a graph traversal (e.g. it needs aggregation logic the graph doesn't support or is off-topic), out exactly this: {NO_QUERY_POSSIBLE}
- Do no invent addresses. Do not assume a name resolves to an address you weren't given.
- Always include a LIMIT.
"""


class GraphQueryTool(Tool):
    name = ToolName.GRAPH_QUERY

    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.llm = OpenAI(
            base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key
        )

    def _generate_cyper(self, question: str) -> str:
        response = self.llm.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
        )

        return response.choices[0].message.content.strip()

    def run(self, input: dict) -> ToolResult:
        start = time.time()
        question = input.get("question", "")

        try:
            raw_cypher = self._generate_cyper(question)

            if raw_cypher.strip() == NO_QUERY_POSSIBLE:
                return ToolResult(
                    tool=self.name,
                    output=None,
                    error="Could not resolve a valid graph query for this question (unresolved entity of unsupported type)",
                    latency_ms=(time.time() - start) * 1000,
                )
            safe_cypher = validate_cypher(raw_cypher)

            with self.driver.session() as session:
                result = session.run(safe_cypher)
                records = [record.data() for record in result]

                return ToolResult(
                    tool=self.name,
                    output={"cypher": safe_cypher, "rows": records},
                    error=None,
                    latency_ms=(time.time() - start) * 1000,
                )
        except CypherValidationError as e:
            return ToolResult(
                tool=self.name,
                output=None,
                error=f"Validation rejected: {e}",
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(
                tool=self.name,
                output=None,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )
