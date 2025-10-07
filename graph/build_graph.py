import re
from collections import Counter
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase

from api.config import settings

# lightweight stopword list
STOP = set("""
a about above after again against all am an and any are as at be because been before being below
between both but by could did do does doing down during each few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just me more
most my myself no nor not of off on once only or other our ours ourselves out over own same she
should so some such than that the their theirs them themselves then there these they this those
through to too under until up very was we were what when where which while who whom why with you
your yours yourself yourselves
""".split())

WORD = re.compile(r"[a-z]{2,}")  # keep alphabetic tokens

def extract_concepts(text: str, max_phr_len=3, max_phr=12):
    t = text.lower()
    toks = [w for w in WORD.findall(t) if w not in STOP]
    if not toks:
        return []
    # unigrams + bigrams + trigrams
    c = Counter()
    for i, w in enumerate(toks):
        c[w] += 1
        if i+1 < len(toks):
            c[f"{w} {toks[i+1]}"] += 1
        if i+2 < len(toks):
            c[f"{w} {toks[i+1]} {toks[i+2]}"] += 1
    # choose top phrases, prefer multiword
    items = list(c.items())
    items.sort(key=lambda kv: (-len(kv[0].split()), -kv[1], kv[0]))
    picked = []
    seen = set()
    for k, _ in items:
        if len(picked) >= max_phr:
            break
        if any(k in s for s in seen):  # avoid subsumed by previous
            continue
        picked.append(k)
        seen.add(k)
    return picked

def main():
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_pass))
    df = pd.read_parquet(Path(settings.processed_dir) / "docs.parquet")

    # Write Sections first
    section_rows = df[["id","doc_name","chunk_idx","text"]].to_dict("records")

    with driver.session() as sess:
        # UNWIND batch insert for Sections
        sess.run("""
        UNWIND $rows AS row
        MERGE (s:Section {id: row.id})
          SET s.doc_name = row.doc_name,
              s.chunk_idx = row.chunk_idx,
              s.text = row.text
        """, rows=section_rows)

        # Build Concepts and MENTIONS in batches
        B = 500
        for i in range(0, len(section_rows), B):
            batch = section_rows[i:i+B]
            concept_payload = []
            for r in batch:
                concepts = extract_concepts(r["text"])
                for name in concepts:
                    concept_payload.append({
                        "sid": r["id"],
                        "name": name,
                        "name_lower": name.lower(),
                    })
            if not concept_payload:
                continue
            sess.run("""
            UNWIND $rows AS row
            MERGE (c:Concept {name: row.name})
              ON CREATE SET c.name_lower = row.name_lower
            MERGE (s:Section {id: row.sid})
            MERGE (s)-[:MENTIONS]->(c)
            """, rows=concept_payload)

    driver.close()
    print("[neo4j] graph built from docs.parquet")

if __name__ == "__main__":
    main()

