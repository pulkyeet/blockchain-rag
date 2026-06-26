from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import get_agent

router = APIRouter()


class AgentRequest(BaseModel):
    query: str


class AgentResponse(BaseModel):
    answer: str | None
    iterations: int
    total_tokens: int
    trace: list[dict]


@router.post("/agent", response_model=AgentResponse)
def run_agent(req: AgentRequest):
    agent = get_agent()
    state = agent.run(req.query)
    return AgentResponse(
        answer=state.final_answer,
        iterations=state.iteration,
        total_tokens=state.total_tokens,
        trace=state.history,
    )
