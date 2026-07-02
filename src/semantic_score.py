"""
semantic_score.py
TF-IDF + cosine similarity. CPU-only, no model download, vectorised over all 100K.
Scores all candidates against the JD in under 60 seconds.
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from parse_jd import JD_TEXT


JD_EXPANDED = JD_TEXT + """
recommendation system ranking system retrieval system search engine
vector search semantic search two-tower dual encoder dense retrieval
production deployment real users scale latency throughput serving
applied ML AI roles product companies not pure services
embeddings fine-tuning evaluation ndcg mrr map a/b testing
""".strip()


def _clean(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_candidate_text(candidate):
    profile = candidate.get("profile", {})
    parts = []

    parts.append(profile.get("headline", ""))
    parts.append(profile.get("summary", ""))
    parts.append(profile.get("current_title", ""))
    parts.append(profile.get("current_industry", ""))

    # Skills — doubled to give extra weight
    for s in candidate.get("skills", []):
        if isinstance(s, dict):
            name = s.get("name", "")
            parts.append(name)
            parts.append(name)

    # Career history
    for job in candidate.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("company", ""))     # ← correct field name
        parts.append(job.get("description", ""))

    # Education
    for edu in candidate.get("education", []):
        parts.append(edu.get("field_of_study", ""))
        parts.append(edu.get("degree", ""))

    return " ".join(p for p in parts if p)


class SemanticScorer:
    def __init__(self, candidates):
        self.candidates = candidates
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=50000,
            sublinear_tf=True,
            min_df=2,
            max_df=0.95,
        )
        jd_text = _clean(JD_EXPANDED)
        candidate_texts = [_clean(build_candidate_text(c)) for c in candidates]
        corpus = [jd_text] + candidate_texts
        matrix = self.vectorizer.fit_transform(corpus)
        self.jd_vec = matrix[0]
        self.cand_vecs = matrix[1:]

    def score_all(self):
        sims = cosine_similarity(self.jd_vec, self.cand_vecs)[0]
        mn, mx = sims.min(), sims.max()
        if mx > mn:
            return (sims - mn) / (mx - mn)
        return sims
