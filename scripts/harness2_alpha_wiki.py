"""Run an isolated Alpha-Wiki evidence replay with the Google Harness² engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness2.core import tree
from harness2.core.proposer import Proposer, Reply
from harness2.core.schedule import run_task
from harness2.core.spec import BenchPrompts, BenchSpec, ChannelSpec
from harness2.substrate.opencode import OpencodeSubstrate

TRAIN = "unsupported-edge"
DOMAIN = "architecture-evidence"
CASES = {
    TRAIN: {"source_conflict": True, "same_sha": True, "source_bound": False},
    "stale-source": {"source_conflict": False, "same_sha": False, "source_bound": True},
    "supported-edge": {"source_conflict": False, "same_sha": True, "source_bound": True},
}
EXPECTED = {TRAIN: "DRIFT", "stale-source": "UNKNOWN", "supported-edge": "PASS"}


class AlphaWikiReplay:
    """Exercise evidence handling with a deterministic executor and public fixtures."""

    def __init__(self, out: Path):
        self.out = out
        self.substrate = OpencodeSubstrate()
        self.spec = BenchSpec(
            name="alpha-wiki", runs_root=out / "runs", install_mode="workspace_config",
            prompts=BenchPrompts(work="Classify a diagram edge against pinned source evidence."),
            channels={name: ChannelSpec("opencode", "local/deterministic")
                      for name in ("proposer", "selector")},
        )
        tree.write_tree(self.substrate.surface(),
                        {"systemprompt.md": "Trust a rendered diagram."},
                        self.base_harness(), stubs=False)
        for case, evidence in CASES.items():
            source = self.task_files(case)
            source.mkdir(parents=True)
            (source / "evidence.json").write_text(json.dumps(evidence))

    def task_prompt(self, task_id: str) -> str:
        return "Return PASS, DRIFT or UNKNOWN for the evidence in evidence.json."

    def domain_of(self, task_id: str) -> str:
        return DOMAIN

    def task_files(self, task_id: str) -> Path:
        return self.out / "sources" / task_id

    def base_harness(self) -> Path:
        return self.out / "baseline"

    def validate_tree(self, candidate: dict[str, str]) -> None:
        if not candidate.get("systemprompt.md"):
            raise ValueError("missing the evidence rule")

    def execute(self, task_id: str, harness_dir: Path | None, run_id: str,
                *, timeout: int | None = None) -> Path:
        rule = ((harness_dir or self.base_harness()) / "systemprompt.md").read_text()
        evidence = json.loads((self.task_files(task_id) / "evidence.json").read_text())
        verdict = "PASS"
        if "pinned source" in rule:
            if evidence["source_conflict"]:
                verdict = "DRIFT"
            elif not (evidence["same_sha"] and evidence["source_bound"]):
                verdict = "UNKNOWN"
        run_dir = self.out / "executions" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "answer.txt").write_text(verdict)
        return run_dir

    def delivered(self, run_dir: Path) -> bool:
        return (run_dir / "answer.txt").is_file()

    def deliverable_text(self, run_dir: Path) -> str:
        return (run_dir / "answer.txt").read_text()

    def deliverable_files(self, run_dir: Path) -> dict[str, str]:
        return {"answer.txt": self.deliverable_text(run_dir)}

    def trajectory(self, run_dir: Path, *, obs_trunc: int) -> str:
        return "[ACTION] Apply evidence rule\n[OBSERVATION] " + self.deliverable_text(run_dir)


class EvidenceEditor(Proposer):
    """Apply one scripted rule change inside the engine's candidate workspace."""

    def call(self, mission, context_dir, label, **kwargs) -> Reply:
        workspace = Path(context_dir) / "harness"
        (workspace / "systemprompt.md").write_text(
            "Check pinned source. A conflict is DRIFT; stale or missing evidence is UNKNOWN."
        )
        reply = Reply(label=label, text="<notes>Require source provenance.</notes>",
                      ok=True, attempts=1, workspace=workspace)
        self._calls.append(reply)
        return reply


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("output must be outside the Alpha-Wiki checkout")
    out.mkdir(parents=True, exist_ok=False)
    adapter = AlphaWikiReplay(out)
    editor = EvidenceEditor(adapter.spec.channels["proposer"])
    result = run_task(TRAIN, 1, adapter=adapter, prop=editor, modes=("agg",),
                      runs_root=adapter.spec.runs_root)
    selection = result.selections["agg"]
    if result.status != "ok" or not selection["ok"] or selection["chosen_is_base"]:
        print(f"UNKNOWN Harness² did not select a candidate: {result.errors}")
        return 2

    summary = next(adapter.spec.runs_root.glob(f"*/{TRAIN}/summary.json"))
    candidate = summary.parent / "harnesses" / selection["chosen_label"]
    scores = {}
    for case, expected in EXPECTED.items():
        outputs = {}
        for label, harness in (("baseline", None), ("candidate", candidate)):
            run_dir = adapter.execute(case, harness, f"evaluation/{case}/{label}")
            outputs[label] = adapter.deliverable_text(run_dir)
        scores[case] = {**outputs, "expected": expected, "candidate_pass": outputs["candidate"] == expected}
    passed = all(case["candidate_pass"] for case in scores.values())
    receipt = {"profile": "alpha-wiki", "executor": "deterministic", "k": 1,
               "engine_receipt": str(summary), "editor_calls": len(editor._calls),
               "result": "PASS" if passed else "DRIFT", "cases": scores}
    (out / "evaluation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["result"], out / "evaluation.json")
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
