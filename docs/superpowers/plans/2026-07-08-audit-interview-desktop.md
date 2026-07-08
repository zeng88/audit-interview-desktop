# Audit Interview Desktop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local runnable audit interview checklist desktop application under `/Users/zeng88/Documents/Git/audit-interview-desktop`.

**Architecture:** Python FastAPI owns business logic, SQLite storage, parsing, retrieval, LLM calls, and exports. React + TypeScript provides the audit-workbench UI approved by the user. Tauri v2 wraps the frontend and provides a future desktop entry point; local verification can run backend and frontend independently when Rust is unavailable.

**Tech Stack:** Python 3, FastAPI, SQLite FTS5, optional sqlite-vec with cosine fallback, React, TypeScript, Vite, Tauri v2, openpyxl, python-docx, PyMuPDF.

---

### Task 1: Repository and Runtime Skeleton

**Files:**
- Create: `README.md`
- Create: `backend-python/requirements.txt`
- Create: `backend-python/app.py`
- Create: `backend-python/config.py`
- Create: `backend-python/db.py`
- Create: `backend-python/schemas.py`
- Create: `backend-python/services/log_service.py`
- Create: `scripts/start_backend.sh`

- [ ] Create backend package directories.
- [ ] Define runtime storage paths under `backend-python/storage`.
- [ ] Implement `GET /health`.
- [ ] Implement SQLite initialization with WAL, foreign keys, tables, FTS5 table, and vector fallback table.
- [ ] Add startup script using UTF-8 environment variables.
- [ ] Verify `python3 backend-python/app.py` starts and `/health` returns `ok`.

### Task 2: Project, Model Config, and File APIs

**Files:**
- Create: `backend-python/services/project_service.py`
- Create: `backend-python/services/model_config_service.py`
- Create: `backend-python/services/file_service.py`
- Modify: `backend-python/app.py`
- Modify: `backend-python/schemas.py`

- [ ] Implement project CRUD APIs.
- [ ] Implement model config CRUD, default config handling, and lightweight connection tests.
- [ ] Implement file upload, listing, deletion, and status tracking.
- [ ] Store uploaded files under `backend-python/storage/files/{project_id}`.
- [ ] Write user-facing errors to `task_logs`.
- [ ] Verify APIs with curl or FastAPI TestClient.

### Task 3: Parsing, Chunking, and FTS

**Files:**
- Create: `backend-python/parsers/pdf_parser.py`
- Create: `backend-python/parsers/docx_parser.py`
- Create: `backend-python/parsers/excel_parser.py`
- Create: `backend-python/parsers/text_parser.py`
- Create: `backend-python/parsers/text_cleaner.py`
- Create: `backend-python/services/parse_service.py`
- Create: `backend-python/services/chunk_service.py`
- Create: `backend-python/services/fts_service.py`
- Modify: `backend-python/app.py`

- [ ] Parse PDF pages with PyMuPDF.
- [ ] Parse DOCX paragraphs and tables with python-docx.
- [ ] Parse XLSX sheets and rows with openpyxl.
- [ ] Parse TXT and CSV as UTF-8 first with common fallback encodings.
- [ ] Chunk text with Chinese-friendly character windows and overlap.
- [ ] Insert chunks and rebuild `chunks_fts`.
- [ ] Implement FTS search-test output containing source file, location, snippet, and score.
- [ ] Verify sample TXT flow creates chunks and returns FTS results.

### Task 4: Embedding, Vector Search, and Hybrid Retrieval

**Files:**
- Create: `backend-python/services/embedding_service.py`
- Create: `backend-python/services/vector_service.py`
- Create: `backend-python/services/retrieval_service.py`
- Modify: `backend-python/app.py`
- Modify: `backend-python/db.py`

- [ ] Implement OpenAI-compatible embeddings call.
- [ ] Store vectors in sqlite-vec when available.
- [ ] Store vectors as JSON/BLOB and compute cosine similarity when sqlite-vec is unavailable.
- [ ] Validate embedding dimension from model config.
- [ ] Implement RRF fusion of FTS and vector results.
- [ ] Expose build-vector-index and hybrid search-test APIs.
- [ ] Verify hybrid search works with a fake deterministic embedding mode for local tests when no API key is configured.

### Task 5: LLM Generation, Checklist, Missing Policies, and Exports

**Files:**
- Create: `backend-python/prompts/system_prompt.py`
- Create: `backend-python/prompts/question_generation_prompt.py`
- Create: `backend-python/prompts/evidence_answer_prompt.py`
- Create: `backend-python/prompts/missing_policy_prompt.py`
- Create: `backend-python/services/llm_service.py`
- Create: `backend-python/services/audit_question_service.py`
- Create: `backend-python/services/evidence_service.py`
- Create: `backend-python/services/checklist_service.py`
- Create: `backend-python/services/export_service.py`
- Create: `backend-python/exporters/excel_exporter.py`
- Create: `backend-python/exporters/word_exporter.py`
- Create: `backend-python/exporters/json_exporter.py`
- Modify: `backend-python/app.py`

- [ ] Implement OpenAI-compatible chat completion calls.
- [ ] Strip Markdown code fences and parse JSON strictly.
- [ ] Add deterministic local fallback generation for development without API keys.
- [ ] Generate questions, retrieve evidence, generate answers, and mark missing-policy items.
- [ ] Ensure one failed question writes logs and does not abort the whole batch.
- [ ] Export xlsx, docx, and json files under `storage/exports`.
- [ ] Verify generated checklist can be exported and opened by libraries.

### Task 6: Frontend Workbench

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/backendApi.ts`
- Create: `frontend/src/pages/ProjectList.tsx`
- Create: `frontend/src/pages/ProjectCreate.tsx`
- Create: `frontend/src/pages/FileUpload.tsx`
- Create: `frontend/src/pages/ModelSettings.tsx`
- Create: `frontend/src/pages/IndexBuild.tsx`
- Create: `frontend/src/pages/GenerateChecklist.tsx`
- Create: `frontend/src/pages/ResultViewer.tsx`
- Create: `frontend/src/components/ChecklistTable.tsx`
- Create: `frontend/src/components/EvidenceDrawer.tsx`
- Create: `frontend/src/components/TaskLogPanel.tsx`

- [ ] Implement the approved audit workbench layout.
- [ ] Implement project creation and navigation.
- [ ] Implement file upload and parsing actions.
- [ ] Implement model config forms and tests.
- [ ] Implement index build and search test screen.
- [ ] Implement checklist generation screen.
- [ ] Implement results table, filters, edit support, evidence drawer, and exports.
- [ ] Verify `npm run build` succeeds.

### Task 7: Tauri Shell, Release Workflow, and Docs

**Files:**
- Create: `package.json`
- Create: `src-tauri/Cargo.toml`
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/src/main.rs`
- Create: `src-tauri/src/commands/backend.rs`
- Create: `.github/workflows/release.yml`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/API.md`
- Create: `docs/RELEASE.md`

- [ ] Add root npm scripts for frontend, backend, and Tauri development.
- [ ] Add Tauri command skeleton for backend health and sidecar startup.
- [ ] Add release workflow for Windows, macOS, and Linux.
- [ ] Document setup, model configuration, local run, and release process.
- [ ] Verify local frontend/backend run; record Rust/Tauri limitation if Rust is absent.

### Task 8: End-to-End Verification

**Files:**
- Create: `backend-python/tests/test_core_flow.py`
- Create: `docs/VERIFICATION.md`

- [ ] Add backend tests for DB init, project CRUD, chunking, FTS, deterministic vectors, checklist fallback, and export creation.
- [ ] Run backend tests.
- [ ] Run frontend TypeScript build.
- [ ] Start backend and confirm `/health`.
- [ ] Start frontend dev server and provide local URL.
- [ ] Document exact verification results.

