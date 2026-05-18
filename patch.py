import sys

content = open('static/index.html', 'r', encoding='utf-8').read()

# 1. Add Pagination UI and Enrich Button styling
css_add = '''
.pagination { padding: 1.5rem; display: flex; justify-content: center; align-items: center; gap: 0.5rem; }
.page-btn { padding: 0.4rem 0.8rem; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); cursor: pointer; color: var(--color-text); }
.page-btn:hover { background: var(--color-surface-dynamic); }
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.page-btn.active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.enrich-btn { position: absolute; top: 1rem; right: 1rem; padding: 0.4rem; border-radius: var(--radius-md); background: var(--color-surface-offset); border: 1px solid var(--color-border); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; z-index: 10; }
.enrich-btn:hover { background: var(--color-purple-highlight); border-color: var(--color-purple); color: var(--color-purple); }
.enrich-btn.loading { opacity: 0.7; cursor: wait; animation: pulse 1.5s infinite; }
@keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
'''
content = content.replace('/* Layout */', css_add + '\n/* Layout */')

# 2. Add Pagination container
content = content.replace('<div class="catalog" id="catalog"></div>', '<div class="catalog" id="catalog"></div>\n      <div class="pagination" id="pagination"></div>')

# 3. Rewrite the JS section
js_start = content.find('let CATALOG = [];')
js_end = content.find('</script>', js_start)

new_js = '''let CATALOG = [];
let currentPage = 1;
let totalPages = 1;
let totalItems = 0;

// Domain → CSS class mapping
const DOMAIN_CLASS = {
  "Universal / Web":"dom-web","Enterprise / Operations":"dom-enterprise","Industry Classification":"dom-data",
  "Supply Chain / Retail":"dom-industry","Procurement / Catalog":"dom-industry","Finance / Banking":"dom-finance",
  "IoT / Smart Home":"dom-iot","BIM / Construction":"dom-bim","Legal / Privacy":"dom-legal",
  "BIM / Architecture":"dom-bim","Food / Agriculture":"dom-food","Energy / Utilities":"dom-energy",
  "Industry 4.0 / Manufacturing":"dom-industry","Science / Engineering":"dom-science","Cybersecurity":"dom-cyber",
  "Data Governance":"dom-data","Data Catalog / FAIR":"dom-data","Enterprise / HR":"dom-enterprise",
  "E-commerce / Retail":"dom-enterprise","Manufacturing / Lean":"dom-industry","Healthcare / Medicine":"dom-health",
  "Energy / Power Grid":"dom-energy","Industry / Digital Twin":"dom-industry","IoT / Sensors":"dom-iot",
  "Knowledge Graph":"dom-kg","Enterprise / Upper":"dom-enterprise"
};
const TYPE_COLOR = {ontology:"var(--color-primary)",vocabulary:"var(--color-blue)",taxonomy:"var(--color-gold)",framework:"var(--color-orange)",standard:"var(--color-success)"};

let activeFilters = {type:"all",industry:null,status:null,format:null};
let viewMode = "grid";
let searchQuery = "";
let selectedItem = null;
let selectedEntities = [];

function getDomainClass(domain){return DOMAIN_CLASS[domain]||"dom-enterprise";}
function qualityColor(q){return q>=0.95?"var(--color-success)":q>=0.85?"var(--color-primary)":"var(--color-warning)";}

async function fetchPage(page = 1) {
    currentPage = page;
    let url = `/api/resources?page=${page}&limit=50`;
    if(searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;
    if(activeFilters.type && activeFilters.type !== "all") url += `&type=${encodeURIComponent(activeFilters.type)}`;
    if(activeFilters.status) url += `&status=${encodeURIComponent(activeFilters.status)}`;
    if(activeFilters.industry) url += `&industry=${encodeURIComponent(activeFilters.industry)}`;
    if(activeFilters.format) url += `&format=${encodeURIComponent(activeFilters.format)}`;
    
    try {
        const res = await fetch(url);
        if(!res.ok) throw new Error("API Error");
        const json = await res.json();
        CATALOG = json.data;
        totalPages = json.total_pages;
        totalItems = json.total;
        render();
        renderPagination();
    } catch(err) {
        console.error(err);
    }
}

async function enrichItem(id, event) {
    if(event) event.stopPropagation();
    const btn = document.getElementById(`enrich-btn-${id}`);
    if(btn) btn.classList.add('loading');
    
    try {
        const res = await fetch(`/api/resources/${id}/enrich`, { method: 'POST' });
        if(res.ok) {
            const updated = await res.json();
            const idx = CATALOG.findIndex(c => c.id === id);
            if(idx !== -1) {
                CATALOG[idx] = updated;
                render();
            }
            if(selectedItem && selectedItem.id === id) {
                openDetail(id); // Re-render detail panel
            }
        }
    } catch(err) {
        console.error("Enrichment failed", err);
    }
}

function renderStats(){
  const row = document.getElementById("stats-row");
  row.innerHTML = `
    <div class="stat-item"><span class="stat-num">${totalItems}</span><span class="stat-label">Найдено</span></div>
    <div class="stat-item" style="border-left:1px solid var(--color-divider);padding-left:1rem"><span class="stat-num">${currentPage} / ${totalPages || 1}</span><span class="stat-label">Страница</span></div>
  `;
}

function renderCard(item){
  const dc = getDomainClass(item.domain);
  const qw = Math.round(item.quality*100);
  const tags = item.tags || [];
  const sdesc = item.short_description || item.description;
  const isEnriched = tags.includes("AI Enriched");
  
  return `<div class="card" onclick="openDetail('${item.id}')" style="position:relative;">
    <button id="enrich-btn-${item.id}" class="enrich-btn" onclick="enrichItem('${item.id}', event)" title="🪄 Обогатить через AI">
        ${isEnriched ? '✨' : '🪄'}
    </button>
    <div class="card-top" style="padding-right: 2rem;">
      <div class="card-title">${item.title}</div>
      <div class="card-id">${item.id}</div>
    </div>
    <div class="card-desc">${sdesc}</div>
    <div class="card-meta">
      <span class="domain-badge ${dc}">${item.country_or_region || item.domain}</span>
      <span class="badge-status status-${item.status}">${item.status}</span>
      <div class="quality-bar" title="Quality: ${qw}%"><div class="quality-fill" style="width:${qw}%;background:${qualityColor(item.quality)}"></div></div>
    </div>
    <div class="card-formats">${(item.formats||[]).map(f=>`<span class="fmt">${f}</span>`).join("")}</div>
    <div class="card-tags">${tags.slice(0,5).map(t=>`<span class="tag" ${t==='AI Enriched'?'style="color:var(--color-purple);border-color:var(--color-purple);background:var(--color-purple-highlight)"':''}>${t}</span>`).join("")}</div>
  </div>`;
}

function renderListCard(item){
  const dc = getDomainClass(item.domain);
  const qw = Math.round(item.quality*100);
  const tags = item.tags || [];
  const sdesc = item.short_description || item.description;
  const isEnriched = tags.includes("AI Enriched");

  return `<div class="card" onclick="openDetail('${item.id}')" style="position:relative;">
    <div class="card-body" style="flex:1;min-width:0;padding-right: 2rem;">
      <div class="card-top"><div class="card-title" style="font-size:var(--text-sm)">${item.title}</div><div class="card-id">${item.id}</div></div>
      <div class="card-desc">${sdesc}</div>
      <div class="card-meta" style="margin-top:0.4rem">
        <span class="domain-badge ${dc}">${item.country_or_region || item.domain}</span>
        ${tags.slice(0,4).map(t=>`<span class="tag">${t}</span>`).join("")}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;flex-shrink:0">
      <span class="badge-status status-${item.status}">${item.status}</span>
      <div style="font-size:var(--text-xs);color:${qualityColor(item.quality)};font-weight:700;font-variant-numeric:tabular-nums">${qw}%</div>
      <div class="card-formats">${(item.formats||[]).map(f=>`<span class="fmt">${f}</span>`).join("")}</div>
      <button id="enrich-btn-${item.id}" class="enrich-btn" style="position:static; margin-top:0.5rem;" onclick="enrichItem('${item.id}', event)" title="🪄 Обогатить через AI">${isEnriched ? '✨' : '🪄'} Обогатить</button>
    </div>
  </div>`;
}

function render(){
  const items = CATALOG;
  const cat = document.getElementById("catalog");
  document.getElementById("result-count").textContent = `Найдено: ${totalItems}`;
  renderStats();
  if(!items.length){
    cat.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-faint)" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v3M11 14h.01"/></svg><h3>Ничего не найдено</h3><p>Попробуйте изменить фильтры или поисковый запрос</p></div>`;
    return;
  }
  cat.innerHTML = items.map(i => viewMode==="list" ? renderListCard(i) : renderCard(i)).join("");
}

function renderPagination() {
    const pag = document.getElementById("pagination");
    if(totalPages <= 1) {
        pag.innerHTML = "";
        return;
    }
    
    let html = `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="fetchPage(${currentPage - 1})">← Назад</button>`;
    
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, start + 4);
    if(end - start < 4) start = Math.max(1, end - 4);
    
    for(let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="fetchPage(${i})">${i}</button>`;
    }
    
    html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="fetchPage(${currentPage + 1})">Вперед →</button>`;
    pag.innerHTML = html;
}

function buildSidebarFilters(){
  document.querySelectorAll(".filter-chip[data-group]").forEach(btn=>{
    btn.addEventListener("click",()=>{
      const group = btn.dataset.group;
      const val = btn.dataset.filter;
      document.querySelectorAll(`.filter-chip[data-group="${group}"]`).forEach(b=>b.classList.remove("active"));
      if(activeFilters[group]===val && group!=="type"){
        activeFilters[group]=null;
      } else {
        btn.classList.add("active");
        activeFilters[group]= group==="type" ? val : (activeFilters[group]===val?null:val);
        if(group!=="type") btn.classList.toggle("active", activeFilters[group]!==null);
      }
      if(group==="type") btn.classList.add("active");
      fetchPage(1); // Re-fetch on filter change
    });
  });
}

function setView(mode){
  viewMode=mode;
  document.getElementById("catalog").className = "catalog"+(mode==="list"?" list-view":"");
  document.getElementById("grid-btn").classList.toggle("active",mode==="grid");
  document.getElementById("list-btn").classList.toggle("active",mode==="list");
  render();
}

function generateQuestionnaire(item, entities){
  const ents = entities.length > 0 ? entities : (item.entities||[]).slice(0,8);
  if(!ents.length) return `<div style="color:var(--color-text-faint)">Нет сущностей для генерации опросника.</div>`;
  const templates = [
    e=>`Используете ли вы понятие <span class="q-entity">${e}</span> в своей работе? Как оно называется у вас?`,
    e=>`Как организован учёт <span class="q-entity">${e}</span>? Ведётся ли реестр или справочник?`,
    e=>`Кто в компании отвечает за управление <span class="q-entity">${e}</span>?`,
    e=>`Какие ключевые атрибуты есть у <span class="q-entity">${e}</span>? Что важно знать о каждом?`,
    e=>`Как <span class="q-entity">${e}</span> связан с другими элементами бизнеса?`,
    e=>`Есть ли у вас автоматизация для работы с <span class="q-entity">${e}</span>? Какая система?`,
  ];
  return ents.map((e,i)=>`<div class="q-item"><span class="q-num">${i+1}.</span><span class="q-text">${templates[i%templates.length](e)}</span></div>`).join("");
}

function openDetail(id){
  const item = CATALOG.find(c=>c.id===id);
  if(!item) return;
  selectedItem = item;
  selectedEntities = [];
  document.getElementById("panel-title").textContent = item.title;
  const dc = getDomainClass(item.domain);
  const qw = Math.round(item.quality*100);
  const sdesc = item.short_description || item.description;
  const region = item.country_or_region || "Не указан";
  const scope = item.coverage_scope || "Не указан";
  
  document.getElementById("panel-body").innerHTML = `
    <div>
      <div style="display:flex; justify-content:space-between; align-items:center">
        <div class="panel-section-title">Описание</div>
        <button class="btn btn-sm btn-ghost" onclick="enrichItem('${item.id}', event)">🪄 Обогатить через AI</button>
      </div>
      <p style="font-size:var(--text-xs);color:var(--color-text-muted);line-height:1.6">${sdesc}</p>
    </div>
    <div style="display:flex; gap:1rem; flex-wrap:wrap; padding: 1rem; background: var(--color-surface-offset); border-radius: var(--radius-md); border: 1px solid var(--color-border);">
        <div><div style="font-size:0.65rem; color:var(--color-text-faint); text-transform:uppercase">Страна/Регион</div><div style="font-weight:600">${region}</div></div>
        <div><div style="font-size:0.65rem; color:var(--color-text-faint); text-transform:uppercase">Масштаб</div><div style="font-weight:600">${scope}</div></div>
    </div>
    <div>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center">
        <span class="domain-badge ${dc}">${item.domain}</span>
        <span class="badge-status status-${item.status}">${item.status}</span>
        <span class="domain-badge" style="background:color-mix(in oklch,${TYPE_COLOR[item.type]||"var(--color-primary)"} 15%,var(--color-surface));color:${TYPE_COLOR[item.type]||"var(--color-primary)"}">${item.type}</span>
      </div>
    </div>
    <div>
      <div class="panel-section-title">Quality Score</div>
      <div class="quality-big">
        <span class="quality-num">${qw}%</span>
        <div class="quality-bar-big"><div class="quality-fill-big" style="width:${qw}%;background:${qualityColor(item.quality)}"></div></div>
      </div>
    </div>
    <div>
      <div class="panel-section-title">Теги и Форматы</div>
      <div class="entity-grid" style="margin-bottom:0.75rem">
        ${(item.formats||[]).map(f=>`<span class="fmt">${f}</span>`).join("")}
      </div>
      <div class="entity-grid">
        ${(item.tags||[]).map(t=>`<span class="tag">${t}</span>`).join("")}
      </div>
    </div>
    <div>
      <div class="panel-section-title">Источники</div>
      <div style="display:flex;flex-direction:column;gap:0.4rem">
        ${(item.targets||[]).map(url=>`<a href="${url}" target="_blank" class="url-link"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>${url}</a>`).join("")}
      </div>
    </div>
    <div>
      <div class="panel-section-title">Ключевые сущности (для опросника)</div>
      <p style="font-size:0.7rem;color:var(--color-text-faint);margin-bottom:0.5rem">Нажмите, чтобы включить/исключить из опросника</p>
      <div class="entity-grid" id="entity-selector">
        ${(item.entities||[]).map(e=>`<button class="entity-chip selected" onclick="toggleEntity('${e}')">${e}</button>`).join("")}
      </div>
    </div>
    <div class="questionnaire">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
        <div class="panel-section-title" style="margin:0">Анкета для бизнеса</div>
        <button class="btn btn-sm btn-ghost" onclick="refreshQuestionnaire()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/></svg> Обновить</button>
      </div>
      <div id="questionnaire">${generateQuestionnaire(item, [])}</div>
      <div style="margin-top:1rem;display:flex;justify-content:flex-end">
        <button class="btn btn-primary" onclick="alert('Скопировано в буфер обмена!')">Скопировать анкету</button>
      </div>
    </div>
  `;
  document.getElementById("detail-overlay").classList.add("open");
}

function toggleEntity(name){
  const el = Array.from(document.querySelectorAll("#entity-selector .entity-chip")).find(e=>e.textContent===name);
  if(!el) return;
  el.classList.toggle("selected");
  if(el.classList.contains("selected")){
    selectedEntities.push(name);
  } else {
    selectedEntities = selectedEntities.filter(e=>e!==name);
  }
  if(selectedItem) document.getElementById("questionnaire").innerHTML = generateQuestionnaire(selectedItem, selectedEntities);
}

function refreshQuestionnaire(){
  if(selectedItem) document.getElementById("questionnaire").innerHTML = generateQuestionnaire(selectedItem, selectedEntities);
}

function closeDetail(e){
  if(!e || e.target===document.getElementById("detail-overlay")){
    document.getElementById("detail-overlay").classList.remove("open");
    selectedItem=null;selectedEntities=[];
  }
}

// Debounce search
let searchTimeout;
document.getElementById("search").addEventListener("input",e=>{
  searchQuery = e.target.value;
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    fetchPage(1);
  }, 300);
});

async function initApp() {
  buildSidebarFilters();
  fetchPage(1);
}

initApp();
'''

content = content[:js_start] + new_js + '\n</script>\n</body>\n</html>'
open('static/index.html', 'w', encoding='utf-8').write(content)
print('Updated index.html')
