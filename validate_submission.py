#!/usr/bin/env python3
"""
Validate the submission ranking file per the ACTUAL Redrob portal requirement:
"A ranked output file of your recommended candidates in the XLSX format."
(Portal upload widget: "Supports: excel, spreadsheet file upto 5 MB.")

This checks structural sanity (100 ranked rows, unique candidate IDs, unique
ranks 1-100, monotone non-increasing score) against a .xlsx file. It does NOT
invent extra rules beyond what the portal actually asks for and what is
needed for the ranking itself to make sense.
"""
import re
import sys
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = ["candidate_id", "rank", "score", "reasoning"]
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")
EXPECTED_DATA_ROWS = 100
MAX_SIZE_MB = 5


def validate_submission(xlsx_path):
    errors = []
    path = Path(xlsx_path)

    if path.suffix.lower() not in (".xlsx", ".xls"):
        errors.append("Filename must use a .xlsx extension (portal requires Excel format).")
        return errors

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        errors.append(f"File is {size_mb:.2f} MB; portal limit is {MAX_SIZE_MB} MB.")

    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        errors.append(f"Cannot read file as .xlsx: {e}")
        return errors

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required column(s): {missing_cols}. Found: {list(df.columns)}")
        return errors

    n = len(df)
    if n != EXPECTED_DATA_ROWS:
        errors.append(f"Expected exactly {EXPECTED_DATA_ROWS} ranked candidates; found {n}.")

    seen_ids, seen_ranks = set(), set()
    for i, row in df.iterrows():
        cid = str(row["candidate_id"]).strip()
        if not CANDIDATE_ID_PATTERN.match(cid):
            errors.append(f"Row {i+2}: candidate_id '{cid}' doesn't match CAND_XXXXXXX.")
        elif cid in seen_ids:
            errors.append(f"Row {i+2}: duplicate candidate_id '{cid}'.")
        else:
            seen_ids.add(cid)

        try:
            rank = int(row["rank"])
            if rank in seen_ranks:
                errors.append(f"Row {i+2}: duplicate rank {rank}.")
            seen_ranks.add(rank)
        except Exception:
            errors.append(f"Row {i+2}: rank must be an integer.")

    missing_ranks = set(range(1, EXPECTED_DATA_ROWS + 1)) - seen_ranks
    if missing_ranks:
        errors.append(f"Missing ranks: {sorted(missing_ranks)}")

    sorted_df = df.sort_values("rank")
    scores = sorted_df["score"].tolist()
    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            errors.append(
                f"score must be non-increasing by rank: "
                f"rank {i+1} ({scores[i]}) < rank {i+2} ({scores[i+1]})."
            )

    empty_reasoning = df["reasoning"].isna().sum() + (df["reasoning"].astype(str).str.strip() == "").sum()
    if empty_reasoning:
        errors.append(f"{empty_reasoning} row(s) have empty reasoning text.")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_submission.py <submission>.xlsx")
        sys.exit(1)

    errors = validate_submission(sys.argv[1])
    if errors:
        print(f"Validation failed ({len(errors)} issue(s)):\n")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

    print("Submission is valid.")


if __name__ == "__main__":
    main()
