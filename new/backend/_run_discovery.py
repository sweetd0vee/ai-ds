import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.loaders import load_dataframe
from app.core.data_analysis import analyze_data_structure
from app.core.data_insights import compute_correlations
from app.core.scientific_discovery import discover_insights, format_discovery_brief

p = Path(r"c:\Users\audit\Work\Arina\2026\ai-ds") / "аренда 1000.xlsx"
df = load_dataframe(str(p))
print("columns", list(df.columns))
parsed, _ = analyze_data_structure(df)
print("kinds", [(c["name"], c["kind"]) for c in parsed["columns"]])
corr = compute_correlations(df, parsed)
disc = discover_insights(df, parsed, corr)
print("roles", disc["roles"])
print("highlights", len(disc["highlights"]))
for h in disc["highlights"]:
    print(" -", h["kind"], "|", h["title"])
print("hypotheses", len(disc["hypotheses"]))
for h in disc["hypotheses"]:
    print(f"#{h['id']} [{h['kind']}/{h['priority']}] {h['title']}")
    print("   ", h["statement"][:220])
print("--- brief ---")
print(format_discovery_brief(disc)[:3000])
