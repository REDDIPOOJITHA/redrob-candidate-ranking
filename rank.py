"""
rank.py — Single entry point as required by submission_spec.md Section 10.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.xlsx
"""
import argparse, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    sys.argv = ["main.py", "--input", args.candidates, "--output", args.out]
    from main import main
    main()
