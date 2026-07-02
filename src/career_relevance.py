"""
career_relevance.py
Reads each job description for ACTUAL retrieval/ranking/recommendation work.
Duration-weighted + ownership language detection.
This is what separates a keyword-stuffer from someone who genuinely built these systems.
"""
import re

DEEP_KEYWORDS = {
    "recommendation system": 3, "recommender system": 3,
    "ranking system": 3, "retrieval system": 3,
    "search engine": 3, "vector search": 3, "semantic search": 3,
    "two-tower": 3, "dual encoder": 3, "dense retrieval": 3,
    "learning to rank": 3, "re-ranking": 2, "reranking": 2,
    "ndcg": 2, "mrr": 2, "map@": 2, "precision@": 2,
    "a/b test": 2, "online evaluation": 2, "offline evaluation": 2,
    "faiss": 2, "pinecone": 2, "weaviate": 2, "qdrant": 2,
    "elasticsearch": 2, "opensearch": 2, "milvus": 2,
    "sentence-transformers": 2, "openai embeddings": 2,
    "embeddings": 1, "vector database": 1, "rag": 1,
    "retrieval": 1, "ranking": 1, "recommendation": 1,
    "similarity search": 1, "llm": 1, "matching": 1,
}

OWNERSHIP = [
    (r"\b(led|owned|built|designed|architected|created|shipped)\b", 1.5),
    (r"\b(responsible for|drove|launched|in charge of)\b", 1.3),
    (r"\b(contributed to|helped|assisted|supported)\b", 0.7),
    (r"\b(familiar with|exposure to|learning|studying)\b", 0.4),
]

DIMINISH = [
    r"\b(\d{1,2})%\s+of\s+(my\s+)?time\b",
    r"\blightweight\b", r"\bnot\s+my\s+main\b",
    r"\bbasic\b", r"\bocccasionally\b",
]


def _score_block(text, duration_months, is_recent):
    if not text:
        return 0.0
    t = text.lower()

    raw = sum(w for kw, w in DEEP_KEYWORDS.items() if kw in t)
    if raw == 0:
        return 0.0

    own = 1.0
    for pat, mult in OWNERSHIP:
        if re.search(pat, t):
            own = max(own, mult)

    dim = 1.0
    for pat in DIMINISH:
        m = re.search(pat, t)
        if m:
            if "%" in pat:
                dim = min(dim, int(m.group(1)) / 100)
            else:
                dim = min(dim, 0.5)

    dur = min(duration_months / 36, 1.0) if duration_months else 0.3
    rec = 1.2 if is_recent else 0.85
    return raw * own * dim * dur * rec


def career_relevance_score(candidate):
    history = candidate.get("career_history", [])
    summary = candidate.get("profile", {}).get("summary", "")

    total = _score_block(summary, 12, True) * 0.5

    sorted_jobs = sorted(
        history,
        key=lambda j: j.get("start_date") or "0000",
        reverse=True,
    )

    for i, job in enumerate(sorted_jobs):
        desc = job.get("description", "")
        title = job.get("title", "")
        duration = job.get("duration_months", 12)
        is_recent = (i == 0)

        title_bonus = 0.3 if any(
            kw in title.lower()
            for kw in ["search", "ranking", "recommendation", "retrieval", "ml", "ai"]
        ) else 0.0

        total += _score_block(desc, duration, is_recent) + title_bonus

    return min(total / 15.0, 1.0)
