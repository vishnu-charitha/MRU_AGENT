# MRDU AI Chatbot — Production Deployment Guide

This guide covers end-to-end production deployment for the MRDU AI Chatbot, including frontend hosting, FastAPI backend hosting, a persistent production PostgreSQL database for student registration records, Qdrant Cloud vector search, and OpenRouter LLM integration.

---

## 1. System Architecture Overview

```
                      +-----------------------------+
                      |   Vercel Edge Network       |
                      |   (React / Vite Frontend)   |
                      +--------------+--------------+
                                     |
               HTTPS (CORS)          |  VITE_API_BASE_URL
                                     v
                      +-----------------------------+
                      |   Render Web Service        |
                      |   (FastAPI / Uvicorn)       |
                      +---+-----------+----------+--+
                          |           |          |
            DATABASE_URL  |           |          |  OPENROUTER_API_KEY
                          v           |          v
         +--------------------+       |      +------------------------+
         | Managed PostgreSQL |       |      | OpenRouter API         |
         | (Neon / Render DB) |       |      | (google/gemma-4-31b-it)|
         +--------------------+       |      +------------------------+
                                      v
                          +------------------------+
                          | Qdrant Cloud Cluster   |
                          | (Knowledge Base RAG)   |
                          +------------------------+
```

---

## 2. Infrastructure & Cost Analysis

| Component | Recommended Provider | Tier / Plan | Cost Estimate | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | [Vercel](https://vercel.com) | Hobby ($0/mo) | Free | Global CDN, automatic HTTPS, CI/CD from Git. |
| **Backend** | [Render](https://render.com) | Free Web Service ($0/mo) or Starter ($7/mo) | $0 to $7/mo | Free tier spins down after 15 min idle (30-50s cold start). Starter ($7/mo) is always awake. |
| **Production Database** | [Neon](https://neon.tech) *(Recommended)* or Render Postgres | Serverless Postgres Free Tier ($0/mo) | Free | **Important:** Render free Postgres expires after 30 days! Neon provides a permanent 1 GB free Postgres database. |
| **Vector Database** | [Qdrant Cloud](https://cloud.qdrant.io) | Free Tier (1 GB cluster) | Free | Persistent cloud vector collection (`mrdu_knowledge_base_v3`). |
| **LLM Inference** | [OpenRouter](https://openrouter.ai) | Pay-as-you-go | ~$1 - $5 usage | Token-based pricing for model `google/gemma-4-31b-it`. |

---

## 3. Step 1: Provision Persistent Production Database (Neon PostgreSQL)

> **Why PostgreSQL over local SQLite?**
> Render and Vercel compute containers have **ephemeral filesystems**. Any restart, idle sleep cycle, or redeployment wipes local `.db` files. A managed PostgreSQL database ensures student registration records persist permanently.

1. Go to [Neon.tech](https://neon.tech) and create a free account.
2. Create a new project named `mrdu-chatbot`.
3. In the Neon Console Dashboard, copy your connection string (`Connection string` -> `Pooled connection` or `Direct connection`).
4. The URL format is:
   ```
   postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]?sslmode=require
   ```
   *(Note: The MRDU backend automatically handles both `postgres://` and `postgresql://` URI prefixes).*

---

## 4. Step 2: Deploy Backend to Render

### A. Deploy via Render Blueprint (`render.yaml`)
1. Push your repository to GitHub (ensure `.env` is NOT tracked).
2. Go to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Select your GitHub repository (`vishnu-charitha/MRU_AGENT`).
5. Render reads `render.yaml` and auto-provisions the Web Service.

### B. Manual Configuration (Alternative)
If setting up as a standard Web Service:
- **Environment:** `Python` (or `Docker`)
- **Region:** Closest to your users (e.g., `Singapore` or `Frankfurt`)
- **Branch:** `main`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`

### C. Backend Environment Variables
Configure the following in **Render** -> **Environment**:

| Variable Name | Required? | Example / Value | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | `postgresql://...` | Connection string from Step 1 (Neon/Postgres). |
| `AUTH_TOKEN_SECRET` | **Yes** | *32+ char hex string* | Secure random JWT secret. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `AUTH_TOKEN_EXPIRE_MINUTES` | No | `1440` | Session duration in minutes (1440 = 24 hours). |
| `QDRANT_URL` | **Yes** | `https://xxxx.cloud.qdrant.io:6333` | Your Qdrant Cloud cluster URL. |
| `QDRANT_API_KEY` | **Yes** | `th1s-1s-y0ur-k3y...` | Your Qdrant Cloud API key. |
| `QDRANT_COLLECTION` | No | `mrdu_knowledge_base_v3` | Vector collection name (defaults to code setting). |
| `OPENROUTER_API_KEY` | **Yes** | `sk-or-v1-...` | Your OpenRouter API key. |
| `OPENROUTER_MODEL` | No | `google/gemma-4-31b-it` | Target model identifier. |
| `FRONTEND_URL` | **Yes** | `https://your-app.vercel.app` | Allowed CORS origin (leave blank until frontend is deployed, then update). |

*Note: Database tables are initialized automatically upon application startup by `api.main:init_db()` (`Base.metadata.create_all`). No manual SQL migration is required for the initial setup.*

Copy your backend URL once deployed (e.g., `https://mrdu-chatbot-backend.onrender.com`).

---

## 5. Step 3: Deploy Frontend to Vercel

1. Go to [Vercel Dashboard](https://vercel.com) and click **Add New...** -> **Project**.
2. Import the GitHub repository (`vishnu-charitha/MRU_AGENT`).
3. Configure the project:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click "Edit" and choose `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. In **Environment Variables**, add:
   - `VITE_API_BASE_URL`: Your Render backend URL (e.g., `https://mrdu-chatbot-backend.onrender.com`).
5. Click **Deploy**. Vercel will build the frontend and assign a production URL (e.g., `https://mrdu-chatbot.vercel.app`).

---

## 6. Step 4: Link CORS Configuration

1. Copy your Vercel production URL (e.g., `https://mrdu-chatbot.vercel.app`).
2. Go back to **Render Dashboard** -> Your Web Service -> **Environment**.
3. Set `FRONTEND_URL` to your Vercel URL.
   *(Note: You can supply comma-separated URLs if you have preview deployments, e.g. `https://mrdu-chatbot.vercel.app,https://mrdu-chatbot-preview.vercel.app`).*
4. Render will automatically redeploy the backend with the new CORS configuration.

---

## 7. Step 5: Post-Deployment Verification

Verify all endpoints using PowerShell or terminal:

### 1. Backend Health Check
```bash
curl -i https://YOUR-BACKEND.onrender.com/health
```
**Expected response:** `200 OK` with `{"status":"ok"}`.

### 2. Qdrant & Knowledge Base Health Check
```bash
curl -i https://YOUR-BACKEND.onrender.com/api/health
```
**Expected response:** `200 OK` with `{"status":"ok","qdrant":"connected"}`.

### 3. Student Registration & Token Issuance
```bash
curl -i -X POST https://YOUR-BACKEND.onrender.com/api/students/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test Admission Student",
    "email": "test.admissions@mru.edu.in",
    "mobile_number": "+919876543210",
    "interested_course": "B.Tech",
    "consent": true
  }'
```
**Expected response:** `200 OK` with `success: true`, `student_id`, and `token`.

### 4. Student Session Validation
```bash
curl -i https://YOUR-BACKEND.onrender.com/api/students/session \
  -H "Authorization: Bearer <TOKEN_FROM_STEP_3>"
```
**Expected response:** `200 OK` with `{"valid":true,"student_id":"..."}`.

### 5. Protected Chat Streaming
```bash
curl -N -X POST https://YOUR-BACKEND.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN_FROM_STEP_3>" \
  -d '{
    "question": "What is the fee structure for B.Tech?"
  }'
```
**Expected response:** HTTP `200 OK` streaming NDJSON chunks with verified sources and answers.

### 6. Persistence Verification
Trigger a redeployment or restart of the backend service on Render, then re-run the Step 4 session validation command. With PostgreSQL connected, the session should remain valid without data loss.

---

## 8. Troubleshooting & Common Gotchas

- **Cold Starts:** On Render's free tier, the first request after 15 minutes of inactivity may take 30-50 seconds to wake up the server. If this latency is unacceptable for production, upgrade the Render instance to the **Starter tier ($7/mo)**.
- **CORS Errors:** Verify that `FRONTEND_URL` in Render matches your exact Vercel domain. The backend automatically strips trailing slashes, but make sure the scheme (`https://`) is included.
- **Database Connection Closed:** The backend uses SQLAlchemy `pool_pre_ping=True` to automatically recycle dropped connections from serverless PostgreSQL pools.
