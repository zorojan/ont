from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from collections import Counter
import sqlite3
import json
import os

app = FastAPI(title="Ontology Discovery API")

DB_FILE = 'ontology.db'

# Make sure static directory exists
os.makedirs('static', exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ─── API Routes (MUST be defined BEFORE static mount) ───

@app.get("/api/resources")
async def get_resources(
    q: str = Query("", description="Search query"),
    type: str = Query("", description="Resource type"),
    status: str = Query("", description="Resource status"),
    industry: str = Query("", description="Industry filter"),
    format: str = Query("", description="Format filter"),
    domain: str = Query("", description="Domain filter"),
    tag: str = Query("", description="Tag filter"),
    region: str = Query("", description="Country/Region filter"),
    scope: str = Query("", description="Coverage scope filter"),
    confidence: str = Query("", description="Confidence filter"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        params = []
        where_clauses = []
        join_clause = ""
        order_clause = "ORDER BY quality DESC, resources.id"
        select_clause = "SELECT resources.*"
        
        if q:
            # Synonym pre-processing
            synonyms = {
                "cyber security": "cybersecurity",
                "cyber-security": "cybersecurity",
                "json-ld": "jsonld",
                "ai ": "artificial intelligence ",
                "ml ": "machine learning ",
                "nlp": "natural language processing"
            }
            processed_q = q.lower()
            for k, v in synonyms.items():
                processed_q = processed_q.replace(k, v)
                
            join_clause = "JOIN resources_fts ON resources.id = resources_fts.id"
            where_clauses.append("resources_fts MATCH ?")
            
            # FTS query with prefix match wildcard '*'
            fts_query = " OR ".join([f'"{term}"*' if not term.endswith('*') else term for term in processed_q.split()])
            if not fts_query: 
                fts_query = '""'
            
            params.append(fts_query)
            # Rank heavily weights title(5.0), description(1.0), tags(2.0), domain(1.0)
            order_clause = "ORDER BY bm25(resources_fts, 5.0, 1.0, 2.0, 1.0), quality DESC, resources.id"
            
        if type and type != "all":
            where_clauses.append("resources.type = ?")
            params.append(type)
            
        if status:
            where_clauses.append("resources.status = ?")
            params.append(status)
            
        if industry:
            where_clauses.append("resources.industry LIKE ?")
            params.append(f"%\"{industry}\"%")
            
        if format:
            where_clauses.append("resources.formats LIKE ?")
            params.append(f"%\"{format}\"%")
        
        if domain:
            where_clauses.append("resources.domain = ?")
            params.append(domain)
            
        if tag:
            where_clauses.append("resources.tags LIKE ?")
            params.append(f"%\"{tag}\"%")
        
        if region:
            where_clauses.append("resources.country_or_region = ?")
            params.append(region)
            
        if scope:
            where_clauses.append("resources.coverage_scope = ?")
            params.append(scope)
            
        if confidence:
            where_clauses.append("resources.confidence = ?")
            params.append(confidence)
            
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
        # Get total count for pagination
        cursor.execute(f"SELECT COUNT(resources.id) FROM resources {join_clause} {where_sql}", params)
        total_items = cursor.fetchone()[0]
        
        # Get paginated data
        query = f"{select_clause} FROM resources {join_clause} {where_sql} {order_clause} LIMIT ? OFFSET ?"
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()
        
        resources = []
        for row in rows:
            resource = dict(row)
            for field in ['targets', 'formats', 'industry', 'tags', 'entities']:
                if resource.get(field):
                    try:
                        resource[field] = json.loads(resource[field])
                    except json.JSONDecodeError:
                        resource[field] = []
                else:
                    resource[field] = []
            resources.append(resource)
            
        conn.close()
        return {
            "data": resources,
            "total": total_items,
            "page": page,
            "limit": limit,
            "total_pages": (total_items + limit - 1) // limit
        }
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/filters")
async def get_filters():
    """Return aggregated counts for all filter facets across the entire database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT type, status, industry, formats, tags, domain, source, country_or_region, coverage_scope, confidence FROM resources")
        rows = cursor.fetchall()
        conn.close()

        types_cnt = Counter()
        statuses_cnt = Counter()
        industries_cnt = Counter()
        formats_cnt = Counter()
        tags_cnt = Counter()
        domains_cnt = Counter()
        sources_cnt = Counter()
        regions_cnt = Counter()
        scopes_cnt = Counter()
        confidence_cnt = Counter()
        
        for row in rows:
            types_cnt[row['type'] or 'unknown'] += 1
            statuses_cnt[row['status'] or 'unknown'] += 1
            domains_cnt[row['domain'] or 'Unknown'] += 1
            sources_cnt[row['source'] or 'unknown'] += 1
            regions_cnt[row['country_or_region'] or 'Unknown'] += 1
            scopes_cnt[row['coverage_scope'] or 'Unknown'] += 1
            confidence_cnt[row['confidence'] or 'Unknown'] += 1
            
            for field_name, counter in [('industry', industries_cnt), ('formats', formats_cnt), ('tags', tags_cnt)]:
                val = row[field_name]
                if val:
                    try:
                        for item in json.loads(val):
                            if item and item != 'all':
                                counter[item] += 1
                    except (json.JSONDecodeError, TypeError):
                        pass
                
        return {
            "total": len(rows),
            "types": dict(types_cnt),
            "statuses": dict(statuses_cnt),
            "industries": dict(sorted(industries_cnt.items(), key=lambda x: -x[1])),
            "formats": dict(sorted(formats_cnt.items(), key=lambda x: -x[1])),
            "tags": dict(sorted(tags_cnt.items(), key=lambda x: -x[1])[:50]),
            "domains": dict(sorted(domains_cnt.items(), key=lambda x: -x[1])),
            "sources": dict(sources_cnt),
            "regions": dict(sorted(regions_cnt.items(), key=lambda x: -x[1])),
            "scopes": dict(sorted(scopes_cnt.items(), key=lambda x: -x[1])),
            "confidence": dict(sorted(confidence_cnt.items(), key=lambda x: -x[1]))
        }
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/resources/{id}/enrich")
async def enrich_resource(id: str = Path(...)):
    """
    On-demand AI Enrichment Stub.
    This endpoint takes a raw resource and simulates generating a structured short_description,
    country_or_region, and coverage_scope using an LLM.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM resources WHERE id = ?", (id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Resource not found")
        
    resource = dict(row)
    
    # -------------------------------------------------------------
    # TODO: Here you would call your LLM API (OpenAI, Gemini, etc.)
    # Example Prompt:
    # "Given the title '{resource['title']}' and description '{resource['description']}', 
    # generate a concise 140-220 char short_description, determine the country_or_region 
    # (Global, EU, US, etc.), and coverage_scope (Universal, Domain-specific)."
    # -------------------------------------------------------------
    
    # Real LLM Call using GitHub PAT
    import urllib.request
    import urllib.error
    
    GITHUB_PAT = os.getenv("GITHUB_TOKEN", "")
    
    prompt = f"""
    Analyze the following metadata for a semantic resource (ontology, taxonomy, etc.):
    Title: {resource.get('title', '')}
    Description: {resource.get('description', '')}
    Current Tags: {resource.get('tags', '[]')}
    Domain: {resource.get('domain', '')}
    
    Return a JSON object with:
    1. "short_description": A clear, concise summary of what this resource is (100-200 chars).
    2. "tags": An array of 3-7 relevant keywords/tags (strings).
    3. "country_or_region": Determine if it's "Global", "US", "EU", "UK", etc. Default to "Global" if unclear.
    4. "coverage_scope": "Universal", "Domain-specific", or "Regional".
    5. "confidence": "High", "Medium", or "Low" based on the clarity of the description.
    """
    
    url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {GITHUB_PAT}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a data enrichment assistant. Reply ONLY with a valid JSON object matching the requested schema. No markdown wrapping."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            llm_reply = result['choices'][0]['message']['content'].strip()
            if llm_reply.startswith("```json"):
                llm_reply = llm_reply[7:-3]
            elif llm_reply.startswith("```"):
                llm_reply = llm_reply[3:-3]
            
            enrichment = json.loads(llm_reply.strip())
            
            short_desc = enrichment.get("short_description", resource.get("description", ""))
            country = enrichment.get("country_or_region", "Global")
            scope = enrichment.get("coverage_scope", "Domain-specific")
            confidence = enrichment.get("confidence", "Medium")
            tags = enrichment.get("tags", [])
            
    except Exception as e:
        print(f"LLM Enrichment failed for {id}:", e)
        raise HTTPException(status_code=500, detail="LLM Enrichment failed")
    
    if "AI Enriched" not in tags:
        tags.append("AI Enriched")
        
    # Update DB
    cursor.execute('''
        UPDATE resources 
        SET short_description = ?, country_or_region = ?, coverage_scope = ?, confidence = ?, tags = ?
        WHERE id = ?
    ''', (short_desc, country, scope, confidence, json.dumps(tags), id))
    
    conn.commit()
    
    # Fetch updated row
    cursor.execute("SELECT * FROM resources WHERE id = ?", (id,))
    updated_row = dict(cursor.fetchone())
    conn.close()
    
    # Process json fields for return
    for field in ['targets', 'formats', 'industry', 'tags', 'entities']:
        if updated_row.get(field):
            try:
                updated_row[field] = json.loads(updated_row[field])
            except json.JSONDecodeError:
                updated_row[field] = []
        else:
            updated_row[field] = []
            
    return updated_row

# ─── Serve index.html at root ───

@app.get("/")
async def root():
    file_path = os.path.join("static", "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"message": "index.html not found in static folder"}

# Mount static LAST so it doesn't shadow /api/* routes
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
