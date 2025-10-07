from typing import List, Dict
from rag.retriever_vector import VectorRetriever
from rag.retriever_graph import GraphHelper
from rag.llm_openrouter import call_openrouter

class HybridRetriever:
    def __init__(self):
        self.vec = VectorRetriever()
        self.gh = GraphHelper()

    def synthesize_answer(self, question: str, context: str) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers questions using provided context."},
            {"role": "user", "content": f"Context: {context}\nQuestion: {question}"}
        ]
        return call_openrouter(messages)

    def search(self, query: str, k: int = 4) -> Dict:
        # 1) vector
        vec_hits = self.vec.search(query, k=max(k, 8))
        seed_ids = [h["id"] for h in vec_hits]

        # 2) graph expansion
        neighbor_ids = self.gh.expand_neighbor_sections(seed_ids, limit_per_concept=5)

        # 3) merge + rerank (simple rule: if a hit is a neighbor, give it a small boost)
        id_to_row = { self.vec.docs.iloc[i].id: dict(h) for i,h in enumerate(vec_hits) }  # NOT correct mapping by i
        # Build mapping by section id instead:
        id_to_hit = { h["id"]: h for h in vec_hits }

        expanded_rows: List[Dict] = []
        seen = set()
        for h in vec_hits:
            h2 = dict(h)
            if h2["id"] in neighbor_ids:
                h2["score"] += 0.05  # tiny boost if graph-connected
            expanded_rows.append(h2)
            seen.add(h2["id"])

        # add extra neighbor sections not in vec top-k (pull their text from docs)
        for sid in neighbor_ids:
            if sid in seen:
                continue
            # find row by id in self.vec.docs
            rows = self.vec.docs[self.vec.docs["id"] == sid]
            if rows.empty:
                continue
            row = rows.iloc[0]
            expanded_rows.append({
                "rank": 9999, "score": 0.01, "id": sid,
                "doc_name": row["doc_name"], "chunk_idx": int(row["chunk_idx"]),
                "text": row["text"]
            })
            seen.add(sid)

        # final sort and cut
        expanded_rows.sort(key=lambda r: -r["score"])
        final_hits = expanded_rows[:max(k, 5)]

        # small graph summary for UI/prompt
        graph_ctx = self.gh.summarize_subgraph([h["id"] for h in final_hits], max_nodes=30)
        return {"hits": final_hits, "graph": graph_ctx}

