import math
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from ai_sample_notes import AI_SAMPLE_NOTES

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL_NAME)

@lru_cache(maxsize=1)
def get_sample_embeddings():
    model = get_model()
    texts = [item["content"] for item in AI_SAMPLE_NOTES]
    return model.encode(texts, normalize_embeddings=True)

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def semantic_search(query: str, top_k: int = 3):
    model = get_model()
    query_embedding = model.encode(query, normalize_embeddings=True)
    embeddings = get_sample_embeddings()

    ranked = []
    for item, embedding in zip(AI_SAMPLE_NOTES, embeddings):
        score = cosine_similarity(query_embedding, embedding)
        ranked.append({
            "title": item["title"],
            "content": item["content"],
            "similarity": round(float(score), 6),
        })

    # Manual descending insertion sort so this ranking is deterministic without
    # relying on an external search service.
    for i in range(1, len(ranked)):
        current = ranked[i]
        j = i - 1
        while j >= 0 and ranked[j]["similarity"] < current["similarity"]:
            ranked[j + 1] = ranked[j]
            j -= 1
        ranked[j + 1] = current

    return ranked[:top_k]
