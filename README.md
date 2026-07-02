# Redrob Intelligent Candidate Ranker

**Redrob Hackathon — Intelligent Candidate Discovery & Ranking Challenge**

## Reproduce the submission

```bash
pip install -r requirements.txt
python rank.py --candidates ./candidates.jsonl --out ./Top100.xlsx
python validate_submission.py Top100.xlsx
```

Runs in ~100 seconds on 16GB CPU. No GPU. No network calls during ranking.

## Run the sandbox locally

```bash
streamlit run app.py
```

Upload any `.jsonl` file with up to 100 candidates, or click **Use bundled sample**.

**The full candidates.jsonl dataset (464 MB) is not included in the repository due to GitHub file size limits. Place the dataset locally and run:**

python rank.py --candidates candidates.jsonl --out outputs/submission.xlsx

## Architecture

Eight signals, each in its own module:

| Signal | Weight | What it does |
|--------|--------|-------------|
| Semantic match | 30% | TF-IDF cosine similarity between JD and full candidate profile |
| Career relevance | 20% | Scans job descriptions for actual retrieval/ranking/recommendation work — not skill tags |
| Company quality | 12% | Product company vs. pure-services background |
| Experience fit | 12% | YoE curve centred on JD's 6-8yr sweet spot |
| Skill match | 12% | Weighted by proficiency + endorsements against JD must-haves |
| Behavioral signals | 8% | Recency-gated: response rate, notice period, last-active date |
| Location fit | 4% | Pune/Noida preferred, India next, relocation-willing last |
| Skill assessments | 2% | Platform's own objective test scores |

### Why TF-IDF and not transformer embeddings

The spec requires ranking to complete in ≤5 minutes on a 16GB CPU-only machine with no network. Per-candidate transformer inference over 100K rows takes 30-90 minutes on CPU. TF-IDF with sklearn's vectorised cosine similarity scores all 100K in under 60 seconds.

### Why career_relevance is the key signal

`career_relevance.py` reads each job description and distinguishes:

- A candidate who **led** a recommendation system for 3 years at a product company (high score)
- A candidate who **contributed to** a retrieval project for 4 months at a services firm (lower score)
- A candidate who lists "RAG, Pinecone" in skills but whose job descriptions show only dashboards (near-zero score)

It does this through duration-weighted scoring, ownership-language detection (`led/owned/built` → 1.5× multiplier, `contributed to` → 0.7×), and diminishing qualifiers (`"30% of my time on ML"` → score × 0.3).

### Filters

- Off-domain titles (HR Manager, Sales Executive, Marketing Manager, etc.) — hard excluded
- Honeypot profiles (experience inconsistency, all-max signals simultaneously) — excluded
- Low response rate + not open-to-work → final score × 0.6

## File structure

```
rank.py                        ← single entry point
app.py                         ← Streamlit sandbox
requirements.txt
validate_submission.py
submission_metadata.yaml
outputs/Top100.xlsx        ← submitted XLSX
data/sample_candidates.jsonl  ← 20-candidate sandbox sample
src/
  main.py                      ← orchestrates load → score → filter → rank → write
  parse_jd.py                  ← JD requirements as structured config
  semantic_score.py            ← TF-IDF semantic matching
  career_relevance.py          ← duration-weighted career history scoring
  scoring.py                   ← experience, company, skills, behavior, location
  explain.py                   ← per-candidate reasoning string generation
```
