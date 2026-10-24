# Persona RAG: Supabase + Streamlit + Vercel (all free tiers)

```
 you ──► Streamlit admin (admin/)  ──► Supabase  ◄── Vercel function (web/api/chat.js) ◄── visitor's browser
         upload, edit, topics,         Postgres + pgvector            embeds the question, searches,        (web/index.html:
         writing, knowledge index      + file storage                 asks Gemini, returns the answer        the dotted ball)
```

| Part | Where it runs | Folder |
|---|---|---|
| Database, vectors, file storage | Supabase | `supabase/schema.sql` |
| Admin dashboard | Streamlit Community Cloud | `admin/` |
| Public site + chat API | Vercel | `web/` |

## The RAG pipeline
1. **Ingest** – upload files (txt, md, csv, json, html, **pdf, docx**) or write posts. Text is extracted (`admin/lib/extract.py`).
2. **Chunk** – split at headings/paragraphs into ~180-word pieces with overlap; each keeps its heading (`chunker.py`).
3. **Embed** – each chunk becomes a 768-number meaning vector with Google `gemini-embedding-001` (`embed.py`).
4. **Store** – chunks and vectors live in Supabase Postgres (pgvector, HNSW index) plus a keyword index.
5. **Retrieve** – `hybrid_search` (SQL) runs a meaning search and a keyword search and merges them. A relevance gate decides "answer" or "I don't know".
6. **Answer** – the Vercel function sends only the retrieved passages to Gemini with instructions to answer from them and cite them.

Only **published** files and posts are indexed. Drafts never reach the chatbot.

## Setup (about 30 minutes)

### 1. Supabase
1. supabase.com → New project (free).
2. **SQL Editor → New query**, paste all of `supabase/schema.sql`, **Run**. (Safe to run again.)
3. **Project Settings → API Keys**: copy the **Project URL** and the **secret key** (the `service_role` key on older projects). Keep it private. It never goes in the browser.

### 2. Gemini key
aistudio.google.com/apikey → create a key (free tier, no card).

### 3. Put the project on GitHub
Push this whole folder to a new (private) repository.

### 4. Admin on Streamlit Community Cloud
1. share.streamlit.io → New app → pick the repo.
2. **Main file path:** `admin/streamlit_app.py`
3. **Advanced settings → Secrets:** paste the contents of `.streamlit/secrets.toml.example` with your real values.
4. Deploy. Sign in with `ADMIN_PASSWORD`.

Run it locally instead: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, then from the repo root
`pip install -r admin/requirements.txt` and `streamlit run admin/streamlit_app.py`.

### 5. Website on Vercel
1. vercel.com → Add New → Project → import the repo.
2. **Root Directory:** `web`
3. **Environment Variables:** the ones in `web/.env.example`.
4. Deploy.

### 6. First use
1. Admin → **Add files** → upload some research.
2. Admin → **Knowledge index** → **Sync now** until "Waiting for embedding" reaches 0.
3. Use **Test retrieval** with real questions (including ones your research can't answer).
4. Open your Vercel URL and ask the ball.

## Tuning the "I don't know" gate
A chunk is used if its **similarity ≥ MIN_SIMILARITY** (default 0.6) **or** its **keyword score ≥ MIN_KEYWORD_RANK** (default 0.2, roughly "two or more of your question's words appear").
- It answers things it shouldn't → raise MIN_SIMILARITY (try 0.65–0.7) and MIN_KEYWORD_RANK (0.3).
- It says "I don't know" too often → lower MIN_SIMILARITY (try 0.5).
Set the same values in Streamlit secrets (for Test retrieval) and Vercel env vars (for the live site). The Knowledge index page lists recent questions and flags unanswered ones.

## Free-tier facts to plan around
- **Supabase** free: 500 MB database, 1 GB files, **project pauses after 7 days without activity** (your data is kept; un-pause it in the dashboard). Visitors using the site count as activity.
- **Gemini** free: embedding is limited to roughly 30,000 tokens per minute and 1,000 requests per day, so a big first upload indexes slowly. **Sync now** resumes where it stopped. Google may use free-tier prompts to improve its products, so only publish what you are happy to send to Google.
- **Vercel Hobby** is for personal, non-commercial use.
- **Streamlit Community Cloud** apps sleep when idle and wake on the next visit.
- The chat endpoint is public and spends your free Gemini quota. It has a small per-IP limit; for more protection turn on Vercel's firewall rate limiting.

## Good to know
- **Folders:** Streamlit can't upload a folder directly. Zip it, upload the zip, and leave "Unzip" ticked. The folder structure is rebuilt.
- **Model name:** Gemini model ids change. If answers come back as plain quoted passages instead of written sentences, set `GEMINI_MODEL` to a current id from AI Studio. The site keeps working in the meantime.
- **"Invalid API key" in Streamlit:** older `supabase` packages reject the new-style secret keys. Use the legacy `service_role` JWT key from the "Legacy API keys" tab, or upgrade the package.
- **Changing EMBED_MODEL** requires **Rebuild everything**, because vectors from different models can't be mixed.
- **Look of the ball:** colours are four variables at the top of `web/index.html`.
