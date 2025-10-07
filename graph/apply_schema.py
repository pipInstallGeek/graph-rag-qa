from neo4j import GraphDatabase
from pathlib import Path
from api.config import settings

def run_cypher_file(session, path: Path):
    txt = path.read_text(encoding="utf-8")
    # split on semicolons that end statements
    for stmt in [s.strip() for s in txt.split(";") if s.strip()]:
        print(f"[cypher] running statement:\n{stmt}\n---")
        session.run(stmt)

def main():
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_pass))
    schema_path = Path("graph/cypher/schema.cypher")
    with driver.session() as sess:
        run_cypher_file(sess, schema_path)
    driver.close()
    print("[neo4j] schema applied")

if __name__ == "__main__":
    main()

