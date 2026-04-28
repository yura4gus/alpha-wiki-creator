from pathlib import Path
from scripts.interview import InterviewConfig
from scripts.bootstrap import bootstrap
from tools.lint import run_all_checks
from tools._models import LintSeverity

def test_fresh_bootstrap_passes_lint_clean(tmp_path: Path):
    cfg = InterviewConfig(
        project_name="demo", project_description="d",
        wiki_dir="wiki", preset="software-project", overlay="none",
        custom_entity_types=None, i18n_languages=["en"],
        hooks="none", ci=False, schema_evolve_mode="gated",
    )
    bootstrap(target=tmp_path, config=cfg)
    findings = run_all_checks(tmp_path / "wiki", schema={}, dir_to_type={}, dependency_rules=[])
    errors = [f for f in findings if f.severity == LintSeverity.ERROR]
    assert errors == [], f"fresh bootstrap should be lint-clean, found errors: {errors}"
