from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    k: int = 4

class AskResponse(BaseModel):
    answer: str
    citations: list[str]
    graph_context: dict | None = None
    latency_ms: float

