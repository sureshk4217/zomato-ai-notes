import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from algorithms import binary_search_iterative, binary_search_recursive, insertion_sort_by_key, linear_search
from ai_service import AUTO_TAG_PROMPT, get_ai_response
from database import Base, engine, get_db
from models import Note, User
from schemas import NoteCreate, NoteResponse, NoteUpdate, UserCreate, UserResponse
from semantic_search import semantic_search

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zomato-notes")

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Zomato Notes API", version="1.0.0")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5500")
DELETE_TOKEN = os.getenv("DELETE_TOKEN", "zomato-delete-token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def process_time_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"
    return response

def verify_delete_token(x_token: Optional[str]):
    if x_token != DELETE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing x-token")

def check_owner(db: Session, owner_id: int):
    owner = db.query(User).filter(User.id == owner_id).first()
    if owner is None:
        raise HTTPException(status_code=404, detail="Owner user not found")
    return owner

def background_index(note_id: int):
    time.sleep(2)
    logger.info("Background indexing completed for note_id=%s at %s", note_id, datetime.now(timezone.utc).isoformat())

def make_ai_suggestion(content: str):
    try:
        raw = get_ai_response(content, AUTO_TAG_PROMPT)
        parsed = json.loads(raw)
        if (
            isinstance(parsed, dict)
            and set(parsed.keys()) == {"tags", "summary"}
            and isinstance(parsed["tags"], list)
            and 1 <= len(parsed["tags"]) <= 3
            and all(isinstance(x, str) and x == x.lower() for x in parsed["tags"])
            and isinstance(parsed["summary"], str)
            and len(parsed["summary"].split()) <= 20
        ):
            return parsed
        logger.warning("Invalid AI response: %s", raw)
    except Exception:
        logger.exception("AI suggestion failed")
    return None

def note_dict(note):
    return {
        "id": note.id, "title": note.title, "content": note.content,
        "tag": note.tag, "owner_id": note.owner_id, "created_at": note.created_at
    }

@app.get("/")
def root():
    return {"message": "Zomato Notes API", "docs": "/docs"}

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(name=payload.name, email=payload.email, password=payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(payload: NoteCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    check_owner(db, payload.owner_id)
    note = Note(title=payload.title, content=payload.content, tag=payload.tag, owner_id=payload.owner_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    background_tasks.add_task(background_index, note.id)
    suggestion = make_ai_suggestion(note.content)
    result = note_dict(note)
    result["ai_suggestion"] = suggestion
    return result

@app.get("/notes", response_model=list[NoteResponse])
def list_notes(tag: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Note)
    if tag:
        q = q.filter(Note.tag == tag)
    return q.order_by(Note.id.asc()).all()

@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return note

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, x_token: Optional[str] = Header(None), db: Session = Depends(get_db)):
    verify_delete_token(x_token)
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted", "id": note_id}

@app.post("/notes/import")
async def import_notes(owner_id: int = Query(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    check_owner(db, owner_id)
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted")
    raw = await file.read()
    lines = [x.strip() for x in raw.decode("utf-8").splitlines() if x.strip()]
    created = []
    for i, line in enumerate(lines, 1):
        note = Note(title=f"Imported Note {i}", content=line, tag="imported", owner_id=owner_id)
        db.add(note)
        created.append(note)
    db.commit()
    return {"created_count": len(created), "owner_id": owner_id}

@app.get("/reports/tag-summary")
def tag_summary(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT tag, COUNT(*) AS note_count
        FROM notes
        GROUP BY tag
        HAVING COUNT(*) > 1
        ORDER BY note_count DESC, tag ASC
    """)).fetchall()
    return [dict(r._mapping) for r in rows]

@app.get("/reports/long-notes")
def long_notes(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, title, content, tag, owner_id, created_at
        FROM notes
        WHERE LENGTH(content) > (SELECT AVG(LENGTH(content)) FROM notes)
        ORDER BY id ASC
    """)).fetchall()
    return [dict(r._mapping) for r in rows]

@app.get("/reports/user-notes")
def user_notes(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT u.id, u.name, u.email, COUNT(n.id) AS note_count
        FROM users u
        LEFT JOIN notes n ON n.owner_id = u.id
        GROUP BY u.id, u.name, u.email
        ORDER BY u.id ASC
    """)).fetchall()
    return [dict(r._mapping) for r in rows]

@app.get("/notes/search")
def ranked_search(keyword: Optional[str] = None, sort_by: Optional[str] = None, db: Session = Depends(get_db)):
    notes = [note_dict(n) for n in db.query(Note).all()]
    if sort_by == "date":
        for n in notes:
            created = n["created_at"]
            n["created_at_epoch"] = created.replace(tzinfo=timezone.utc).timestamp() if created.tzinfo is None else created.timestamp()
        return insertion_sort_by_key(notes, "created_at_epoch")[:5]
    if keyword is None:
        raise HTTPException(status_code=400, detail="Provide keyword or sort_by=date")
    needle = keyword.casefold()
    for n in notes:
        n["score"] = n["content"].casefold().count(needle) if needle else 0
    return insertion_sort_by_key(notes, "score")[:5]

@app.get("/notes/lookup")
def title_lookup(title: str, algo: str = Query("iterative", pattern="^(iterative|recursive)$"), db: Session = Depends(get_db)):
    notes = db.query(Note).order_by(Note.title.asc()).all()
    titles = [n.title for n in notes]
    if algo == "iterative":
        index = binary_search_iterative(titles, title)
    else:
        index = binary_search_recursive(titles, title, 0, len(titles) - 1)
    if index == -1:
        raise HTTPException(status_code=404, detail="Title not found")
    return note_dict(notes[index])

@app.get("/notes/quick-find")
def quick_find(tag: str, db: Session = Depends(get_db)):
    notes = [note_dict(n) for n in db.query(Note).filter(Note.tag == tag).all()]
    result = linear_search(notes, "tag", tag)
    if result is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return result

@app.get("/notes/smart-search")
def smart_search(q: str):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")
    return semantic_search(q.strip(), top_k=3)
