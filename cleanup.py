"""
Database cleanup script: removes junk W3ID entries that are NOT real semantic resources.

Criteria for REMOVAL (ALL must be true):
1. Source is w3id.org
2. Description is shorter than 50 characters (practically empty)
3. Title and description do NOT contain any semantic keywords
   (ontology, vocabulary, taxonomy, knowledge, schema, rdf, owl, linked data, semantic, sparql)
"""
import sqlite3, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'ontology.db'

# Semantic keywords — if ANY of these appear in title or description, we KEEP the record
SEMANTIC_KEYWORDS = [
    'ontolog', 'vocabular', 'taxonom', 'knowledge', 'schema', 'rdf', 'owl ',
    'linked data', 'semantic', 'sparql', 'skos', 'turtle', 'triple', 'graph',
    'metadata', 'namespace', 'predicate', 'inference', 'reasoner', 'class hierarchy',
    'concept', 'thesaur', 'nomenclature', 'classification', 'identifier',
    'persistent uri', 'persistent url', 'w3c', 'standard', 'specification',
    'data model', 'interoperab', 'fair ', 'open data', 'provenance',
]

MIN_DESCRIPTION_LENGTH = 50  # descriptions shorter than this are suspect

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Backup count
    c.execute("SELECT COUNT(id) FROM resources")
    total_before = c.fetchone()[0]
    
    # Find candidates for removal
    c.execute("""
        SELECT id, title, description, source FROM resources 
        WHERE source = 'w3id.org' AND LENGTH(COALESCE(description, '')) < ?
    """, (MIN_DESCRIPTION_LENGTH,))
    
    candidates = c.fetchall()
    
    to_remove = []
    to_keep = []
    
    for row in candidates:
        text = ((row['title'] or '') + ' ' + (row['description'] or '')).lower()
        
        has_semantic = any(kw in text for kw in SEMANTIC_KEYWORDS)
        
        if has_semantic:
            to_keep.append(row['id'])
        else:
            to_remove.append(row['id'])
    
    print(f"=== Cleanup Analysis ===")
    print(f"Total records before: {total_before}")
    print(f"W3ID short-description candidates: {len(candidates)}")
    print(f"  Contain semantic keywords (KEEP): {len(to_keep)}")
    print(f"  No semantic keywords (REMOVE): {len(to_remove)}")
    
    # Show some examples of what will be removed
    print(f"\n=== Sample records to be REMOVED ({min(15, len(to_remove))} of {len(to_remove)}) ===")
    for rid in to_remove[:15]:
        c.execute("SELECT id, title, description FROM resources WHERE id = ?", (rid,))
        r = c.fetchone()
        desc = (r['description'] or '').replace('\n', ' ').strip()[:60]
        print(f"  ❌ [{r['id']}] {r['title']} => '{desc}'")
    
    # Show some examples of what will be KEPT despite short desc
    print(f"\n=== Sample records KEPT despite short desc ({min(10, len(to_keep))} of {len(to_keep)}) ===")
    for rid in to_keep[:10]:
        c.execute("SELECT id, title, description FROM resources WHERE id = ?", (rid,))
        r = c.fetchone()
        desc = (r['description'] or '').replace('\n', ' ').strip()[:60]
        print(f"  ✅ [{r['id']}] {r['title']} => '{desc}'")
    
    # Execute deletion
    if to_remove:
        placeholders = ','.join(['?'] * len(to_remove))
        c.execute(f"DELETE FROM resources WHERE id IN ({placeholders})", to_remove)
        conn.commit()
        
    c.execute("SELECT COUNT(id) FROM resources")
    total_after = c.fetchone()[0]
    
    print(f"\n=== Result ===")
    print(f"Records before: {total_before}")
    print(f"Records removed: {len(to_remove)}")
    print(f"Records after: {total_after}")
    
    conn.close()

if __name__ == '__main__':
    main()
