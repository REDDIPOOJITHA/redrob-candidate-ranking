"""
app.py — Streamlit sandbox for the Redrob candidate ranker.
Deploy to Streamlit Cloud (free): share.streamlit.io
Accepts up to 100 candidates as .jsonl upload or uses the bundled sample.
"""
import streamlit as st
import json, sys, os, csv, io
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

st.set_page_config(page_title="Redrob Candidate Ranker", page_icon="🎯", layout="wide")
st.title("🎯 Redrob Intelligent Candidate Ranker")
st.caption("8-signal ranking · CPU-only · No LLM API calls · ~100s for 100K candidates")

with st.sidebar:
    st.header("Scoring signals & weights")
    for name, w, desc in [
        ("Semantic match",    "30%", "TF-IDF cosine vs. full JD"),
        ("Career relevance",  "20%", "Actual retrieval/ranking work in job history"),
        ("Company quality",   "12%", "Product company vs. pure services"),
        ("Experience fit",    "12%", "YoE curve centred on 6-8yr sweet spot"),
        ("Skill match",       "12%", "Weighted by proficiency + endorsements"),
        ("Behavioral signals","8%",  "Recency-gated: response rate, notice period"),
        ("Location fit",      "4%",  "Pune/Noida preferred, India next"),
        ("Skill assessments", "2%",  "Platform objective test scores"),
    ]:
        st.markdown(f"**{name}** `{w}`")
        st.caption(desc)
    st.divider()
    st.markdown("**Filters**")
    st.caption("Off-domain titles (HR/Sales/Marketing) → excluded")
    st.caption("Honeypot profiles → excluded")
    st.caption("Response rate <10% + not open-to-work → score ×0.6")

st.subheader("1. Load candidates")
col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader("Upload candidates.jsonl (≤100 candidates)", type=["jsonl", "json"])
with col2:
    use_sample = st.button("▶ Use bundled 20-candidate sample", use_container_width=True)

candidates = []
if uploaded:
    for line in uploaded.read().decode("utf-8").strip().split("\n"):
        line = line.strip()
        if line:
            try: candidates.append(json.loads(line))
            except: st.error(f"Bad JSON line"); break
    if candidates:
        st.success(f"Loaded {len(candidates)} candidates.")
elif use_sample:
    sp = os.path.join(os.path.dirname(__file__), "data", "sample_candidates.jsonl")
    if os.path.exists(sp):
        with open(sp) as f:
            for line in f:
                line = line.strip()
                if line: candidates.append(json.loads(line))
        st.success(f"Loaded {len(candidates)} sample candidates.")
    else:
        st.warning("No sample file found. Please upload a .jsonl file.")

if candidates:
    if len(candidates) > 100:
        st.warning(f"Trimming to 100 for sandbox.")
        candidates = candidates[:100]

    st.subheader("2. Run")
    if st.button("🚀 Rank candidates", type="primary", use_container_width=True):
        with st.spinner("Scoring…"):
            try:
                from semantic_score import SemanticScorer
                from career_relevance import career_relevance_score
                from scoring import (
                    experience_score, company_quality_score, skill_score,
                    behavior_score, location_score, skill_assessment_score,
                    title_disqualifier, detect_honeypot,
                )
                from explain import generate_reasoning

                W = dict(semantic=0.30, career=0.20, company=0.12,
                         experience=0.12, skill=0.12, behavior=0.08,
                         location=0.04, assessment=0.02)

                scorer = SemanticScorer(candidates)
                sems   = scorer.score_all()

                results, skipped = [], []
                for i, c in enumerate(candidates):
                    if detect_honeypot(c):
                        skipped.append((c["candidate_id"], "honeypot")); continue
                    if not title_disqualifier(c):
                        skipped.append((c["candidate_id"], "off-domain")); continue

                    sem = float(sems[i])
                    car = career_relevance_score(c)
                    co  = company_quality_score(c)
                    exp = experience_score(c)
                    sk  = skill_score(c)
                    beh = behavior_score(c)
                    loc = location_score(c)
                    ass = skill_assessment_score(c)

                    final = (W["semantic"]*sem + W["career"]*car + W["company"]*co +
                             W["experience"]*exp + W["skill"]*sk + W["behavior"]*beh +
                             W["location"]*loc + W["assessment"]*ass)

                    sig = c.get("redrob_signals", {})
                    if sig.get("recruiter_response_rate", 0) < 0.10 and \
                       not sig.get("open_to_work_flag", False):
                        final *= 0.60

                    sc = dict(semantic_score=round(sem,3), career_score=round(car,3),
                              skill_score=round(sk,3), company_score=round(co,3),
                              behavior_score=round(beh,3), final_score=final)
                    results.append({
                        **sc,
                        "candidate_id": c["candidate_id"],
                        "title": c.get("profile",{}).get("current_title",""),
                        "yoe":   c.get("profile",{}).get("years_of_experience",0),
                        "loc":   c.get("profile",{}).get("location",""),
                        "reasoning": generate_reasoning(c, sc),
                    })

                results.sort(key=lambda x: -x["final_score"])
                st.success(f"✅ Ranked {len(results)} | {len(skipped)} filtered")

                st.subheader("3. Results")
                for rank, r in enumerate(results, 1):
                    with st.expander(
                        f"#{rank}  {r['candidate_id']}  —  {r['title']}  "
                        f"({r['yoe']:.1f}yrs, {r['loc']})  **Score: {r['final_score']:.3f}**",
                        expanded=(rank <= 3)
                    ):
                        c1,c2,c3,c4,c5 = st.columns(5)
                        c1.metric("Semantic", r["semantic_score"])
                        c2.metric("Career",   r["career_score"])
                        c3.metric("Skills",   r["skill_score"])
                        c4.metric("Company",  r["company_score"])
                        c5.metric("Behavior", r["behavior_score"])
                        st.markdown(f"**Reasoning:** {r['reasoning']}")

                st.subheader("4. Download XLSX")
                mx = results[0]["final_score"] if results else 1
                mn = results[-1]["final_score"] if results else 0
                rng = mx - mn if mx > mn else 1
                rows = []
                for rank, r in enumerate(results, 1):
                    norm = 0.40 + 0.59*(r["final_score"]-mn)/rng - (rank-1)*1e-6
                    rows.append({"candidate_id": r["candidate_id"], "rank": rank,
                                 "score": round(min(norm, 0.9999), 6),
                                 "reasoning": r["reasoning"]})
                out_df = pd.DataFrame(rows, columns=["candidate_id","rank","score","reasoning"])
                xbuf = io.BytesIO()
                out_df.to_excel(xbuf, index=False, engine="openpyxl")
                st.download_button("⬇ Download submission.xlsx", xbuf.getvalue(),
                                   file_name="submission.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)

                if skipped:
                    with st.expander(f"Filtered ({len(skipped)})"):
                        for cid, reason in skipped:
                            st.text(f"{cid} — {reason}")

            except Exception as e:
                st.error(f"Error: {e}")
                import traceback; st.code(traceback.format_exc())
