"""Design Rule: reason/act/synthesize are pure AgentState -> AgentState transformations. ALL loop-control logic lives in should_continue() and run()."""

import json
import re
import time

from shared.contracts import AgentState, ToolName, Tool, ToolResult
from services.agent.prompts import build_prompt, build_synth_prompt, REPAIR_SUFFIX

MAX_ITERATIONS = 6
TOKEN_BUDGET = 10000

VALID_ACTORS = {"vector_retrieval", "text_to_sql", "graph_query", "finish"}

INPUT_KEY_OVERRIDES = {
    ToolName.TEXT_TO_SQL: "query",
}


class ReActAgent:
    def __init__(self, tools: dict[ToolName, Tool], llm_client, model: str):
        self.tools = tools
        self.llm = llm_client
        self.model = model

    # LLM call
    def _complete(self, messages: list[dict]) -> tuple[str, int]:
        response = self.llm.chat.completions.create(
            model=self.model, messages=messages, temperature=0
        )
        text = response.choices[0].message.content.strip()
        tokens = getattr(response, "usage", None)
        token_count = (
            tokens.total_tokens if tokens else _estimate_tokens(messages, text)
        )
        return text, token_count

    # Nodes (AgentState -> AgentState)
    def reason(self, state: AgentState) -> AgentState:
        messages = build_prompt(state)
        raw, tok = self._complete(messages)
        state.total_tokens += tok

        action = _parse_action(raw)
        if action is None:
            repaired_messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": REPAIR_SUFFIX},
            ]
            raw2, tok2 = self._complete(repaired_messages)
            state.total_tokens += tok2
            action = _parse_action(raw2)
        if action is None:
            action = {
                "thought": "could not product a valid action after repair attempt",
                "action": "finish",
                "action_input": {
                    "answer": "I wasn't able to determine a next step for this question."
                },
            }
        state.history.append({"role": "assistant", "action": action})
        state.iteration += 1
        return state

    def act(self, state: AgentState) -> AgentState:
        action = next(e["action"] for e in reversed(state.history) if e["role"] == "assistant")
        tool_name = ToolName(action["action"])
        raw_input = dict(action.get("action_input", {}))  

        override_key = INPUT_KEY_OVERRIDES.get(tool_name)
        if override_key and "question" in raw_input:
            raw_input[override_key] = raw_input.pop("question")
        elif override_key and override_key not in raw_input:
            
            state.tool_results.append(ToolResult(
                tool=tool_name, output=None,
                error=f"Missing required input '{override_key}' or 'question' in action_input: {raw_input}",
            ))
            state.history.append({
                "role": "observation",
                "content": "Missing required input. Recover: retry with a 'question' key in action_input, switch tools, or finish.",
            })
            return state   # only return early on the actual failure case

        tool = self.tools[tool_name]
        result = tool.run(raw_input)
        state.tool_results.append(result)

        if result.error:
            obs = f"{result.error} | Recover: fix the input and retry, switch tools, or finish with what you have."
        else:
            obs = _format_output(result.output)
        state.history.append({"role": "observation", "content": obs})
        return state

    def synthesize(self, state: AgentState) -> AgentState:
        messages = build_synth_prompt(state)
        raw, tok = self._complete(messages)
        state.total_tokens += tok
        state.final_answer = "[partial] " + raw
        return state

    def should_continue(self, state: AgentState) -> AgentState:
        action = state.history[-1]["action"]
        if action["action"] == "finish":
            state.final_answer = action.get("action_input", {}).get(
                "answer", "(no answer provided)"
            )
            return "finish"
        if state.iteration >= MAX_ITERATIONS or state.total_tokens >= TOKEN_BUDGET:
            return "force_synth"
        if _is_repeat_call(state, action):
            state.history.append(
                {
                    "role": "observation",
                    "content": "You already tried this exact tool call and it failed. Try a different tool call or a different input or finish",
                }
            )
            return "continue"

    def run(self, query: str) -> AgentState:
        state = AgentState(query=query)
        while True:
            state = self.reason(state)
            decision = self.should_continue(state)
            if decision == "finish":
                break
            if decision == "force_synth":
                state = self.synthesize(state)
                break
            state = self.act(state)
        return state


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_action(raw: str) -> dict | None:
    match = _JSON_OBJECT_RE.search(raw)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if "action" not in obj or obj["action"] not in VALID_ACTORS:
        return None

    obj.setdefault("action_input", {})
    obj.setdefault("thought", "")
    return obj


def _format_output(output) -> str:
    # bounded size to 4k so we don't blow the token budget in one go
    text = json.dumps(output, default=str)
    if len(text) > 4000:
        text = text[:4000] + "... [truncated]"
    return text


def _is_repeat_call(state: AgentState, current_action: dict) -> bool:
    if current_action["action"] == "finish":
        return False
    sig = (
        current_action["action"],
        json.dumps(current_action.get("action_input", {}), sort_keys=True),
    )
    seen = []
    for entry in state.history[:-1]:
        if entry["role"] == "assistant":
            a = entry["action"]
            seen.append(
                (a["action"], json.dumps(a.get("action_input", {}), sort_keys=True))
            )
    return sig in seen


def _estimate_tokens(messages: list[dict], completion: str) -> int:
    # assuming each token = 4 characters (a crude way but something)
    total_chars = sum(len(m["content"]) for m in messages) + len(completion)
    return total_chars // 4
