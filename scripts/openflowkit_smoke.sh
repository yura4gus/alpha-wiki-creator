#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
out="${1:?pass a new directory outside the checkout}"
python3 - "$root" "$out" <<'PYOUT'
from pathlib import Path
import sys
if Path(sys.argv[2]).resolve().is_relative_to(Path(sys.argv[1])):
    raise SystemExit("fixture output must be outside the checkout")
PYOUT
mkdir "$out"
out="$(cd "$out" && pwd -P)"
source="$out/fixture"
git init --quiet "$source"

# Keep the fixture isolated and exercise OpenFlowKit with a real changed source.
cat > "$source/compose.yaml" <<'YAML'
services:
  alpha-fixture:
    image: alpine:3.22
YAML
printf '%s\n' '"""Source file for the offline repository map fixture."""' > "$source/main.py"
commit_fixture() {
  git -C "$source" add compose.yaml main.py
  git -C "$source" -c core.hooksPath=/dev/null -c user.name='Alpha-Wiki CI' \
    -c user.email=ci@example.invalid commit --quiet -m "$1"
}
commit_fixture baseline
sha="$(git -C "$source" rev-parse HEAD)"
python3 "$root/scripts/openflowkit_pilot.py" "$source" --sha "$sha" --out "$out/baseline"
cat >> "$source/compose.yaml" <<'YAML'
  drift-fixture:
    image: alpine:3.22
    depends_on:
      - alpha-fixture
YAML
commit_fixture drift
sha="$(git -C "$source" rev-parse HEAD)"
status=0
python3 "$root/scripts/openflowkit_pilot.py" "$source" --sha "$sha" --out "$out/drift" \
  --baseline "$out/baseline/report.json" || status=$?
test "$status" -eq 1
python3 - "$out/drift/report.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
assert report["result"] == "DRIFT", report
matches = [row for row in report["drift"]["missing"] if row["name"] == "drift-fixture"]
assert len(matches) == 1 and matches[0]["evidence"][0]["file"] == "compose.yaml", report
PY
