"""
Rule-based auto-classifier for Ontology Discovery Catalog.
Fills in: country_or_region, coverage_scope, confidence, industries, resource_type
Based on keyword analysis of title, description, tags, domain — NO LLM needed.
"""
import sqlite3, json, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'ontology.db'

# ── Keyword dictionaries for classification ──

REGION_RULES = {
    'EU': ['european', 'europe', 'eu ', ' eu', 'nace', 'eurostat', 'esco', 'eclass', 'inspire', 'europeana',
           'gdpr', 'etsi', 'cen ', 'cenelec', 'fiware'],
    'US': ['american', 'us ', ' usa', 'naics', 'sic code', 'fda', 'nist', 'epa.gov', 'census.gov',
           'nih.gov', 'medicare', 'hipaa', 'osha'],
    'UK': ['united kingdom', 'uk ', 'british', 'england', 'nhs', 'gov.uk', 'ordnance survey'],
    'JP': ['japan', 'japanese', 'jpn'],
    'CN': ['china', 'chinese', 'chn'],
    'DE': ['german', 'germany', 'deu', 'deutschland'],
    'FR': ['french', 'france', 'fra'],
    'AU': ['australia', 'australian'],
    'CA': ['canada', 'canadian'],
    'IN': ['india', 'indian'],
    'AM': ['armenia', 'armenian', 'yerevan'],
    'BR': ['brazil', 'brazilian'],
    'RU': ['russia', 'russian'],
    'KR': ['korea', 'korean'],
}

INDUSTRY_KEYWORDS = {
    'healthcare': ['health', 'medical', 'clinical', 'hospital', 'patient', 'drug', 'pharma',
                    'disease', 'therapy', 'diagnosis', 'biomedical', 'hl7', 'fhir', 'snomed',
                    'loinc', 'icd-', 'nursing', 'anatomy', 'gene', 'genomic'],
    'finance': ['financ', 'bank', 'trading', 'stock', 'payment', 'fibo', 'accounting',
                'insurance', 'audit', 'tax', 'credit', 'loan', 'investment', 'monetary',
                'fiscal', 'ledger', 'invoice', 'xbrl'],
    'manufacturing': ['manufactur', 'factory', 'production', 'assembly', 'machining',
                       'cnc', 'lean', 'iso 9001', 'quality control', 'bom', 'plm',
                       'automation', 'robot', 'industry 4'],
    'energy': ['energy', 'power', 'electric', 'solar', 'wind', 'nuclear', 'oil', 'gas',
               'renewable', 'grid', 'smart grid', 'utility', 'fuel', 'battery', 'hydro'],
    'construction': ['construction', 'building', 'bim', 'architect', 'civil', 'structural',
                      'ifc', 'concrete', 'steel', 'bridge', 'road', 'infrastructure'],
    'agriculture': ['agri', 'farm', 'crop', 'livestock', 'soil', 'food', 'nutrition',
                     'grain', 'harvest', 'pesticide', 'irrigation', 'cattle', 'plant'],
    'logistics': ['logistic', 'supply chain', 'transport', 'shipping', 'freight', 'cargo',
                   'warehouse', 'delivery', 'fleet', 'port', 'maritime', 'aviation'],
    'retail': ['retail', 'e-commerce', 'ecommerce', 'shopping', 'product catalog',
               'merchandise', 'store', 'consumer', 'barcode', 'gtin', 'ean'],
    'education': ['education', 'learning', 'school', 'university', 'academic', 'student',
                   'course', 'curriculum', 'teaching', 'pedagogy', 'mooc', 'lms'],
    'telecom': ['telecom', 'network', 'mobile', '5g', 'lte', 'spectrum', 'bandwidth',
                'wireless', 'antenna', 'fiber'],
    'automotive': ['automotive', 'vehicle', 'car', 'motor', 'driving', 'autonomous',
                    'adas', 'v2x', 'chassis', 'engine', 'tire'],
    'aerospace': ['aerospace', 'aircraft', 'aviation', 'satellite', 'space', 'nasa',
                   'rocket', 'propulsion', 'orbit'],
    'cybersecurity': ['cybersecurity', 'cyber security', 'threat', 'malware', 'intrusion',
                       'vulnerability', 'exploit', 'stix', 'mitre', 'attack', 'incident',
                       'forensic', 'firewall', 'encryption'],
    'iot': ['iot', 'internet of things', 'sensor', 'smart home', 'mqtt', 'zigbee',
            'wearable', 'embedded', 'actuator', 'smart city', 'edge computing'],
    'legal': ['legal', 'law', 'regulation', 'compliance', 'privacy', 'gdpr', 'contract',
              'license', 'intellectual property', 'patent', 'court', 'judicial'],
    'media': ['media', 'journalism', 'news', 'broadcast', 'video', 'audio', 'podcast',
              'streaming', 'entertainment', 'publishing', 'music', 'film'],
    'government': ['government', 'public sector', 'e-government', 'municipal', 'federal',
                    'census', 'civic', 'policy', 'voting', 'legislation'],
    'environment': ['environment', 'climate', 'ecology', 'biodiversity', 'conservation',
                     'pollution', 'emission', 'sustainability', 'carbon', 'ecosystem',
                     'ocean', 'marine', 'wildlife', 'forest'],
    'real_estate': ['real estate', 'property', 'housing', 'rent', 'mortgage', 'land',
                     'zoning', 'building permit'],
}

SCOPE_KEYWORDS = {
    'Universal': ['universal', 'general purpose', 'upper ontology', 'foundational',
                   'cross-domain', 'meta', 'top-level', 'schema.org', 'dublin core',
                   'foaf', 'skos', 'owl', 'rdfs', 'rdf', 'prov', 'dcat'],
    'Domain-specific': ['domain', 'specific', 'specialized', 'sector', 'vertical',
                         'industry-specific', 'clinical', 'financial', 'manufacturing'],
    'Regional': ['national', 'regional', 'local', 'country', 'jurisdiction',
                  'government', 'municipal', 'federal', 'state'],
}

TYPE_KEYWORDS = {
    'ontology': ['ontology', 'owl', 'rdf schema', 'semantic model', 'knowledge representation',
                  'description logic', 'class hierarchy'],
    'vocabulary': ['vocabulary', 'thesaurus', 'glossary', 'dictionary', 'term', 'lexicon',
                    'skos', 'concept scheme', 'controlled vocabulary'],
    'taxonomy': ['taxonomy', 'classification', 'categorization', 'hierarchy', 'tree structure',
                  'typology', 'nomenclature'],
    'standard': ['standard', 'iso ', 'ieee', 'w3c recommendation', 'rfc ', 'specification',
                  'normative', 'ietf'],
    'framework': ['framework', 'reference model', 'architecture', 'methodology',
                   'best practice', 'guideline'],
}

def classify_text(text):
    """Analyze text and return classification results."""
    text_lower = text.lower()
    
    # Detect region
    region = 'Global'
    for reg, keywords in REGION_RULES.items():
        for kw in keywords:
            if kw in text_lower:
                region = reg
                break
        if region != 'Global':
            break
    
    # Detect industries
    industries = []
    for ind, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score >= 2:
            industries.append(ind)
        elif score == 1 and len(text_lower) < 500:
            industries.append(ind)
    
    # Detect scope
    scope = 'Universal'
    if industries:
        scope = 'Domain-specific'
    for sc, keywords in SCOPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scope = sc
                break
    
    # Detect resource type
    rtype = None
    best_score = 0
    for t, keywords in TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            rtype = t
    
    return region, industries, scope, rtype

def compute_confidence(resource):
    """Compute confidence score: High / Medium / Low."""
    score = 0
    desc = resource.get('description', '') or ''
    tags = resource.get('tags', '[]')
    try:
        tag_list = json.loads(tags) if isinstance(tags, str) else tags
    except:
        tag_list = []
    
    if len(desc) > 100: score += 3
    elif len(desc) > 30: score += 1
    
    if len(tag_list) > 3: score += 2
    elif len(tag_list) > 0: score += 1
    
    source = resource.get('source', '')
    if source == 'lov': score += 2
    elif source == 'seed': score += 3
    
    if resource.get('domain') and resource['domain'] not in ('W3ID Project', 'Unknown'):
        score += 1
    
    if score >= 6: return 'High'
    if score >= 3: return 'Medium'
    return 'Low'

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM resources")
    rows = cursor.fetchall()
    
    updated = 0
    stats = {'region': 0, 'scope': 0, 'industry': 0, 'confidence': 0, 'type': 0}
    
    for row in rows:
        resource = dict(row)
        rid = resource['id']
        
        # Build text blob for analysis
        text = ' '.join(filter(None, [
            resource.get('title', ''),
            resource.get('description', ''),
            resource.get('domain', ''),
            resource.get('tags', ''),
        ]))
        
        region, industries, scope, rtype = classify_text(text)
        confidence = compute_confidence(resource)
        
        updates = {}
        
        # Only update if field is empty
        if not resource.get('country_or_region'):
            updates['country_or_region'] = region
            stats['region'] += 1
            
        if not resource.get('coverage_scope'):
            updates['coverage_scope'] = scope
            stats['scope'] += 1
            
        if not resource.get('confidence'):
            updates['confidence'] = confidence
            stats['confidence'] += 1
        
        # Merge industries
        try:
            existing_ind = json.loads(resource.get('industry', '[]') or '[]')
        except:
            existing_ind = []
        if existing_ind == ['all'] or not existing_ind:
            if industries:
                updates['industry'] = json.dumps(industries)
                stats['industry'] += 1
        
        # Update type if current type seems wrong and we found a better match
        if rtype and resource.get('type') == 'ontology' and resource.get('source') != 'seed':
            if rtype != 'ontology':
                updates['type'] = rtype
                stats['type'] += 1
        
        if updates:
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [rid]
            cursor.execute(f"UPDATE resources SET {set_clause} WHERE id = ?", values)
            updated += 1
    
    conn.commit()
    conn.close()
    
    print(f"Rule-based classification complete!")
    print(f"Records processed: {len(rows)}")
    print(f"Records updated: {updated}")
    print(f"Fields filled:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

if __name__ == '__main__':
    main()
