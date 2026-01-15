# FastAPI on Vercel (converted)

This project is ready to deploy to Vercel as a single Python Function.

## Structure

- `api/index.py` — FastAPI app (Vercel looks for an exported `app`)
- `requirements.txt` — Python deps
- `vercel.json` — routes all paths to the FastAPI function

## Run locally

### Option A: Vercel dev (closest to prod)
```bash
npm i -g vercel
vercel dev
```

### Option B: Uvicorn
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
```

Then open:
- http://localhost:8000/api/system
- http://localhost:8000/api/services

## Deploy

1. Push this folder to GitHub
2. Import the repo in Vercel and deploy

