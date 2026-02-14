import re
import statistics
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "run_with_depth.log"

pat = re.compile(r"\[ID\]\s+reached_depth=(\d+)")
depths = []

with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = pat.search(line)
        if m:
            depths.append(int(m.group(1)))

if not depths:
    print("No [ID] reached_depth lines found.")
    sys.exit(1)

print("Moves logged:", len(depths))
print("min depth:", min(depths))
print("avg depth:", round(statistics.mean(depths), 2))
print("max depth:", max(depths))
