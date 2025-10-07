from neo4j import GraphDatabase
from api.config import settings

class GraphHelper:
    def __init__(self):
        self.driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_pass))

    def close(self):
        self.driver.close()

    def expand_neighbor_sections(self, section_ids: list[str], limit_per_concept: int = 5) -> list[str]:
        # Given seed sections, find other sections that mention the same concepts
        query = """
        UNWIND $seed AS sid
        MATCH (s:Section {id: sid})-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(n:Section)
        WHERE n.id <> s.id
        WITH n, count(*) AS votes
        RETURN n.id AS id, votes
        ORDER BY votes DESC
        LIMIT $lim
        """
        lim = max(20, len(section_ids)*limit_per_concept)
        with self.driver.session() as sess:
            res = sess.run(query, seed=section_ids, lim=lim)
            return [r["id"] for r in res]

    def summarize_subgraph(self, section_ids: list[str], max_nodes: int = 30) -> dict:
        query = """
        UNWIND $seed AS sid
        MATCH (s:Section {id: sid})-[:MENTIONS]->(c:Concept)
        RETURN collect(distinct {sid:s.id, doc:s.doc_name, idx:s.chunk_idx})[0..$mn] AS sections,
               collect(distinct {concept:c.name})[0..$mn] AS concepts
        """
        with self.driver.session() as sess:
            rec = sess.run(query, seed=section_ids, mn=max_nodes).single()
            return {"sections": rec["sections"], "concepts": rec["concepts"]}

