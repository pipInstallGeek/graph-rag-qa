from pathlib import Path
import pandas as pd
import numpy as np
import faiss
from api.config import settings
from rag.embed import Embedder

def main():
    processed = Path(settings.processed_dir) / "docs.parquet"
    if not processed.exists():
        raise SystemExit(f"Missing {processed}. Run: python scripts/ingest.py")
    df = pd.read_parquet(processed)
    texts = df["text"].tolist()
    emb = Embedder(settings.embeddings_model)
    vecs = emb.encode(texts).astype(np.float32)

    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)
    
    faiss_dir = Path(settings.faiss_dir)
    faiss_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(faiss_dir / "index.faiss"))
    df[["id", "doc_name", "chunk_idx"]].to_parquet(faiss_dir / "mapping.parquet", index=False)

    print(f"[faiss] Index size: {index.ntotal}, dim: {dim}")
    print(f"[faiss] Saved index -> {faiss_dir/'index.faiss'}")
    print(f"[faiss] Saved mapping -> {faiss_dir/'mapping.parquet'}")

if __name__ == "__main__":
    main()
