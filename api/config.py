from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    openrouter_token: str | None = os.getenv("OPENROUTER_TOKEN")
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_pass: str = os.getenv("NEO4J_PASS", "neo4jpassword")
    data_dir: str = os.getenv("DATA_DIR", "./data")
    processed_dir: str = os.getenv("PROCESSED_DIR", "./data/processed")
    faiss_dir: str = os.getenv("FAISS_DIR", "./data/faiss")
    embeddings_model: str = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

settings = Settings()

