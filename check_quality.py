"""Analyze W3ID data quality to understand the scope of junk entries."""
import sqlite3, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('ontology.db')
c = conn.cursor()

# Overall stats by source
print("=== Records by source ===")
c.execute("SELECT source, COUNT(id) FROM resources GROUP BY source")
for r in c.fetchall(): print(f"  {r[0]}: {r[1]}")

# W3ID description lengths
SRC = 'w3id.org'
print(f"\n=== W3ID ({SRC}) description quality ===")
c.execute("SELECT COUNT(id) FROM resources WHERE source=?", (SRC,))
total_w3id = c.fetchone()[0]
print(f"  Total W3ID: {total_w3id}")

for threshold in [0, 10, 30, 50, 80, 100, 150]:
    c.execute(f"SELECT COUNT(id) FROM resources WHERE source=? AND LENGTH(COALESCE(description,'')) <= ?", (SRC, threshold))
    cnt = c.fetchone()[0]
    pct = round(cnt/total_w3id*100) if total_w3id else 0
    print(f"  Description <= {threshold} chars: {cnt} ({pct}%)")

# Sample junk
print("\n=== Sample junk W3ID (description < 40 chars) ===")
c.execute("SELECT id, title, description FROM resources WHERE source=? AND LENGTH(COALESCE(description,'')) < 40 LIMIT 15", (SRC,))
for r in c.fetchall():
    desc = (r[2] or '').replace('\n',' ').strip()
    print(f"  [{r[0]}] {r[1]} => '{desc}'")

# Sample GOOD
print("\n=== Sample GOOD W3ID (description > 100 chars, mentions semantic terms) ===")
c.execute("""SELECT id, title, SUBSTR(description,1,100) FROM resources WHERE source=? AND LENGTH(COALESCE(description,'')) > 100
    AND (LOWER(description) LIKE '%ontolog%' OR LOWER(description) LIKE '%vocabular%' 
    OR LOWER(description) LIKE '%rdf%' OR LOWER(description) LIKE '%semantic%'
    OR LOWER(description) LIKE '%knowledge%' OR LOWER(description) LIKE '%linked data%') 
    LIMIT 10""", (SRC,))
for r in c.fetchall():
    print(f"  [{r[0]}] {r[1]} => '{r[2]}...'")

# Semantic content detection
print("\n=== W3ID semantic vs non-semantic ===")
c.execute("""SELECT COUNT(id) FROM resources WHERE source=? 
    AND (LOWER(title) LIKE '%ontolog%' OR LOWER(description) LIKE '%ontolog%' 
    OR LOWER(title) LIKE '%vocabular%' OR LOWER(description) LIKE '%vocabular%' 
    OR LOWER(description) LIKE '%schema%' OR LOWER(description) LIKE '%linked data%'
    OR LOWER(description) LIKE '%rdf%' OR LOWER(description) LIKE '%semantic%'
    OR LOWER(description) LIKE '%knowledge%' OR LOWER(description) LIKE '%taxonomy%'
    OR LOWER(description) LIKE '%owl%' OR LOWER(description) LIKE '%sparql%'
    OR LOWER(title) LIKE '%taxonomy%' OR LOWER(title) LIKE '%knowledge%')""", (SRC,))
semantic = c.fetchone()[0]
print(f"  Semantic-related: {semantic}")
print(f"  Not semantic-related: {total_w3id - semantic}")

# What would we keep?
print("\n=== Proposed KEEP criteria (desc > 50 OR semantic keywords) ===")
c.execute("""SELECT COUNT(id) FROM resources WHERE source=? AND (
    LENGTH(COALESCE(description,'')) > 50
    OR LOWER(title) LIKE '%ontolog%' OR LOWER(title) LIKE '%vocabular%'
    OR LOWER(title) LIKE '%taxonomy%' OR LOWER(title) LIKE '%knowledge%'
    OR LOWER(title) LIKE '%schema%' OR LOWER(title) LIKE '%linked data%'
    OR LOWER(description) LIKE '%ontolog%' OR LOWER(description) LIKE '%vocabular%'
    OR LOWER(description) LIKE '%rdf%' OR LOWER(description) LIKE '%semantic%'
    OR LOWER(description) LIKE '%sparql%' OR LOWER(description) LIKE '%owl%'
)""", (SRC,))
keep = c.fetchone()[0]
remove = total_w3id - keep
print(f"  Would KEEP: {keep}")
print(f"  Would REMOVE: {remove}")

conn.close()
