# google-adk-skills-demo

A production-structured multi-agent research pipeline built with **Google ADK**,
where every agent's behaviour is defined by an **[agentskills.io](https://agentskills.io/specification)**-compliant
skill package.

```
user query
   │
   ▼
research_orchestrator            (root agent — sees only the skill catalog)
   └── research_pipeline         (SequentialAgent)
         ├── web_search_agent    ← skills/web-search
         ├── data_analysis_agent ← skills/data-analysis
         └── report_writer_agent ← skills/report-writer
   │
   ▼
Markdown research report
```

## How skills drive the agents

The runtime implements the spec's **progressive disclosure** model:

| Level | What loads | When |
|-------|-----------|------|
| 1 | `name` + `description` (frontmatter) | At startup — the orchestrator's catalog and each agent's `description` |
| 2 | The full SKILL.md body | As each sub-agent's `instruction` |
| 3 | `references/` and `assets/` files | On demand, via the `read_skill_resource` tool |

Tool resolution is convention-based (the spec defines no tool-declaration
field): every name in a skill's `allowed-tools` must be a function defined in
exactly one module under that skill's `scripts/`. The function's docstring is
what the LLM sees, and the registry rejects tools without one.

## Layout

```
skills/                  # pure agentskills.io skill packages
  web-search/
    SKILL.md             # frontmatter (spec fields only) + agent instructions
    scripts/search.py    # provides the search_web tool
    references/          # loaded on demand
    assets/
  data-analysis/
  report-writer/
skill_runtime/           # consumes the packages
  manifest.py            # SKILL.md parsing + full spec validation
  registry.py            # discovery, tool resolution, progressive disclosure
  cli.py                 # `validate` command (mirrors skills-ref validate)
orchestrator/agent.py    # ADK agents wired from the registry
agent.py                 # ADK entry point (adk run / adk web)
main.py                  # standalone CLI runner
tests/                   # 34 offline tests (no network, no API key needed)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env     # add GOOGLE_API_KEY (or Vertex AI project settings)
```

## Run

```bash
# ADK dev UI
adk web

# CLI
python main.py "AI trends in 2025"
python main.py "quantum computing" --focus "hardware,error correction" --results 8
```

## Validate & test

```bash
# Spec-validate every skill package (CI-friendly; non-zero exit on failure)
python -m skill_runtime.cli validate skills/

# Test suite — offline, covers spec validation, tool resolution,
# progressive disclosure, and tool error propagation
pytest
```

## Operational notes

- **Strict startup**: an invalid SKILL.md or unresolvable tool aborts agent
  startup (`load_all(strict=True)`) instead of degrading silently.
- **Error propagation**: tools never raise into the LLM loop — they return
  structured error payloads (`{"error": ...}` / `REPORT ERROR: ...`) that each
  downstream stage recognises and forwards instead of analysing.
- **Sandboxed resources**: `read_skill_resource` only serves files inside the
  requesting skill's own `references/` and `assets/` directories.
- **Config via env**: `ADK_MODEL` (default `gemini-2.0-flash`), `LOG_LEVEL`,
  and credentials in `.env` — see `.env.example`.

## Adding a new skill

1. `mkdir skills/my-skill` — the directory name **must** equal the frontmatter `name`.
2. Write `SKILL.md` with spec-compliant frontmatter and the agent instructions as the body.
3. Put each tool named in `allowed-tools` as a documented function in `skills/my-skill/scripts/`.
4. `python -m skill_runtime.cli validate skills/my-skill`
5. Wire an agent in `orchestrator/agent.py` with `_skill_agent("my_agent", "my-skill")`.
