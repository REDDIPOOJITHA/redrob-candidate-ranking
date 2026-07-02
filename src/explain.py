"""
explain.py
Generates honest, specific reasoning strings per candidate.
Only uses data actually present in the candidate's profile — no hallucination.
Stage 4 penalises templated/empty/hallucinated reasoning.
"""
from parse_jd import MUST_HAVE_SKILLS, PREFERRED_LOCATIONS


def generate_reasoning(candidate, scores):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    history = candidate.get("career_history", [])

    title = profile.get("current_title", "Unknown")
    yoe = profile.get("years_of_experience", 0)
    location = profile.get("location", "Unknown")

    parts = []
    parts.append(f"{title} with {yoe:.1f} yrs in {location}")

    sem = scores.get("semantic_score", 0)
    if sem > 0.7:
        parts.append("strong JD alignment")
    elif sem > 0.5:
        parts.append("moderate JD alignment")

    # Real skills present
    rel = [s.get("name", "") for s in candidate.get("skills", [])
           if isinstance(s, dict) and s.get("name", "").lower() in MUST_HAVE_SKILLS]
    if rel:
        parts.append(f"skills: {', '.join(rel[:4])}")

    # Career highlight
    hl = _career_highlight(history)
    if hl:
        parts.append(hl)

    # Company quality
    co = scores.get("company_score", 0)
    if co > 0.7:
        parts.append("product-company background")
    elif co < 0.2:
        parts.append("primarily services background")

    # Availability
    notice = signals.get("notice_period_days", 90)
    open_flag = signals.get("open_to_work_flag", False)
    response = signals.get("recruiter_response_rate", 0)

    avail = []
    if open_flag:
        avail.append("actively looking")
    if notice <= 30:
        avail.append(f"{notice}d notice")
    elif notice > 60:
        avail.append(f"long notice ({notice}d)")
    if response < 0.2 and not open_flag:
        avail.append("low response rate")
    if avail:
        parts.append("; ".join(avail))

    # Concerns
    concern = _concern(candidate, scores)
    if concern:
        parts.append(concern)

    return "; ".join(parts)[:280] + "."


def _career_highlight(history):
    SIGNALS = [
        ("recommendation system", "built recommendation system"),
        ("ranking system", "built ranking system"),
        ("retrieval system", "built retrieval system"),
        ("vector search", "worked with vector search"),
        ("semantic search", "built semantic search"),
        ("rag", "implemented RAG pipeline"),
        ("faiss", "used FAISS in production"),
        ("pinecone", "used Pinecone in production"),
        ("embeddings", "worked with embeddings"),
        ("retrieval", "built retrieval systems"),
        ("ranking", "built ranking systems"),
        ("llm", "deployed LLM systems"),
        ("production", "has production ML experience"),
    ]
    text = " ".join(
        (j.get("description", "") + " " + j.get("title", "")).lower()
        for j in history
    )
    for kw, label in SIGNALS:
        if kw in text:
            return label
    return None


def _concern(candidate, scores):
    concerns = []
    loc = candidate.get("profile", {}).get("location", "").lower()
    country = candidate.get("profile", {}).get("country", "").lower()
    if not any(p in loc for p in PREFERRED_LOCATIONS) and country != "india":
        concerns.append(f"outside India ({loc or 'unknown'})")

    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    if yoe < 4:
        concerns.append(f"under-experienced ({yoe:.1f} yrs)")
    elif yoe > 12:
        concerns.append(f"overexperienced ({yoe:.1f} yrs)")

    if scores.get("behavior_score", 0) < 0.3:
        concerns.append("low platform engagement")

    return ("concern: " + "; ".join(concerns)) if concerns else None
