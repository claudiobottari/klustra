# klustra — Specifica di progetto

**Recursive knowledge abstraction engine.** Da file eterogenei a wiki OKF gerarchica: concepts → cluster → home.
**Versione:** 0.2-draft · **Licenza:** da decidere prima del primo commit · **Runtime:** Python ≥ 3.11
**Nome:** `klustra` (confermato libero su PyPI)
**Prior art di riferimento:** Karpathy LLM Wiki (gist apr-2026), OKF v0.1 (GoogleCloudPlatform/knowledge-catalog), RAPTOR (Sarthi et al., ICLR 2024), llm-wiki-compiler (atomicstrata), llm_wiki (nashsu), okf-gem/okflint (validator ecosystem).

---

## 1. Obiettivo

Libreria Python + CLI che:
1. Ingesta fonti eterogenee (file, folder ricorsive, in futuro URL/SharePoint/blob) tramite **translator pluggable**
2. Compila pagine OKF di livello 0 (`concept`/`entity`) con provenienza esatta e wikilinks
3. **Astrae ricorsivamente**: clusterizza i concepts, genera pagine `cluster` di livello crescente fino a una `home` per dominio (pattern RAPTOR applicato a pagine wiki invece che a chunk)
4. Mantiene la wiki incrementalmente (add/modify/delete di singole fonti)
5. Esporta su target multipli (filesystem OKF/Obsidian, HTML, Delta)
6. Espone API di contesto per agent retrieval (concept + antenati cluster)

Non-goal v1: UI, serving, embedding server proprio, auth SharePoint (arriva con il translator URL).

**Nota di rischio progettuale (da letteratura):** la wiki compilata costa più token in query rispetto a RAG piatto e il vantaggio si materializza su domande di sintesi multi-fonte, non su lookup puntuali (Cochran 2026, preregistrato). Conseguenza: il retrieval deve attivare la gerarchia solo dove serve (§7.3) e la context API è parsimoniosa di default (§7.2).

---

## 2. Architettura — moduli

```
klustra/
├── core/           # modelli dati (pydantic), config, StateStore, ChangeSet
├── ingestion/      # source manager, translator registry, DomainRegistry + SourceConnector (§4.4)
├── translators/    # un modulo per formato (excel.py, markdown.py, text.py, ...)
├── engine/         # compile two-phase + librarian + validate/lint
├── hierarchy/      # clustering ricorsivo + cluster/home pages + judge
├── linking/        # wikilink resolver + link graph (deterministico)
├── exporters/      # okf_bundle, obsidian, html, delta
├── llm/            # provider abstraction + prompt registry + token budget
│   └── prompts/    # default prompts (Jinja2 .md)
├── cli.py          # entrypoint CLI (typer)
└── api.py          # facade libreria (class Klustra)
tests/              # pytest; fixture: mini-corpus per dominio + golden bundle
```

Dipendenze: `pydantic>=2`, `typer`, `hdbscan`, `scikit-learn` (GMM opzionale), `umap-learn`, `numpy`, `openai`, `anthropic`, `pyyaml`, `jinja2`, `openpyxl`. Extra opzionali: `klustra[delta]` (databricks-sdk, delta), `klustra[pdf]` (docling).

---

## 3. Modello dati (core)

### 3.1 Page (frontmatter OKF-P)

```yaml
---
type: concept            # concept | entity | record-set | cluster | home | index
level: 0                 # 0 = atomico; cluster: 1..N; home: level max della gerarchia
entity_id: prod.cable.p-laser-320kv
title: "..."
description: "..."
aliases: []
domain: engineering
tags: [domain/hvdc, standard/iec-62895, status/verified]
confidence: 0.92
sources:                 # SOLO level 0. Percorso esatto + locator
  - source_id: "sha256:9f2a..."
    source_path: "sharepoint://sites/RD/datasheets/PL320.pdf"
    locator: "page:4/table:2"
    translator: "pdf@1.0"
children: []             # SOLO level >= 1: entity_id delle pagine aggregate
memberships: []          # SOLO level 0, se soft clustering attivo: cluster secondari (§6.1)
cluster_meta:            # SOLO type: cluster|home
  algo: hdbscan          # o gmm
  run_id: "..."
  cohesion: 0.78
superseded_by: null      # entity_id del cluster successore, se superseded (§6.4)
created_at: ...
updated_at: ...
schema_version: "1.0"
---
```

Regole:
- `type: cluster` unico per tutti i livelli aggregati; il livello è SOLO in `level`. `home` = radice del dominio (una per dominio). Pagina meta cross-dominio (`domain: _meta`) solo debug, esclusa dal retrieval di default.
- `entity_id` = identità = path (`.` → `/`). Cluster: `cluster.<domain>.l<level>.<slug-stabile>`.
- Wikilinks nel body SOLO verso `entity_id` esistenti: `[[prod.family.p-laser]]`. Mai verso titoli, mai inventati.

### 3.2 StateStore (ABC)

Implementazioni: `FileStateStore` (v0.1: `.klustra/state.json` + vault filesystem — CLI standalone) e `DeltaStateStore` (v1.0: tabelle pages/records/links/sources come da spec storage OKF-P separata).
Traccia: sources (SHA-256, path, translator, stato, timestamps), pages (entity_id → source_ids, level, content-hash, embedding-hash), link graph, run log. Ogni mutazione riporta `run_id`.

### 3.3 ChangeSet

Output di ogni operazione di ingestion e input del compile incrementale:
`{sources: {added, modified, removed}, pages: {added, updated, removed, affected}}`.

---

## 4. Ingestion e Translators

### 4.1 Pattern: Strategy + Registry

```python
class Translator(ABC):
    name: str                    # "excel"
    version: str                 # "1.0" — nella provenienza
    extensions: set[str]         # {".xlsx", ".xls", ".xlsm"}
    schemes: set[str] = set()    # future: {"sharepoint", "https"}
    deterministic: bool = True   # False per translator agentici (stesso contratto output)

    @abstractmethod
    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult: ...

class TranslationResult(BaseModel):
    units: list[KnowledgeUnit]   # 1 source → N unità
    source_metadata: dict
    warnings: list[str]

class KnowledgeUnit(BaseModel):
    unit_id: str                 # {source_id}#{seq} — deterministico
    kind: str                    # narrative | table | record_batch | image_text
    content_md: str
    records: list[dict] | None   # righe tidy se kind=table/record_batch
    locator: str                 # "sheet:Params!A1:F120" | "page:4/table:2"
    inherited_context: dict      # metadati ereditati (foglio, sezione, unità globali)
```

- `TranslatorRegistry.register(translator)`: estensione/scheme → translator. Formato custom = una classe, zero modifiche altrove.
- Translator deterministici: **zero LLM** (consenso unanime dell'ecosistema: fetch/convert deterministico separato dalla sintesi LLM). La semantica la fa l'engine.

### 4.2 ExcelTranslator (riferimento di qualità)

1 file → N unit:
1. Table detection per foglio (structural anchors: righe/colonne vuote, cambi tipo, merged headers); un foglio può produrre più unità.
2. Tabella → `KnowledgeUnit(kind="table")`: `content_md` = tabella markdown normalizzata (merged cells esplose), `records` = righe tidy tipizzate, `locator` = `sheet:{nome}!{range}`, `inherited_context` = {sheet_name, title_row, global_units, file_props}.
3. Testo fuori tabella → `kind="narrative"` per foglio.
4. Formule: `{"value": 42, "formula": "=B2*C2"}`.
5. Nessuna decisione semantica entity-vs-record: la fa l'engine.

### 4.3 Source manager

| Operazione | Libreria | CLI |
|---|---|---|
| Ingest file | `nx.ingest_file(path, domain=...)` | `klustra ingest FILE -d DOMAIN` |
| Ingest folder ricorsiva | `nx.ingest_folder(path, recursive=True, glob=...)` | `klustra ingest DIR -r` |
| Update file | `nx.update_source(path)` | `klustra update FILE` |
| Rimozione | `nx.remove_source(path)` | `klustra remove FILE` |
| Sync folder (diff) | `nx.sync_folder(path)` | `klustra sync DIR` |
| Compile | `nx.compile()` | `klustra compile` |
| Hierarchy | `nx.build_hierarchy()` | `klustra hierarchy` |
| Export | `nx.export(target, out)` | `klustra export obsidian -o DIR` |

- `sync_folder` = diff listing ↔ state → genera add/update/remove. Building block del futuro scheduler SharePoint (stesso diff, listing da Graph API delta query).
- Delete: cascade con **shared entity preservation** — rimuove il source da `sources[]`; pagina rigenerata dai rimanenti; zero sources → pagina rimossa, link entranti → lint.
- Tutte ritornano `ChangeSet`.

### 4.4 Domain Registry

Componente dedicato (`ingestion/domain_registry.py`) che espone la configurazione dei domini a tutto il resto del sistema. **v0.1: legge da file locali.** Nessun altro modulo tocca il file di config direttamente — se in futuro la sorgente diventa una tabella Delta o un servizio, cambia solo questo componente.

**Formato:** un file TOML per dominio in `.klustra/domains/<label>.toml` (coerente con `noesis.toml`/`.klustra/instructions/` già in spec — stesso stile, stessa cartella).

```toml
# .klustra/domains/engineering.toml
label = "engineering"
title = "Ingegneria — Cavi HVDC"
description = "Documentazione tecnica, datasheet, norme per la linea prodotti HVDC"

[[sources]]
type = "local_folder"       # unico tipo supportato in v0.1
path = "C:/data/engineering"
recursive = true
glob = ["*.xlsx", "*.pdf", "*.md"]

[[sources]]
type = "local_folder"
path = "C:/data/engineering-archive"
recursive = false
```

Il **prompt di contesto/comportamento per dominio** non duplica qui: resta `.klustra/instructions/<label>.md` (§10), agganciato per convenzione di naming (`label` del domain = filename delle instructions). Il domain file descrive *dove sono i dati*; le instructions descrivono *come trattarli*. Se le instructions non esistono per un `label`, il compile procede con le sole instructions di default e un warning.

**Modello dati:**

```python
class SourceConfig(BaseModel):
    type: str              # "local_folder" oggi; "sharepoint"|"blob" in futuro — stesso campo, valori nuovi
    # campi specifici per type, validati da uno schema per-type

class DomainConfig(BaseModel):
    label: str              # chiave primaria, matcha instructions/<label>.md
    title: str
    description: str
    sources: list[SourceConfig]   # una o più fonti per dominio
```

**Pattern Connector (parallelo a Translator, stesso registry):**

```python
class SourceConnector(ABC):
    type: str                # "local_folder"
    @abstractmethod
    def sync(self, source: SourceConfig, state: StateStore) -> ChangeSet: ...
```

`LocalFolderConnector` è l'unica implementazione v0.1 — wrappa `ingestion.sync_folder` già in §4.3 dietro questo contratto. Aggiungere `SharePointConnector`/`BlobConnector` in futuro significa: una classe nuova + un `type` nuovo nel TOML, **zero modifiche** a `DomainRegistry`, `engine/`, `hierarchy/` — stessa garanzia di estensibilità dei translator.

**Trigger di update (v0.1, entrambi manuali/espliciti — nessun polling automatico):**

| Meccanismo | Comando | Note |
|---|---|---|
| CLI manuale | `klustra sync --domain engineering` | Invoca il connector di ogni source del dominio, produce un `ChangeSet`, passa al compile. Per tutti i domini: `klustra sync --all` |
| Webhook (stub, endpoint pronto ma non collegato a nulla in v0.1) | `klustra webhook serve` | Espone un endpoint HTTP minimale che accetta `{domain, source_index}` e invoca lo stesso `sync()` del connector — pass-through, zero logica di parsing del payload del provider. L'integrazione reale con Graph API change notifications / Event Grid è v1.x (§15); qui si fissa solo il contratto: qualunque provider notifichi, il webhook traduce sempre nella stessa chiamata `connector.sync()` → `ChangeSet` → compile |

**Comandi CLI aggiuntivi:**

| Comando | Effetto |
|---|---|
| `klustra domain list` | Elenca i domini da `.klustra/domains/*.toml` |
| `klustra domain show LABEL` | Config risolta + stato ultimo sync + instructions collegate (o warning se mancanti) |
| `klustra sync --domain LABEL` / `--all` | Trigger manuale, per tutte le sources del dominio |

---

## 5. Engine — compile two-phase + Librarian

### Phase 1 — Extraction
Per ogni unit nuova/cambiata: LLM structured-output → concept candidates `{name, entity_id_proposal, summary, is_new, related_existing[]}`. Prompt riceve: unit, indice corrente del dominio filtrato per rilevanza (§9), instructions di dominio (§10).

### Dependency resolution
Reverse index concept→sources dallo state. Sources non cambiate che condividono concepts con quelle cambiate → ri-estratte nello stesso batch (un solo passaggio post-extraction, lo state completo è interrogabile).

### Phase 2 — Merge & generate (Librarian)
LLM che genera/aggiorna la pagina per concept, ricevendo tutti i contributi dei sources owner. Responsabilità nel prompt:
1. Sintesi coerente multi-contributo
2. **Obsolescenza**: claim in conflitto → prevale timestamp più recente; il claim scartato va in `## Storia e revisioni` con reference, mai silenziato
3. **Citazioni obbligatorie**: ogni claim fattuale → `^[source_id:locator]`; pagina senza citazioni = reject
4. **Wikilinks solo da lista chiusa** di entity_id forniti nel prompt

Post-generation (deterministico): validazione frontmatter (pydantic), resolver wikilinks (rule-based su alias-map), link graph update, scrittura atomica, index rebuild.

### 5.1 Validate vs Lint (separati, allineati all'ecosistema OKF)

| Comando | Domanda | Politica |
|---|---|---|
| `klustra validate` | Conformance OKF §9: frontmatter parseable, `type` non vuoto, path=identity, reserved files corretti | Hard error, blocca l'export okf_bundle. **Mai** errore per broken link o campi opzionali mancanti (per spec OKF sono "conoscenza non ancora scritta") |
| `klustra lint` | Qualità: reachability (orphans, isole disconnesse, non-in-index), completeness (stub, campi mancanti), freshness (`--stale-after`), provenance (claim non citati, citazioni rotte), hygiene (titoli duplicati, self-link), broken wikilinks | Warning di default; ogni categoria promuovibile a errore in config → quality gate del run |

Contraddizioni e staleness *semantica* sono fuori dal lint deterministico (richiedono comprensione): responsabilità del Librarian (§5.2) e di un check LLM schedulabile (`klustra lint --semantic`, v0.3).

---

## 6. Hierarchy engine (il cuore)

### 6.1 Algoritmo ricorsivo (RAPTOR-style su pagine)

```
level = 0; pages = concepts del dominio
loop:
    embeddings = embed(pages)                     # body_md; cache per content-hash
    reduced = UMAP(embeddings)                    # n_neighbors scala con |pages|
    clusters, outliers = cluster(reduced)         # v. sotto
    if n_top_nodes <= home_threshold (default 5) or len(clusters) <= 1:
        genera HOME (type: home, level=level+1); break
    for c in clusters:  genera pagina cluster (level=level+1, children=[...])
    outliers: pass-through al livello successivo (nessuna pagina placeholder)
    pages = cluster_pages + outliers; level += 1
```

**Clustering — decisione hard vs soft (configurabile per dominio, default hard):**
- `mode: "hard"` (default): HDBSCAN. Ogni concept ha un solo cluster padre → albero pulito, `children` è partizione. `min_cluster_size` configurabile (default 4).
- `mode: "soft"`: GMM con soglia di probabilità (RAPTOR): un concept può appartenere a più cluster. Il cluster a probabilità massima è il **padre primario** (per l'albero di navigazione e la home); gli altri finiscono in `memberships` del concept e come children *secondari* del cluster (linkati nel body, non in `children`). La gerarchia resta un albero per navigazione, un DAG per contesto.
- Features: embedding (peso 1.0); tag-overlap e adiacenza link-graph opzionali dietro flag (v0.2+).

**Pagina cluster:** sintesi LLM da title+description+tags dei children (mai i body interi; per children cluster anche la loro sintesi). Output: titolo tematico, descrizione, body che spiega il tema e linka tutti i membri. **Home:** prompt dedicato ("spiega il dominio a un nuovo ingegnere, naviga per aree").

### 6.2 Incrementalità

Trigger: `ChangeSet` del compile.
1. **Pre-filtro di materialità (deterministico, zero LLM):** per ogni concept modificato, distanza coseno tra embedding vecchio e nuovo; sotto soglia (default 0.10, configurabile) → il delta non è materiale, si aggiorna solo `updated_at`, nessun judge, nessuna risalita. (Principio materiality-scored da letteratura streaming compilation: non ogni delta merita una chiamata LLM.)
2. Delta materiali e concepts nuovi/rimossi → identifica i cluster L1 affected (membership o centroide più vicino per i nuovi).
3. **LLM-judge di riclustering** per ogni cluster affected: input {sintesi attuale, membri, delta} → structured `fits | regenerate_page | recluster_subtree`:
   - `fits`: aggiorna solo la pagina cluster
   - `regenerate_page`: rigenera sintesi, propaga il judge al parent
   - `recluster_subtree`: re-run clustering sul sottoinsieme del parent, ricostruzione del ramo
4. Propagazione verso l'alto solo su cambio strutturale del livello inferiore. Full re-hierarchy: `klustra hierarchy --full` o soglia di drift accumulato (% concepts cambiati dall'ultimo full run).

### 6.3 Stabilità dei cluster

- Matching tra run: nuovo cluster eredita l'`entity_id` del vecchio se Jaccard membri ≥ 0.6. Altrimenti nuovo id; il vecchio → `status/superseded` + `superseded_by` in frontmatter (redirect: i wikilink entranti restano risolvibili, il lint segnala la migrazione).
- Slug cluster: tematico generato dall'LLM alla prima creazione, poi **immutabile** finché il cluster sopravvive al matching.

---

## 7. Retrieval e context API

### 7.1 API

```python
nx.context(entity_id, depth=1, include=("ancestors",)) -> ConceptContext
nx.navigate(from_entity_id=None) -> home / children       # discesa guidata
nx.search(query, level=None, mode="collapsed") -> ranked   # v. 7.3
```

### 7.2 Parsimonia by-default

`nx.context` default: pagina + **solo la catena ancestors come title+description** (una lookup, zero LLM, poche centinaia di token). Siblings, body dei cluster, records_ref: solo su richiesta esplicita (`include=("ancestors","siblings","records")`, `depth=N`). Motivazione: il costo query della wiki può superare il RAG piatto sui lookup semplici; il contesto ricco va speso solo dove la query lo giustifica.

### 7.3 Strategia anti-bypass (lezione Progressive Disclosure)

Evidenza empirica: agenti con tool di ricerca generici **non caricano l'indice/gerarchia** — inferiscono il path della pagina e la leggono direttamente, azzerando il valore dei livelli di sintesi. Contromisure di design:
1. **Collapsed-tree search** (`mode="collapsed"`, default): concept + cluster + home indicizzati **insieme** nello stesso vector space; il ranking sceglie da solo il livello di astrazione giusto per la query (query sintetiche matchano naturalmente le pagine cluster). La gerarchia dà valore anche all'agente che fa una sola search, senza richiedere traversal esplicito.
2. `mode="tree"`: traversal esplicito top-down con pruning per livello (per agenti orchestrati che navigano).
3. Nelle integrazioni downstream (MCP server, tool per agent): esporre `context/navigate/search` come **unici tool di accesso alla wiki** — non affiancare un file-read generico sul vault, o gli agenti lo useranno bypassando la gerarchia.

Il boost di ranking per pagine cluster/home non è responsabilità di klustra (dipende dallo stack a valle); klustra garantisce `level` e catena ancestors sempre disponibili a costo O(1).

---

## 8. LLM layer

`LLMProvider` ABC + implementazioni: `OpenAICompatible` (OpenRouter/OpenAI/Databricks/gateway, base_url configurabile), `Anthropic`, `Google`. Config per ruolo:

```toml
[llm.extraction]   provider="openrouter" model="deepseek/deepseek-v4-flash" max_tokens=4096
[llm.librarian]    provider="openrouter" model="deepseek/deepseek-v4-pro"
[llm.hierarchy]    provider="anthropic"  model="claude-sonnet-4-6"
[llm.judge]        provider="openrouter" model="deepseek/deepseek-v4-flash"
[llm.embeddings]   provider="openai"     model="text-embedding-3-small"
```

Retry con backoff (default 3), rate limiting, structured output via JSON schema (tool-use dove supportato, altrimenti response_format).

## 9. Token sensitivity

- Budget per chiamata per ruolo; ogni prompt builder dichiara componenti con priorità e strategia di riduzione: indice → filtrato per similarity con l'unit poi troncato; contributi merge → summary-of-summaries oltre budget; children cluster → solo title+description.
- Accounting per chiamata {run_id, role, model, tokens_in/out, cost_estimate} → `klustra stats`.
- Cache extraction+embedding per content-hash; zero chiamate su contenuto invariato.

## 10. Prompt customization

- Default nel package (`klustra/llm/prompts/*.md`, Jinja2).
- Override: `.klustra/prompts/{role}.md` (sostituzione completa) o `.klustra/instructions/{domain}.md` (**iniettato** in tutti i prompt del dominio: contesto aziendale, tassonomia tag, regola entity-vs-record, glossario). User-authored, mai riscritte dal sistema.
- `klustra prompts show ROLE` / `klustra prompts diff` per trasparenza.

## 11. Exporters

`Exporter` ABC + registry: `okf_bundle` (link markdown relativi; passa `klustra validate` + interoperabile con okflint/okf-gem; index/log riservati senza frontmatter; root index con `okf_version: "0.1"`), `obsidian` ([[wikilinks]]), `html` (statico, nav home→cluster→concept), `delta` (v1.0). Export multipli per run.

## 12. CLI e config

`typer`; comandi §4.3 + `init` (scaffold: klustra.toml, instructions template, .klustra/), `validate`, `lint`, `stats`, `prompts`. Config `klustra.toml` a root; secrets SOLO da env (`OPENROUTER_API_KEY` ecc.). `klustra` ≡ `python -m klustra`.

## 13. Tracciabilità

Ogni run: `run_id`, comando, parametri, ChangeSet, accounting LLM, esito quality gates → `.klustra/runs.jsonl` (o tabella run su Delta). Mai loggati contenuti pagine/prompt/output LLM (salvo `--debug`). `log.md` OKF per dominio generato deterministicamente dai run.

## 14. Testing

- Unit: translators (fixture file reali per formato, incluso Excel multi-tabella caotico), resolver wikilink, matching cluster (Jaccard), pre-filtro materialità.
- Integration: mini-corpus per dominio → golden bundle OKF diffato; run incrementali (add/modify/delete) con assert sul ChangeSet e sulla stabilità degli entity_id cluster.
- LLM: mock provider deterministico per CI; smoke test opzionale con provider reale dietro env flag.

## 15. Roadmap

| Fase | Contenuto |
|---|---|
| v0.1 | core + FileStateStore, DomainRegistry (TOML, LocalFolderConnector), Excel/Markdown/Text translators, compile two-phase, validate+lint, exporter obsidian+okf_bundle, CLI (incl. `domain`/`sync`) |
| v0.2 | Hierarchy engine (UMAP+HDBSCAN/GMM, judge, materialità, stabilità), context API + collapsed search, exporter html |
| v0.3 | PdfTranslator (layout-aware), DocxTranslator, lint --semantic, stats completo |
| v1.0 | DeltaStateStore + exporter delta, sync scheduler hooks, MCP server, hardening |
| v1.x | `SharePointConnector`/`BlobConnector` (nuovi `type` in DomainConfig, §4.4), webhook reale (Graph API change notifications / Event Grid), translator URL/scrape, translator agentici |

## 16. Decisioni aperte (bloccanti per v0.1)

1. ~~Nome~~ — deciso: `klustra`
2. Licenza (interna Prysmian vs open source)
3. Embedding di default (`text-embedding-3-small` vs locale) — impatta chi può girare la CLI senza chiave OpenAI
4. Lingua delle pagine generate: forzata per dominio o auto (lingua dominante dei sources)
