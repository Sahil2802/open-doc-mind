<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=220&fontSize=50&text=open-doc-mind&color=0:6366f1,100:8b5cf6" alt="Banner"/>
</p>

<div align="center">

# open-doc-mind

A production-ready RAG system for PDF and text documents with AI-powered answers and cited sources.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a97f?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-ffffff)](LICENSE)

[Quick Start](#-quick-start) • [Features](#-features) • [Setup](#-setup) • [API](#-api-reference) • [Contributing](#-contributing)

</div>

---

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Hybrid Retrieval** | Combines vector search (BGE embeddings) with BM25 keyword search using Reciprocal Rank Fusion |
| 📄 **Multi-Format Support** | PDF parsing via PyMuPDF and plain text file ingestion |
| 🎯 **Citation-First** | Grounded responses with source citations; refuses to answer when context doesn't support it |
| 🌊 **Streaming Responses** | Real-time token streaming via Server-Sent Events (SSE) |
| 📊 **Evaluation Ready** | RAGAS metrics integration with golden set evaluation pipeline |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                              Frontend                               │
│                   React + TypeScript + Vite                         │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│    │  ChatWindow │    │ UploadPanel │    │CitationCard │            │
│    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘            │
└───────────┼──────────────────┼──────────────────┼───────────────────┘
            │                  │                  │
            └──────────────────┴──────────────────┘
                                  │
                              SSE + REST
                                  │
┌─────────────────────────────────┴───────────────────────────────────┐
│                               Backend                               │
│                    FastAPI (Python 3.11+)                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │  Ingestion  │    │  Retrieval  │    │ Generation  │              │
│  │  Pipeline   │    │  Pipeline   │    │  Pipeline   │              │
│  └─────┬───────┘    └──────┬──────┘    └──────┬──────┘              │
└────────┼───────────────────┼──────────────────┼─────────────────────┘
         │                   │                  │
         ▼                   ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Pinecone     │  │    Supabase     │  │   Groq API      │
│  (Vectors)      │  │  (PostgreSQL)   │  │    (LLM)        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Supabase](https://supabase.com) account (free tier)
- [Pinecone](https://pinecone.io) account (free tier)
- [Groq](https://groq.com) API key (free tier)

---

## 🛠️ Setup

### 1. Clone & Install Backend

```bash
git clone https://github.com/Sahil2802/open-doc-mind.git
cd open-doc-mind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `backend/.env`:

```bash
# Pinecone
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=rag-docs
PINECONE_ENVIRONMENT=us-east-1-aws

# Groq
GROQ_API_KEY=your_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_key

# LangSmith (optional)
LANGCHAIN_API_KEY=your_key
LANGCHAIN_TRACING_V2=true
```

### 3. Setup Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env`:
```bash
VITE_API_URL=http://localhost:8000
```

---

##  Running the Application

### Backend

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`

---

##  API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload PDF or TXT file |
| `POST` | `/api/query` | Ask a question (SSE streaming) |
| `GET` | `/api/documents` | List uploaded documents |
| `DELETE` | `/api/documents/{id}` | Delete a document |

### Example: Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

Streaming response:
```
data: {"token": "The", "finished": false}
data: {"token": " document", "finished": false}
...
data: {"finished": true}
```

---

## 📁 Project Structure

```
open-doc-mind/
├── backend/
│   ├── api/                    # FastAPI routes & models
│   ├── ingestion/             # Parsing, chunking, embedding
│   ├── retrieval/             # Vector, BM25, fusion, reranking
│   ├── generation/            # LLM, prompts, citations
│   └── config/                # Settings & prompts
├── frontend/
│   └── src/
│       ├── components/        # React components
│       ├── hooks/             # Custom hooks
│       └── api/               # API client
├── eval/                      # RAGAS evaluation
└── .github/workflows/         # CI/CD
```

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|-------|-------------|
| **Frontend** | React, TypeScript, Vite |
| **Backend** | Python, FastAPI, LangChain |
| **Embeddings** | BGE Small (384-dim) |
| **Vector DB** | Pinecone |
| **Keyword Search** | BM25 (rank_bm25) |
| **Re-ranker** | Cross-Encoder ms-marco-MiniLM-L-6-v2 |
| **LLM** | Groq (Llama 3.1 8B) |
| **Storage** | Supabase (PostgreSQL + Storage) |
| **Evaluation** | RAGAS |

</div>

---

## CI Results

Latest evaluation results from GitHub Actions:

| Metric | Score | Threshold |
|--------|-------|-----------|
| Faithfulness | ≥ 0.75 | ≥ 0.75 ✓ |
| Context Precision | ≥ 0.75 | ≥ 0.75 ✓ |
| Answer Relevancy | ≥ 0.75 | ≥ 0.75 ✓ |
| Refusal Accuracy | ≥ 0.85 | ≥ 0.85 ✓ |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with Python, FastAPI, and React**
Made for production-grade RAG applications

</div>