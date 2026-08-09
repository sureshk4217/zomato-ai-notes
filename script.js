const API_BASE = "http://127.0.0.1:8000";
const DELETE_TOKEN = "zomato-delete-token";

const CATEGORY_TREE = {
  name: "All Tags",
  children: [
    { name: "Work", children: [
      { name: "Standups", children: [] },
      { name: "Retros", children: [] },
    ]},
    { name: "Personal", children: [
      { name: "Health", children: [
        { name: "Fitness", children: [] },
      ]},
      { name: "Recipes", children: [] },
    ]},
    { name: "Travel", children: [] },
  ],
};

let allNotes = [];
let debounceTimer = null;

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

async function fetchNotes(tag = "") {
  return request(tag ? `/notes?tag=${encodeURIComponent(tag)}` : "/notes");
}

async function createNote(note) {
  return request("/notes", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(note),
  });
}

async function deleteNote(id) {
  return request(`/notes/${id}`, {
    method: "DELETE",
    headers: {"x-token": DELETE_TOKEN},
  });
}

async function updateNote(id, patch) {
  return request(`/notes/${id}`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(patch),
  });
}

function showError(message, target = "error") {
  const el = document.getElementById(target);
  el.textContent = message;
  el.classList.remove("hidden");
}

function clearError(target = "error") {
  document.getElementById(target).classList.add("hidden");
}

function renderNotes(notes) {
  const list = document.getElementById("notesList");
  list.innerHTML = "";

  notes.forEach(note => {
    const card = document.createElement("article");
    card.className = "note-card";
    card.dataset.noteId = note.id;

    const title = document.createElement("h3");
    title.textContent = note.title;

    const content = document.createElement("p");
    content.textContent = note.content;

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `#${note.id} • ${note.tag} • owner ${note.owner_id}`;

    const del = document.createElement("button");
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      try {
        await deleteNote(note.id);
        card.remove();
        allNotes = allNotes.filter(n => n.id !== note.id);
      } catch (e) {
        showError(e.message);
      }
    });

    card.append(title, content, meta, del);

    if (note.ai_suggestion) renderAISuggestion(card, note);
    list.appendChild(card);
  });
}

function renderAISuggestion(card, note) {
  const box = document.createElement("div");
  box.className = "ai-box";

  const heading = document.createElement("strong");
  heading.textContent = "AI Suggests";

  const tags = document.createElement("div");
  tags.textContent = `Tags: ${note.ai_suggestion.tags.join(", ")}`;

  const summary = document.createElement("div");
  summary.textContent = `Summary: ${note.ai_suggestion.summary}`;

  const apply = document.createElement("button");
  apply.textContent = "Apply as tag";
  apply.addEventListener("click", async () => {
    try {
      const firstTag = note.ai_suggestion.tags[0];
      const updated = await updateNote(note.id, {tag: firstTag});
      note.tag = updated.tag;
      allNotes = allNotes.map(n => n.id === note.id ? {...n, tag: updated.tag} : n);
      renderNotes(allNotes);
    } catch (e) {
      showError(e.message);
    }
  });

  box.append(heading, tags, summary, apply);
  card.appendChild(box);
}

function recursiveRenderTree(node, parent) {
  const li = document.createElement("li");
  const label = document.createElement("div");
  label.className = "tree-node";
  label.textContent = node.name;
  li.appendChild(label);

  if (node.children && node.children.length) {
    const ul = document.createElement("ul");
    node.children.forEach(child => recursiveRenderTree(child, ul));
    label.addEventListener("click", () => ul.classList.toggle("hidden"));
    li.appendChild(ul);
  }
  parent.appendChild(li);
}

function renderCategoryTree() {
  const root = document.getElementById("categoryTree");
  root.className = "tree";
  const ul = document.createElement("ul");
  recursiveRenderTree(CATEGORY_TREE, ul);
  root.appendChild(ul);
}

function renderTagButtons() {
  const container = document.getElementById("tagButtons");
  ["work", "health", "recipes", "travel", "random"].forEach(tag => {
    const button = document.createElement("button");
    button.textContent = tag;
    button.addEventListener("click", async () => {
      try {
        const result = await request(`/notes/quick-find?tag=${encodeURIComponent(tag)}`);
        renderNotes(allNotes);
        const card = document.querySelector(`[data-note-id="${result.id}"]`);
        if (card) {
          card.classList.add("highlight");
          card.scrollIntoView({behavior: "smooth", block: "center"});
        }
      } catch (e) {
        showError(e.message);
      }
    });
    container.appendChild(button);
  });
}

async function loadInitial() {
  try {
    clearError();
    allNotes = await fetchNotes();
    document.getElementById("loading").classList.add("hidden");
    renderNotes(allNotes);
  } catch (e) {
    document.getElementById("loading").classList.add("hidden");
    showError(e.message);
  }
}

document.getElementById("noteForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError("formError");

  const title = document.getElementById("title").value.trim();
  const content = document.getElementById("noteContent").value.trim();
  const tag = document.getElementById("tag").value.trim();

  if (!title || !content) {
    showError("Title and content are required.", "formError");
    return;
  }

  try {
    const note = await createNote({title, content, tag: tag || "general", owner_id: 1});
    allNotes.push(note);
    renderNotes(allNotes);
    event.target.reset();
    document.getElementById("tag").value = "work";
  } catch (e) {
    showError(e.message, "formError");
  }
});

document.getElementById("searchBox").addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    const value = document.getElementById("searchBox").value.trim().toLowerCase();
    const mode = document.getElementById("sortMode").value;

    try {
      if (mode === "relevance" && value) {
        const result = await request(`/notes/search?keyword=${encodeURIComponent(value)}`);
        renderNotes(result);
      } else if (mode === "date") {
        const result = await request("/notes/search?sort_by=date");
        renderNotes(result);
      } else {
        const filtered = allNotes.filter(n =>
          `${n.title} ${n.content} ${n.tag}`.toLowerCase().includes(value)
        );
        renderNotes(filtered);
      }
    } catch (e) {
      showError(e.message);
    }
  }, 400);
});

document.getElementById("sortMode").addEventListener("change", () => {
  document.getElementById("searchBox").dispatchEvent(new Event("input"));
});

document.getElementById("lookupBtn").addEventListener("click", async () => {
  const title = document.getElementById("exactTitle").value.trim();
  const algo = document.getElementById("lookupAlgo").value;
  if (!title) return;
  try {
    const note = await request(`/notes/lookup?title=${encodeURIComponent(title)}&algo=${algo}`);
    renderNotes(allNotes);
    const card = document.querySelector(`[data-note-id="${note.id}"]`);
    if (card) {
      card.classList.add("highlight");
      card.scrollIntoView({behavior: "smooth", block: "center"});
    }
  } catch (e) {
    showError(e.message);
  }
});

document.getElementById("smartBtn").addEventListener("click", async () => {
  const q = document.getElementById("smartQuery").value.trim();
  const results = document.getElementById("smartResults");
  results.innerHTML = "";
  if (!q) return;

  try {
    const data = await request(`/notes/smart-search?q=${encodeURIComponent(q)}`);
    data.forEach(item => {
      const div = document.createElement("div");
      div.className = "smart-result";
      const title = document.createElement("strong");
      title.textContent = item.title;
      const score = document.createElement("span");
      score.textContent = ` — similarity ${item.similarity}`;
      const content = document.createElement("p");
      content.textContent = item.content;
      div.append(title, score, content);
      results.appendChild(div);
    });
  } catch (e) {
    showError(e.message);
  }
});

renderCategoryTree();
renderTagButtons();
loadInitial();
