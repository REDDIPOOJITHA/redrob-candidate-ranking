"""
scoring.py
Experience, company quality, skill match, behavior, location signals.
"""
from datetime import date
from parse_jd import (
    MUST_HAVE_SKILLS, NICE_TO_HAVE_SKILLS,
    PRODUCT_COMPANIES, SERVICE_COMPANIES,
    DISQUALIFYING_TITLES, PREFERRED_LOCATIONS,
)


# ── Experience ────────────────────────────────────────────────────────────────

def experience_score(candidate):
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    try:
        yoe = float(yoe)
    except Exception:
        yoe = 0
    if 6 <= yoe <= 8:   return 1.0
    if 5 <= yoe < 6:    return 0.85
    if 8 < yoe <= 9:    return 0.85
    if 4 <= yoe < 5:    return 0.65
    if 9 < yoe <= 12:   return 0.70
    if 3 <= yoe < 4:    return 0.40
    if yoe > 12:        return 0.50
    return 0.10


# ── Company quality ───────────────────────────────────────────────────────────

def company_quality_score(candidate):
    history = candidate.get("career_history", [])
    if not history:
        return 0.4
    product = service = 0
    for job in history:
        co = str(job.get("company", "")).lower()   # ← correct field
        if any(p in co for p in PRODUCT_COMPANIES):
            product += 1
        elif any(s in co for s in SERVICE_COMPANIES):
            service += 1
    total = len(history)
    if product > 0 and service == 0:
        return min(1.0, 0.6 + (product / total) * 0.4)
    if product > 0:
        return 0.5 + (product / total) * 0.3
    if service == total:
        return 0.15
    return 0.35


# ── Skill match ───────────────────────────────────────────────────────────────

def skill_score(candidate):
    PROF = {"beginner": 0.4, "intermediate": 0.7, "advanced": 1.0}
    skill_map = {}

    for s in candidate.get("skills", []):
        if isinstance(s, dict):
            name = s.get("name", "").lower().strip()
            w = PROF.get(s.get("proficiency", "intermediate"), 0.7)
            endorse_boost = min(s.get("endorsements", 0) / 50, 0.3) * 0.1
            skill_map[name] = min(w + endorse_boost, 1.0)

    # Also scan career text for implied skills
    all_text = " ".join(
        job.get("description", "").lower()
        for job in candidate.get("career_history", [])
    ) + " " + candidate.get("profile", {}).get("summary", "").lower()

    for skill in MUST_HAVE_SKILLS | NICE_TO_HAVE_SKILLS:
        if skill in all_text and skill not in skill_map:
            skill_map[skill] = 0.5

    must = len(MUST_HAVE_SKILLS)
    nice = len(NICE_TO_HAVE_SKILLS)

    must_score = sum(skill_map.get(s, 0) for s in MUST_HAVE_SKILLS if s in skill_map) / must
    nice_score = sum(skill_map.get(s, 0) for s in NICE_TO_HAVE_SKILLS if s in skill_map) / nice

    return 0.80 * must_score + 0.20 * nice_score


# ── Behavioral availability ───────────────────────────────────────────────────

def _days_since(date_str):
    if not date_str:
        return 999
    try:
        d = date(*[int(x) for x in date_str[:10].split("-")])
        return (date(2026, 7, 1) - d).days
    except Exception:
        return 999


def behavior_score(candidate):
    signals = candidate.get("redrob_signals", {})

    days = _days_since(signals.get("last_active_date"))
    if days <= 30:   recency = 1.0
    elif days <= 60: recency = 0.85
    elif days <= 90: recency = 0.70
    elif days <= 180:recency = 0.40
    elif days <= 365:recency = 0.15
    else:            recency = 0.0

    # Availability
    avail = 0.0
    if signals.get("open_to_work_flag", False):
        avail += 0.40
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:   avail += 0.35
    elif notice <= 60: avail += 0.20
    elif notice <= 90: avail += 0.05
    avail += 0.25 * signals.get("recruiter_response_rate", 0)

    # Engagement
    engage = 0.0
    engage += 0.20 * (signals.get("profile_completeness_score", 0) / 100)
    engage += 0.20 * min(signals.get("github_activity_score", 0) / 10, 1.0)
    engage += 0.20 * signals.get("interview_completion_rate", 0)
    engage += 0.15 * min(signals.get("saved_by_recruiters_30d", 0) / 10, 1.0)
    engage += 0.10 * min(signals.get("profile_views_received_30d", 0) / 50, 1.0)
    engage += 0.15 * signals.get("offer_acceptance_rate", 0.5)

    base = 0.40 * min(avail, 1.0) + 0.60 * min(engage, 1.0)
    gated = recency * base + (1 - recency) * base * 0.2
    return min(gated, 1.0)


# ── Location ──────────────────────────────────────────────────────────────────

def location_score(candidate):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    loc = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    relocate = signals.get("willing_to_relocate", False)

    if any(p in loc for p in PREFERRED_LOCATIONS):
        return 1.0
    if country == "india":
        return 0.80
    if relocate:
        return 0.60
    return 0.25


# ── Filters ───────────────────────────────────────────────────────────────────

def title_disqualifier(candidate):
    title = candidate.get("profile", {}).get("current_title", "").lower()
    for bad in DISQUALIFYING_TITLES:
        if bad in title:
            return False
    return True


def detect_honeypot(candidate):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    history = candidate.get("career_history", [])
    title = profile.get("current_title", "").lower()
    skills = [s.get("name", "").lower() for s in candidate.get("skills", []) if isinstance(s, dict)]

    # Non-tech title with many AI skills stuffed in
    non_tech = any(t in title for t in DISQUALIFYING_TITLES)
    ai_skills = sum(1 for s in skills if any(
        kw in s for kw in ["python", "llm", "embedding", "ml", "ai", "deep learning"]
    ))
    if non_tech and ai_skills >= 5:
        return True

    # Experience inconsistency
    yoe = profile.get("years_of_experience", 0)
    total_months = sum(j.get("duration_months", 0) for j in history)
    if total_months > 0 and yoe > 0:
        if yoe < (total_months / 12) * 0.4 and yoe > 2:
            return True

    # Statistically impossible perfect signals
    if (signals.get("profile_completeness_score", 0) == 100 and
            signals.get("recruiter_response_rate", 0) == 1.0 and
            signals.get("interview_completion_rate", 0) == 1.0 and
            signals.get("github_activity_score", 0) == 10 and
            signals.get("offer_acceptance_rate", 0) == 1.0):
        return True

    return False


# ── Skill assessment ──────────────────────────────────────────────────────────

def skill_assessment_score(candidate):
    signals = candidate.get("redrob_signals", {})
    assessments = signals.get("skill_assessment_scores", {})
    if not assessments:
        return 0.5
    RELEVANT = {"python", "machine learning", "nlp", "deep learning",
                "sql", "llm", "embeddings", "data structures", "algorithms"}
    scores = [v / 100 for k, v in assessments.items() if k.lower() in RELEVANT]
    if not scores:
        scores = [v / 100 for v in assessments.values()]
    return sum(scores) / len(scores) if scores else 0.5
