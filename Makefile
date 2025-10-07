SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
export PYTHONPATH := $(PWD)

.PHONY: venv torch install up down api ingest index demo clean clean-graph help

# 1) Create venv
venv:
	python3 -m venv $(VENV)
	$(PIP) install -U pip setuptools wheel --no-input

# 2) Install CPU-only PyTorch explicitly (prevents CUDA/nvidia wheels)
torch: venv
	$(PIP) install --index-url https://download.pytorch.org/whl/cpu torch==2.4.1

# 3) Install the rest of the deps from requirements.txt (no torch inside!)
install: torch
	$(PIP) install -r requirements.txt

# Docker: Neo4j up/down
up:
	/mnt/c/Program\ Files/Docker/Docker/resources/bin/docker compose -f docker/docker-compose.yml up -d
down:
	/mnt/c/Program\ Files/Docker/Docker/resources/bin/docker compose -f docker/docker-compose.yml down -v

# API server
api:
	$(UVICORN) api.main:app --reload --port 8080

# Pipelines
ingest:
	$(PY) -m scripts.ingest

index:
	$(PY) -m scripts.index_faiss

# Quick test
demo:
	curl -X POST http://127.0.0.1:8080/ask \
	  -H "Content-Type: application/json" \
	  -d '{"question":"Test query?", "k":3}'

# Cleanup generated artifacts
clean:
	rm -rf data/processed/* data/faiss/* graph/*.db graph/__pycache__ graph/*.log

clean-graph:
	$(PY) -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('$(NEO4J_URI)', auth=('$(NEO4J_USER)', '$(NEO4J_PASS)')); session = driver.session(); session.run('MATCH (n) DETACH DELETE n'); session.close(); driver.close()"


NEO4J_URI := bolt://localhost:7687
NEO4J_USER := neo4j
NEO4J_PASS := neo4jpassword

graph-schema:
	$(PY) -m graph.apply_schema

graph-build:
	$(PY) -m graph.build_graph

help:
	@echo "make venv      - create virtual env"
	@echo "make torch     - install CPU-only torch (2.4.1) from PyTorch CPU wheels"
	@echo "make install   - install project deps (after torch); DO NOT list torch in requirements.txt"
	@echo "make up        - start Neo4j via docker-compose"
	@echo "make down      - stop Neo4j and remove volumes"
	@echo "make ingest    - chunk docs from data/raw into data/processed/docs.parquet"
	@echo "make index     - build FAISS index in data/faiss"
	@echo "make api       - run FastAPI on http://127.0.0.1:8080"
	@echo "make demo      - sample POST to /ask"
	@echo "make clean     - remove processed data and index"
	@echo "make clean-graph - remove all nodes and relationships from Neo4j"