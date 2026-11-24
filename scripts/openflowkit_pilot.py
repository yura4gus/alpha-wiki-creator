"""Run the optional Alpha-Wiki architecture pilot against a pinned Git tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

PACKAGE = "openflowkit@0.3.0"
DIAGRAMS = Path(__file__).resolve().parents[1] / "docs/alphawiki-openflowkit-v1/architecture"


def run(*args: str, allow_drift: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(args, text=True, capture_output=True, timeout=120)
    if result.returncode and not (allow_drift and result.returncode == 1):
        raise ValueError(result.stderr.strip() or result.stdout.strip() or f"{args[0]} failed")
    return result


def ofk(*args: str, allow_drift: bool = False) -> subprocess.CompletedProcess:
    return run("npx", "--yes", PACKAGE, *args, allow_drift=allow_drift)


def git(repo: Path, *args: str) -> str:
    return run("git", "-C", str(repo), *args).stdout.strip()


def check_checkout(repo: Path, sha: str) -> None:
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("use the root of a Git checkout")
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or git(repo, "rev-parse", "HEAD") != sha:
        raise ValueError("HEAD must match the requested full Git SHA")
    if git(repo, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("use a clean checkout; untracked and modified files are present")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def drift(snapshot: Path, model: Path) -> dict:
    result = ofk("drift", str(snapshot), "--model", str(model), "--json", allow_drift=True)
    report = json.loads(result.stdout)
    if type(report.get("drift")) is not bool or result.returncode != int(report["drift"]):
        raise ValueError("OpenFlowKit did not return a consistent drift report")
    return report


def render(model: Path, out: Path) -> None:
    ofk("validate", str(model), "--strict")
    ofk("render", str(model), "--strict", "-o", str(out / (model.stem + ".svg")))
    ofk("convert", str(model), "--strict", "-o", str(out / (model.stem + ".openflow.json")))


def main() -> int:
    if sys.version_info < (3, 12):
        print("UNKNOWN use Python 3.12 or later", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="clean checkout root")
    parser.add_argument("--sha", required=True, help="exact expected HEAD")
    parser.add_argument("--out", required=True, type=Path, help="new directory outside both checkouts")
    parser.add_argument("--baseline", type=Path, help="report.json from an earlier discovery of this repo")
    args = parser.parse_args()

    report_path = None
    try:
        repo = args.repo.resolve()
        out = args.out.resolve()
        if any(out.is_relative_to(root) for root in (repo, DIAGRAMS.parents[2])):
            raise ValueError("output must be outside the source and harness checkouts")
        check_checkout(repo, args.sha)
        git_dir = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
        if out.is_relative_to(git_dir):
            raise ValueError("output must be outside Git metadata")
        source = {"git_common_dir": str(git_dir), "sha": args.sha, "checkout": str(repo)}
        baseline_sha = None
        if args.baseline:
            baseline = json.loads(args.baseline.read_text())
            model = args.baseline.resolve().parent / "discovery.ofk"
            if (baseline.get("kind") != "repo-observed" or baseline.get("result") != "PASS"
                    or baseline["source"]["git_common_dir"] != source["git_common_dir"]
                    or baseline["model_sha256"] != sha256(model)):
                raise ValueError("baseline must be a passing, unchanged discovery from the same repository")
            baseline_sha = baseline["source"]["sha"]

        version = ofk("--version").stdout.strip()
        if version != "openflowkit 0.3.0":
            raise ValueError(f"unexpected CLI version: {version}")
        out.mkdir(parents=True, exist_ok=False)
        report_path = out / "report.json"
        with tempfile.TemporaryDirectory(prefix="openflowkit-") as temp:
            snapshot = Path(temp) / "source"
            snapshot.mkdir()
            archive = Path(temp) / "source.tar"
            git(repo, "archive", "--format=tar", f"--output={archive}", args.sha)
            with tarfile.open(archive) as tree:
                tree.extractall(snapshot, filter="data")

            if args.baseline is None:
                model = out / "discovery.ofk"
                discovery = ofk("discover", str(snapshot), "--name", repo.name,
                                "--out", str(model), "--no-svg").stdout
                (out / "discovery.txt").write_text(discovery)
                mapping = ofk("map", str(snapshot), "--depth", "detailed",
                              "--html", str(out / "repo-map.html")).stdout
                (out / "map.txt").write_text(mapping)
                render(model, out)
                for curated in sorted(DIAGRAMS.glob("*.ofk")):
                    render(curated, out)
                ofk("build", str(DIAGRAMS), "--out", str(out / "canvas-site"))

            report = drift(snapshot, model)
            check_checkout(repo, args.sha)
        receipt = {
            "result": "DRIFT" if report["drift"] else "PASS",
            "kind": "repo-drift" if args.baseline else "repo-observed",
            "source": source,
            "baseline_sha": baseline_sha,
            "model_sha256": sha256(model),
            "tool": version,
            "drift": report,
            "next_action": "review the reported topology differences" if report["drift"]
                           else "review source evidence and coverage before using the model",
        }
        report_path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"{receipt['result']} {report_path}")
        return int(report["drift"])
    except (KeyError, OSError, TypeError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        if report_path is not None:
            failure = {"result": "UNKNOWN", "source": source, "diagnostic": str(exc),
                       "next_action": "resolve the diagnostic and rerun with a new output directory"}
            try:
                report_path.write_text(json.dumps(failure, indent=2) + "\n")
            except OSError as write_error:
                print(f"could not save the failure receipt: {write_error}", file=sys.stderr)
        print(f"UNKNOWN {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
