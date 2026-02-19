# Re:Search — Python Backend

AI researcher agent with a Universal Node/Edge knowledge graph, RAG ingestion pipeline, and autonomous LangGraph agent.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify scaffold
python -c "import backend; print('scaffold ok')"
python cli/main.py --help
```

## Project Structure

```
Search/
├── docs/                    # Design documentation
├── backend/
│   ├── config.py            # Centralised settings (env-driven)
│   ├── db/                  # Phase 1: SQLite + FTS5 + sqlite-vec
│   ├── scraper/             # Phase 2: httpx + trafilatura + playwright
│   ├── rag/                 # Phase 3: chunker + embedder + ingestor
│   ├── agent/               # Phase 4: LangGraph researcher graph
│   └── api/                 # Phase 5: FastAPI HTTP layer
├── cli/
│   └── main.py              # Typer CLI entry-point
├── tests/                   # pytest test suite
├── requirements.txt
└── pyproject.toml
```

## Configuration

Copy `.env.example` (if provided) to `.env` and set:

| Variable | Default | Description |
|---|---|---|
| `RESEARCH_WORKSPACE` | `~/.research_data` | Directory for the SQLite DB |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_CHAT_MODEL` | `llama3.2` | Chat/reasoning model |
| `OPENAI_API_KEY` | _(unset)_ | Required if using OpenAI |
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## Build Phases

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Project scaffold |
| 1 | 🔲 Pending | Database layer |
| 2 | 🔲 Pending | Web scraper |
| 3 | 🔲 Pending | RAG ingestion |
| 4 | 🔲 Pending | LangGraph agent |
| 5 | 🔲 Pending | FastAPI HTTP layer |
