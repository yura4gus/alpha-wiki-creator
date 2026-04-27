from pathlib import Path
import yaml
from tools.lint import check_required_frontmatter

def test_missing_frontmatter_field_detected(sample_wiki: Path):
    schema = {"module": ["title", "slug", "status", "owner"]}  # owner missing on all modules
    findings = check_required_frontmatter(sample_wiki / "wiki", schema, dir_to_type={"modules": "module"})
    assert any("owner" in f.message for f in findings)
