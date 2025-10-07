from pathlib import Path
import numpy as np
import pandas as pd
import faiss
from api.config import settings
from rag.embed import Embedder

class VectorRetriever:
    def __init__(self):
        self.emb = Embedder(settings.embeddings_model)
        faiss_path = Path(settings.faiss_dir) / "index.faiss"
        map_path = Path(settings.faiss_dir) / "mapping.parquet"
        if not faiss_path.exists() or not map_path.exists():
            raise RuntimeError("FAISS index or mapping missing. Run scripts/index_faiss.py first.")
        self.index = faiss.read_index(str(faiss_path))
        self.mapping = pd.read_parquet(map_path)
        processed = Path(settings.processed_dir) / "docs.parquet"
        self.docs = pd.read_parquet(processed)

    def search(self, query: str, k: int = 4):
        q = self.emb.encode_one(query).astype(np.float32)
        D, I = self.index.search(q.reshape(1, -1), k)
        I = I[0].tolist()
        D = D[0].tolist()
        rows = []
        for rank, (idx, score) in enumerate(zip(I, D), start=1):
            row = self.docs.iloc[idx]
            rows.append({
                "rank": rank,
                "score": float(score),
                "id": row["id"],
                "doc_name": row["doc_name"],
                "chunk_idx": int(row["chunk_idx"]),
                "text": row["text"]
            })
        return rows
