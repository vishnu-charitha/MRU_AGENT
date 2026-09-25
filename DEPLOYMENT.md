# Deployment Guide

## 1. Push repository to GitHub
Initialize your Git repository, commit all tracked files, and push to a remote GitHub repository. Ensure `.env` files are not staged!

## 2. Create Render Web Service
- Go to [Render Dashboard](https://dashboard.render.com).
- Click "New" -> "Web Service".

## 3. Connect GitHub repository
- Connect the GitHub repository containing the MRDU Knowledge Base.

## 4. Configure build/start commands
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

## 5. Add backend environment variables
In the Render Web Service settings, add the following variables:
- `QDRANT_URL`: Your Qdrant URL
- `QDRANT_API_KEY`: Your Qdrant API Key
- `QDRANT_COLLECTION`: `mrdu_knowledge_base`
- `OPENROUTER_API_KEY`: Your OpenRouter API Key
- `OPENROUTER_MODEL`: `google/gemma-4-31b-it`
- `FRONTEND_URL`: Leave empty initially until Vercel is deployed.

## 6. Deploy backend
Click "Deploy". Wait for the build to pass.

## 7. Obtain Render backend URL
Once deployed, copy the Render URL (e.g., `https://mrdu-chatbot-backend.onrender.com`).

## 8. Create Vercel project
- Go to [Vercel Dashboard](https://vercel.com).
- Import the same GitHub repository.
- Set the Root Directory to `frontend`.
- Select Framework Preset: `Vite`.

## 9. Set VITE_API_BASE_URL
In Vercel Environment Variables, add:
- `VITE_API_BASE_URL`: The Render URL obtained in Step 7.

## 10. Deploy frontend
Click "Deploy". Wait for the Vercel build to succeed.

## 11. Copy Vercel URL
Once deployed, copy the Vercel production domain.

## 12. Update Render FRONTEND_URL
Go back to Render Web Service -> Environment.
Update `FRONTEND_URL` with the Vercel URL obtained in Step 11.

## 13. Redeploy backend
Click "Manual Deploy" on Render to apply the CORS update.

## 14. Test end-to-end
Visit your Vercel URL and interact with the MRDU Assistant!
