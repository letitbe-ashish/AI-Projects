# RAG Chatbot with OCR and Memory Isolation

A **fully local, privacy-preserving RAG (Retrieval-Augmented Generation) chatbot** built with LangGraph, ChromaDB, and Ollama. Supports multi-modal document ingestion (PDF with table extraction, plain text, and images via OCR), per-session isolated vector stores, persistent conversation memory, and real-time streaming — all powered by multiple local Ollama models with no cloud APIs.

---

## Features

- **Multi-modal document ingestion** — PDF (with smart table extraction), TXT, and images (OCR)
- **Session-isolated knowledge bases** — each conversation thread gets its own ChromaDB vector collection
- **Persistent conversation memory** — full chat history survives restarts via LangGraph + SQLite
- **Real-time streaming responses** — tokens stream live as the model generates them
- **100% offline** — embeddings, inference, and storage all run locally via Ollama
- **Multi-session UI** — switch between past conversations from the sidebar

---

## Architecture

```
User uploads document
        ↓
rag_tools.py → parse (PDF/TXT/OCR) → chunk → embed (nomic-embed-text) → ChromaDB
        ↓
User types a message
        ↓
main.py (LangGraph chat_node)
  → retrieve top-10 relevant chunks from ChromaDB
  → inject as SystemMessage
  → llama3.2:3b generates response
        ↓
Streamlit streams tokens live → SqliteSaver checkpoints history
```

### File Structure

```
NRAG V3/
├── app.py           # Streamlit UI — chat, file upload, session management
├── main.py          # LangGraph graph + RAG injection + SQLite checkpointer
├── rag_tools.py     # Document loaders (PDF/TXT/image), chunking, ChromaDB
├── requirements.txt # Python dependencies
├── .gitignore
│
├── chatbot.db       # ← auto-created: LangGraph conversation history (SQLite)
├── chroma_db/       # ← auto-created: ChromaDB vector store
└── docs/            # ← auto-created: uploaded files, organised per thread
```

---

## Getting Started

### Prerequisites

1. **Python 3.11+**
2. **[Ollama](https://ollama.com/download)** installed and running

### 1. Clone the repo

```bash
git clone https://github.com/your-username/nrag-v3.git
cd nrag-v3
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Pull the required Ollama models

```bash
# Chat LLM
ollama pull llama3.2:3b

# Embedding model
ollama pull nomic-embed-text

# OCR model (for image uploads)
ollama pull glm-ocr
```

> **Memory note:** All models are capped to a `num_ctx` of 4096 tokens to keep total RAM usage under ~4.5 GB, making this runnable on machines with 8 GB RAM.

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## How to Use

1. **Start a new chat** — click **New Chat** in the sidebar (or one is created automatically)
2. **Upload documents** — use the **Upload Documents** panel in the sidebar
   - Supported: `.pdf`, `.txt`, `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`
   - Documents are indexed into the current thread's private knowledge base
3. **Ask questions** — type in the chat box; the assistant retrieves relevant context from your documents automatically
4. **Switch conversations** — click any thread ID in the sidebar to load a previous session

---

## Tech Stack

| Component | Technology |
|---|---|
| UI | [Streamlit](https://streamlit.io/) |
| LLM | [llama3.2:3b](https://ollama.com/library/llama3.2) via [Ollama](https://ollama.com/) |
| Embeddings | [nomic-embed-text](https://ollama.com/library/nomic-embed-text) via Ollama |
| OCR | [glm-ocr](https://ollama.com/library/glm-ocr) via Ollama |
| Vector Store | [ChromaDB](https://www.trychroma.com/) (persistent, per-thread) |
| Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) StateGraph |
| Memory | SQLite via LangGraph `SqliteSaver` |
| PDF Parsing | [pdfplumber](https://github.com/jsvine/pdfplumber) |

---

## Known Limitations

- **8 GB RAM systems** — keep Ollama idle before uploading images; the OCR model is evicted from RAM after each use (`keep_alive=0`) to free space for the chat LLM
- **No duplicate detection** — re-uploading the same file re-indexes it; delete `chroma_db/` and `docs/<thread_id>/` to reset a thread's knowledge base
- **Thread names are UUIDs** — there is no rename feature yet

---

## Possible Extensions

- [ ] Hybrid search (BM25 + vector) for better retrieval
- [ ] Cross-encoder re-ranking of retrieved chunks
- [ ] Thread naming / renaming in the sidebar
- [ ] Support for `.docx` files
- [ ] Metadata-filtered retrieval (query a specific document only)
- [ ] Swap LLM model from the sidebar at runtime

---

## License

MIT License — see [LICENSE](LICENSE) for details.
