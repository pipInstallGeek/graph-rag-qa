// Sections are text chunks
CREATE CONSTRAINT section_id IF NOT EXISTS
FOR (s:Section) REQUIRE s.id IS UNIQUE;

// Concepts are surface strings
CREATE CONSTRAINT concept_name IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE;

// Helpful indexes
CREATE INDEX section_doc IF NOT EXISTS
FOR (s:Section) ON (s.doc_name);

CREATE INDEX concept_lower IF NOT EXISTS
FOR (c:Concept) ON (c.name_lower);

