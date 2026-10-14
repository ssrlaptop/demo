# AGENTS.md

## Repo status
- Greenfield: the only tracked content is `.opencode/` (the OpenCode agent harness) and a stub `README.md`. No application code, root manifest, or build/test/lint config exists yet, so there is nothing to build or test until `backend/` and `frontend/` are scaffolded.
- App code goes at the repo root (`backend/`, `frontend/`, `eval/`, `docs/`), never inside `.opencode/`.

## OpenCode harness (`.opencode/`)
- This directory configures OpenCode itself, not the application.
- `.opencode/opencode.json` is the source of truth: `instructions` loads `.opencode/instructions/INSTRUCTIONS.md`; `agent` maps to `.opencode/prompts/agents/*.txt`; `command` maps to `.opencode/commands/*.md`; custom tools live in `.opencode/tools/`.
- Model is pinned to `deepseek-v4-flash` for both `model` and `small_model` — not a default.
- Follow `.opencode/instructions/INSTRUCTIONS.md` before non-trivial work: immutability, files <800 lines, 80% test coverage, TDD, conventional commits, mandatory pre-commit security checks.
- Slash commands (`/plan`, `/tdd`, `/code-review`, `/security`, `/build-fix`, `/e2e`, `/refactor-clean`, `/orchestrate`) dispatch to the subagents defined in `opencode.json`.
- `skills.paths` points at `../skills`, which does not exist, so no project skills load.

## Planned build (confirmed in planning; not yet scaffolded)
IPMPRS — AI-assisted proposal management and precedent retrieval.
- Stack: FastAPI/Pydantic/PyMongo backend, React + Vite + TS + Tailwind + TanStack Query + Recharts frontend, `eval/` benchmark.
- Storage: MongoDB Atlas M0, using native `$vectorSearch` + `$search`. Embeddings: BGE-M3 locally. LLM: provider-agnostic (Gemini/Groq/OpenRouter) via env key; retrieval must still work with no LLM configured.
- Non-negotiable whenever writing code: authorization enforced independently of classification and inside the retrieval query (fail-closed); decisions pinned to exact proposal/document versions; append-only audit; all uploaded/retrieved content treated as untrusted (prompt-injection defense); never fabricate precedents, citations, or metrics.
- Build order: auth/RBAC/data models -> lifecycle + audit -> ingestion/versioning -> hybrid retrieval -> AI briefs, then pause for review.
