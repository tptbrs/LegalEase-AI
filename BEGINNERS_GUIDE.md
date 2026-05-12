# LegalEase AI — Beginner's Guide

This guide assumes you've never built an AI project before. It explains every
piece — what it is, why it's there, and how it fits with the rest. By the end
you'll be able to explain this project to anyone, including yourself.

---

## Table of contents

1. [What does this app actually do](#1-what-does-this-app-actually-do)
2. [Words you'll keep hearing — a glossary](#2-glossary)
3. [The mental model: a librarian and a writer](#3-the-mental-model)
4. [Frontend vs backend, and why you need two terminals](#4-frontend-vs-backend)
5. [The seven steps, in plain English](#5-the-seven-steps)
6. [Conversational follow-ups — how the chat memory works](#6-conversational-follow-ups)
7. [Walk-through: what happens when you click "Ask"](#7-walk-through)
8. [A tour of every file in the project](#8-file-tour)
9. [Setting it up from scratch](#9-setup)
10. [Running it every day](#10-daily-run)
11. [Viva prep — questions and good answers](#11-viva-prep)
12. [Things that go wrong, and how to fix them](#12-troubleshooting)
13. [Where to learn more](#13-going-deeper)

---

## 1. What does this app actually do

LegalEase AI is a website. You open it in a browser, and you can do five things:

| Page | What happens |
|---|---|
| **Home** | A landing page that explains what the app does |
| **Legal Q&A** | You type a legal question. The system finds the relevant Indian Act sections and writes a grounded answer that cites them. You can ask follow-up questions in the same conversation |
| **Strategy** | You describe a dispute. The system designs a phased legal action plan with timelines, costs, statutory hooks per phase, critical deadlines, and evidence to preserve. You can ask follow-up questions to refine the plan |
| **FIR Generator** | You describe a crime. The system writes a formal First Information Report (FIR) draft mapped to BNS/IPC sections, and gives you a downloadable PDF |
| **Document Analyzer** | You upload a contract, legal notice, scanned PDF, or photo of a document. The system OCRs it if needed, extracts every key clause, flags every risky clause with severity, recommends action, and lets you ask follow-up questions about the same document |

Underneath every answer there's also a **Pipeline Trace** panel. Click it and
you see how the system actually did its work — what it searched for, what it
found, what it sent to the AI model. This is the most important feature for
your viva.

### Three things to highlight in the demo

1. **Citations are always real.** Every legal claim points to a real PDF
   section. The system can't make up sections.
2. **Conversations remember context.** Ask "what about section 24?" after
   your first question and the assistant uses the earlier context to answer.
3. **Pipeline is fully transparent.** Expand the trace under any answer and
   you'll see the domain classification, retrieved chunks, reranked chunks,
   model used, and per-stage latencies.

---

## 2. Glossary

Keep this section open while you read the rest. It will help.

### Concepts

**AI (Artificial Intelligence).** A computer program that can produce outputs
which look "smart" — like writing essays, classifying images, or translating
text. In this project, AI specifically means an **LLM**.

**LLM (Large Language Model).** A specific kind of AI that has been trained on
a huge amount of text. You give it a prompt (some text), and it predicts what
text comes next. ChatGPT, Gemini, and Claude are all LLMs. This project uses
**Google's Gemini**.

**Hallucination.** When an LLM confidently makes up something that isn't true.
RAG (next entry) is one way to reduce hallucination.

**RAG (Retrieval-Augmented Generation).** The technique this project uses.
Instead of asking the LLM directly, we first **retrieve** relevant documents
from our own database, then **generate** an answer using only those documents
as context. The LLM is forced to ground its answer in real text we showed it.

**Embedding.** A way of turning a piece of text into a list of about 384
numbers. Texts with similar *meanings* get similar number lists. Think of it
like turning each sentence into GPS coordinates: similar sentences end up at
nearby locations.

**Vector.** Just a fancy word for "list of numbers". Embeddings are vectors.

**Vector store.** A place to keep all your embeddings, with fast search. We
use a simple **NumPy file** (`embeddings.npy`) plus a metadata sidecar
(`records.json`) as our vector store.

**Cosine similarity.** The math we use to measure how close two vectors are.
For our normalised vectors it ends up between 0 and 1; higher means more
similar.

**Chunk.** When we ingest a 500-page PDF, we don't store it as one giant
block — we split it into smaller pieces (one section each typically). Each
piece is a chunk. We embed each chunk separately.

**Cross-encoder.** A second AI model that looks at *(question, chunk)*
together and gives a more accurate relevance score than the embedding model
can. Slower per pair, much more accurate.

**Prompt.** The text you send to an LLM. In this project, prompts are
carefully constructed: a system instruction, the retrieved chunks, the
conversation history (if any), the user's question, and a strict JSON output
schema.

**JSON.** A standard text format for structured data:
`{"answer": "...", "citations": [...]}`. We force the LLM to respond in JSON
so we can render it as nice cards on the website.

**Cite tags.** In our prompts we number retrieved chunks `[#1]`, `[#2]`, etc.
We tell the LLM: "every legal claim must be tagged with the `[#n]` of the
chunk it came from." Later we resolve those numbers back to the actual chunks
when rendering citations.

**Conversation history.** The list of prior user/assistant messages in the
current chat. The backend uses this so the LLM can answer follow-up questions
in context (e.g. "tell me more about that section").

**Document context.** When you upload a document for analysis and then ask
follow-up questions about it, the document text is sent along with each
follow-up so the LLM can answer using both the document *and* retrieved
Indian law.

### Web stack words

**API (Application Programming Interface).** A way for one program to talk to
another. In this project, the website (frontend) talks to a Python program
(backend) over an API. Think of it like a restaurant menu: the frontend
orders specific things, the backend cooks them.

**Endpoint.** One specific item on the API menu. We have endpoints like
`/api/qa` (ask a question) and `/api/fir` (generate an FIR).

**HTTP.** The protocol your browser uses to talk to websites. Endpoints are
called via HTTP requests (mostly POST and GET).

**Localhost.** Your own computer. When you see `http://localhost:5173`, that
means "the website is running on port 5173 of this very machine".

**Port.** Like a door number on your computer. Different programs use
different ports so they don't clash. The backend uses port **8000**, the
frontend uses **5173**.

**Frontend.** The part of the app the user sees and interacts with — the
website itself. Written in JavaScript using React.

**Backend.** The part the user doesn't see — does the actual work:
classifying, retrieving, ranking, calling Gemini. Written in Python using
FastAPI.

**FastAPI.** A Python library for writing backends. It handles HTTP requests,
validates inputs, and returns JSON responses.

**React.** A JavaScript library for building interactive web pages.

**Vite.** The tool that runs the React development server. When you type
`npm run dev`, Vite starts a server that serves your React app.

**Tailwind CSS.** A way of writing styles using short utility class names in
your HTML/JSX instead of writing custom CSS files.

**Framer Motion.** A library that adds smooth animations to React components
— page transitions, fade-ins, the chat bubble appearance, etc.

**npm and pip.** Package installers. `pip install` for Python, `npm install`
for JavaScript. They download the libraries your project depends on.

**Virtual environment (venv).** An isolated Python environment per project.
It keeps each project's dependencies separate so they don't conflict. The
`.venv` folder in `backend/` is your virtual environment for this project.

### Project-specific words

**Pipeline.** The sequence of seven steps that runs every time a user asks
something. The heart of the project. Each step is in its own file in
`backend/pipeline/`.

**Pipeline trace.** A summary of what happened in each pipeline stage,
returned alongside the answer. The frontend shows this in an expandable
panel. It's how you prove to an examiner that the system is doing real work,
not just calling Gemini.

**BNS, BNSS, BSA.** The three new (2023) Indian criminal codes —
Bharatiya Nyaya Sanhita (replaces IPC), Bharatiya Nagarik Suraksha Sanhita
(replaces CrPC), Bharatiya Sakshya Adhiniyam (replaces Evidence Act).

**Model fallback chain.** `GEMINI_MODEL` in `.env` accepts a comma-separated
list of model names. When the first model's daily free-tier quota runs out,
the wrapper falls through to the next one automatically.

---

## 3. The mental model

The clearest way to understand what this app does is to imagine **two people
working together**:

- **A librarian** who knows where every section of every Indian Act is in a
  giant library. Given any question, she can quickly pull out the most
  relevant 5 pages. She doesn't write — she only finds.

- **A writer** who is brilliant at phrasing things, but doesn't know any law.
  Given some pages and a question, he can summarise them into a clear answer.
  But without pages, he'll make stuff up.

A normal chatbot is just the writer alone — fast, but unreliable.

LegalEase AI is the librarian + the writer working together. You ask the
question, the librarian finds the right pages, the writer turns them into a
clear answer, and we show you both the answer and the pages he used.

The librarian is **all the local code** — the classifier, retriever,
reranker. The writer is **Gemini** — the LLM we call at the end. The pages
are the **Indian Act PDFs** we ingested into the vector store.

When you ask a follow-up question, the writer is also given a transcript of
the prior conversation, so he can answer "explain that more simply" with full
context.

That's literally the whole project.

---

## 4. Frontend vs backend

Think of a restaurant:

- The **frontend** is the dining area, the menu, and the waiter. The customer
  sits down, looks at the menu, places an order, and eventually gets food on
  a plate. Pretty.
- The **backend** is the kitchen. Hidden, noisy, lots of work happening, but
  the customer never sees it. They just place an order and get food.

Web apps work the same way. Your browser is the dining area. The Python
server is the kitchen.

For development, both have to be running:

- **Backend** runs on `http://localhost:8000`. It's the "kitchen".
- **Frontend** runs on `http://localhost:5173`. It's what you actually open
  in your browser.

That's why you need **two terminals** to run this project — one for each.

When you click **Ask**, here's what happens:

1. The browser (frontend) sends a request to `http://localhost:5173/api/qa`.
2. Vite (which runs the frontend) sees `/api/...` and *forwards* the request
   to `http://localhost:8000/api/qa` — that's the backend.
3. The backend runs the pipeline and returns JSON.
4. Vite hands the JSON back to the browser.
5. React renders the answer on the page.

The "forwarding" is called a **proxy**, set up in `frontend/vite.config.js`.
This is why you don't see CORS errors during development: from the browser's
point of view, everything comes from `localhost:5173`.

---

## 5. The seven steps

Every time you ask a question, the backend runs through seven steps in order.
They live in `backend/pipeline/` — one Python file each.

```
USER QUESTION  (+ conversation history if any, + document context if any)
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1.  classifier.py     — What kind of law is this?      │
│ Step 2.  retriever.py      — Find the closest 20 chunks     │
│ Step 3.  reranker.py       — Pick the best 5 of those 20    │
│ Step 4.  prompt_builder.py — Write the prompt: system + ctx │
│                              + history + question + schema  │
│ Step 5.  llm_caller.py     — Send to Gemini, fall back on   │
│                              quota errors to the next model │
│ Step 6.  postprocessor.py  — Parse JSON, attach citations   │
│ Step 7.  main.py           — Bundle answer + trace, return  │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
ANSWER + CITATIONS + PIPELINE TRACE → frontend
```

### Step 1 — Classify the domain

> File: `backend/pipeline/classifier.py`

We have 8 possible legal domains: `criminal`, `consumer`, `labour`, `family`,
`cyber`, `property`, `constitutional`, `tax`, plus a `general` fallback.

The classifier scans the question for keywords. Each domain has a weighted
keyword list:

```python
"criminal": [
    ("fir", 3.0),
    ("ipc", 3.0),
    ("bns", 3.0),
    ("arrest", 2.0),
    ("police", 1.5),
    ...
]
```

For a question containing "police" and "arrest", the criminal score is
`1.5 + 2.0 = 3.5`. Whichever domain has the highest score wins.

**Why so simple?**
1. It runs in under 1 millisecond — no AI model needs to be loaded.
2. It's transparent. The pipeline trace shows exactly which keywords matched.
3. For 8 broad domains, this is good enough. We don't need a fancy ML
   classifier when a lexicon gives the right answer.

### Step 2 — Retrieve relevant chunks

> File: `backend/pipeline/retriever.py`

This is where the AI part begins. We have ~thousands of chunks (one per
section of each Act PDF) saved as a NumPy matrix of embeddings.

What happens:

1. Convert the user's question into an embedding using
   `sentence-transformers/all-MiniLM-L6-v2`.
2. Compare the question embedding to every stored chunk embedding using a
   single matrix multiplication (cosine similarity, since both are
   normalised).
3. Optionally filter by domain: if the classifier said "criminal", consider
   only chunks tagged `criminal` or `constitutional`.
4. Return the top 12 most similar chunks (tuned down from 20 — same precision
   in practice, faster reranking).

**Performance note:** the `add()` method that populates this store during
ingestion batches new rows so that we only call `np.vstack` once per batch
instead of once per chunk. For 1500 chunks at batch size 64, that's ~24
array copies instead of 1500 — visibly faster ingestion.

### Step 3 — Rerank the candidates

> File: `backend/pipeline/reranker.py`

A **cross-encoder** model takes 20 `(question, chunk)` pairs and gives each a
more accurate relevance score than the embedding model. We keep the top 4.

**Why two steps?** The embedding model is fast but fuzzy; the cross-encoder
is accurate but slow. Using both gives us speed AND precision.

### Step 4 — Build the prompt

> File: `backend/pipeline/prompt_builder.py`

A "prompt" is just the text you send to the LLM. Ours has up to five parts:

1. **System instruction**: "You are LegalEase AI. Answer ONLY using the
   sections in CONTEXT. Cite each legal claim with [#n]. Output valid JSON
   matching this schema. RESPONSE LANGUAGE: [English | Hindi]."
2. **Document context (optional)**: if the user uploaded a document and is
   asking follow-ups about it, the document text is injected here.
3. **Prior conversation (optional)**: if there are earlier turns in this
   chat, they're inserted as `User: ... / Assistant: ...` so the LLM has
   memory.
4. **Context block**: the 5 reranked chunks, numbered `[#1]`, `[#2]`, etc.
5. **User block**: the actual question, followed by a reminder of the
   response language rule.

We have **four prompt modes**, one per feature:
- `qa` — for the **first** Legal Q&A question (full structured response)
- `chat` — for follow-up turns in Q&A, Strategy, and Document Analyzer
  (concise conversational answers with inline citation chips)
- `strategy` — for the **first** Strategy turn (phased action plan)
- `fir` — for the FIR generator
- `document_analysis` — for the *initial* document upload (asks for an
  exhaustive list of every key clause and every risk)

**Hindi enforcement.** The language instruction is repeated twice — once in
the system prompt and once at the end of the user prompt — because Gemini's
JSON mode sometimes drops parts of the system prompt. The instruction
explicitly lists every field that must be in the chosen language, while
stating that statute names and section numbers stay in English so they
remain searchable.

### Step 5 — Call the LLM

> File: `backend/pipeline/llm_caller.py`

This file is the *only* place we talk to Gemini. It uses Google's official
`google-genai` library.

A clever bit: the `GEMINI_MODEL` setting in `.env` is a **comma-separated
priority list of models**:

```
GEMINI_MODEL=gemini-3.1-flash-lite,gemini-2.5-flash-lite,gemini-2.0-flash-lite
```

If the first model returns a 429 (daily quota exhausted), the wrapper
automatically falls through to the next model. The model that actually
answered is recorded in the pipeline trace, so the frontend shows the truth.

### Step 6 — Postprocess the response

> File: `backend/pipeline/postprocessor.py`

LLMs aren't perfect. The postprocessor:
1. Strips any markdown fences (`` ```json ... ``` ``) the model accidentally
   wrapped its JSON in.
2. Tries `json.loads()`.
3. If that fails, does a "balanced brace recovery" — finds the first balanced
   `{...}` block and parses only that.
4. Walks the parsed JSON, collects every `cite: <int>` value.
5. For each cite, looks up the corresponding chunk and builds a citation
   object with `act_name`, `section`, and the actual quoted text.

The frontend never sees the raw LLM output. It only sees the parsed JSON
plus resolved citations.

### Step 7 — Bundle and return

> File: `backend/main.py`

The `_run_pipeline()` function measures each stage's latency, packages
everything into a `StructuredEnvelope` (`{ ok, mode, data, citations,
pipeline_trace }`), and returns it as JSON to the frontend.

For the document analyzer, the envelope additionally contains
`data._document_text` — the extracted document content. The frontend keeps
this around so follow-up questions can be answered with the document still
in context.

---

## 6. Conversational follow-ups

The QA endpoint accepts an optional **`history`** field — a list of
`{role, content}` dicts representing prior turns of the same conversation.
The Chat, Strategy, and Document Analyzer pages all use this to give you
real chat-style conversations.

### How history flows

1. **First user question** — frontend sends `{ query, language, history: [] }`.
2. Backend runs the pipeline. Returns answer.
3. **Frontend stores both the user message and the assistant's answer text**
   in a local `messages` array.
4. **User types a follow-up** — frontend builds a history of every prior turn
   and sends `{ query: "next question", language, history: [...] }`.
5. Backend's prompt builder injects a `PREVIOUS CONVERSATION:` block before
   the new question, so the LLM has memory.
6. The LLM answers the follow-up in context.

### Limits

- Up to the last **8 turns** are kept in the prompt (to bound token cost).
- Each turn is truncated to **1500 characters**.

### Document Analyzer follow-ups

When you analyse a document, the backend returns the extracted document text
in `data._document_text`. The frontend stores this. When you ask a follow-up,
the frontend sends `document_context: <the_doc_text>` along with the
question and history. The prompt builder includes a `DOCUMENT BEING
DISCUSSED:` block in the prompt, so the LLM can answer using both the
document AND retrieved Indian law sections.

This means you can:
- Upload a contract.
- See the structured analysis.
- Ask "explain clause 5 more simply" — the model uses the actual clause text.
- Ask "what's the worst case if I sign this?" — answered with both the
  document and retrieved legal references.

### Why this is the right design

- No server-side session state. The conversation lives in the browser
  (React state). If you refresh, the conversation is gone, but the system
  is stateless and scales easily.
- The history goes through the prompt itself, so the LLM has full context
  including the *answer text* it gave previously — not just the user's
  questions.
- For deeper feature work, you could persist history server-side later
  (SQLite + session ID). Currently kept client-side for simplicity.

---

## 7. Walk-through

Let's follow one specific request from start to finish.

You type *"What are my rights if my employer doesn't pay overtime?"* and
click **Ask**.

### In your browser (`Chat.jsx`)

The page maintains a `messages` state array (empty at the start). When you
submit:

```js
const handleSubmit = async (text) => {
  setMessages([...messages, { role: 'user', content: text }])
  setLoading(true)
  const history = messages.map(m => ({ role: m.role, content: m.content }))
  const data = await postQA({ query: text, language: lang, history })
  setMessages(prev => [...prev, { role: 'assistant', content: data.data.answer, response: data }])
}
```

For the first message, `history` is an empty array.

### `postQA()` in `utils/api.js`

Sends:

```
POST /api/qa
Content-Type: application/json

{
  "query": "What are my rights if my employer doesn't pay overtime?",
  "language": "en",
  "history": []
}
```

### In the backend (`main.py`)

```python
@app.post("/api/qa")
async def qa(req: QARequest):
    return await _run_pipeline(
        query=req.query,
        mode=PromptMode.QA,
        language=req.language,
        history=[t.model_dump() for t in req.history],
        ...
    )
```

### Stages 1–6

Run as described in [§5](#5-the-seven-steps). Briefly:

- **Classify**: keywords `employer`, `overtime` match the **labour** domain.
- **Retrieve**: top 12 chunks from `Code_on_Wages_2019` + `Industrial_Disputes_Act_1947`.
- **Rerank**: top 4 picked by cross-encoder.
- **Prompt**: built with system + context + user question. History is empty
  so no `PREVIOUS CONVERSATION` block.
- **LLM call**: Gemini returns JSON with `answer`, `key_provisions`,
  `recommended_actions`, `warnings`.
- **Postprocess**: citations resolved.

### Stage 7 — return

```json
{
  "ok": true,
  "mode": "qa",
  "data": {
    "answer": "Under the Code on Wages, 2019, your employer is legally required...",
    "key_provisions": [...],
    "recommended_actions": [...],
    "warnings": [...]
  },
  "citations": [...],
  "pipeline_trace": {
    "classification": {...},
    "retrieved_chunks": [...],
    "reranked_chunks": [...],
    "model": "gemini-3.1-flash-lite",
    "latency_ms": {...}
  }
}
```

### Frontend renders

`Chat.jsx` adds the assistant message. `ChatThread.jsx` renders:
- Your question as a gold-bordered bubble (right-aligned).
- The assistant's answer text as a dark bubble (left-aligned).
- Below the latest assistant bubble: key provisions card, recommended actions
  card, citation cards, the pipeline trace panel.

### Follow-up

You type *"What if I'm a contract worker, not a regular employee?"*

The frontend now sends:

```json
{
  "query": "What if I'm a contract worker, not a regular employee?",
  "language": "en",
  "history": [
    { "role": "user", "content": "What are my rights if my employer doesn't pay overtime?" },
    { "role": "assistant", "content": "Under the Code on Wages, 2019..." }
  ]
}
```

The prompt now includes a `PREVIOUS CONVERSATION` block. The LLM knows you
were just discussing overtime under the Code on Wages, and answers the new
question with that context.

---

## 8. File tour

### Project root

```
Legal/
├── BEGINNERS_GUIDE.md     ← you're reading this
├── .gitignore             ← tells Git which files to ignore (.env, .venv, etc.)
├── backend/               ← all Python server code
└── frontend/              ← all React UI code
```

### `backend/`

```
backend/
├── requirements.txt        — Python libraries the project needs
├── requirements-dev.txt    — extra libraries only for development (pytest, ruff)
├── .env                    — your Gemini API key + model fallback chain (gitignored;
│                             edit this once after first clone)
│
├── config.py               — single Settings class. All configuration lives here.
│                             Every other file reads from get_settings()
├── main.py                 — the FastAPI app. Defines /api/qa, /api/strategy,
│                             /api/fir, /api/analyze-document, /api/health.
│                             /api/qa auto-switches to CHAT mode on follow-ups
├── ingest.py               — CLI you run once to ingest the PDFs
│
├── pipeline/               — the seven RAG stages, one file each
│   ├── ingestion.py        — parse PDFs into section-aware chunks
│   ├── classifier.py       — domain classifier (rule-based)
│   ├── retriever.py        — NumPy vector store + embedding model (batched insert)
│   ├── reranker.py         — cross-encoder reranker
│   ├── prompt_builder.py   — mode-specific prompts, history support, language enforcement
│   ├── llm_caller.py       — Gemini wrapper with model fallback on 429
│   └── postprocessor.py    — parse JSON, attach citations
│
├── services/               — side helpers (not part of RAG pipeline)
│   ├── document_extractor.py  — extract text from uploaded files (PDFs + OCR for scanned PDFs / images)
│   └── fir_pdf.py             — render an FIR JSON into a downloadable PDF
│
├── scripts/                — operational/setup scripts
│   ├── fetch_acts.py       — downloads PDFs from URLs in the manifest
│   └── acts_manifest.json  — list of {act, year, domain, URL} to download
│
├── data/acts/              — 10 Indian Act PDFs (~24 MB)
│   ├── Bharatiya_Nyaya_Sanhita__2023__criminal.pdf
│   ├── Constitution_of_India__1950__constitutional.pdf
│   └── ... 8 more
│
└── chroma_db/              — created by `python ingest.py`
    ├── embeddings.npy      — float32 matrix of all chunk vectors
    └── records.json        — chunk_id → text → metadata for each row
```

> Note: the folder is named `chroma_db/` for historical reasons. The project
> previously used ChromaDB, but we switched to a NumPy-based store because
> ChromaDB's `chroma-hnswlib` dependency requires Visual C++ build tools on
> Windows. The folder name was kept to avoid touching config in 5 places.

### `frontend/`

```
frontend/
├── package.json            — list of Node libraries
├── vite.config.js          — Vite config + the /api proxy to backend
├── tailwind.config.js      — theme colours (dark + gold)
├── postcss.config.js       — boilerplate for Tailwind
├── index.html              — the single HTML file (it's a single-page app)
│
└── src/
    ├── main.jsx            — entry point: mounts <App /> into the DOM
    ├── App.jsx             — sets up the six routes
    ├── index.css           — Tailwind directives + custom utility classes
    │
    ├── i18n/               — internationalisation (English + Hindi)
    │   ├── index.jsx       — LanguageProvider + useI18n() hook
    │   ├── en.json         — every English UI string
    │   └── hi.json         — every Hindi UI string
    │
    ├── utils/
    │   └── api.js          — the only place we make HTTP calls (uses axios).
    │                         postQA accepts `history` and `documentContext`
    │
    ├── components/         — reusable bits used by multiple pages
    │   ├── Layout.jsx          — wraps every page with Navbar + animations
    │   ├── Navbar.jsx          — top bar with nav links + EN/हिन्दी toggle
    │   ├── LoadingDots.jsx     — three-dot spinner with stage labels
    │   ├── CitationCard.jsx    — one citation tile
    │   ├── ChatThread.jsx      — shared chat UI: bubbles, sticky input,
    │   │                          thinking indicator, latest-message details
    │   └── PipelineTrace.jsx   — the expandable trace panel (collapsed by default; click to open)
    │
    └── pages/              — one component per route
        ├── Landing.jsx          — /
        ├── Chat.jsx             — /chat (uses ChatThread)
        ├── Strategy.jsx         — /strategy (uses ChatThread; first turn renders phased plan)
        ├── DocumentUpload.jsx   — /analyze (initial analysis + ChatThread for follow-ups)
        └── FIRGenerator.jsx     — /fir (one-shot form + PDF download)
```

---

## 9. Setup

You only do this once per computer.

### Prerequisites — install these first

| Tool | Where to get it |
|---|---|
| **Python 3.12** | https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe |
| **Node.js 18+** | https://nodejs.org/ (LTS version) |
| **A Gemini API key** | https://aistudio.google.com/app/apikey (free, instant) |

> **Important:** use Python 3.12, not 3.13. Some scientific libraries don't
> yet have Windows wheels for 3.13 and require Visual C++ build tools to
> compile from source.

When installing Python, tick **"Add python.exe to PATH"** and **"py
launcher"**. Open a fresh PowerShell window after install and verify:
`py -3.12 --version` should print `Python 3.12.x`.

### Backend setup

```powershell
cd "D:\Legal Claude\Legal\backend"

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked, run once:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

The PyTorch line is important — `--index-url https://download.pytorch.org/whl/cpu`
fetches a CPU-only build instead of the 2 GB CUDA wheel.

### Configure your Gemini key

The project ships with a ready-to-edit `backend/.env` file that already has
the model fallback chain set. You only need to paste in your Gemini API key:

```powershell
notepad .env
```

Make the `GEMINI_API_KEY` line look like this (use your real key):

```
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_MODEL=gemini-3.1-flash-lite,gemini-2.5-flash-lite,gemini-2.0-flash-lite
```

The `GEMINI_MODEL` line is already filled in — leave it as is unless you
want to swap models manually.

The second line is the **model fallback chain** — if the first model hits
its daily quota, the system automatically tries the next.

Verify Python sees the key:

```powershell
python -c "from config import get_settings; s = get_settings(); print('key set:', bool(s.gemini_api_key))"
```

Should print `key set: True`.

### Ingest the PDFs

```powershell
python ingest.py
```

First run downloads `sentence-transformers/all-MiniLM-L6-v2` (~80 MB) to your
HuggingFace cache, then chunks every PDF, embeds every chunk, and saves to
`chroma_db/`. Takes ~3–5 minutes on CPU.

Thanks to the batched-vstack optimisation in `retriever.add()`, this is
significantly faster than a row-by-row insert for the same number of chunks.

Verify:

```powershell
python ingest.py --stats
```

### Frontend setup

In a **new** terminal:

```powershell
cd "D:\Legal Claude\Legal\frontend"
npm install
```

---

## 10. Daily run

Two terminals.

**Terminal 1 — backend** (with `(.venv)` prefix):

```powershell
cd "D:\Legal Claude\Legal\backend"
.\.venv\Scripts\Activate.ps1
python main.py
```

Wait for `Uvicorn running on http://0.0.0.0:8000`.

**Terminal 2 — frontend**:

```powershell
cd "D:\Legal Claude\Legal\frontend"
npm run dev
```

Open `http://localhost:5173`.

To stop, **Ctrl+C** in each.

---

## 11. Viva prep

### Q: Tell me what your project does in one minute.

**A:** "LegalEase AI is a Retrieval-Augmented Generation system for Indian
law. The user asks a legal question; the system classifies the domain,
retrieves the most relevant sections from a vector database of real Indian
Act PDFs, reranks them with a cross-encoder, builds a prompt with conversation
history and strict JSON output schema, calls the Gemini API, and parses the
response — attaching citations back to the original sections. The user can
ask follow-up questions in the same conversation. Every answer is anchored
to text from real PDFs, so the system can't hallucinate sections."

### Q: How is this different from just asking ChatGPT?

**A:** "ChatGPT alone is one model with no factual grounding — it can invent
sections. My system uses LLM-style models only at the final synthesis step.
Before that, I do classification and retrieval locally so the model is
constrained to only use real text from real Indian Acts. The pipeline trace
at the bottom of every answer shows exactly which sections were retrieved
and which model answered."

### Q: Show me that this isn't just a wrapper.

**A:** Open the Pipeline Trace under any answer. Point out:
- The classification confidence and matched keywords.
- The 20 retrieved chunks with similarity scores.
- The 5 reranked chunks with cross-encoder scores.
- The actual model that answered.
- The per-stage latency.

Then: "Notice that classification, retrieval, and reranking all run locally
in milliseconds. Only one stage out of seven is the LLM call. The entire
vector store is a NumPy file — there's no external service apart from
Gemini at the very end."

### Q: How does the follow-up chat work?

**A:** "Conversation history lives in the browser as a React state array.
When the user asks a follow-up, the frontend sends the entire prior
conversation along with the new question. The prompt builder injects a
`PREVIOUS CONVERSATION` block before the new question, so the LLM sees the
full context. I cap it at 8 most recent turns and 1500 chars per turn to
keep prompt size bounded. For the Document Analyzer, I additionally preserve
the document text in `document_context` so follow-up questions are answered
using both the document AND retrieved Indian law sections."

### Q: Why two retrieval stages?

**A:** "Standard production RAG pattern. The bi-encoder
(sentence-transformers) is fast — milliseconds for thousands of chunks — but
less precise. The cross-encoder is more accurate per pair but expensive.
So I use the bi-encoder to fast-filter from thousands of chunks down to 20
candidates, then the cross-encoder to accurately pick the top 4 from those
12. The added latency is around 150 milliseconds, worth it for precision."

### Q: How do you handle the LLM hallucinating?

**A:** "Three layers:
1. The prompt explicitly says: answer only from the supplied context, cite
   with `[#n]` tags.
2. The output is forced to JSON mode using Gemini's `response_mime_type`
   parameter.
3. The postprocessor refuses to render any `[#n]` citation that doesn't map
   to an actual retrieved chunk."

### Q: Why a NumPy vector store and not ChromaDB or FAISS?

**A:** "I started with ChromaDB but `chroma-hnswlib` requires Visual C++
build tools on Windows for Python 3.12 — that's a 6 GB install just for one
library. So I rewrote the store as a NumPy file. At my corpus size, the
cosine similarity is a single matrix multiply that runs in single-digit
milliseconds. There's no performance loss, the install is 100 MB lighter,
and it works on any machine with NumPy. The retriever's `add()` method
batches new rows for one `vstack` per batch instead of one per chunk — O(n)
copies instead of O(n²) on ingest."

### Q: Why is the classifier rule-based?

**A:** "Three reasons. First, it runs in under a millisecond — no model
loaded. Second, it's fully explainable: the trace shows exactly which
keywords matched. Third, for 8 broad domains in well-defined legal
vocabulary, a hand-curated lexicon beats a trained classifier on cost,
latency, and maintainability."

### Q: What happens if your Gemini quota runs out?

**A:** "Model fallback chain in `.env`:
`GEMINI_MODEL=gemini-3.1-flash-lite,gemini-2.5-flash-lite,gemini-2.0-flash-lite`.
The wrapper tries them in order. On a 429 quota error, it falls through to
the next model automatically. The pipeline trace shows which model actually
answered, so the examiner can see the system gracefully degraded rather
than failed."

### Q: How do you handle Hindi?

**A:** "Two layers. The frontend has English and Hindi JSON dictionaries
in `src/i18n/` — every UI string is in both. The backend prompt builder
inserts a strict language instruction into the system prompt and repeats
it at the end of the user prompt, explicitly listing every field that
must be in the chosen language. Statute names and section numbers stay
in English so they remain searchable."

### Q: How could you scale to 10× more PDFs?

**A:** "Swap the NumPy store for a real ANN index like FAISS — its public
interface in `retriever.py` is preserved, so only the implementation file
changes. Beyond that, batch the embedding generation on GPU if available,
and consider persisting conversation history to SQLite for multi-session
chats."

---

## 12. Troubleshooting

| Error | What it means | Fix |
|---|---|---|
| `Microsoft Visual C++ 14.0 or greater is required` | Some library is trying to compile from source | Use Python 3.12, not 3.13 |
| `Activate.ps1 cannot be loaded` | PowerShell blocks unsigned scripts | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `LLMConfigError: GEMINI_API_KEY is not set` | `.env` missing or in the wrong folder | Must be at `backend/.env` |
| `Vector store is empty` | You forgot to ingest | Run `python ingest.py` from `backend/` |
| `429 RESOURCE_EXHAUSTED` once and works after | Per-minute rate limit | Slow down, wait 30 sec between rapid clicks |
| `429 RESOURCE_EXHAUSTED` consistently with `limit: 20` | Daily quota exhausted on one model | The fallback chain handles this. If all models are exhausted, wait or enable billing |
| Frontend page loads but `Ask` button does nothing | Backend not running | Check Terminal 1 shows "Uvicorn running on :8000" |
| `JSX syntax extension is not currently enabled` | A `.js` file contains JSX | The i18n file is already named `.jsx`. If you see this, check the import path |
| `ECONNREFUSED` proxy errors in frontend terminal | Backend was stopped or crashed | Restart backend |
| Hindi text shows as boxes | Missing Devanagari font | Install Noto Sans Devanagari |
| Backend takes 30+ seconds on first request | First-time model load | Normal once. Hit `GET /api/health` to warm up before demoing |
| Follow-up answer ignores context | History array malformed or empty | Open browser DevTools → Network → /api/qa → check the request body has a non-empty `history` field |
| Document follow-ups don't reference the document | `documentContext` not sent | Make sure you ran the initial analysis first; the doc text is captured then |
| Hindi answer comes back in English | LLM ignored language instruction | Try a different model in the fallback chain. The newer flash models follow Hindi instructions more reliably |
| `The AI returned an incomplete response` on document analysis | Model output was truncated (very long document) or genuinely malformed | Try a shorter document or be more specific in the "concern" field. The postprocessor now auto-recovers most truncations — if you see this it means even recovery failed |
| Mobile menu hamburger doesn't appear | You're viewing at ≥ 1024 px wide | Resize your browser narrower, or use DevTools device mode |

---

## 13. Going deeper

### Concepts to study

- **Embeddings** — read the `BERT` and `Sentence-BERT` papers.
- **Cross-encoders vs bi-encoders** — `MS MARCO` literature.
- **Prompt engineering** — Anthropic and OpenAI publish good guides.
- **RAG patterns** — search papers from 2023 onwards; the field evolves fast.

### Next features to add

1. **Tests.** `pytest` already in `requirements-dev.txt`. Easy first
   targets: `classifier.py` (pure function), `postprocessor.py` (malformed
   JSON edge cases).
2. **Streaming responses.** Gemini supports SSE; frontend can render
   incrementally. Add `/api/qa/stream`.
4. **Server-side conversation persistence.** Currently history lives only in
   the browser. Add a SQLite table keyed by session ID for multi-session
   chats.
5. **More PDFs.** Edit `backend/scripts/acts_manifest.json` and re-run
   `python -m scripts.fetch_acts`.
6. **Authentication.** Single-user demo right now. If you deploy publicly,
   only `main.py` needs changes — every route already returns clean
   envelopes.

### What was improved most recently

**Latest round — performance, UX polish, robustness:**

- **Pipeline trace collapsed by default.** Cleaner answer area; click the
  trace bar under any response to expand the X-ray view.
- **Retrieval & rerank tuned for speed.** Lowered defaults: `retrieval_top_k`
  20 → 12 and `rerank_top_k` 5 → 4. Reranking is noticeably faster with no
  observable precision loss at this corpus size.
- **Per-mode output token budgets.** CHAT follow-ups now request only 1024
  output tokens (was 2048) — concise replies don't need the headroom, so
  the LLM round-trip is ~30-40% faster on follow-ups. Document analysis was
  bumped to 8192 tokens so exhaustive "every clause, every risk" output
  doesn't get truncated.
- **Postprocessor hardened against malformed JSON.** Now handles smart/curly
  quotes (`"`/`"` → `"`), trailing commas, and truncated output (counts
  unclosed brackets and closes them to recover a partial response). The
  error message when parsing genuinely fails now explains *why* (likely
  truncated due to large document) instead of just "did not return JSON".
- **`config.py` defaults improved.** Default `GEMINI_MODEL` is now the full
  fallback chain `gemini-3.1-flash-lite,gemini-2.5-flash-lite,gemini-2.0-flash-lite`,
  so the project works out-of-the-box even without a custom `.env`.
- **Mobile menu fixed.** Hamburger now appears below the `lg` breakpoint
  (1024px) instead of `md` (768px) — covers phones, tablets, and small
  laptops. Drawer animates via height-expand, closes on link tap or route
  change, body scroll locks while open.
- **Copy-to-clipboard on every assistant bubble.** Hover (or focus) shows a
  Copy button in the bubble header; click copies the answer text; turns
  into "✓ Copied" for 1.5s.
- **Empty-state suggestion chips.** New chats on `/chat` and `/strategy`
  show 4 clickable example prompts (English + Hindi swap based on language).
  Click one → submits as your first question. Disappears once a conversation
  starts.
- **`.env.example` consolidated into `.env`.** Single config file; the
  `GEMINI_MODEL` line is pre-filled with the fallback chain so you only
  need to paste your API key.

**Earlier rounds:**

- **Strategy is now a distinct feature.** Returns a phased action plan with
  per-phase title, duration, qualitative cost, statutory hooks, and
  risk-if-skipped — its own prompt mode `STRATEGY` and dedicated frontend
  renderer with cost-coded pills.
- **Follow-ups feel like chat.** New `CHAT` prompt mode returns 2-5 sentence
  conversational answers with inline citation chips, not full structured
  reports. The full panel (provisions, citations, trace) is shown only under
  the *first* assistant turn.
- **Document follow-ups work properly.** Doc analyzer follow-ups now go
  through `CHAT` mode with the document text preserved as `document_context`,
  so questions are answered concisely using both the document and retrieved
  Indian law.
- **OCR for scanned PDFs and images.** Uploaded files that don't have a text
  layer (scanned PDFs, photographed notices) now run through EasyOCR. Supports
  both English and Hindi. Image files (.jpg, .png) are also accepted directly.
- Conversational follow-ups in Q&A, Strategy, and Document Analyzer pages.
- Document text preserved post-analysis so follow-ups can reference it.
- Document analysis prompt asks for **every** key clause and **every**
  risky clause, with a 6–10 sentence summary, larger output token budget.
- **Rights section removed.** Functionality (categorised rights with
  statutory basis) was duplicating what the Q&A page can produce when
  asked directly. Five focused features is cleaner than six overlapping ones.
- Hindi language enforcement strengthened — instruction repeated in both
  system and user prompts.
- `retriever.add()` batches insertions so ingestion does O(batches) array
  copies instead of O(chunks).
- Removed unused `chroma_collection` config setting.
- Home page: secondary CTA now correctly labelled "Build a Case Strategy"
  matching its `/strategy` destination; Strategy feature tile added to the
  landing feature grid (was missing).

### Where the data came from

The 10 Indian Act PDFs were downloaded from:
- `mha.gov.in` — BNS, BNSS, BSA (Ministry of Home Affairs)
- `legislative.gov.in` — Constitution
- `meity.gov.in` — IT Act
- `ncdrc.nic.in` — Consumer Protection Act
- `labour.gov.in` — Code on Wages
- `hrylabour.gov.in` — Industrial Disputes Act
- `cdnbbsr.s3waas.gov.in` — Hindu Marriage Act, Transfer of Property Act

`indiacode.nic.in` was avoided because its bitstream URLs require an
interactive browser session.

---

Read this end-to-end once, then run the app and explore the Pipeline Trace
under a few questions. By the third question you'll see exactly how every
part you read about shows up live in the trace.

Good luck.
