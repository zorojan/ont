"""Setup FTS5 virtual table for lightning-fast full-text search."""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'ontology.db'

def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    print("Setting up FTS5 index...")
    
    # 1. Create FTS5 table
    c.execute("DROP TABLE IF EXISTS resources_fts")
    c.execute("""
        CREATE VIRTUAL TABLE resources_fts USING fts5(
            id UNINDEXED, 
            title, 
            description, 
            tags, 
            domain,
            tokenize="unicode61 remove_diacritics 1"
        )
    """)
    
    # 2. Populate FTS5 table with existing data 
    c.execute("""
        INSERT INTO resources_fts (id, title, description, tags, domain)
        SELECT id, title, description, tags, domain FROM resources
    """)
    print(f"Populated FTS5 table with {c.rowcount} rows.")
    
    # 3. Create triggers to keep FTS in sync
    c.execute("DROP TRIGGER IF EXISTS resources_ai")
    c.execute("""
        CREATE TRIGGER resources_ai AFTER INSERT ON resources BEGIN
          INSERT INTO resources_fts(id, title, description, tags, domain) 
          VALUES (new.id, new.title, new.description, new.tags, new.domain);
        END;
    """)

    c.execute("DROP TRIGGER IF EXISTS resources_au")
    c.execute("""
        CREATE TRIGGER resources_au AFTER UPDATE ON resources BEGIN
          UPDATE resources_fts SET 
            title = new.title, 
            description = new.description, 
            tags = new.tags, 
            domain = new.domain
          WHERE id = new.id;
        END;
    """)

    c.execute("DROP TRIGGER IF EXISTS resources_ad")
    c.execute("""
        CREATE TRIGGER resources_ad AFTER DELETE ON resources BEGIN
          DELETE FROM resources_fts WHERE id = old.id;
        END;
    """)
    
    conn.commit()
    conn.close()
    print("FTS5 setup complete! Triggers are active.")

if __name__ == '__main__':
    main()
