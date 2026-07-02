"""
main.py — Redrob candidate ranker. Produces submission CSV.

Usage:
    python main.py --input candidates.jsonl --output submission.xlsx

Runs in ~100s on 16GB CPU. No GPU. No network during ranking.
"""
import sys, os, json, csv, argparse, time
from pathlib import Path
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from semantic_score import SemanticScorer
from career_relevance import career_relevance_score
from scoring import (
    experience_score, company_quality_score, skill_score,
    behavior_score, location_score, skill_assessment_score,
    title_disqualifier, detect_honeypot,
)
from explain import generate_reasoning

# ── Weights (tuned to NDCG@10 being 50% of final score) ─────────────────────
W = {
    "semantic":   0.30,   # TF-IDF JD similarity
    "career":     0.20,   # actual retrieval/ranking work in history
    "company":    0.12,   # product vs services background
    "experience": 0.12,   # YoE fit
    "skill":      0.12,   # skill match weighted by proficiency
    "behavior":   0.08,   # recency-gated availability
    "location":   0.04,   # Pune/Noida preferred
    "assessment": 0.02,   # platform skill test scores
}


def load_candidates(path):
    candidates = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    candidates.append(json.loads(line))
                except Exception:
                    continue
    return candidates


def score_one(candidate, sem):
    if detect_honeypot(candidate):
        return None
    if not title_disqualifier(candidate):
        return None

    car = career_relevance_score(candidate)
    co  = company_quality_score(candidate)
    exp = experience_score(candidate)
    sk  = skill_score(candidate)
    beh = behavior_score(candidate)
    loc = location_score(candidate)
    ass = skill_assessment_score(candidate)

    final = (
        W["semantic"]   * sem +
        W["career"]     * car +
        W["company"]    * co  +
        W["experience"] * exp +
        W["skill"]      * sk  +
        W["behavior"]   * beh +
        W["location"]   * loc +
        W["assessment"] * ass
    )

    # Hard gate: very unresponsive + not looking → multiply down
    signals = candidate.get("redrob_signals", {})
    if signals.get("recruiter_response_rate", 0) < 0.10 and \
       not signals.get("open_to_work_flag", False):
        final *= 0.60

    return {
        "candidate_id":  candidate["candidate_id"],
        "final_score":   final,
        "semantic_score": round(sem, 4),
        "career_score":  round(car, 4),
        "company_score": round(co, 4),
        "skill_score":   round(sk, 4),
        "behavior_score":round(beh, 4),
        "_candidate":    candidate,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="../data/candidates.jsonl")
    parser.add_argument("--output", default="../outputs/submission.xlsx")
    args = parser.parse_args()

    # Resolve input path
    inp = Path(args.input)
    if not inp.exists():
        for p in [Path("candidates.jsonl"), Path("../candidates.jsonl")]:
            if p.exists():
                inp = p; break

    print(f"[1/5] Loading {inp} ...")
    t0 = time.time()
    candidates = load_candidates(inp)
    print(f"      {len(candidates):,} candidates in {time.time()-t0:.1f}s")

    print("[2/5] Building TF-IDF index ...")
    t0 = time.time()
    scorer = SemanticScorer(candidates)
    sem_scores = scorer.score_all()
    print(f"      Done in {time.time()-t0:.1f}s")

    print("[3/5] Scoring ...")
    t0 = time.time()
    results = []
    n_honeypot = n_disq = 0
    for i, c in enumerate(candidates):
        if i % 10000 == 0:
            print(f"      {i:,}/{len(candidates):,}", end="\r")
        r = score_one(c, float(sem_scores[i]))
        if r is None:
            if detect_honeypot(c): n_honeypot += 1
            else: n_disq += 1
        else:
            results.append(r)
    print(f"\n      {len(results):,} scored | {n_honeypot} honeypots | {n_disq} disqualified | {time.time()-t0:.1f}s")

    print("[4/5] Ranking top 100 ...")
    results.sort(key=lambda x: (-x["final_score"], x["candidate_id"]))
    top100 = results[:100]

    print("[5/5] Writing XLSX ...")
    max_s = top100[0]["final_score"]
    min_s = top100[-1]["final_score"]
    rng   = max_s - min_s if max_s > min_s else 1.0

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rank, r in enumerate(top100, 1):
        cand = r.pop("_candidate")
        # Strictly monotone score: epsilon per rank prevents validator tie-break errors
        norm = 0.40 + 0.59 * (r["final_score"] - min_s) / rng
        norm = norm - (rank - 1) * 1e-6
        norm = round(min(norm, 0.9999), 6)
        reasoning = generate_reasoning(cand, r)
        rows.append({
            "candidate_id": r["candidate_id"],
            "rank":  rank,
            "score": norm,
            "reasoning": reasoning,
        })

    df = pd.DataFrame(rows, columns=["candidate_id", "rank", "score", "reasoning"])
    if out.suffix.lower() == ".csv":
        df.to_csv(out, index=False)
    else:
        df.to_excel(out, index=False, engine="openpyxl")

    print(f"\n✅ Written to {out}")
    for row in rows[:3]:
        print(f"  #{row['rank']} {row['candidate_id']} score={row['score']}")
        print(f"     {row['reasoning'][:100]}...")


if __name__ == "__main__":
    main()
