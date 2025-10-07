from fastapi import FastAPI, HTTPException
from time import perf_counter
from api.models import AskRequest, AskResponse
from rag.hybrid_retriever import HybridRetriever
import re
from rag.retriever_graph import GraphHelper
from rag.llm_openrouter import call_openrouter

app = FastAPI(title="Graph-RAG-QA")
hybrid = None


def assemble_answer(hits, max_chars=800):
    texts = []
    for h in hits:
        t = re.sub(r'\s+', ' ', h["text"]).strip()
        texts.append(t)
    return " … ".join(texts)[:max_chars]

@app.on_event("startup")
def startup():
    global hybrid
    hybrid = HybridRetriever()

@app.get("/health", tags=["health"])
def health():
    neo4j_status = "unknown"
    neo4j_error = None
    openrouter_status = "unknown"
    openrouter_error = None
    # Neo4j health check
    try:
        graph = GraphHelper()
        with graph.driver.session() as session:
            result = session.run("RETURN 1 AS ok").single()
            graph.close()
        if result and result["ok"] == 1:
            neo4j_status = "ok"
        else:
            neo4j_status = "error"
            neo4j_error = "Neo4j health check failed"
    except Exception as e:
        neo4j_status = "error"
        neo4j_error = f"Neo4j health check error: {str(e)}"
    # OpenRouter health check (minimal token usage)
    try:
        ping_msg = [{"role": "user", "content": "ping"}]
        resp = call_openrouter(ping_msg)
        if resp:
            openrouter_status = "ok"
        else:
            openrouter_status = "error"
            openrouter_error = "No response from OpenRouter"
    except Exception as e:
        openrouter_status = "error"
        openrouter_error = f"OpenRouter health check error: {str(e)}"
    errors = []
    if neo4j_error:
        errors.append({"service": "neo4j", "error": neo4j_error})
    if openrouter_error:
        errors.append({"service": "openrouter", "error": openrouter_error})
    return {
        "status": "ok",
        "llm": openrouter_status,
        "graph": "on",
        "neo4j": neo4j_status,
        "errors": errors
    }

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    t0 = perf_counter()
    res = hybrid.search(req.question, k=getattr(req, "k", 4))
    hits = res["hits"]
    graph_ctx = res["graph"]

    if hits:
        context = assemble_answer(hits[:3])
        answer = hybrid.synthesize_answer(req.question, context)
        citations = [f"{h['doc_name']}#{h['chunk_idx']}" for h in hits[:3]]
    else:
        answer, citations = "No context retrieved.", []

    latency = (perf_counter() - t0) * 1000
    return AskResponse(answer=answer, citations=citations, graph_context=graph_ctx, latency_ms=latency)
