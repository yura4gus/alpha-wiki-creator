from pathlib import Path
from click.testing import CliRunner
from tools.lint import cli

def test_lint_dry_run_exits_with_findings(sample_wiki: Path):
    r = CliRunner().invoke(cli, ["--wiki-dir", str(sample_wiki / "wiki"), "--dry-run"])
    assert r.exit_code != 0  # broken-link causes nonzero
    assert "broken-wikilink" in r.output
