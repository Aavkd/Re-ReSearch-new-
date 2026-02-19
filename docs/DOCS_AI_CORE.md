# AI & Agentic Core Documentation

## 1. Overview
The AI Core of **Re:Search** is designed to function as a proactive "Second Brain," moving beyond simple chatbots to offer persistent, stateful research assistance. It leverages a local-first architecture to ensure privacy and speed, while optionally integrating cloud models for complex reasoning.

## 2. Agentic Architecture (LangGraph)
We utilize **LangGraph** to orchestrate complex, multi-step workflows. Unlike linear chains, LangGraph allows for cyclic graphs, enabling agents to loop, self-correct, and maintain state over long-running tasks.

### The "Researcher Agent" Workflow
The Researcher Agent is the primary autonomous worker in the system.
1.  **Planning Phase:** The agent receives a high-level objective (e.g., "Research solid-state batteries"). It decomposes this into specific search queries and sub-tasks.
2.  **Execution Phase (Loop):**
    *   **Search:** Queries the web using the Scraper tool.
    *   **Evaluation:** Analyzes search results for relevance.
    *   **Scraping:** Fetches full content from promising URLs.
    *   **Synthesis:** Summarizes findings and updates its internal state.
3.  **Completion:** The agent compiles the gathered information into a structured "Artifact" (a new node in the graph) and notifies the user.

### State Management
*   **Short-term Memory:** Managed within the LangGraph state (conversation history, current plan, scratchpad).
*   **Long-term Memory:** Persisted to the SQLite database (see Section 4).

## 3. RAG Pipeline (Retrieval-Augmented Generation)
The RAG pipeline enables the "Chat with Knowledge Base" feature, allowing the AI to ground its answers in the user's saved data.

### 1. Ingestion
*   **Input:** URLs, PDF files, or manual text notes.
*   **Processing:**
    *   **Scraping/Parsing:** Content is extracted using a Rust-based scraper (leveraging `reqwest` and `scraper`) or a PDF parser.
    *   **Cleaning:** Mozilla's `readability.js` (ported to Rust) is used to strip clutter (ads, navbars) and extract the core text.
    *   **Chunking:** Text is split into semantic chunks to optimize retrieval.

### 2. Embedding & Storage
*   **Embedding Model:** A local embedding model runs to convert text chunks into vector representations.
*   **Vector Store:** Vectors are stored directly in **SQLite** using the `sqlite-vec` extension. This eliminates the need for a separate vector database (like Pinecone or Weaviate), keeping the architecture simple and local.

### 3. Retrieval
*   **Semantic Search:** When a user asks a question, the query is embedded and compared against stored vectors using `sqlite-vec` to find the most relevant chunks.
*   **Graph Traversal:** The system can also traverse explicit relationships (edges) in the SQL database to find related context (e.g., "See also" links).

## 4. Web Scraping & Search Tools
The scraping engine is built in **Rust** for performance and safety.

*   **Technology:** `reqwest` for HTTP requests, `scraper` for HTML parsing.
*   **Readability:** Integration of a readability algorithm ensures only high-quality text is fed to the LLM.
*   **Rate Limiting:** Polite scraping policies are enforced to avoid IP bans.
*   **Bridge:** The Rust backend exposes these capabilities to the AI layer via Tauri commands.

## 5. LLM Integration
The system is model-agnostic, supporting a hybrid approach:

*   **Local (Ollama):** The default recommendation. Models like Llama 3 or Mistral run locally for zero-latency, private, and cost-free inference. Perfect for summarization, embedding, and routine tasks.
*   **Cloud (OpenAI/Anthropic):** Optional integration for tasks requiring SOTA reasoning capabilities.
*   **Routing:** The "Brain" component decides which model to use based on task complexity and user preference.

## 6. Database Interaction
The AI interacts with the **SQLite** database through a unified "Node" abstraction.

*   **Universal Nodes:** Every entity (Source, Note, Chat, Concept) is a row in the `nodes` table.
*   **Vector Search:** `sqlite-vec` enables similarity search on the `embedding` column.
*   **Graph Queries:** The `edges` table allows the AI to understand and create structural relationships between content (e.g., linking a "Source" to a "Summary").
