# MRDU AI College Knowledge Assistant

## Overview
A comprehensive RAG-powered College Knowledge Assistant for the Malla Reddy (MR) Deemed to be University Off Campus Tirupati. This intelligent assistant parses official academic documents to provide instant, grounded answers about admissions, fees, departments, and regulations.

## Architecture
- **Frontend**: Vite + React + Vanilla CSS (Glassmorphism)
- **Backend**: FastAPI (Python)
- **Embeddings**: `all-MiniLM-L6-v2`
- **Vector DB**: Qdrant Cloud
- **LLM Engine**: `google/gemma-4-31b-it` (via OpenRouter)

## Features
- **Retrieval Augmented Generation (RAG)**: Answers are generated strictly from the local knowledge base.
- **Scope Guard**: Rejects queries regarding unsupported programs (MBA, BBA, BCA, MCA, Ph.D.).
- **Source Citation**: Automatically provides source documentation links for all grounded answers.
- **Campus Separation**: Differentiates between Tirupati Campus and Main Campus information.

## Knowledge Scope
The chatbot currently covers B.Tech/M.Tech MR20/MR21/MR22/MR24 only where official source documents are available.

**Known Knowledge Gaps:**
The following regulations are currently unavailable in the dataset and will return an "insufficient information" response:
- B.Tech MR21
- M.Tech MR20
- M.Tech MR22

## Local Setup
### 1. Backend
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions, environment variable configurations, and CI/CD steps.
