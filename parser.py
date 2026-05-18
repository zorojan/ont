import sqlite3
import json
import os
import requests
import concurrent.futures
import re
from datetime import datetime

DB_FILE = 'ontology.db'
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

INITIAL_DATA = [
  {"id":"schema-org","w3id":"https://schema.org","title":"Schema.org","type":"vocabulary","description":"Универсальный структурированный словарь для web. Покрывает организации, продукты, события, людей, заказы, инвойсы и более 800 типов.","targets":["https://schema.org/"],"formats":["jsonld","rdf","ttl"],"domain":"Universal / Web","industry":["all"],"tags":["universal","SEO","products","organizations","e-commerce","orders"],"quality":1.0,"status":"verified","source":"schema.org","entities":["Organization","Product","Offer","Order","Invoice","Person","Event","Place","Service","Review","Rating","BreadcrumbList","ItemList"],"questions_hint":"Как называется компания? Какие продукты/услуги предлагает? Кому продаёт — B2B или B2C?"},
  {"id":"apqc-pcf","w3id":"https://apqc.org/pcf","title":"APQC Process Classification Framework","type":"framework","description":"Кросс-отраслевая таксономия бизнес-процессов: 12 категорий, 1200+ процессов. Используется для бенчмаркинга и моделирования операций.","targets":["https://www.apqc.org/process-frameworks"],"formats":["xlsx","pdf"],"domain":"Enterprise / Operations","industry":["manufacturing","retail","services","healthcare","finance","logistics"],"tags":["processes","operations","benchmarking","cross-industry","APQC"],"quality":0.97,"status":"verified","source":"apqc.org","entities":["Process","Category","Activity","Metric","KPI","BenchmarkGroup","OperatingModel"],"questions_hint":"Какие бизнес-процессы наиболее критичны? Как измеряете эффективность процессов?"},
  {"id":"naics","w3id":"https://www.census.gov/naics","title":"NAICS — North American Industry Classification","type":"taxonomy","description":"Отраслевой классификатор экономики Северной Америки: 20 секторов, 1000+ отраслей. Официальный стандарт для идентификации типа бизнеса.","targets":["https://www.census.gov/naics/"],"formats":["xlsx","csv","rdf"],"domain":"Industry Classification","industry":["all"],"tags":["classification","industry","SIC","NACE","sectors"],"quality":0.99,"status":"verified","source":"census.gov","entities":["Sector","Subsector","IndustryGroup","Industry","NationalIndustry"],"questions_hint":"Как классифицируется основная деятельность компании? Есть ли несколько видов деятельности?"},
  {"id":"nace","w3id":"https://ec.europa.eu/eurostat/web/nace","title":"NACE Rev.2 — European Industry Classification","type":"taxonomy","description":"Европейский статистический классификатор экономической деятельности. Аналог NAICS для EU. 21 секция, 88 подразделов.","targets":["https://ec.europa.eu/eurostat/web/nace"],"formats":["xlsx","csv"],"domain":"Industry Classification","industry":["all"],"tags":["EU","classification","Eurostat","sectors","statistics"],"quality":0.99,"status":"verified","source":"eurostat.eu","entities":["Section","Division","Group","Class"],"questions_hint":"В каком регионе работает компания? Какой NACE-код у основной деятельности?"},
  {"id":"gs1-voc","w3id":"https://ref.gs1.org/voc/","title":"GS1 Web Vocabulary","type":"vocabulary","description":"Расширение schema.org для supply chain: штрихкоды, продукты питания, одежда, GTIN, логистика, торговые партнёры. Machine-readable в JSON-LD / TTL.","targets":["https://ref.gs1.org/voc/"],"formats":["jsonld","ttl","rdf"],"domain":"Supply Chain / Retail","industry":["retail","food","manufacturing","logistics"],"tags":["GS1","GTIN","barcode","supply chain","food","products","GDSN"],"quality":0.95,"status":"verified","source":"gs1.org","entities":["Product","ProductGroup","Offer","Party","TradeItem","Packaging","CertificationDetails","FoodBeverageTobaccoProduct"],"questions_hint":"Есть ли у товаров штрих-коды / GTIN? Работаете ли с ритейл-сетями? Нужна ли прослеживаемость партий?"},
  {"id":"unspsc","w3id":"https://www.unspsc.org","title":"UNSPSC — Product & Service Classification","type":"taxonomy","description":"UN/SPSC: универсальная классификация товаров и услуг для закупок и тендеров. 55000+ кодов, охватывает все типы продуктов.","targets":["https://www.unspsc.org/"],"formats":["xlsx","csv"],"domain":"Procurement / Catalog","industry":["manufacturing","retail","services","logistics"],"tags":["procurement","catalog","products","services","UN","tenders"],"quality":0.94,"status":"verified","source":"unspsc.org","entities":["Segment","Family","Class","Commodity","BusinessFunction"],"questions_hint":"Компания участвует в тендерах? Есть ли каталог закупаемых материалов/услуг?"},
  {"id":"fibo","w3id":"https://w3id.org/fibo","title":"FIBO — Financial Industry Business Ontology","type":"ontology","description":"OMG-стандарт для финансовых инструментов, ценных бумаг, юридических лиц и сделок. Охватывает: банки, страховщики, фонды, деривативы, регуляторную отчётность.","targets":["https://spec.edmcouncil.org/fibo/"],"formats":["ttl","owl","rdf"],"domain":"Finance / Banking","industry":["finance","banking","insurance"],"tags":["finance","banking","securities","instruments","derivatives","OMG","regulatory"],"quality":0.96,"status":"verified","source":"edmcouncil.org","entities":["FinancialInstrument","LegalEntity","Account","Contract","Party","Currency","MarketIdentifier","Regulator","Transaction"],"questions_hint":"Тип лицензии (банк, брокер, страховщик)? Работаете с деривативами? Что нужно для регуляторной отчётности?"},
  {"id":"saref","w3id":"https://w3id.org/saref","title":"SAREF — Smart Applications REFerence","type":"ontology","description":"ETSI-стандарт для smart home и IoT: устройства, сервисы, измерения, состояния, команды. Есть расширения: energy, building, agriculture, environment.","targets":["https://saref.etsi.org/core/"],"formats":["ttl","owl"],"domain":"IoT / Smart Home","industry":["iot","smartcity","manufacturing","energy"],"tags":["IoT","devices","smart home","ETSI","sensors","commands","states"],"quality":0.97,"status":"verified","source":"etsi.org","entities":["Device","Sensor","Actuator","Service","Property","State","Command","Measurement","FeatureOfInterest","UnitOfMeasure"],"questions_hint":"Какие устройства используются? Собираются ли данные датчиков? Нужна автоматизация или оповещения?"},
  {"id":"bot","w3id":"https://w3id.org/bot","title":"BOT — Building Topology Ontology","type":"ontology","description":"W3C-LBD стандарт для BIM: здания, этажи, зоны, элементы конструкции. Интегрируется с IFC, SAREF for Building и SSN/SOSA.","targets":["https://github.com/w3c-lbd-cg/bot"],"formats":["ttl","owl"],"domain":"BIM / Construction","industry":["construction","realestate","facility"],"tags":["BIM","building","topology","IFC","spaces","zones","floors"],"quality":0.95,"status":"verified","source":"w3id.org","entities":["Building","Storey","Space","Element","Zone","Interface","Site","BuildingElement"],"questions_hint":"Управляете несколькими объектами? Нужен учёт помещений, инвентаря, технического обслуживания?"},
  {"id":"dpv","w3id":"https://w3id.org/dpv","title":"DPV — Data Privacy Vocabulary","type":"vocabulary","description":"W3C-стандарт для описания обработки персональных данных: GDPR-compliance, цели, правовые основания, риски, технические меры.","targets":["https://w3c.github.io/dpv/dpv/"],"formats":["ttl","jsonld","owl"],"domain":"Legal / Privacy","industry":["all"],"tags":["GDPR","privacy","data processing","compliance","legal","consent"],"quality":0.95,"status":"verified","source":"w3c.org","entities":["PersonalData","Processing","Purpose","LegalBasis","DataSubject","DataController","DataProcessor","Consent","Risk","TechnicalMeasure"],"questions_hint":"Работаете с персональными данными EU? Есть ли DPA? Нужна GDPR-документация?"},
  {"id":"ifc-owl","w3id":"https://w3id.org/ifcOWL","title":"IFC OWL — Industry Foundation Classes","type":"ontology","description":"OWL-сериализация IFC: полная модель строительных объектов для BIM-обмена. Охватывает геометрию, материалы, MEP-системы.","targets":["https://technical.buildingsmart.org/"],"formats":["ttl","owl"],"domain":"BIM / Architecture","industry":["construction","architecture","facility"],"tags":["BIM","IFC","architecture","geometry","MEP","materials"],"quality":0.93,"status":"verified","source":"buildingsmart.org","entities":["IfcBuilding","IfcWall","IfcSpace","IfcDoor","IfcWindow","IfcColumn","IfcBeam","IfcMaterial","IfcSystem"],"questions_hint":"Используется ли BIM-ПО? Нужна ли интеграция с Revit/ArchiCAD? Есть ли 3D-модели объектов?"},
  {"id":"foodon","w3id":"https://w3id.org/foodon","title":"FoodOn — Food Ontology","type":"ontology","description":"Широкое покрытие пищевой отрасли: продукты, ингредиенты, технологические процессы, происхождение, безопасность. Используется в агро/фудтех.","targets":["https://foodon.org/"],"formats":["owl","ttl"],"domain":"Food / Agriculture","industry":["food","agriculture","horeca","brewing"],"tags":["food","beverage","ingredients","processing","agriculture","HACCP","origin"],"quality":0.92,"status":"verified","source":"foodon.org","entities":["FoodProduct","FoodMaterial","Ingredient","Recipe","ProcessStep","Origin","Allergen","Packaging","StorageCondition"],"questions_hint":"Производите или перерабатываете продукты? Есть рецептуры? Отслеживаете происхождение ингредиентов?"},
  {"id":"seas","w3id":"https://w3id.org/seas","title":"SEAS — Smart Energy Aware Systems","type":"ontology","description":"Онтология для энергосистем: потребление, генерация, прогнозирование, умные счётчики, сети. Базируется на SOSA/SSN.","targets":["https://github.com/thesmartenergy/seas"],"formats":["ttl","owl","rdf"],"domain":"Energy / Utilities","industry":["energy","utilities","manufacturing","smartcity"],"tags":["energy","smart grid","forecasting","meters","renewable","IoT"],"quality":0.90,"status":"verified","source":"w3id.org","entities":["ElectricPowerSystem","SmartMeter","Forecast","LoadProfile","EnergyStorage","Inverter","Grid","Tariff"],"questions_hint":"Контролируете энергопотребление? Есть ли солнечные/ветровые установки? Нужна аналитика по тарифам?"},
  {"id":"gist","w3id":"https://w3id.org/gist","title":"Gist — Core Enterprise Ontology","type":"ontology","description":"Минималистичная верхняя онтология для корпоративной интеграции данных: события, место, организация, продукт, задача, транзакция.","targets":["https://www.semanticarts.com/gist/"],"formats":["ttl","owl"],"domain":"Enterprise / Upper","industry":["all"],"tags":["enterprise","upper ontology","integration","events","transactions"],"quality":0.90,"status":"verified","source":"semanticarts.com","entities":["Organization","Place","Event","Task","Transaction","Product","Collection","Agreement","TimeInstant","Magnitude"],"questions_hint":"Как устроена юридическая структура компании? Есть ли дочерние организации, филиалы, холдинги?"},
  {"id":"iof","w3id":"https://www.industrialontologies.org","title":"IOF — Industrial Ontology Foundry","type":"ontology","description":"Набор эталонных онтологий для цифрового производства: активы, процессы, обслуживание, качество. Совместимо с BFO.","targets":["https://www.industrialontologies.org/"],"formats":["ttl","owl"],"domain":"Industry 4.0 / Manufacturing","industry":["manufacturing","automotive","aerospace"],"tags":["manufacturing","Industry 4.0","assets","maintenance","quality","IOF","BFO"],"quality":0.88,"status":"verified","source":"industrialontologies.org","entities":["ManufacturingProcess","Asset","Equipment","MaintenanceAction","QualityCharacteristic","WorkOrder","Batch","ProductionOrder"],"questions_hint":"Есть ли PLM или MES системы? Ведётся ли учёт оборудования? Как контролируется качество?"},
  {"id":"qudt","w3id":"https://w3id.org/qudt","title":"QUDT — Quantities, Units, Dimensions","type":"ontology","description":"Онтология единиц измерения и физических величин для науки, инженерии, измерительных систем.","targets":["https://qudt.org/"],"formats":["ttl","owl","rdf"],"domain":"Science / Engineering","industry":["manufacturing","science","engineering"],"tags":["units","measurements","quantities","SI","engineering"],"quality":0.95,"status":"verified","source":"qudt.org","entities":["QuantityKind","Unit","Quantity","Dimension","SystemOfUnits"],"questions_hint":"Используются ли специфические единицы измерения? Есть ли конвертация единиц в системах?"},
  {"id":"uco","w3id":"https://w3id.org/uco","title":"UCO — Unified Cyber Ontology","type":"ontology","description":"Онтология для кибербезопасности и цифровой криминалистики: события, доказательства, артефакты, личности, действия.","targets":["https://unifiedcyberontology.org/"],"formats":["ttl","owl","jsonld"],"domain":"Cybersecurity","industry":["cybersecurity","government","finance"],"tags":["cybersecurity","forensics","STIX","investigation","threat intelligence"],"quality":0.89,"status":"verified","source":"unifiedcyberontology.org","entities":["CyberItem","ObservableObject","Action","Identity","Tool","ThreatActor","Vulnerability","Incident"],"questions_hint":"Есть ли SOC или команда ИБ? Нужна ли интеграция с SIEM? Ведётся ли threat intelligence?"},
  {"id":"prov-o","w3id":"https://www.w3.org/TR/prov-o/","title":"PROV-O — Provenance Ontology","type":"ontology","description":"W3C-стандарт для описания происхождения данных: сущности, действия, агенты, производные, атрибуции.","targets":["https://www.w3.org/TR/prov-o/"],"formats":["ttl","owl","rdf"],"domain":"Data Governance","industry":["all"],"tags":["provenance","lineage","W3C","audit","FAIR","data governance"],"quality":0.99,"status":"verified","source":"w3c.org","entities":["Entity","Activity","Agent","Usage","Generation","Derivation","Attribution","Revision"],"questions_hint":"Откуда берётся данные в системах? Нужна ли аудиторская трассировка? Важна ли FAIR-compliance?"},
  {"id":"dcat","w3id":"https://www.w3.org/TR/vocab-dcat/","title":"DCAT — Data Catalog Vocabulary","type":"vocabulary","description":"W3C-словарь для публикации каталогов датасетов. Описывает датасеты, дистрибутивы, сервисы данных, каталоги.","targets":["https://www.w3.org/TR/vocab-dcat/"],"formats":["ttl","rdf","jsonld"],"domain":"Data Catalog / FAIR","industry":["all"],"tags":["catalog","datasets","FAIR","metadata","W3C","data management"],"quality":0.99,"status":"verified","source":"w3c.org","entities":["Catalog","Dataset","Distribution","DataService","CatalogRecord","Resource"],"questions_hint":"Есть ли внутренний каталог данных? Нужен ли FAIR data management? Публикуете ли open data?"},
  {"id":"org","w3id":"https://www.w3.org/TR/vocab-org/","title":"W3C Organization Ontology","type":"ontology","description":"W3C-онтология для описания структуры организаций: подразделения, роли, сайты, участия, смены.","targets":["https://www.w3.org/TR/vocab-org/"],"formats":["ttl","rdf"],"domain":"Enterprise / HR","industry":["all"],"tags":["organization","HR","structure","departments","roles","W3C"],"quality":0.97,"status":"verified","source":"w3c.org","entities":["Organization","OrganizationalUnit","Role","Membership","Site","Post","ChangeEvent"],"questions_hint":"Как устроена структура компании? Есть ли организационная схема? Используется ли HR-система?"},
  {"id":"gr","w3id":"https://www.heppnetz.de/ontologies/goodrelations/v1","title":"GoodRelations — Business Ontology","type":"ontology","description":"Онтология для e-commerce: предложения, продавцы, цены, гарантии, условия доставки, способы оплаты.","targets":["https://www.heppnetz.de/ontologies/goodrelations/v1"],"formats":["owl","rdf"],"domain":"E-commerce / Retail","industry":["retail","e-commerce","services"],"tags":["e-commerce","offers","prices","payments","delivery","warranties"],"quality":0.88,"status":"verified","source":"heppnetz.de","entities":["Offering","BusinessEntity","PriceSpecification","PaymentMethod","DeliveryMethod","Warranty","TypeAndQuantityNode","ProductOrService"],"questions_hint":"Как формируются цены? Какие способы оплаты принимаются? Есть ли гарантия на товары/услуги?"},
  {"id":"lean-alliance","w3id":"https://www.lean.org/lexicon-terms","title":"Lean Manufacturing Lexicon","type":"taxonomy","description":"Таксономия принципов и методов Lean: VSM, 5S, Kaizen, Kanban, SMED, TPM. Используется как базис для опросников по производству.","targets":["https://www.lean.org/lexicon-terms/"],"formats":["html"],"domain":"Manufacturing / Lean","industry":["manufacturing","logistics","automotive"],"tags":["lean","manufacturing","VSM","5S","Kaizen","Kanban","waste","Toyota"],"quality":0.85,"status":"candidate","source":"lean.org","entities":["ValueStream","Waste","Takt","Kanban","Kaizen","5S","PullSystem","CycleTime","OEE"],"questions_hint":"Внедрены ли Lean/Kaizen практики? Как измеряется OEE? Есть ли система управления потерями?"},
  {"id":"hl7-fhir","w3id":"https://www.hl7.org/fhir","title":"HL7 FHIR — Healthcare Interoperability","type":"standard","description":"Международный стандарт обмена медицинскими данными: пациенты, диагнозы, назначения, результаты анализов, страхование.","targets":["https://www.hl7.org/fhir/"],"formats":["jsonld","rdf","xml"],"domain":"Healthcare / Medicine","industry":["healthcare","pharma","insurance"],"tags":["healthcare","FHIR","HL7","patients","diagnoses","EHR","clinical"],"quality":0.97,"status":"verified","source":"hl7.org","entities":["Patient","Practitioner","Organization","Encounter","Condition","Observation","MedicationRequest","Procedure","Claim","Coverage"],"questions_hint":"Ведётся ли электронная медицинская карта? Есть ли интеграция с ЛИС/РИС? Нужна ли телемедицина?"},
  {"id":"cim-energy","w3id":"https://www.iec.ch/cim","title":"IEC CIM — Common Information Model Energy","type":"standard","description":"IEC-стандарт для электросетей: топология сети, активы, SCADA-данные, оперативное управление, балансирование.","targets":["https://cimug.ucaiug.org/"],"formats":["ttl","owl","rdf"],"domain":"Energy / Power Grid","industry":["energy","utilities"],"tags":["power grid","utilities","IEC","SCADA","transmission","distribution"],"quality":0.91,"status":"verified","source":"iec.ch","entities":["ACLineSegment","Substation","BusbarSection","Breaker","EnergyConsumer","GeneratingUnit","Transformer","Load"],"questions_hint":"Управляете ли электросетью? Есть SCADA? Нужна интеграция с системами диспетчеризации?"},
  {"id":"digitwin","w3id":"https://w3id.org/DigiTwin","title":"Digital Twin Ontology","type":"ontology","description":"Онтология для цифровых двойников промышленных объектов: asset, simulation, monitoring, event correlation.","targets":["https://github.com/DigiTwinProject"],"formats":["ttl","owl"],"domain":"Industry / Digital Twin","industry":["manufacturing","automotive","aerospace"],"tags":["digital twin","simulation","Industry 4.0","monitoring","asset"],"quality":0.82,"status":"candidate","source":"w3id.org","entities":["DigitalTwin","PhysicalAsset","SimulationModel","ObservedState","Alert","SynchronizationPoint"],"questions_hint":"Есть ли цифровые модели оборудования? Используется ли предиктивное обслуживание?"},
  {"id":"ssn-sosa","w3id":"https://www.w3.org/TR/vocab-ssn/","title":"SSN/SOSA — Sensor & Observation Ontology","type":"ontology","description":"W3C-стандарт для сенсорных данных: датчики, платформы, наблюдения, сэмплы, свойства. Базис для IoT-данных.","targets":["https://www.w3.org/TR/vocab-ssn/"],"formats":["ttl","owl","rdf"],"domain":"IoT / Sensors","industry":["iot","manufacturing","environment","agriculture"],"tags":["sensors","IoT","observations","W3C","SSN","SOSA","platforms"],"quality":0.98,"status":"verified","source":"w3c.org","entities":["Sensor","Platform","Observation","Sample","Feature","Property","Procedure","Actuator"],"questions_hint":"Собираются ли данные с датчиков? Нужна ли интеграция с SCADA/IoT-платформами?"},
  {"id":"wikidata-ont","w3id":"https://www.wikidata.org/wiki/Wikidata:Main_Page","title":"Wikidata Ontology","type":"vocabulary","description":"Связанный граф знаний: 100M+ элементов, кросс-доменные свойства. Используется для обогащения данных, NER, knowledge base linking.","targets":["https://www.wikidata.org/"],"formats":["rdf","jsonld","ttl"],"domain":"Knowledge Graph","industry":["all"],"tags":["knowledge graph","entities","LOD","cross-domain","enrichment"],"quality":0.98,"status":"verified","source":"wikidata.org","entities":["Item","Property","Statement","Reference","Qualifier","Label","Description","Alias"],"questions_hint":"Нужно ли связывать данные с внешними источниками? Важна ли геолокация, категории, отраслевые коды?"},
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id TEXT PRIMARY KEY,
            title TEXT,
            w3id TEXT,
            type TEXT,
            description TEXT,
            domain TEXT,
            quality REAL,
            status TEXT,
            source TEXT,
            questions_hint TEXT,
            targets JSON,
            formats JSON,
            industry JSON,
            tags JSON,
            entities JSON
        )
    ''')
    conn.commit()
    return conn

def calculate_quality(item):
    score = 0.2 # base score
    desc = item.get('description', '')
    if desc and len(desc) > 50:
        score += 0.2
    if item.get('targets') and len(item.get('targets')) > 0:
        score += 0.2
    if item.get('formats') and len(item.get('formats')) > 0:
        score += 0.2
    if item.get('source') in ['lov', 'w3c', 'w3id.org']:
        score += 0.2
    
    score = min(score, 1.0)
    
    if score >= 0.8:
        status = 'verified'
    elif score >= 0.5:
        status = 'candidate'
    else:
        status = 'weak'
        
    return score, status

def insert_data(conn, data):
    cursor = conn.cursor()
    inserted = 0
    for item in data:
        # Check if already exists
        cursor.execute("SELECT id FROM resources WHERE id=?", (item.get('id'),))
        if cursor.fetchone():
            continue
            
        score, status = calculate_quality(item)
        
        # Override with explicit values if provided
        final_score = item.get('quality', score)
        final_status = item.get('status', status)
            
        cursor.execute('''
            INSERT INTO resources (
                id, title, w3id, type, description, domain, quality, status, source, questions_hint,
                targets, formats, industry, tags, entities
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.get('id'),
            item.get('title'),
            item.get('w3id', ''),
            item.get('type', 'ontology'),
            item.get('description', ''),
            item.get('domain', 'Universal / Web'),
            final_score,
            final_status,
            item.get('source', ''),
            item.get('questions_hint', ''),
            json.dumps(item.get('targets', [])),
            json.dumps(item.get('formats', [])),
            json.dumps(item.get('industry', [])),
            json.dumps(item.get('tags', [])),
            json.dumps(item.get('entities', []))
        ))
        inserted += 1
    
    conn.commit()
    print(f"Inserted {inserted} new items into database.")

def fetch_from_lov():
    print("Fetching from LOV API...")
    try:
        response = requests.get('https://lov.linkeddata.es/dataset/lov/api/v2/vocabulary/list', timeout=20)
        if response.status_code == 200:
            vocabularies = response.json()
            data = []
            for v in vocabularies:
                uri = v.get('uri', '')
                prefix = v.get('nsp', '')
                
                title = prefix
                if v.get('titles') and len(v['titles']) > 0:
                    title = v['titles'][0].get('value', prefix)
                
                desc = ''
                if v.get('descriptions') and len(v['descriptions']) > 0:
                    desc = v['descriptions'][0].get('value', '')
                    
                tags = v.get('tags', [])
                
                item = {
                    'id': f"lov-{prefix}",
                    'w3id': uri,
                    'title': title,
                    'type': 'vocabulary',
                    'description': desc,
                    'domain': 'Linked Open Data',
                    'targets': [uri],
                    'formats': ['ttl', 'rdf'],
                    'industry': ['all'],
                    'tags': tags + ['LOV'],
                    'source': 'lov',
                    'entities': []
                }
                data.append(item)
            return data
        else:
            print(f"LOV returned status {response.status_code}")
    except Exception as e:
        print(f"Failed to fetch from LOV: {e}")
    return []

def fetch_readme(path):
    url = f"https://raw.githubusercontent.com/perma-id/w3id.org/master/{path}"
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f"token {GITHUB_TOKEN}"
        
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            content = res.text
            # Basic markdown parsing
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else path.split('/')[0]
            
            # Find first non-empty line that isn't a heading
            desc = ""
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('['):
                    desc = line
                    break
            
            # Limit description length
            if len(desc) > 300:
                desc = desc[:297] + "..."
                
            return {
                'id': f"w3id-{path.split('/')[0]}",
                'w3id': f"https://w3id.org/{path.split('/')[0]}",
                'title': title,
                'type': 'ontology',
                'description': desc,
                'domain': 'W3ID Project',
                'targets': [f"https://github.com/perma-id/w3id.org/tree/master/{path.split('/')[0]}"],
                'formats': ['ttl'],
                'industry': ['all'],
                'tags': ['W3ID'],
                'source': 'w3id.org',
                'entities': []
            }
    except Exception as e:
        pass
    return None

def fetch_from_w3id():
    print("Fetching W3ID projects from GitHub...")
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f"token {GITHUB_TOKEN}"
    
    try:
        res = requests.get('https://api.github.com/repos/perma-id/w3id.org/git/trees/master?recursive=1', headers=headers, timeout=20)
        if res.status_code == 200:
            tree = res.json().get('tree', [])
            readmes = [t['path'] for t in tree if t['path'].lower().endswith('readme.md') and t['path'].count('/') == 1]
            print(f"Found {len(readmes)} projects with READMEs. Downloading...")
            
            data = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                # Process all of them via thread pool
                results = list(executor.map(fetch_readme, readmes))
                
                for r in results:
                    if r:
                        data.append(r)
            return data
        else:
            print(f"GitHub API returned status {res.status_code}")
    except Exception as e:
        print(f"Failed to fetch from GitHub: {e}")
    return []

if __name__ == '__main__':
    print("Initializing Ontology Discovery Catalog DB...")
    conn = init_db()
    
    # 1. Insert fixed initial data
    insert_data(conn, INITIAL_DATA)
    
    # 2. Fetch and insert LOV data
    lov_data = fetch_from_lov()
    if lov_data:
        insert_data(conn, lov_data)
        
    # 3. Fetch and insert W3ID data
    w3id_data = fetch_from_w3id()
    if w3id_data:
        insert_data(conn, w3id_data)
        
    conn.close()
    print("Enrichment complete!")
