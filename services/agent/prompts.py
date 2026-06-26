"""Tool catalog + Prompt building for the raw ReAct loop"""

import json

TOOL_CATALOG = """You have access to these tools. Call exactly one per step.

1. vector_retrieval — unstructured docs: Solidity concepts, OpenZeppelin, vulnerability
   classes, audit reports, protocol whitepapers. Use for "what is/explain/how does X work"
   questions about code or concepts, NOT for on-chain data.
   Example: {"action": "vector_retrieval", "action_input": {"question": "what is a reentrancy attack"}}

2. text_to_sql — tabular aggregation over on-chain Ethereum data (addresses, contracts,
   transactions, token_transfers). Use for totals, counts, volume, "how many/how much".
   Example: {"action": "text_to_sql", "action_input": {"question": "total USDC volume through Uniswap V2 in the dataset"}}

3. graph_query — multi-hop relationships over the same on-chain data (who interacted with
   whom, transaction paths). Use for "what did wallet X do", "what contracts did X talk to".
   Example: {"action": "graph_query", "action_input": {"question": "what contracts did 0xabc... send transactions to"}}

4. finish — you have enough to answer, or no tool can help.
   Example: {"action": "finish", "action_input": {"answer": "Uniswap V2 alone accounted for ~84% of tracked router volume in the dataset."}}

If a question needs on-chain data AND a concept explanation, call one tool at a time and
chain them across steps — do not try to answer both halves in one call.
"""

SYSTEM_PROMPT = f"""You are a ReAct agent answering questions about Ethereum smart contracts
and on-chain activity. At each step, respond with EXACTLY ONE JSON object, nothing else —
no markdown fences, no explanation outside the JSON.

Format: {{"thought": "...", "action": "<tool name>", "action_input": {{...}}}}

{TOOL_CATALOG}

Rules:
- Output ONLY the JSON object. No text before or after it.
- "action" must be exactly one of: vector_retrieval, text_to_sql, graph_query, finish.
- Never invent data. If a tool returns an error, read it and decide: retry with fixed
  input, switch tools, or finish with what you have.
- Use the conversation scratchpad below to see what you've already tried.
"""

REPAIR_SUFFIX = """

Your previous response was not valid JSON or was missing required fields.
Respond with EXACTLY ONE JSON object in this exact shape, nothing else:
{"thought": "...", "action": "<tool name>", "action_input": {...}}
"""

SYNTH_PROMPT_TEMPLATE = """You are answering a question but ran out of steps/budget before
finishing normally. Using ONLY the information gathered below, give the best possible answer.
Prefix nothing — just answer directly. If the gathered info is insufficient, say so plainly.

Original question: {query}

Gathered information:
{scratchpad}
"""

def _format_scratchpad(state) -> str:
    """Render AgentState.history as a flat transcript for a the prompt."""
    lines = []
    for entry in state.history:
        if entry["role"] == "assistant":
            a = entry["action"]
            lines.append(
                f"Thought: {a.get('thought', '')}\n"
                f"Action: {a['action']}({json.dumps(a.get('action_input', {}))})"
            )
        elif entry["role"] == "observation":
            lines.append(f"Observation: {entry['content']}")
    return "\n".join(lines) if lines else "(nothing tried yet)"

def build_prompt(state) -> list[dict]:
    scratchpad = _format_scratchpad(state)
    user_content = f"Question: {state.query}\n\nScratchpad so far:\n {scratchpad}\n\nWhat's your next step?"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

def build_synth_prompt(state) -> list[dict]:
    scratchpad = _format_scratchpad(state)
    return [
        {"role": "user", "content": SYNTH_PROMPT_TEMPLATE.format(query=state.query, scratchpad=scratchpad)}
    ]