# Zomato Notes — AI-Augmented Internal Knowledge Base

A single integrated FastAPI + SQLite + plain HTML/CSS/JavaScript capstone.

## 1. Repository structure

```text
zomato-notes/
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── algorithms.py
│   ├── ai_service.py
│   ├── semantic_search.py
│   ├── ranking_dataset.py
│   ├── ai_sample_notes.py
│   ├── seed.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── sample_import.txt
├── .gitignore
└── README.md
```

## 2. Setup

Python 3.10+ is recommended.

```bash
git clone <YOUR_PUBLIC_REPOSITORY_URL>
cd zomato-notes

python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Copy `.env.example` to `.env`. The default is offline mock AI:

```text
MOCK_AI=1
```

No API key is needed for the graded baseline.

## 3. Seed the database

From `backend/`:

```bash
python seed.py
```

Expected:

```text
Database seeded successfully.
```

## 4. Run backend

From `backend/`:

```bash
uvicorn main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## 5. Run frontend

Open a second terminal at the repository root:

```bash
python -m http.server 5500 --directory frontend --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:5500
```

CORS is configured for exactly:

```text
http://127.0.0.1:5500
```

If you serve the frontend from another origin, change `FRONTEND_ORIGIN` in `.env`.

## 6. Seed users

The seed contains:

```text
Alice: alice@example.com / alicepass123
Bob:   bob@example.com / bobpass123
```

These are demo credentials only.

The seed creates the required baseline notes, 12 ranking notes with `kb-demo`, and 8 AI sample notes with `ai-demo`.

## 7. Part 1 API examples

### Create user

```http
POST /users
Content-Type: application/json

{
  "name": "Charlie",
  "email": "charlie@example.com",
  "password": "charlie123"
}
```

### Create note

```http
POST /notes
Content-Type: application/json

{
  "title": "Incident follow-up",
  "content": "Investigated payment timeout errors and confirmed the database pool was exhausted.",
  "tag": "incident",
  "owner_id": 1
}
```

The response contains:

```json
{
  "id": 23,
  "title": "Incident follow-up",
  "content": "Investigated payment timeout errors and confirmed the database pool was exhausted.",
  "tag": "incident",
  "owner_id": 1,
  "created_at": "...",
  "ai_suggestion": {
    "tags": ["investigated", "payment", "timeout"],
    "summary": "Investigated payment timeout errors and confirmed the database pool was exhausted."
  }
}
```

### List/filter

```http
GET /notes
GET /notes?tag=work
GET /notes/1
```

### Update

```http
PUT /notes/1
Content-Type: application/json

{
  "title": "Updated title",
  "tag": "incident"
}
```

### Delete

Missing token:

```http
DELETE /notes/1
```

Expected: `401`.

Correct token:

```http
DELETE /notes/1
x-token: zomato-delete-token
```

Expected: `200`.

Every response includes:

```text
X-Process-Time: <seconds>
```

### Invalid payload examples

Malformed email:

```json
{
  "name": "Test",
  "email": "not-an-email",
  "password": "password123"
}
```

Expected: `422`.

Short password:

```json
{
  "name": "Test",
  "email": "test@example.com",
  "password": "short"
}
```

Expected: `422`.

Over-length title:

```json
{
  "title": "<121 characters>",
  "content": "test",
  "tag": "work",
  "owner_id": 1
}
```

Expected: `422`.

### Invalid owner

```http
POST /notes
```

with:

```json
{
  "title": "Invalid owner",
  "content": "This must not be inserted.",
  "tag": "test",
  "owner_id": 99999
}
```

Expected: `404`, with no orphan note.

## 8. Bulk import

Use `sample_import.txt`:

```http
POST /notes/import?owner_id=1
Content-Type: multipart/form-data
```

The five non-empty lines create five notes.

An invalid owner returns `404` before any line is processed.

## 9. Raw SQL reports

```http
GET /reports/tag-summary
GET /reports/long-notes
GET /reports/user-notes
```

The tag summary uses `GROUP BY` and `HAVING COUNT(*) > 1`.

The long-notes report uses a subquery comparing each note length against the average.

The user report uses a SQL `JOIN`.

## 10. Background task

`POST /notes` registers a background job that waits two seconds and logs an indexing completion message.

The HTTP response is returned before that background log is printed.

## 11. Part 2 — ranking engine

`backend/algorithms.py` contains four handwritten algorithms:

- `insertion_sort_by_key`
- `binary_search_iterative`
- `binary_search_recursive`
- `linear_search`

There is no `sorted()` or `.sort()` in that file.

### Relevance search

```http
GET /notes/search?keyword=apple
```

The endpoint counts case-insensitive keyword occurrences in content and uses insertion sort.

Try:

```http
GET /notes/search?keyword=apple
GET /notes/search?keyword=coffee
```

### Date sort

```http
GET /notes/search?sort_by=date
```

The same insertion sort is reused with `created_at_epoch`.

### Exact title lookup

```http
GET /notes/lookup?title=Apple%20Harvest%20Notes&algo=iterative
GET /notes/lookup?title=Apple%20Harvest%20Notes&algo=recursive
```

The database performs:

```sql
ORDER BY title ASC
```

and the selected binary-search implementation locates the title.

### Quick tag jump

```http
GET /notes/quick-find?tag=work
GET /notes/quick-find?tag=health
GET /notes/quick-find?tag=recipes
GET /notes/quick-find?tag=travel
GET /notes/quick-find?tag=random
```

The frontend renders five buttons and highlights the returned note.

## 12. Part 3 — AI auto-tagging

The default graded mode is:

```text
MOCK_AI=1
```

It requires:

- no API key
- no signup
- no LLM network request

The mock path returns deterministic JSON containing `tags` and `summary`.

The prompt template is stored verbatim in `backend/ai_service.py` in `AUTO_TAG_PROMPT`.

The real note creation path calls `get_ai_response()`, parses the result with `json.loads`, and returns `ai_suggestion`.

A parse/API failure never prevents note creation; the suggestion becomes `null`.

The frontend shows an `AI Suggests` panel and an `Apply as tag` button.

## 13. Optional real LLM mode

Set:

```text
MOCK_AI=0
GROQ_API_KEY=<your-key>
GROQ_MODEL=llama-3.1-8b-instant
```

Never commit `.env`.

The implementation uses a chat-completions compatible request with system/user message roles.

## 14. Smart Search

The implementation uses exactly:

```text
sentence-transformers==3.0.0
sentence-transformers/all-MiniLM-L6-v2
```

First model load requires internet to download and cache the model.

Run once while online by starting the backend and making a request such as:

```http
GET /notes/smart-search?q=leg%20day%20exercise%20plan
```

The model is cached locally by Hugging Face, normally under:

```text
~/.cache/huggingface
```

After the model weights are cached, the semantic-search operation itself does not need an API key or LLM service.

### Required checks

```http
GET /notes/smart-search?q=leg%20day%20exercise%20plan
```

`Gym schedule change` should appear in the top three.

```http
GET /notes/smart-search?q=dinner%20ideas%20with%20vegetables
```

`Recipe idea` should appear in the top three.

The frontend Smart Search control is separate from the literal keyword search.

## 15. Frontend requirements covered

The frontend uses:

- semantic HTML
- external CSS
- real `fetch()` calls
- dynamic `createElement()` / `appendChild()`
- client-side validation
- inline errors
- 400ms debounced search
- recursive category-tree rendering
- loading state
- backend error state
- sticky navigation
- responsive layout at 600px
- no inline event handlers
- no `alert()`, `confirm()`, or `prompt()`

## 16. End-to-end verification

With both servers running:

1. Open the frontend.
2. Confirm the initial `GET /notes`.
3. Add a note.
4. Confirm `POST /notes` in browser DevTools → Network.
5. Refresh the browser and confirm the note remains.
6. Delete the note.
7. Confirm `DELETE /notes/{id}` with the `x-token`.
8. Refresh and confirm the note is gone.
9. Test relevance/date sorting.
10. Test both binary-search modes.
11. Test each quick tag button.
12. Test Smart Search.
13. Test `/docs`.
14. Test invalid requests and report endpoints.

## 17. Git workflow for submission

Use one public repository.

Example:

```bash
git init
git add .
git commit -m "feat: build core notes API and dashboard"

git checkout -b part-1-core-app
git add .
git commit -m "feat: complete core app"
git push -u origin part-1-core-app
```

Open and merge a Pull Request into `main`.

Then:

```bash
git checkout main
git pull

git checkout -b part-2-ranking
git add .
git commit -m "feat: integrate ranking algorithms"
git push -u origin part-2-ranking
```

Open and merge the second PR.

Then:

```bash
git checkout main
git pull

git checkout -b part-3-intelligence
git add .
git commit -m "feat: add AI tagging and semantic search"
git push -u origin part-3-intelligence
```

Open and merge the third PR.

Finally submit the single public `main` repository URL through the LMS.

## Important

Do not commit `.env`, API keys, database secrets, or generated virtual-environment files.

Before submission, run through every acceptance criterion in the assignment and replace the example request/response snippets in this README with your own actual run output where the grader expects evidence.
